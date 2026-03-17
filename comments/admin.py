from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from .models import Comentario


@admin.register(Comentario)
class ComentarioAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("alvo_tipo", "alvo_id", "autor", "resolvido", "updated_at")
    list_filter = ("alvo_tipo", "resolvido")
    search_fields = ("alvo_id", "conteudo_html")
    filter_horizontal = ("mentions",)
