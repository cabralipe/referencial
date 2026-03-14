from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ava.models import (
    Atividade,
    AtividadeTentativa,
    Aula,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
)
from ava.services import AtividadeService, ProgressoService


def _aplicar_status_progresso_aulas(matricula, aulas):
    """Anexa atributo `progresso_concluido` nas aulas para uso em template."""
    aula_ids = [a.id for a in aulas]
    concluidas = set(
        ProgressoAula.objects.filter(
            matricula=matricula,
            aula_id__in=aula_ids,
            is_concluida=True,
        ).values_list("aula_id", flat=True)
    )
    for aula_item in aulas:
        aula_item.progresso_concluido = aula_item.id in concluidas
    return aulas


@login_required
def dashboard(request):
    """
    Dashboard do Aluno mostrando matriculas ativas e resumo.
    """
    matriculas = MatriculaCurso.objects.filter(aluno=request.user, status="ativa").select_related("curso")
    return render(request, "ava/student/dashboard.html", {"matriculas": matriculas})


@login_required
def curso_detalhe(request, slug):
    """
    Pagina do curso matriculado. Exibe os modulos e o progresso.
    """
    matricula = get_object_or_404(
        MatriculaCurso.objects.select_related("curso"),
        aluno=request.user,
        curso__slug=slug,
    )

    modulos = list(
        matricula.curso.modulos.filter(is_active=True)
        .order_by("ordem", "id")
        .prefetch_related(
            Prefetch(
                "aulas",
                queryset=Aula.objects.filter(is_active=True).order_by("ordem", "id"),
            )
        )
    )
    aulas = [aula for modulo in modulos for aula in modulo.aulas.all()]
    _aplicar_status_progresso_aulas(matricula, aulas)

    return render(
        request,
        "ava/student/curso.html",
        {
            "matricula": matricula,
            "curso": matricula.curso,
            "modulos": modulos,
        },
    )


