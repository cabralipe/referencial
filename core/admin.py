"""Configuracoes do Django Admin para entidades centrais."""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from meb.services import deliver_admin_broadcast

from .admin_mixins import ClienteScopedAdminMixin
from .forms import ClienteTemaAdminForm, UsuarioChangeForm, UsuarioCreationForm
from .models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Eixo, TipoUsuarioCadastro, Usuario


class BroadcastMessageForm(ActionForm):
    conteudo = forms.CharField(
        label="Mensagem para o chat",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Digite a mensagem do disparo..."}),
    )


@admin.register(Cliente)
class ClienteAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    cliente_scope_lookup = "pk"
    list_display = ("nome", "slug", "ativo", "created_at")
    list_filter = ("ativo",)
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}


_CHAVE_CHOICES = [
    ("", "— Selecione uma chave —"),
    (
        "Personalização da tela de Criar Conta",
        [
            ("cadastro_titulo", "cadastro_titulo — Título principal do formulário"),
            ("cadastro_subtitulo", "cadastro_subtitulo — Subtítulo / descrição abaixo do título"),
            ("cadastro_label_tipo_usuario", "cadastro_label_tipo_usuario — Label do seletor de tipo de usuário"),
            ("cadastro_label_municipio", "cadastro_label_municipio — Label do campo de município"),
            ("cadastro_placeholder_municipio", "cadastro_placeholder_municipio — Placeholder do campo de município"),
            ("cadastro_label_escola", "cadastro_label_escola — Label do campo de escola"),
            ("cadastro_placeholder_escola", "cadastro_placeholder_escola — Placeholder do campo de escola"),
            ("cadastro_label_nome", "cadastro_label_nome — Label do campo nome completo"),
            ("cadastro_placeholder_nome", "cadastro_placeholder_nome — Placeholder do campo nome completo"),
            ("cadastro_label_email", "cadastro_label_email — Label do campo e-mail"),
            ("cadastro_placeholder_email", "cadastro_placeholder_email — Placeholder do campo e-mail"),
            ("cadastro_label_senha", "cadastro_label_senha — Label do campo senha"),
            ("cadastro_label_confirmar_senha", "cadastro_label_confirmar_senha — Label do campo confirmar senha"),
        ],
    ),
    (
        "Plugins e integrações",
        [
            ("synthesis_plugin", "synthesis_plugin — Plugin de síntese de respostas (ex: openai)"),
            ("export_plugin", "export_plugin — Plugin de exportação de dados (ex: default)"),
        ],
    ),
    (
        "Pontuação e trilhas",
        [
            ("score.config", "score.config — Configuração de pontuação (JSON)"),
            ("ppp.trilhas", "ppp.trilhas — Configuração de trilhas PPP (JSON)"),
        ],
    ),
]

_CHAVE_HELP = {
    "cadastro_titulo": "Texto exibido como título do formulário de cadastro.",
    "cadastro_subtitulo": "Texto exibido logo abaixo do título.",
    "cadastro_label_tipo_usuario": "Rótulo do seletor de tipo de usuário.",
    "cadastro_label_municipio": "Rótulo do campo de município.",
    "cadastro_placeholder_municipio": "Texto de exemplo dentro do campo de município.",
    "cadastro_label_escola": "Rótulo do campo de escola.",
    "cadastro_placeholder_escola": "Texto de exemplo dentro do campo de escola.",
    "cadastro_label_nome": "Rótulo do campo nome completo.",
    "cadastro_placeholder_nome": "Texto de exemplo dentro do campo nome.",
    "cadastro_label_email": "Rótulo do campo e-mail.",
    "cadastro_placeholder_email": "Texto de exemplo dentro do campo e-mail.",
    "cadastro_label_senha": "Rótulo do campo senha.",
    "cadastro_label_confirmar_senha": "Rótulo do campo confirmar senha.",
    "synthesis_plugin": 'Identificador do provedor de síntese. Exemplo: "openai".',
    "export_plugin": 'Identificador do provedor de exportação. Exemplo: "default".',
    "score.config": "JSON com as configurações de pontuação do cliente.",
    "ppp.trilhas": "JSON com a configuração de trilhas do PPP.",
}


class ClienteConfigAdminForm(forms.ModelForm):
    chave = forms.ChoiceField(
        choices=_CHAVE_CHOICES,
        label="Chave",
        help_text="Selecione a configuração que deseja definir para este cliente.",
    )

    class Meta:
        model = ClienteConfig
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance and instance.chave:
            existing_values = [v for group in _CHAVE_CHOICES[1:] for v, _ in group[1]]
            if instance.chave not in existing_values:
                self.fields["chave"] = forms.CharField(
                    initial=instance.chave,
                    label="Chave",
                    help_text="Chave personalizada (não está na lista padrão).",
                )
            else:
                self.fields["chave"].initial = instance.chave
            valor_help = _CHAVE_HELP.get(instance.chave, "")
            if valor_help:
                self.fields["valor_texto"].help_text = valor_help


@admin.register(ClienteConfig)
class ClienteConfigAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    form = ClienteConfigAdminForm
    list_display = ("cliente", "chave", "valor_texto", "updated_at")
    search_fields = ("cliente__nome", "chave")
    list_filter = ("cliente",)


@admin.register(ClienteFeatureFlag)
class ClienteFeatureFlagAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("cliente", "flag", "ativo")
    list_filter = ("cliente", "ativo")
    search_fields = ("flag",)


