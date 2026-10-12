"""Salas de trabalho dos GTs do Referencial (experiência no AVA).

Toda autorização é resolvida no servidor por ``ava.services.gt_access``: as
views pedem a capacidade antes de agir e o template apenas reflete o que já foi
decidido. Esconder botão não é controle de acesso.
"""

from __future__ import annotations

import mimetypes
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ava.forms_gt import (
    AtaGTForm,
    CicloReferencialForm,
    DiagnosticoGTForm,
    EstrategiaGTForm,
    GerarSalasForm,
    ImportacaoObjetivosForm,
    InscricaoManualForm,
    JustificativaForm,
    MetaGTForm,
    ModeloAtaGTForm,
    ObjetivoReferencialForm,
    ParecerRevisaoForm,
    QuadroObjetivoGTForm,
    ReuniaoGTForm,
    SalaGTForm,
    SituacaoSalaForm,
)
from ava.models.gt_sala import (
    AtaReuniaoGT,
    CicloReferencial,
    EstrategiaGT,
    InscricaoSalaGT,
    MetaGT,
    ModeloAtaGT,
    ObjetivoReferencial,
    PresencaReuniaoGT,
    ReuniaoGT,
    SalaGT,
    TrabalhoGT,
    VersaoTrabalhoGT,
)
from ava.services.audit_service import AVAAuditService
from ava.services.gt_comentario_service import ComentarioGTService
from ava.services.gt_access import (
    ROLES_ADMIN_REFERENCIAL,
    acesso_a_sala,
    e_admin_referencial,
    pode_ver_conteudo,
    salas_do_catalogo,
    tem_visao_global,
)
from ava.services.gt_documento_service import DocumentoGTService, resumo_frequencia_pessoal
from ava.services.gt_reuniao_service import (
    AtaGTService,
    ModeloAtaGTService,
    ReuniaoGTService,
)
from ava.services.gt_sala_service import SalaGTService
from ava.services.gt_trabalho_service import TrabalhoGTService
from ava.services.gt_tutorial_service import NOME_CICLO_EXEMPLO, TutorialGTService
from exports.models import ExportJob


PAGINA_TAMANHO = 20


# ----------------------------------------------------------------------
# Helpers de escopo e permissão
# ----------------------------------------------------------------------


