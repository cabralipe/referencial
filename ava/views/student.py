from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
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
from ava.services.access_control import course_eixo_block_message, user_can_access_course_by_eixo


FINALIZED_ATTEMPT_STATUSES = [
    AtividadeTentativa.Status.ENVIADA,
    AtividadeTentativa.Status.CORRIGIDA,
]

_AVA_MANAGER_ROLES = {"admin_cliente", "articulador", "revisor", "super_admin"}
_MATERIAL_TIPOS = {"pdf", "arquivo", "apresentacao"}


def _is_ava_manager(user) -> bool:
    return getattr(user, "role", None) in _AVA_MANAGER_ROLES


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
                feedback = questao.feedback_erro or "Resposta incorreta. Revise o conteúdo da aula e tente relacionar a questão ao material estudado."

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
    Dashboard do aluno mostrando cursos em andamento e concluídos.
    """
    matriculas = list(
        MatriculaCurso.objects.filter(
            aluno=request.user,
            status__in=[MatriculaCurso.Status.ATIVA, MatriculaCurso.Status.CONCLUIDA],
        ).select_related("curso")
    )
    matriculas = [matricula for matricula in matriculas if user_can_access_course_by_eixo(request.user, matricula.curso)]
    for matricula in matriculas:
        ProgressoService.sincronizar_matricula(matricula)
    matriculas_em_andamento = [matricula for matricula in matriculas if matricula.status == MatriculaCurso.Status.ATIVA]
    matriculas_concluidas = [matricula for matricula in matriculas if matricula.status == MatriculaCurso.Status.CONCLUIDA]

    aulas_concluidas_por_matricula = {}
    for matricula in matriculas_em_andamento:
        aulas_concluidas_por_matricula[matricula.id] = set(
            ProgressoAula.objects.filter(matricula=matricula, is_concluida=True)
            .values_list("aula_id", flat=True)
        )

    for matricula in matriculas_em_andamento:
        modulos = list(
            matricula.curso.modulos.filter(is_active=True)
            .order_by("ordem", "id")
            .prefetch_related(
                Prefetch("aulas", queryset=Aula.objects.filter(is_active=True).order_by("ordem", "id"))
            )
        )
        modulos = ProgressoService.filtrar_modulos_disponiveis(matricula, modulos)
        concluidas = aulas_concluidas_por_matricula.get(matricula.id, set())
        matricula.proxima_aula = None
        for modulo in modulos:
            for aula in modulo.aulas.all():
                if aula.id not in concluidas:
                    matricula.proxima_aula = aula
                    break
            if matricula.proxima_aula:
                break

    return render(
        request,
        "ava/student/dashboard.html",
        {
            "matriculas_em_andamento": matriculas_em_andamento,
            "matriculas_concluidas": matriculas_concluidas,
        },
    )


def _motivo_bloqueio_modulo(matricula, modulo, agora=None):
    """Retorna string descritiva do motivo do bloqueio, ou None se disponível."""
    if not modulo.is_active:
        return None  # inativo, não mostrar para aluno

    agora = agora or timezone.now()
    if modulo.data_liberacao_programada and modulo.data_liberacao_programada > agora:
        return f"Disponível a partir de {modulo.data_liberacao_programada.astimezone().strftime('%d/%m/%Y às %H:%M')}"

    if modulo.pre_requisito_modulo_id:
        pre_req = modulo.pre_requisito_modulo
        titulo_prereq = pre_req.titulo if pre_req else "módulo anterior"
        return f"Requer conclusão de: {titulo_prereq}"

    return None


@login_required
def curso_detalhe(request, slug):
    """
    Página do curso matriculado. Exibe os módulos e o progresso.
    """
    matricula = get_object_or_404(
        MatriculaCurso.objects.select_related("curso"),
        aluno=request.user,
        curso__slug=slug,
    )
    if not user_can_access_course_by_eixo(request.user, matricula.curso):
        messages.warning(request, course_eixo_block_message(matricula.curso))
        return redirect("ava:catalogo")
    ProgressoService.sincronizar_matricula(matricula)

    is_manager = _is_ava_manager(request.user)
    modulos_bloqueados = []
    if is_manager:
        modulos = list(
            matricula.curso.modulos.order_by("ordem", "id")
            .prefetch_related(
                Prefetch(
                    "aulas",
                    queryset=Aula.objects.order_by("ordem", "id"),
                )
            )
        )
    else:
        todos_modulos = list(
            matricula.curso.modulos.filter(is_active=True)
            .select_related("pre_requisito_modulo")
            .order_by("ordem", "id")
            .prefetch_related(
                Prefetch(
                    "aulas",
                    queryset=Aula.objects.filter(is_active=True).order_by("ordem", "id"),
                )
            )
        )
        agora = timezone.now()
        modulos = ProgressoService.filtrar_modulos_disponiveis(matricula, todos_modulos, agora)
        for modulo in todos_modulos:
            if modulo in modulos:
                continue
            motivo = _motivo_bloqueio_modulo(matricula, modulo, agora)
            if motivo:
                modulos_bloqueados.append({"modulo": modulo, "motivo": motivo})

    total_modulos = len(modulos) + len(modulos_bloqueados)
    aulas = [aula for modulo in modulos for aula in modulo.aulas.all()]
    _aplicar_status_progresso_aulas(matricula, aulas)

    return render(
        request,
        "ava/student/curso.html",
        {
            "matricula": matricula,
            "curso": matricula.curso,
            "modulos": modulos,
            "modulos_bloqueados": modulos_bloqueados,
            "total_modulos": total_modulos,
            "is_manager": is_manager,
        },
    )


@login_required
def acessar_aula(request, curso_slug, aula_id):
    """
    Página de consumo da aula (video, textos).
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    if not user_can_access_course_by_eixo(request.user, matricula.curso):
        messages.warning(request, course_eixo_block_message(matricula.curso))
        return redirect("ava:catalogo")
    ProgressoService.sincronizar_matricula(matricula)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    is_manager = _is_ava_manager(request.user)
    if not is_manager and not ProgressoService.modulo_disponivel(matricula, aula.modulo):
        messages.warning(request, "Este modulo ainda nao esta disponivel.")
        return redirect("ava:aluno_curso_detalhe", slug=curso_slug)

    ProgressoService.marcar_aula_visualizada(matricula, aula)
    conteudos = list(aula.conteudos.all().order_by("ordem", "id"))
    atividades = list(aula.atividades.all().order_by("titulo", "id"))

    if is_manager:
        modulos = list(
            matricula.curso.modulos.order_by("ordem", "id")
            .prefetch_related(
                Prefetch(
                    "aulas",
                    queryset=Aula.objects.order_by("ordem", "id"),
                )
            )
        )
    else:
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
        modulos = ProgressoService.filtrar_modulos_disponiveis(matricula, modulos)
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

    conteudos_materiais = [c for c in conteudos if c.tipo in _MATERIAL_TIPOS]
    conteudos_outros = [c for c in conteudos if c.tipo not in _MATERIAL_TIPOS]

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
            "conteudos_outros": conteudos_outros,
            "conteudos_materiais": conteudos_materiais,
            "atividades": atividades,
            "modulos": modulos,
            "aula_anterior": aula_anterior,
            "proxima_aula": proxima_aula,
            "is_manager": is_manager,
        },
    )


