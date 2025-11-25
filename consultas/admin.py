from django.contrib import admin

from .models import ConsultaPublica, ManifestacaoPublica


@admin.register(ConsultaPublica)
class ConsultaPublicaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "cliente", "data_publicacao", "data_fechamento", "ativa")
    list_filter = ("cliente", "ativa")
    search_fields = ("titulo", "slug", "token_acesso")
    readonly_fields = ("token_acesso", "created_at", "updated_at")


@admin.register(ManifestacaoPublica)
class ManifestacaoPublicaAdmin(admin.ModelAdmin):
    list_display = ("consulta", "pagina", "nome_completo", "cidade", "estado", "created_at")
    list_filter = ("estado", "consulta")
    search_fields = ("nome_completo", "cpf", "comentario")
    readonly_fields = ("created_at", "updated_at", "ip_address", "user_agent")
