from django.db import models
from core.mixins import TenantModel
from .module import CursoModulo


class PosicaoImagem(models.TextChoices):
    ACIMA = "acima", "Acima do texto"
    ABAIXO = "abaixo", "Abaixo do texto"


class AlinhamentoImagem(models.TextChoices):
    ESQUERDA = "esquerda", "Esquerda"
    CENTRO = "centro", "Centro"
    DIREITA = "direita", "Direita"


class Aula(TenantModel):
    class Tipo(models.TextChoices):
        CONTEUDO = "conteudo", "Conteúdo Teórico"
        MISTA = "mista", "Teoria + Prática"
        AVALIATIVA = "avaliativa", "Avaliação/Quiz"

    modulo = models.ForeignKey(CursoModulo, on_delete=models.CASCADE, related_name="aulas")
    titulo = models.CharField("Título", max_length=255)
    resumo = models.TextField("Resumo", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    tipo = models.CharField("Tipo", max_length=20, choices=Tipo.choices, default=Tipo.CONTEUDO)
    duracao_estimada_minutos = models.PositiveIntegerField("Duração (Min)", default=0)
    is_obigatoria = models.BooleanField("Obrigatória?", default=True)
    is_active = models.BooleanField("Aula Publicada?", default=True)
    data_liberacao = models.DateTimeField("Data de liberação", null=True, blank=True)
    pre_requisito_aula = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="aulas_dependentes")

    imagem_display = models.ImageField(
        "Imagem de exibição",
        upload_to="ava/aulas/imagens/",
        null=True,
        blank=True,
        max_length=500,
    )
    imagem_posicao = models.CharField(
        "Posição da imagem",
        max_length=10,
        choices=PosicaoImagem.choices,
        default=PosicaoImagem.ACIMA,
    )
    imagem_largura_percent = models.PositiveIntegerField(
        "Largura da imagem (%)",
        default=100,
    )
    imagem_alinhamento = models.CharField(
        "Alinhamento da imagem",
        max_length=10,
        choices=AlinhamentoImagem.choices,
        default=AlinhamentoImagem.CENTRO,
    )

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"
        ordering = ["modulo", "ordem"]

    def __str__(self):
        return f"Aula {self.ordem}: {self.titulo}"

class ConteudoAula(TenantModel):
    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto Rico"
        VIDEO = "video", "Vídeo Incorporado"
        PDF = "pdf", "PDF/Apostila"
        ARQUIVO = "arquivo", "Arquivo para Download"
        LINK = "link", "Link Externo"
        APRESENTACAO = "apresentacao", "Apresentação Interativa"
        IMAGEM = "imagem", "Imagem"
        AUDIO = "audio", "Áudio/Podcast"
        EMBED = "embed", "Embed HTML Genérico"

    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name="conteudos")
    tipo = models.CharField("Tipo", max_length=30, choices=Tipo.choices)
    titulo = models.CharField("Título/Rótulo", max_length=255)
    descricao = models.TextField("Descrição Menor", blank=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    is_obrigatorio = models.BooleanField("Consumo Obrigatório?", default=True)

    # Dados de acordo com o tipo
    conteudo_texto = models.TextField("Texto Rico", blank=True)
    url = models.URLField("URL de Vídeo/Link/Embed", blank=True, max_length=1000)
    arquivo = models.FileField("Arquivo/PDF/Mídia", upload_to="ava/aulas/arquivos/", null=True, blank=True, max_length=500)
    embed_code = models.TextField("Código de Embed (Iframe, etc)", blank=True)

    imagem_display = models.ImageField(
        "Imagem de exibição",
        upload_to="ava/aulas/imagens/",
        null=True,
        blank=True,
        max_length=500,
    )
    imagem_posicao = models.CharField(
        "Posição da imagem",
        max_length=10,
        choices=PosicaoImagem.choices,
        default=PosicaoImagem.ACIMA,
    )
    imagem_largura_percent = models.PositiveIntegerField(
        "Largura da imagem (%)",
        default=100,
    )
    imagem_alinhamento = models.CharField(
        "Alinhamento da imagem",
        max_length=10,
        choices=AlinhamentoImagem.choices,
        default=AlinhamentoImagem.CENTRO,
    )

    class Meta:
        verbose_name = "Conteúdo de Aula"
        verbose_name_plural = "Conteúdos de Aula"
        ordering = ["aula", "ordem"]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"
