"""Planilhas configuráveis.

O administrador monta o modelo de planilha pela interface (nome, escopo,
colunas, tipos, obrigatoriedade, validações). Os dados importados ficam
gravados em registros/valores estruturados — consultáveis, filtráveis,
ordenáveis e exportáveis — e não apenas no arquivo XLSX original.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import slugify

from ava.storage import private_ava_storage
from core.mixins import TenantModel


ALLOWED_PLANILHA_EXTENSIONS = ["xlsx", "xlsm", "xls", "csv", "ods"]
MAX_PLANILHA_FILE_SIZE = 20 * 1024 * 1024

VALORES_VERDADEIROS = {"1", "sim", "s", "true", "verdadeiro", "yes", "y", "x"}
VALORES_FALSOS = {"0", "nao", "não", "n", "false", "falso", "no"}

FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y")


def planilha_importacao_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"ava/planilhas/{instance.cliente_id}/{instance.modelo_id}/"
        f"{instance.pk or 'novo'}{suffix}"
    )


def planilha_valor_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    registro = instance.registro
    return (
        f"ava/planilhas/{registro.cliente_id}/{registro.modelo_id}/valores/"
        f"{registro.pk or 'novo'}/{instance.coluna_id}{suffix}"
    )


class ModeloPlanilha(TenantModel):
    """Definição, feita pelo administrador, de uma planilha do município."""

    nome = models.CharField("Nome do modelo", max_length=150)
    slug = models.SlugField("Identificador", max_length=160)
    descricao = models.TextField("Descrição", blank=True)
    versao = models.PositiveIntegerField("Versão", default=1)
    ativo = models.BooleanField("Ativo", default=True)

    escola = models.ForeignKey(
        "curriculum.Escola",
        on_delete=models.PROTECT,
        related_name="modelos_planilha",
        null=True,
        blank=True,
        help_text="Deixe vazio para valer em todo o município.",
    )
    curso = models.ForeignKey(
        "ava.Curso",
        on_delete=models.PROTECT,
        related_name="modelos_planilha",
        null=True,
        blank=True,
        help_text="Deixe vazio para valer em qualquer curso/turma.",
    )

    permite_professor = models.BooleanField(
        "Professores podem preencher",
        default=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="modelos_planilha_criados",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="modelos_planilha_atualizados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Modelo de planilha"
        verbose_name_plural = "Modelos de planilha"
        ordering = ["nome", "-versao"]
        unique_together = ("cliente", "slug", "versao")
        indexes = [
            models.Index(fields=["cliente", "ativo"]),
            models.Index(fields=["cliente", "escola", "curso"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.nome} (v{self.versao})"

    def clean(self):
        # O slug é derivado aqui (e não só no save) para que um full_clean()
        # anterior à gravação já enxergue o valor gerado.
        if not self.slug and self.nome:
            self.slug = slugify(self.nome)[:160]
        super().clean()
        errors: dict[str, str] = {}
        if self.escola_id and self.cliente_id and self.escola.cliente_id != self.cliente_id:
            errors["escola"] = "A escola deve pertencer ao mesmo município do modelo."
        if self.curso_id and self.cliente_id and self.curso.cliente_id != self.cliente_id:
            errors["curso"] = "O curso deve pertencer ao mesmo município do modelo."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)[:160]
        super().save(*args, **kwargs)

    def colunas_visiveis(self):
        return self.colunas.filter(is_deleted=False, visivel=True).order_by("ordem", "id")

    def colunas_ativas(self):
        return self.colunas.filter(is_deleted=False).order_by("ordem", "id")


class ColunaPlanilha(TenantModel):
    """Uma coluna configurável de um :class:`ModeloPlanilha`."""

    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        TEXTO_LONGO = "texto_longo", "Texto longo"
        DATA = "data", "Data"
        INTEIRO = "inteiro", "Número inteiro"
        DECIMAL = "decimal", "Número decimal"
        BOOLEANO = "booleano", "Sim/Não"
        SELECAO = "selecao", "Seleção"
        PROFESSOR = "professor", "Professor"
        ESCOLA = "escola", "Escola"
        PARTICIPANTE = "participante", "Aluno/Participante"
        ARQUIVO = "arquivo", "Arquivo"

    #: Tipos cujo valor aponta para um registro do próprio sistema.
    TIPOS_RELACIONAIS = {Tipo.PROFESSOR, Tipo.ESCOLA, Tipo.PARTICIPANTE}

    modelo = models.ForeignKey(
        ModeloPlanilha,
        on_delete=models.CASCADE,
        related_name="colunas",
    )
    chave = models.SlugField("Identificador da coluna", max_length=80)
    titulo = models.CharField("Título exibido", max_length=150)
    ajuda = models.CharField("Texto de ajuda", max_length=255, blank=True)
    tipo = models.CharField("Tipo", max_length=20, choices=Tipo.choices)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    obrigatorio = models.BooleanField("Obrigatório", default=False)
    visivel = models.BooleanField("Visível", default=True)
    valor_padrao = models.CharField("Valor padrão", max_length=255, blank=True)
    opcoes = models.JSONField(
        "Opções de seleção",
        default=list,
        blank=True,
        help_text="Lista de valores aceitos quando o tipo for 'Seleção'.",
    )
    validacoes = models.JSONField(
        "Regras de validação",
        default=dict,
        blank=True,
        help_text=(
            "Chaves aceitas: min, max, min_length, max_length, regex, "
            "data_min, data_max."
        ),
    )

    class Meta:
        verbose_name = "Coluna de planilha"
        verbose_name_plural = "Colunas de planilha"
        ordering = ["ordem", "id"]
        unique_together = ("modelo", "chave")
        indexes = [
            models.Index(fields=["cliente", "modelo", "ordem"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.titulo} ({self.get_tipo_display()})"

    def save(self, *args, **kwargs):
        if not self.chave:
            self.chave = slugify(self.titulo)[:80]
        if not self.cliente_id and self.modelo_id:
            self.cliente_id = self.modelo.cliente_id
        super().save(*args, **kwargs)

    def clean(self):
        if not self.chave and self.titulo:
            self.chave = slugify(self.titulo)[:80]
        if not self.cliente_id and self.modelo_id:
            self.cliente_id = self.modelo.cliente_id
        super().clean()
        errors: dict[str, str] = {}
        if self.tipo == self.Tipo.SELECAO and not self.opcoes_normalizadas():
            errors["opcoes"] = "Informe ao menos uma opção para colunas de seleção."
        if self.opcoes and not isinstance(self.opcoes, (list, tuple)):
            errors["opcoes"] = "As opções devem ser uma lista de valores."
        if self.validacoes and not isinstance(self.validacoes, dict):
            errors["validacoes"] = "As regras de validação devem ser um objeto."
        regex = (self.validacoes or {}).get("regex") if isinstance(self.validacoes, dict) else None
        if regex:
            try:
                re.compile(regex)
            except re.error:
                errors["validacoes"] = "A expressão regular informada é inválida."
        if errors:
            raise ValidationError(errors)

    def opcoes_normalizadas(self) -> list[str]:
        if not self.opcoes:
            return []
        if isinstance(self.opcoes, str):
            bruto = [parte.strip() for parte in self.opcoes.splitlines()]
        else:
            bruto = [str(item).strip() for item in self.opcoes]
        return [item for item in bruto if item]

    @property
    def armazena_em(self) -> str:
        """Nome do campo de :class:`ValorRegistroPlanilha` que guarda o valor."""

        if self.tipo in (self.Tipo.INTEIRO, self.Tipo.DECIMAL):
            return "valor_numero"
        if self.tipo == self.Tipo.DATA:
            return "valor_data"
        if self.tipo == self.Tipo.BOOLEANO:
            return "valor_booleano"
        if self.tipo in self.TIPOS_RELACIONAIS:
            return "valor_referencia_id"
        if self.tipo == self.Tipo.ARQUIVO:
            return "arquivo"
        return "valor_texto"


class RegistroPlanilha(TenantModel):
    """Uma linha preenchida de um modelo de planilha."""

    modelo = models.ForeignKey(
        ModeloPlanilha,
        on_delete=models.PROTECT,
        related_name="registros",
    )
    escola = models.ForeignKey(
        "curriculum.Escola",
        on_delete=models.PROTECT,
        related_name="registros_planilha",
        null=True,
        blank=True,
    )
    curso = models.ForeignKey(
        "ava.Curso",
        on_delete=models.PROTECT,
        related_name="registros_planilha",
        null=True,
        blank=True,
    )
    diario = models.ForeignKey(
        "ava.DiarioBordo",
        on_delete=models.SET_NULL,
        related_name="registros_planilha",
        null=True,
        blank=True,
        help_text="Vínculo opcional com um registro do diário de bordo.",
    )
    chave_externa = models.CharField(
        "Chave externa",
        max_length=150,
        blank=True,
        help_text="Identificador usado para atualizar registros já importados.",
    )
    importacao = models.ForeignKey(
        "ava.ImportacaoPlanilha",
        on_delete=models.SET_NULL,
        related_name="registros",
        null=True,
        blank=True,
    )
    linha_origem = models.PositiveIntegerField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registros_planilha_criados",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="registros_planilha_atualizados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Registro de planilha"
        verbose_name_plural = "Registros de planilha"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["cliente", "modelo", "escola"]),
            models.Index(fields=["cliente", "modelo", "chave_externa"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Registro {self.pk} de {self.modelo_id}"

    def save(self, *args, **kwargs):
        if not self.cliente_id and self.modelo_id:
            self.cliente_id = self.modelo.cliente_id
        super().save(*args, **kwargs)

    def valores_por_chave(self) -> dict[str, "ValorRegistroPlanilha"]:
        return {
            valor.coluna.chave: valor
            for valor in self.valores.filter(is_deleted=False).select_related("coluna")
        }


class ValorRegistroPlanilha(TenantModel):
    """Valor de uma coluna dentro de um registro, tipado conforme a coluna."""

    registro = models.ForeignKey(
        RegistroPlanilha,
        on_delete=models.CASCADE,
        related_name="valores",
    )
    coluna = models.ForeignKey(
        ColunaPlanilha,
        on_delete=models.PROTECT,
        related_name="valores",
    )
    valor_texto = models.TextField(blank=True)
    valor_numero = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    valor_data = models.DateField(null=True, blank=True)
    valor_booleano = models.BooleanField(null=True, blank=True)
    valor_referencia_id = models.PositiveBigIntegerField(null=True, blank=True)
    arquivo = models.FileField(
        upload_to=planilha_valor_upload_path,
        storage=private_ava_storage,
        max_length=500,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Valor de registro de planilha"
        verbose_name_plural = "Valores de registro de planilha"
        ordering = ["coluna__ordem", "id"]
        unique_together = ("registro", "coluna")
        indexes = [
            models.Index(fields=["cliente", "coluna", "valor_texto"]),
            models.Index(fields=["cliente", "coluna", "valor_numero"]),
            models.Index(fields=["cliente", "coluna", "valor_data"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.coluna_id}={self.valor_exibicao()}"

    def save(self, *args, **kwargs):
        if not self.cliente_id and self.registro_id:
            self.cliente_id = self.registro.cliente_id
        super().save(*args, **kwargs)

    def valor_bruto(self):
        campo = self.coluna.armazena_em
        if campo == "arquivo":
            return self.arquivo
        return getattr(self, campo)

    def valor_exibicao(self) -> str:
        tipo = self.coluna.tipo
        if tipo == ColunaPlanilha.Tipo.BOOLEANO:
            if self.valor_booleano is None:
                return ""
            return "Sim" if self.valor_booleano else "Não"
        if tipo == ColunaPlanilha.Tipo.DATA:
            return self.valor_data.strftime("%d/%m/%Y") if self.valor_data else ""
        if tipo == ColunaPlanilha.Tipo.INTEIRO:
            return str(int(self.valor_numero)) if self.valor_numero is not None else ""
        if tipo == ColunaPlanilha.Tipo.DECIMAL:
            return f"{self.valor_numero:.2f}" if self.valor_numero is not None else ""
        if tipo == ColunaPlanilha.Tipo.ARQUIVO:
            return Path(self.arquivo.name).name if self.arquivo else ""
        # Tipos relacionais guardam o rótulo legível em valor_texto.
        return self.valor_texto or ""


class ImportacaoPlanilha(TenantModel):
    """Registro de auditoria de cada importação realizada."""

    class Status(models.TextChoices):
        PENDENTE = "pendente", "Aguardando mapeamento"
        VALIDADA = "validada", "Validada"
        CONCLUIDA = "concluida", "Concluída"
        CANCELADA = "cancelada", "Cancelada"
        ERRO = "erro", "Com erros"

    class Modo(models.TextChoices):
        ADICIONAR = "adicionar", "Adicionar novos registros"
        ATUALIZAR = "atualizar", "Atualizar registros existentes"

    modelo = models.ForeignKey(
        ModeloPlanilha,
        on_delete=models.PROTECT,
        related_name="importacoes",
    )
    arquivo = models.FileField(
        "Arquivo enviado",
        upload_to=planilha_importacao_upload_path,
        storage=private_ava_storage,
        max_length=500,
        validators=[FileExtensionValidator(ALLOWED_PLANILHA_EXTENSIONS)],
    )
    nome_original = models.CharField(max_length=255, blank=True)
    tamanho_bytes = models.PositiveBigIntegerField(default=0)
    modo = models.CharField(max_length=20, choices=Modo.choices, default=Modo.ADICIONAR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    mapeamento = models.JSONField(
        "Mapeamento de colunas",
        default=dict,
        blank=True,
        help_text="Cabeçalho da planilha -> chave da coluna configurada.",
    )
    coluna_chave = models.CharField(
        "Coluna usada como chave",
        max_length=80,
        blank=True,
        help_text="Obrigatória no modo de atualização.",
    )
    cabecalhos = models.JSONField(default=list, blank=True)
    erros = models.JSONField(default=list, blank=True)
    total_linhas = models.PositiveIntegerField(default=0)
    total_criados = models.PositiveIntegerField(default=0)
    total_atualizados = models.PositiveIntegerField(default=0)
    total_ignorados = models.PositiveIntegerField(default=0)
    concluida_em = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="importacoes_planilha",
    )

    class Meta:
        verbose_name = "Importação de planilha"
        verbose_name_plural = "Importações de planilha"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["cliente", "modelo", "status"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.nome_original or self.arquivo.name} ({self.get_status_display()})"

    def clean(self):
        super().clean()
        if self.arquivo and getattr(self.arquivo, "size", 0) > MAX_PLANILHA_FILE_SIZE:
            raise ValidationError({"arquivo": "O arquivo deve ter no máximo 20 MB."})

    def save(self, *args, **kwargs):
        if not self.cliente_id and self.modelo_id:
            self.cliente_id = self.modelo.cliente_id
        if self.arquivo:
            if not self.nome_original:
                self.nome_original = Path(self.arquivo.name).name
            self.tamanho_bytes = getattr(self.arquivo, "size", self.tamanho_bytes) or 0
        super().save(*args, **kwargs)


# ----------------------------------------------------------------------
# Conversão/validação de valores conforme o tipo configurado
# ----------------------------------------------------------------------


class ValorInvalido(ValueError):
    """Valor de célula que não satisfaz a configuração da coluna."""


def converter_valor(coluna: ColunaPlanilha, bruto):
    """Converte ``bruto`` para o tipo da coluna, aplicando as validações.

    Retorna o valor já tipado (ou ``None`` quando vazio) e levanta
    :class:`ValorInvalido` com mensagem em português quando não for aceitável.
    """

    if bruto is None:
        texto = ""
    elif isinstance(bruto, str):
        texto = bruto.strip()
    elif isinstance(bruto, (datetime, date)):
        texto = bruto.isoformat()
    else:
        texto = str(bruto).strip()

    if not texto and coluna.valor_padrao:
        texto = coluna.valor_padrao.strip()

    if not texto:
        if coluna.obrigatorio:
            raise ValorInvalido(f"'{coluna.titulo}' é obrigatório.")
        return None

    regras = coluna.validacoes if isinstance(coluna.validacoes, dict) else {}
    tipo = coluna.tipo

    if tipo in (ColunaPlanilha.Tipo.TEXTO, ColunaPlanilha.Tipo.TEXTO_LONGO):
        limite_min = regras.get("min_length")
        limite_max = regras.get("max_length")
        if limite_min is not None and len(texto) < int(limite_min):
            raise ValorInvalido(
                f"'{coluna.titulo}' deve ter ao menos {limite_min} caracteres."
            )
        if limite_max is not None and len(texto) > int(limite_max):
            raise ValorInvalido(
                f"'{coluna.titulo}' deve ter no máximo {limite_max} caracteres."
            )
        regex = regras.get("regex")
        if regex and not re.fullmatch(regex, texto):
            raise ValorInvalido(f"'{coluna.titulo}' não está no formato esperado.")
        return texto

    if tipo == ColunaPlanilha.Tipo.SELECAO:
        opcoes = coluna.opcoes_normalizadas()
        correspondencia = next(
            (opcao for opcao in opcoes if opcao.casefold() == texto.casefold()),
            None,
        )
        if correspondencia is None:
            permitidas = ", ".join(opcoes) or "nenhuma opção configurada"
            raise ValorInvalido(
                f"'{coluna.titulo}' aceita apenas: {permitidas}."
            )
        return correspondencia

    if tipo == ColunaPlanilha.Tipo.BOOLEANO:
        normalizado = texto.casefold()
        if normalizado in VALORES_VERDADEIROS:
            return True
        if normalizado in VALORES_FALSOS:
            return False
        raise ValorInvalido(f"'{coluna.titulo}' aceita apenas Sim/Não.")

    if tipo == ColunaPlanilha.Tipo.INTEIRO:
        try:
            numero = int(Decimal(texto.replace(",", ".")))
        except (InvalidOperation, ValueError):
            raise ValorInvalido(f"'{coluna.titulo}' deve ser um número inteiro.") from None
        _validar_faixa_numerica(coluna, numero, regras)
        return Decimal(numero)

    if tipo == ColunaPlanilha.Tipo.DECIMAL:
        try:
            numero = Decimal(texto.replace(".", "").replace(",", ".")) if _usa_virgula(texto) else Decimal(texto)
        except InvalidOperation:
            raise ValorInvalido(f"'{coluna.titulo}' deve ser um número decimal.") from None
        _validar_faixa_numerica(coluna, numero, regras)
        return numero

    if tipo == ColunaPlanilha.Tipo.DATA:
        valor = _converter_data(texto)
        if valor is None:
            raise ValorInvalido(
                f"'{coluna.titulo}' deve ser uma data válida (dd/mm/aaaa)."
            )
        data_min = _converter_data(str(regras.get("data_min"))) if regras.get("data_min") else None
        data_max = _converter_data(str(regras.get("data_max"))) if regras.get("data_max") else None
        if data_min and valor < data_min:
            raise ValorInvalido(
                f"'{coluna.titulo}' não pode ser anterior a {data_min:%d/%m/%Y}."
            )
        if data_max and valor > data_max:
            raise ValorInvalido(
                f"'{coluna.titulo}' não pode ser posterior a {data_max:%d/%m/%Y}."
            )
        return valor

    # Tipos relacionais e arquivo são resolvidos pelo serviço de importação,
    # que tem acesso ao escopo do município. Aqui devolvemos o texto bruto.
    return texto


def _usa_virgula(texto: str) -> bool:
    return "," in texto


def _validar_faixa_numerica(coluna: ColunaPlanilha, numero, regras: dict) -> None:
    minimo = regras.get("min")
    maximo = regras.get("max")
    if minimo is not None and Decimal(str(numero)) < Decimal(str(minimo)):
        raise ValorInvalido(f"'{coluna.titulo}' deve ser maior ou igual a {minimo}.")
    if maximo is not None and Decimal(str(numero)) > Decimal(str(maximo)):
        raise ValorInvalido(f"'{coluna.titulo}' deve ser menor ou igual a {maximo}.")


def _converter_data(texto: str):
    texto = (texto or "").strip()
    if not texto:
        return None
    if "T" in texto:
        texto = texto.split("T", 1)[0]
    if " " in texto:
        texto = texto.split(" ", 1)[0]
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None
