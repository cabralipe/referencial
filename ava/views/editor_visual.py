"""Editor visual de imagem para Aula e ConteudoAula no admin."""
from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse

from ava.models import Aula, ConteudoAula
from ava.models.lesson import AlinhamentoImagem, PosicaoImagem


def _is_admin_role(request) -> bool:
    return (
        bool(getattr(request.user, "is_active", False))
        and bool(getattr(request.user, "is_staff", False))
        and getattr(request.user, "role", None) in {"admin_cliente", "super_admin"}
    )


def _is_super_admin(request) -> bool:
    return bool(getattr(request.user, "is_superuser", False)) or getattr(
        request.user, "role", None
    ) == "super_admin"


def _check_object_permission(request, obj) -> None:
    if not _is_admin_role(request):
        raise PermissionDenied("Apenas administradores podem usar o editor visual.")
    if not _is_super_admin(request) and obj.cliente_id != getattr(request.user, "cliente_id", None):
        raise PermissionDenied("Você não tem acesso a este registro.")


def _clamp_largura(raw) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 100
    return max(10, min(100, value))


def _normalize_choice(raw, choices_enum, default):
    valid = {choice.value for choice in choices_enum}
    if raw in valid:
        return raw
    return default


def _save_image_config(request, obj):
    if "imagem_display" in request.FILES:
        obj.imagem_display = request.FILES["imagem_display"]
    if request.POST.get("remover_imagem") == "1":
        if obj.imagem_display:
            obj.imagem_display.delete(save=False)
        obj.imagem_display = None
    obj.imagem_posicao = _normalize_choice(
        request.POST.get("imagem_posicao"),
        PosicaoImagem,
        PosicaoImagem.ACIMA,
    )
    obj.imagem_alinhamento = _normalize_choice(
        request.POST.get("imagem_alinhamento"),
        AlinhamentoImagem,
        AlinhamentoImagem.CENTRO,
    )
    obj.imagem_largura_percent = _clamp_largura(request.POST.get("imagem_largura_percent"))
    obj.save(
        update_fields=[
            "imagem_display",
            "imagem_posicao",
            "imagem_alinhamento",
            "imagem_largura_percent",
            "updated_at",
        ]
    )


def editor_visual_aula(model_admin, request, object_id):
    obj = Aula.objects.select_related("modulo", "modulo__curso").filter(pk=object_id).first()
    if obj is None:
        messages.error(request, "Aula não encontrada.")
        return redirect("admin:ava_aula_changelist")
    _check_object_permission(request, obj)

    if request.method == "POST":
        _save_image_config(request, obj)
        messages.success(request, "Imagem da aula atualizada.")
        if "salvar_e_voltar" in request.POST:
            return redirect("admin:ava_aula_change", obj.pk)
        return redirect("admin:ava_aula_editor_visual", obj.pk)

    context = {
        **model_admin.admin_site.each_context(request),
        "title": f"Editor visual — {obj.titulo}",
        "subtitle": f"{obj.modulo.curso.titulo} · Aula {obj.ordem}",
        "object": obj,
        "alvo_tipo": "aula",
        "alvo_titulo": obj.titulo,
        "alvo_resumo": obj.resumo,
        "alvo_texto_secundario": "",
        "posicao_choices": PosicaoImagem.choices,
        "alinhamento_choices": AlinhamentoImagem.choices,
        "voltar_url": reverse("admin:ava_aula_change", args=[obj.pk]),
        "changelist_url": reverse("admin:ava_aula_changelist"),
        "opts": model_admin.model._meta,
        "has_view_permission": True,
    }
    return render(request, "admin/ava/editor_visual.html", context)


def editor_visual_conteudo(model_admin, request, object_id):
    obj = ConteudoAula.objects.select_related("aula", "aula__modulo", "aula__modulo__curso").filter(pk=object_id).first()
    if obj is None:
        messages.error(request, "Conteúdo de aula não encontrado.")
        return redirect("admin:ava_conteudoaula_changelist")
    _check_object_permission(request, obj)

    if request.method == "POST":
        _save_image_config(request, obj)
        messages.success(request, "Imagem do conteúdo de aula atualizada.")
        if "salvar_e_voltar" in request.POST:
            return redirect("admin:ava_conteudoaula_change", obj.pk)
        return redirect("admin:ava_conteudoaula_editor_visual", obj.pk)

    context = {
        **model_admin.admin_site.each_context(request),
        "title": f"Editor visual — {obj.titulo}",
        "subtitle": f"{obj.aula.modulo.curso.titulo} · {obj.aula.titulo}",
        "object": obj,
        "alvo_tipo": "conteudo",
        "alvo_titulo": obj.titulo,
        "alvo_resumo": obj.descricao,
        "alvo_texto_secundario": obj.conteudo_texto,
        "posicao_choices": PosicaoImagem.choices,
        "alinhamento_choices": AlinhamentoImagem.choices,
        "voltar_url": reverse("admin:ava_conteudoaula_change", args=[obj.pk]),
        "changelist_url": reverse("admin:ava_conteudoaula_changelist"),
        "opts": model_admin.model._meta,
        "has_view_permission": True,
    }
    return render(request, "admin/ava/editor_visual.html", context)
