from typing import ClassVar

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from ava.models import AutorizacaoCurso, Curso, EncontroCurso, PresencaCurso
from ava.services.attendance_service import (
    matriculas_do_curso,
    registrar_presenca,
    resumo_frequencia,
)
from ava.services.audit_service import AVAAuditService


class EncontroForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-check-input"
                if isinstance(field.widget, forms.CheckboxInput)
                else "form-control"
            )

    class Meta:
        model = EncontroCurso
        fields: ClassVar = [
            "titulo",
            "data_aula",
            "realizado",
            "link_aberto",
            "link_expira_em",
        ]
        widgets: ClassVar = {
            "data_aula": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "link_expira_em": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}
            ),
        }

    def clean(self):
        data = super().clean()
        if (
            data.get("realizado")
            and data.get("data_aula")
            and data["data_aula"] > timezone.localdate()
        ):
            self.add_error(
                "data_aula", "Um encontro futuro não pode ser marcado como realizado."
            )
        if data.get("link_aberto") and (
            not data.get("link_expira_em") or data["link_expira_em"] <= timezone.now()
        ):
            self.add_error(
                "link_expira_em", "Para abrir o link, informe um prazo futuro."
            )
        return data


def cursos_gerenciaveis(user):
    qs = Curso.raw_objects.filter(
        is_deleted=False, cliente__in=user.get_ava_clientes_queryset()
    )
    if user.is_superuser or user.role in {"super_admin", "admin_cliente"}:
        return qs
    autorizados = AutorizacaoCurso.raw_objects.filter(
        usuario=user,
        is_deleted=False,
        papel__in=["gestor", "tutor"],
    ).values("curso_id")
    return qs.filter(Q(autor_principal=user) | Q(pk__in=autorizados))


@login_required
@require_http_methods(["GET", "POST"])
def frequencia_lista(request):
    cursos = cursos_gerenciaveis(request.user).order_by("titulo")
    if not cursos.exists():
        raise PermissionDenied("Você não possui cursos para registrar frequência.")
    curso = (
        get_object_or_404(cursos, pk=request.GET["curso"])
        if request.GET.get("curso")
        else cursos.first()
    )
    form = EncontroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        encontro = form.save(commit=False)
        encontro.curso = curso
        encontro.cliente_id = curso.cliente_id
        encontro.save()
        return redirect("ava:frequencia_checklist", encontro_id=encontro.pk)
    encontros = EncontroCurso.raw_objects.filter(curso=curso, is_deleted=False)
    resumo = []
    for matricula in matriculas_do_curso(curso):
        resumo.append({"matricula": matricula, **resumo_frequencia(matricula)})
    return render(
        request,
        "ava/management/frequencia_lista.html",
        {
            "cursos": cursos,
            "curso": curso,
            "form": form,
            "encontros": encontros,
            "resumo": resumo,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def frequencia_checklist(request, encontro_id):
    encontro = get_object_or_404(
        EncontroCurso.raw_objects.select_for_update(),
        pk=encontro_id,
        curso__in=cursos_gerenciaveis(request.user),
        is_deleted=False,
    )
    matriculas = list(matriculas_do_curso(encontro.curso))
    form = EncontroForm(request.POST or None, instance=encontro)
    if request.method == "POST" and form.is_valid():
        selecionados = set(request.POST.getlist("presentes"))
        if not selecionados.issubset({str(m.pk) for m in matriculas}):
            return HttpResponseBadRequest(
                "A lista contém cursistas de outro curso ou sem matrícula ativa."
            )
        form.save()
        for matricula in matriculas:
            registrar_presenca(
                encontro,
                matricula,
                request.user,
                presente=str(matricula.pk) in selecionados,
                origem="checklist",
            )
        AVAAuditService.registrar(
            cliente_id=encontro.cliente_id,
            usuario=request.user,
            entidade="ava.EncontroCurso",
            entidade_id=encontro.pk,
            acao="frequencia_checklist",
            diff={
                "data_aula": encontro.data_aula.isoformat(),
                "presentes": sorted(selecionados),
            },
        )
        messages.success(request, "Data e frequência salvas.")
        return redirect("ava:frequencia_checklist", encontro_id=encontro.pk)
    presentes = set(
        PresencaCurso.raw_objects.filter(
            encontro=encontro,
            presente=True,
            is_deleted=False,
        ).values_list("matricula_id", flat=True)
    )
    linhas = [
        {
            "matricula": m,
            "presente": (str(m.pk) in request.POST.getlist("presentes"))
            if request.method == "POST"
            else m.pk in presentes,
        }
        for m in matriculas
    ]
    return render(
        request,
        "ava/management/frequencia_checklist.html",
        {
            "encontro": encontro,
            "form": form,
            "linhas": linhas,
            "link_presenca": request.build_absolute_uri(
                reverse("ava:confirmar_presenca", args=[encontro.token])
            ),
        },
    )


@require_http_methods(["GET", "POST"])
@transaction.atomic
def confirmar_presenca(request, token):
    encontro = get_object_or_404(
        EncontroCurso.raw_objects.select_for_update(),
        token=token,
        is_deleted=False,
        curso__is_deleted=False,
    )
    if not request.user.is_authenticated:
        login_form = AuthenticationForm(request, data=request.POST or None)
        for field in login_form.fields.values():
            field.widget.attrs["class"] = "form-control"
        if request.method == "POST" and login_form.is_valid():
            login(request, login_form.get_user())
            return redirect("ava:confirmar_presenca", token=token)
        return render(
            request,
            "ava/student/confirmar_presenca.html",
            {
                "encontro": encontro,
                "login_form": login_form,
            },
        )
    matricula = get_object_or_404(
        matriculas_do_curso(encontro.curso), aluno=request.user
    )
    aberto = (
        encontro.link_aberto
        and encontro.link_expira_em
        and encontro.link_expira_em > timezone.now()
    )
    if request.method == "POST":
        if not aberto:
            messages.error(request, "O link de presença está fechado ou expirou.")
        else:
            registrar_presenca(
                encontro, matricula, request.user, presente=True, origem="link"
            )
            AVAAuditService.registrar(
                cliente_id=encontro.cliente_id,
                usuario=request.user,
                entidade="ava.EncontroCurso",
                entidade_id=encontro.pk,
                acao="presenca_confirmada_link",
                diff={"matricula_id": matricula.pk},
            )
            messages.success(request, "Sua presença foi confirmada.")
        return redirect("ava:confirmar_presenca", token=token)
    presente = PresencaCurso.raw_objects.filter(
        encontro=encontro,
        matricula=matricula,
        presente=True,
        is_deleted=False,
    ).exists()
    return render(
        request,
        "ava/student/confirmar_presenca.html",
        {
            "encontro": encontro,
            "aberto": aberto,
            "presente": presente,
        },
    )
