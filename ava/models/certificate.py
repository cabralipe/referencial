import uuid
from django.db import models
from django.conf import settings
from core.mixins import TenantModel
from .course import Curso, TrilhaFormativa
from .enrollment import MatriculaCurso, MatriculaTrilha

class ConfigCertificado(TenantModel):
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name="config_certificado", null=True, blank=True)
    trilha = models.OneToOneField(TrilhaFormativa, on_delete=models.CASCADE, related_name="config_certificado", null=True, blank=True)
    
    template_html = models.TextField("Template HTML", blank=True, help_text="Variáveis permitidas: {{aluno}}, {{curso}}, {{carga_horaria}}, {{data}}, etc.")
    carga_horaria_impressa = models.PositiveIntegerField("Carga Horária Impressa", default=0, help_text="0 para usar a carga horária original do curso/trilha")
    assinatura_digital_url = models.URLField("URL da Assinatura (Imagem)", blank=True)

    class Meta:
        verbose_name = "Configuração de Certificado"
        verbose_name_plural = "Configurações de Certificados"

    def __str__(self):
        if self.curso: return f"Certificado Curso: {self.curso.titulo}"
        if self.trilha: return f"Certificado Trilha: {self.trilha.nome}"
        return "Configuração Órfã"

class Certificado(TenantModel):
    # Pode ser de um Curso específico ou de uma Trilha inteira
    matricula_curso = models.OneToOneField(MatriculaCurso, on_delete=models.CASCADE, related_name="certificado_emitido", null=True, blank=True)
    matricula_trilha = models.OneToOneField(MatriculaTrilha, on_delete=models.CASCADE, related_name="certificado_emitido", null=True, blank=True)
    
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificados_ava")
    
    codigo_validacao = models.CharField("Código Validação Único", max_length=64, unique=True, blank=True)
    data_emissao = models.DateTimeField("Data de Emissão", auto_now_add=True)
    nota_final = models.DecimalField("Nota Final no certificado", max_digits=5, decimal_places=2, null=True, blank=True)
    carga_horaria = models.PositiveIntegerField("Carga Horária", default=0)

    # Cache do payload para imutabilidade caso o curso mude depois
    dados_impressos = models.JSONField("Dados Impressos (Snapshot)", default=dict, blank=True)
    arquivo_pdf = models.FileField("Arquivo PDF (Gerado)", upload_to="ava/certificados/pdfs/", null=True, blank=True)

    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"
        indexes = [
            models.Index(fields=["cliente", "codigo_validacao"]),
            models.Index(fields=["cliente", "aluno"]),
        ]

    def save(self, *args, **kwargs):
        if not self.codigo_validacao:
            self.codigo_validacao = uuid.uuid4().hex.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.matricula_curso: return f"Certificado: {self.aluno.username} - {self.matricula_curso.curso.titulo}"
        if self.matricula_trilha: return f"Certificado: {self.aluno.username} - {self.matricula_trilha.trilha.nome}"
        return f"Certificado {self.codigo_validacao}"
