"""Admin para exportações."""

from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from .models import ExportJob


@admin.register(ExportJob)
class ExportJobAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("cliente", "alvo_tipo", "alvo_id", "formato", "status", "created_at")
    list_filter = ("status", "formato", "alvo_tipo")
    search_fields = ("alvo_id",)
    readonly_fields = ("created_at", "finished_at")
