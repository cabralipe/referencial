import uuid

from django.conf import settings
from django.db import models

from core.mixins import TenantModel

from .course import Curso, TrilhaFormativa
from .enrollment import MatriculaCurso, MatriculaTrilha


def certificado_fundo_upload_path(instance, filename):
    return f"ava/certificados/fundos/{instance.cliente_id or 'sem-cliente'}/{filename}"


def certificado_assinatura_upload_path(instance, filename):
    return f"ava/certificados/assinaturas/{instance.config_id or 'sem-config'}/{filename}"


CERTIFICATE_VARIABLES = (
    ("aluno_nome", "Nome do cursista"),
    ("aluno_email", "E-mail"),
    ("aluno_role", "Tipo de usuario"),
    ("aluno_tipo_cadastro", "Tipo de cadastro"),
    ("aluno_escola", "Escola"),
    ("aluno_gt", "GTs"),
    ("aluno_eixos", "Eixos do usuario"),
    ("curso_nome", "Curso"),
    ("curso_eixos", "Eixos do curso"),
    ("carga_horaria", "Carga horaria"),
    ("nota_final", "Nota final"),
    ("progresso_percentual", "Progresso"),
    ("data_emissao", "Data de emissao"),
    ("codigo_validacao", "Codigo de validacao"),
)


DEFAULT_CERTIFICATE_VARIABLES = [
    "aluno_nome",
    "curso_nome",
    "carga_horaria",
    "data_emissao",
    "codigo_validacao",
]


def default_certificate_variables():
    return list(DEFAULT_CERTIFICATE_VARIABLES)


class ConfigCertificado(TenantModel):
    class TemaPadrao(models.TextChoices):
        CLASSICO = "classico", "Classico"
        MODERNO = "moderno", "Moderno"
        INSTITUCIONAL = "institucional", "Institucional"

    class Alinhamento(models.TextChoices):
        ESQUERDA = "left", "Alinhado a esquerda"
        CENTRO = "center", "Centralizado"
        DIREITA = "right", "Alinhado a direita"
        JUSTIFICADO = "justify", "Justificado"

    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name="config_certificado", null=True, blank=True)
    trilha = models.OneToOneField(
        TrilhaFormativa,
        on_delete=models.CASCADE,
        related_name="config_certificado",
        null=True,
        blank=True,
    )

    titulo = models.CharField("Titulo impresso", max_length=180, default="Certificado")
    subtitulo = models.TextField(
        "Subtitulo impresso",
        blank=True,
        default="Certificamos que {{aluno_nome}} concluiu {{curso_nome}}.",
    )
    subtitulo_alinhamento = models.CharField(
        "Alinhamento do subtitulo",
        max_length=10,
        choices=Alinhamento.choices,
        default=Alinhamento.CENTRO,
    )
    template_html = models.TextField(
        "Template HTML",
        blank=True,
        help_text="Opcional. Variaveis permitidas: {{aluno_nome}}, {{curso_nome}}, {{carga_horaria}}, {{data_emissao}}, etc.",
    )
    carga_horaria_impressa = models.PositiveIntegerField(
        "Carga horaria impressa",
        default=0,
        help_text="0 para usar a carga horaria original do curso/trilha.",
    )
    campos_variaveis = models.JSONField(
        "Campos variaveis impressos",
        default=default_certificate_variables,
        blank=True,
        help_text="Lista dos campos do usuario/curso que serao exibidos no certificado.",
    )
    fundo = models.ImageField(
        "Fundo do certificado",
        upload_to=certificado_fundo_upload_path,
        null=True,
        blank=True,
        help_text="Imagem de fundo opcional. Se nao enviada, o tema padrao sera usado.",
    )
    verso_ativo = models.BooleanField(
        "Incluir verso (segunda pagina)",
        default=False,
        help_text="Quando ativo, o PDF tera uma segunda pagina configuravel.",
    )
    verso_titulo = models.CharField(
        "Titulo do verso",
        max_length=180,
        blank=True,
        default="Conteudo programatico",
    )
    verso_template_html = models.TextField(
        "Conteudo do verso (HTML)",
        blank=True,
        help_text=(
            "Aceita HTML e as mesmas variaveis da frente, como {{aluno_nome}}, "
            "{{curso_nome}}, {{carga_horaria}} e {{codigo_validacao}}."
        ),
    )
    verso_alinhamento = models.CharField(
        "Alinhamento do conteudo do verso",
        max_length=10,
        choices=Alinhamento.choices,
        default=Alinhamento.ESQUERDA,
    )
    verso_fundo = models.ImageField(
        "Fundo do verso",
        upload_to=certificado_fundo_upload_path,
        null=True,
        blank=True,
        help_text="Imagem de fundo opcional para a segunda pagina.",
    )
    tema_padrao = models.CharField(
        "Tema padrao",
        max_length=30,
        choices=TemaPadrao.choices,
        default=TemaPadrao.CLASSICO,
    )
    texto_x = models.PositiveSmallIntegerField("Posicao horizontal do texto (%)", default=50)
    texto_y = models.PositiveSmallIntegerField("Posicao vertical do texto (%)", default=42)
    texto_largura = models.PositiveSmallIntegerField("Largura do bloco de texto (%)", default=72)
    texto_tamanho = models.PositiveSmallIntegerField("Tamanho do texto", default=18)
    titulo_tamanho = models.PositiveSmallIntegerField("Tamanho do titulo", default=42)
    cor_texto = models.CharField("Cor do texto", max_length=7, default="#1f2937")
    quantidade_assinaturas = models.PositiveSmallIntegerField(
        "Quantidade de assinaturas",
        default=2,
        help_text="Define os espacos proporcionais; cadastre imagens nas assinaturas abaixo quando houver PNG.",
    )
    assinatura_digital_url = models.URLField("URL da assinatura legada", blank=True)

    class Meta:
        verbose_name = "Configuracao de Certificado"
        verbose_name_plural = "Configuracoes de Certificados"

    def __str__(self):
        if self.curso:
            return f"Certificado Curso: {self.curso.titulo}"
        if self.trilha:
            return f"Certificado Trilha: {self.trilha.nome}"
        return "Configuracao sem curso/trilha"


