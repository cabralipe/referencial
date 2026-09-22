"""Interface do professor (Diário de Bordo) e do administrador (planilhas)."""

from __future__ import annotations

import mimetypes
from datetime import date
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ava.forms_diario import (
    ColunaPlanilhaFormSet,
    DiarioBordoForm,
    DiarioBordoMidiaForm,
    DiarioBordoParticipanteForm,
    DiarioBordoRevisaoForm,
    ImportacaoUploadForm,
    MapeamentoImportacaoForm,
    ModeloPlanilhaForm,
)
from ava.models import (
    Aula,
    ColunaPlanilha,
    Curso,
    CursoModulo,
    DiarioBordo,
    DiarioBordoMidia,
    ImportacaoPlanilha,
    ModeloPlanilha,
    RegistroPlanilha,
)
from ava.models.diario import OrigemAula
from ava.services import (
    AVAAuditService,
    DiarioBordoExportService,
    DiarioBordoService,
    PlanilhaExportService,
    PlanilhaImportService,
    sugerir_mapeamento,
)
from ava.services.planilha_service import (
    PlanilhaFormatoNaoSuportado,
    formatos_suportados,
)
from core.models import Usuario
from curriculum.models import Escola


#: Quem pode usar o Diário de Bordo.
ROLES_DIARIO = {
    Usuario.Role.PROFESSOR,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.DIRETOR,
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
}

#: Quem pode configurar modelos de planilha.
ROLES_ADMIN_PLANILHA = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
}

#: Quem pode revisar/bloquear registros de terceiros.
ROLES_REVISAO_VIEW = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.SUPER_ADMIN,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.DIRETOR,
}

#: Papéis limitados à própria escola.
ROLES_ESCOPO_ESCOLA = {
    Usuario.Role.PROFESSOR,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.DIRETOR,
}

PAGINA_TAMANHO = 20
#: Teto de linhas por exportação, para não estourar memória.
MAX_EXPORTACAO = 5000


# ----------------------------------------------------------------------
# Helpers de permissão/escopo
# ----------------------------------------------------------------------


