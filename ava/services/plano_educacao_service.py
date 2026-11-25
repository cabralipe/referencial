"""Plano colaborativo: inscrição direta e gravação atômica por célula."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from ava.data.pne_2026 import CATEGORIAS_PNE, ESTRATEGIAS_PNE
from ava.models import CicloReferencial, InscricaoSalaGT, LinhaPlanoEducacao, ObjetivoReferencial, SalaGT
from ava.services.gt_access import e_admin_referencial


def pode_ler(usuario, sala):
    if not usuario.get_ava_clientes_queryset().filter(pk=sala.cliente_id).exists():
        return False
    return e_admin_referencial(usuario) or InscricaoSalaGT.raw_objects.filter(
        is_deleted=False, sala=sala, usuario=usuario, estado="confirmada"
    ).exists()


def pode_editar(usuario, sala):
    if not sala.editavel or not sala.ciclo.ativo or not pode_ler(usuario, sala):
        return False
    return e_admin_referencial(usuario) or InscricaoSalaGT.raw_objects.filter(
        is_deleted=False, sala=sala, usuario=usuario, estado="confirmada"
    ).exclude(papel="leitor").exists()


def exigir_edicao(usuario, sala):
    if not pode_editar(usuario, sala):
        raise PermissionDenied("Inscreva-se na sala para editar. Leitores têm acesso somente à leitura.")


def letra_meta(indice):
    resultado = ""
    while indice:
        indice, resto = divmod(indice - 1, 26)
        resultado = chr(97 + resto) + resultado
    return resultado


@transaction.atomic
def preparar_ciclo(ciclo):
    """Inicialização idempotente, sem modificar salas e redações anteriores."""
    ciclo = CicloReferencial.raw_objects.select_for_update().get(pk=ciclo.pk)
    if ciclo.planilha_pne_preparada:
        return
    for numero, (titulo, quantidade) in enumerate(CATEGORIAS_PNE, 1):
        objetivo, _ = ObjetivoReferencial.raw_objects.get_or_create(
            cliente_id=ciclo.cliente_id, codigo=f"PNE-{numero:02}", is_deleted=False,
            defaults={"ordem": numero, "titulo": titulo},
        )
        sala, _ = SalaGT.raw_objects.get_or_create(
            cliente_id=ciclo.cliente_id, ciclo=ciclo, objetivo=objetivo, is_deleted=False,
            defaults={"participantes_editam_conteudo": True, "situacao": "em_andamento"},
        )
        principal, _ = LinhaPlanoEducacao.raw_objects.get_or_create(
            cliente_id=ciclo.cliente_id, sala=sala, codigo=str(numero), tipo="objetivo",
            defaults={"ordem": 0},
        )
        for indice in range(1, quantidade + 1):
            LinhaPlanoEducacao.raw_objects.get_or_create(
                cliente_id=ciclo.cliente_id, sala=sala, codigo=f"{numero}.{letra_meta(indice)}", tipo="meta",
                defaults={"ordem": indice, "objetivo_relacionado": principal},
            )
        LinhaPlanoEducacao.raw_objects.bulk_create([
            LinhaPlanoEducacao(
                cliente_id=ciclo.cliente_id, sala=sala, codigo=f"{numero}.{indice}",
                tipo="estrategia", ordem=indice, objetivo_relacionado=principal,
            )
            for indice in range(1, ESTRATEGIAS_PNE[numero - 1] + 1)
        ], ignore_conflicts=True)
    ciclo.planilha_pne_preparada = True
    ciclo.save(update_fields=["planilha_pne_preparada", "updated_at"])


@transaction.atomic
def inscrever(usuario, sala):
    sala = SalaGT.raw_objects.select_for_update().select_related("ciclo").get(pk=sala.pk)
    if not sala.editavel or not sala.ciclo.ativo or not sala.inscricoes_abertas:
        raise ValidationError("Esta sala está encerrada para novas inscrições.")
    # A autorização de município é verificada pela view antes de chamar o serviço.
    if not usuario.get_ava_clientes_queryset().filter(pk=sala.cliente_id).exists():
        raise PermissionDenied
    vinculo, _ = InscricaoSalaGT.raw_objects.get_or_create(
        cliente_id=sala.cliente_id, sala=sala, usuario=usuario, is_deleted=False,
        defaults={"estado": "confirmada", "decidida_em": timezone.now()},
    )
    if vinculo.estado != "confirmada":
        vinculo.estado = "confirmada"
        vinculo.papel = "participante"
        vinculo.ordem_espera = None
        vinculo.decidida_em = timezone.now()
        vinculo.save()
    sala.recalcular_ocupacao()
    return vinculo


def linhas_da_sala(sala):
    linhas = list(LinhaPlanoEducacao.raw_objects.filter(is_deleted=False, sala=sala).select_related("editado_por"))
    principais = {linha.pk: linha for linha in linhas if linha.tipo == "objetivo"}
    return sorted(linhas, key=lambda linha: (
        principais[linha.objetivo_relacionado_id].ordem if linha.objetivo_relacionado_id in principais else linha.ordem,
        {"objetivo": 0, "meta": 1, "estrategia": 2, "indicador": 3}[linha.tipo], linha.ordem, linha.pk,
    ))


def serializar(linha):
    return {"id": linha.pk, "codigo": linha.codigo, "tipo": linha.tipo, "rotulo": linha.rotulo,
            "objetivo_id": linha.objetivo_relacionado_id, "texto": linha.texto, "revisao": linha.revisao,
            "autor": (linha.editado_por.nome or linha.editado_por.email) if linha.editado_por_id else "",
            "atualizado_em": linha.updated_at.isoformat()}


def linhas_serializadas(sala):
    linhas = linhas_da_sala(sala)
    objetivos = {linha.pk: linha.rotulo for linha in linhas if linha.tipo == "objetivo"}
    resultado = []
    for indice, linha in enumerate(linhas):
        grupo_id = linha.objetivo_relacionado_id or linha.pk
        proxima = linhas[indice + 1] if indice + 1 < len(linhas) else None
        dados = serializar(linha)
        dados["grupo_id"] = grupo_id
        dados["grupo_rotulo"] = objetivos[grupo_id]
        dados["fim_objetivo"] = proxima is None or (proxima.objetivo_relacionado_id or proxima.pk) != grupo_id
        resultado.append(dados)
    return resultado


@transaction.atomic
def salvar_celula(sala, usuario, linha_id, texto, revisao):
    exigir_edicao(usuario, sala)
    if not isinstance(texto, str) or len(texto) > 50000:
        raise ValidationError("Informe um texto com até 50.000 caracteres.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in texto):
        raise ValidationError("O texto contém caracteres de controle inválidos.")
    if type(revisao) is not int or revisao < 0:
        raise ValidationError("Revisão inválida.")
    linhas = LinhaPlanoEducacao.raw_objects.filter(is_deleted=False, sala=sala, pk=linha_id)
    # Compare-and-swap: a checagem e a escrita são uma única instrução SQL.
    gravada = linhas.filter(revisao=revisao).update(
        texto=texto, revisao=F("revisao") + 1, editado_por=usuario, updated_at=timezone.now(),
    )
    linha = linhas.select_related("editado_por").get()
    # Reenvio após perda de conexão pode ser confirmado sem escrever outra versão.
    return linha, bool(gravada or linha.texto == texto)


@transaction.atomic
def adicionar_linha(sala, usuario, tipo, objetivo_id=None):
    exigir_edicao(usuario, sala)
    SalaGT.raw_objects.select_for_update().get(pk=sala.pk)
    if tipo == "objetivo":
        ordem = (LinhaPlanoEducacao.raw_objects.filter(sala=sala, tipo="objetivo").aggregate(n=Max("ordem"))["n"] or 0) + 1
        codigo = f"{sala.objetivo.ordem}.{ordem + 1}"
        principal = None
    elif tipo in {"meta", "estrategia", "indicador"}:
        principal = LinhaPlanoEducacao.raw_objects.get(sala=sala, pk=objetivo_id, tipo="objetivo", is_deleted=False)
        ordem = (LinhaPlanoEducacao.raw_objects.filter(sala=sala, objetivo_relacionado=principal, tipo=tipo).aggregate(n=Max("ordem"))["n"] or 0) + 1
        codigo = f"{principal.codigo}.{letra_meta(ordem) if tipo == 'meta' else ordem}"
    else:
        raise ValidationError("Tipo de linha inválido.")
    return LinhaPlanoEducacao.raw_objects.create(
        cliente_id=sala.cliente_id, sala=sala, tipo=tipo, codigo=codigo, ordem=ordem,
        objetivo_relacionado=principal,
    )
