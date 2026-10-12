"""Reuniões, frequência e atas das salas de GT."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ava.models.gt_sala import (
    AtaReuniaoGT,
    InscricaoSalaGT,
    ModeloAtaGT,
    PresencaReuniaoGT,
    ReuniaoGT,
    SalaGT,
)
from ava.services.audit_service import AVAAuditService
from ava.services.gt_access import acesso_a_sala, e_admin_referencial
from ava.services.gt_sala_service import SalaGTService


class ReuniaoGTService:
    """Agenda da sala, lançamento e validação de frequência."""

    @staticmethod
    @transaction.atomic
    def salvar_reuniao(reuniao: ReuniaoGT, usuario, *, criando: bool) -> ReuniaoGT:
        acesso_a_sala(usuario, reuniao.sala).exigir("pode_gerir_reunioes")
        if criando and not reuniao.responsavel_registro_id:
            reuniao.responsavel_registro = usuario
        reuniao.full_clean()
        reuniao.save()
        AVAAuditService.registrar(
            cliente_id=reuniao.cliente_id,
            usuario=usuario,
            entidade="ava.ReuniaoGT",
            entidade_id=reuniao.pk,
            acao="criada" if criando else "atualizada",
            diff={
                "sala": reuniao.sala_id,
                "data_hora": reuniao.data_hora.isoformat() if reuniao.data_hora else None,
                "situacao": reuniao.situacao,
            },
        )
        if criando:
            ReuniaoGTService.preparar_presencas(reuniao, usuario)
        return reuniao

    # ------------------------------------------------------------------
    # Frequência
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def preparar_presencas(reuniao: ReuniaoGT, usuario) -> int:
        """Cria a lista de presença a partir dos membros confirmados do GT.

        A lista nunca é inferida por login ou acesso à sala: todo mundo entra
        como ausente e alguém responsável registra o que ocorreu.
        """

        acesso_a_sala(usuario, reuniao.sala).exigir("pode_lancar_presenca")
        if reuniao.frequencia_validada:
            raise ValidationError("A frequência já foi validada. Reabra antes de alterar a lista.")

        existentes = set(
            PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao_id=reuniao.pk
            ).values_list("usuario_id", flat=True)
        )
        criadas = 0
        for inscricao in SalaGTService.membros_ativos(reuniao.sala):
            if inscricao.usuario_id in existentes:
                continue
            presenca = PresencaReuniaoGT(
                cliente_id=reuniao.cliente_id,
                reuniao=reuniao,
                usuario_id=inscricao.usuario_id,
                situacao=PresencaReuniaoGT.Situacao.AUSENTE,
                registrado_por=usuario,
                registrado_em=timezone.now(),
            )
            presenca.save()
            criadas += 1
        return criadas

    @staticmethod
    @transaction.atomic
    def lancar_presencas(
        reuniao: ReuniaoGT,
        usuario,
        lancamentos: dict[int, dict],
    ) -> int:
        """Grava presença/ausência/justificativa de cada membro do GT."""

        acesso_a_sala(usuario, reuniao.sala).exigir("pode_lancar_presenca")
        if reuniao.frequencia_validada:
            raise ValidationError(
                "A frequência desta reunião está validada. Reabra com justificativa para corrigir."
            )
        if reuniao.situacao == ReuniaoGT.Situacao.CANCELADA:
            raise ValidationError("Não é possível lançar presença em reunião cancelada.")

        membros = {
            inscricao.usuario_id for inscricao in SalaGTService.membros_ativos(reuniao.sala)
        }
        validos = set(dict(PresencaReuniaoGT.Situacao.choices))
        alteradas = 0
        agora = timezone.now()

        for usuario_id, dados in lancamentos.items():
            if usuario_id not in membros:
                # Ignora silenciosamente quem não é membro confirmado do GT.
                continue
            situacao = dados.get("situacao")
            if situacao not in validos:
                raise ValidationError({"situacao": "Situação de presença inválida."})
            justificativa = (dados.get("justificativa") or "").strip()[:255]

            presenca = PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao_id=reuniao.pk, usuario_id=usuario_id
            ).first()
            criando = presenca is None
            if criando:
                presenca = PresencaReuniaoGT(
                    cliente_id=reuniao.cliente_id,
                    reuniao=reuniao,
                    usuario_id=usuario_id,
                    registrado_por=usuario,
                    registrado_em=agora,
                )
            anterior = None if criando else presenca.situacao
            presenca.situacao = situacao
            presenca.justificativa = (
                justificativa if situacao == PresencaReuniaoGT.Situacao.JUSTIFICADA else ""
            )
            if not criando:
                presenca.alterado_por = usuario
                presenca.alterado_em = agora
            presenca.full_clean()
            presenca.save()
            if anterior != presenca.situacao:
                alteradas += 1

        AVAAuditService.registrar(
            cliente_id=reuniao.cliente_id,
            usuario=usuario,
            entidade="ava.ReuniaoGT",
            entidade_id=reuniao.pk,
            acao="frequencia_lancada",
            diff={"alteradas": alteradas, "resumo": reuniao.resumo_frequencia()},
        )
        return alteradas

    @staticmethod
    @transaction.atomic
    def validar_frequencia(reuniao: ReuniaoGT, usuario) -> ReuniaoGT:
        acesso_a_sala(usuario, reuniao.sala).exigir(
            "pode_validar_presenca",
            "Apenas a coordenação do GT ou a administração valida a frequência.",
        )
        if reuniao.frequencia_validada:
            return reuniao
        if reuniao.situacao == ReuniaoGT.Situacao.CANCELADA:
            raise ValidationError("Reunião cancelada não possui frequência a validar.")
        if not PresencaReuniaoGT.raw_objects.filter(
            is_deleted=False, reuniao_id=reuniao.pk
        ).exists():
            raise ValidationError("Lance a frequência antes de validar.")

        reuniao.frequencia_validada = True
        reuniao.frequencia_validada_em = timezone.now()
        reuniao.frequencia_validada_por = usuario
        if reuniao.situacao == ReuniaoGT.Situacao.AGENDADA:
            reuniao.situacao = ReuniaoGT.Situacao.REALIZADA
        reuniao.save(
            update_fields=[
                "frequencia_validada",
                "frequencia_validada_em",
                "frequencia_validada_por",
                "situacao",
                "updated_at",
            ]
        )
        AVAAuditService.registrar(
            cliente_id=reuniao.cliente_id,
            usuario=usuario,
            entidade="ava.ReuniaoGT",
            entidade_id=reuniao.pk,
            acao="frequencia_validada",
            diff={"resumo": reuniao.resumo_frequencia()},
        )
        return reuniao

    @staticmethod
    @transaction.atomic
    def reabrir_frequencia(reuniao: ReuniaoGT, usuario, *, justificativa: str) -> ReuniaoGT:
        acesso_a_sala(usuario, reuniao.sala).exigir(
            "pode_reabrir_presenca",
            "Apenas a coordenação do GT ou a administração reabre a frequência.",
        )
        if not (justificativa or "").strip():
            raise ValidationError(
                {"justificativa": "Registre a justificativa da correção da frequência."}
            )
        if not reuniao.frequencia_validada:
            raise ValidationError("A frequência desta reunião já está aberta.")

        reuniao.frequencia_validada = False
        reuniao.frequencia_validada_em = None
        reuniao.frequencia_validada_por = None
        reuniao.justificativa_reabertura = justificativa
        reuniao.save(
            update_fields=[
                "frequencia_validada",
                "frequencia_validada_em",
                "frequencia_validada_por",
                "justificativa_reabertura",
                "updated_at",
            ]
        )
        AVAAuditService.registrar(
            cliente_id=reuniao.cliente_id,
            usuario=usuario,
            entidade="ava.ReuniaoGT",
            entidade_id=reuniao.pk,
            acao="frequencia_reaberta",
            diff={"justificativa": justificativa},
        )
        return reuniao

    @staticmethod
    def frequencia_do_usuario(sala: SalaGT, usuario):
        """Presenças do próprio usuário na sala — base da consulta individual."""

        return (
            PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao__sala_id=sala.pk, usuario_id=usuario.pk
            )
            .select_related("reuniao")
            .order_by("-reuniao__data_hora")
        )


class ModeloAtaGTService:
    """Modelo institucional de ata, versionado e administrável."""

    @staticmethod
    def obter_ativo(cliente_id: int) -> ModeloAtaGT | None:
        return (
            ModeloAtaGT.raw_objects.filter(is_deleted=False, cliente_id=cliente_id, ativo=True)
            .order_by("-versao", "-id")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def publicar_versao(
        cliente_id: int,
        usuario,
        *,
        nome: str,
        cabecalho: str = "",
        rodape: str = "",
        orientacoes: str = "",
        secoes: list[dict] | None = None,
    ) -> ModeloAtaGT:
        """Cria a próxima versão do modelo sem alterar as atas já geradas."""

        if not e_admin_referencial(usuario):
            raise ValidationError("Apenas a administração do Referencial publica modelos de ata.")
        nome = (nome or "").strip()
        if not nome:
            raise ValidationError({"nome": "Informe o nome do modelo."})

        ultima = (
            ModeloAtaGT.raw_objects.filter(is_deleted=False, cliente_id=cliente_id, nome=nome)
            .order_by("-versao")
            .values_list("versao", flat=True)
            .first()
        )
        ModeloAtaGT.raw_objects.filter(
            is_deleted=False, cliente_id=cliente_id, ativo=True
        ).update(ativo=False)

        modelo = ModeloAtaGT(
            cliente_id=cliente_id,
            nome=nome,
            versao=int(ultima or 0) + 1,
            ativo=True,
            cabecalho=cabecalho or "",
            rodape=rodape or "",
            orientacoes=orientacoes or "",
            secoes=secoes if secoes is not None else list(ModeloAtaGT.SECOES_PADRAO),
            created_by=usuario,
        )
        modelo.full_clean()
        modelo.save()
        AVAAuditService.registrar(
            cliente_id=cliente_id,
            usuario=usuario,
            entidade="ava.ModeloAtaGT",
            entidade_id=modelo.pk,
            acao="versao_publicada",
            diff={"nome": modelo.nome, "versao": modelo.versao},
        )
        return modelo


class AtaGTService:
    """Minuta padronizada, revisão e validação da ata."""

    CAMPOS = ["pauta", "sintese", "decisoes", "encaminhamentos", "pendencias", "assinaturas"]

    @staticmethod
    @transaction.atomic
    def garantir_minuta(reuniao: ReuniaoGT, usuario) -> AtaReuniaoGT:
        """Cria a minuta pré-preenchida apenas com dados seguros e existentes."""

        acesso_a_sala(usuario, reuniao.sala).exigir("pode_editar_ata")
        ata = AtaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao_id=reuniao.pk).first()
        if ata is not None:
            return ata

        modelo = ModeloAtaGTService.obter_ativo(reuniao.cliente_id)
        secoes = modelo.secoes_efetivas() if modelo else list(ModeloAtaGT.SECOES_PADRAO)
        ata = AtaReuniaoGT(
            cliente_id=reuniao.cliente_id,
            reuniao=reuniao,
            modelo=modelo,
            modelo_nome=modelo.nome if modelo else "Modelo padrão do sistema",
            modelo_versao=modelo.versao if modelo else 1,
            estrutura_json={
                "nome": modelo.nome if modelo else "Modelo padrão do sistema",
                "versao": modelo.versao if modelo else 1,
                "cabecalho": modelo.cabecalho if modelo else "",
                "rodape": modelo.rodape if modelo else "",
                "orientacoes": modelo.orientacoes if modelo else "",
                "secoes": secoes,
            },
            # Pré-preenchimento seguro: só o que já existe no registro da reunião.
            pauta=reuniao.pauta or "",
        )
        ata.save()
        AVAAuditService.registrar(
            cliente_id=ata.cliente_id,
            usuario=usuario,
            entidade="ava.AtaReuniaoGT",
            entidade_id=ata.pk,
            acao="minuta_criada",
            diff={"reuniao": reuniao.pk, "modelo": ata.modelo_nome, "versao": ata.modelo_versao},
        )
        return ata

    @staticmethod
    @transaction.atomic
    def salvar(ata: AtaReuniaoGT, usuario, dados: dict, *, version_esperada=None) -> AtaReuniaoGT:
        acesso_a_sala(usuario, ata.reuniao.sala).exigir("pode_editar_ata")
        if not ata.editavel:
            raise ValidationError(
                "Esta ata já está validada. Reabra com justificativa antes de alterar."
            )
        if version_esperada not in (None, ""):
            try:
                esperada = int(version_esperada)
            except (TypeError, ValueError):
                esperada = None
            if esperada is not None and esperada != ata.version:
                raise ValidationError(
                    "Outra pessoa alterou esta ata enquanto você editava. "
                    "Recarregue a página antes de salvar."
                )

        for campo in AtaGTService.CAMPOS:
            if campo in dados and dados[campo] is not None:
                setattr(ata, campo, dados[campo])
        extras = dados.get("secoes_extra")
        if isinstance(extras, dict):
            ata.secoes_extra = extras
        ata.updated_by = usuario
        ata.full_clean()
        ata.save()
        AVAAuditService.registrar(
            cliente_id=ata.cliente_id,
            usuario=usuario,
            entidade="ava.AtaReuniaoGT",
            entidade_id=ata.pk,
            acao="minuta_atualizada",
            diff={"version": ata.version, "estado": ata.estado},
        )
        return ata

    @staticmethod
    @transaction.atomic
    def enviar_para_revisao(ata: AtaReuniaoGT, usuario) -> AtaReuniaoGT:
        acesso_a_sala(usuario, ata.reuniao.sala).exigir("pode_editar_ata")
        if ata.estado != AtaReuniaoGT.Estado.MINUTA:
            raise ValidationError("Somente a minuta pode ser enviada para revisão.")
        ata.estado = AtaReuniaoGT.Estado.EM_REVISAO
        ata.updated_by = usuario
        ata.save(update_fields=["estado", "updated_by", "updated_at"])
        AVAAuditService.registrar(
            cliente_id=ata.cliente_id,
            usuario=usuario,
            entidade="ava.AtaReuniaoGT",
            entidade_id=ata.pk,
            acao="minuta_em_revisao",
        )
        return ata

    @staticmethod
    @transaction.atomic
    def validar(ata: AtaReuniaoGT, usuario) -> AtaReuniaoGT:
        acesso_a_sala(usuario, ata.reuniao.sala).exigir(
            "pode_validar_ata",
            "Apenas a coordenação do GT ou a administração valida a ata.",
        )
        if ata.validada:
            return ata
        if not (ata.sintese or "").strip():
            raise ValidationError(
                {"sintese": "Registre a síntese das discussões antes de validar a ata."}
            )
        ata.estado = AtaReuniaoGT.Estado.VALIDADA
        ata.validada_em = timezone.now()
        ata.validada_por = usuario
        ata.updated_by = usuario
        ata.save(
            update_fields=["estado", "validada_em", "validada_por", "updated_by", "updated_at"]
        )
        AVAAuditService.registrar(
            cliente_id=ata.cliente_id,
            usuario=usuario,
            entidade="ava.AtaReuniaoGT",
            entidade_id=ata.pk,
            acao="ata_validada",
        )
        return ata

    @staticmethod
    @transaction.atomic
    def reabrir(ata: AtaReuniaoGT, usuario, *, justificativa: str) -> AtaReuniaoGT:
        acesso_a_sala(usuario, ata.reuniao.sala).exigir(
            "pode_validar_ata",
            "Apenas a coordenação do GT ou a administração reabre a ata.",
        )
        if not (justificativa or "").strip():
            raise ValidationError({"justificativa": "Registre a justificativa da reabertura."})
        if not ata.validada:
            raise ValidationError("Esta ata já está editável.")
        ata.estado = AtaReuniaoGT.Estado.EM_REVISAO
        ata.validada_em = None
        ata.validada_por = None
        ata.updated_by = usuario
        ata.save(
            update_fields=["estado", "validada_em", "validada_por", "updated_by", "updated_at"]
        )
        AVAAuditService.registrar(
            cliente_id=ata.cliente_id,
            usuario=usuario,
            entidade="ava.AtaReuniaoGT",
            entidade_id=ata.pk,
            acao="ata_reaberta",
            diff={"justificativa": justificativa},
        )
        return ata

    @staticmethod
    def participantes_para_ata(reuniao: ReuniaoGT) -> list[dict]:
        """Participantes da reunião para o corpo da ata (sem justificativas)."""

        presencas = (
            PresencaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao_id=reuniao.pk)
            .select_related("usuario")
            .order_by("usuario__nome", "usuario__email")
        )
        papeis = {
            inscricao.usuario_id: inscricao.get_papel_display()
            for inscricao in SalaGTService.membros_ativos(reuniao.sala)
        }
        return [
            {
                "nome": presenca.usuario.nome or presenca.usuario.email,
                "papel": papeis.get(presenca.usuario_id, InscricaoSalaGT.Papel.PARTICIPANTE.label),
                "presente": presenca.situacao == PresencaReuniaoGT.Situacao.PRESENTE,
                "situacao": presenca.get_situacao_display(),
            }
            for presenca in presencas
        ]
