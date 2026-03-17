from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("usuario", "tipo", "lida", "created_at")
    list_filter = ("tipo", "lida")
    search_fields = ("tipo", "payload_json")
