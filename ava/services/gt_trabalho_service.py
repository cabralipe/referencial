"""Diagnóstico, quadro do objetivo, metas, estratégias e fluxo de aprovação."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ava.models.gt_sala import (
    AtaReuniaoGT,
    EstrategiaGT,
    MetaGT,
    SalaGT,
    TrabalhoGT,
    VersaoTrabalhoGT,
)
from ava.services.audit_service import AVAAuditService
from ava.services.gt_access import acesso_a_sala


CAMPOS_DIAGNOSTICO = [
    "diagnostico_nao_aplicavel",
    "diagnostico_situacao",
    "diagnostico_evidencias",
    "diagnostico_desafios",
    "diagnostico_potencialidades",
    "diagnostico_publico",
]

CAMPOS_QUADRO = ["objetivo_proposto", "observacoes", "pendencias"]


class ConflitoDeVersao(ValidationError):
    """Edição concorrente: o conteúdo mudou depois que a tela foi carregada."""


class TrabalhoGTService:
    # ------------------------------------------------------------------
    # Versões
    # ------------------------------------------------------------------
    @staticmethod
    def snapshot(trabalho: TrabalhoGT) -> dict:
        sala: SalaGT = trabalho.sala
        metas = list(
            MetaGT.raw_objects.filter(is_deleted=False, trabalho_id=trabalho.pk)
            .order_by("ordem", "id")
            .values("id", "ordem", "descricao", "indicador", "prazo", "observacoes")
        )
        estrategias = []
        for estrategia in (
            EstrategiaGT.raw_objects.filter(is_deleted=False, trabalho_id=trabalho.pk)
            .order_by("ordem", "id")
            .prefetch_related("metas")
        ):
            estrategias.append(
                {
                    "id": estrategia.pk,
                    "ordem": estrategia.ordem,
                    "descricao": estrategia.descricao,
                    "responsavel": estrategia.responsavel,
                    "prazo": estrategia.prazo,
                    "recursos": estrategia.recursos,
                    "indicador": estrategia.indicador,
                    "metas": [meta.pk for meta in estrategia.metas.all()],
                }
            )
        return {
            "objetivo": {
                "codigo": sala.objetivo.codigo,
                "titulo": sala.objetivo.titulo,
                "texto_oficial": sala.objetivo.texto,
                "proposta_do_gt": trabalho.objetivo_proposto,
            },
            "diagnostico": {campo: getattr(trabalho, campo) for campo in CAMPOS_DIAGNOSTICO},
            "observacoes": trabalho.observacoes,
            "pendencias": trabalho.pendencias,
            "metas": metas,
            "estrategias": estrategias,
            "estado": trabalho.estado,
            "version": trabalho.version,
        }

    @staticmethod
    def registrar_versao(trabalho: TrabalhoGT, usuario, *, motivo: str = "") -> VersaoTrabalhoGT:
        """Congela o conteúdo atual como versão recuperável."""

        ultimo = (
            VersaoTrabalhoGT.raw_objects.filter(is_deleted=False, trabalho_id=trabalho.pk)
            .order_by("-numero")
            .values_list("numero", flat=True)
            .first()
        )
        versao = VersaoTrabalhoGT(
            cliente_id=trabalho.cliente_id,
            trabalho=trabalho,
            numero=int(ultimo or 0) + 1,
            estado=trabalho.estado,
            conteudo_json=TrabalhoGTService.snapshot(trabalho),
            motivo=motivo[:255],
            criado_por=usuario,
        )
        versao.save()
        return versao

    # ------------------------------------------------------------------
    # Edição
    # ------------------------------------------------------------------
    @staticmethod
    def _checar_versao(trabalho: TrabalhoGT, version_esperada) -> None:
        if version_esperada in (None, ""):
            return
        try:
            esperada = int(version_esperada)
        except (TypeError, ValueError):
            return
        if esperada != trabalho.version:
            raise ConflitoDeVersao(
                "Outra pessoa alterou este conteúdo enquanto você editava. "
                "Recarregue a página para ver a versão atual antes de salvar."
            )

    @staticmethod
    def _exigir_edicao(trabalho: TrabalhoGT, usuario):
        acesso = acesso_a_sala(usuario, trabalho.sala)
        acesso.exigir(
            "pode_editar_conteudo",
            "Você não tem autorização para editar o conteúdo deste GT.",
        )
        if not trabalho.editavel:
            raise ValidationError(
                "Este conteúdo está em revisão ou aprovado. "
                "Solicite a reabertura à coordenação antes de editar."
            )
        return acesso

    @staticmethod
    @transaction.atomic
    def salvar_diagnostico(
        trabalho: TrabalhoGT, usuario, dados: dict, *, version_esperada=None
    ) -> TrabalhoGT:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        TrabalhoGTService._checar_versao(trabalho, version_esperada)

        for campo in CAMPOS_DIAGNOSTICO:
            if campo in dados:
                setattr(trabalho, campo, dados[campo])
        trabalho.diagnostico_atualizado_em = timezone.now()
        trabalho.diagnostico_atualizado_por = usuario
        trabalho.updated_by = usuario
        trabalho.full_clean()
        trabalho.save()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="diagnostico_atualizado",
            diff={"version": trabalho.version, "nao_aplicavel": trabalho.diagnostico_nao_aplicavel},
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def salvar_quadro(
        trabalho: TrabalhoGT, usuario, dados: dict, *, version_esperada=None
    ) -> TrabalhoGT:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        TrabalhoGTService._checar_versao(trabalho, version_esperada)

        for campo in CAMPOS_QUADRO:
            if campo in dados:
                setattr(trabalho, campo, dados[campo])
        trabalho.updated_by = usuario
        trabalho.full_clean()
        trabalho.save()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="quadro_atualizado",
            diff={"version": trabalho.version},
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def salvar_meta(trabalho: TrabalhoGT, usuario, *, meta: MetaGT | None = None, dados: dict) -> MetaGT:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        criando = meta is None
        if criando:
            meta = MetaGT(cliente_id=trabalho.cliente_id, trabalho=trabalho)
            proxima = (
                MetaGT.raw_objects.filter(is_deleted=False, trabalho_id=trabalho.pk).count() + 1
            )
            meta.ordem = dados.get("ordem") or proxima
        for campo in ("ordem", "descricao", "indicador", "prazo", "observacoes"):
            if campo in dados and dados[campo] is not None:
                setattr(meta, campo, dados[campo])
        meta.full_clean()
        meta.save()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.MetaGT",
            entidade_id=meta.pk,
            acao="criada" if criando else "atualizada",
            diff={"trabalho": trabalho.pk, "ordem": meta.ordem},
        )
        return meta

    @staticmethod
    @transaction.atomic
    def remover_meta(trabalho: TrabalhoGT, usuario, meta_id: int) -> None:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        meta = MetaGT.raw_objects.filter(
            is_deleted=False, trabalho_id=trabalho.pk, pk=meta_id
        ).first()
        if meta is None:
            return
        meta.delete()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.MetaGT",
            entidade_id=meta_id,
            acao="removida",
            diff={"trabalho": trabalho.pk},
        )

    @staticmethod
    @transaction.atomic
    def salvar_estrategia(
        trabalho: TrabalhoGT,
        usuario,
        *,
        estrategia: EstrategiaGT | None = None,
        dados: dict,
        metas_ids: list[int] | None = None,
    ) -> EstrategiaGT:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        criando = estrategia is None
        if criando:
            estrategia = EstrategiaGT(cliente_id=trabalho.cliente_id, trabalho=trabalho)
            proxima = (
                EstrategiaGT.raw_objects.filter(
                    is_deleted=False, trabalho_id=trabalho.pk
                ).count()
                + 1
            )
            estrategia.ordem = dados.get("ordem") or proxima
        for campo in ("ordem", "descricao", "responsavel", "prazo", "recursos", "indicador"):
            if campo in dados and dados[campo] is not None:
                setattr(estrategia, campo, dados[campo])
        estrategia.full_clean()
        estrategia.save()
        if metas_ids is not None:
            validas = list(
                MetaGT.raw_objects.filter(
                    is_deleted=False, trabalho_id=trabalho.pk, pk__in=metas_ids
                ).values_list("id", flat=True)
            )
            estrategia.metas.set(validas)
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.EstrategiaGT",
            entidade_id=estrategia.pk,
            acao="criada" if criando else "atualizada",
            diff={"trabalho": trabalho.pk, "ordem": estrategia.ordem},
        )
        return estrategia

    @staticmethod
    @transaction.atomic
    def remover_estrategia(trabalho: TrabalhoGT, usuario, estrategia_id: int) -> None:
        TrabalhoGTService._exigir_edicao(trabalho, usuario)
        estrategia = EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho_id=trabalho.pk, pk=estrategia_id
        ).first()
        if estrategia is None:
            return
        estrategia.delete()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.EstrategiaGT",
            entidade_id=estrategia_id,
            acao="removida",
            diff={"trabalho": trabalho.pk},
        )

    # ------------------------------------------------------------------
    # Fluxo
    # ------------------------------------------------------------------
    @staticmethod
    def pendencias_para_aprovacao(trabalho: TrabalhoGT) -> list[str]:
        """Validações mínimas configuráveis para aprovar o conteúdo."""

        sala: SalaGT = trabalho.sala
        ciclo = sala.ciclo
        pendencias: list[str] = []

        if not sala.objetivo_id:
            pendencias.append("Vincule a sala a um objetivo do Referencial.")
        if not trabalho.diagnostico_preenchido:
            pendencias.append(
                "Preencha o diagnóstico ou marque explicitamente que ele não se aplica."
            )

        total_metas = MetaGT.raw_objects.filter(
            is_deleted=False, trabalho_id=trabalho.pk
        ).count()
        minimo_metas = int(ciclo.min_metas_para_aprovacao or 0)
        if total_metas < minimo_metas:
            pendencias.append(
                f"Registre ao menos {minimo_metas} meta(s); há {total_metas} cadastrada(s)."
            )

        total_estrategias = EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho_id=trabalho.pk
        ).count()
        minimo_estrategias = int(ciclo.min_estrategias_para_aprovacao or 0)
        if total_estrategias < minimo_estrategias:
            pendencias.append(
                f"Registre ao menos {minimo_estrategias} estratégia(s); há {total_estrategias} cadastrada(s)."
            )

        if ciclo.exige_ata_para_aprovacao:
            tem_ata_validada = AtaReuniaoGT.raw_objects.filter(
                is_deleted=False,
                reuniao__sala_id=sala.pk,
                estado=AtaReuniaoGT.Estado.VALIDADA,
            ).exists()
            if not tem_ata_validada:
                pendencias.append("Valide a ata de pelo menos uma reunião do GT.")

        return pendencias

    @staticmethod
    @transaction.atomic
    def submeter_revisao(trabalho: TrabalhoGT, usuario) -> TrabalhoGT:
        acesso = acesso_a_sala(usuario, trabalho.sala)
        acesso.exigir("pode_submeter_revisao")
        if trabalho.estado not in TrabalhoGT.ESTADOS_EDITAVEIS:
            raise ValidationError("Somente rascunhos ou ajustes solicitados podem ser submetidos.")
        trabalho.estado = TrabalhoGT.Estado.EM_REVISAO
        trabalho.enviado_revisao_em = timezone.now()
        trabalho.enviado_revisao_por = usuario
        trabalho.parecer_revisao = ""
        trabalho.updated_by = usuario
        trabalho.save(
            update_fields=[
                "estado",
                "enviado_revisao_em",
                "enviado_revisao_por",
                "parecer_revisao",
                "updated_by",
                "updated_at",
            ]
        )
        TrabalhoGTService.registrar_versao(trabalho, usuario, motivo="Submetido para revisão")
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="submetido_revisao",
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def solicitar_ajustes(trabalho: TrabalhoGT, usuario, *, parecer: str) -> TrabalhoGT:
        acesso_a_sala(usuario, trabalho.sala).exigir("pode_solicitar_ajustes")
        if not (parecer or "").strip():
            raise ValidationError({"parecer": "Descreva os ajustes solicitados."})
        if trabalho.estado != TrabalhoGT.Estado.EM_REVISAO:
            raise ValidationError("Só é possível solicitar ajustes de conteúdo em revisão.")
        trabalho.estado = TrabalhoGT.Estado.AJUSTES_SOLICITADOS
        trabalho.parecer_revisao = parecer
        trabalho.updated_by = usuario
        trabalho.save(update_fields=["estado", "parecer_revisao", "updated_by", "updated_at"])
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="ajustes_solicitados",
            diff={"parecer": parecer},
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def aprovar(trabalho: TrabalhoGT, usuario) -> TrabalhoGT:
        acesso_a_sala(usuario, trabalho.sala).exigir("pode_aprovar_conteudo")
        if trabalho.estado not in {
            TrabalhoGT.Estado.EM_REVISAO,
            TrabalhoGT.Estado.AJUSTES_SOLICITADOS,
        }:
            raise ValidationError("Somente conteúdo em revisão pode ser aprovado.")
        pendencias = TrabalhoGTService.pendencias_para_aprovacao(trabalho)
        if pendencias:
            raise ValidationError(pendencias)

        trabalho.estado = TrabalhoGT.Estado.APROVADO
        trabalho.aprovado_em = timezone.now()
        trabalho.aprovado_por = usuario
        trabalho.parecer_revisao = ""
        trabalho.updated_by = usuario
        trabalho.save(
            update_fields=[
                "estado",
                "aprovado_em",
                "aprovado_por",
                "parecer_revisao",
                "updated_by",
                "updated_at",
            ]
        )
        TrabalhoGTService.registrar_versao(trabalho, usuario, motivo="Conteúdo aprovado")
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="aprovado",
            diff={"version": trabalho.version},
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def publicar(trabalho: TrabalhoGT, usuario) -> TrabalhoGT:
        acesso_a_sala(usuario, trabalho.sala).exigir("pode_publicar_conteudo")
        if trabalho.estado != TrabalhoGT.Estado.APROVADO:
            raise ValidationError("Somente conteúdo aprovado pode ser publicado.")
        trabalho.estado = TrabalhoGT.Estado.PUBLICADO
        trabalho.publicado_em = timezone.now()
        trabalho.publicado_por = usuario
        trabalho.updated_by = usuario
        trabalho.save(
            update_fields=["estado", "publicado_em", "publicado_por", "updated_by", "updated_at"]
        )
        TrabalhoGTService.registrar_versao(trabalho, usuario, motivo="Conteúdo publicado")
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="publicado",
        )
        return trabalho

    @staticmethod
    @transaction.atomic
    def reabrir(trabalho: TrabalhoGT, usuario, *, justificativa: str) -> TrabalhoGT:
        acesso_a_sala(usuario, trabalho.sala).exigir(
            "pode_reabrir_conteudo",
            "Apenas a administração do Referencial reabre conteúdo aprovado ou publicado.",
        )
        if not (justificativa or "").strip():
            raise ValidationError({"justificativa": "Registre a justificativa da reabertura."})
        if trabalho.estado in TrabalhoGT.ESTADOS_EDITAVEIS:
            raise ValidationError("Este conteúdo já está editável.")

        # A versão aprovada permanece congelada em VersaoTrabalhoGT; a edição
        # recomeça a partir de um novo rascunho.
        TrabalhoGTService.registrar_versao(
            trabalho, usuario, motivo=f"Reaberto: {justificativa}"[:255]
        )
        estado_anterior = trabalho.estado
        trabalho.estado = TrabalhoGT.Estado.RASCUNHO
        trabalho.parecer_revisao = justificativa
        trabalho.updated_by = usuario
        trabalho.save(update_fields=["estado", "parecer_revisao", "updated_by", "updated_at"])
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="ava.TrabalhoGT",
            entidade_id=trabalho.pk,
            acao="reaberto",
            diff={"de": estado_anterior, "justificativa": justificativa},
        )
        return trabalho

    @staticmethod
    def progresso(trabalho: TrabalhoGT | None) -> dict:
        """Resumo usado na lista geral: progresso e pendências sem expor conteúdo."""

        if trabalho is None:
            return {
                "estado": None,
                "estado_display": "Sem conteúdo iniciado",
                "diagnostico": False,
                "metas": 0,
                "estrategias": 0,
                "percentual": 0,
            }
        metas = MetaGT.raw_objects.filter(is_deleted=False, trabalho_id=trabalho.pk).count()
        estrategias = EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho_id=trabalho.pk
        ).count()
        etapas = [
            trabalho.diagnostico_preenchido,
            metas > 0,
            estrategias > 0,
            trabalho.estado != TrabalhoGT.Estado.RASCUNHO,
            trabalho.consolidavel,
        ]
        return {
            "estado": trabalho.estado,
            "estado_display": trabalho.get_estado_display(),
            "diagnostico": trabalho.diagnostico_preenchido,
            "metas": metas,
            "estrategias": estrategias,
            "percentual": int(round(100 * sum(1 for item in etapas if item) / len(etapas))),
        }
