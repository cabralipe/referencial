"""Autorização das salas de GT.

Toda capacidade é resolvida aqui, no servidor, a partir do papel global do
usuário (``core.Usuario.Role``) e do vínculo com a sala
(:class:`ava.models.gt_sala.InscricaoSalaGT`). As views e os serviços consultam
este módulo; o template apenas reflete o que já foi decidido aqui.

O padrão é negar: sem vínculo ativo e sem papel de visão global, o usuário só
enxerga a lista de salas e o conteúdo publicado.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet

from ava.models.gt_sala import InscricaoSalaGT, SalaGT, TrabalhoGT
from core.models import Usuario


#: Configura ciclo, objetivos, salas, capacidade, papéis; reabre e arquiva.
ROLES_ADMIN_REFERENCIAL = {
    Usuario.Role.SUPER_ADMIN,
    Usuario.Role.ADMIN_CLIENTE,
}

#: Acompanham todos os GTs do município (inclui rascunhos) e exportam documentos.
ROLES_VISAO_GLOBAL = ROLES_ADMIN_REFERENCIAL | {
    Usuario.Role.ARTICULADOR,
    Usuario.Role.REVISOR,
}

#: Papéis que podem pedir inscrição em uma sala.
ROLES_PODEM_SE_INSCREVER = {
    Usuario.Role.ADMIN_CLIENTE,
    Usuario.Role.ARTICULADOR,
    Usuario.Role.REVISOR,
    Usuario.Role.MEMBRO_GT,
    Usuario.Role.DIRETOR,
    Usuario.Role.COORDENADOR_PEDAGOGICO,
    Usuario.Role.PROFESSOR,
    Usuario.Role.LEITOR,
}


def e_admin_referencial(usuario) -> bool:
    return getattr(usuario, "role", None) in ROLES_ADMIN_REFERENCIAL


def tem_visao_global(usuario) -> bool:
    return getattr(usuario, "role", None) in ROLES_VISAO_GLOBAL


def obter_inscricao(usuario, sala: SalaGT) -> InscricaoSalaGT | None:
    """Inscrição (de qualquer estado) do usuário na sala, se existir."""

    if not getattr(usuario, "is_authenticated", False) or not sala.pk:
        return None
    cache = getattr(usuario, "_gt_inscricoes_cache", None)
    if cache is None:
        cache = {}
        setattr(usuario, "_gt_inscricoes_cache", cache)
    if sala.pk not in cache:
        cache[sala.pk] = (
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala_id=sala.pk, usuario_id=usuario.pk
            )
            .order_by("-id")
            .first()
        )
    return cache[sala.pk]


@dataclass(frozen=True)
class AcessoSala:
    """Capacidades do usuário em uma sala específica."""

    sala: SalaGT
    papel: str | None
    estado_inscricao: str | None
    admin: bool
    visao_global: bool
    coordenacao: bool
    relatoria: bool
    participante: bool

    # -- leitura --
    pode_ver: bool
    pode_ver_rascunhos: bool
    pode_ver_frequencia_da_sala: bool

    # -- escrita --
    pode_editar_conteudo: bool
    pode_submeter_revisao: bool
    pode_aprovar_conteudo: bool
    pode_publicar_conteudo: bool
    pode_solicitar_ajustes: bool
    pode_reabrir_conteudo: bool

    pode_gerir_inscricoes: bool
    pode_gerir_papeis: bool
    pode_gerir_reunioes: bool
    pode_lancar_presenca: bool
    pode_validar_presenca: bool
    pode_reabrir_presenca: bool
    pode_editar_ata: bool
    pode_validar_ata: bool
    pode_exportar: bool
    pode_configurar_sala: bool

    def exigir(self, capacidade: str, mensagem: str | None = None) -> None:
        if not getattr(self, capacidade, False):
            raise PermissionDenied(
                mensagem or "Você não possui permissão para esta ação nesta sala de GT."
            )


def acesso_a_sala(usuario, sala: SalaGT) -> AcessoSala:
    """Resolve as capacidades do usuário na sala — sempre do lado do servidor."""

    admin = e_admin_referencial(usuario)
    global_ = tem_visao_global(usuario)
    inscricao = obter_inscricao(usuario, sala)
    ativa = bool(inscricao and inscricao.ativa)
    papel = inscricao.papel if inscricao else None
    estado_inscricao = inscricao.estado if inscricao else None

    coordenacao = bool(ativa and papel == InscricaoSalaGT.Papel.COORDENACAO)
    relatoria = bool(ativa and papel == InscricaoSalaGT.Papel.RELATORIA) or coordenacao
    participante = bool(ativa and papel == InscricaoSalaGT.Papel.PARTICIPANTE)

    sala_editavel = sala.editavel
    coord_ou_admin = coordenacao or admin

    participante_colabora = bool(
        participante and sala.participantes_editam_conteudo and sala_editavel
    )

    pode_editar_conteudo = bool(sala_editavel and (relatoria or admin)) or participante_colabora

    return AcessoSala(
        sala=sala,
        papel=papel,
        estado_inscricao=estado_inscricao,
        admin=admin,
        visao_global=global_,
        coordenacao=coordenacao,
        relatoria=relatoria,
        participante=participante,
        pode_ver=bool(global_ or ativa),
        pode_ver_rascunhos=bool(global_ or ativa),
        pode_ver_frequencia_da_sala=bool(global_ or coordenacao or relatoria),
        pode_editar_conteudo=pode_editar_conteudo,
        pode_submeter_revisao=bool(sala_editavel and (relatoria or admin)),
        pode_aprovar_conteudo=coord_ou_admin,
        pode_publicar_conteudo=coord_ou_admin,
        pode_solicitar_ajustes=coord_ou_admin,
        pode_reabrir_conteudo=admin,
        pode_gerir_inscricoes=coord_ou_admin,
        # Ninguém concede papel a si mesmo: a coordenação distribui relatoria e
        # participação, mas só o administrador define/retira coordenação.
        pode_gerir_papeis=coord_ou_admin,
        pode_gerir_reunioes=bool(coordenacao or relatoria or admin),
        pode_lancar_presenca=bool(coordenacao or relatoria or admin),
        pode_validar_presenca=coord_ou_admin,
        pode_reabrir_presenca=coord_ou_admin,
        pode_editar_ata=bool(coordenacao or relatoria or admin),
        pode_validar_ata=coord_ou_admin,
        pode_exportar=bool(global_ or coordenacao or relatoria),
        pode_configurar_sala=admin,
    )


def exigir_acesso(usuario, sala: SalaGT, capacidade: str, mensagem: str | None = None) -> AcessoSala:
    acesso = acesso_a_sala(usuario, sala)
    acesso.exigir(capacidade, mensagem)
    return acesso


def pode_ver_conteudo(acesso: AcessoSala, trabalho: TrabalhoGT | None) -> bool:
    """Conteúdo em rascunho só é visível a quem tem vínculo ou visão global."""

    if trabalho is None:
        return acesso.pode_ver
    if acesso.pode_ver_rascunhos:
        return True
    return trabalho.consolidavel


def salas_visiveis(usuario, cliente_ids) -> QuerySet[SalaGT]:
    """Salas que o usuário pode abrir, já isoladas por município.

    Usuários sem visão global veem as salas às quais estão vinculados; a lista
    geral continua acessível (sem conteúdo restrito) por outra consulta.
    """

    qs = (
        SalaGT.raw_objects.filter(is_deleted=False, cliente_id__in=list(cliente_ids))
        .select_related("cliente", "ciclo", "objetivo", "gt")
    )
    if tem_visao_global(usuario):
        return qs
    return qs.filter(
        Q(
            inscricoes__usuario_id=usuario.pk,
            inscricoes__is_deleted=False,
            inscricoes__estado=InscricaoSalaGT.Estado.CONFIRMADA,
        )
    ).distinct()


def salas_do_catalogo(usuario, cliente_ids) -> QuerySet[SalaGT]:
    """Todas as salas do município para a vitrine de inscrição.

    A vitrine mostra objetivo, ocupação, situação e coordenação — nunca o
    conteúdo em rascunho, o diagnóstico ou a frequência.
    """

    return (
        SalaGT.raw_objects.filter(is_deleted=False, cliente_id__in=list(cliente_ids))
        .select_related("cliente", "ciclo", "objetivo", "gt")
        .order_by("objetivo__ordem", "objetivo__codigo")
    )