def _roles_required(roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if getattr(request.user, "role", None) not in roles:
                raise PermissionDenied(
                    "Você não possui permissão para acessar esta área."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


diario_required = _roles_required(ROLES_DIARIO)
planilha_admin_required = _roles_required(ROLES_ADMIN_PLANILHA)


def _parse_int(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _parse_date(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        return None


def _cliente_atual(request):
    """Município em que a operação acontece, respeitando o escopo do usuário."""

    permitidos = request.user.get_ava_clientes_queryset()
    cliente_id = _parse_int(
        request.POST.get("municipio") or request.GET.get("municipio")
    )
    if cliente_id:
        return get_object_or_404(permitidos, pk=cliente_id)
    cliente = permitidos.first()
    if cliente is None:
        raise PermissionDenied("Nenhum município está disponível para este usuário.")
    return cliente


def _cliente_ids(user) -> list[int]:
    return list(user.get_ava_clientes_queryset().values_list("id", flat=True))


def _diarios_do_usuario(user):
    """Queryset base do diário, já isolado por município e escola."""

    qs = (
        DiarioBordo.raw_objects.filter(
            is_deleted=False, cliente_id__in=_cliente_ids(user)
        )
        .select_related(
            "cliente", "escola", "professor", "curso", "modulo", "aula", "revisado_por"
        )
        .prefetch_related("midias", "participantes")
    )
    if user.role in ROLES_ESCOPO_ESCOLA:
        if not user.escola_id:
            return qs.none()
        qs = qs.filter(escola_id=user.escola_id)
    return qs


def _modelos_do_usuario(user, cliente=None):
    qs = ModeloPlanilha.raw_objects.filter(
        is_deleted=False, cliente_id__in=_cliente_ids(user)
    ).select_related("cliente", "escola", "curso")
    if cliente is not None:
        qs = qs.filter(cliente=cliente)
    if user.role in ROLES_ESCOPO_ESCOLA:
        qs = qs.filter(
            Q(escola__isnull=True) | Q(escola_id=user.escola_id),
            permite_professor=True,
            ativo=True,
        )
    return qs


# ----------------------------------------------------------------------
# Diário de Bordo — listagem e filtros
# ----------------------------------------------------------------------


def _filtrar_diarios(qs, filtros):
    if filtros["escola_id"]:
        qs = qs.filter(escola_id=filtros["escola_id"])
    if filtros["professor_id"]:
        qs = qs.filter(professor_id=filtros["professor_id"])
    if filtros["curso_id"]:
        qs = qs.filter(curso_id=filtros["curso_id"])
    if filtros["modulo_id"]:
        qs = qs.filter(modulo_id=filtros["modulo_id"])
    if filtros["origem"]:
        qs = qs.filter(origem=filtros["origem"])
    if filtros["status"]:
        qs = qs.filter(status=filtros["status"])
    if filtros["tipo_atividade"]:
        qs = qs.filter(tipo_atividade=filtros["tipo_atividade"])
    if filtros["data_inicio"]:
        qs = qs.filter(data_aula__gte=filtros["data_inicio"])
    if filtros["data_fim"]:
        qs = qs.filter(data_aula__lte=filtros["data_fim"])
    if filtros["q"]:
        termo = filtros["q"]
        qs = qs.filter(
            Q(titulo__icontains=termo)
            | Q(conteudo_trabalhado__icontains=termo)
            | Q(local_realizacao__icontains=termo)
            | Q(grupo_participante__icontains=termo)
        )
    return qs


def _extrair_filtros(request):
    return {
        "q": request.GET.get("q", "").strip(),
        "escola_id": _parse_int(request.GET.get("escola")),
        "professor_id": _parse_int(request.GET.get("professor")),
        "curso_id": _parse_int(request.GET.get("curso")),
        "modulo_id": _parse_int(request.GET.get("modulo")),
        "origem": request.GET.get("origem", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "tipo_atividade": request.GET.get("tipo_atividade", "").strip(),
        "data_inicio": _parse_date(request.GET.get("data_inicio")),
        "data_fim": _parse_date(request.GET.get("data_fim")),
    }


@diario_required
def diario_lista(request):
    cliente = _cliente_atual(request)
    filtros = _extrair_filtros(request)
    qs = _filtrar_diarios(
        _diarios_do_usuario(request.user).filter(cliente=cliente), filtros
    )

    escolas = Escola.raw_objects.filter(cliente=cliente, is_deleted=False).order_by("nome")
    professores = Usuario.objects.filter(
        cliente=cliente,
        role__in=[Usuario.Role.PROFESSOR, Usuario.Role.COORDENADOR_PEDAGOGICO],
    ).order_by("nome", "email")
    cursos = Curso.raw_objects.filter(cliente=cliente, is_deleted=False).order_by("titulo")
    if request.user.role in ROLES_ESCOPO_ESCOLA:
        escolas = escolas.filter(pk=request.user.escola_id)

    paginator = Paginator(qs.order_by("-data_aula", "-id"), PAGINA_TAMANHO)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "ava/management/diario_lista.html",
        {
            "cliente_atual": cliente,
            "municipios_ava": request.user.get_ava_clientes_queryset(),
            "pode_gerir_multiplos_avas": request.user.get_ava_clientes_queryset().count() > 1,
            "filtros": filtros,
            "escolas": escolas,
            "professores": professores,
            "cursos": cursos,
            "origem_choices": OrigemAula.choices,
            "status_choices": DiarioBordo.Status.choices,
            "tipo_atividade_choices": DiarioBordo.TipoAtividade.choices,
            "page_obj": page_obj,
            "querystring": query_params.urlencode(),
            "total_registros": paginator.count,
        },
    )


@diario_required
def diario_exportar(request, formato):
    if formato not in {"xlsx", "csv"}:
        raise Http404("Formato de exportação não suportado.")
    cliente = _cliente_atual(request)
    filtros = _extrair_filtros(request)
    qs = _filtrar_diarios(
        _diarios_do_usuario(request.user).filter(cliente=cliente), filtros
    ).order_by("-data_aula", "-id")

    diarios = list(qs[:MAX_EXPORTACAO])
    if formato == "csv":
        payload = DiarioBordoExportService.para_csv(diarios)
        content_type = "text/csv; charset=utf-8"
    else:
        payload = DiarioBordoExportService.para_xlsx(diarios)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    AVAAuditService.registrar(
        cliente_id=cliente.id,
        usuario=request.user,
        entidade="ava.DiarioBordo",
        entidade_id="exportacao",
        acao="exportado",
        diff={"formato": formato, "total": len(diarios)},
    )
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="diario-de-bordo.{formato}"'
    )
    return response


# ----------------------------------------------------------------------
# Diário de Bordo — criação e edição
# ----------------------------------------------------------------------


@diario_required
def diario_novo(request):
    cliente = _cliente_atual(request)
    instancia = DiarioBordo(cliente=cliente)
    if request.user.role == Usuario.Role.PROFESSOR:
        instancia.escola_id = request.user.escola_id
        instancia.professor = request.user

    aula_id = _parse_int(request.GET.get("aula"))
    if aula_id:
        aula = Aula.raw_objects.filter(
            is_deleted=False, cliente=cliente, pk=aula_id
        ).select_related("modulo__curso").first()
        if aula is not None:
            instancia.origem = OrigemAula.NO_SISTEMA
            instancia.aplicar_dados_da_aula(aula)

    form = DiarioBordoForm(
        request.POST or None,
        instance=instancia,
        user=request.user,
        cliente=cliente,
    )
    if request.method == "POST" and form.is_valid():
        diario = form.save(commit=False)
        diario.cliente = cliente
        try:
            DiarioBordoService.salvar(diario, request.user, criando=True)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                "Registro criado como rascunho. Adicione frequência e fotos antes de enviar.",
            )
            return redirect("ava:diario_editar", diario_id=diario.id)
    elif request.method == "POST":
        messages.error(request, "Revise os campos destacados para salvar o registro.")

    return render(
        request,
        "ava/management/diario_form.html",
        {
            "form": form,
            "cliente_atual": cliente,
            "titulo_pagina": "Novo registro do diário de bordo",
            "texto_botao": "Salvar rascunho",
        },
    )


def _obter_diario(request, diario_id) -> DiarioBordo:
    return get_object_or_404(_diarios_do_usuario(request.user), pk=diario_id)


@diario_required
def diario_editar(request, diario_id):
    diario = _obter_diario(request, diario_id)
    editavel = DiarioBordoService.pode_editar(diario, request.user)

    form = DiarioBordoForm(
        request.POST or None,
        instance=diario,
        user=request.user,
        cliente=diario.cliente,
    )
    if request.method == "POST":
        if not editavel:
            messages.error(request, "Este registro não pode mais ser alterado.")
            return redirect("ava:diario_editar", diario_id=diario.id)
        if form.is_valid():
            atualizado = form.save(commit=False)
            try:
                DiarioBordoService.salvar(atualizado, request.user, criando=False)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, "Registro atualizado com sucesso.")
                return redirect("ava:diario_editar", diario_id=diario.id)
        else:
            messages.error(request, "Revise os campos destacados para salvar o registro.")

    return render(
        request,
        "ava/management/diario_form.html",
        {
            "form": form,
            "diario": diario,
            "editavel": editavel,
            "cliente_atual": diario.cliente,
            "midia_form": DiarioBordoMidiaForm(),
            "participante_form": DiarioBordoParticipanteForm(),
            "revisao_form": DiarioBordoRevisaoForm(),
            "pode_revisar": request.user.role in ROLES_REVISAO_VIEW,
            "midias": diario.midias.filter(is_deleted=False).order_by("ordem", "id"),
            "participantes": diario.participantes.filter(is_deleted=False).order_by("nome"),
            "titulo_pagina": "Editar registro do diário de bordo",
            "texto_botao": "Salvar alterações",
        },
    )


@diario_required
def diario_detalhe(request, diario_id):
    diario = _obter_diario(request, diario_id)
    return render(
        request,
        "ava/management/diario_detalhe.html",
        {
            "diario": diario,
            "cliente_atual": diario.cliente,
            "midias": diario.midias.filter(is_deleted=False).order_by("ordem", "id"),
            "participantes": diario.participantes.filter(is_deleted=False).order_by("nome"),
            "revisao_form": DiarioBordoRevisaoForm(),
            "pode_revisar": request.user.role in ROLES_REVISAO_VIEW,
            "editavel": DiarioBordoService.pode_editar(diario, request.user),
        },
    )


@diario_required
@require_POST
def diario_enviar(request, diario_id):
    diario = _obter_diario(request, diario_id)
    try:
        DiarioBordoService.enviar(diario, request.user)
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Registro enviado para revisão.")
    return redirect("ava:diario_detalhe", diario_id=diario.id)


@diario_required
@require_POST
def diario_revisar(request, diario_id):
    diario = _obter_diario(request, diario_id)
    form = DiarioBordoRevisaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise os campos do parecer.")
        return redirect("ava:diario_detalhe", diario_id=diario.id)
    try:
        DiarioBordoService.revisar(
            diario,
            request.user,
            parecer=form.cleaned_data["parecer"],
            bloquear=form.cleaned_data["bloquear"],
        )
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _mensagem_de_erro(exc))
    else:
        messages.success(request, "Revisão registrada.")
    return redirect("ava:diario_detalhe", diario_id=diario.id)


