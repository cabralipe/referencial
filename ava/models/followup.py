from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from ava.storage import private_ava_storage
from core.mixins import TenantModel


ALLOWED_FOLLOWUP_EXTENSIONS = [
    "pdf",
    "doc",
    "docx",
    "odt",
    "xls",
    "xlsx",
    "ods",
    "csv",
    "jpg",
    "jpeg",
    "png",
]
MAX_FOLLOWUP_FILE_SIZE = 20 * 1024 * 1024


def acompanhamento_upload_path(instance, filename):
    suffix = Path(filename).suffix.lower()
    return (
        f"ava/acompanhamento/{instance.cliente_id}/"
        f"{instance.escola_id}/{instance.created_by_id}/{instance.pk or 'novo'}{suffix}"
    )


class DocumentoAcompanhamento(TenantModel):
    class Categoria(models.TextChoices):
        RELATORIO = "relatorio", "Relatório"
        FREQUENCIA = "frequencia", "Frequência"
        EXPERIENCIA_EXITOSA = "experiencia_exitosa", "Experiência exitosa"
        PRATICA_PEDAGOGICA = "pratica_pedagogica", "Prática pedagógica"
        OUTRO = "outro", "Outro"

    escola = models.ForeignKey(
        "curriculum.Escola",
        on_delete=models.PROTECT,
        related_name="documentos_acompanhamento",
    )
    curso = models.ForeignKey(
        "ava.Curso",
        on_delete=models.PROTECT,
        related_name="documentos_acompanhamento",
        null=True,
        blank=True,
        verbose_name="Turma/curso",
    )
    aluno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documentos_acompanhamento",
        null=True,
        blank=True,
    )
    categoria = models.CharField(max_length=30, choices=Categoria.choices)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    periodo_referencia = models.DateField(
        "Período de referência",
        null=True,
        blank=True,
        help_text="Use o primeiro dia do mês ou a data à qual o registro se refere.",
    )
    arquivo = models.FileField(
        upload_to=acompanhamento_upload_path,
        storage=private_ava_storage,
        max_length=500,
        validators=[FileExtensionValidator(ALLOWED_FOLLOWUP_EXTENSIONS)],
    )
    nome_original = models.CharField(max_length=255, blank=True)
    tamanho_bytes = models.PositiveBigIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documentos_acompanhamento_criados",
        verbose_name="Incluído por",
    )
    arquivado = models.BooleanField(default=False)
    arquivado_em = models.DateTimeField(null=True, blank=True)
    arquivado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="documentos_acompanhamento_arquivados",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Documento de acompanhamento"
        verbose_name_plural = "Documentos de acompanhamento"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["cliente", "escola", "arquivado"]),
            models.Index(fields=["cliente", "curso", "aluno"]),
            models.Index(fields=["cliente", "categoria", "periodo_referencia"]),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.escola_id and self.cliente_id and self.escola.cliente_id != self.cliente_id:
            errors["escola"] = "A escola deve pertencer ao mesmo município do documento."
        if self.curso_id and self.cliente_id and self.curso.cliente_id != self.cliente_id:
            errors["curso"] = "A turma/curso deve pertencer ao mesmo município do documento."
        if self.aluno_id:
            if self.aluno.cliente_id != self.cliente_id:
                errors["aluno"] = "O aluno deve pertencer ao mesmo município do documento."
            elif self.aluno.escola_id != self.escola_id:
                errors["aluno"] = "O aluno deve pertencer à escola selecionada."
            elif self.curso_id and not self.curso.matriculas.filter(
                aluno_id=self.aluno_id,
                is_deleted=False,
            ).exists():
                errors["aluno"] = "O aluno deve estar matriculado na turma/curso selecionada."
        if self.arquivo and getattr(self.arquivo, "size", 0) > MAX_FOLLOWUP_FILE_SIZE:
            errors["arquivo"] = "O arquivo deve ter no máximo 20 MB."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.arquivo:
            if not self.nome_original:
                self.nome_original = Path(self.arquivo.name).name
            self.tamanho_bytes = getattr(self.arquivo, "size", self.tamanho_bytes) or 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
