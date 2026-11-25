"""Fluxo simples do plano: ciclo, categorias, tabela, participantes e exportação."""

import csv
import io
import json

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from ava.data.pne_2026 import FONTE_PNE
from ava.models import CicloReferencial, InscricaoSalaGT, LinhaPlanoEducacao, SalaGT
from ava.services import plano_educacao_service as plano
from ava.services.gt_access import e_admin_referencial
from ava.services.gt_sala_service import SalaGTService
from ava.views.gt import _cliente_atual, _ciclo_atual, _contexto_base, _obter_sala, gt_required, gt_admin_required


def _ciclo(request):
    cliente = _cliente_atual(request)
    ciclo, ciclos = _ciclo_atual(request, cliente)
    if ciclo is None:
        ciclo, _ = CicloReferencial.raw_objects.get_or_create(
            cliente=cliente, nome="Plano de Educação 2026–2036", is_deleted=False,
            defaults={"inscricoes_abertas": True},
        )
    plano.preparar_ciclo(ciclo)
    return cliente, ciclo, ciclos


def _salas(ciclo):
    return SalaGT.raw_objects.filter(ciclo=ciclo, gt__isnull=True, is_deleted=False).select_related("objetivo", "ciclo", "cliente")


def _contexto_sala(request, sala, aba):
    contexto = _contexto_base(request, sala.cliente)
    contexto.update(sala=sala, aba=aba, ciclo_atual=sala.ciclo,
                    pode_ler=plano.pode_ler(request.user, sala),
                    editavel=plano.pode_editar(request.user, sala), fonte_pne=FONTE_PNE)
    return contexto


@gt_required
def catalogo(request):
    cliente, ciclo, ciclos = _ciclo(request)
    salas = _salas(ciclo).annotate(
        total_metas=Count("linhas_plano", filter=Q(linhas_plano__tipo="meta", linhas_plano__is_deleted=False), distinct=True),
        preenchidas=Count("linhas_plano", filter=Q(linhas_plano__is_deleted=False) & ~Q(linhas_plano__texto=""), distinct=True),
        total_linhas=Count("linhas_plano", filter=Q(linhas_plano__is_deleted=False), distinct=True),
    )
    busca = request.GET.get("q", "").strip()
    if busca:
        salas = salas.filter(objetivo__titulo__icontains=busca)
    minhas = set(InscricaoSalaGT.raw_objects.filter(usuario=request.user, sala__ciclo=ciclo, is_deleted=False, estado="confirmada").values_list("sala_id", flat=True))
    cartoes = [{"sala": sala, "inscrito": sala.pk in minhas} for sala in salas]
    contexto = _contexto_base(request, cliente)
    contexto.update(ciclo_atual=ciclo, ciclos=ciclos, cartoes=cartoes, busca=busca, fonte_pne=FONTE_PNE)
    return render(request, "ava/plano/catalogo.html", contexto)


@gt_required
@never_cache
def sala(request, sala_id):
    sala = _obter_sala(request, sala_id)
    if sala.gt_id:
        from ava.views import gt
        return gt.sala_trabalho(request, sala_id) if request.path.endswith('/trabalho/') else gt.sala_detalhe(request, sala_id)
    contexto = _contexto_sala(request, sala, "tabela")
    # A estrutura pode ser vista antes da inscrição; redações só após entrar.
    linhas = [plano.serializar(linha) for linha in plano.linhas_da_sala(sala)]
    if not contexto["pode_ler"]:
        for linha in linhas:
            linha.update(texto="", autor="", revisao=0)
    contexto.update(linhas=linhas)
    return render(request, "ava/plano/tabela.html", contexto)


@gt_required
@require_POST
def entrar(request, sala_id):
    sala = _obter_sala(request, sala_id)
    if sala.gt_id:
        from ava.views.gt import inscricao_solicitar
        return inscricao_solicitar(request, sala_id)
    try:
        plano.inscrever(request.user, sala)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("ava:gt_sala_trabalho", sala_id=sala.pk)


@gt_required
@never_cache
@require_http_methods(["GET", "POST"])
def celulas(request, sala_id):
    sala = _obter_sala(request, sala_id)
    if sala.gt_id or not plano.pode_ler(request.user, sala):
        raise PermissionDenied
    if request.method == "GET":
        return JsonResponse({"linhas": [plano.serializar(linha) for linha in plano.linhas_da_sala(sala)], "editavel": plano.pode_editar(request.user, sala)})
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError
        if dados.get("acao") == "adicionar":
            linha = plano.adicionar_linha(sala, request.user, dados.get("tipo"), dados.get("objetivo_id"))
            return JsonResponse({"linha": plano.serializar(linha)}, status=201)
        if type(dados.get("id")) is not int:
            raise ValidationError("Linha inválida.")
        linha, salva = plano.salvar_celula(sala, request.user, dados["id"], dados.get("texto"), dados.get("revisao"))
        return JsonResponse({"linha": plano.serializar(linha)}, status=200 if salva else 409)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return JsonResponse({"erro": "Dados inválidos."}, status=400)
    except ValidationError as exc:
        return JsonResponse({"erro": " ".join(exc.messages)}, status=400)
    except LinhaPlanoEducacao.DoesNotExist:
        raise Http404


