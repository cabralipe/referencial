"""Admin do domínio de currículo."""

from django.contrib import admin

from .models import Anexo, GT, Pergunta, Resposta, Tarefa, TextoUnico


@admin.register(GT)
class GTAdmin(admin.ModelAdmin):
    list_display = ("nome", "etapa", "cliente", "created_at")
    search_fields = ("nome", "etapa", "cliente__nome")
    filter_horizontal = ("membros",)


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("ordem", "tipo", "status", "cliente")
    list_filter = ("cliente", "tipo", "status")
    search_fields = ("cliente__nome",)


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
    list_display = ("tarefa", "ordem", "obrigatoria", "permite_upload")
    list_filter = ("tarefa", "permite_upload", "obrigatoria")
    search_fields = ("texto",)


@admin.register(Resposta)
class RespostaAdmin(admin.ModelAdmin):
    list_display = ("gt", "pergunta", "autor", "version", "updated_at")
    list_filter = ("gt", "pergunta", "autor")
    search_fields = ("conteudo_html",)


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = ("resposta", "url", "ordem")
    list_filter = ("resposta",)


@admin.register(TextoUnico)
class TextoUnicoAdmin(admin.ModelAdmin):
    list_display = ("gt", "tarefa", "responsavel", "version", "updated_at")
    list_filter = ("gt", "tarefa")
