"""Agregacoes para dashboards municipal e do usuario."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from bank.models import PlanoPublicado
from courses.models import AvaliacaoPlano, CursoCertificadoEmitido, CursoProgresso, PlanoAula


def _clean_label(value: str | None, fallback: str = "Nao informado") -> str:
    cleaned = (value or "").strip()
    return cleaned or fallback


def user_dashboard(cliente_id: int, usuario_id: int) -> dict:
    progresso_qs = CursoProgresso.objects.filter(cliente_id=cliente_id, usuario_id=usuario_id)
    cursos_ativos = progresso_qs.count()
    percentual_medio = (
        progresso_qs.aggregate(avg=Avg("percentual"))["avg"] or 0
    )
    cursos_concluidos = progresso_qs.filter(percentual__gte=100).count()
    cursos_em_andamento = max(cursos_ativos - cursos_concluidos, 0)

    planos_qs = PlanoAula.objects.filter(
        cliente_id=cliente_id,
        autor_id=usuario_id,
    )
    planos_enviados = planos_qs.filter(
        status__in=[PlanoAula.Status.EM_REVISAO, PlanoAula.Status.APROVADO, PlanoAula.Status.PUBLICADO]
    ).count()
    planos_por_status = list(
        planos_qs.values("status").annotate(total=Count("id")).order_by("-total", "status")
    )
    media_rubrica_autor = (
        AvaliacaoPlano.objects.filter(cliente_id=cliente_id, plano__autor_id=usuario_id).aggregate(avg=Avg("pontuacao"))["avg"]
        or 0
    )
    certificados = CursoCertificadoEmitido.objects.filter(cliente_id=cliente_id, usuario_id=usuario_id).count()
    return {
        "cursos_ativos": cursos_ativos,
        "cursos_concluidos": cursos_concluidos,
        "cursos_em_andamento": cursos_em_andamento,
        "percentual_concluido_medio": round(float(percentual_medio), 2),
        "planos_enviados": planos_enviados,
        "planos_por_status": planos_por_status,
        "media_avaliacao_planos": round(float(media_rubrica_autor), 2),
        "certificados_emitidos": certificados,
    }


def admin_dashboard(cliente_id: int) -> dict:
    planos_qs = PlanoAula.objects.filter(cliente_id=cliente_id)

    por_escola = list(
        planos_qs.values("escola")
        .annotate(total=Count("id"))
        .order_by("-total", "escola")[:10]
    )
    por_escola = [
        {"escola": _clean_label(item.get("escola")), "total": item["total"]}
        for item in por_escola
    ]

    por_componente = list(
        planos_qs.values("componente_curricular")
        .annotate(total=Count("id"))
        .order_by("-total", "componente_curricular")[:10]
    )
    por_componente = [
        {"componente_curricular": _clean_label(item.get("componente_curricular")), "total": item["total"]}
        for item in por_componente
    ]

    por_etapa = list(
        planos_qs.values("etapa_modalidade")
        .annotate(total=Count("id"))
        .order_by("-total", "etapa_modalidade")[:10]
    )
    por_etapa = [
        {"etapa_modalidade": _clean_label(item.get("etapa_modalidade")), "total": item["total"]}
        for item in por_etapa
    ]

    por_status = list(
        planos_qs.values("status")
        .annotate(total=Count("id"))
        .order_by("-total", "status")
    )
    por_status = [
        {"status": _clean_label(item.get("status")), "total": item["total"]}
        for item in por_status
    ]

    top_autores = list(
        planos_qs.values("autor_id", "autor__nome", "autor__email")
        .annotate(total=Count("id"))
        .order_by("-total", "autor__nome")[:10]
    )
    top_autores = [
        {
            "autor_id": item["autor_id"],
            "nome": _clean_label(item.get("autor__nome"), fallback="Sem nome"),
            "email": _clean_label(item.get("autor__email"), fallback="-"),
            "total": item["total"],
        }
        for item in top_autores
    ]

    now = timezone.now()
    cutoff_30_days = now - timedelta(days=30)
    producao_mensal = list(
        planos_qs.filter(created_at__gte=now - timedelta(days=180))
        .annotate(mes=TruncMonth("created_at"))
        .values("mes")
        .annotate(total=Count("id"))
        .order_by("mes")
    )
    producao_mensal = [
        {
            "mes": item["mes"].strftime("%Y-%m"),
            "total": item["total"],
        }
        for item in producao_mensal
        if item.get("mes")
    ]

    media_rubrica = (
        AvaliacaoPlano.objects.filter(cliente_id=cliente_id).aggregate(avg=Avg("pontuacao"))["avg"] or 0
    )
    total_avaliacoes = AvaliacaoPlano.objects.filter(cliente_id=cliente_id).count()

    progresso_qs = CursoProgresso.objects.filter(cliente_id=cliente_id)
    progresso_medio_cursos = progresso_qs.aggregate(avg=Avg("percentual"))["avg"] or 0
    cursos_concluidos = progresso_qs.filter(percentual__gte=100).count()
    cursos_em_andamento = progresso_qs.filter(percentual__lt=100).count()

    planos_publicados = PlanoPublicado.objects.filter(cliente_id=cliente_id).count()
    curadoria_por_status = list(
        PlanoPublicado.objects.filter(cliente_id=cliente_id)
        .values("status_curadoria")
        .annotate(total=Count("id"))
        .order_by("-total", "status_curadoria")
    )
    curadoria_por_status = [
        {"status_curadoria": _clean_label(item.get("status_curadoria")), "total": item["total"]}
        for item in curadoria_por_status
    ]

    certificados_emitidos = CursoCertificadoEmitido.objects.filter(cliente_id=cliente_id).count()

    total_planos = planos_qs.count()
    autores_ativos = planos_qs.values("autor_id").distinct().count()

    return {
        "engajamento_por_escola": por_escola,
        "producao_por_componente": por_componente,
        "producao_por_etapa": por_etapa,
        "producao_por_status": por_status,
        "top_autores": top_autores,
        "producao_mensal": producao_mensal,
        "curadoria_por_status": curadoria_por_status,
        "media_avaliacao_rubrica": round(float(media_rubrica), 2),
        "media_progresso_cursos": round(float(progresso_medio_cursos), 2),
        "total_avaliacoes": total_avaliacoes,
        "cursos_concluidos": cursos_concluidos,
        "cursos_em_andamento": cursos_em_andamento,
        "planos_publicados": planos_publicados,
        "certificados_emitidos": certificados_emitidos,
        "totais": {
            "total_planos": total_planos,
            "planos_ultimos_30_dias": planos_qs.filter(created_at__gte=cutoff_30_days).count(),
            "autores_ativos": autores_ativos,
        },
    }