def gt_required(view_func):
    """Área acessível a qualquer usuário autenticado com município no AVA."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.get_ava_clientes_queryset().exists():
            raise PermissionDenied("Nenhum município está disponível para este usuário.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def gt_admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(request.user, "role", None) not in ROLES_ADMIN_REFERENCIAL:
            raise PermissionDenied(
                "Apenas a administração do Referencial acessa esta configuração."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def _parse_int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _cliente_ids(user) -> list[int]:
    return list(user.get_ava_clientes_queryset().values_list("id", flat=True))


def _cliente_atual(request):
    permitidos = request.user.get_ava_clientes_queryset()
    cliente_id = _parse_int(request.POST.get("municipio") or request.GET.get("municipio"))
    if cliente_id:
        return get_object_or_404(permitidos, pk=cliente_id)
    cliente = permitidos.first()
    if cliente is None:
        raise PermissionDenied("Nenhum município está disponível para este usuário.")
    return cliente


def _obter_sala(request, sala_id) -> SalaGT:
    return get_object_or_404(
        SalaGT.raw_objects.filter(
            is_deleted=False, cliente_id__in=_cliente_ids(request.user)
        ).select_related("cliente", "ciclo", "objetivo", "gt"),
        pk=sala_id,
    )


def _obter_reuniao(request, reuniao_id) -> ReuniaoGT:
    return get_object_or_404(
        ReuniaoGT.raw_objects.filter(
            is_deleted=False, cliente_id__in=_cliente_ids(request.user)
        ).select_related("sala__ciclo", "sala__objetivo", "sala__gt", "responsavel_registro"),
        pk=reuniao_id,
    )


def _ciclo_atual(request, cliente):
    ciclo_id = _parse_int(request.GET.get("ciclo") or request.POST.get("ciclo"))
    ciclos = CicloReferencial.raw_objects.filter(
        is_deleted=False, cliente=cliente
    ).order_by("-ativo", "-inicio", "nome")
    if ciclo_id:
        return get_object_or_404(ciclos, pk=ciclo_id), ciclos
    return ciclos.filter(ativo=True).first() or ciclos.first(), ciclos


def _contexto_base(request, cliente) -> dict:
    return {
        "cliente_atual": cliente,
        "municipios_ava": request.user.get_ava_clientes_queryset(),
        "pode_gerir_multiplos_avas": request.user.get_ava_clientes_queryset().count() > 1,
        "e_admin_referencial": e_admin_referencial(request.user),
        "tem_visao_global": tem_visao_global(request.user),
    }


def _mensagens_de_erro(request, exc: ValidationError) -> None:
    for mensagem in getattr(exc, "messages", [str(exc)]):
        messages.error(request, mensagem)


def _mensagens_do_form(request, form) -> None:
    for campo, erros in form.errors.items():
        rotulo = form.fields[campo].label if campo in form.fields else ""
        for erro in erros:
            messages.error(request, f"{rotulo}: {erro}" if rotulo else erro)


def _redirecionar(request, fallback: str, **kwargs):
    """Redireciona para ``next`` apenas quando for uma URL interna."""

    destino = request.POST.get("next") or ""
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(destino)
    return redirect(fallback, **kwargs)


def _trabalho_para_edicao(request, sala: SalaGT) -> TrabalhoGT:
    """Garante o conteúdo da sala apenas para quem pode editá-lo."""

    acesso_a_sala(request.user, sala).exigir(
        "pode_editar_conteudo", "Você não tem autorização para editar o conteúdo deste GT."
    )
    return SalaGTService.garantir_trabalho(sala)


def _trabalho_existente(sala: SalaGT) -> TrabalhoGT:
    trabalho = TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).first()
    if trabalho is None:
        raise Http404("Este GT ainda não possui conteúdo registrado.")
    return trabalho


# ----------------------------------------------------------------------
# Lista geral das salas
# ----------------------------------------------------------------------


@gt_required
def salas_lista(request):
    """Vitrine das salas: objetivo, ocupação, situação, inscrição e progresso."""

    cliente = _cliente_atual(request)
    ciclo, ciclos = _ciclo_atual(request, cliente)

    busca = request.GET.get("q", "").strip()
    situacao = request.GET.get("situacao", "").strip()
    somente_minhas = request.GET.get("minhas") == "1"

    salas = salas_do_catalogo(request.user, [cliente.id])
    if ciclo is not None:
        salas = salas.filter(ciclo=ciclo)
    if situacao:
        salas = salas.filter(situacao=situacao)
    if busca:
        salas = salas.filter(
            Q(objetivo__codigo__icontains=busca)
            | Q(objetivo__titulo__icontains=busca)
            | Q(objetivo__texto__icontains=busca)
            | Q(gt__nome__icontains=busca)
        )

    minhas = {
        inscricao.sala_id: inscricao
        for inscricao in InscricaoSalaGT.raw_objects.filter(
            is_deleted=False, usuario=request.user, sala__in=salas
        ).select_related("sala")
    }
    if somente_minhas:
        salas = salas.filter(pk__in=list(minhas.keys()) or [0])

    salas = list(salas)
    trabalhos = {
        trabalho.sala_id: trabalho
        for trabalho in TrabalhoGT.raw_objects.filter(
            is_deleted=False, sala_id__in=[sala.pk for sala in salas]
        ).select_related("sala")
    }
    coordenacoes = {}
    for inscricao in InscricaoSalaGT.raw_objects.filter(
        is_deleted=False,
        sala_id__in=[sala.pk for sala in salas],
        estado=InscricaoSalaGT.Estado.CONFIRMADA,
        papel=InscricaoSalaGT.Papel.COORDENACAO,
    ).select_related("usuario"):
        coordenacoes.setdefault(inscricao.sala_id, []).append(
            inscricao.usuario.nome or inscricao.usuario.email
        )

    cartoes = []
    for sala in salas:
        trabalho = trabalhos.get(sala.pk)
        inscricao = minhas.get(sala.pk)
        acesso = acesso_a_sala(request.user, sala)
        cartoes.append(
            {
                "sala": sala,
                "trabalho": trabalho,
                "progresso": TrabalhoGTService.progresso(trabalho),
                "inscricao": inscricao,
                "acesso": acesso,
                "coordenacao": ", ".join(coordenacoes.get(sala.pk, [])),
                "pode_solicitar": bool(
                    sala.aceita_inscricao
                    and (
                        inscricao is None
                        or inscricao.estado not in InscricaoSalaGT.ESTADOS_EM_DISPUTA
                    )
                ),
                "pode_cancelar": bool(
                    inscricao is not None
                    and inscricao.estado in InscricaoSalaGT.ESTADOS_EM_DISPUTA
                ),
                "lista_espera": InscricaoSalaGT.raw_objects.filter(
                    is_deleted=False, sala_id=sala.pk, estado=InscricaoSalaGT.Estado.LISTA_ESPERA
                ).count(),
            }
        )

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "cartoes": cartoes,
            "ciclo_atual": ciclo,
            "ciclos": ciclos,
            "filtros": {"q": busca, "situacao": situacao, "minhas": somente_minhas},
            "situacao_choices": SalaGT.Situacao.choices,
            "total_salas": len(cartoes),
            "total_objetivos": ObjetivoReferencial.raw_objects.filter(
                is_deleted=False, cliente=cliente, ativo=True
            ).count(),
        }
    )
    return render(request, "ava/gt/salas_lista.html", contexto)


# ----------------------------------------------------------------------
# Sala: visão geral
# ----------------------------------------------------------------------


@gt_required
def sala_detalhe(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso = acesso_a_sala(request.user, sala)
    trabalho = TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).first()

    if not acesso.pode_ver and not (trabalho and trabalho.consolidavel):
        raise PermissionDenied(
            "Você não participa deste GT. Solicite inscrição na lista de salas."
        )

    inscricao = InscricaoSalaGT.raw_objects.filter(
        is_deleted=False, sala_id=sala.pk, usuario=request.user
    ).first()
    membros = list(SalaGTService.membros_ativos(sala)) if acesso.pode_ver else []
    reunioes = (
        ReuniaoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk)
        .select_related("responsavel_registro")
        .order_by("-data_hora")[:10]
        if acesso.pode_ver
        else []
    )

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "acesso": acesso,
            "trabalho": trabalho,
            "mostra_conteudo": pode_ver_conteudo(acesso, trabalho),
            "progresso": TrabalhoGTService.progresso(trabalho),
            "inscricao": inscricao,
            "membros": membros,
            "reunioes": reunioes,
            "minha_frequencia": (
                resumo_frequencia_pessoal(sala, request.user) if inscricao else None
            ),
            "minhas_presencas": (
                ReuniaoGTService.frequencia_do_usuario(sala, request.user) if inscricao else []
            ),
            "documentos": (
                DocumentoGTService.documentos_da_sala(sala)[:5] if acesso.pode_exportar else []
            ),
            "situacao_choices": SalaGT.Situacao.choices,
            "aba": "visao_geral",
        }
    )
    return render(request, "ava/gt/sala_detalhe.html", contexto)


# ----------------------------------------------------------------------
# Sala: diagnóstico e quadro do objetivo
# ----------------------------------------------------------------------


@gt_required
def sala_trabalho(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso = acesso_a_sala(request.user, sala)
    trabalho = TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).first()

    if not acesso.pode_ver and not (trabalho and trabalho.consolidavel):
        raise PermissionDenied("Você não participa deste GT.")
    if trabalho is None:
        if not acesso.pode_editar_conteudo and not acesso.admin:
            raise PermissionDenied("O conteúdo deste GT ainda não foi iniciado.")
        trabalho = SalaGTService.garantir_trabalho(sala)

    metas = list(
        MetaGT.raw_objects.filter(is_deleted=False, trabalho=trabalho).order_by("ordem", "id")
    )
    estrategias = list(
        EstrategiaGT.raw_objects.filter(is_deleted=False, trabalho=trabalho)
        .order_by("ordem", "id")
        .prefetch_related("metas")
    )

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "acesso": acesso,
            "trabalho": trabalho,
            "mostra_conteudo": pode_ver_conteudo(acesso, trabalho),
            "editavel": acesso.pode_editar_conteudo and trabalho.editavel,
            "diagnostico_form": DiagnosticoGTForm(instance=trabalho),
            "quadro_form": QuadroObjetivoGTForm(instance=trabalho),
            "meta_form": MetaGTForm(),
            "estrategia_form": EstrategiaGTForm(trabalho=trabalho),
            "metas": metas,
            "estrategias": estrategias,
            "pendencias": TrabalhoGTService.pendencias_para_aprovacao(trabalho),
            "parecer_form": ParecerRevisaoForm(),
            "justificativa_form": JustificativaForm(),
            "versoes": VersaoTrabalhoGT.raw_objects.filter(
                is_deleted=False, trabalho=trabalho
            ).select_related("criado_por")[:10],
            "comentarios_habilitados": ComentarioGTService.habilitado(sala.cliente),
            "comentarios": (
                ComentarioGTService.listar(trabalho)
                if ComentarioGTService.habilitado(sala.cliente)
                else []
            ),
            "comentarios_abertos": (
                ComentarioGTService.total_abertos(trabalho)
                if ComentarioGTService.habilitado(sala.cliente)
                else 0
            ),
            "campos_comentaveis": ComentarioGTService.campos_para_formulario(),
            "aba": "trabalho",
        }
    )
    return render(request, "ava/gt/sala_trabalho.html", contexto)


@require_POST
@gt_required
def trabalho_diagnostico_salvar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    form = DiagnosticoGTForm(request.POST, instance=trabalho)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
    try:
        TrabalhoGTService.salvar_diagnostico(
            trabalho,
            request.user,
            form.cleaned_data,
            version_esperada=request.POST.get("version"),
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Diagnóstico salvo.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def trabalho_quadro_salvar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    form = QuadroObjetivoGTForm(request.POST, instance=trabalho)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
    try:
        TrabalhoGTService.salvar_quadro(
            trabalho,
            request.user,
            form.cleaned_data,
            version_esperada=request.POST.get("version"),
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Quadro do objetivo salvo.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def meta_salvar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    meta_id = _parse_int(request.POST.get("meta_id"))
    meta = (
        MetaGT.raw_objects.filter(is_deleted=False, trabalho=trabalho, pk=meta_id).first()
        if meta_id
        else None
    )
    form = MetaGTForm(request.POST, instance=meta)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
    try:
        TrabalhoGTService.salvar_meta(trabalho, request.user, meta=meta, dados=form.cleaned_data)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Meta salva.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def meta_remover(request, sala_id, meta_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    try:
        TrabalhoGTService.remover_meta(trabalho, request.user, meta_id)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Meta removida.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def estrategia_salvar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    estrategia_id = _parse_int(request.POST.get("estrategia_id"))
    estrategia = (
        EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho=trabalho, pk=estrategia_id
        ).first()
        if estrategia_id
        else None
    )
    form = EstrategiaGTForm(request.POST, instance=estrategia, trabalho=trabalho)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
    try:
        TrabalhoGTService.salvar_estrategia(
            trabalho,
            request.user,
            estrategia=estrategia,
            dados=form.cleaned_data,
            metas_ids=[meta.pk for meta in form.cleaned_data.get("metas", [])],
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Estratégia salva.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def estrategia_remover(request, sala_id, estrategia_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_para_edicao(request, sala)
    try:
        TrabalhoGTService.remover_estrategia(trabalho, request.user, estrategia_id)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Estratégia removida.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def trabalho_transicao(request, sala_id, acao):
    """Submeter, solicitar ajustes, aprovar, publicar ou reabrir o conteúdo."""

    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_existente(sala)
    try:
        if acao == "submeter":
            TrabalhoGTService.submeter_revisao(trabalho, request.user)
            messages.success(request, "Conteúdo enviado para revisão da coordenação.")
        elif acao == "ajustes":
            form = ParecerRevisaoForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Descreva os ajustes solicitados.")
                return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
            TrabalhoGTService.solicitar_ajustes(
                trabalho, request.user, parecer=form.cleaned_data["parecer"]
            )
            messages.success(request, "Ajustes solicitados ao GT.")
        elif acao == "aprovar":
            TrabalhoGTService.aprovar(trabalho, request.user)
            messages.success(request, "Conteúdo aprovado e congelado como versão.")
        elif acao == "publicar":
            TrabalhoGTService.publicar(trabalho, request.user)
            messages.success(request, "Conteúdo publicado.")
        elif acao == "reabrir":
            form = JustificativaForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Registre a justificativa da reabertura.")
                return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)
            TrabalhoGTService.reabrir(
                trabalho, request.user, justificativa=form.cleaned_data["justificativa"]
            )
            messages.success(request, "Conteúdo reaberto para ajustes.")
        else:
            raise Http404("Ação inválida.")
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def comentario_criar(request, sala_id):
    """Comentário/pedido de ajuste ancorado em um campo do quadro."""

    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_existente(sala)
    try:
        ComentarioGTService.criar(
            trabalho,
            request.user,
            campo=request.POST.get("campo", "geral"),
            texto=request.POST.get("texto", ""),
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Comentário registrado.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@require_POST
@gt_required
def comentario_resolver(request, sala_id, comentario_id):
    sala = _obter_sala(request, sala_id)
    trabalho = _trabalho_existente(sala)
    try:
        resolvido = ComentarioGTService.resolver(trabalho, request.user, comentario_id)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        if resolvido is None:
            messages.warning(request, "Comentário não encontrado.")
        else:
            messages.success(request, "Comentário marcado como resolvido.")
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


# ----------------------------------------------------------------------
# Sala: inscrições
# ----------------------------------------------------------------------


@gt_required
def sala_inscricoes(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso = acesso_a_sala(request.user, sala)
    acesso.exigir("pode_gerir_inscricoes", "Você não gerencia as inscrições deste GT.")

    inscricoes = (
        InscricaoSalaGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk)
        .select_related("usuario", "decidida_por")
        .order_by("estado", "ordem_espera", "usuario__nome")
    )
    vinculados = list(inscricoes.values_list("usuario_id", flat=True))

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "acesso": acesso,
            "inscricoes": inscricoes,
            "por_estado": {
                estado: [i for i in inscricoes if i.estado == estado]
                for estado, _ in InscricaoSalaGT.Estado.choices
            },
            "inscricao_form": InscricaoManualForm(
                cliente=sala.cliente, excluir_ids=vinculados
            ),
            "justificativa_form": JustificativaForm(),
            "papel_choices": InscricaoSalaGT.Papel.choices,
            "salas_do_ciclo": SalaGT.raw_objects.filter(
                is_deleted=False, ciclo_id=sala.ciclo_id
            ).exclude(pk=sala.pk).select_related("objetivo"),
            "aba": "inscricoes",
        }
    )
    return render(request, "ava/gt/sala_inscricoes.html", contexto)


@require_POST
@gt_required
def inscricao_solicitar(request, sala_id):
    """Pedido de inscrição do próprio usuário."""

    sala = _obter_sala(request, sala_id)
    try:
        inscricao = SalaGTService.solicitar_inscricao(sala, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        if inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA:
            messages.success(request, f"Inscrição confirmada no GT do objetivo {sala.objetivo.codigo}.")
        elif inscricao.estado == InscricaoSalaGT.Estado.LISTA_ESPERA:
            messages.warning(
                request,
                f"Sala lotada: você entrou na lista de espera na posição {inscricao.ordem_espera}. "
                "A vaga só é garantida após a confirmação da coordenação.",
            )
        else:
            messages.info(request, "Pedido de inscrição registrado e aguardando aprovação.")
    return _redirecionar(request, "ava:gt_salas")


@require_POST
@gt_required
def inscricao_manual(request, sala_id):
    sala = _obter_sala(request, sala_id)
    form = InscricaoManualForm(request.POST, cliente=sala.cliente)
    if not form.is_valid():
        messages.error(request, "Selecione um participante válido.")
        return redirect("ava:gt_sala_inscricoes", sala_id=sala.pk)
    try:
        inscricao = SalaGTService.solicitar_inscricao(
            sala,
            request.user,
            usuario_alvo=form.cleaned_data["usuario"],
            forcar_confirmacao=True,
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Participante inscrito na sala.")
        papel = form.cleaned_data["papel"]
        if papel != InscricaoSalaGT.Papel.PARTICIPANTE:
            # A inscrição já está válida; se o papel exigir perfil superior,
            # avisamos em vez de devolver 403 e perder o contexto da tela.
            try:
                SalaGTService.definir_papel(inscricao, request.user, papel=papel)
            except (PermissionDenied, ValidationError) as exc:
                messages.warning(
                    request,
                    "Participante inscrito, mas o papel não foi aplicado: "
                    f"{'; '.join(getattr(exc, 'messages', [str(exc)]))}",
                )
    return redirect("ava:gt_sala_inscricoes", sala_id=sala.pk)


def _obter_inscricao(request, sala: SalaGT, inscricao_id) -> InscricaoSalaGT:
    return get_object_or_404(
        InscricaoSalaGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).select_related(
            "usuario", "sala__ciclo", "sala__objetivo", "sala__gt"
        ),
        pk=inscricao_id,
    )


@require_POST
@gt_required
def inscricao_acao(request, sala_id, inscricao_id, acao):
    sala = _obter_sala(request, sala_id)
    inscricao = _obter_inscricao(request, sala, inscricao_id)
    try:
        if acao == "aprovar":
            resultado = SalaGTService.aprovar_inscricao(inscricao, request.user)
            if resultado.estado == InscricaoSalaGT.Estado.LISTA_ESPERA:
                messages.warning(
                    request,
                    f"Sala lotada: a inscrição foi para a lista de espera (posição {resultado.ordem_espera}).",
                )
            else:
                messages.success(request, "Inscrição confirmada.")
        elif acao == "recusar":
            form = JustificativaForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Registre o motivo da recusa.")
                return redirect("ava:gt_sala_inscricoes", sala_id=sala.pk)
            SalaGTService.recusar_inscricao(
                inscricao, request.user, justificativa=form.cleaned_data["justificativa"]
            )
            messages.success(request, "Inscrição recusada.")
        elif acao == "remover":
            SalaGTService.cancelar_inscricao(
                inscricao, request.user, justificativa=request.POST.get("justificativa", "")
            )
            messages.success(request, "Participante removido da sala.")
        elif acao == "papel":
            SalaGTService.definir_papel(
                inscricao, request.user, papel=request.POST.get("papel", "")
            )
            messages.success(request, "Papel atualizado.")
        elif acao == "mover":
            destino = get_object_or_404(
                SalaGT.raw_objects.filter(
                    is_deleted=False, cliente_id__in=_cliente_ids(request.user)
                ),
                pk=_parse_int(request.POST.get("destino")),
            )
            SalaGTService.mover_inscricao(inscricao, destino, request.user)
            messages.success(request, "Participante movido de sala.")
        else:
            raise Http404("Ação inválida.")
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    return redirect("ava:gt_sala_inscricoes", sala_id=sala.pk)


@require_POST
@gt_required
def inscricao_desistir(request, sala_id):
    """Desistência do próprio participante."""

    sala = _obter_sala(request, sala_id)
    inscricao = InscricaoSalaGT.raw_objects.filter(
        is_deleted=False, sala_id=sala.pk, usuario=request.user
    ).first()
    if inscricao is None:
        raise Http404("Você não possui inscrição nesta sala.")
    try:
        SalaGTService.cancelar_inscricao(
            inscricao, request.user, justificativa=request.POST.get("justificativa", "")
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Sua inscrição foi cancelada.")
    return _redirecionar(request, "ava:gt_salas")


@require_POST
@gt_required
def lista_espera_promover(request, sala_id):
    sala = _obter_sala(request, sala_id)
    quantidade = _parse_int(request.POST.get("quantidade")) or 1
    try:
        promovidas = SalaGTService.promover_lista_espera(
            sala, request.user, quantidade=quantidade
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        if promovidas:
            messages.success(request, f"{len(promovidas)} inscrição(ões) confirmada(s).")
        else:
            messages.warning(request, "Não há vaga disponível ou a fila está vazia.")
    return redirect("ava:gt_sala_inscricoes", sala_id=sala.pk)


# ----------------------------------------------------------------------
# Sala: reuniões e frequência
# ----------------------------------------------------------------------


@gt_required
def sala_reunioes(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso = acesso_a_sala(request.user, sala)
    acesso.exigir("pode_ver", "Você não participa deste GT.")

    reunioes = (
        ReuniaoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk)
        .select_related("responsavel_registro", "frequencia_validada_por")
        .prefetch_related(
            Prefetch(
                "presencas",
                queryset=PresencaReuniaoGT.raw_objects.filter(is_deleted=False),
            )
        )
        .annotate(
            total_presentes=Count(
                "presencas",
                filter=Q(
                    presencas__is_deleted=False,
                    presencas__situacao=PresencaReuniaoGT.Situacao.PRESENTE,
                ),
            )
        )
        .order_by("-data_hora")
    )

    paginator = Paginator(reunioes, PAGINA_TAMANHO)
    pagina = paginator.get_page(request.GET.get("page"))

    form = None
    if acesso.pode_gerir_reunioes:
        instancia = ReuniaoGT(cliente_id=sala.cliente_id, sala=sala)
        form = ReuniaoGTForm(instance=instancia)

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "acesso": acesso,
            "page_obj": pagina,
            "reuniao_form": form,
            "total_reunioes": paginator.count,
            "aba": "reunioes",
        }
    )
    return render(request, "ava/gt/sala_reunioes.html", contexto)


@require_POST
@gt_required
def reuniao_nova(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso_a_sala(request.user, sala).exigir("pode_gerir_reunioes")
    instancia = ReuniaoGT(cliente_id=sala.cliente_id, sala=sala, responsavel_registro=request.user)
    form = ReuniaoGTForm(request.POST, instance=instancia)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_sala_reunioes", sala_id=sala.pk)
    reuniao = form.save(commit=False)
    reuniao.cliente_id = sala.cliente_id
    reuniao.sala = sala
    try:
        ReuniaoGTService.salvar_reuniao(reuniao, request.user, criando=True)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect("ava:gt_sala_reunioes", sala_id=sala.pk)
    messages.success(request, "Reunião criada e lista de presença preparada.")
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


@gt_required
def reuniao_detalhe(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    sala = reuniao.sala
    acesso = acesso_a_sala(request.user, sala)
    acesso.exigir("pode_ver", "Você não participa deste GT.")

    presencas = (
        PresencaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao_id=reuniao.pk)
        .select_related("usuario", "registrado_por", "alterado_por")
        .order_by("usuario__nome", "usuario__email")
    )
    if not acesso.pode_ver_frequencia_da_sala:
        # Participante consulta apenas a própria frequência.
        presencas = presencas.filter(usuario=request.user)

    ata = AtaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao_id=reuniao.pk).first()

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "reuniao": reuniao,
            "acesso": acesso,
            "presencas": presencas,
            "resumo": reuniao.resumo_frequencia() if acesso.pode_ver_frequencia_da_sala else None,
            "situacao_presenca_choices": PresencaReuniaoGT.Situacao.choices,
            "reuniao_form": (
                ReuniaoGTForm(instance=reuniao) if acesso.pode_gerir_reunioes else None
            ),
            "ata": ata,
            "ata_form": AtaGTForm(instance=ata) if ata and acesso.pode_editar_ata else None,
            "justificativa_form": JustificativaForm(),
            "aba": "reunioes",
        }
    )
    return render(request, "ava/gt/reuniao_detalhe.html", contexto)


@require_POST
@gt_required
def reuniao_editar(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    acesso_a_sala(request.user, reuniao.sala).exigir("pode_gerir_reunioes")
    form = ReuniaoGTForm(request.POST, instance=reuniao)
    if not form.is_valid():
        _mensagens_do_form(request, form)
        return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
    atualizada = form.save(commit=False)
    try:
        ReuniaoGTService.salvar_reuniao(atualizada, request.user, criando=False)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Reunião atualizada.")
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


@require_POST
@gt_required
def frequencia_lancar(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    lancamentos: dict[int, dict] = {}
    for chave, valor in request.POST.items():
        if not chave.startswith("situacao_"):
            continue
        usuario_id = _parse_int(chave.removeprefix("situacao_"))
        if usuario_id is None:
            continue
        lancamentos[usuario_id] = {
            "situacao": valor,
            "justificativa": request.POST.get(f"justificativa_{usuario_id}", ""),
        }
    if not lancamentos:
        messages.warning(request, "Nenhuma presença foi informada.")
        return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
    try:
        alteradas = ReuniaoGTService.lancar_presencas(reuniao, request.user, lancamentos)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, f"Frequência registrada ({alteradas} alteração(ões)).")
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


@require_POST
@gt_required
def frequencia_preparar(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    try:
        criadas = ReuniaoGTService.preparar_presencas(reuniao, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(
            request, f"Lista de presença atualizada com {criadas} membro(s) do GT."
        )
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


@require_POST
@gt_required
def frequencia_validar(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    try:
        ReuniaoGTService.validar_frequencia(reuniao, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Frequência conferida e validada.")
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


@require_POST
@gt_required
def frequencia_reabrir(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    form = JustificativaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Registre a justificativa da correção.")
        return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
    try:
        ReuniaoGTService.reabrir_frequencia(
            reuniao, request.user, justificativa=form.cleaned_data["justificativa"]
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Frequência reaberta para correção (registrado na auditoria).")
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


# ----------------------------------------------------------------------
# Ata
# ----------------------------------------------------------------------


@require_POST
@gt_required
def ata_acao(request, reuniao_id, acao):
    reuniao = _obter_reuniao(request, reuniao_id)
    ata = AtaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao_id=reuniao.pk).first()
    try:
        if acao == "minuta":
            AtaGTService.garantir_minuta(reuniao, request.user)
            messages.success(request, "Minuta criada a partir do modelo institucional.")
        elif acao == "salvar":
            if ata is None:
                ata = AtaGTService.garantir_minuta(reuniao, request.user)
            form = AtaGTForm(request.POST, instance=ata)
            if not form.is_valid():
                _mensagens_do_form(request, form)
                return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
            AtaGTService.salvar(
                ata,
                request.user,
                form.cleaned_data,
                version_esperada=request.POST.get("version"),
            )
            messages.success(request, "Ata salva.")
        elif acao == "revisao":
            if ata is None:
                raise ValidationError("Crie a minuta antes de enviar para revisão.")
            AtaGTService.enviar_para_revisao(ata, request.user)
            messages.success(request, "Minuta enviada para revisão.")
        elif acao == "validar":
            if ata is None:
                raise ValidationError("Crie a minuta antes de validar.")
            AtaGTService.validar(ata, request.user)
            messages.success(request, "Ata validada.")
        elif acao == "reabrir":
            if ata is None:
                raise ValidationError("Não há ata para reabrir.")
            form = JustificativaForm(request.POST)
            if not form.is_valid():
                messages.error(request, "Registre a justificativa da reabertura.")
                return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
            AtaGTService.reabrir(
                ata, request.user, justificativa=form.cleaned_data["justificativa"]
            )
            messages.success(request, "Ata reaberta para correção.")
        else:
            raise Http404("Ação inválida.")
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)


# ----------------------------------------------------------------------
# Documentos
# ----------------------------------------------------------------------


@gt_required
def sala_documentos(request, sala_id):
    sala = _obter_sala(request, sala_id)
    acesso = acesso_a_sala(request.user, sala)
    acesso.exigir("pode_ver", "Você não participa deste GT.")
    trabalho = TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).first()

    contexto = _contexto_base(request, sala.cliente)
    contexto.update(
        {
            "sala": sala,
            "acesso": acesso,
            "trabalho": trabalho,
            "versoes": (
                VersaoTrabalhoGT.raw_objects.filter(is_deleted=False, trabalho=trabalho)
                .select_related("criado_por")
                .order_by("-numero")
                if trabalho
                else []
            ),
            "documentos": (
                DocumentoGTService.documentos_da_sala(sala) if acesso.pode_exportar else []
            ),
            "atas": AtaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao__sala_id=sala.pk
            ).select_related("reuniao").order_by("-reuniao__data_hora"),
            "aba": "documentos",
        }
    )
    return render(request, "ava/gt/sala_documentos.html", contexto)


@require_POST
@gt_required
def documento_objetivo_gerar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    try:
        job = DocumentoGTService.gerar_documento_objetivo(sala, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect("ava:gt_sala_documentos", sala_id=sala.pk)
    messages.success(
        request,
        f"Documento gerado: {DocumentoGTService.nome_do_arquivo(job)}. Use o botão de download.",
    )
    return redirect("ava:gt_sala_documentos", sala_id=sala.pk)


@require_POST
@gt_required
def documento_ata_gerar(request, reuniao_id):
    reuniao = _obter_reuniao(request, reuniao_id)
    try:
        job = DocumentoGTService.gerar_documento_ata(reuniao, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect("ava:gt_reuniao", reuniao_id=reuniao.pk)
    messages.success(request, f"Ata gerada: {DocumentoGTService.nome_do_arquivo(job)}.")
    return redirect("ava:gt_sala_documentos", sala_id=reuniao.sala_id)


@gt_required
def documento_download(request, job_id):
    """Download protegido: a autorização é revalidada a cada requisição."""

    job = get_object_or_404(
        ExportJob.raw_objects.filter(
            is_deleted=False, cliente_id__in=_cliente_ids(request.user)
        ),
        pk=job_id,
    )
    DocumentoGTService.autorizar_download(job, request.user)
    try:
        arquivo = DocumentoGTService.abrir_arquivo(job)
    except (FileNotFoundError, OSError) as exc:
        raise Http404("Arquivo não encontrado.") from exc

    nome = DocumentoGTService.nome_do_arquivo(job)
    AVAAuditService.registrar(
        cliente_id=job.cliente_id,
        usuario=request.user,
        entidade="exports.ExportJob",
        entidade_id=job.pk,
        acao="documento_gt_baixado",
        diff={"arquivo": nome},
    )
    resposta = FileResponse(
        arquivo,
        as_attachment=True,
        filename=nome,
        content_type=mimetypes.guess_type(nome)[0]
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    resposta["Cache-Control"] = "private, no-store"
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


# ----------------------------------------------------------------------
# Administração do Referencial
# ----------------------------------------------------------------------


@gt_admin_required
def admin_painel(request):
    cliente = _cliente_atual(request)
    ciclo, ciclos = _ciclo_atual(request, cliente)

    objetivos = ObjetivoReferencial.raw_objects.filter(
        is_deleted=False, cliente=cliente
    ).order_by("ordem", "codigo")
    salas = (
        SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente)
        .select_related("ciclo", "objetivo", "gt")
        .order_by("objetivo__ordem")
    )
    if ciclo is not None:
        salas = salas.filter(ciclo=ciclo)

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "ciclo_atual": ciclo,
            "ciclos": ciclos,
            "objetivos": objetivos,
            "total_objetivos_ativos": objetivos.filter(ativo=True).count(),
            "salas": salas,
            "gerar_salas_form": GerarSalasForm(),
            "modelo_ata": ModeloAtaGTService.obter_ativo(cliente.id),
            "modelos_ata": ModeloAtaGT.raw_objects.filter(
                is_deleted=False, cliente=cliente
            ).order_by("-versao")[:10],
            "consolidacoes": ExportJob.raw_objects.filter(
                is_deleted=False,
                cliente=cliente,
                alvo_tipo=ExportJob.AlvoTipo.GT_CONSOLIDADO,
            ).order_by("-created_at")[:10],
        }
    )
    return render(request, "ava/gt/admin_painel.html", contexto)


@gt_admin_required
def ciclo_form(request, ciclo_id=None):
    cliente = _cliente_atual(request)
    instancia = (
        get_object_or_404(
            CicloReferencial.raw_objects.filter(is_deleted=False, cliente=cliente), pk=ciclo_id
        )
        if ciclo_id
        else CicloReferencial(cliente=cliente)
    )
    form = CicloReferencialForm(request.POST or None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        ciclo = form.save(commit=False)
        ciclo.cliente = cliente
        ciclo.save()
        AVAAuditService.registrar(
            cliente_id=cliente.id,
            usuario=request.user,
            entidade="ava.CicloReferencial",
            entidade_id=ciclo.pk,
            acao="criado" if not ciclo_id else "atualizado",
            diff={"nome": ciclo.nome, "inscricoes_abertas": ciclo.inscricoes_abertas},
        )
        messages.success(request, "Ciclo salvo.")
        return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")
    if request.method == "POST":
        _mensagens_do_form(request, form)

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "form": form,
            "ciclo": instancia if ciclo_id else None,
            "titulo_pagina": "Editar ciclo" if ciclo_id else "Novo ciclo",
        }
    )
    return render(request, "ava/gt/ciclo_form.html", contexto)


@require_POST
@gt_admin_required
def ciclo_gerar_salas(request, ciclo_id):
    cliente = _cliente_atual(request)
    ciclo = get_object_or_404(
        CicloReferencial.raw_objects.filter(is_deleted=False, cliente=cliente), pk=ciclo_id
    )
    form = GerarSalasForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise os dados informados.")
        return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")
    try:
        resultado = SalaGTService.gerar_salas_do_ciclo(
            ciclo,
            request.user,
            criar_gt_ausente=form.cleaned_data["criar_gt_ausente"],
            capacidade=form.cleaned_data["capacidade"],
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")
    messages.success(
        request,
        f"{resultado['criadas']} sala(s) criada(s); {resultado['existentes']} já existia(m).",
    )
    if resultado["sem_gt"]:
        messages.warning(
            request,
            f"{resultado['sem_gt']} objetivo(s) sem GT correspondente. "
            "Cadastre o GT ou marque a opção de criar automaticamente.",
        )
    return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")


@gt_admin_required
def objetivos_lista(request):
    cliente = _cliente_atual(request)
    objetivos = ObjetivoReferencial.raw_objects.filter(
        is_deleted=False, cliente=cliente
    ).order_by("ordem", "codigo")

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "objetivos": objetivos,
            "total": objetivos.count(),
            "ativos": objetivos.filter(ativo=True).count(),
            "importacao_form": ImportacaoObjetivosForm(),
        }
    )
    return render(request, "ava/gt/objetivos_lista.html", contexto)


@gt_admin_required
def objetivo_form(request, objetivo_id=None):
    cliente = _cliente_atual(request)
    instancia = (
        get_object_or_404(
            ObjetivoReferencial.raw_objects.filter(is_deleted=False, cliente=cliente),
            pk=objetivo_id,
        )
        if objetivo_id
        else ObjetivoReferencial(cliente=cliente)
    )
    form = ObjetivoReferencialForm(request.POST or None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        objetivo = form.save(commit=False)
        objetivo.cliente = cliente
        objetivo.save()
        AVAAuditService.registrar(
            cliente_id=cliente.id,
            usuario=request.user,
            entidade="ava.ObjetivoReferencial",
            entidade_id=objetivo.pk,
            acao="criado" if not objetivo_id else "atualizado",
            diff={"codigo": objetivo.codigo, "ativo": objetivo.ativo},
        )
        messages.success(request, "Objetivo salvo.")
        return redirect("ava:gt_objetivos")
    if request.method == "POST":
        _mensagens_do_form(request, form)

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "form": form,
            "objetivo": instancia if objetivo_id else None,
            "titulo_pagina": "Editar objetivo" if objetivo_id else "Novo objetivo",
        }
    )
    return render(request, "ava/gt/objetivo_form.html", contexto)


@require_POST
@gt_admin_required
def objetivos_importar(request):
    cliente = _cliente_atual(request)
    form = ImportacaoObjetivosForm(request.POST, request.FILES)
    if not form.is_valid():
        for erros in form.errors.values():
            for erro in erros:
                messages.error(request, erro)
        return redirect("ava:gt_objetivos")

    registros = form.cleaned_data["registros"]
    criados = atualizados = 0
    codigos = []
    for registro in registros:
        codigos.append(registro["codigo"])
        objetivo = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente, codigo=registro["codigo"]
        ).first()
        if objetivo is None:
            objetivo = ObjetivoReferencial(cliente=cliente, codigo=registro["codigo"])
            criados += 1
        else:
            atualizados += 1
        objetivo.titulo = registro["titulo"]
        objetivo.texto = registro["texto"]
        objetivo.ordem = registro["ordem"]
        objetivo.ativo = True
        objetivo.full_clean()
        objetivo.save()

    desativados = 0
    if form.cleaned_data.get("desativar_ausentes"):
        desativados = (
            ObjetivoReferencial.raw_objects.filter(
                is_deleted=False, cliente=cliente, ativo=True
            )
            .exclude(codigo__in=codigos)
            .update(ativo=False)
        )

    AVAAuditService.registrar(
        cliente_id=cliente.id,
        usuario=request.user,
        entidade="ava.ObjetivoReferencial",
        entidade_id="importacao",
        acao="importados",
        diff={
            "criados": criados,
            "atualizados": atualizados,
            "desativados": desativados,
            "codigos": codigos,
        },
    )
    messages.success(
        request,
        f"{criados} objetivo(s) criado(s) e {atualizados} atualizado(s)."
        + (f" {desativados} desativado(s)." if desativados else ""),
    )
    return redirect("ava:gt_objetivos")


@gt_admin_required
def sala_form(request, sala_id=None):
    cliente = _cliente_atual(request)
    instancia = (
        get_object_or_404(
            SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente), pk=sala_id
        )
        if sala_id
        else SalaGT(cliente=cliente)
    )
    form = SalaGTForm(request.POST or None, instance=instancia, cliente=cliente)
    if request.method == "POST" and form.is_valid():
        sala = form.save(commit=False)
        sala.cliente = cliente
        try:
            sala.full_clean()
        except ValidationError as exc:
            _mensagens_de_erro(request, exc)
        else:
            sala.save()
            SalaGTService.garantir_trabalho(sala)
            AVAAuditService.registrar(
                cliente_id=cliente.id,
                usuario=request.user,
                entidade="ava.SalaGT",
                entidade_id=sala.pk,
                acao="criada" if not sala_id else "atualizada",
                diff={
                    "objetivo": sala.objetivo.codigo,
                    "gt": sala.gt.nome,
                    "capacidade": sala.capacidade,
                },
            )
            messages.success(request, "Sala salva.")
            return redirect("ava:gt_sala", sala_id=sala.pk)
    elif request.method == "POST":
        _mensagens_do_form(request, form)

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "form": form,
            "sala": instancia if sala_id else None,
            "titulo_pagina": "Editar sala" if sala_id else "Nova sala",
        }
    )
    return render(request, "ava/gt/sala_form.html", contexto)


@require_POST
@gt_admin_required
def sala_situacao(request, sala_id):
    sala = _obter_sala(request, sala_id)
    form = SituacaoSalaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Selecione a nova situação da sala.")
        return redirect("ava:gt_sala", sala_id=sala.pk)
    try:
        SalaGTService.alterar_situacao(
            sala,
            request.user,
            situacao=form.cleaned_data["situacao"],
            justificativa=form.cleaned_data.get("justificativa", ""),
        )
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
    else:
        messages.success(request, "Situação da sala atualizada.")
    return redirect("ava:gt_sala", sala_id=sala.pk)


@gt_admin_required
def modelo_ata_form(request):
    cliente = _cliente_atual(request)
    ativo = ModeloAtaGTService.obter_ativo(cliente.id)
    inicial = {}
    if ativo:
        inicial = {
            "nome": ativo.nome,
            "cabecalho": ativo.cabecalho,
            "rodape": ativo.rodape,
            "orientacoes": ativo.orientacoes,
            "secoes": "\n".join(
                f"{secao.get('chave')}|{secao.get('titulo')}"
                for secao in ativo.secoes_efetivas()
            ),
        }
    form = ModeloAtaGTForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            modelo = ModeloAtaGTService.publicar_versao(
                cliente.id,
                request.user,
                nome=form.cleaned_data["nome"],
                cabecalho=form.cleaned_data.get("cabecalho", ""),
                rodape=form.cleaned_data.get("rodape", ""),
                orientacoes=form.cleaned_data.get("orientacoes", ""),
                secoes=form.cleaned_data.get("secoes"),
            )
        except ValidationError as exc:
            _mensagens_de_erro(request, exc)
        else:
            messages.success(
                request,
                f"Modelo publicado na versão {modelo.versao}. As atas já geradas não mudam.",
            )
            return redirect("ava:gt_admin")
    elif request.method == "POST":
        messages.error(request, "Revise os campos do modelo de ata.")

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "form": form,
            "modelo_ativo": ativo,
            "modelos": ModeloAtaGT.raw_objects.filter(
                is_deleted=False, cliente=cliente
            ).order_by("-versao"),
            "secoes_padrao": ModeloAtaGT.SECOES_PADRAO,
        }
    )
    return render(request, "ava/gt/modelo_ata_form.html", contexto)


@require_POST
@gt_required
def consolidacao_gerar(request, ciclo_id):
    """Consolidação institucional dos objetivos do ciclo."""

    cliente = _cliente_atual(request)
    ciclo = get_object_or_404(
        CicloReferencial.raw_objects.filter(is_deleted=False, cliente=cliente), pk=ciclo_id
    )
    salas_ids = [
        pk for pk in (_parse_int(valor) for valor in request.POST.getlist("salas")) if pk
    ]
    try:
        job = DocumentoGTService.gerar_consolidado(ciclo, request.user, salas_ids=salas_ids)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")

    resumo = (job.payload_json or {}).get("resumo", {})
    messages.success(
        request,
        "Consolidação gerada com {total} objetivo(s): {consolidados} consolidado(s) e "
        "{pendentes} pendente(s).".format(
            total=resumo.get("total", 0),
            consolidados=resumo.get("consolidados", 0),
            pendentes=resumo.get("pendentes", 0),
        ),
    )
    return redirect(f"{reverse('ava:gt_admin')}?ciclo={ciclo.pk}")


@gt_required
def acompanhamento(request):
    """Painel de acompanhamento dos GTs para quem tem visão institucional."""

    if not tem_visao_global(request.user):
        raise PermissionDenied("Esta visão é restrita ao acompanhamento institucional.")
    cliente = _cliente_atual(request)
    ciclo, ciclos = _ciclo_atual(request, cliente)

    salas = (
        SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente)
        .select_related("ciclo", "objetivo", "gt")
        .order_by("objetivo__ordem", "objetivo__codigo")
    )
    if ciclo is not None:
        salas = salas.filter(ciclo=ciclo)
    salas = list(salas)

    trabalhos = {
        trabalho.sala_id: trabalho
        for trabalho in TrabalhoGT.raw_objects.filter(
            is_deleted=False, sala_id__in=[sala.pk for sala in salas]
        )
    }
    linhas = []
    for sala in salas:
        trabalho = trabalhos.get(sala.pk)
        linhas.append(
            {
                "sala": sala,
                "trabalho": trabalho,
                "progresso": TrabalhoGTService.progresso(trabalho),
                "reunioes": ReuniaoGT.raw_objects.filter(
                    is_deleted=False, sala_id=sala.pk
                ).count(),
                "atas_validadas": AtaReuniaoGT.raw_objects.filter(
                    is_deleted=False,
                    reuniao__sala_id=sala.pk,
                    estado=AtaReuniaoGT.Estado.VALIDADA,
                ).count(),
            }
        )

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "linhas": linhas,
            "ciclo_atual": ciclo,
            "ciclos": ciclos,
            "consolidados": sum(
                1 for linha in linhas if linha["trabalho"] and linha["trabalho"].consolidavel
            ),
            "agora": timezone.localtime(),
        }
    )
    return render(request, "ava/gt/acompanhamento.html", contexto)


# ----------------------------------------------------------------------
# Tutorial guiado
# ----------------------------------------------------------------------


@gt_admin_required
def tutorial_guiado(request):
    """Roteiro passo a passo que leva o administrador a cada página na ordem."""

    cliente = _cliente_atual(request)
    ciclo, ciclos = _ciclo_atual(request, cliente)
    passos = TutorialGTService.montar_roteiro(cliente, ciclo)

    contexto = _contexto_base(request, cliente)
    contexto.update(
        {
            "passos": passos,
            "progresso": TutorialGTService.progresso(passos),
            "ciclo_atual": ciclo,
            "ciclos": ciclos,
            "ciclo_exemplo": TutorialGTService.ciclo_exemplo(cliente),
            "nome_ciclo_exemplo": NOME_CICLO_EXEMPLO,
        }
    )
    return render(request, "ava/gt/tutorial.html", contexto)


@require_POST
@gt_admin_required
def tutorial_exemplo_criar(request):
    cliente = _cliente_atual(request)
    try:
        ciclo = TutorialGTService.criar_exemplo(cliente, request.user)
    except ValidationError as exc:
        _mensagens_de_erro(request, exc)
        return redirect(f"{reverse('ava:gt_tutorial')}?municipio={cliente.id}")
    messages.success(
        request,
        f"Exemplo criado em “{ciclo.nome}”: dois objetivos de demonstração, as salas, "
        "você como coordenação e uma reunião com a lista de presença pronta.",
    )
    return redirect(f"{reverse('ava:gt_tutorial')}?municipio={cliente.id}&ciclo={ciclo.pk}")


@require_POST
@gt_admin_required
def tutorial_exemplo_remover(request):
    cliente = _cliente_atual(request)
    removidos = TutorialGTService.remover_exemplo(cliente, request.user)
    if removidos["ciclo"]:
        messages.success(
            request,
            f"Exemplo removido: {removidos['salas']} sala(s) e "
            f"{removidos['objetivos']} objetivo(s) de demonstração saíram da lista.",
        )
    else:
        messages.info(request, "Nenhum exemplo de demonstração encontrado neste município.")
    return redirect(f"{reverse('ava:gt_tutorial')}?municipio={cliente.id}")
