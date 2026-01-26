"""Views HTML para o módulo de revisores."""

from __future__ import annotations

import json
from typing import Any, Iterable

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from comments.models import Comentario
from core.models import Cliente, Usuario
from core.utils import flag_ativa
from curriculum.models import Pergunta, Resposta, TextoUnico
from diffs.services import build_diff
from notifications.models import Notificacao
from notifications.services import criar_notificacao
from reviews.models import ReviewDecision, Revisao
from services.reviewer_scope import get_reviewer_queryset
from workshop.models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha


def _ensure_reviewer(user: Usuario) -> None:
    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Autenticação obrigatória.")
    if getattr(user, "role", None) != user.Role.REVISOR:
        raise PermissionDenied("Acesso restrito ao perfil revisor.")


def _pick_mural_payload(notificacao: Notificacao) -> dict[str, Any]:
    payload = notificacao.payload_json or {}
    return {
        "id": payload.get("mural_id", str(notificacao.id)),
        "titulo": payload.get("titulo") or "",
        "conteudo_html": payload.get("conteudo_html") or "",
        "link_url": payload.get("link_url"),
        "anexos": payload.get("anexos") or [],
        "fixado": bool(payload.get("fixado", False)),
        "gt_ids": payload.get("gt_ids") or [],
        "criado_por": payload.get("criado_por") or {},
        "created_at": notificacao.created_at,
        "updated_at": notificacao.updated_at,
    }


def _get_mural_posts(user: Usuario, gt_id: int | None) -> list[dict[str, Any]]:
    if not gt_id:
        return []
    base = Notificacao.objects.filter(
        cliente_id=user.cliente_id,
        tipo="mural_post",
    )
    if getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
        base = base.filter(usuario=user)
    posts: list[dict[str, Any]] = []
    for notificacao in base.order_by("-updated_at")[:30]:
        payload = _pick_mural_payload(notificacao)
        gt_ids = payload.get("gt_ids") or []
        if gt_ids and gt_id not in gt_ids:
            continue
        posts.append(payload)
    return posts


def _get_target_context(revisao: Revisao) -> dict[str, Any]:
    alvo_tipo = revisao.alvo_tipo
    alvo_id = revisao.alvo_id
    contexto = {
        "titulo": f"{alvo_tipo} #{alvo_id}",
        "subtitulo": "",
        "conteudo_html": "",
        "orientacao": "",
        "gt_id": None,
        "etapa": "",
    }
    if alvo_tipo == Revisao.AlvoTipo.RESPOSTA:
        resposta = Resposta.objects.select_related("pergunta__tarefa", "gt").filter(pk=alvo_id).first()
        if not resposta:
            return contexto
        pergunta: Pergunta | None = getattr(resposta, "pergunta", None)
        tarefa_nome = getattr(pergunta, "tarefa", None)
        tarefa_label = tarefa_nome.nome if tarefa_nome else ""
        contexto.update(
            {
                "titulo": pergunta.texto if pergunta else "Resposta",
                "subtitulo": f"{tarefa_label} • {resposta.gt.nome}" if tarefa_label else resposta.gt.nome,
                "conteudo_html": resposta.conteudo_html or "",
                "orientacao": pergunta.texto if pergunta else "",
                "gt_id": resposta.gt_id,
                "etapa": getattr(resposta.gt, "etapa", ""),
                "version": resposta.version,
            }
        )
    elif alvo_tipo == Revisao.AlvoTipo.TEXTO_UNICO:
        texto = TextoUnico.objects.select_related("tarefa", "gt").filter(pk=alvo_id).first()
        if not texto:
            return contexto
        tarefa = texto.tarefa
        contexto.update(
            {
                "titulo": f"Texto único • {tarefa.nome}",
                "subtitulo": texto.gt.nome,
                "conteudo_html": texto.conteudo_html or "",
                "orientacao": tarefa.nome,
                "gt_id": texto.gt_id,
                "etapa": getattr(texto.gt, "etapa", ""),
                "version": texto.version,
            }
        )
    elif alvo_tipo == Revisao.AlvoTipo.QUADRO:
        quadro = Quadro.objects.select_related("gt").filter(pk=alvo_id).first()
        if not quadro:
            return contexto
        linhas = list(QuadroLinha.objects.filter(quadro=quadro).order_by("ordem", "linha"))
        colunas = list(QuadroColuna.objects.filter(quadro=quadro).order_by("ordem", "coluna"))
        celulas = CelulaQuadro.objects.filter(quadro=quadro).order_by("linha", "coluna")
        lookup = {(c.linha, c.coluna): (c.valor_html or "") for c in celulas}
        table_rows: list[list[str]] = []
        if colunas:
            table_rows.append([""] + [col.nome for col in colunas])
            for linha in linhas:
                row = [linha.nome]
                for col in colunas:
                    row.append(lookup.get((linha.linha, col.coluna), ""))
                table_rows.append(row)
        else:
            for (linha, coluna), valor in lookup.items():
                table_rows.append([f"L{linha} C{coluna}", valor])
        contexto.update(
            {
                "titulo": f"Quadro • {quadro.template}",
                "subtitulo": quadro.gt.nome,
                "conteudo_html": "",
                "orientacao": "Quadro colaborativo",
                "gt_id": quadro.gt_id,
                "etapa": getattr(quadro.gt, "etapa", ""),
                "table_rows": table_rows,
                "version": quadro.version,
            }
        )
    return contexto


