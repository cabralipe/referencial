"""Escopo de revisoes permitido ao revisor."""

from __future__ import annotations

from django.db import models
from django.db.models.functions import Cast

from curriculum.models import Area, Pergunta, Resposta, Tarefa, TextoUnico
from reviews.models import ReviewerAssignment, Revisao
from workshop.models import Quadro


def get_reviewer_queryset(user):
    if not getattr(user, "is_authenticated", False):
        return Revisao.objects.none()
    cliente_id = getattr(user, "cliente_id", None)
    if not cliente_id:
        return Revisao.objects.none()

    assignments = ReviewerAssignment.objects.filter(cliente_id=cliente_id, reviewer_id=user.id)
    if not assignments.exists():
        return Revisao.objects.none()

    tarefa_ids: set[int] = set()
    etapas: set[str] = set()
    gt_ids: set[int] = set()

    for assignment in assignments:
        if assignment.scope_type == ReviewerAssignment.ScopeType.TRAIL:
            try:
                tarefa_ids.add(int(assignment.scope_id))
            except (TypeError, ValueError):
                continue
        elif assignment.scope_type == ReviewerAssignment.ScopeType.ETAPA:
            etapas.add(str(assignment.scope_id))
        elif assignment.scope_type == ReviewerAssignment.ScopeType.COMPONENTE:
            try:
                area_id = int(assignment.scope_id)
            except (TypeError, ValueError):
                continue
            area = Area.objects.filter(pk=area_id, cliente_id=cliente_id).first()
            if area:
                gt_ids.update(area.gts.values_list("id", flat=True))
        elif assignment.scope_type == ReviewerAssignment.ScopeType.PPP:
            # PPP trabalha com tarefas selecionadas; assumimos scope_id como tarefa.
            try:
                tarefa_ids.add(int(assignment.scope_id))
            except (TypeError, ValueError):
                continue

    if etapas:
        tarefa_ids.update(Tarefa.objects.filter(cliente_id=cliente_id, etapa__in=etapas).values_list("id", flat=True))

    respostas_qs = Resposta.objects.filter(cliente_id=cliente_id)
    textos_qs = TextoUnico.objects.filter(cliente_id=cliente_id)
    quadros_qs = Quadro.objects.filter(cliente_id=cliente_id)

    if tarefa_ids:
        perguntas_ids = Pergunta.objects.filter(tarefa_id__in=tarefa_ids).values_list("id", flat=True)
        respostas_qs = respostas_qs.filter(pergunta_id__in=perguntas_ids)
        textos_qs = textos_qs.filter(tarefa_id__in=tarefa_ids)
    if gt_ids:
        respostas_qs = respostas_qs.filter(gt_id__in=gt_ids)
        textos_qs = textos_qs.filter(gt_id__in=gt_ids)
        quadros_qs = quadros_qs.filter(gt_id__in=gt_ids)

    resposta_ids = respostas_qs.annotate(id_text=Cast("id", models.CharField())).values("id_text")
    texto_ids = textos_qs.annotate(id_text=Cast("id", models.CharField())).values("id_text")
    quadro_ids = quadros_qs.annotate(id_text=Cast("id", models.CharField())).values("id_text")

    return Revisao.objects.filter(cliente_id=cliente_id).filter(
        models.Q(alvo_tipo=Revisao.AlvoTipo.RESPOSTA, alvo_id__in=resposta_ids)
        | models.Q(alvo_tipo=Revisao.AlvoTipo.TEXTO_UNICO, alvo_id__in=texto_ids)
        | models.Q(alvo_tipo=Revisao.AlvoTipo.QUADRO, alvo_id__in=quadro_ids)
    )
