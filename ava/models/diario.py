"""Diário de Bordo do professor.

Registro estruturado de cada encontro/aula, com frequência (quantitativa ou
nominal), fotografias e comprovantes. O registro pode nascer de uma aula já
cadastrada no AVA ("no sistema"), de uma atividade presencial/externa sem
vínculo, ou de uma combinação das duas ("híbrida").
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from ava.storage import private_ava_storage
from core.mixins import TenantModel


ALLOWED_DIARIO_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp", "heic"]
ALLOWED_DIARIO_DOC_EXTENSIONS = [
    "pdf",
    "doc",
    "docx",
    "odt",
    "xls",
    "xlsx",
    "ods",
    "csv",
]
ALLOWED_DIARIO_MIDIA_EXTENSIONS = (
    ALLOWED_DIARIO_IMAGE_EXTENSIONS + ALLOWED_DIARIO_DOC_EXTENSIONS
)

ALLOWED_DIARIO_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}
ALLOWED_DIARIO_DOC_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/csv",
    "application/csv",
    "text/plain",
}

MAX_DIARIO_MIDIA_SIZE = 10 * 1024 * 1024


def diario_midia_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    diario = instance.diario
    return (
        f"ava/diario-bordo/{diario.cliente_id}/{diario.escola_id}/"
        f"{diario.pk or 'novo'}/{instance.pk or 'midia'}{suffix}"
    )


class OrigemAula(models.TextChoices):
    """De onde veio a aula registrada no diário."""

    NO_SISTEMA = "no_sistema", "No sistema"
    PRESENCIAL_EXTERNA = "presencial_externa", "Presencial externa"
    ATIVIDADE_EXTERNA = "atividade_externa", "Atividade externa"
    HIBRIDA = "hibrida", "Híbrida"


#: Origens que aceitam/necessitam vínculo com a estrutura do AVA.
ORIGENS_COM_SISTEMA = {OrigemAula.NO_SISTEMA, OrigemAula.HIBRIDA}
#: Origens que exigem a descrição manual do local/atividade.
ORIGENS_COM_EXTERNO = {
    OrigemAula.PRESENCIAL_EXTERNA,
    OrigemAula.ATIVIDADE_EXTERNA,
    OrigemAula.HIBRIDA,
}


class DiarioBordo(TenantModel):
    """Registro de um encontro/aula conduzido por um professor."""

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        ENVIADO = "enviado", "Enviado"
        REVISADO = "revisado", "Revisado"
        BLOQUEADO = "bloqueado", "Bloqueado"

    class TipoAtividade(models.TextChoices):
        AULA = "aula", "Aula"
        OFICINA = "oficina", "Oficina"
        FORMACAO = "formacao", "Formação"
        REUNIAO = "reuniao", "Reunião"
        VISITA_TECNICA = "visita_tecnica", "Visita técnica"
        OUTRA = "outra", "Outra"

    #: Status em que o professor ainda pode alterar o conteúdo do registro.
    STATUS_EDITAVEIS = {Status.RASCUNHO}

    escola = models.ForeignKey(
        "curriculum.Escola",
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
    )
    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
        verbose_name="Professor responsável",
    )

    origem = models.CharField(
        "Origem da aula",
        max_length=30,
        choices=OrigemAula.choices,
        default=OrigemAula.NO_SISTEMA,
    )

    # ---- Vínculo com a estrutura do AVA (origem "no sistema" ou "híbrida") ----
    curso = models.ForeignKey(
        "ava.Curso",
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
        null=True,
        blank=True,
        verbose_name="Curso/turma",
    )
    modulo = models.ForeignKey(
        "ava.CursoModulo",
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
        null=True,
        blank=True,
        verbose_name="Módulo",
    )
    aula = models.ForeignKey(
        "ava.Aula",
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
        null=True,
        blank=True,
        verbose_name="Aula cadastrada",
        help_text="Vincule a uma aula existente em vez de recriar o registro.",
    )

    # ---- Dados do encontro (comuns a todas as origens) ----
    data_aula = models.DateField("Data da aula/encontro")
    titulo = models.CharField("Título/assunto", max_length=255)
    conteudo_trabalhado = models.TextField("Conteúdo trabalhado")
    metodologia = models.TextField("Metodologia e atividades realizadas", blank=True)
    observacoes = models.TextField("Observações", blank=True)

    # ---- Dados exclusivos de atividades presenciais/externas ----
    tipo_atividade = models.CharField(
        "Tipo de atividade",
        max_length=30,
        choices=TipoAtividade.choices,
        blank=True,
    )
    local_realizacao = models.CharField("Local onde ocorreu", max_length=255, blank=True)
    instituicao_parceira = models.CharField(
        "Instituição ou espaço utilizado",
        max_length=255,
        blank=True,
    )
    grupo_participante = models.CharField(
        "Curso, turma ou grupo participante",
        max_length=255,
        blank=True,
        help_text="Use quando o grupo não estiver cadastrado como curso no AVA.",
    )
    responsavel_externo = models.CharField(
        "Responsável pela atividade",
        max_length=255,
        blank=True,
        help_text="Preencha quando a atividade for conduzida por outra pessoa.",
    )

    # ---- Frequência ----
    participantes_previstos = models.PositiveIntegerField(
        "Participantes previstos",
        null=True,
        blank=True,
    )
    participantes_presentes = models.PositiveIntegerField(
        "Participantes presentes",
        default=0,
    )
    frequencia_nominal = models.BooleanField(
        "Registrar lista nominal",
        default=False,
        help_text="Quando marcado, a quantidade é calculada pela lista de presença.",
    )

    # ---- Fluxo ----
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )
    enviado_em = models.DateTimeField(null=True, blank=True)
    revisado_em = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="diarios_bordo_revisados",
        null=True,
        blank=True,
    )
    parecer_revisao = models.TextField("Parecer da revisão", blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="diarios_bordo_criados",
        verbose_name="Criado por",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="diarios_bordo_atualizados",
        null=True,
        blank=True,
        verbose_name="Última alteração por",
    )

    class Meta:
        verbose_name = "Diário de bordo"
        verbose_name_plural = "Diários de bordo"
        ordering = ["-data_aula", "-id"]
        indexes = [
            models.Index(fields=["cliente", "escola", "status"]),
            models.Index(fields=["cliente", "professor", "data_aula"]),
            models.Index(fields=["cliente", "origem", "data_aula"]),
            models.Index(fields=["cliente", "curso", "modulo"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - legibilidade no admin
        return f"{self.data_aula:%d/%m/%Y} · {self.titulo}"

    # ------------------------------------------------------------------
    # Regras de origem
    # ------------------------------------------------------------------
    @property
    def usa_estrutura_do_sistema(self) -> bool:
        return self.origem in ORIGENS_COM_SISTEMA

    @property
    def usa_dados_externos(self) -> bool:
        return self.origem in ORIGENS_COM_EXTERNO

    @property
    def editavel(self) -> bool:
        return self.status in self.STATUS_EDITAVEIS

    def aplicar_dados_da_aula(self, aula) -> None:
        """Pré-preenche o registro a partir de uma aula já cadastrada."""

        modulo = aula.modulo
        self.aula = aula
        self.modulo = modulo
        self.curso = modulo.curso
        if not self.titulo:
            self.titulo = aula.titulo
        if not self.conteudo_trabalhado:
            self.conteudo_trabalhado = aula.resumo or ""

    def sincronizar_frequencia(self) -> None:
        """Mantém ``participantes_presentes`` coerente com a lista nominal."""

        if not self.frequencia_nominal or not self.pk:
            return
        self.participantes_presentes = self.participantes.filter(
            is_deleted=False,
            presente=True,
        ).count()

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}

        if self.escola_id and self.cliente_id and self.escola.cliente_id != self.cliente_id:
            errors["escola"] = "A escola deve pertencer ao mesmo município do registro."

        if self.professor_id and self.cliente_id:
            if self.professor.cliente_id != self.cliente_id:
                errors["professor"] = "O professor deve pertencer ao mesmo município do registro."
            elif self.professor.escola_id and self.professor.escola_id != self.escola_id:
                errors["professor"] = "O professor deve pertencer à escola selecionada."

        if self.curso_id and self.cliente_id and self.curso.cliente_id != self.cliente_id:
            errors["curso"] = "O curso deve pertencer ao mesmo município do registro."
        if self.modulo_id and self.curso_id and self.modulo.curso_id != self.curso_id:
            errors["modulo"] = "O módulo deve pertencer ao curso selecionado."
        if self.aula_id and self.modulo_id and self.aula.modulo_id != self.modulo_id:
            errors["aula"] = "A aula deve pertencer ao módulo selecionado."

        if self.usa_estrutura_do_sistema and not self.curso_id:
            errors["curso"] = (
                "Informe o curso/turma quando a aula for realizada no sistema."
            )
        if not self.usa_estrutura_do_sistema and (
            self.curso_id or self.modulo_id or self.aula_id
        ):
            errors["origem"] = (
                "Registros externos não devem ser vinculados a curso, módulo ou aula do sistema."
            )

        if self.usa_dados_externos:
            if not self.local_realizacao:
                errors["local_realizacao"] = (
                    "Informe o local onde a atividade foi realizada."
                )
            if not self.tipo_atividade:
                errors["tipo_atividade"] = "Informe o tipo da atividade realizada."
        elif self.local_realizacao or self.instituicao_parceira or self.tipo_atividade:
            # Campos externos preenchidos em registro totalmente interno: limpa
            # em vez de bloquear, para não travar a troca de origem.
            self.local_realizacao = ""
            self.instituicao_parceira = ""
            self.tipo_atividade = ""

        if (
            self.participantes_previstos is not None
            and self.participantes_presentes > self.participantes_previstos
        ):
            errors["participantes_presentes"] = (
                "A quantidade de presentes não pode superar a de previstos."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.aula_id and not self.modulo_id:
            self.modulo_id = self.aula.modulo_id
        if self.modulo_id and not self.curso_id:
            self.curso_id = self.modulo.curso_id
        super().save(*args, **kwargs)


class DiarioBordoParticipante(TenantModel):
    """Lista nominal de presença de um encontro."""

    diario = models.ForeignKey(
        DiarioBordo,
        on_delete=models.CASCADE,
        related_name="participantes",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="presencas_diario_bordo",
        null=True,
        blank=True,
        help_text="Use quando o participante já estiver cadastrado no sistema.",
    )
    nome = models.CharField("Nome do participante", max_length=255)
    identificacao = models.CharField(
        "Identificação",
        max_length=100,
        blank=True,
        help_text="Matrícula, turma ou outro identificador interno. Evite dados sensíveis.",
    )
    presente = models.BooleanField("Presente", default=True)
    justificativa = models.CharField("Justificativa da ausência", max_length=255, blank=True)

    class Meta:
        verbose_name = "Participante do diário de bordo"
        verbose_name_plural = "Participantes do diário de bordo"
        ordering = ["nome", "id"]
        indexes = [
            models.Index(fields=["cliente", "diario", "presente"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.nome

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if not (self.nome or "").strip():
            errors["nome"] = "Informe o nome do participante."
        if self.usuario_id and self.cliente_id and self.usuario.cliente_id != self.cliente_id:
            errors["usuario"] = "O participante deve pertencer ao mesmo município."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.usuario_id and not (self.nome or "").strip():
            self.nome = self.usuario.nome or self.usuario.email
        self.nome = (self.nome or "").strip()
        if not self.cliente_id and self.diario_id:
            self.cliente_id = self.diario.cliente_id
        super().save(*args, **kwargs)


class DiarioBordoMidia(TenantModel):
    """Fotografias e comprovantes anexados a um registro do diário."""

    class Tipo(models.TextChoices):
        FOTO = "foto", "Fotografia"
        COMPROVANTE = "comprovante", "Comprovante/documento"

    diario = models.ForeignKey(
        DiarioBordo,
        on_delete=models.CASCADE,
        related_name="midias",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.FOTO)
    arquivo = models.FileField(
        "Arquivo",
        upload_to=diario_midia_upload_path,
        storage=private_ava_storage,
        max_length=500,
        validators=[FileExtensionValidator(ALLOWED_DIARIO_MIDIA_EXTENSIONS)],
    )
    legenda = models.CharField("Legenda", max_length=255, blank=True)
    nome_original = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=150, blank=True)
    tamanho_bytes = models.PositiveBigIntegerField(default=0)
    ordem = models.PositiveIntegerField(default=0)
    consentimento_registrado = models.BooleanField(
        "Consentimento de imagem registrado",
        default=False,
        help_text="Confirma que há autorização de uso de imagem dos retratados (LGPD).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="midias_diario_bordo",
    )

    class Meta:
        verbose_name = "Mídia do diário de bordo"
        verbose_name_plural = "Mídias do diário de bordo"
        ordering = ["ordem", "id"]
        indexes = [
            models.Index(fields=["cliente", "diario", "tipo"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return self.legenda or self.nome_original or f"Mídia {self.pk}"

    @property
    def is_imagem(self) -> bool:
        return Path(self.arquivo.name or "").suffix.lower().lstrip(".") in (
            ALLOWED_DIARIO_IMAGE_EXTENSIONS
        )

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        arquivo = self.arquivo
        if arquivo:
            tamanho = getattr(arquivo, "size", 0) or 0
            if tamanho > MAX_DIARIO_MIDIA_SIZE:
                errors["arquivo"] = "O arquivo deve ter no máximo 10 MB."
            content_type = (
                getattr(arquivo, "content_type", "") or self.content_type or ""
            ).lower()
            extensao = Path(arquivo.name or "").suffix.lower().lstrip(".")
            if self.tipo == self.Tipo.FOTO:
                if extensao and extensao not in ALLOWED_DIARIO_IMAGE_EXTENSIONS:
                    errors["arquivo"] = "Fotografias aceitam apenas JPG, PNG, WEBP ou HEIC."
                elif content_type and content_type not in ALLOWED_DIARIO_IMAGE_MIME_TYPES:
                    errors["arquivo"] = "O tipo MIME enviado não corresponde a uma imagem."
            elif content_type and content_type not in (
                ALLOWED_DIARIO_IMAGE_MIME_TYPES | ALLOWED_DIARIO_DOC_MIME_TYPES
            ):
                errors["arquivo"] = "Tipo de arquivo não permitido para comprovantes."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.cliente_id and self.diario_id:
            self.cliente_id = self.diario.cliente_id
        if self.arquivo:
            if not self.nome_original:
                self.nome_original = Path(self.arquivo.name).name
            self.tamanho_bytes = getattr(self.arquivo, "size", self.tamanho_bytes) or 0
            content_type = getattr(self.arquivo, "content_type", "")
            if content_type:
                self.content_type = content_type
        super().save(*args, **kwargs)
