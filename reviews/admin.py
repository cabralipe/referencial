from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from .models import Revisao


@admin.register(Revisao)
class RevisaoAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("alvo_tipo", "alvo_id", "status", "revisor", "solicitante", "updated_at")
    list_filter = ("alvo_tipo", "status", "revisor")
    search_fields = ("alvo_id", "parecer_html")
