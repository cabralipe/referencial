from django.contrib import admin

from .models import MebMessage, MebThread


@admin.register(MebThread)
class MebThreadAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "usuario", "updated_at")
    search_fields = ("usuario__email", "usuario__nome")
    list_filter = ("cliente",)


@admin.register(MebMessage)
class MebMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "thread", "origem", "autor", "created_at")
    list_filter = ("origem", "cliente")
    search_fields = ("conteudo", "autor__email", "autor__nome")
