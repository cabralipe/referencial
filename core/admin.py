"""Configurações do Django Admin para entidades centrais."""

from django.contrib import admin

from .models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Usuario


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativo", "created_at")
    list_filter = ("ativo",)
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(ClienteConfig)
class ClienteConfigAdmin(admin.ModelAdmin):
    list_display = ("cliente", "chave", "valor_texto", "updated_at")
    search_fields = ("cliente__nome", "chave")
    list_filter = ("cliente",)


@admin.register(ClienteFeatureFlag)
class ClienteFeatureFlagAdmin(admin.ModelAdmin):
    list_display = ("cliente", "flag", "ativo")
    list_filter = ("cliente", "ativo")
    search_fields = ("flag",)


@admin.register(ClienteTema)
class ClienteTemaAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "logo_url",
        "cor_primaria",
        "cor_secundaria",
        "updated_at",
    )
    list_filter = ("cliente",)
    search_fields = ("cliente__nome",)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("email", "nome", "cliente", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "cliente")
    search_fields = ("email", "nome")
    ordering = ("email",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("cliente", "entidade", "entidade_id", "acao", "timestamp")
    search_fields = ("entidade", "entidade_id", "acao")
    list_filter = ("cliente", "acao")
    readonly_fields = ("diff_json", "timestamp")

    def has_add_permission(self, request):  # pragma: no cover - admin safety
        return False
