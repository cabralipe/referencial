from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from ava.forms import AtividadeForumMensagemForm
from ava.models import (
    Atividade,
    AtividadeForumMensagem,
    AtividadeTentativa,
    Aula,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
)
from ava.services import AtividadeService, ProgressoService


FINALIZED_ATTEMPT_STATUSES = [
    AtividadeTentativa.Status.ENVIADA,
    AtividadeTentativa.Status.CORRIGIDA,
]


def _nome_usuario(usuario):
    return usuario.get_full_name() or getattr(usuario, "nome", "") or usuario.email


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


def _forum_messages_queryset(atividade: Atividade):
    return (
        AtividadeForumMensagem.objects.filter(atividade=atividade)
        .select_related("autor", "resposta_para__autor")
        .prefetch_related("anexos")
        .order_by("created_at", "id")
    )


def _montar_resultado_quiz(tentativa, questoes):
    if not tentativa or not questoes:
        return []

    respostas = {
        resposta.questao_id: resposta
        for resposta in tentativa.respostas_quiz.select_related(
            "questao",
            "alternativa_selecionada",
        )
    }
    resultados = []

    for questao in questoes:
        alternativas = list(questao.alternativas.all())
        resposta = respostas.get(questao.id)
        alternativa_correta = next((alternativa for alternativa in alternativas if alternativa.is_correta), None)
        alternativa_selecionada = resposta.alternativa_selecionada if resposta else None
        is_correta = bool(resposta and resposta.is_correta)

        feedback = ""
        if resposta:
            if alternativa_selecionada and alternativa_selecionada.feedback_especifico:
                feedback = alternativa_selecionada.feedback_especifico
            elif is_correta:
                feedback = questao.feedback_acerto or "Resposta correta."
            else:
                feedback = questao.feedback_erro or "Resposta incorreta. Revise o conteudo da aula e tente relacionar a questao ao material estudado."

        resultados.append(
            {
                "questao": questao,
                "resposta": resposta,
                "alternativa_selecionada": alternativa_selecionada,
                "alternativa_correta": alternativa_correta,
                "is_correta": is_correta,
                "nota_item": resposta.nota_item if resposta else 0,
                "feedback": feedback,
            }
        )

    return resultados


@login_required
def dashboard(request):
    """
    Dashboard do aluno mostrando cursos em andamento e concluidos.
    """
    matriculas = list(
        MatriculaCurso.objects.filter(
            aluno=request.user,
            status__in=[MatriculaCurso.Status.ATIVA, MatriculaCurso.Status.CONCLUIDA],
        ).select_related("curso")
    )
    for matricula in matriculas:
        ProgressoService.sincronizar_matricula(matricula)
    matriculas_em_andamento = [matricula for matricula in matriculas if matricula.status == MatriculaCurso.Status.ATIVA]
    matriculas_concluidas = [matricula for matricula in matriculas if matricula.status == MatriculaCurso.Status.CONCLUIDA]
    return render(
        request,
        "ava/student/dashboard.html",
        {
            "matriculas_em_andamento": matriculas_em_andamento,
            "matriculas_concluidas": matriculas_concluidas,
        },
    )


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
    ProgressoService.sincronizar_matricula(matricula)

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
    ProgressoService.sincronizar_matricula(matricula)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    ProgressoService.marcar_aula_visualizada(matricula, aula)
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
    ProgressoService.sincronizar_matricula(matricula)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    atividade = get_object_or_404(Atividade, id=atividade_id, aula=aula)

    questoes = list(atividade.questoes.all().prefetch_related("alternativas"))
    is_forum = atividade.tipo == Atividade.Tipo.FORUM
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
    tentativa_em_andamento = (
        AtividadeTentativa.objects.filter(
            aluno=request.user,
            atividade=atividade,
            status=AtividadeTentativa.Status.EM_ANDAMENTO,
        )
        .order_by("-data_inicio")
        .first()
    )
    tentativa = tentativa_finalizada or tentativa_em_andamento

    forum_form = AtividadeForumMensagemForm(request.POST or None) if is_forum else None
    forum_messages = list(_forum_messages_queryset(atividade)) if is_forum else []
    forum_participantes = len({mensagem.autor_id for mensagem in forum_messages}) if is_forum else 0

    tentativas_finalizadas_count = AtividadeTentativa.objects.filter(
        aluno=request.user,
        atividade=atividade,
        status__in=FINALIZED_ATTEMPT_STATUSES,
    ).count()
    limite_atingido = (
        atividade.tentativas_permitidas > 0
        and tentativas_finalizadas_count >= atividade.tentativas_permitidas
    )

    if request.method == "POST":
        if is_forum:
            arquivos = request.FILES.getlist("arquivos")
            if forum_form.is_valid():
                resposta_para_id = forum_form.cleaned_data.get("resposta_para")
                resposta_para = None
                if resposta_para_id:
                    resposta_para = atividade.mensagens_forum.select_related("autor").filter(pk=resposta_para_id).first()
                    if resposta_para is None:
                        messages.error(request, "Não foi possível localizar a mensagem que você tentou responder.")
                        return redirect(
                            "ava:aluno_responder_atividade",
                            curso_slug=curso_slug,
                            aula_id=aula_id,
                            atividade_id=atividade_id,
                        )
                try:
                    AtividadeService.publicar_mensagem_forum(
                        aluno=request.user,
                        atividade=atividade,
                        texto=forum_form.cleaned_data["mensagem"],
                        arquivos=arquivos,
                        resposta_para=resposta_para,
                    )
                    messages.success(request, "Tarefa concluída com sucesso. Mensagem publicada no fórum.")
                    return redirect(f"{request.path}#forum-thread")
                except ValueError as exc:
                    messages.error(request, str(exc))
            else:
                messages.error(request, "Não foi possível publicar a mensagem. Revise os campos do formulário.")
        else:
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
                messages.error(request, "Este quiz ainda não possui questões cadastradas.")
            else:
                tentativa_processada = tentativa_em_andamento
                if tentativa_processada is None:
                    tentativa_processada, erro = AtividadeService.iniciar_tentativa(request.user, atividade)
                    if erro:
                        messages.warning(request, erro)
                        return redirect("ava:aluno_acessar_aula", curso_slug=curso_slug, aula_id=aula_id)

                if usa_formulario_quiz:
                    dados_respostas = {k: v for k, v in request.POST.items() if k.isdigit()}
                    AtividadeService.submeter_quiz(tentativa_processada, dados_respostas)
                    messages.success(request, "Tarefa concluida com sucesso.")
                else:
                    texto = request.POST.get("texto_resposta", "")
                    arquivo = request.FILES.get("arquivo_enviado")
                    AtividadeService.submeter_tarefa_discursiva(tentativa_processada, texto, arquivo)
                    messages.success(request, "Tarefa concluida com sucesso.")

                return redirect(
                    "ava:aluno_responder_atividade",
                    curso_slug=curso_slug,
                    aula_id=aula_id,
                    atividade_id=atividade_id,
                )

    quiz_resultados = []
    if tentativa and tentativa.status in FINALIZED_ATTEMPT_STATUSES and usa_formulario_quiz:
        quiz_resultados = _montar_resultado_quiz(tentativa, questoes)

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
            "is_forum": is_forum,
            "forum_form": forum_form,
            "forum_messages": forum_messages,
            "forum_total_mensagens": len(forum_messages),
            "forum_total_participantes": forum_participantes,
            "quiz_resultados": quiz_resultados,
        },
    )


