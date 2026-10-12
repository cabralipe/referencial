"""Regras de ciclo, salas, inscrição, capacidade e papéis dos GTs."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from ava.models.gt_sala import (
    CicloReferencial,
    InscricaoSalaGT,
    ObjetivoReferencial,
    SalaGT,
    TrabalhoGT,
)
from ava.services.audit_service import AVAAuditService, diff_de_campos
from ava.services.gt_access import e_admin_referencial
from curriculum.models import GT


CAMPOS_AUDITADOS_INSCRICAO = ["sala_id", "usuario_id", "estado", "papel", "ordem_espera"]


def _notificar(usuario_id: int, cliente_id: int, tipo: str, payload: dict) -> None:
    """Grava a notificação in-app da mudança de estado da inscrição.

    Usa o mesmo modelo do inbox já existente (``notifications.Notificacao``,
    lido por ``GET /api/v1/notificacoes``) e respeita a flag
    ``ff.notifications.enabled``. Diferente de
    ``notifications.services.criar_notificacao``, **não** publica em Channels
    nem enfileira e-mail no Celery: a inscrição não pode ficar presa esperando
    Redis/SMTP, e o requisito é comunicar a mudança sem tornar um serviço
    externo obrigatório. Falhas aqui nunca derrubam a operação de negócio.
    """

    try:
        from core.models import Cliente
        from core.utils import flag_ativa
        from notifications.models import Notificacao

        cliente = Cliente.objects.filter(pk=cliente_id).first()
        if not cliente or not flag_ativa(cliente, "ff.notifications.enabled"):
            return
        Notificacao.objects.create(
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            tipo=tipo,
            payload_json=payload,
        )
    except Exception:  # pragma: no cover - notificação é best-effort
        return


class SalaGTService:
    """Criação de salas, inscrição com capacidade atômica e papéis por sala."""

    # ------------------------------------------------------------------
    # Salas e trabalho
    # ------------------------------------------------------------------
    @staticmethod
    def garantir_trabalho(sala: SalaGT) -> TrabalhoGT:
        trabalho = TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).first()
        if trabalho is not None:
            return trabalho
        trabalho = TrabalhoGT(cliente_id=sala.cliente_id, sala=sala)
        trabalho.save()
        return trabalho

    @staticmethod
    @transaction.atomic
    def gerar_salas_do_ciclo(
        ciclo: CicloReferencial,
        usuario,
        *,
        criar_gt_ausente: bool = False,
        capacidade: int | None = None,
    ) -> dict[str, int]:
        """Cria uma sala por objetivo ativo do município, sem duplicar nada.

        Quando ``criar_gt_ausente`` é falso, objetivos sem GT correspondente
        ficam pendentes e são devolvidos na contagem — o administrador escolhe
        o GT manualmente em vez de o sistema inventar um cadastro.
        """

        if not e_admin_referencial(usuario):
            raise PermissionDenied("Apenas a administração do Referencial gera as salas do ciclo.")

        objetivos = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente_id=ciclo.cliente_id, ativo=True
        ).order_by("ordem", "codigo")

        criadas = 0
        existentes = 0
        sem_gt = 0
        etapa = (ciclo.nome or "Referencial")[:120]

        for objetivo in objetivos:
            if SalaGT.raw_objects.filter(
                is_deleted=False, cliente_id=ciclo.cliente_id, ciclo=ciclo, objetivo=objetivo
            ).exists():
                existentes += 1
                continue

            nome_gt = f"GT {objetivo.codigo} - {objetivo.titulo}"[:255]
            gt = GT.raw_objects.filter(
                is_deleted=False, cliente_id=ciclo.cliente_id, nome=nome_gt
            ).first()
            if gt is None and criar_gt_ausente:
                gt = GT.objects.create(
                    cliente_id=ciclo.cliente_id, nome=nome_gt, etapa=etapa
                )
            if gt is None:
                sem_gt += 1
                continue
            if SalaGT.raw_objects.filter(
                is_deleted=False, cliente_id=ciclo.cliente_id, ciclo=ciclo, gt=gt
            ).exists():
                existentes += 1
                continue

            sala = SalaGT(
                cliente_id=ciclo.cliente_id,
                ciclo=ciclo,
                objetivo=objetivo,
                gt=gt,
                capacidade=capacidade,
            )
            sala.full_clean()
            sala.save()
            SalaGTService.garantir_trabalho(sala)
            AVAAuditService.registrar(
                cliente_id=sala.cliente_id,
                usuario=usuario,
                entidade="ava.SalaGT",
                entidade_id=sala.pk,
                acao="criada",
                diff={"objetivo": objetivo.codigo, "gt": gt.nome, "ciclo": ciclo.nome},
            )
            criadas += 1

        return {"criadas": criadas, "existentes": existentes, "sem_gt": sem_gt}

    @staticmethod
    @transaction.atomic
    def alterar_situacao(sala: SalaGT, usuario, *, situacao: str, justificativa: str = "") -> SalaGT:
        if not e_admin_referencial(usuario):
            raise PermissionDenied("Apenas a administração do Referencial altera a situação da sala.")
        if situacao not in dict(SalaGT.Situacao.choices):
            raise ValidationError({"situacao": "Situação inválida."})
        if situacao in {SalaGT.Situacao.ARQUIVADA, SalaGT.Situacao.CONCLUIDA} and not (
            justificativa or ""
        ).strip():
            raise ValidationError(
                {"justificativa": "Registre a justificativa para concluir ou arquivar a sala."}
            )

        anterior = sala.situacao
        sala.situacao = situacao
        sala.justificativa_situacao = justificativa or ""
        campos = ["situacao", "justificativa_situacao", "updated_at"]
        if situacao == SalaGT.Situacao.ARQUIVADA:
            sala.arquivada_em = timezone.now()
            sala.arquivada_por = usuario
            campos += ["arquivada_em", "arquivada_por"]
        else:
            sala.arquivada_em = None
            sala.arquivada_por = None
            campos += ["arquivada_em", "arquivada_por"]
        sala.save(update_fields=campos)
        AVAAuditService.registrar(
            cliente_id=sala.cliente_id,
            usuario=usuario,
            entidade="ava.SalaGT",
            entidade_id=sala.pk,
            acao="situacao_alterada",
            diff={"de": anterior, "para": situacao, "justificativa": justificativa or ""},
        )
        return sala

    # ------------------------------------------------------------------
    # Capacidade
    # ------------------------------------------------------------------
    @staticmethod
    def _reservar_vaga(sala: SalaGT) -> bool:
        """Reserva uma vaga de forma atômica no banco.

        Usa ``UPDATE ... WHERE vagas_ocupadas < capacidade`` em vez de ler e
        depois gravar: duas requisições simultâneas disputam o mesmo UPDATE e
        apenas uma consegue ocupar a última vaga, em qualquer backend suportado
        (inclusive SQLite, que não oferece ``SELECT ... FOR UPDATE``).
        """

        if sala.capacidade is None:
            SalaGT.raw_objects.filter(pk=sala.pk).update(
                vagas_ocupadas=F("vagas_ocupadas") + 1
            )
            sala.refresh_from_db(fields=["vagas_ocupadas"])
            return True

        atualizadas = SalaGT.raw_objects.filter(
            pk=sala.pk, vagas_ocupadas__lt=sala.capacidade
        ).update(vagas_ocupadas=F("vagas_ocupadas") + 1)
        sala.refresh_from_db(fields=["vagas_ocupadas", "capacidade"])
        return bool(atualizadas)

    @staticmethod
    def _liberar_vaga(sala: SalaGT) -> None:
        SalaGT.raw_objects.filter(pk=sala.pk, vagas_ocupadas__gt=0).update(
            vagas_ocupadas=F("vagas_ocupadas") - 1
        )
        sala.refresh_from_db(fields=["vagas_ocupadas"])

    @staticmethod
    def _proxima_posicao_espera(sala: SalaGT) -> int:
        maior = (
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala_id=sala.pk, estado=InscricaoSalaGT.Estado.LISTA_ESPERA
            ).aggregate(maior=Max("ordem_espera"))
            or {}
        ).get("maior")
        return int(maior or 0) + 1

    # ------------------------------------------------------------------
    # Inscrição
    # ------------------------------------------------------------------
    @staticmethod
    def _validar_limite_de_salas(sala: SalaGT, usuario_alvo, inscricao_atual=None) -> None:
        limite = sala.ciclo.max_salas_por_participante
        if not limite:
            return
        qs = InscricaoSalaGT.raw_objects.filter(
            is_deleted=False,
            cliente_id=sala.cliente_id,
            sala__ciclo_id=sala.ciclo_id,
            usuario_id=usuario_alvo.pk,
            estado__in=list(InscricaoSalaGT.ESTADOS_EM_DISPUTA),
        )
        if inscricao_atual is not None and inscricao_atual.pk:
            qs = qs.exclude(pk=inscricao_atual.pk)
        if qs.count() >= limite:
            raise ValidationError(
                f"Este ciclo permite a participação em no máximo {limite} GT(s)."
            )

    @staticmethod
    @transaction.atomic
    def solicitar_inscricao(
        sala: SalaGT,
        solicitante,
        *,
        usuario_alvo=None,
        forcar_confirmacao: bool = False,
    ) -> InscricaoSalaGT:
        """Pedido de inscrição do próprio usuário ou inscrição feita pela gestão."""

        usuario_alvo = usuario_alvo or solicitante
        inscrevendo_outro = usuario_alvo.pk != solicitante.pk

        if inscrevendo_outro or forcar_confirmacao:
            from ava.services.gt_access import acesso_a_sala

            acesso_a_sala(solicitante, sala).exigir(
                "pode_gerir_inscricoes",
                "Apenas a coordenação do GT ou a administração inscreve outras pessoas.",
            )
        elif not sala.aceita_inscricao:
            raise ValidationError("As inscrições desta sala não estão abertas.")

        if sala.situacao not in SalaGT.SITUACOES_ABERTAS:
            raise ValidationError("Esta sala não está recebendo participantes.")
        if getattr(usuario_alvo, "cliente_id", None) and (
            usuario_alvo.cliente_id != sala.cliente_id
        ):
            raise ValidationError("O participante pertence a outro município.")

        inscricao = InscricaoSalaGT.raw_objects.filter(
            is_deleted=False, sala_id=sala.pk, usuario_id=usuario_alvo.pk
        ).first()
        if inscricao is not None and inscricao.estado in InscricaoSalaGT.ESTADOS_EM_DISPUTA:
            raise ValidationError("Já existe uma inscrição ativa desta pessoa nesta sala.")

        SalaGTService._validar_limite_de_salas(sala, usuario_alvo, inscricao)

        if inscricao is None:
            inscricao = InscricaoSalaGT(
                cliente_id=sala.cliente_id,
                sala=sala,
                usuario=usuario_alvo,
            )
        inscricao.solicitada_em = timezone.now()
        inscricao.ordem_espera = None
        inscricao.justificativa = ""
        inscricao.decidida_em = None
        inscricao.decidida_por = None
        if inscricao.papel not in dict(InscricaoSalaGT.Papel.choices):
            inscricao.papel = InscricaoSalaGT.Papel.PARTICIPANTE

        confirmar = forcar_confirmacao or sala.ciclo.confirmacao_automatica
        if confirmar:
            if SalaGTService._reservar_vaga(sala):
                inscricao.estado = InscricaoSalaGT.Estado.CONFIRMADA
                inscricao.decidida_em = timezone.now()
                inscricao.decidida_por = solicitante
            elif sala.aceita_lista_espera:
                inscricao.estado = InscricaoSalaGT.Estado.LISTA_ESPERA
                inscricao.ordem_espera = SalaGTService._proxima_posicao_espera(sala)
            else:
                raise ValidationError(
                    "Esta sala está lotada e não possui lista de espera habilitada."
                )
        else:
            inscricao.estado = InscricaoSalaGT.Estado.SOLICITADA

        inscricao.full_clean()
        inscricao.save()
        if inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA:
            SalaGTService._sincronizar_membros_do_gt(sala)
        SalaGTService._auditar_inscricao(inscricao, solicitante, "inscricao_solicitada")
        _notificar(
            usuario_alvo.pk,
            sala.cliente_id,
            "gt.inscricao",
            {
                "sala": sala.pk,
                "objetivo": sala.objetivo.codigo,
                "estado": inscricao.estado,
            },
        )
        return inscricao

    @staticmethod
    @transaction.atomic
    def aprovar_inscricao(inscricao: InscricaoSalaGT, responsavel) -> InscricaoSalaGT:
        sala = inscricao.sala
        from ava.services.gt_access import acesso_a_sala

        acesso_a_sala(responsavel, sala).exigir("pode_gerir_inscricoes")

        if inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA:
            return inscricao
        if inscricao.estado not in {
            InscricaoSalaGT.Estado.SOLICITADA,
            InscricaoSalaGT.Estado.LISTA_ESPERA,
        }:
            raise ValidationError("Somente inscrições solicitadas ou em lista de espera podem ser aprovadas.")

        SalaGTService._validar_limite_de_salas(sala, inscricao.usuario, inscricao)

        if not SalaGTService._reservar_vaga(sala):
            if not sala.aceita_lista_espera:
                raise ValidationError(
                    "Esta sala está lotada e não possui lista de espera habilitada."
                )
            # Sem vaga: a inscrição vai (ou permanece) para a fila, sempre com
            # posição definida — nenhuma vaga é prometida antes da confirmação.
            if inscricao.estado != InscricaoSalaGT.Estado.LISTA_ESPERA:
                inscricao.estado = InscricaoSalaGT.Estado.LISTA_ESPERA
                inscricao.ordem_espera = SalaGTService._proxima_posicao_espera(sala)
                inscricao.save(update_fields=["estado", "ordem_espera", "updated_at"])
                SalaGTService._auditar_inscricao(
                    inscricao, responsavel, "inscricao_para_lista_espera"
                )
            return inscricao

        inscricao.estado = InscricaoSalaGT.Estado.CONFIRMADA
        inscricao.ordem_espera = None
        inscricao.decidida_em = timezone.now()
        inscricao.decidida_por = responsavel
        inscricao.save(
            update_fields=["estado", "ordem_espera", "decidida_em", "decidida_por", "updated_at"]
        )
        SalaGTService._sincronizar_membros_do_gt(sala)
        SalaGTService._auditar_inscricao(inscricao, responsavel, "inscricao_confirmada")
        _notificar(
            inscricao.usuario_id,
            sala.cliente_id,
            "gt.inscricao",
            {"sala": sala.pk, "objetivo": sala.objetivo.codigo, "estado": inscricao.estado},
        )
        return inscricao

    @staticmethod
    @transaction.atomic
    def recusar_inscricao(
        inscricao: InscricaoSalaGT, responsavel, *, justificativa: str = ""
    ) -> InscricaoSalaGT:
        sala = inscricao.sala
        from ava.services.gt_access import acesso_a_sala

        acesso_a_sala(responsavel, sala).exigir("pode_gerir_inscricoes")
        if not (justificativa or "").strip():
            raise ValidationError({"justificativa": "Registre o motivo da recusa."})

        era_confirmada = inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA
        inscricao.estado = InscricaoSalaGT.Estado.RECUSADA
        inscricao.ordem_espera = None
        inscricao.justificativa = justificativa
        inscricao.decidida_em = timezone.now()
        inscricao.decidida_por = responsavel
        inscricao.save(
            update_fields=[
                "estado",
                "ordem_espera",
                "justificativa",
                "decidida_em",
                "decidida_por",
                "updated_at",
            ]
        )
        if era_confirmada:
            SalaGTService._liberar_vaga(sala)
            SalaGTService._sincronizar_membros_do_gt(sala)
        SalaGTService._auditar_inscricao(inscricao, responsavel, "inscricao_recusada")
        _notificar(
            inscricao.usuario_id,
            sala.cliente_id,
            "gt.inscricao",
            {"sala": sala.pk, "objetivo": sala.objetivo.codigo, "estado": inscricao.estado},
        )
        return inscricao

    @staticmethod
    @transaction.atomic
    def cancelar_inscricao(
        inscricao: InscricaoSalaGT, usuario, *, justificativa: str = ""
    ) -> InscricaoSalaGT:
        """Desistência do próprio participante ou remoção pela gestão."""

        sala = inscricao.sala
        if inscricao.usuario_id != usuario.pk:
            from ava.services.gt_access import acesso_a_sala

            acesso_a_sala(usuario, sala).exigir(
                "pode_gerir_inscricoes",
                "Apenas a coordenação do GT ou a administração remove participantes.",
            )

        era_confirmada = inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA
        inscricao.estado = InscricaoSalaGT.Estado.CANCELADA
        inscricao.ordem_espera = None
        inscricao.justificativa = justificativa or ""
        inscricao.decidida_em = timezone.now()
        inscricao.decidida_por = usuario
        inscricao.save(
            update_fields=[
                "estado",
                "ordem_espera",
                "justificativa",
                "decidida_em",
                "decidida_por",
                "updated_at",
            ]
        )
        if era_confirmada:
            SalaGTService._liberar_vaga(sala)
            SalaGTService._sincronizar_membros_do_gt(sala)
        SalaGTService._auditar_inscricao(inscricao, usuario, "inscricao_cancelada")
        return inscricao

    @staticmethod
    @transaction.atomic
    def promover_lista_espera(sala: SalaGT, responsavel, *, quantidade: int = 1) -> list[InscricaoSalaGT]:
        """Promove, em ordem, quem está na lista de espera — nunca automático."""

        from ava.services.gt_access import acesso_a_sala

        acesso_a_sala(responsavel, sala).exigir("pode_gerir_inscricoes")

        promovidas: list[InscricaoSalaGT] = []
        fila = InscricaoSalaGT.raw_objects.filter(
            is_deleted=False, sala_id=sala.pk, estado=InscricaoSalaGT.Estado.LISTA_ESPERA
        ).order_by("ordem_espera", "solicitada_em", "id")
        for inscricao in fila[: max(quantidade, 0)]:
            if not SalaGTService._reservar_vaga(sala):
                break
            inscricao.estado = InscricaoSalaGT.Estado.CONFIRMADA
            inscricao.ordem_espera = None
            inscricao.decidida_em = timezone.now()
            inscricao.decidida_por = responsavel
            inscricao.save(
                update_fields=[
                    "estado",
                    "ordem_espera",
                    "decidida_em",
                    "decidida_por",
                    "updated_at",
                ]
            )
            SalaGTService._auditar_inscricao(inscricao, responsavel, "inscricao_promovida")
            _notificar(
                inscricao.usuario_id,
                sala.cliente_id,
                "gt.inscricao",
                {"sala": sala.pk, "objetivo": sala.objetivo.codigo, "estado": inscricao.estado},
            )
            promovidas.append(inscricao)
        if promovidas:
            SalaGTService._sincronizar_membros_do_gt(sala)
        return promovidas

    @staticmethod
    @transaction.atomic
    def mover_inscricao(
        inscricao: InscricaoSalaGT, destino: SalaGT, responsavel
    ) -> InscricaoSalaGT:
        """Move o participante para outra sala do mesmo ciclo."""

        origem = inscricao.sala
        from ava.services.gt_access import acesso_a_sala

        acesso_a_sala(responsavel, origem).exigir("pode_gerir_inscricoes")
        acesso_a_sala(responsavel, destino).exigir("pode_gerir_inscricoes")

        if destino.pk == origem.pk:
            return inscricao
        if destino.cliente_id != origem.cliente_id or destino.ciclo_id != origem.ciclo_id:
            raise ValidationError("Só é possível mover entre salas do mesmo ciclo e município.")
        if InscricaoSalaGT.raw_objects.filter(
            is_deleted=False, sala_id=destino.pk, usuario_id=inscricao.usuario_id
        ).exists():
            raise ValidationError("Esta pessoa já possui inscrição na sala de destino.")

        era_confirmada = inscricao.estado == InscricaoSalaGT.Estado.CONFIRMADA
        if era_confirmada and not SalaGTService._reservar_vaga(destino):
            raise ValidationError("A sala de destino está lotada.")

        inscricao.sala = destino
        inscricao.papel = InscricaoSalaGT.Papel.PARTICIPANTE
        inscricao.decidida_em = timezone.now()
        inscricao.decidida_por = responsavel
        inscricao.save(update_fields=["sala", "papel", "decidida_em", "decidida_por", "updated_at"])
        if era_confirmada:
            SalaGTService._liberar_vaga(origem)
            SalaGTService._sincronizar_membros_do_gt(origem)
            SalaGTService._sincronizar_membros_do_gt(destino)
        SalaGTService._auditar_inscricao(inscricao, responsavel, "inscricao_movida")
        return inscricao

    # ------------------------------------------------------------------
    # Papéis por sala
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def definir_papel(inscricao: InscricaoSalaGT, responsavel, *, papel: str) -> InscricaoSalaGT:
        sala = inscricao.sala
        from ava.services.gt_access import acesso_a_sala

        acesso = acesso_a_sala(responsavel, sala)
        acesso.exigir("pode_gerir_papeis")

        if papel not in dict(InscricaoSalaGT.Papel.choices):
            raise ValidationError({"papel": "Papel inválido."})
        if inscricao.estado != InscricaoSalaGT.Estado.CONFIRMADA:
            raise ValidationError("Só é possível atribuir papel a inscrições confirmadas.")
        if not acesso.admin and inscricao.usuario_id == responsavel.pk:
            raise ValidationError("Você não pode alterar o seu próprio papel nesta sala.")
        if not acesso.admin and (
            papel == InscricaoSalaGT.Papel.COORDENACAO
            or inscricao.papel == InscricaoSalaGT.Papel.COORDENACAO
        ):
            raise PermissionDenied(
                "Somente a administração do Referencial define ou retira a coordenação do GT."
            )

        anterior = inscricao.papel
        inscricao.papel = papel
        inscricao.papel_concedido_por = responsavel
        inscricao.papel_concedido_em = timezone.now()
        inscricao.save(
            update_fields=["papel", "papel_concedido_por", "papel_concedido_em", "updated_at"]
        )
        AVAAuditService.registrar(
            cliente_id=sala.cliente_id,
            usuario=responsavel,
            entidade="ava.InscricaoSalaGT",
            entidade_id=inscricao.pk,
            acao="papel_alterado",
            diff={"de": anterior, "para": papel, "usuario": inscricao.usuario_id},
        )
        return inscricao

    # ------------------------------------------------------------------
    # Apoio
    # ------------------------------------------------------------------
    @staticmethod
    def _sincronizar_membros_do_gt(sala: SalaGT) -> None:
        """Mantém ``GT.membros`` alinhado às inscrições confirmadas da sala.

        O cadastro de membros continua sendo o do GT (``curriculum.GT``): a sala
        apenas reflete nele quem foi confirmado, sem criar um segundo cadastro.
        """

        confirmados = set(
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala_id=sala.pk, estado=InscricaoSalaGT.Estado.CONFIRMADA
            ).values_list("usuario_id", flat=True)
        )
        gt = sala.gt
        atuais = set(gt.membros.values_list("id", flat=True))
        adicionar = confirmados - atuais
        if adicionar:
            gt.membros.add(*adicionar)
        # Remove apenas quem entrou pela sala e deixou de estar confirmado.
        inscritos_na_sala = set(
            InscricaoSalaGT.raw_objects.filter(is_deleted=False, sala_id=sala.pk).values_list(
                "usuario_id", flat=True
            )
        )
        remover = (atuais & inscritos_na_sala) - confirmados
        if remover:
            gt.membros.remove(*remover)

    @staticmethod
    def _auditar_inscricao(inscricao: InscricaoSalaGT, usuario, acao: str) -> None:
        AVAAuditService.registrar(
            cliente_id=inscricao.cliente_id,
            usuario=usuario,
            entidade="ava.InscricaoSalaGT",
            entidade_id=inscricao.pk,
            acao=acao,
            diff=diff_de_campos(inscricao, CAMPOS_AUDITADOS_INSCRICAO),
        )

    @staticmethod
    def membros_ativos(sala: SalaGT):
        """Inscrições confirmadas da sala, base da frequência das reuniões."""

        return (
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala_id=sala.pk, estado=InscricaoSalaGT.Estado.CONFIRMADA
            )
            .select_related("usuario")
            .order_by("papel", "usuario__nome", "usuario__email")
        )
