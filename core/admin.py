"""Configurações do Django Admin para entidades centrais."""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Usuario
from .forms import UsuarioCreationForm, UsuarioChangeForm, ClienteTemaAdminForm
from meb.services import deliver_admin_broadcast


class BroadcastMessageForm(ActionForm):
    conteudo = forms.CharField(
        label="Mensagem para o chat",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Digite a mensagem do disparo..."}),
    )


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
    form = ClienteTemaAdminForm
    list_display = (
        "cliente",
        "logo_url",
        "meb_avatar_url",
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
    action_form = BroadcastMessageForm
    actions = ["broadcast_chat_message"]

    @admin.action(description="Disparar mensagem no chat para os usuários selecionados")
    def broadcast_chat_message(self, request, queryset):
        user_role = getattr(request.user, "role", None)
        if user_role not in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}:
            self.message_user(
                request,
                "Apenas administradores podem enviar disparos de mensagens.",
                level=messages.ERROR,
            )
            return

        conteudo = (request.POST.get("conteudo") or "").strip()
        if not conteudo:
            self.message_user(
                request,
                "Digite a mensagem antes de enviar o disparo.",
                level=messages.ERROR,
            )
            return

        total_enviados = 0
        skipped = 0
        usuarios_by_cliente: dict[int, list[int]] = {}
        for usuario in queryset:
            if not usuario.cliente_id:
                skipped += 1
                continue
            usuarios_by_cliente.setdefault(usuario.cliente_id, []).append(usuario.id)

        for cliente_id, usuario_ids in usuarios_by_cliente.items():
            enviados = deliver_admin_broadcast(
                cliente_id=cliente_id,
                autor=request.user,
                conteudo=conteudo,
                usuario_ids=usuario_ids,
                include_all=False,
            )
            total_enviados += enviados

        if total_enviados == 0:
            self.message_user(
                request,
                "Nenhum destinatário elegível encontrado para este disparo.",
                level=messages.WARNING,
            )
            return

        msg = f"Disparo enviado para {total_enviados} destinatário(s)."
        if skipped:
            msg += f" {skipped} usuário(s) sem cliente foram ignorados."
        self.message_user(request, msg, level=messages.SUCCESS)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("cliente", "entidade", "entidade_id", "acao", "timestamp")
    search_fields = ("entidade", "entidade_id", "acao")
    list_filter = ("cliente", "acao")
    readonly_fields = ("diff_json", "timestamp")

    def has_add_permission(self, request):  # pragma: no cover - admin safety
        return False
