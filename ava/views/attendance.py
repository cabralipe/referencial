from typing import ClassVar
import hashlib
import secrets

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

from ava.models import AutorizacaoCurso, Curso, DiarioBordo, EncontroCurso, MatriculaCurso, PresencaCurso, PresencaLinkDispositivo, RepasseFrequencia
from ava.services.attendance_service import (
    matriculas_do_curso,
    registrar_presenca,
    resumo_frequencia,
    remover_chamada,
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
            "registro_retroativo",
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
        if data.get("registro_retroativo"):
            data["realizado"] = True
            data["link_aberto"] = False
            data["link_expira_em"] = None
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


def _chamadas_do_usuario(user):
    from ava.views.diario import _diarios_do_usuario

    return EncontroCurso.raw_objects.filter(
        Q(curso__in=cursos_gerenciaveis(user))
        | Q(diario__in=_diarios_do_usuario(user)),
        is_deleted=False,
    )


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
    form = EncontroForm(
        request.POST or None,
        initial={"registro_retroativo": request.GET.get("retroativo") == "1"},
    )
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
            "repasses_fisicos": RepasseFrequencia.raw_objects.filter(curso=curso, is_deleted=False),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def frequencia_checklist(request, encontro_id):
    from ava.services.diario_service import DiarioBordoService

    encontro = get_object_or_404(
        _chamadas_do_usuario(request.user).select_for_update(),
        pk=encontro_id,
    )
    if encontro.diario_id and not DiarioBordoService.pode_editar(encontro.diario, request.user):
        raise PermissionDenied("Este diário não pode mais ter a frequência alterada.")
    matriculas = list(matriculas_do_curso(encontro.curso))
    data_registrada = encontro.data_aula
    form = EncontroForm(request.POST or None, instance=encontro)
    if request.method == "POST" and form.is_valid():
        selecionados = set(request.POST.getlist("presentes"))
        if not selecionados.issubset({str(m.pk) for m in matriculas}):
            return HttpResponseBadRequest(
                "A lista contém cursistas de outro curso ou sem matrícula ativa."
            )
        form.save()
        if encontro.diario_id:
            diario = encontro.diario
            diario.data_aula = encontro.data_aula
            diario.titulo = encontro.titulo
            diario.modo_frequencia = (
                DiarioBordo.ModoFrequencia.RETROATIVA if encontro.registro_retroativo
                else DiarioBordo.ModoFrequencia.LINK if encontro.link_aberto
                else DiarioBordo.ModoFrequencia.PRESENCIAL
            )
            diario.updated_by = request.user
            diario.save(update_fields=["data_aula", "titulo", "modo_frequencia", "updated_by", "updated_at"])
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
                "registro_retroativo": encontro.registro_retroativo,
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
            "presentes_registrados": [m for m in matriculas if m.pk in presentes],
            "data_registrada": data_registrada,
            "link_presenca": request.build_absolute_uri(
                reverse("ava:confirmar_presenca", args=[encontro.token])
            ),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def frequencia_remover(request, encontro_id):
    """Remove uma chamada e impede o uso do respectivo link de presença."""
    encontro = get_object_or_404(
        _chamadas_do_usuario(request.user).select_for_update(),
        pk=encontro_id,
    )
    if encontro.diario_id:
        from ava.services.diario_service import DiarioBordoService
        if not DiarioBordoService.pode_editar(encontro.diario, request.user):
            raise PermissionDenied("Este diário não pode ter a chamada excluída. Reabra o registro antes de excluir.")
    voltar_url = reverse("ava:frequencia_checklist", args=[encontro.pk])
    if request.method == "GET":
        return render(request, "ava/management/confirmar_exclusao.html", {
            "titulo_pagina": "Excluir registro de presença", "objeto": encontro,
            "descricao": "A chamada, as presenças e o link ou QR Code serão removidos. A frequência do curso será recalculada.",
            "voltar_url": voltar_url,
        })
    total_removido = remover_chamada(encontro)
    AVAAuditService.registrar(
        cliente_id=encontro.cliente_id,
        usuario=request.user,
        entidade="ava.EncontroCurso",
        entidade_id=encontro.pk,
        acao="frequencia_removida",
        diff={"presencas_removidas": total_removido},
    )
    messages.success(request, "Chamada e link de frequência removidos.")
    if encontro.diario_id:
        return redirect("ava:diario_editar", diario_id=encontro.diario_id)
    return redirect(f"{reverse('ava:frequencia_lista')}?curso={encontro.curso_id}")


@require_http_methods(["GET", "POST"])
@transaction.atomic
def confirmar_presenca(request, token):
    encontro = get_object_or_404(
        EncontroCurso.raw_objects.select_for_update(of=("self",)).filter(
            Q(diario__isnull=True) | Q(diario__is_deleted=False),
        ),
        token=token,
        is_deleted=False,
        curso__is_deleted=False,
    )
    aberto = (
        encontro.link_aberto
        and encontro.link_expira_em
        and encontro.link_expira_em > timezone.now()
        and not encontro.registro_retroativo
        and (not encontro.diario_id or encontro.diario.status == DiarioBordo.Status.RASCUNHO)
    )
    device_key = request.COOKIES.get("ava_presence_device") or secrets.token_urlsafe(32)
    device_hash = hashlib.sha256(device_key.encode()).hexdigest()
    bloqueado = PresencaLinkDispositivo.raw_objects.filter(
        encontro=encontro, dispositivo_hash=device_hash, is_deleted=False
    ).exists()
    matriculas = matriculas_do_curso(encontro.curso)
    if request.method == "POST":
        if not aberto:
            messages.error(request, "O link de presenca esta fechado ou expirou.")
        elif bloqueado:
            messages.error(request, "Este telefone ja confirmou presenca nesta chamada.")
        else:
            matricula = get_object_or_404(matriculas, pk=request.POST.get("matricula"))
            registrar_presenca(encontro, matricula, None, presente=True, origem="link")
            PresencaLinkDispositivo.raw_objects.create(
                cliente_id=encontro.cliente_id, encontro=encontro, dispositivo_hash=device_hash
            )
            messages.success(request, "Sua presenca foi confirmada.")
        response = redirect("ava:confirmar_presenca", token=token)
    else:
        response = render(request, "ava/student/confirmar_presenca.html", {
            "encontro": encontro, "aberto": aberto, "bloqueado": bloqueado, "matriculas": matriculas,
        })
    response.set_cookie("ava_presence_device", device_key, max_age=31536000, secure=request.is_secure(), httponly=True, samesite="Lax")
    return response

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
