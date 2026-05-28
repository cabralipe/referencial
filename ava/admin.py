from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse

from ava.forms import CursoEstruturaCopyForm
from ava.services import CourseCloneService
from ava.services.course_copy_service import CourseCopyOptions

from .models import (
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


ADMIN_ROLES = {"admin_cliente", "super_admin"}


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

    def has_view_permission(self, request, obj=None):
        return self._is_admin_role(request)

    def has_add_permission(self, request, obj):
        return self._is_admin_role(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin_role(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_admin_role(request)


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
    list_display = ("titulo", "slug", "cliente", "status", "is_aberto")
    list_filter = ("status", "cliente", "is_aberto")
    search_fields = ("titulo", "descricao_curta")
    prepopulated_fields = {"slug": ("titulo",)}

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
    list_display = ("titulo", "curso", "ordem", "is_active", "data_liberacao_programada", "pre_requisito_modulo")
    list_filter = ("curso", "is_active", "data_liberacao_programada")
    search_fields = ("titulo", "curso__titulo")
    inlines = [AulaInline]


@admin.register(Aula)
class AulaAdmin(AVAModelAdmin):
    list_display = ("titulo", "modulo", "ordem", "tipo", "is_active")
    list_filter = ("modulo__curso", "tipo", "is_active")
    search_fields = ("titulo", "modulo__titulo", "modulo__curso__titulo")
    inlines = [ConteudoAulaInline, AtividadeInline]


@admin.register(Atividade)
class AtividadeAdmin(AVAModelAdmin):
    list_display = ("titulo", "aula", "tipo", "is_obrigatoria")
    list_filter = ("tipo", "is_obrigatoria", "aula__modulo__curso")
    search_fields = ("titulo", "descricao", "aula__titulo")


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


@admin.register(AtividadeTentativa)
class AtividadeTentativaAdmin(AVAModelAdmin):
    list_display = ("aluno", "atividade", "status", "data_inicio")
    list_filter = ("status", "atividade__aula__modulo__curso")
    search_fields = ("aluno__nome", "aluno__email", "atividade__titulo")


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


@admin.register(Certificado)
class CertificadoAdmin(AVAModelAdmin):
    list_display = ("aluno", "codigo_validacao", "data_emissao")
    search_fields = ("aluno__nome", "aluno__email", "codigo_validacao")
    readonly_fields = ("codigo_validacao", "dados_impressos", "data_emissao")


@admin.register(ConfigCertificado)
class ConfigCertificadoAdmin(AVAModelAdmin):
    list_display = ("__str__", "cliente")
