"""Salas de trabalho dos Grupos de Trabalho (GTs) do Referencial.

Cada objetivo oficial do Referencial ganha uma sala por ciclo. A sala concentra
inscrição/capacidade, diagnóstico, quadro de construção do objetivo (metas e
estratégias), reuniões com frequência, ata e os documentos gerados.

O cadastro de pessoas continua em :class:`core.models.Usuario` e o de grupos em
:class:`curriculum.models.GT` — aqui nada é duplicado: a sala apenas amarra o
GT existente a um objetivo e a um ciclo.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.mixins import TenantModel


class CicloReferencial(TenantModel):
    """Edição/ano de trabalho do Referencial, com as regras configuráveis."""

    nome = models.CharField("Nome do ciclo", max_length=150)
    descricao = models.TextField("Descrição", blank=True)
    inicio = models.DateField("Início dos trabalhos", null=True, blank=True)
    fim = models.DateField("Encerramento dos trabalhos", null=True, blank=True)

    inscricoes_abertas = models.BooleanField("Inscrições abertas", default=False)
    inscricoes_inicio = models.DateField(
        "Abertura das inscrições",
        null=True,
        blank=True,
        help_text="Deixe vazio para não limitar a data inicial.",
    )
    inscricoes_fim = models.DateField(
        "Encerramento das inscrições",
        null=True,
        blank=True,
        help_text="Deixe vazio para não limitar a data final.",
    )
    max_salas_por_participante = models.PositiveSmallIntegerField(
        "Limite de GTs por participante",
        null=True,
        blank=True,
        help_text="Deixe vazio para permitir a inscrição em quantos GTs o participante quiser.",
    )
    permite_lista_espera = models.BooleanField(
        "Permitir lista de espera",
        default=True,
        help_text="Quando a sala lota, a inscrição entra em fila ordenada em vez de ser recusada.",
    )
    confirmacao_automatica = models.BooleanField(
        "Confirmar inscrições automaticamente",
        default=True,
        help_text=(
            "Desmarque para que cada pedido fique como 'solicitada' até a coordenação "
            "ou o administrador aprovar."
        ),
    )
    min_metas_para_aprovacao = models.PositiveSmallIntegerField(
        "Mínimo de metas para aprovar",
        default=1,
        help_text="Use 0 para não exigir um número mínimo de metas.",
    )
    min_estrategias_para_aprovacao = models.PositiveSmallIntegerField(
        "Mínimo de estratégias para aprovar",
        default=1,
        help_text="Use 0 para não exigir um número mínimo de estratégias.",
    )
    exige_ata_para_aprovacao = models.BooleanField(
        "Exigir ata validada para aprovar",
        default=False,
    )
    ativo = models.BooleanField("Ciclo ativo", default=True)

    class Meta:
        verbose_name = "Ciclo do Referencial"
        verbose_name_plural = "Ciclos do Referencial"
        ordering = ["-inicio", "nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "nome"],
                condition=models.Q(is_deleted=False),
                name="uniq_ciclo_referencial_nome",
            )
        ]
        indexes = [models.Index(fields=["cliente", "ativo"])]

    def __str__(self) -> str:  # pragma: no cover - legibilidade no admin
        return self.nome

    def clean(self):
        super().clean()
        if self.inicio and self.fim and self.fim < self.inicio:
            raise ValidationError({"fim": "O encerramento não pode ser anterior ao início."})
        if (
            self.inscricoes_inicio
            and self.inscricoes_fim
            and self.inscricoes_fim < self.inscricoes_inicio
        ):
            raise ValidationError(
                {"inscricoes_fim": "O fim das inscrições não pode ser anterior à abertura."}
            )

    @property
    def janela_inscricao_vigente(self) -> bool:
        """Indica se a data de hoje está dentro da janela configurada."""

        hoje = timezone.localdate()
        if self.inscricoes_inicio and hoje < self.inscricoes_inicio:
            return False
        if self.inscricoes_fim and hoje > self.inscricoes_fim:
            return False
        return True

    @property
    def aceita_inscricao(self) -> bool:
        return bool(self.ativo and self.inscricoes_abertas and self.janela_inscricao_vigente)


class ObjetivoReferencial(TenantModel):
    """Objetivo oficial do Referencial — cadastrado/importado, nunca inventado.

    O ``codigo`` é o identificador estável usado nas importações, na ordenação
    oficial e na nomenclatura dos documentos exportados.
    """

    codigo = models.CharField(
        "Código",
        max_length=20,
        help_text="Identificador estável do objetivo (ex.: 01, OBJ-01). Não altere depois de publicado.",
    )
    ordem = models.PositiveIntegerField(
        "Ordem oficial",
        default=0,
        help_text="Define a sequência usada na consolidação institucional.",
    )
    titulo = models.CharField("Título curto", max_length=255)
    texto = models.TextField(
        "Redação oficial",
        blank=True,
        help_text="Texto oficial do objetivo. Fica preservado mesmo quando o GT propõe nova redação.",
    )
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Objetivo do Referencial"
        verbose_name_plural = "Objetivos do Referencial"
        ordering = ["ordem", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "codigo"],
                condition=models.Q(is_deleted=False),
                name="uniq_objetivo_referencial_codigo",
            )
        ]
        indexes = [models.Index(fields=["cliente", "ativo", "ordem"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.codigo} · {self.titulo}"

    def clean(self):
        super().clean()
        self.codigo = (self.codigo or "").strip()
        if not self.codigo:
            raise ValidationError({"codigo": "Informe o código do objetivo."})
        if not (self.titulo or "").strip():
            raise ValidationError({"titulo": "Informe o título do objetivo."})


class SalaGT(TenantModel):
    """Sala de trabalho: um GT existente trabalhando um objetivo em um ciclo."""

    class Situacao(models.TextChoices):
        PLANEJAMENTO = "planejamento", "Em planejamento"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"
        ARQUIVADA = "arquivada", "Arquivada"

    #: Situações em que a sala ainda recebe inscrições e edição de conteúdo.
    SITUACOES_ABERTAS = {Situacao.PLANEJAMENTO, Situacao.EM_ANDAMENTO}

    ciclo = models.ForeignKey(
        CicloReferencial,
        on_delete=models.PROTECT,
        related_name="salas",
        verbose_name="Ciclo",
    )
    objetivo = models.ForeignKey(
        ObjetivoReferencial,
        on_delete=models.PROTECT,
        related_name="salas",
        verbose_name="Objetivo do Referencial",
    )
    gt = models.ForeignKey(
        "curriculum.GT",
        on_delete=models.PROTECT,
        related_name="salas_referencial",
        verbose_name="Grupo de Trabalho",
        help_text="Reaproveita o GT já cadastrado no Referencial.",
    )

    capacidade = models.PositiveIntegerField(
        "Limite de participantes",
        null=True,
        blank=True,
        help_text="Deixe vazio para não limitar o número de participantes.",
    )
    vagas_ocupadas = models.PositiveIntegerField(
        "Vagas confirmadas",
        default=0,
        editable=False,
        help_text="Mantido pelo sistema para validar a lotação de forma atômica.",
    )
    inscricoes_abertas = models.BooleanField("Inscrições abertas nesta sala", default=True)
    permite_lista_espera = models.BooleanField("Permitir lista de espera", default=True)
    participantes_editam_conteudo = models.BooleanField(
        "Participantes podem editar o conteúdo",
        default=False,
        help_text=(
            "Quando ativo, participantes confirmados colaboram no diagnóstico, nas metas e "
            "nas estratégias enquanto o conteúdo estiver editável."
        ),
    )
    inscricoes_inicio = models.DateField(
        "Abertura das inscrições (sala)",
        null=True,
        blank=True,
        help_text="Opcional. Sobrepõe a janela do ciclo apenas para esta sala.",
    )
    inscricoes_fim = models.DateField(
        "Encerramento das inscrições (sala)",
        null=True,
        blank=True,
    )

    situacao = models.CharField(
        "Situação",
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.PLANEJAMENTO,
    )
    observacoes = models.TextField("Observações", blank=True)

    arquivada_em = models.DateTimeField(null=True, blank=True)
    arquivada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="salas_gt_arquivadas",
        null=True,
        blank=True,
    )
    justificativa_situacao = models.TextField(
        "Justificativa da última mudança de situação",
        blank=True,
    )

    class Meta:
        verbose_name = "Sala de GT"
        verbose_name_plural = "Salas de GT"
        ordering = ["objetivo__ordem", "objetivo__codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "ciclo", "objetivo"],
                condition=models.Q(is_deleted=False),
                name="uniq_sala_gt_por_objetivo_ciclo",
            ),
            models.UniqueConstraint(
                fields=["cliente", "ciclo", "gt"],
                condition=models.Q(is_deleted=False),
                name="uniq_sala_gt_por_gt_ciclo",
            ),
        ]
        indexes = [
            models.Index(fields=["cliente", "ciclo", "situacao"]),
            models.Index(fields=["cliente", "gt"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.objetivo.codigo} · {self.gt.nome}"

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if self.ciclo_id and self.cliente_id and self.ciclo.cliente_id != self.cliente_id:
            errors["ciclo"] = "O ciclo deve pertencer ao mesmo município da sala."
        if self.objetivo_id and self.cliente_id and self.objetivo.cliente_id != self.cliente_id:
            errors["objetivo"] = "O objetivo deve pertencer ao mesmo município da sala."
        if self.gt_id and self.cliente_id and self.gt.cliente_id != self.cliente_id:
            errors["gt"] = "O GT deve pertencer ao mesmo município da sala."
        if (
            self.inscricoes_inicio
            and self.inscricoes_fim
            and self.inscricoes_fim < self.inscricoes_inicio
        ):
            errors["inscricoes_fim"] = "O fim das inscrições não pode ser anterior à abertura."
        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Capacidade e janela de inscrição
    # ------------------------------------------------------------------
    @property
    def sem_limite_de_vagas(self) -> bool:
        return self.capacidade is None

    @property
    def vagas_disponiveis(self) -> int | None:
        if self.capacidade is None:
            return None
        return max(self.capacidade - self.vagas_ocupadas, 0)

    @property
    def lotada(self) -> bool:
        return self.capacidade is not None and self.vagas_ocupadas >= self.capacidade

    @property
    def janela_inscricao_vigente(self) -> bool:
        hoje = timezone.localdate()
        inicio = self.inscricoes_inicio or (self.ciclo.inscricoes_inicio if self.ciclo_id else None)
        fim = self.inscricoes_fim or (self.ciclo.inscricoes_fim if self.ciclo_id else None)
        if inicio and hoje < inicio:
            return False
        if fim and hoje > fim:
            return False
        return True

    @property
    def aceita_inscricao(self) -> bool:
        if self.situacao not in self.SITUACOES_ABERTAS:
            return False
        if not self.inscricoes_abertas:
            return False
        if self.ciclo_id and not (self.ciclo.ativo and self.ciclo.inscricoes_abertas):
            return False
        return self.janela_inscricao_vigente

    @property
    def aceita_lista_espera(self) -> bool:
        ciclo_permite = self.ciclo.permite_lista_espera if self.ciclo_id else True
        return bool(self.permite_lista_espera and ciclo_permite)

    @property
    def editavel(self) -> bool:
        return self.situacao in self.SITUACOES_ABERTAS

    def recalcular_ocupacao(self) -> int:
        """Recalcula ``vagas_ocupadas`` a partir das inscrições confirmadas."""

        total = InscricaoSalaGT.raw_objects.filter(
            is_deleted=False,
            sala_id=self.pk,
            estado=InscricaoSalaGT.Estado.CONFIRMADA,
        ).count()
        if total != self.vagas_ocupadas:
            SalaGT.raw_objects.filter(pk=self.pk).update(vagas_ocupadas=total)
            self.vagas_ocupadas = total
        return total


class InscricaoSalaGT(TenantModel):
    """Vínculo de uma pessoa com uma sala, com estado e papel na sala.

    Um único registro por pessoa/sala: pedir inscrição novamente reabre o
    mesmo vínculo em vez de criar duplicata.
    """

    class Estado(models.TextChoices):
        SOLICITADA = "solicitada", "Solicitada"
        CONFIRMADA = "confirmada", "Confirmada"
        LISTA_ESPERA = "lista_espera", "Lista de espera"
        RECUSADA = "recusada", "Recusada"
        CANCELADA = "cancelada", "Cancelada"

    class Papel(models.TextChoices):
        COORDENACAO = "coordenacao", "Coordenação do GT"
        RELATORIA = "relatoria", "Relatoria"
        PARTICIPANTE = "participante", "Participante"
        LEITOR = "leitor", "Leitor"

    #: Estados que ocupam vaga e dão acesso de trabalho à sala.
    ESTADOS_ATIVOS = {Estado.CONFIRMADA}
    #: Estados que contam para o limite de GTs por participante.
    ESTADOS_EM_DISPUTA = {Estado.SOLICITADA, Estado.CONFIRMADA, Estado.LISTA_ESPERA}

    sala = models.ForeignKey(
        SalaGT,
        on_delete=models.CASCADE,
        related_name="inscricoes",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inscricoes_sala_gt",
        verbose_name="Participante",
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.SOLICITADA,
    )
    papel = models.CharField(
        "Papel na sala",
        max_length=20,
        choices=Papel.choices,
        default=Papel.PARTICIPANTE,
    )
    ordem_espera = models.PositiveIntegerField(
        "Posição na lista de espera",
        null=True,
        blank=True,
    )
    solicitada_em = models.DateTimeField("Solicitada em", default=timezone.now)
    decidida_em = models.DateTimeField("Decisão registrada em", null=True, blank=True)
    decidida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="inscricoes_sala_gt_decididas",
        null=True,
        blank=True,
        verbose_name="Responsável pela decisão",
    )
    papel_concedido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="papeis_sala_gt_concedidos",
        null=True,
        blank=True,
    )
    papel_concedido_em = models.DateTimeField(null=True, blank=True)
    justificativa = models.TextField("Justificativa/observação", blank=True)

    class Meta:
        verbose_name = "Inscrição em sala de GT"
        verbose_name_plural = "Inscrições em salas de GT"
        ordering = ["sala", "ordem_espera", "usuario__nome", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "sala", "usuario"],
                condition=models.Q(is_deleted=False),
                name="uniq_inscricao_sala_gt_por_usuario",
            )
        ]
        indexes = [
            models.Index(fields=["cliente", "sala", "estado"]),
            models.Index(fields=["cliente", "usuario", "estado"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        nome = getattr(self.usuario, "nome", "") or getattr(self.usuario, "email", "")
        return f"{nome} · {self.get_estado_display()}"

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if self.sala_id and self.cliente_id and self.sala.cliente_id != self.cliente_id:
            errors["sala"] = "A sala deve pertencer ao mesmo município da inscrição."
        if self.usuario_id and self.cliente_id:
            usuario_cliente_id = getattr(self.usuario, "cliente_id", None)
            if usuario_cliente_id and usuario_cliente_id != self.cliente_id:
                errors["usuario"] = "O participante deve pertencer ao mesmo município da sala."
        if errors:
            raise ValidationError(errors)

    @property
    def ativa(self) -> bool:
        return self.estado in self.ESTADOS_ATIVOS

    @property
    def e_coordenacao(self) -> bool:
        return self.ativa and self.papel == self.Papel.COORDENACAO

    @property
    def e_relatoria(self) -> bool:
        return self.ativa and self.papel in {self.Papel.RELATORIA, self.Papel.COORDENACAO}


class TrabalhoGT(TenantModel):
    """Conteúdo construído pela sala: diagnóstico e quadro do objetivo."""

    class Estado(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_REVISAO = "em_revisao", "Em revisão"
        AJUSTES_SOLICITADOS = "ajustes_solicitados", "Ajustes solicitados"
        APROVADO = "aprovado", "Aprovado"
        PUBLICADO = "publicado", "Publicado"
        ARQUIVADO = "arquivado", "Arquivado"

    #: Estados em que relatoria/coordenação ainda editam o conteúdo.
    ESTADOS_EDITAVEIS = {Estado.RASCUNHO, Estado.AJUSTES_SOLICITADOS}
    #: Estados cujo conteúdo é considerado consolidável institucionalmente.
    ESTADOS_CONSOLIDAVEIS = {Estado.APROVADO, Estado.PUBLICADO}

    sala = models.OneToOneField(
        SalaGT,
        on_delete=models.CASCADE,
        related_name="trabalho",
    )

    # ---- Diagnóstico ----
    diagnostico_nao_aplicavel = models.BooleanField(
        "Diagnóstico não se aplica",
        default=False,
        help_text="Marque apenas quando o GT registrar formalmente que não há diagnóstico a apresentar.",
    )
    diagnostico_situacao = models.TextField("Caracterização da situação atual", blank=True)
    diagnostico_evidencias = models.TextField("Evidências e fontes consultadas", blank=True)
    diagnostico_desafios = models.TextField("Desafios identificados", blank=True)
    diagnostico_potencialidades = models.TextField("Potencialidades identificadas", blank=True)
    diagnostico_publico = models.TextField("Público e território pertinentes", blank=True)
    diagnostico_atualizado_em = models.DateTimeField(null=True, blank=True)
    diagnostico_atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="diagnosticos_gt_atualizados",
        null=True,
        blank=True,
    )

    # ---- Quadro do objetivo ----
    objetivo_proposto = models.TextField(
        "Proposta de redação do objetivo",
        blank=True,
        help_text="A redação oficial permanece preservada no cadastro do objetivo.",
    )
    observacoes = models.TextField("Observações", blank=True)
    pendencias = models.TextField("Pendências", blank=True)

    # ---- Fluxo ----
    estado = models.CharField(
        "Estado",
        max_length=25,
        choices=Estado.choices,
        default=Estado.RASCUNHO,
    )
    version = models.PositiveIntegerField(default=1)
    enviado_revisao_em = models.DateTimeField(null=True, blank=True)
    enviado_revisao_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="trabalhos_gt_enviados",
        null=True,
        blank=True,
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="trabalhos_gt_aprovados",
        null=True,
        blank=True,
    )
    publicado_em = models.DateTimeField(null=True, blank=True)
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="trabalhos_gt_publicados",
        null=True,
        blank=True,
    )
    parecer_revisao = models.TextField("Parecer/ajustes solicitados", blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="trabalhos_gt_atualizados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Trabalho do GT"
        verbose_name_plural = "Trabalhos dos GTs"
        ordering = ["sala__objetivo__ordem"]
        indexes = [models.Index(fields=["cliente", "estado"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Trabalho · {self.sala}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.pk:
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields:
                update_fields = set(update_fields)
                update_fields.update({"version", "updated_at"})
                kwargs["update_fields"] = list(update_fields)
        else:
            self.version = 1
        if not self.cliente_id and self.sala_id:
            self.cliente_id = self.sala.cliente_id
        super().save(*args, **kwargs)

    @property
    def etag(self) -> str:
        return f'W/"trabalho-gt-{self.pk}-v{self.version}"'

    @property
    def editavel(self) -> bool:
        return self.estado in self.ESTADOS_EDITAVEIS

    @property
    def consolidavel(self) -> bool:
        return self.estado in self.ESTADOS_CONSOLIDAVEIS

    @property
    def diagnostico_preenchido(self) -> bool:
        if self.diagnostico_nao_aplicavel:
            return True
        return bool((self.diagnostico_situacao or "").strip())


class MetaGT(TenantModel):
    """Meta/resultado esperado de um objetivo em construção."""

    trabalho = models.ForeignKey(
        TrabalhoGT,
        on_delete=models.CASCADE,
        related_name="metas",
    )
    ordem = models.PositiveIntegerField("Ordem", default=0)
    descricao = models.TextField("Meta/resultado esperado")
    indicador = models.TextField("Indicador ou evidência de acompanhamento", blank=True)
    prazo = models.CharField("Prazo/período", max_length=120, blank=True)
    observacoes = models.TextField("Observações", blank=True)

    class Meta:
        verbose_name = "Meta do GT"
        verbose_name_plural = "Metas do GT"
        ordering = ["ordem", "id"]
        indexes = [models.Index(fields=["cliente", "trabalho", "ordem"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.descricao[:80]

    def clean(self):
        super().clean()
        if not (self.descricao or "").strip():
            raise ValidationError({"descricao": "Descreva a meta."})

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id and self.trabalho_id:
            self.cliente_id = self.trabalho.cliente_id
        super().save(*args, **kwargs)


class EstrategiaGT(TenantModel):
    """Estratégia/ação vinculada a uma ou mais metas."""

    trabalho = models.ForeignKey(
        TrabalhoGT,
        on_delete=models.CASCADE,
        related_name="estrategias",
    )
    ordem = models.PositiveIntegerField("Ordem", default=0)
    descricao = models.TextField("Estratégia/ação")
    responsavel = models.CharField("Responsável", max_length=255, blank=True)
    prazo = models.CharField("Prazo/período", max_length=120, blank=True)
    recursos = models.TextField("Recursos e apoios necessários", blank=True)
    indicador = models.TextField("Indicador ou evidência", blank=True)
    metas = models.ManyToManyField(
        MetaGT,
        related_name="estrategias",
        blank=True,
        verbose_name="Metas atendidas",
    )

    class Meta:
        verbose_name = "Estratégia do GT"
        verbose_name_plural = "Estratégias do GT"
        ordering = ["ordem", "id"]
        indexes = [models.Index(fields=["cliente", "trabalho", "ordem"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.descricao[:80]

    def clean(self):
        super().clean()
        if not (self.descricao or "").strip():
            raise ValidationError({"descricao": "Descreva a estratégia."})

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id and self.trabalho_id:
            self.cliente_id = self.trabalho.cliente_id
        super().save(*args, **kwargs)


class VersaoTrabalhoGT(TenantModel):
    """Retrato imutável do trabalho em uma transição de estado.

    Garante que o conteúdo aprovado permaneça recuperável e identificável
    mesmo quando o GT retomar a edição em uma nova versão.
    """

    trabalho = models.ForeignKey(
        TrabalhoGT,
        on_delete=models.CASCADE,
        related_name="versoes",
    )
    numero = models.PositiveIntegerField("Versão")
    estado = models.CharField("Estado registrado", max_length=25)
    conteudo_json = models.JSONField("Conteúdo", default=dict)
    motivo = models.CharField("Motivo do registro", max_length=255, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="versoes_trabalho_gt",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Versão do trabalho do GT"
        verbose_name_plural = "Versões do trabalho do GT"
        ordering = ["-numero", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "trabalho", "numero"],
                condition=models.Q(is_deleted=False),
                name="uniq_versao_trabalho_gt_numero",
            )
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"v{self.numero} · {self.estado}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id and self.trabalho_id:
            self.cliente_id = self.trabalho.cliente_id
        super().save(*args, **kwargs)


class ReuniaoGT(TenantModel):
    """Reunião da sala, base da frequência e da ata."""

    class Modalidade(models.TextChoices):
        PRESENCIAL = "presencial", "Presencial"
        ONLINE = "online", "Online"
        HIBRIDA = "hibrida", "Híbrida"

    class Situacao(models.TextChoices):
        AGENDADA = "agendada", "Agendada"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    sala = models.ForeignKey(
        SalaGT,
        on_delete=models.CASCADE,
        related_name="reunioes",
    )
    titulo = models.CharField("Título da reunião", max_length=255)
    data_hora = models.DateTimeField("Data e hora")
    pauta = models.TextField("Pauta", blank=True)
    modalidade = models.CharField(
        "Modalidade",
        max_length=20,
        choices=Modalidade.choices,
        default=Modalidade.PRESENCIAL,
    )
    local = models.CharField("Local", max_length=255, blank=True)
    link = models.URLField("Link de acesso", max_length=500, blank=True)
    situacao = models.CharField(
        "Situação",
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.AGENDADA,
    )
    responsavel_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reunioes_gt_registradas",
        verbose_name="Responsável pelo registro",
    )

    frequencia_validada = models.BooleanField("Frequência validada", default=False)
    frequencia_validada_em = models.DateTimeField(null=True, blank=True)
    frequencia_validada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="frequencias_gt_validadas",
        null=True,
        blank=True,
    )
    justificativa_reabertura = models.TextField(
        "Justificativa da última reabertura/correção",
        blank=True,
    )

    class Meta:
        verbose_name = "Reunião do GT"
        verbose_name_plural = "Reuniões do GT"
        ordering = ["-data_hora", "-id"]
        indexes = [
            models.Index(fields=["cliente", "sala", "data_hora"]),
            models.Index(fields=["cliente", "sala", "situacao"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{timezone.localtime(self.data_hora):%d/%m/%Y %H:%M} · {self.titulo}"

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if self.sala_id and self.cliente_id and self.sala.cliente_id != self.cliente_id:
            errors["sala"] = "A reunião deve pertencer ao mesmo município da sala."
        if self.modalidade in {self.Modalidade.PRESENCIAL, self.Modalidade.HIBRIDA} and not (
            self.local or ""
        ).strip():
            errors["local"] = "Informe o local da reunião presencial."
        if self.modalidade in {self.Modalidade.ONLINE, self.Modalidade.HIBRIDA} and not (
            self.link or ""
        ).strip():
            errors["link"] = "Informe o link de acesso da reunião online."
        if not (self.titulo or "").strip():
            errors["titulo"] = "Informe o título da reunião."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id and self.sala_id:
            self.cliente_id = self.sala.cliente_id
        super().save(*args, **kwargs)

    @property
    def presencas_abertas(self) -> bool:
        return not self.frequencia_validada and self.situacao != self.Situacao.CANCELADA

    def resumo_frequencia(self) -> dict[str, int]:
        presencas = self.presencas.filter(is_deleted=False)
        total = presencas.count()
        presentes = presencas.filter(situacao=PresencaReuniaoGT.Situacao.PRESENTE).count()
        justificadas = presencas.filter(
            situacao=PresencaReuniaoGT.Situacao.JUSTIFICADA
        ).count()
        return {
            "total": total,
            "presentes": presentes,
            "justificadas": justificadas,
            "ausentes": total - presentes - justificadas,
        }


class PresencaReuniaoGT(TenantModel):
    """Presença de um membro do GT em uma reunião.

    A presença é sempre lançada por uma pessoa responsável — nunca inferida a
    partir de login ou de acesso à sala.
    """

    class Situacao(models.TextChoices):
        PRESENTE = "presente", "Presente"
        AUSENTE = "ausente", "Ausente"
        JUSTIFICADA = "justificada", "Ausência justificada"

    reuniao = models.ForeignKey(
        ReuniaoGT,
        on_delete=models.CASCADE,
        related_name="presencas",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="presencas_reuniao_gt",
        verbose_name="Membro do GT",
    )
    situacao = models.CharField(
        "Situação",
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.AUSENTE,
    )
    justificativa = models.CharField("Justificativa", max_length=255, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="presencas_gt_registradas",
        null=True,
        blank=True,
    )
    registrado_em = models.DateTimeField(null=True, blank=True)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="presencas_gt_alteradas",
        null=True,
        blank=True,
    )
    alterado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Presença em reunião do GT"
        verbose_name_plural = "Presenças em reuniões do GT"
        ordering = ["usuario__nome", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "reuniao", "usuario"],
                condition=models.Q(is_deleted=False),
                name="uniq_presenca_reuniao_gt_usuario",
            )
        ]
        indexes = [models.Index(fields=["cliente", "reuniao", "situacao"])]

    def __str__(self) -> str:  # pragma: no cover
        nome = getattr(self.usuario, "nome", "") or getattr(self.usuario, "email", "")
        return f"{nome} · {self.get_situacao_display()}"

    def clean(self):
        super().clean()
        if self.situacao == self.Situacao.JUSTIFICADA and not (self.justificativa or "").strip():
            raise ValidationError(
                {"justificativa": "Registre a justificativa da ausência."}
            )

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.cliente_id and self.reuniao_id:
            self.cliente_id = self.reuniao.cliente_id
        super().save(*args, **kwargs)


class ModeloAtaGT(TenantModel):
    """Modelo institucional de ata, administrável centralmente e versionado.

    Publicar um novo modelo cria uma nova versão; as atas já geradas guardam o
    retrato do modelo que usaram e não mudam.
    """

    SECOES_PADRAO = [
        {"chave": "pauta", "titulo": "Pauta", "orientacao": "Itens previstos para a reunião."},
        {
            "chave": "sintese",
            "titulo": "Síntese das discussões",
            "orientacao": "Resumo do que foi debatido pelo grupo.",
        },
        {
            "chave": "decisoes",
            "titulo": "Decisões",
            "orientacao": "Deliberações tomadas pelo GT.",
        },
        {
            "chave": "encaminhamentos",
            "titulo": "Encaminhamentos, responsáveis e prazos",
            "orientacao": "O que será feito, por quem e até quando.",
        },
        {
            "chave": "pendencias",
            "titulo": "Pendências",
            "orientacao": "Questões que seguem abertas.",
        },
        {
            "chave": "assinaturas",
            "titulo": "Assinaturas / ciência",
            "orientacao": "Campos para assinatura ou registro de ciência conforme o processo local.",
        },
    ]

    nome = models.CharField("Nome do modelo", max_length=150)
    versao = models.PositiveIntegerField("Versão", default=1)
    ativo = models.BooleanField("Modelo em uso", default=True)
    cabecalho = models.TextField("Cabeçalho institucional", blank=True)
    rodape = models.TextField("Rodapé institucional", blank=True)
    orientacoes = models.TextField("Orientações de preenchimento", blank=True)
    secoes = models.JSONField(
        "Seções",
        default=list,
        blank=True,
        help_text="Lista de seções com chave, título e orientação. Vazio usa as seções padrão.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="modelos_ata_gt_criados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Modelo de ata do GT"
        verbose_name_plural = "Modelos de ata do GT"
        ordering = ["nome", "-versao"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "nome", "versao"],
                condition=models.Q(is_deleted=False),
                name="uniq_modelo_ata_gt_nome_versao",
            )
        ]
        indexes = [models.Index(fields=["cliente", "ativo"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.nome} (v{self.versao})"

    def secoes_efetivas(self) -> list[dict]:
        if isinstance(self.secoes, list) and self.secoes:
            return [secao for secao in self.secoes if isinstance(secao, dict) and secao.get("chave")]
        return list(self.SECOES_PADRAO)


class AtaReuniaoGT(TenantModel):
    """Minuta/ata de uma reunião, gerada a partir do modelo institucional."""

    class Estado(models.TextChoices):
        MINUTA = "minuta", "Minuta"
        EM_REVISAO = "em_revisao", "Em revisão"
        VALIDADA = "validada", "Ata validada"

    ESTADOS_EDITAVEIS = {Estado.MINUTA, Estado.EM_REVISAO}

    reuniao = models.OneToOneField(
        ReuniaoGT,
        on_delete=models.CASCADE,
        related_name="ata",
    )
    modelo = models.ForeignKey(
        ModeloAtaGT,
        on_delete=models.SET_NULL,
        related_name="atas",
        null=True,
        blank=True,
    )
    modelo_nome = models.CharField("Modelo utilizado", max_length=150, blank=True)
    modelo_versao = models.PositiveIntegerField("Versão do modelo", default=1)
    estrutura_json = models.JSONField(
        "Retrato do modelo",
        default=dict,
        blank=True,
        help_text="Cópia do modelo no momento da criação da minuta.",
    )

    pauta = models.TextField("Pauta", blank=True)
    sintese = models.TextField("Síntese das discussões", blank=True)
    decisoes = models.TextField("Decisões", blank=True)
    encaminhamentos = models.TextField("Encaminhamentos, responsáveis e prazos", blank=True)
    pendencias = models.TextField("Pendências", blank=True)
    assinaturas = models.TextField("Assinaturas / ciência", blank=True)
    secoes_extra = models.JSONField(
        "Seções adicionais do modelo",
        default=dict,
        blank=True,
    )

    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=Estado.choices,
        default=Estado.MINUTA,
    )
    version = models.PositiveIntegerField(default=1)
    validada_em = models.DateTimeField(null=True, blank=True)
    validada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="atas_gt_validadas",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="atas_gt_atualizadas",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Ata de reunião do GT"
        verbose_name_plural = "Atas de reuniões do GT"
        ordering = ["-reuniao__data_hora"]
        indexes = [models.Index(fields=["cliente", "estado"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.get_estado_display()} · {self.reuniao_id}"

    def save(self, *args, **kwargs):  # type: ignore[override]
        if self.pk:
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields:
                update_fields = set(update_fields)
                update_fields.update({"version", "updated_at"})
                kwargs["update_fields"] = list(update_fields)
        else:
            self.version = 1
        if not self.cliente_id and self.reuniao_id:
            self.cliente_id = self.reuniao.cliente_id
        super().save(*args, **kwargs)

    @property
    def etag(self) -> str:
        return f'W/"ata-gt-{self.pk}-v{self.version}"'

    @property
    def editavel(self) -> bool:
        return self.estado in self.ESTADOS_EDITAVEIS

    @property
    def validada(self) -> bool:
        return self.estado == self.Estado.VALIDADA