def _build_diff_html(revisao: Revisao, target_context: dict[str, Any]) -> str:
    alvo_tipo = revisao.alvo_tipo
    alvo_id = revisao.alvo_id
    version = target_context.get("version")
    if not version or version <= 1:
        return ""
    if alvo_tipo not in {Revisao.AlvoTipo.RESPOSTA, Revisao.AlvoTipo.TEXTO_UNICO}:
        return ""
    return build_diff(alvo_tipo, alvo_id, version - 1, version)


def _build_inbox_items(revisoes: Iterable[Revisao], user: Usuario) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for revisao in revisoes:
        alvo_tipo = revisao.alvo_tipo
        alvo_id = revisao.alvo_id
        pending_comments = Comentario.objects.filter(
            cliente_id=revisao.cliente_id,
            alvo_tipo=alvo_tipo,
            alvo_id=alvo_id,
            resolvido=False,
        ).count()
        last_reviewer_action = (
            ReviewDecision.objects.filter(
                cliente_id=revisao.cliente_id,
                target_type=alvo_tipo,
                target_id=alvo_id,
                actor_role=ReviewDecision.ActorRole.REVIEWER,
                actor=user,
            )
            .order_by("-created_at")
            .first()
        )
        reviewer_recommendation = (
            ReviewDecision.objects.filter(
                cliente_id=revisao.cliente_id,
                target_type=alvo_tipo,
                target_id=alvo_id,
                actor_role=ReviewDecision.ActorRole.REVIEWER,
                actor=user,
            )
            .exclude(decision_type=ReviewDecision.DecisionType.IN_PROGRESS)
            .order_by("-created_at")
            .first()
        )
        in_progress = bool(
            ReviewDecision.objects.filter(
                cliente_id=revisao.cliente_id,
                target_type=alvo_tipo,
                target_id=alvo_id,
                actor_role=ReviewDecision.ActorRole.REVIEWER,
                actor=user,
                decision_type=ReviewDecision.DecisionType.IN_PROGRESS,
            ).exists()
        )
        returned_count = ReviewDecision.objects.filter(
            cliente_id=revisao.cliente_id,
            target_type=alvo_tipo,
            target_id=alvo_id,
            actor_role=ReviewDecision.ActorRole.REDACTOR,
            decision_type=ReviewDecision.DecisionType.RECOMMEND_RETURN,
        ).count()
        changed_since_last = bool(last_reviewer_action and revisao.updated_at > last_reviewer_action.created_at)
        items.append(
            {
                "id": revisao.id,
                "alvo_tipo": revisao.alvo_tipo,
                "alvo_id": revisao.alvo_id,
                "status": revisao.status,
                "updated_at": revisao.updated_at,
                "solicitante": revisao.solicitante,
                "pending_comments": pending_comments,
                "changed_since_last": changed_since_last,
                "returned_count": returned_count,
                "in_progress": in_progress,
                "recommendation": reviewer_recommendation,
            }
        )
    return items


