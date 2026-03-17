from django.contrib import admin

from core.admin_mixins import ClienteScopedAdminMixin
from .models import MebMessage, MebThread


@admin.register(MebThread)
class MebThreadAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "cliente", "usuario", "updated_at")
    search_fields = ("usuario__email", "usuario__nome")
    list_filter = ("cliente",)


@admin.register(MebMessage)
class MebMessageAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "thread", "origem", "autor", "created_at")
    list_filter = ("origem", "cliente")
    search_fields = ("conteudo", "autor__email", "autor__nome")