@admin.register(ClienteTema)
class ClienteTemaAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
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


@admin.register(Eixo)
class EixoAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("nome", "cliente", "ativo", "ordem_exibicao")
    list_filter = ("cliente", "ativo")
    search_fields = ("nome", "descricao")
    ordering = ("cliente", "ordem_exibicao", "nome")

    def _has_admin_access(self, request) -> bool:
        if not getattr(request.user, "is_active", False) or not getattr(request.user, "is_staff", False):
            return False
        return getattr(request.user, "role", None) in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}

    def has_module_permission(self, request):
        return self._has_admin_access(request)

    def has_view_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)

    def has_add_permission(self, request):
        return self._has_admin_access(request)

    def has_change_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)


class TipoUsuarioCadastroAdminForm(forms.ModelForm):
    class Meta:
        model = TipoUsuarioCadastro
        fields = "__all__"
        widgets = {"role_interno": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role_interno"].initial = Usuario.Role.DIRETOR

    def clean_role_interno(self):
        return Usuario.Role.DIRETOR


@admin.register(TipoUsuarioCadastro)
class TipoUsuarioCadastroAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    form = TipoUsuarioCadastroAdminForm
    list_display = (
        "nome",
        "cliente",
        "role_interno",
        "seguimento",
        "acesso_ppp",
        "exibir_no_cadastro",
        "ativo",
        "ordem_exibicao",
    )
    list_filter = ("role_interno", "acesso_ppp", "exibir_no_cadastro", "ativo", "cliente")
    search_fields = ("nome", "slug")
    ordering = ("cliente", "ordem_exibicao", "nome")
    prepopulated_fields = {"slug": ("nome",)}
    exclude = ("seguimento",)

    def _has_admin_access(self, request) -> bool:
        if not getattr(request.user, "is_active", False) or not getattr(request.user, "is_staff", False):
            return False
        return getattr(request.user, "role", None) in {Usuario.Role.ADMIN_CLIENTE, Usuario.Role.SUPER_ADMIN}

    def has_module_permission(self, request):
        return self._has_admin_access(request)

    def has_view_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)

    def has_add_permission(self, request):
        return self._has_admin_access(request)

    def has_change_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._has_admin_access(request) and self._belongs_to_cliente(request, obj)


@admin.register(Usuario)
class UsuarioAdmin(ClienteScopedAdminMixin, DjangoUserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    model = Usuario
    list_display = (
        "email",
        "nome",
        "cliente",
        "clientes_resumo",
        "escola",
        "tipo_cadastro",
        "role",
        "seguimento",
        "is_active",
        "last_login",
    )
    list_filter = ("role", "tipo_cadastro", "seguimento", "is_active", "cliente", "escola")
    search_fields = ("email", "nome")
    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")
    filter_horizontal = ("clientes", "eixos", "groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informacoes pessoais", {"fields": ("nome", "cliente", "clientes", "escola", "tipo_cadastro", "role", "seguimento", "eixos")}),
        (
            "Permissoes",
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
                    "clientes",
                    "escola",
                    "tipo_cadastro",
                    "role",
                    "seguimento",
                    "eixos",
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

    def clientes_resumo(self, obj):
        clientes = list(obj.clientes.values_list("nome", flat=True)[:3])
        if obj.cliente and obj.cliente.nome not in clientes:
            clientes.insert(0, obj.cliente.nome)
        if not clientes:
            return "-"
        if obj.clientes.count() > 3:
            return f"{', '.join(clientes)}..."
        return ", ".join(clientes)

    clientes_resumo.short_description = "Clientes permitidos"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "escola":
            from curriculum.models import Escola

            if getattr(request.user, "role", None) == Usuario.Role.SUPER_ADMIN:
                kwargs["queryset"] = Escola.raw_objects.filter(is_deleted=False)
            else:
                kwargs["queryset"] = Escola.objects.filter(cliente_id=getattr(request, "cliente_id", None))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description="Disparar mensagem no chat para os usuarios selecionados")
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
        scope_cliente_id = getattr(request, "cliente_id", None)
        for usuario in queryset:
            target_cliente_id = None
            if scope_cliente_id and usuario.can_access_cliente(scope_cliente_id):
                target_cliente_id = scope_cliente_id
            if not target_cliente_id:
                target_cliente_id = usuario.get_default_cliente_id()
            if not target_cliente_id:
                skipped += 1
                continue
            usuarios_by_cliente.setdefault(target_cliente_id, []).append(usuario.id)

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
                "Nenhum destinatario elegivel encontrado para este disparo.",
                level=messages.WARNING,
            )
            return

        msg = f"Disparo enviado para {total_enviados} destinatario(s)."
        if skipped:
            msg += f" {skipped} usuario(s) sem cliente foram ignorados."
        self.message_user(request, msg, level=messages.SUCCESS)


@admin.register(AuditLog)
class AuditLogAdmin(ClienteScopedAdminMixin, admin.ModelAdmin):
    list_display = ("cliente", "entidade", "entidade_id", "acao", "timestamp")
    search_fields = ("entidade", "entidade_id", "acao")
    list_filter = ("cliente", "acao")
    readonly_fields = ("diff_json", "timestamp")

    def has_add_permission(self, request):  # pragma: no cover - admin safety
        return False
