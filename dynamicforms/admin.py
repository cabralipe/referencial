"""Admin para formulários dinâmicos."""

from django.contrib import admin

from .models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico


class CampoDinamicoInline(admin.TabularInline):
    model = CampoDinamico
    extra = 0


@admin.register(FormularioDinamico)
class FormularioDinamicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "ativo")
    list_filter = ("cliente", "ativo")
    search_fields = ("nome", "descricao")
    inlines = [CampoDinamicoInline]


@admin.register(CampoDinamico)
class CampoDinamicoAdmin(admin.ModelAdmin):
    list_display = ("formulario", "chave", "tipo", "ordem")
    list_filter = ("formulario", "tipo")


@admin.register(RespostaCampoDinamico)
class RespostaCampoDinamicoAdmin(admin.ModelAdmin):
    list_display = ("campo", "owner_type", "owner_id", "updated_at")
    list_filter = ("owner_type", "campo__formulario")
