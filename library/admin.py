from django.contrib import admin

from .models import BlocoTexto, Midia


@admin.register(Midia)
class MidiaAdmin(admin.ModelAdmin):
    list_display = ("url", "uploaded_by", "created_at")
    search_fields = ("url", "legenda")
    list_filter = ("uploaded_by",)


@admin.register(BlocoTexto)
class BlocoTextoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "created_by", "updated_at")
    search_fields = ("titulo", "conteudo_html")
    list_filter = ("created_by",)
