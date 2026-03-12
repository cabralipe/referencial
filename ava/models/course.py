from django.db import models
from django.conf import settings
from core.mixins import TenantModel

class TrilhaFormativa(TenantModel):
    nome = models.CharField("Nome", max_length=255)
    descricao = models.TextField("Descrição", blank=True)
    capa = models.ImageField("Capa", upload_to="ava/trilhas/capas/", null=True, blank=True)
    ordem_exibicao = models.PositiveIntegerField("Ordem de exibição", default=0)
    is_active = models.BooleanField("Ativo", default=True)
    carga_horaria_total = models.PositiveIntegerField("Carga horária total", default=0, help_text="Calculada automaticamente ou definida manualmente.")

    class Meta:
        verbose_name = "Trilha Formativa"
        verbose_name_plural = "Trilhas Formativas"
        ordering = ["ordem_exibicao", "nome"]

    def __str__(self):
        return self.nome

class CursoCategoria(TenantModel):
    nome = models.CharField("Nome", max_length=150)
    descricao = models.TextField("Descrição", blank=True)

    class Meta:
        verbose_name = "Categoria de Curso"
        verbose_name_plural = "Categorias de Curso"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

class Curso(TenantModel):
    cliente = models.ForeignKey(
        "core.Cliente",
        on_delete=models.PROTECT,
        related_name="ava_cursos",
    )

    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        PUBLICADO = "publicado", "Publicado"
        ARQUIVADO = "arquivado", "Arquivado"

    titulo = models.CharField("Título", max_length=255)
    slug = models.SlugField("Slug", max_length=255, unique=True)
    descricao_curta = models.CharField("Descrição curta", max_length=255, blank=True)
    descricao_longa = models.TextField("Descrição longa", blank=True)
    capa = models.ImageField("Capa", upload_to="ava/cursos/capas/", null=True, blank=True)
    
    categoria = models.ForeignKey(CursoCategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="cursos")
    trilhas = models.ManyToManyField(TrilhaFormativa, related_name="cursos", blank=True)

    carga_horaria = models.PositiveIntegerField("Carga Horária", default=0)
    nivel = models.CharField("Nível", max_length=100, blank=True)
    publico_alvo = models.CharField("Público-alvo", max_length=255, blank=True)
    ementa = models.TextField("Ementa", blank=True)
    objetivos = models.TextField("Objetivos", blank=True)

    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.RASCUNHO)
    is_aberto = models.BooleanField("Curso aberto (Inscrição livre)?", default=False)
    
    permite_certificado = models.BooleanField("Permite certificado?", default=True)
    nota_minima = models.DecimalField("Nota mínima para aprovação", max_digits=5, decimal_places=2, default=70.00)
    progresso_minimo = models.PositiveIntegerField("Progresso mínimo (%)", default=100, help_text="Percentual mínimo de conclusão exigido.")

    autor_principal = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="cursos_criados", verbose_name="Autor/Responsável")
    data_inicio_disponibilidade = models.DateTimeField("Início da disponibilidade", null=True, blank=True)
    data_fim_disponibilidade = models.DateTimeField("Fim da disponibilidade", null=True, blank=True)
    ordem_na_trilha = models.PositiveIntegerField("Ordem dentro da trilha principal", default=0)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["cliente", "status", "is_aberto"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.titulo