@diario_required
@require_POST
def diario_reabrir(request, diario_id):
    diario = _obter_diario(request, diario_id)
    try:
        DiarioBordoService.reabrir(diario, request.user)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Registro reaberto como rascunho.")
    return redirect("ava:diario_detalhe", diario_id=diario.id)


def _mensagem_de_erro(exc) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return str(exc)


# ----------------------------------------------------------------------
# Diário de Bordo — frequência e mídias
# ----------------------------------------------------------------------


@diario_required
@require_POST
def diario_participante_adicionar(request, diario_id):
    diario = _obter_diario(request, diario_id)
    form = DiarioBordoParticipanteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Informe o nome do participante.")
        return redirect("ava:diario_editar", diario_id=diario.id)
    try:
        DiarioBordoService.registrar_presenca(
            diario,
            request.user,
            nome=form.cleaned_data["nome"],
            identificacao=form.cleaned_data["identificacao"],
            presente=form.cleaned_data["presente"],
            justificativa=form.cleaned_data["justificativa"],
        )
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _mensagem_de_erro(exc))
    else:
        messages.success(request, "Participante registrado.")
    return redirect("ava:diario_editar", diario_id=diario.id)


@diario_required
@require_POST
def diario_participante_remover(request, diario_id, participante_id):
    diario = _obter_diario(request, diario_id)
    try:
        DiarioBordoService.remover_presenca(diario, request.user, participante_id)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Participante removido.")
    return redirect("ava:diario_editar", diario_id=diario.id)