@login_required
def reviewer_inbox(request: HttpRequest) -> HttpResponse:
    _ensure_reviewer(request.user)
    queryset = get_reviewer_queryset(request.user).select_related("solicitante", "revisor")
    items = _build_inbox_items(queryset, request.user)
    tab = request.GET.get("tab", "para_revisar")
    tabs = {
        "para_revisar": [item for item in items if item["status"] == Revisao.Status.EM_REVISAO and not item["in_progress"] and not item["recommendation"]],
        "em_andamento": [item for item in items if item["in_progress"]],
        "revisado": [item for item in items if item["recommendation"]],
        "devolvido": [item for item in items if item["status"] == Revisao.Status.REPROVADO],
        "validado": [item for item in items if item["status"] == Revisao.Status.APROVADO],
    }
    return render(
        request,
        "reviewer_inbox.html",
        {
            "tab": tab,
            "items": tabs.get(tab, []),
            "counts": {key: len(value) for key, value in tabs.items()},
        },
    )


@login_required
def reviewer_mark_in_progress(request: HttpRequest, revisao_id: int) -> HttpResponse:
    _ensure_reviewer(request.user)
    if request.method != "POST":
        raise PermissionDenied("Método não permitido.")
    revisao = get_reviewer_queryset(request.user).filter(pk=revisao_id).first()
    if not revisao:
        raise Http404("Revisão não encontrada.")
    ReviewDecision.objects.create(
        cliente_id=revisao.cliente_id,
        target_type=revisao.alvo_tipo,
        target_id=revisao.alvo_id,
        actor=request.user,
        actor_role=ReviewDecision.ActorRole.REVIEWER,
        decision_type=ReviewDecision.DecisionType.IN_PROGRESS,
    )
    return redirect(reverse("reviewer_inbox") + "?tab=em_andamento")