@login_required
def marcar_conteudo(request, conteudo_id):
    """
    Endpoint para marcar conteúdo como visualizado.
    """
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER", "/"))

    marcado = ProgressoService.marcar_conteudo_visualizado(request.user, conteudo_id)
    if request.headers.get("HX-Request"):
        return HttpResponse(status=204)

    if marcado:
        messages.success(request, "Conteúdo marcado como lido.")
    else:
        messages.info(request, "Esse conteúdo já estava marcado como lido.")

    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER", "/"))


@login_required
def responder_atividade(request, curso_slug, aula_id, atividade_id):
    """
    Página de resposta da atividade/questionario.
    """
    matricula = get_object_or_404(MatriculaCurso, aluno=request.user, curso__slug=curso_slug)
    if not user_can_access_course_by_eixo(request.user, matricula.curso):
        messages.warning(request, course_eixo_block_message(matricula.curso))
        return redirect("ava:catalogo")
    ProgressoService.sincronizar_matricula(matricula)
    aula = get_object_or_404(Aula, id=aula_id, modulo__curso=matricula.curso)
    if not ProgressoService.modulo_disponivel(matricula, aula.modulo):
        messages.warning(request, "Este modulo ainda nao esta disponivel.")
        return redirect("ava:aluno_curso_detalhe", slug=curso_slug)

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
        .prefetch_related("arquivos")
        .order_by("-data_envio", "-data_inicio")
        .first()
    )
    tentativa_em_andamento = (
        AtividadeTentativa.objects.filter(
            aluno=request.user,
            atividade=atividade,
            status=AtividadeTentativa.Status.EM_ANDAMENTO,
        )
        .prefetch_related("arquivos")
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
                messages.info(request, "Limite de tentativas alcançado para esta atividade.")
                return redirect(
                    "ava:aluno_responder_atividade",
                    curso_slug=curso_slug,
                    aula_id=aula_id,
                    atividade_id=atividade_id,
                )

            arquivos_enviados = request.FILES.getlist("arquivos_enviados")
            if atividade.tipo == Atividade.Tipo.ENVIO_ARQUIVO and not arquivos_enviados:
                messages.error(request, "Essa atividade exige envio de pelo menos um arquivo.")
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
                    messages.success(request, "Tarefa concluída com sucesso.")
                else:
                    texto = request.POST.get("texto_resposta", "")
                    AtividadeService.submeter_tarefa_discursiva(tentativa_processada, texto, arquivos_enviados or None)
                    messages.success(request, "Tarefa concluída com sucesso.")

                url = reverse(
                    "ava:aluno_responder_atividade",
                    kwargs={"curso_slug": curso_slug, "aula_id": aula_id, "atividade_id": atividade_id},
                )
                return HttpResponseRedirect(url + "#resultado")

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
    pdf.drawString(margem_x, y, "Comprovante de tarefa concluída")

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
        ("Módulo", modulo.titulo),
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