@diario_required
@require_POST
def diario_midia_adicionar(request, diario_id):
    diario = _obter_diario(request, diario_id)
    form = DiarioBordoMidiaForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(
            request,
            "Não foi possível anexar o arquivo: "
            + "; ".join(
                f"{campo}: {', '.join(erros)}" for campo, erros in form.errors.items()
            ),
        )
        return redirect("ava:diario_editar", diario_id=diario.id)
    try:
        DiarioBordoService.adicionar_midia(
            diario,
            request.user,
            form.cleaned_data["arquivo"],
            tipo=form.cleaned_data["tipo"],
            legenda=form.cleaned_data["legenda"],
            consentimento=form.cleaned_data["consentimento_registrado"],
        )
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _mensagem_de_erro(exc))
    else:
        messages.success(request, "Arquivo anexado com sucesso.")
    return redirect("ava:diario_editar", diario_id=diario.id)


@diario_required
@require_POST
def diario_midia_remover(request, diario_id, midia_id):
    diario = _obter_diario(request, diario_id)
    try:
        DiarioBordoService.remover_midia(diario, request.user, midia_id)
    except PermissionDenied as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Arquivo removido.")
    return redirect("ava:diario_editar", diario_id=diario.id)


@diario_required
def diario_midia_arquivo(request, diario_id, midia_id):
    """Serve a mídia pelo Django — nunca por URL pública do storage."""

    diario = _obter_diario(request, diario_id)
    midia = get_object_or_404(
        DiarioBordoMidia.raw_objects.filter(is_deleted=False, diario=diario),
        pk=midia_id,
    )
    try:
        arquivo = midia.arquivo.open("rb")
    except FileNotFoundError as exc:
        raise Http404("Arquivo não encontrado.") from exc

    content_type = (
        midia.content_type
        or mimetypes.guess_type(midia.nome_original or midia.arquivo.name)[0]
        or "application/octet-stream"
    )
    response = FileResponse(
        arquivo,
        as_attachment=request.GET.get("download") == "1",
        filename=midia.nome_original or midia.arquivo.name.rsplit("/", 1)[-1],
        content_type=content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@diario_required
def diario_aulas_json(request):
    """Alimenta os selects encadeados de curso → módulo → aula."""

    cliente = _cliente_atual(request)
    curso_id = _parse_int(request.GET.get("curso"))
    modulo_id = _parse_int(request.GET.get("modulo"))

    modulos = CursoModulo.raw_objects.filter(is_deleted=False, cliente=cliente)
    aulas = Aula.raw_objects.filter(is_deleted=False, cliente=cliente)
    if curso_id:
        modulos = modulos.filter(curso_id=curso_id)
        aulas = aulas.filter(modulo__curso_id=curso_id)
    if modulo_id:
        aulas = aulas.filter(modulo_id=modulo_id)

    return JsonResponse(
        {
            "modulos": [
                {"id": m.id, "titulo": m.titulo}
                for m in modulos.order_by("ordem", "titulo")[:200]
            ],
            "aulas": [
                {
                    "id": a.id,
                    "titulo": a.titulo,
                    "resumo": a.resumo,
                    "modulo_id": a.modulo_id,
                }
                for a in aulas.order_by("ordem", "titulo")[:200]
            ],
        }
    )


# ----------------------------------------------------------------------
# Planilhas configuráveis — administração
# ----------------------------------------------------------------------


@planilha_admin_required
def planilha_modelo_lista(request):
    cliente = _cliente_atual(request)
    modelos = _modelos_do_usuario(request.user, cliente).order_by("nome", "-versao")
    paginator = Paginator(modelos, PAGINA_TAMANHO)
    return render(
        request,
        "ava/management/planilha_modelo_lista.html",
        {
            "cliente_atual": cliente,
            "municipios_ava": request.user.get_ava_clientes_queryset(),
            "pode_gerir_multiplos_avas": request.user.get_ava_clientes_queryset().count() > 1,
            "page_obj": paginator.get_page(request.GET.get("page")),
            "formatos": formatos_suportados(),
        },
    )


@planilha_admin_required
def planilha_modelo_form(request, modelo_id=None):
    cliente = _cliente_atual(request)
    if modelo_id:
        modelo = get_object_or_404(
            _modelos_do_usuario(request.user), pk=modelo_id
        )
        cliente = modelo.cliente
        criando = False
    else:
        modelo = ModeloPlanilha(cliente=cliente, created_by=request.user)
        criando = True

    form = ModeloPlanilhaForm(
        request.POST or None, instance=modelo, cliente=cliente
    )
    formset = ColunaPlanilhaFormSet(request.POST or None, instance=modelo)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        salvo = form.save(commit=False)
        salvo.cliente = cliente
        if criando:
            salvo.created_by = request.user
        salvo.updated_by = request.user
        salvo.full_clean()
        salvo.save()

        formset.instance = salvo
        colunas = formset.save(commit=False)
        for coluna in colunas:
            coluna.modelo = salvo
            coluna.cliente_id = salvo.cliente_id
            coluna.full_clean()
            coluna.save()
        for removida in formset.deleted_objects:
            removida.delete()

        AVAAuditService.registrar_planilha(
            salvo,
            request.user,
            acao="modelo_criado" if criando else "modelo_atualizado",
            diff={"nome": salvo.nome, "versao": salvo.versao},
        )
        messages.success(request, "Modelo de planilha salvo com sucesso.")
        return redirect("ava:planilha_modelo_editar", modelo_id=salvo.id)
    if request.method == "POST":
        messages.error(request, "Revise os campos destacados para salvar o modelo.")

    return render(
        request,
        "ava/management/planilha_modelo_form.html",
        {
            "form": form,
            "formset": formset,
            "modelo": None if criando else modelo,
            "cliente_atual": cliente,
            "tipos": ColunaPlanilha.Tipo.choices,
            "titulo_pagina": "Novo modelo de planilha" if criando else f"Editar: {modelo.nome}",
        },
    )


@planilha_admin_required
@require_POST
def planilha_modelo_alternar(request, modelo_id):
    modelo = get_object_or_404(_modelos_do_usuario(request.user), pk=modelo_id)
    modelo.ativo = not modelo.ativo
    modelo.updated_by = request.user
    modelo.save(update_fields=["ativo", "updated_by", "updated_at"])
    AVAAuditService.registrar_planilha(
        modelo,
        request.user,
        acao="modelo_ativado" if modelo.ativo else "modelo_desativado",
    )
    messages.success(
        request,
        "Modelo ativado." if modelo.ativo else "Modelo desativado.",
    )
    return redirect("ava:planilha_modelo_lista")


# ----------------------------------------------------------------------
# Planilhas configuráveis — dados, importação e exportação
# ----------------------------------------------------------------------


def _modelo_acessivel(request, modelo_id) -> ModeloPlanilha:
    return get_object_or_404(_modelos_do_usuario(request.user), pk=modelo_id)


def _registros_do_modelo(request, modelo: ModeloPlanilha):
    qs = (
        RegistroPlanilha.raw_objects.filter(
            is_deleted=False, cliente_id=modelo.cliente_id, modelo=modelo
        )
        .select_related("escola", "curso", "created_by")
        .prefetch_related("valores__coluna")
    )
    if request.user.role in ROLES_ESCOPO_ESCOLA:
        qs = qs.filter(Q(escola__isnull=True) | Q(escola_id=request.user.escola_id))
    return qs


@diario_required
def planilha_registros(request, modelo_id):
    modelo = _modelo_acessivel(request, modelo_id)
    colunas = list(modelo.colunas_visiveis())
    qs = _registros_do_modelo(request, modelo)

    busca = request.GET.get("q", "").strip()
    if busca:
        qs = qs.filter(
            Q(valores__valor_texto__icontains=busca)
            | Q(chave_externa__icontains=busca)
        ).distinct()

    coluna_ordem = request.GET.get("ordenar", "").strip()
    direcao = request.GET.get("direcao", "asc")
    if coluna_ordem:
        coluna = next((c for c in colunas if c.chave == coluna_ordem), None)
        if coluna is not None:
            campo = f"valores__{coluna.armazena_em}"
            if coluna.armazena_em == "arquivo":
                campo = "valores__valor_texto"
            prefixo = "" if direcao == "asc" else "-"
            qs = qs.filter(valores__coluna=coluna).order_by(f"{prefixo}{campo}")

    paginator = Paginator(qs, PAGINA_TAMANHO)
    page_obj = paginator.get_page(request.GET.get("page"))
    linhas = []
    for registro in page_obj:
        valores = registro.valores_por_chave()
        linhas.append(
            {
                "registro": registro,
                "celulas": [
                    valores[coluna.chave].valor_exibicao()
                    if coluna.chave in valores
                    else ""
                    for coluna in colunas
                ],
            }
        )
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "ava/management/planilha_registros.html",
        {
            "modelo": modelo,
            "colunas": colunas,
            "linhas": linhas,
            "page_obj": page_obj,
            "busca": busca,
            "coluna_ordem": coluna_ordem,
            "direcao": direcao,
            "querystring": query_params.urlencode(),
            "cliente_atual": modelo.cliente,
            "pode_importar": request.user.role in ROLES_ADMIN_PLANILHA
            or modelo.permite_professor,
            "importacoes": ImportacaoPlanilha.raw_objects.filter(
                is_deleted=False, modelo=modelo
            ).select_related("created_by").order_by("-created_at")[:10],
        },
    )