@login_required
def reviewer_review_detail(request: HttpRequest, revisao_id: int) -> HttpResponse:
    _ensure_reviewer(request.user)
    revisao = get_reviewer_queryset(request.user).select_related("solicitante", "revisor").filter(pk=revisao_id).first()
    if not revisao:
        raise Http404("Revisão não encontrada.")

    target_context = _get_target_context(revisao)
    cliente = Cliente.objects.filter(pk=revisao.cliente_id).first()
    diff_html = ""
    if cliente and flag_ativa(cliente, "ff.diff.enabled"):
        diff_html = _build_diff_html(revisao, target_context)

    comentarios = (
        Comentario.objects.filter(
            cliente_id=revisao.cliente_id,
            alvo_tipo=revisao.alvo_tipo,
            alvo_id=revisao.alvo_id,
        )
        .select_related("autor", "resolvido_por")
        .order_by("created_at")
    )
    mural_posts = _get_mural_posts(request.user, target_context.get("gt_id"))

    if request.method == "POST":
        action = request.POST.get("action") or ""
        if action == "add_comment":
            conteudo_html = (request.POST.get("conteudo_html") or "").strip()
            anchor_raw = (request.POST.get("anchor_json") or "").strip()
            anchor_json = {}
            if anchor_raw:
                try:
                    anchor_json = json.loads(anchor_raw)
                except json.JSONDecodeError:
                    anchor_json = {"raw": anchor_raw}
            if conteudo_html:
                comentario = Comentario.objects.create(
                    cliente_id=revisao.cliente_id,
                    alvo_tipo=revisao.alvo_tipo,
                    alvo_id=revisao.alvo_id,
                    conteudo_html=conteudo_html,
                    anchor_json=anchor_json,
                    autor=request.user,
                )
                _notificar_comentario(revisao, comentario, request.user)
            return redirect(request.path)
        if action == "resolve_comment":
            comentario_id = request.POST.get("comentario_id")
            comentario = comentarios.filter(pk=comentario_id).first()
            if comentario and not comentario.resolvido:
                comentario.resolvido = True
                comentario.resolvido_por = request.user
                comentario.resolved_at = timezone.now()
                comentario.save(update_fields=["resolvido", "resolvido_por", "resolved_at", "updated_at"])
            return redirect(request.path)
        if action == "recommend":
            decision = (request.POST.get("decision") or "").lower()
            note = request.POST.get("note") or ""
            checklist = request.POST.getlist("checklist")
            decision_map = {
                "approve": ReviewDecision.DecisionType.RECOMMEND_APPROVE,
                "return": ReviewDecision.DecisionType.RECOMMEND_RETURN,
                "minor": ReviewDecision.DecisionType.RECOMMEND_MINOR,
            }
            if decision in decision_map:
                recommendation = ReviewDecision.objects.create(
                    cliente_id=revisao.cliente_id,
                    target_type=revisao.alvo_tipo,
                    target_id=revisao.alvo_id,
                    actor=request.user,
                    actor_role=ReviewDecision.ActorRole.REVIEWER,
                    decision_type=decision_map[decision],
                    checklist=checklist,
                    note=note,
                )
                interessados = Usuario.objects.filter(
                    cliente_id=revisao.cliente_id,
                    role__in=[request.user.Role.ARTICULADOR, request.user.Role.ADMIN_CLIENTE],
                )
                for interessado in interessados:
                    criar_notificacao(
                        cliente_id=revisao.cliente_id,
                        usuario_id=interessado.id,
                        tipo="revisao.reviewer_recommendation",
                        payload={"revisao_id": revisao.id, "decision": recommendation.decision_type},
                    )
            return redirect(reverse("reviewer_inbox") + "?tab=revisado")
        if action == "in_progress":
            ReviewDecision.objects.create(
                cliente_id=revisao.cliente_id,
                target_type=revisao.alvo_tipo,
                target_id=revisao.alvo_id,
                actor=request.user,
                actor_role=ReviewDecision.ActorRole.REVIEWER,
                decision_type=ReviewDecision.DecisionType.IN_PROGRESS,
            )
            return redirect(reverse("reviewer_inbox") + "?tab=em_andamento")

    reviewer_recommendation = (
        ReviewDecision.objects.filter(
            cliente_id=revisao.cliente_id,
            target_type=revisao.alvo_tipo,
            target_id=revisao.alvo_id,
            actor_role=ReviewDecision.ActorRole.REVIEWER,
            actor=request.user,
        )
        .exclude(decision_type=ReviewDecision.DecisionType.IN_PROGRESS)
        .order_by("-created_at")
        .first()
    )

    return render(
        request,
        "reviewer_review_detail.html",
        {
            "revisao": revisao,
            "target": target_context,
            "diff_html": diff_html,
            "comentarios": comentarios,
            "mural_posts": mural_posts,
            "reviewer_recommendation": reviewer_recommendation,
        },
    )


def _notificar_comentario(revisao: Revisao, comentario: Comentario, autor: Usuario) -> None:
    alvo_tipo = revisao.alvo_tipo
    alvo_id = revisao.alvo_id
    usuario_ids: set[int] = set()
    if alvo_tipo == Revisao.AlvoTipo.RESPOSTA:
        resposta = Resposta.objects.select_related("gt").filter(pk=alvo_id).first()
        if resposta:
            usuario_ids.update(resposta.gt.membros.values_list("id", flat=True))
    elif alvo_tipo == Revisao.AlvoTipo.TEXTO_UNICO:
        texto = TextoUnico.objects.select_related("gt").filter(pk=alvo_id).first()
        if texto:
            usuario_ids.update(texto.gt.membros.values_list("id", flat=True))
    elif alvo_tipo == Revisao.AlvoTipo.QUADRO:
        quadro = Quadro.objects.select_related("gt").filter(pk=alvo_id).first()
        if quadro:
            usuario_ids.update(quadro.gt.membros.values_list("id", flat=True))
    usuario_ids.discard(autor.id)
    for usuario_id in usuario_ids:
        criar_notificacao(
            cliente_id=revisao.cliente_id,
            usuario_id=usuario_id,
            tipo="comentario.novo",
            payload={"comentario_id": comentario.id, "alvo_tipo": comentario.alvo_tipo, "alvo_id": comentario.alvo_id},
        )
