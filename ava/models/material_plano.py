"""Links e anexos exibidos junto ao documento nacional no plano de educação."""

from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from django.db import models

from ava.storage import private_ava_storage
from core.mixins import TenantModel


EXTENSOES_MATERIAL_PLANO = [
    "pdf", "doc", "docx", "odt", "xls", "xlsx", "ods", "csv", "txt",
    "ppt", "pptx", "odp", "jpg", "jpeg", "png", "webp", "zip",
]


def material_plano_upload_path(instance, filename):
    return f"ava/plano/materiais/{instance.cliente_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


def validar_tamanho_material_plano(arquivo):
    if arquivo.size > 20 * 1024 * 1024:
        raise ValidationError("O anexo deve ter no máximo 20 MB.")


class MaterialReferenciaPlano(TenantModel):
    titulo = models.CharField("Título", max_length=255)
    ciclo = models.ForeignKey(
        "ava.CicloReferencial", on_delete=models.PROTECT, null=True, blank=True,
        related_name="materiais_referencia", verbose_name="Ciclo",
        help_text="Deixe vazio para mostrar em todos os ciclos deste município.",
        limit_choices_to={"is_deleted": False},
    )
    link = models.URLField(
        "Link", max_length=2000, blank=True, validators=[URLValidator(schemes=["http", "https"])],
        help_text="Endereço completo, começando com https:// ou http://.",
    )
    arquivo = models.FileField(
        "Anexo", upload_to=material_plano_upload_path, storage=private_ava_storage,
        max_length=500, blank=True,
        validators=[FileExtensionValidator(EXTENSOES_MATERIAL_PLANO), validar_tamanho_material_plano],
        help_text="Até 20 MB. Documentos, planilhas, apresentações, imagens ou ZIP.",
    )
    nome_original = models.CharField(max_length=255, blank=True, editable=False)
    ordem = models.PositiveIntegerField("Ordem de exibição", default=0)
    ativo = models.BooleanField("Ativo", default=True)

    class Meta:
        verbose_name = "Material de referência do Plano de Educação"
        verbose_name_plural = "Materiais de referência do Plano de Educação"
        ordering = ["ordem", "titulo", "pk"]
        indexes = [models.Index(fields=["cliente", "ativo", "ordem"], name="ava_material_plano_ativo_idx")]

    def __str__(self):
        return self.titulo

    def clean(self):
        super().clean()
        if not self.link and not self.arquivo:
            raise ValidationError("Informe um link ou envie um anexo. Você também pode incluir os dois.")
        if self.ciclo_id and self.cliente_id and self.ciclo.cliente_id != self.cliente_id:
            raise ValidationError({"ciclo": "O ciclo deve pertencer ao mesmo município do material."})

    def save(self, *args, **kwargs):
        if self.arquivo and not self.arquivo._committed:
            self.nome_original = Path(self.arquivo.name).name[:255]
        super().save(*args, **kwargs)
