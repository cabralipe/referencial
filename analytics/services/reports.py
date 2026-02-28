"""Agregacoes para dashboards municipal e do usuario."""

from django.db.models import Avg, Count

from bank.models import PlanoPublicado
from courses.models import AvaliacaoPlano, CursoCertificadoEmitido, CursoProgresso, PlanoAula


def user_dashboard(cliente_id: int, usuario_id: int) -> dict:
    cursos_ativos = CursoProgresso.objects.filter(cliente_id=cliente_id, usuario_id=usuario_id).count()
    percentual_medio = (
        CursoProgresso.objects.filter(cliente_id=cliente_id, usuario_id=usuario_id).aggregate(avg=Avg("percentual"))["avg"]
        or 0
    )
    planos_enviados = PlanoAula.objects.filter(
        cliente_id=cliente_id,
        autor_id=usuario_id,
        status__in=[PlanoAula.Status.EM_REVISAO, PlanoAula.Status.APROVADO, PlanoAula.Status.PUBLICADO],
    ).count()
    certificados = CursoCertificadoEmitido.objects.filter(cliente_id=cliente_id, usuario_id=usuario_id).count()
    return {
        "cursos_ativos": cursos_ativos,
        "percentual_concluido_medio": round(float(percentual_medio), 2),
        "planos_enviados": planos_enviados,
        "certificados_emitidos": certificados,
    }


def admin_dashboard(cliente_id: int) -> dict:
    por_escola = list(
        PlanoAula.objects.filter(cliente_id=cliente_id)
        .values("escola")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    por_componente = list(
        PlanoAula.objects.filter(cliente_id=cliente_id)
        .values("componente_curricular")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    media_rubrica = (
        AvaliacaoPlano.objects.filter(cliente_id=cliente_id).aggregate(avg=Avg("pontuacao"))["avg"] or 0
    )
    planos_publicados = PlanoPublicado.objects.filter(cliente_id=cliente_id).count()
    certificados_emitidos = CursoCertificadoEmitido.objects.filter(cliente_id=cliente_id).count()
    return {
        "engajamento_por_escola": por_escola,
        "producao_por_componente": por_componente,
        "media_avaliacao_rubrica": round(float(media_rubrica), 2),
        "planos_publicados": planos_publicados,
        "certificados_emitidos": certificados_emitidos,
    }