class AssinaturaCertificado(TenantModel):
    config = models.ForeignKey(ConfigCertificado, on_delete=models.CASCADE, related_name="assinaturas")
    titulo = models.CharField("Nome/assinatura", max_length=150, blank=True)
    cargo = models.CharField("Cargo", max_length=150, blank=True)
    imagem = models.ImageField(
        "Imagem PNG da assinatura",
        upload_to=certificado_assinatura_upload_path,
        null=True,
        blank=True,
        help_text="Opcional. Sem imagem, o sistema mantem apenas o campo para assinatura.",
    )
    ordem = models.PositiveSmallIntegerField("Ordem", default=1)
    x = models.PositiveSmallIntegerField("Posicao horizontal (%)", default=0, help_text="0 usa distribuicao automatica.")
    y = models.PositiveSmallIntegerField("Posicao vertical (%)", default=78)
    largura = models.PositiveSmallIntegerField("Largura (%)", default=22)

    class Meta:
        verbose_name = "Assinatura de Certificado"
        verbose_name_plural = "Assinaturas de Certificado"
        ordering = ["ordem", "id"]
        indexes = [
            models.Index(fields=["cliente", "config", "ordem"]),
        ]

    def __str__(self):
        return self.titulo or f"Assinatura {self.ordem}"


class Certificado(TenantModel):
    matricula_curso = models.OneToOneField(
        MatriculaCurso,
        on_delete=models.CASCADE,
        related_name="certificado_emitido",
        null=True,
        blank=True,
    )
    matricula_trilha = models.OneToOneField(
        MatriculaTrilha,
        on_delete=models.CASCADE,
        related_name="certificado_emitido",
        null=True,
        blank=True,
    )
    config = models.ForeignKey(
        ConfigCertificado,
        on_delete=models.SET_NULL,
        related_name="certificados",
        null=True,
        blank=True,
    )
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificados_ava")
    emitido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="certificados_emitidos_ava",
        null=True,
        blank=True,
    )

    codigo_validacao = models.CharField("Codigo validacao unico", max_length=64, unique=True, blank=True)
    data_emissao = models.DateTimeField("Data de emissao", auto_now_add=True)
    liberado_em = models.DateTimeField(
        "Liberado no AVA em",
        null=True,
        blank=True,
        help_text="Em branco mantem o certificado oculto para o cursista.",
    )
    nota_final = models.DecimalField("Nota final no certificado", max_digits=5, decimal_places=2, null=True, blank=True)
    carga_horaria = models.PositiveIntegerField("Carga horaria", default=0)
    dados_impressos = models.JSONField("Dados impressos (snapshot)", default=dict, blank=True)
    arquivo_pdf = models.FileField("Arquivo PDF gerado", upload_to="ava/certificados/pdfs/", null=True, blank=True)

    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"
        indexes = [
            models.Index(fields=["cliente", "codigo_validacao"]),
            models.Index(fields=["cliente", "aluno"]),
            models.Index(fields=["cliente", "liberado_em"]),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo_validacao:
            self.codigo_validacao = uuid.uuid4().hex.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        aluno_nome = self.aluno.get_full_name() or getattr(self.aluno, "nome", "") or self.aluno.email
        if self.matricula_curso:
            return f"Certificado: {aluno_nome} - {self.matricula_curso.curso.titulo}"
        if self.matricula_trilha:
            return f"Certificado: {aluno_nome} - {self.matricula_trilha.trilha.nome}"
        return f"Certificado {self.codigo_validacao}"