@diario_required
def planilha_exportar(request, modelo_id, formato):
    if formato not in {"xlsx", "csv"}:
        raise Http404("Formato de exportação não suportado.")
    modelo = _modelo_acessivel(request, modelo_id)
    registros = list(_registros_do_modelo(request, modelo)[:MAX_EXPORTACAO])

    if formato == "csv":
        payload = PlanilhaExportService.para_csv(modelo, registros)
        content_type = "text/csv; charset=utf-8"
    else:
        payload = PlanilhaExportService.para_xlsx(modelo, registros)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    AVAAuditService.registrar_planilha(
        modelo,
        request.user,
        acao="exportado",
        diff={"formato": formato, "total": len(registros)},
    )
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="{modelo.slug or "planilha"}.{formato}"'
    )
    return response


@diario_required
def planilha_modelo_em_branco(request, modelo_id):
    """Baixa um arquivo com os cabeçalhos configurados, pronto para preencher."""

    modelo = _modelo_acessivel(request, modelo_id)
    payload = PlanilhaExportService.modelo_em_branco_xlsx(modelo)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="modelo-{modelo.slug or modelo.id}.xlsx"'
    )
    return response


def _pode_importar(request, modelo: ModeloPlanilha) -> bool:
    if request.user.role in ROLES_ADMIN_PLANILHA:
        return True
    return modelo.permite_professor and modelo.ativo