@login_required
def baixar_comprovante_atividade(request, tentativa_id):
    tentativa = get_object_or_404(
        AtividadeTentativa.objects.select_related(
            "aluno",
            "atividade__aula__modulo__curso",
        ),
        id=tentativa_id,
        aluno=request.user,
        status__in=FINALIZED_ATTEMPT_STATUSES,
    )

    atividade = tentativa.atividade
    aula = atividade.aula
    modulo = aula.modulo
    curso = modulo.curso
    data_envio = tentativa.data_envio or tentativa.data_correcao or tentativa.data_inicio
    data_envio_local = timezone.localtime(data_envio)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, altura = A4
    margem_x = 24 * mm
    y = altura - 28 * mm

    pdf.setTitle(f"Comprovante de atividade {tentativa.id}")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margem_x, y, "Comprovante de tarefa concluida")

    y -= 12 * mm
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margem_x, y, "Este documento comprova o envio/conclusão da tarefa no módulo AVA.")

    y -= 14 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margem_x, y, "Dados do aluno")
    y -= 8 * mm
    pdf.setFont("Helvetica", 10)

    linhas = [
        ("Aluno", _nome_usuario(tentativa.aluno)),
        ("E-mail", tentativa.aluno.email),
        ("Curso", curso.titulo),
        ("Modulo", modulo.titulo),
        ("Aula", aula.titulo),
        ("Tarefa", atividade.titulo),
        ("Tipo", atividade.get_tipo_display()),
        ("Status", tentativa.get_status_display()),
        ("Data de envio", data_envio_local.strftime("%d/%m/%Y %H:%M")),
        ("Protocolo", f"AVA-{tentativa.id:08d}"),
    ]

    if tentativa.nota_obtida is not None:
        linhas.append(("Nota", f"{tentativa.nota_obtida} / {atividade.nota_maxima}"))

    for rotulo, valor in linhas:
        if y < 32 * mm:
            pdf.showPage()
            y = altura - 28 * mm
            pdf.setFont("Helvetica", 10)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(margem_x, y, f"{rotulo}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margem_x + 34 * mm, y, str(valor)[:110])
        y -= 7 * mm

    y -= 6 * mm
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        margem_x,
        y,
        f"Emitido em {timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')} pelo AVA PROLUC.",
    )
    pdf.showPage()
    pdf.save()

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="comprovante-atividade-{tentativa.id}.pdf"'
    return response