@gt_required
def participantes(request, sala_id=None):
    if sala_id:
        sala = _obter_sala(request, sala_id)
        if sala.gt_id:
            from ava.views.gt import sala_inscricoes
            return sala_inscricoes(request, sala_id)
        cliente, ciclo = sala.cliente, sala.ciclo
        contexto = _contexto_sala(request, sala, "participantes")
    else:
        cliente, ciclo, _ = _ciclo(request)
        sala = None
        contexto = _contexto_base(request, cliente)
    if not e_admin_referencial(request.user):
        raise PermissionDenied
    inscricoes = InscricaoSalaGT.raw_objects.filter(is_deleted=False, estado="confirmada", sala__in=_salas(ciclo)).select_related("usuario", "sala__objetivo")
    if sala:
        inscricoes = inscricoes.filter(sala=sala)
    contexto.update(ciclo_atual=ciclo, inscricoes=inscricoes.order_by("usuario__nome", "sala__objetivo__ordem"),
                    papel_choices=[("participante", "Editor"), ("leitor", "Leitor"), ("coordenacao", "Coordenação"), ("relatoria", "Relatoria")], aba="participantes")
    return render(request, "ava/plano/participantes.html", contexto)


@gt_admin_required
@require_POST
def papel(request, sala_id, inscricao_id):
    sala = _obter_sala(request, sala_id)
    inscricao = get_object_or_404(InscricaoSalaGT.raw_objects, pk=inscricao_id, sala=sala, is_deleted=False)
    try:
        SalaGTService.definir_papel(inscricao, request.user, papel=request.POST.get("papel"))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, "Papel atualizado.")
    return redirect(f"{reverse('ava:gt_participantes')}?municipio={sala.cliente_id}&ciclo={sala.ciclo_id}")


class CicloSimplesForm(forms.ModelForm):
    class Meta:
        model = CicloReferencial
        fields = ["nome", "descricao", "inicio", "fim", "ativo"]
        widgets = {"nome": forms.TextInput(attrs={"class": "form-control"}),
                   "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
                   "inicio": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"}),
                   "fim": forms.DateInput(format="%Y-%m-%d", attrs={"class": "form-control", "type": "date"})}


@gt_admin_required
def ciclo_form(request, ciclo_id=None):
    cliente = _cliente_atual(request)
    instancia = get_object_or_404(CicloReferencial.raw_objects, cliente=cliente, pk=ciclo_id, is_deleted=False) if ciclo_id else CicloReferencial(cliente=cliente, inscricoes_abertas=True)
    form = CicloSimplesForm(request.POST if request.method == "POST" else None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ciclo = form.save()
            plano.preparar_ciclo(ciclo)
        return redirect(f"{reverse('ava:gt_salas')}?municipio={cliente.pk}&ciclo={ciclo.pk}")
    contexto = _contexto_base(request, cliente)
    contexto.update(form=form, ciclo=instancia, titulo_pagina="Editar ciclo" if ciclo_id else "Novo ciclo")
    return render(request, "ava/plano/ciclo_form.html", contexto)


@gt_required
@never_cache
def exportar(request, sala_id=None):
    if sala_id:
        sala = _obter_sala(request, sala_id)
        if sala.gt_id:
            from ava.views.gt import sala_documentos
            return sala_documentos(request, sala_id)
        if not plano.pode_ler(request.user, sala):
            raise PermissionDenied
        cliente, ciclo = sala.cliente, sala.ciclo
        salas = [sala]
        contexto = _contexto_sala(request, sala, "exportar")
    else:
        cliente, ciclo, _ = _ciclo(request)
        salas = _salas(ciclo)
        if not e_admin_referencial(request.user):
            salas = salas.filter(inscricoes__usuario=request.user, inscricoes__is_deleted=False, inscricoes__estado="confirmada").distinct()
        salas = list(salas)
        contexto = _contexto_base(request, cliente)
    formato = request.GET.get("formato")
    if formato in {"csv", "docx"}:
        if not salas:
            raise PermissionDenied("Inscreva-se em uma sala para exportar seu trabalho.")
        nome = slugify(ciclo.nome) or "plano-educacao"
        if sala_id:
            nome += f"-objetivo-{sala.objetivo.ordem}"
        if formato == "csv":
            resposta = HttpResponse(content_type="text/csv; charset=utf-8")
            resposta.write("\ufeff")
            writer = csv.writer(resposta, delimiter=";")
            writer.writerow(["Categoria", "Item", "Texto"])
            def seguro(texto):
                return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r")) else texto
            for item in salas:
                for linha in plano.linhas_da_sala(item):
                    writer.writerow([seguro(item.objetivo.titulo), linha.rotulo, seguro(linha.texto)])
        else:
            from docx import Document
            from docx.shared import Pt
            documento = Document()
            documento.styles["Normal"].font.name = "Arial"
            documento.styles["Normal"].font.size = Pt(11)
            documento.add_heading(ciclo.nome, 0)
            documento.add_paragraph(cliente.nome)
            documento.add_paragraph(f"Exportado em {timezone.localtime():%d/%m/%Y às %H:%M}")
            for indice, item in enumerate(salas):
                if indice:
                    documento.add_page_break()
                documento.add_heading(f"{item.objetivo.ordem}) {item.objetivo.titulo}", level=1)
                tabela = documento.add_table(rows=1, cols=2)
                tabela.style = "Table Grid"
                tabela.rows[0].cells[0].text = "Objetivos e metas"
                tabela.rows[0].cells[1].text = "Texto produzido"
                for linha in plano.linhas_da_sala(item):
                    celulas = tabela.add_row().cells
                    celulas[0].text, celulas[1].text = linha.rotulo, linha.texto
            buffer = io.BytesIO()
            documento.save(buffer)
            resposta = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        resposta["Content-Disposition"] = f'attachment; filename="{nome}.{formato}"'
        resposta["Cache-Control"] = "private, no-store"
        resposta["X-Content-Type-Options"] = "nosniff"
        return resposta
    contexto.update(ciclo_atual=ciclo, salas_exportar=salas, aba="exportar")
    return render(request, "ava/plano/exportar.html", contexto)