@diario_required
def planilha_importar(request, modelo_id):
    """Etapa 1: upload do arquivo e leitura dos cabeçalhos."""

    modelo = _modelo_acessivel(request, modelo_id)
    if not _pode_importar(request, modelo):
        raise PermissionDenied("Você não pode importar dados neste modelo.")

    form = ImportacaoUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        importacao = form.save(commit=False)
        importacao.cliente_id = modelo.cliente_id
        importacao.modelo = modelo
        importacao.created_by = request.user
        try:
            importacao.full_clean(exclude=["nome_original", "tamanho_bytes"])
        except ValidationError as exc:
            for campo, erros in exc.message_dict.items():
                form.add_error(campo if campo in form.fields else None, erros)
        else:
            importacao.save()
            try:
                leitura = PlanilhaImportService(importacao, request.user).ler()
            except PlanilhaFormatoNaoSuportado as exc:
                importacao.status = ImportacaoPlanilha.Status.ERRO
                importacao.erros = [{"linha": 0, "coluna": "—", "mensagem": str(exc)}]
                importacao.save(update_fields=["status", "erros", "updated_at"])
                messages.error(request, str(exc))
                return redirect("ava:planilha_importar", modelo_id=modelo.id)

            importacao.cabecalhos = leitura.cabecalhos
            importacao.mapeamento = sugerir_mapeamento(modelo, leitura.cabecalhos)
            importacao.total_linhas = len(leitura.linhas)
            importacao.save(
                update_fields=["cabecalhos", "mapeamento", "total_linhas", "updated_at"]
            )
            return redirect("ava:planilha_importar_mapear", importacao_id=importacao.id)
    elif request.method == "POST":
        messages.error(request, "Selecione um arquivo válido para importar.")

    return render(
        request,
        "ava/management/planilha_importar.html",
        {
            "modelo": modelo,
            "form": form,
            "cliente_atual": modelo.cliente,
            "formatos": formatos_suportados(),
            "colunas": list(modelo.colunas_ativas()),
        },
    )


