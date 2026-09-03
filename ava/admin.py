import json
import logging
import zipfile
from tempfile import SpooledTemporaryFile

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify

from ava.forms import CursoEstruturaCopyForm
from ava.models.certificate import CERTIFICATE_VARIABLES, DEFAULT_CERTIFICATE_VARIABLES
from ava.services import CourseCloneService
from ava.services.certificate_service import CertificacaoService
from ava.services.course_copy_service import CourseCopyOptions
from core.models import Eixo, TipoUsuarioCadastro, Usuario
from curriculum.models import Escola, GT
from tasks.certificates import build_certificate_pdf

from .models import (
    AssinaturaCertificado,
    Atividade,
    AtividadeForumAnexo,
    AtividadeForumMensagem,
    AtividadeTentativa,
    AtividadeTentativaArquivo,
    Aula,
    Certificado,
    ConfigCertificado,
    ConteudoAula,
    Curso,
    CursoCategoria,
    CursoModulo,
    MatriculaCurso,
    MatriculaTrilha,
    QuizAlternativa,
    QuizQuestao,
    TrilhaFormativa,
)


logger = logging.getLogger(__name__)


ADMIN_ROLES = {"admin_cliente", "super_admin"}

EIXO_RESTRICAO_ROLE_CHOICES = (
    (Usuario.Role.DIRETOR, "Diretor"),
    (Usuario.Role.COORDENADOR_PEDAGOGICO, "Coordenador Pedagógico"),
    (Usuario.Role.PROFESSOR, "Professor"),
    (Usuario.Role.ARTICULADOR, "Redator"),
    (Usuario.Role.REVISOR, "Revisor"),
    (Usuario.Role.MEMBRO_GT, "Membro GT"),
    (Usuario.Role.LEITOR, "Leitor"),
)


def _model_has_cliente(model) -> bool:
    return any(field.attname == "cliente_id" for field in model._meta.fields)


def _model_has_soft_delete(model) -> bool:
    return any(field.attname == "is_deleted" for field in model._meta.fields)


