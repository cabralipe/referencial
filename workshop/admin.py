"""Admin para quadros."""

from django.contrib import admin

from .models import CelulaQuadro, Quadro


class CelulaQuadroInline(admin.TabularInline):
    model = CelulaQuadro
    extra = 0


@admin.register(Quadro)
class QuadroAdmin(admin.ModelAdmin):
    list_display = ("gt", "template", "version", "updated_at")
    list_filter = ("template", "gt")
    inlines = [CelulaQuadroInline]


@admin.register(CelulaQuadro)
class CelulaQuadroAdmin(admin.ModelAdmin):
    list_display = ("quadro", "linha", "coluna", "valor_html")
    list_filter = ("quadro",)