def _obter_importacao(request, importacao_id) -> ImportacaoPlanilha:
    importacao = get_object_or_404(
        ImportacaoPlanilha.raw_objects.filter(
            is_deleted=False, cliente_id__in=_cliente_ids(request.user)
        ).select_related("modelo"),
        pk=importacao_id,
    )
    _modelo_acessivel(request, importacao.modelo_id)
    if not _pode_importar(request, importacao.modelo):
        raise PermissionDenied("Você não pode importar dados neste modelo.")
    return importacao


@diario_required
def planilha_importar_mapear(request, importacao_id):
    """Etapas 2 a 4: mapeamento, pré-visualização, validação e gravação."""

    importacao = _obter_importacao(request, importacao_id)
    modelo = importacao.modelo
    servico = PlanilhaImportService(importacao, request.user)

    try:
        leitura = servico.ler()
    except PlanilhaFormatoNaoSuportado as exc:
        messages.error(request, str(exc))
        return redirect("ava:planilha_importar", modelo_id=modelo.id)

    inicial = {"coluna_chave": importacao.coluna_chave}
    for indice, cabecalho in enumerate(leitura.cabecalhos):
        inicial[f"col_{indice}"] = (importacao.mapeamento or {}).get(cabecalho, "")

    form = MapeamentoImportacaoForm(
        request.POST or None,
        modelo=modelo,
        cabecalhos=leitura.cabecalhos,
        initial=inicial,
    )
    validacao = None
    confirmar = request.POST.get("acao") == "confirmar"

    if request.method == "POST" and form.is_valid():
        importacao.mapeamento = form.cleaned_data["mapeamento"]
        importacao.coluna_chave = form.cleaned_data.get("coluna_chave") or ""
        importacao.save(update_fields=["mapeamento", "coluna_chave", "updated_at"])

        servico = PlanilhaImportService(importacao, request.user)
        validacao = servico.validar(leitura)
        importacao.erros = [erro.as_dict() for erro in validacao.erros]
        importacao.status = (
            ImportacaoPlanilha.Status.VALIDADA
            if validacao.valida
            else ImportacaoPlanilha.Status.ERRO
        )
        importacao.save(update_fields=["erros", "status", "updated_at"])

        if confirmar and validacao.valida:
            servico.gravar(validacao)
            messages.success(
                request,
                f"Importação concluída: {importacao.total_criados} criados, "
                f"{importacao.total_atualizados} atualizados.",
            )
            return redirect("ava:planilha_registros", modelo_id=modelo.id)
        if confirmar:
            messages.error(
                request,
                "A planilha possui erros e não foi gravada. Corrija as linhas indicadas.",
            )
        elif validacao.valida:
            messages.success(
                request,
                f"{len(validacao.linhas_validas)} linha(s) válidas. "
                "Confira a pré-visualização e confirme a gravação.",
            )
        else:
            messages.warning(
                request, "Foram encontrados erros. Nenhum dado foi gravado ainda."
            )

    return render(
        request,
        "ava/management/planilha_importar_mapear.html",
        {
            "importacao": importacao,
            "modelo": modelo,
            "form": form,
            "leitura": leitura,
            "preview": [
                {
                    "numero": linha.numero,
                    "celulas": [
                        linha.valores.get(cabecalho, "")
                        for cabecalho in leitura.cabecalhos
                    ],
                }
                for linha in leitura.preview
            ],
            "validacao": validacao,
            "cliente_atual": modelo.cliente,
            "total_linhas": len(leitura.linhas),
        },
    )


@diario_required
@require_POST
def planilha_importar_cancelar(request, importacao_id):
    importacao = _obter_importacao(request, importacao_id)
    importacao.status = ImportacaoPlanilha.Status.CANCELADA
    importacao.save(update_fields=["status", "updated_at"])
    AVAAuditService.registrar_planilha(importacao, request.user, acao="importacao_cancelada")
    messages.info(request, "Importação cancelada. Nenhum dado foi gravado.")
    return redirect("ava:planilha_registros", modelo_id=importacao.modelo_id)