class AVAAdminPermissionMixin:
    def _is_admin_role(self, request) -> bool:
        return (
            bool(getattr(request.user, "is_active", False))
            and bool(getattr(request.user, "is_staff", False))
            and getattr(request.user, "role", None) in ADMIN_ROLES
        )

    def _is_super_admin(self, request) -> bool:
        return bool(getattr(request.user, "is_superuser", False)) or getattr(request.user, "role", None) == "super_admin"

    def _same_cliente(self, request, obj) -> bool:
        if obj is None or not hasattr(obj, "cliente_id"):
            return True
        return self._is_super_admin(request) or obj.cliente_id == getattr(request.user, "cliente_id", None)

    def has_module_permission(self, request):
        return self._is_admin_role(request)

    def has_view_permission(self, request, obj=None):
        return self._is_admin_role(request) and self._same_cliente(request, obj)

    def has_add_permission(self, request):
        return self._is_admin_role(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin_role(request) and self._same_cliente(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._is_admin_role(request) and self._same_cliente(request, obj)


class AVAInlinePermissionMixin:
    def _is_admin_role(self, request) -> bool:
        return (
            bool(getattr(request.user, "is_active", False))
            and bool(getattr(request.user, "is_staff", False))
            and getattr(request.user, "role", None) in ADMIN_ROLES
        )

    def _is_super_admin(self, request) -> bool:
        return bool(getattr(request.user, "is_superuser", False)) or getattr(request.user, "role", None) == "super_admin"

    def has_view_permission(self, request, obj=None):
        return self._is_admin_role(request)

    def has_add_permission(self, request, obj):
        return self._is_admin_role(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin_role(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_admin_role(request)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        related_model = getattr(db_field.remote_field, "model", None)
        if (
            not self._is_super_admin(request)
            and related_model is not None
            and hasattr(related_model, "_meta")
            and _model_has_cliente(related_model)
        ):
            manager = getattr(related_model, "raw_objects", related_model._default_manager)
            related_qs = manager.filter(cliente_id=request.user.cliente_id)
            if _model_has_soft_delete(related_model):
                related_qs = related_qs.filter(is_deleted=False)
            kwargs["queryset"] = related_qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class AVAModelAdmin(AVAAdminPermissionMixin, admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self._is_super_admin(request) or not _model_has_cliente(self.model):
            return qs
        return qs.filter(cliente_id=request.user.cliente_id)

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not self._is_super_admin(request) and _model_has_cliente(self.model) and "cliente" not in exclude:
            exclude.append("cliente")
        return exclude

    def save_model(self, request, obj, form, change):
        if not self._is_super_admin(request) and hasattr(obj, "cliente_id") and not obj.cliente_id:
            obj.cliente_id = request.user.cliente_id
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        related_model = getattr(db_field.remote_field, "model", None)
        if not self._is_super_admin(request) and related_model is not None:
            if db_field.name == "cliente":
                kwargs["queryset"] = related_model.objects.filter(pk=request.user.cliente_id)
            elif hasattr(related_model, "_meta") and _model_has_cliente(related_model):
                manager = getattr(related_model, "raw_objects", related_model._default_manager)
                related_qs = manager.filter(cliente_id=request.user.cliente_id)
                if _model_has_soft_delete(related_model):
                    related_qs = related_qs.filter(is_deleted=False)
                kwargs["queryset"] = related_qs
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        related_model = getattr(db_field.remote_field, "model", None)
        if (
            not self._is_super_admin(request)
            and related_model is not None
            and hasattr(related_model, "_meta")
            and _model_has_cliente(related_model)
        ):
            manager = getattr(related_model, "raw_objects", related_model._default_manager)
            related_qs = manager.filter(cliente_id=request.user.cliente_id)
            if _model_has_soft_delete(related_model):
                related_qs = related_qs.filter(is_deleted=False)
            kwargs["queryset"] = related_qs
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class AVATabularInline(AVAInlinePermissionMixin, admin.TabularInline):
    extra = 0


class AVAStackedInline(AVAInlinePermissionMixin, admin.StackedInline):
    extra = 0


class AulaInline(AVATabularInline):
    model = Aula
    extra = 1


class ConteudoAulaInline(AVATabularInline):
    model = ConteudoAula
    extra = 1


class AtividadeInline(AVAStackedInline):
    model = Atividade


class QuizAlternativaInline(AVATabularInline):
    model = QuizAlternativa
    extra = 2
    fields = ("ordem", "texto", "is_correta", "feedback_especifico")
    exclude = ("cliente",)


class QuizQuestaoAdminForm(forms.ModelForm):
    class Meta:
        model = QuizQuestao
        fields = "__all__"

    def clean_atividade(self):
        atividade = self.cleaned_data.get("atividade")
        if atividade and atividade.tipo not in [Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO]:
            raise forms.ValidationError(
                "A questão de quiz só pode ser vinculada a atividades do tipo Quiz ou Questionário."
            )
        return atividade


class CursoAdminForm(forms.ModelForm):
    eixos_restricao_roles = forms.MultipleChoiceField(
        label="Perfis afetados pela restricao de eixos",
        choices=EIXO_RESTRICAO_ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Se nenhum perfil for marcado, a restricao por eixo vale para todos os perfis nao administradores.",
    )

    class Meta:
        model = Curso
        fields = "__all__"

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if not slug:
            return slug

        existing = Curso.raw_objects.filter(slug=slug)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("Já existe um curso com este slug. Informe um slug diferente.")
        return slug


    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get("cliente") or getattr(self.instance, "cliente", None)
        eixos = cleaned_data.get("eixos")
        if cliente and eixos is not None:
            invalidos = eixos.exclude(cliente=cliente)
            if invalidos.exists():
                raise forms.ValidationError("Todos os eixos selecionados devem pertencer ao mesmo cliente do curso.")
        return cleaned_data


class CursoModuloAdminForm(forms.ModelForm):
    eixos_restricao_roles = forms.MultipleChoiceField(
        label="Perfis afetados pela restricao de eixos",
        choices=EIXO_RESTRICAO_ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Se nenhum perfil for marcado, a restricao por eixo vale para todos os perfis nao administradores.",
    )

    class Meta:
        model = CursoModulo
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso") or getattr(self.instance, "curso", None)
        eixos = cleaned_data.get("eixos")
        if curso and eixos is not None:
            invalidos = eixos.exclude(cliente_id=curso.cliente_id)
            if invalidos.exists():
                raise forms.ValidationError("Todos os eixos selecionados devem pertencer ao mesmo cliente do curso.")
        return cleaned_data


class AtividadeAdminForm(forms.ModelForm):
    eixos_restricao_roles = forms.MultipleChoiceField(
        label="Perfis afetados pela restricao de eixos",
        choices=EIXO_RESTRICAO_ROLE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Se nenhum perfil for marcado, a restricao por eixo vale para todos os perfis nao administradores.",
    )

    class Meta:
        model = Atividade
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        aula = cleaned_data.get("aula") or getattr(self.instance, "aula", None)
        eixos = cleaned_data.get("eixos")
        if aula and eixos is not None:
            invalidos = eixos.exclude(cliente_id=aula.modulo.cliente_id)
            if invalidos.exists():
                raise forms.ValidationError("Todos os eixos selecionados devem pertencer ao mesmo cliente da aula.")
        return cleaned_data


AtividadeInline.form = AtividadeAdminForm
AtividadeInline.filter_horizontal = ("eixos",)


class ConfigCertificadoAdminForm(forms.ModelForm):
    campos_variaveis = forms.MultipleChoiceField(
        label="Campos que entram no certificado",
        choices=CERTIFICATE_VARIABLES,
        required=False,
        initial=DEFAULT_CERTIFICATE_VARIABLES,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ConfigCertificado
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        variaveis_json = json.dumps(list(CERTIFICATE_VARIABLES), ensure_ascii=False)
        for field_name in ("titulo", "subtitulo", "template_html", "verso_titulo", "verso_template_html"):
            field = self.fields.get(field_name)
            if field:
                field.widget.attrs["data-certificate-variable-picker"] = "1"
                field.widget.attrs["data-certificate-variables"] = variaveis_json
        if self.instance and self.instance.pk:
            self.fields["campos_variaveis"].initial = self.instance.campos_variaveis or DEFAULT_CERTIFICATE_VARIABLES

    class Media:
        css = {"all": ("ava/admin/certificate_variables.css",)}
        js = ("ava/admin/certificate_variables.js",)

    def clean_campos_variaveis(self):
        return list(self.cleaned_data.get("campos_variaveis") or DEFAULT_CERTIFICATE_VARIABLES)

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso")
        trilha = cleaned_data.get("trilha")
        if not curso and not trilha:
            raise forms.ValidationError("Informe um curso ou uma trilha para a configuração do certificado.")
        if curso and trilha:
            raise forms.ValidationError("Use uma configuração separada para curso e trilha.")
        return cleaned_data


class CertificadoBatchEmitForm(forms.Form):
    config = forms.ModelChoiceField(
        label="Modelo/configuração",
        queryset=ConfigCertificado.objects.none(),
        required=True,
    )
    curso = forms.ModelChoiceField(
        label="Curso",
        queryset=Curso.objects.none(),
        required=False,
        help_text="Opcional quando o modelo já estiver vinculado a um curso.",
    )
    aluno = forms.ModelChoiceField(
        label="Cursista individual",
        queryset=Usuario.objects.none(),
        required=False,
    )
    eixos = forms.ModelMultipleChoiceField(
        label="Eixo",
        queryset=Eixo.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Filtra por eixo do curso ou eixo vinculado ao usuário.",
    )
    escola = forms.ModelChoiceField(label="Escola", queryset=Escola.objects.none(), required=False)
    gt = forms.ModelChoiceField(label="GT", queryset=GT.objects.none(), required=False)
    tipos_usuario = forms.MultipleChoiceField(
        label="Tipos de usuários",
        choices=Usuario.Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    tipo_cadastro = forms.ModelChoiceField(
        label="Tipo de cadastro",
        queryset=TipoUsuarioCadastro.objects.none(),
        required=False,
    )
    campos_variaveis = forms.MultipleChoiceField(
        label="Campos impressos neste lote",
        choices=CERTIFICATE_VARIABLES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    liberar_agora = forms.BooleanField(label="Liberar no AVA agora", required=False, initial=True)
    liberar_em = forms.DateTimeField(
        label="Programar liberação para",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Use este campo quando não marcar liberação imediata.",
    )
    aprovar_pendentes = forms.BooleanField(
        label="Emitir também para cursistas sem conclusão",
        required=False,
        help_text="A tela de confirmação mostra quem ainda não concluiu antes de emitir.",
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        cliente_id = None if getattr(request.user, "role", None) == Usuario.Role.SUPER_ADMIN else request.user.cliente_id
        configs = ConfigCertificado.objects.select_related("curso", "trilha").order_by("curso__titulo", "trilha__nome", "id")
        cursos = Curso.objects.order_by("titulo")
        usuarios = Usuario.objects.order_by("nome", "email")
        eixos = Eixo.objects.order_by("ordem_exibicao", "nome")
        escolas = Escola.objects.order_by("nome")
        gts = GT.objects.order_by("nome")
        tipos = TipoUsuarioCadastro.objects.order_by("nome")
        if cliente_id:
            configs = configs.filter(cliente_id=cliente_id)
            cursos = cursos.filter(cliente_id=cliente_id)
            usuarios = usuarios.filter(cliente_id=cliente_id)
            eixos = eixos.filter(cliente_id=cliente_id)
            escolas = escolas.filter(cliente_id=cliente_id)
            gts = gts.filter(cliente_id=cliente_id)
            tipos = tipos.filter(cliente_id=cliente_id)

        self.fields["config"].queryset = configs
        self.fields["curso"].queryset = cursos
        self.fields["aluno"].queryset = usuarios
        self.fields["eixos"].queryset = eixos
        self.fields["escola"].queryset = escolas
        self.fields["gt"].queryset = gts
        self.fields["tipo_cadastro"].queryset = tipos

        config_id = self.data.get("config") if self.is_bound else None
        config = configs.filter(pk=config_id).first() if config_id else None
        self.fields["campos_variaveis"].initial = (
            config.campos_variaveis if config and config.campos_variaveis else DEFAULT_CERTIFICATE_VARIABLES
        )

    def clean(self):
        cleaned_data = super().clean()
        config = cleaned_data.get("config")
        curso = cleaned_data.get("curso")
        if config and config.curso_id:
            cleaned_data["curso"] = config.curso
        elif not curso:
            raise forms.ValidationError("Selecione um curso ou uma configuração vinculada a curso.")

        if not cleaned_data.get("liberar_agora") and not cleaned_data.get("liberar_em"):
            raise forms.ValidationError("Informe uma data para programar a liberação ou marque liberar agora.")
        return cleaned_data


class AssinaturaCertificadoInline(AVATabularInline):
    model = AssinaturaCertificado
    extra = 0
    fields = ("ordem", "titulo", "cargo", "imagem", "x", "y", "largura")
    exclude = ("cliente",)


@admin.register(TrilhaFormativa)
class TrilhaFormativaAdmin(AVAModelAdmin):
    list_display = ("nome", "cliente", "is_active", "ordem_exibicao")
    list_filter = ("cliente", "is_active")
    search_fields = ("nome", "descricao")


@admin.register(CursoCategoria)
class CursoCategoriaAdmin(AVAModelAdmin):
    list_display = ("nome", "cliente")
    search_fields = ("nome", "descricao")


@admin.register(Curso)
class CursoAdmin(AVAModelAdmin):
    form = CursoAdminForm
    change_list_template = "admin/ava/curso/change_list.html"
    list_display = ("titulo", "slug", "cliente", "status", "is_aberto", "eixos_resumo")
    list_filter = ("status", "cliente", "is_aberto", "eixos")
    search_fields = ("titulo", "descricao_curta")
    prepopulated_fields = {"slug": ("titulo",)}
    filter_horizontal = ("trilhas", "eixos")

    def eixos_resumo(self, obj):
        nomes = list(obj.eixos.order_by("ordem_exibicao", "nome").values_list("nome", flat=True)[:3])
        if not nomes:
            return "Livre"
        if obj.eixos.count() > 3:
            return f"{', '.join(nomes)}..."
        return ", ".join(nomes)

    eixos_resumo.short_description = "Eixos"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "copiar-estrutura/",
                self.admin_site.admin_view(self.copy_structure_view),
                name="ava_curso_copy_structure",
            ),
        ]
        return custom_urls + urls

    def copy_structure_view(self, request):
        if not self._is_super_admin(request):
            raise PermissionDenied("A cópia entre municípios está disponível apenas para super admins.")

        form = CursoEstruturaCopyForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            curso_copiado = CourseCloneService.clone_course(
                CourseCopyOptions(
                    curso_origem=form.cleaned_data["curso_origem"],
                    cliente_destino=form.cleaned_data["cliente_destino"],
                    novo_titulo=form.cleaned_data["novo_titulo"],
                    novo_slug=form.cleaned_data["novo_slug"],
                    copiar_atividades=form.cleaned_data["copiar_atividades"],
                    manter_status_publicacao=form.cleaned_data["manter_status_publicacao"],
                    usuario_executor=request.user,
                )
            )
            messages.success(
                request,
                f"Estrutura copiada com sucesso para '{curso_copiado.cliente.nome}' no curso '{curso_copiado.titulo}'.",
            )
            return redirect(reverse("admin:ava_curso_change", args=[curso_copiado.id]))

        context = {
            **self.admin_site.each_context(request),
            "title": "Copiar estrutura de curso entre municípios",
            "opts": self.model._meta,
            "form": form,
            "media": self.media + form.media,
        }
        return render(request, "admin/ava/curso/copy_structure.html", context)


@admin.register(CursoModulo)
class CursoModuloAdmin(AVAModelAdmin):
    form = CursoModuloAdminForm
    list_display = ("titulo", "curso", "ordem", "is_active", "data_liberacao_programada", "pre_requisito_modulo", "eixos_resumo")
    list_filter = ("curso", "is_active", "data_liberacao_programada", "eixos")
    search_fields = ("titulo", "curso__titulo")
    filter_horizontal = ("eixos",)
    inlines = [AulaInline]

    def eixos_resumo(self, obj):
        nomes = list(obj.eixos.order_by("ordem_exibicao", "nome").values_list("nome", flat=True)[:3])
        if not nomes:
            return "Livre"
        if obj.eixos.count() > 3:
            return f"{', '.join(nomes)}..."
        return ", ".join(nomes)

    eixos_resumo.short_description = "Eixos"


@admin.register(Aula)
class AulaAdmin(AVAModelAdmin):
    list_display = ("titulo", "modulo", "ordem", "tipo", "is_active", "editor_visual_link")
    list_filter = ("modulo__curso", "tipo", "is_active")
    search_fields = ("titulo", "modulo__titulo", "modulo__curso__titulo")
    inlines = [ConteudoAulaInline, AtividadeInline]
    fieldsets = (
        (None, {
            "fields": (
                "modulo",
                "titulo",
                "resumo",
                "ordem",
                "tipo",
                "duracao_estimada_minutos",
                "is_obigatoria",
                "is_active",
                "data_liberacao",
                "pre_requisito_aula",
            ),
        }),
        ("Imagem de exibição", {
            "description": (
                "Use o <strong>Editor visual</strong> (botão no topo desta página, "
                "após salvar) para enviar a imagem e ajustar tamanho/posição com pré-visualização."
            ),
            "fields": (
                "imagem_display",
                "imagem_posicao",
                "imagem_largura_percent",
                "imagem_alinhamento",
            ),
        }),
    )
    change_form_template = "admin/ava/aula/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/editor-visual/",
                self.admin_site.admin_view(self.editor_visual_view),
                name="ava_aula_editor_visual",
            ),
        ]
        return custom + urls

    def editor_visual_link(self, obj):
        if obj.pk is None:
            return "—"
        url = reverse("admin:ava_aula_editor_visual", args=[obj.pk])
        return format_html('<a class="button" href="{}">Abrir editor visual</a>', url)

    editor_visual_link.short_description = "Editor visual"

    def editor_visual_view(self, request, object_id):
        from ava.views.editor_visual import editor_visual_aula
        return editor_visual_aula(self, request, object_id)


@admin.register(ConteudoAula)
class ConteudoAulaAdmin(AVAModelAdmin):
    list_display = ("titulo", "aula", "tipo", "ordem", "editor_visual_link")
    list_filter = ("tipo", "aula__modulo__curso")
    search_fields = ("titulo", "aula__titulo", "aula__modulo__titulo")
    fieldsets = (
        (None, {
            "fields": (
                "aula",
                "tipo",
                "titulo",
                "descricao",
                "ordem",
                "is_obrigatorio",
            ),
        }),
        ("Conteúdo específico do tipo", {
            "fields": (
                "conteudo_texto",
                "url",
                "arquivo",
                "embed_code",
            ),
        }),
        ("Imagem de exibição", {
            "description": (
                "Use o <strong>Editor visual</strong> (botão no topo desta página, "
                "após salvar) para enviar a imagem e ajustar tamanho/posição com pré-visualização."
            ),
            "fields": (
                "imagem_display",
                "imagem_posicao",
                "imagem_largura_percent",
                "imagem_alinhamento",
            ),
        }),
    )
    change_form_template = "admin/ava/conteudoaula/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/editor-visual/",
                self.admin_site.admin_view(self.editor_visual_view),
                name="ava_conteudoaula_editor_visual",
            ),
        ]
        return custom + urls

    def editor_visual_link(self, obj):
        if obj.pk is None:
            return "—"
        url = reverse("admin:ava_conteudoaula_editor_visual", args=[obj.pk])
        return format_html('<a class="button" href="{}">Abrir editor visual</a>', url)

    editor_visual_link.short_description = "Editor visual"

    def editor_visual_view(self, request, object_id):
        from ava.views.editor_visual import editor_visual_conteudo
        return editor_visual_conteudo(self, request, object_id)


@admin.register(Atividade)
class AtividadeAdmin(AVAModelAdmin):
    form = AtividadeAdminForm
    list_display = ("titulo", "aula", "tipo", "is_obrigatoria", "acesso_bloqueado", "eixos_resumo")
    list_filter = ("tipo", "is_obrigatoria", "acesso_bloqueado", "aula__modulo__curso", "eixos")
    search_fields = ("titulo", "descricao", "aula__titulo")
    filter_horizontal = ("eixos",)

    def eixos_resumo(self, obj):
        nomes = list(obj.eixos.order_by("ordem_exibicao", "nome").values_list("nome", flat=True)[:3])
        if not nomes:
            return "Livre"
        if obj.eixos.count() > 3:
            return f"{', '.join(nomes)}..."
        return ", ".join(nomes)

    eixos_resumo.short_description = "Eixos"


@admin.register(QuizQuestao)
class QuizQuestaoAdmin(AVAModelAdmin):
    form = QuizQuestaoAdminForm
    list_display = ("ordem", "atividade", "cliente")
    list_filter = ("atividade__aula__modulo__curso",)
    search_fields = ("enunciado", "atividade__titulo")
    inlines = [QuizAlternativaInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "atividade":
            formfield.queryset = formfield.queryset.filter(
                tipo__in=[Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO]
            )
        return formfield


@admin.register(QuizAlternativa)
class QuizAlternativaAdmin(AVAModelAdmin):
    list_display = ("questao", "ordem", "is_correta", "cliente")
    list_filter = ("is_correta", "questao__atividade__aula__modulo__curso")
    search_fields = ("texto", "questao__enunciado")


class AtividadeTentativaArquivoInline(admin.TabularInline):
    model = AtividadeTentativaArquivo
    extra = 0
    fields = ("arquivo", "nome_original", "created_at")
    readonly_fields = ("created_at",)


@admin.register(AtividadeTentativa)
class AtividadeTentativaAdmin(AVAModelAdmin):
    list_display = ("aluno", "atividade", "status", "data_inicio")
    list_filter = ("status", "atividade__aula__modulo__curso")
    search_fields = ("aluno__nome", "aluno__email", "atividade__titulo")
    inlines = [AtividadeTentativaArquivoInline]


@admin.register(AtividadeForumMensagem)
class AtividadeForumMensagemAdmin(AVAModelAdmin):
    list_display = ("atividade", "autor", "created_at", "cliente")
    list_filter = ("atividade__aula__modulo__curso",)
    search_fields = ("texto", "autor__nome", "autor__email", "atividade__titulo")


@admin.register(AtividadeForumAnexo)
class AtividadeForumAnexoAdmin(AVAModelAdmin):
    list_display = ("mensagem", "nome_original", "created_at", "cliente")
    list_filter = ("mensagem__atividade__aula__modulo__curso",)
    search_fields = ("nome_original", "mensagem__autor__nome", "mensagem__atividade__titulo")


@admin.register(AtividadeTentativaArquivo)
class AtividadeTentativaArquivoAdmin(AVAModelAdmin):
    list_display = ("tentativa", "nome_original", "created_at", "cliente")
    list_filter = ("tentativa__atividade__aula__modulo__curso",)
    search_fields = ("nome_original", "tentativa__aluno__nome", "tentativa__atividade__titulo")


@admin.register(MatriculaCurso)
class MatriculaCursoAdmin(AVAModelAdmin):
    list_display = ("aluno", "curso", "status", "progresso_percentual")
    list_filter = ("status", "curso")
    search_fields = ("aluno__nome", "aluno__email", "curso__titulo")


@admin.register(MatriculaTrilha)
class MatriculaTrilhaAdmin(AVAModelAdmin):
    list_display = ("aluno", "trilha", "status", "progresso_percentual")
    list_filter = ("status", "trilha")
    search_fields = ("aluno__nome", "aluno__email", "trilha__nome")


def _certificado_nome_arquivo(certificado):
    aluno_nome = certificado.dados_impressos.get("aluno_nome") or getattr(certificado.aluno, "nome", "") or certificado.aluno.email
    curso_nome = certificado.dados_impressos.get("curso_nome")
    if not curso_nome and certificado.matricula_curso_id:
        curso_nome = certificado.matricula_curso.curso.titulo
    base = slugify(f"{aluno_nome}-{curso_nome or certificado.codigo_validacao}") or certificado.codigo_validacao
    return f"{base}.pdf"


def _candidate_queryset_from_form(form, request):
    data = form.cleaned_data
    curso = data["curso"]
    qs = (
        MatriculaCurso.objects.select_related(
            "aluno",
            "aluno__escola",
            "aluno__tipo_cadastro",
            "curso",
        )
        .prefetch_related("aluno__grupos_trabalho", "aluno__eixos", "curso__eixos")
        .filter(curso=curso)
        .order_by("aluno__nome", "aluno__email")
    )
    if getattr(request.user, "role", None) != Usuario.Role.SUPER_ADMIN:
        qs = qs.filter(cliente_id=request.user.cliente_id)
    if data.get("aluno"):
        qs = qs.filter(aluno=data["aluno"])
    if data.get("escola"):
        qs = qs.filter(aluno__escola=data["escola"])
    if data.get("gt"):
        qs = qs.filter(aluno__grupos_trabalho=data["gt"])
    if data.get("tipos_usuario"):
        qs = qs.filter(aluno__role__in=data["tipos_usuario"])
    if data.get("tipo_cadastro"):
        qs = qs.filter(aluno__tipo_cadastro=data["tipo_cadastro"])
    eixos = data.get("eixos")
    if eixos:
        qs = qs.filter(Q(curso__eixos__in=eixos) | Q(aluno__eixos__in=eixos)).distinct()
    return qs


@admin.register(Certificado)
class CertificadoAdmin(AVAModelAdmin):
    change_list_template = "admin/ava/certificado/change_list.html"
    list_display = ("aluno", "curso_certificado", "codigo_validacao", "data_emissao", "liberado_em", "pdf_link")
    list_filter = ("liberado_em", "matricula_curso__curso", "aluno__escola")
    search_fields = ("aluno__nome", "aluno__email", "codigo_validacao")
    readonly_fields = ("codigo_validacao", "dados_impressos", "data_emissao", "arquivo_pdf")
    actions = ("baixar_certificados_zip",)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "emitir/",
                self.admin_site.admin_view(self.emitir_view),
                name="ava_certificado_emitir_lote",
            ),
            path(
                "baixar-todos/",
                self.admin_site.admin_view(self.baixar_todos_view),
                name="ava_certificado_baixar_todos",
            ),
            path(
                "<int:object_id>/baixar/",
                self.admin_site.admin_view(self.baixar_pdf_view),
                name="ava_certificado_baixar_pdf",
            ),
        ]
        return custom + urls

    def curso_certificado(self, obj):
        if obj.matricula_curso_id:
            return obj.matricula_curso.curso.titulo
        if obj.matricula_trilha_id:
            return obj.matricula_trilha.trilha.nome
        return "-"

    curso_certificado.short_description = "Curso/Trilha"

    def pdf_link(self, obj):
        if not obj.pk or not obj.arquivo_pdf:
            return "-"
        url = reverse("admin:ava_certificado_baixar_pdf", args=[obj.pk])
        return format_html('<a class="button" href="{}">Baixar PDF</a>', url)

    pdf_link.short_description = "PDF"

    def baixar_pdf_view(self, request, object_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        certificado = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not certificado.arquivo_pdf:
            raise Http404("Certificado sem PDF gerado.")
        return FileResponse(certificado.arquivo_pdf.open("rb"), as_attachment=True, filename=_certificado_nome_arquivo(certificado))

    def _garantir_pdf(self, certificado):
        """Garante que o certificado tenha PDF, gerando na hora se necessario.

        A geracao normal acontece no worker Celery apos a emissao em lote. Quando
        a fila esta indisponivel o PDF nunca chega a ser criado, entao aqui fazemos
        um fallback sincrono no proprio download. Retorna True quando ha um PDF
        disponivel (existente ou recem gerado) e False quando nao foi possivel
        gerar (por exemplo, certificado sem configuracao).
        """
        if certificado.arquivo_pdf:
            return True
        config = certificado.config
        if config is None:
            logger.warning(
                "Certificado %s sem configuração; PDF não pode ser gerado no download.",
                certificado.pk,
            )
            return False
        try:
            CertificacaoService.gerar_pdf(certificado, config)
            certificado.save(update_fields=["arquivo_pdf"])
        except Exception:
            logger.exception(
                "Falha ao gerar PDF do certificado %s durante o download em ZIP.",
                certificado.pk,
            )
            return False
        return bool(certificado.arquivo_pdf)

    def _resposta_zip(self, request, queryset, *, nome_arquivo):
        certificados = queryset.select_related(
            "aluno", "config", "matricula_curso__curso"
        ).iterator(chunk_size=200)
        buffer = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
        total = 0
        sem_pdf = 0
        nomes_usados = set()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for certificado in certificados:
                if not self._garantir_pdf(certificado):
                    sem_pdf += 1
                    continue
                nome_pdf = _certificado_nome_arquivo(certificado)
                nome_base, extensao = nome_pdf.rsplit(".", 1)
                nome_unico = nome_pdf
                contador = 2
                while nome_unico.casefold() in nomes_usados:
                    nome_unico = f"{nome_base}-{contador}.{extensao}"
                    contador += 1
                nomes_usados.add(nome_unico.casefold())
                certificado.arquivo_pdf.open("rb")
                try:
                    zip_file.writestr(nome_unico, certificado.arquivo_pdf.read())
                finally:
                    certificado.arquivo_pdf.close()
                total += 1
        if not total:
            buffer.close()
            if sem_pdf:
                self.message_user(
                    request,
                    f"Não foi possível gerar o PDF de {sem_pdf} certificado(s). "
                    "Verifique se os cursos possuem configuração de certificado e consulte os logs.",
                    level=messages.ERROR,
                )
            else:
                self.message_user(request, "Nenhum certificado possui PDF gerado.", level=messages.WARNING)
            return None
        if sem_pdf:
            self.message_user(
                request,
                f"{sem_pdf} certificado(s) foram ignorados por não ter PDF gerado.",
                level=messages.WARNING,
            )
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=nome_arquivo, content_type="application/zip")

    def baixar_certificados_zip(self, request, queryset):
        return self._resposta_zip(request, queryset, nome_arquivo="certificados-selecionados.zip")

    baixar_certificados_zip.short_description = "Baixar certificados selecionados em ZIP"

    def baixar_todos_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        # Nao filtramos por arquivo_pdf: os que ainda nao tiverem PDF sao gerados
        # sob demanda dentro de _resposta_zip (fallback quando a fila Celery nao
        # processou a geracao apos a emissao em lote).
        queryset = self.get_queryset(request)
        response = self._resposta_zip(request, queryset, nome_arquivo="todos-os-certificados.zip")
        if response is not None:
            return response
        return redirect("admin:ava_certificado_changelist")

    def emitir_view(self, request):
        form = CertificadoBatchEmitForm(request.POST or None, request=request)
        candidatos = []
        pendentes = []
        elegiveis = []
        emitidos = []

        if request.method == "POST" and form.is_valid():
            candidatos = list(_candidate_queryset_from_form(form, request))
            for matricula in candidatos:
                elegibilidade = CertificacaoService.avaliar_matricula(matricula)
                item = {"matricula": matricula, "elegibilidade": elegibilidade}
                if elegibilidade.approved:
                    elegiveis.append(item)
                else:
                    pendentes.append(item)

            if request.POST.get("confirmar") == "1":
                if pendentes and not form.cleaned_data.get("aprovar_pendentes"):
                    messages.warning(
                        request,
                        "Há cursistas sem conclusão. Marque a aprovação de pendentes para confirmar a emissão mesmo assim.",
                    )
                else:
                    liberar_em = timezone.now() if form.cleaned_data.get("liberar_agora") else form.cleaned_data.get("liberar_em")
                    campos = form.cleaned_data.get("campos_variaveis") or form.cleaned_data["config"].campos_variaveis
                    try:
                        with transaction.atomic():
                            for matricula in candidatos:
                                certificado, _, _ = CertificacaoService.emitir_para_matricula(
                                    matricula,
                                    form.cleaned_data["config"],
                                    emitido_por=request.user,
                                    campos=campos,
                                    liberado_em=liberar_em,
                                    aprovar_pendente=form.cleaned_data.get("aprovar_pendentes"),
                                    gerar_pdf=False,
                                )
                                if certificado:
                                    emitidos.append(certificado)
                    except Exception:
                        logger.exception("Falha ao preparar certificados no admin do AVA")
                        messages.error(
                            request,
                            "Não foi possível preparar os certificados. Nenhum registro deste lote foi salvo. "
                            "Consulte os logs do serviço web para o detalhe técnico.",
                        )
                    else:
                        enfileirados = 0
                        for certificado in emitidos:
                            try:
                                build_certificate_pdf.delay(certificado.pk, list(campos))
                            except Exception:
                                logger.exception(
                                    "Falha ao enviar o certificado %s para a fila de PDFs",
                                    certificado.pk,
                                )
                                break
                            enfileirados += 1

                        if enfileirados == len(emitidos):
                            messages.success(
                                request,
                                f"{len(emitidos)} certificado(s) preparado(s). Os PDFs serão gerados em segundo plano.",
                            )
                        else:
                            messages.error(
                                request,
                                f"{len(emitidos)} certificado(s) foram preparados, mas somente {enfileirados} "
                                "entraram na fila de PDFs. Verifique o Redis e o worker Celery antes de tentar novamente.",
                            )
                        return redirect("admin:ava_certificado_changelist")

        context = {
            **self.admin_site.each_context(request),
            "title": "Elaborar certificados AVA",
            "opts": self.model._meta,
            "form": form,
            "media": self.media + form.media,
            "candidatos": candidatos,
            "elegiveis": elegiveis,
            "pendentes": pendentes,
            "confirmacao_exigida": bool(candidatos),
        }
        return render(request, "admin/ava/certificado/batch_emit.html", context)


@admin.register(ConfigCertificado)
class ConfigCertificadoAdmin(AVAModelAdmin):
    form = ConfigCertificadoAdminForm
    inlines = [AssinaturaCertificadoInline]
    list_display = ("__str__", "cliente", "tema_padrao", "quantidade_assinaturas", "preview_link")
    list_filter = ("cliente", "tema_padrao")
    search_fields = ("curso__titulo", "trilha__nome", "titulo")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "cliente",
                    "curso",
                    "trilha",
                    "titulo",
                    "subtitulo",
                    "subtitulo_alinhamento",
                    "template_html",
                    "campos_variaveis",
                )
            },
        ),
        ("Fundo e tema", {"fields": ("fundo", "tema_padrao", "cor_texto")}),
        (
            "Verso (segunda página)",
            {
                "fields": (
                    "verso_ativo",
                    "verso_titulo",
                    "verso_template_html",
                    "verso_alinhamento",
                    "verso_fundo",
                ),
                "description": "Ative para acrescentar uma segunda página ao PDF. O conteúdo aceita HTML e variáveis do certificado.",
            },
        ),
        (
            "Posição do texto",
            {"fields": ("texto_x", "texto_y", "texto_largura", "titulo_tamanho", "texto_tamanho")},
        ),
        ("Carga horária e assinaturas", {"fields": ("carga_horaria_impressa", "quantidade_assinaturas", "assinatura_digital_url")}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="ava_configcertificado_preview",
            ),
        ]
        return custom + urls

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if self._is_super_admin(request):
            return fieldsets
        sanitized = []
        for title, options in fieldsets:
            fields = tuple(field for field in options.get("fields", ()) if field != "cliente")
            sanitized_options = {**options, "fields": fields}
            sanitized.append((title, sanitized_options))
        return sanitized

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, AssinaturaCertificado):
                obj.cliente_id = form.instance.cliente_id
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    def preview_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:ava_configcertificado_preview", args=[obj.pk])
        return format_html('<a class="button" target="_blank" href="{}">Prévia</a>', url)

    preview_link.short_description = "Prévia"

    def preview_view(self, request, object_id):
        config = get_object_or_404(self.get_queryset(request), pk=object_id)
        matricula = None
        if config.curso_id:
            matricula = (
                MatriculaCurso.objects.select_related("aluno", "aluno__escola", "aluno__tipo_cadastro", "curso")
                .prefetch_related("aluno__grupos_trabalho", "aluno__eixos", "curso__eixos")
                .filter(curso=config.curso)
                .order_by("aluno__nome", "aluno__email")
                .first()
            )
        if not matricula:
            return HttpResponse("Cadastre ao menos uma matrícula no curso para visualizar a prévia.", status=404)
        html = CertificacaoService.renderizar_html(None, matricula, config)
        return HttpResponse(html)
