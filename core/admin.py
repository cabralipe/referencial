"""Configurações do Django Admin para entidades centrais."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Usuario
from .forms import UsuarioCreationForm, UsuarioChangeForm


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
class UsuarioAdmin(DjangoUserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario
    list_display = ("email", "nome", "cliente", "role", "is_active", "last_login")
    list_filter = ("role", "is_active", "cliente")
    search_fields = ("email", "nome")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("nome", "cliente", "role")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Datas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "nome",
                    "cliente",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("cliente", "entidade", "entidade_id", "acao", "timestamp")
    search_fields = ("entidade", "entidade_id", "acao")
    list_filter = ("cliente", "acao")
    readonly_fields = ("diff_json", "timestamp")

    def has_add_permission(self, request):  # pragma: no cover - admin safety
        return False