@login_required
def acessar_aula(request, curso_slug, aula_id):
    """
    Pagina de consumo da aula (video, textos).
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    conteudos = aula.conteudos.all().order_by("ordem", "id")
    atividades = list(aula.atividades.all().order_by("titulo", "id"))

    modulos = list(
        matricula.curso.modulos.filter(is_active=True)
        .order_by("ordem", "id")
        .prefetch_related(
            Prefetch(
                "aulas",
                queryset=Aula.objects.filter(is_active=True).order_by("ordem", "id"),
            )
        )
    )
    aulas_ordenadas = [a for modulo in modulos for a in modulo.aulas.all()]

    # Marca a aula como iniciada / cria o progresso
    ProgressoService._garantir_progressos(matricula, aula)
    _aplicar_status_progresso_aulas(matricula, aulas_ordenadas)

    visualizados = set(
        ProgressoConteudo.objects.filter(
            progresso_aula__matricula=matricula,
            progresso_aula__aula=aula,
            is_visualizado=True,
        ).values_list("conteudo_id", flat=True)
    )
    for conteudo in conteudos:
        conteudo.is_visualizado = conteudo.id in visualizados

    atividade_ids = [atividade.id for atividade in atividades]
    atividades_enviadas = set(
        AtividadeTentativa.objects.filter(
            aluno=request.user,
            atividade_id__in=atividade_ids,
            status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA],
        ).values_list("atividade_id", flat=True)
    )
    for atividade in atividades:
        atividade.tentativas_existentes = atividade.id in atividades_enviadas

    aula_anterior = None
    proxima_aula = None
    for idx, aula_item in enumerate(aulas_ordenadas):
        if aula_item.id != aula.id:
            continue
        if idx > 0:
            aula_anterior = aulas_ordenadas[idx - 1]
        if idx + 1 < len(aulas_ordenadas):
            proxima_aula = aulas_ordenadas[idx + 1]
        break

    return render(
        request,
        "ava/student/aula.html",
        {
            "matricula": matricula,
            "aula": aula,
            "conteudos": conteudos,
            "atividades": atividades,
            "modulos": modulos,
            "aula_anterior": aula_anterior,
            "proxima_aula": proxima_aula,
        },
    )


@login_required
def marcar_conteudo(request, conteudo_id):
    """
    Endpoint para marcar conteudo como visualizado.
    """
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "/"))

    marcado = ProgressoService.marcar_conteudo_visualizado(request.user, conteudo_id)
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)

    if marcado:
        messages.success(request, "Conteudo marcado como lido.")
    else:
        messages.info(request, "Esse conteudo ja estava marcado como lido.")

    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER", "/"))


@login_required
def responder_atividade(request, curso_slug, aula_id, atividade_id):
    """
    Pagina de resposta da atividade/questionario.
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    atividade = get_object_or_404(Atividade, id=atividade_id, aula=aula)
    questoes = list(atividade.questoes.all().prefetch_related("alternativas"))
    usa_formulario_quiz = atividade.tipo in [Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO] or bool(questoes)

    tentativa_finalizada = (
        AtividadeTentativa.objects.filter(
            aluno=request.user,
            atividade=atividade,
            status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA],
        )
        .order_by("-data_envio", "-data_inicio")
        .first()
    )
    tentativas_finalizadas_count = AtividadeTentativa.objects.filter(
        aluno=request.user,
        atividade=atividade,
        status__in=[AtividadeTentativa.Status.ENVIADA, AtividadeTentativa.Status.CORRIGIDA],
    ).count()
    limite_atingido = (
        atividade.tentativas_permitidas > 0
        and tentativas_finalizadas_count >= atividade.tentativas_permitidas
    )
    tentativa_em_andamento = (
        AtividadeTentativa.objects.filter(
            aluno=request.user,
            atividade=atividade,
            status=AtividadeTentativa.Status.EM_ANDAMENTO,
        )
        .order_by("-data_inicio")
        .first()
    )

    if request.method == "POST":
        if limite_atingido and tentativa_em_andamento is None:
            messages.info(request, "Limite de tentativas alcancado para esta atividade.")
            return redirect(
                "ava:aluno_responder_atividade",
                curso_slug=curso_slug,
                aula_id=aula_id,
                atividade_id=atividade_id,
            )

        if atividade.tipo == Atividade.Tipo.ENVIO_ARQUIVO and not request.FILES.get("arquivo_enviado"):
            messages.error(request, "Essa atividade exige envio de arquivo.")
        elif usa_formulario_quiz and not questoes:
            messages.error(request, "Este quiz ainda nao possui questoes cadastradas.")
        else:
            tentativa = tentativa_em_andamento
            if tentativa is None:
                tentativa, erro = AtividadeService.iniciar_tentativa(request.user, atividade)
                if erro:
                    messages.warning(request, erro)
                    return redirect("ava:aluno_acessar_aula", curso_slug=curso_slug, aula_id=aula_id)

            if usa_formulario_quiz:
                dados_respostas = {k: v for k, v in request.POST.items() if k.isdigit()}
                AtividadeService.submeter_quiz(tentativa, dados_respostas)
                messages.success(request, "Questionario enviado com sucesso!")
            else:
                texto = request.POST.get("texto_resposta", "")
                arquivo = request.FILES.get("arquivo_enviado")
                AtividadeService.submeter_tarefa_discursiva(tentativa, texto, arquivo)
                messages.success(request, "Atividade enviada com sucesso!")

            return redirect(
                "ava:aluno_responder_atividade",
                curso_slug=curso_slug,
                aula_id=aula_id,
                atividade_id=atividade_id,
            )

    tentativa = tentativa_finalizada or tentativa_em_andamento

    return render(
        request,
        "ava/student/atividade.html",
        {
            "curso": matricula.curso,
            "aula": aula,
            "atividade": atividade,
            "questoes": questoes,
            "usa_formulario_quiz": usa_formulario_quiz,
            "tentativa": tentativa,
        },
    )
