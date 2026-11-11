from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from ava.storage import private_ava_storage
from core.mixins import TenantModel


def arquivo_frequencia_path(instance, filename):
    from pathlib import Path
    from uuid import uuid4
    return f"ava/frequencias/{instance.cliente_id}/{uuid4().hex}{Path(filename).suffix.lower()}"


class RepasseFrequencia(TenantModel):
    curso = models.ForeignKey('ava.Curso', on_delete=models.PROTECT, related_name='repasses_frequencia')
    data_encontro = models.DateField('Data do encontro')
    descricao = models.CharField('Atividade', max_length=255)
    arquivo = models.FileField('Frequência física', upload_to=arquivo_frequencia_path, storage=private_ava_storage, validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])])
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Repasse de frequência presencial'
        verbose_name_plural = 'Repasses de frequência presencial'
        ordering = ['-data_encontro', '-id']

    def clean(self):
        super().clean()
        if self.curso_id and self.cliente_id and self.curso.cliente_id != self.cliente_id:
            raise ValidationError({'curso': 'O curso deve pertencer ao mesmo município.'})
        if self.arquivo and self.arquivo.size > 10 * 1024 * 1024:
            raise ValidationError({'arquivo': 'O arquivo deve ter no máximo 10 MB.'})

    def __str__(self):
        return f'{self.curso} — {self.descricao} ({self.data_encontro:%d/%m/%Y})'


class RegistroSeminario(TenantModel):
    class Tipo(models.TextChoices):
        SEMINARIO = 'seminario', 'Seminário'
        PRATICA = 'pratica', 'Prática dirigida'
        VISITA = 'visita', 'Visita'

    matricula = models.ForeignKey('ava.MatriculaCurso', on_delete=models.PROTECT, related_name='registros_seminario')
    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices)
    atividade = models.CharField('Atividade', max_length=255)
    data_realizacao = models.DateField('Data de realização')
    nota = models.DecimalField('Nota atribuída', max_digits=6, decimal_places=2)
    observacoes = models.TextField('Observações', blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Seminário ou prática dirigida'
        verbose_name_plural = 'Seminários e práticas dirigidas'
        ordering = ['-data_realizacao', '-id']

    def clean(self):
        super().clean()
        if self.matricula_id and self.cliente_id and self.matricula.cliente_id != self.cliente_id:
            raise ValidationError({'matricula': 'A matrícula deve pertencer ao mesmo município.'})
        if self.nota is not None and self.nota < 0:
            raise ValidationError({'nota': 'A nota não pode ser negativa.'})

    def __str__(self):
        return f'{self.matricula} — {self.atividade}'
