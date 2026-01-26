"""Serviços para cálculo de progresso e próxima missão."""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Prefetch

from core.utils import usuario_e_membro_do_gt
from curriculum.models import GT, Pergunta, Resposta, Tarefa
from reviews.models import Revisao


@dataclass(frozen=True)
class NextBlock:
    gt_id: int
    tarefa_id: int
    pergunta_id: int
    resposta_id: int | None
    status: str


_STATUS_PRIORITY = {
    "devolvido": 0,
    "em_andamento": 1,
    "nao_iniciado": 2,
    "em_revisao": 3,
    "concluido": 4,
}


def _status_for_block(resposta: Resposta | None, revisao_status: str | None) -> str:
    if revisao_status == Revisao.Status.REPROVADO:
        return "devolvido"
    if revisao_status == Revisao.Status.APROVADO:
        return "concluido"
    if revisao_status == Revisao.Status.EM_REVISAO:
        return "em_revisao"
    if resposta and (resposta.conteudo_html or "").strip():
        return "em_andamento"
    return "nao_iniciado"


def get_next_block_for_user(user) -> NextBlock | None:
    if not getattr(user, "is_authenticated", False):
        return None

    gt_ids = list(GT.objects.filter(membros=user).values_list("id", flat=True))
    if not gt_ids:
        return None

    cliente_id = getattr(user, "cliente_id", None)
    tarefas = (
        Tarefa.objects.filter(cliente_id=cliente_id)
        .prefetch_related(Prefetch("perguntas", queryset=Pergunta.objects.prefetch_related("gts")))
        .order_by("ordem")
    )
    respostas = Resposta.objects.select_related("pergunta", "pergunta__tarefa").filter(
        gt_id__in=gt_ids,
        pergunta__tarefa__in=tarefas,
    )
    respostas_map = {(resp.gt_id, resp.pergunta_id): resp for resp in respostas}

    revisoes = Revisao.objects.filter(
        cliente_id=cliente_id,
        alvo_tipo=Revisao.AlvoTipo.RESPOSTA,
        alvo_id__in=[str(resp.id) for resp in respostas],
    ).order_by("-updated_at")
    revisao_map: dict[int, str] = {}
    for rev in revisoes:
        resposta_id = int(rev.alvo_id)
        if resposta_id not in revisao_map:
            revisao_map[resposta_id] = rev.status

    best: NextBlock | None = None
    best_priority = 99

    for tarefa in tarefas:
        for pergunta in tarefa.perguntas.all().order_by("ordem"):
            for gt_id in gt_ids:
                if not usuario_e_membro_do_gt(user, gt_id):
                    continue
                if pergunta.gts.exists() and not pergunta.gts.filter(pk=gt_id).exists():
                    continue
                resposta = respostas_map.get((gt_id, pergunta.id))
                revisao_status = revisao_map.get(getattr(resposta, "id", 0))
                status = _status_for_block(resposta, revisao_status)
                priority = _STATUS_PRIORITY.get(status, 99)
                if priority < best_priority:
                    best_priority = priority
                    best = NextBlock(
                        gt_id=gt_id,
                        tarefa_id=tarefa.id,
                        pergunta_id=pergunta.id,
                        resposta_id=getattr(resposta, "id", None),
                        status=status,
                    )
                if best_priority == 0:
                    return best

    if best and best.status == "concluido":
        return None
    return best
