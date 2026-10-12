"""Comentários e pedidos de ajuste no conteúdo do GT.

Reaproveita o app de comentários já existente (:class:`comments.models.Comentario`,
genérico por ``alvo_tipo``/``alvo_id``/``anchor_json``) em vez de criar um segundo
mecanismo: o comentário é ancorado no GT, no campo e na versão do conteúdo em que
foi escrito. Respeita a mesma feature flag do restante do produto
(``ff.comments.enabled``).
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from ava.models.gt_sala import TrabalhoGT
from ava.services.audit_service import AVAAuditService
from ava.services.gt_access import acesso_a_sala
from comments.models import Comentario
from core.utils import flag_ativa


ALVO_TIPO = Comentario.AlvoTipo.TRABALHO_GT

#: Campos do quadro que aceitam comentário, com o rótulo mostrado na tela.
CAMPOS_COMENTAVEIS: dict[str, str] = {
    "geral": "Observação geral do GT",
    "diagnostico_situacao": "Diagnóstico — situação atual",
    "diagnostico_evidencias": "Diagnóstico — evidências e fontes",
    "diagnostico_desafios": "Diagnóstico — desafios",
    "diagnostico_potencialidades": "Diagnóstico — potencialidades",
    "diagnostico_publico": "Diagnóstico — público e território",
    "objetivo_proposto": "Proposta de redação do objetivo",
    "metas": "Metas e resultados esperados",
    "estrategias": "Estratégias e ações",
}

MAX_TAMANHO_COMENTARIO = 4000


class ComentarioGTService:
    """Criação, listagem e resolução dos comentários do quadro do objetivo."""

    @staticmethod
    def habilitado(cliente) -> bool:
        return flag_ativa(cliente, "ff.comments.enabled")

    @staticmethod
    def _exigir_flag(cliente) -> None:
        if not ComentarioGTService.habilitado(cliente):
            raise PermissionDenied(
                "Os comentários estão desabilitados para este município."
            )

    @staticmethod
    def listar(trabalho: TrabalhoGT, *, incluir_resolvidos: bool = True):
        queryset = Comentario.raw_objects.filter(
            is_deleted=False,
            cliente_id=trabalho.cliente_id,
            alvo_tipo=ALVO_TIPO,
            alvo_id=str(trabalho.pk),
        ).select_related("autor", "resolvido_por")
        if not incluir_resolvidos:
            queryset = queryset.filter(resolvido=False)
        return queryset.order_by("resolvido", "-created_at")

    @staticmethod
    def total_abertos(trabalho: TrabalhoGT) -> int:
        return ComentarioGTService.listar(trabalho, incluir_resolvidos=False).count()

    @staticmethod
    def criar(trabalho: TrabalhoGT, usuario, *, campo: str, texto: str) -> Comentario:
        """Registra um comentário/pedido de ajuste ancorado em um campo."""

        sala = trabalho.sala
        ComentarioGTService._exigir_flag(sala.cliente)
        acesso_a_sala(usuario, sala).exigir(
            "pode_ver", "Você não participa deste GT para comentar o conteúdo."
        )

        campo = (campo or "geral").strip()
        if campo not in CAMPOS_COMENTAVEIS:
            raise ValidationError({"campo": "Campo inválido para comentário."})
        texto = (texto or "").strip()
        if not texto:
            raise ValidationError({"texto": "Escreva o comentário."})
        if len(texto) > MAX_TAMANHO_COMENTARIO:
            raise ValidationError(
                {"texto": f"O comentário deve ter no máximo {MAX_TAMANHO_COMENTARIO} caracteres."}
            )

        comentario = Comentario(
            cliente_id=trabalho.cliente_id,
            alvo_tipo=ALVO_TIPO,
            alvo_id=str(trabalho.pk),
            anchor_json={
                "campo": campo,
                "campo_rotulo": CAMPOS_COMENTAVEIS[campo],
                "version": trabalho.version,
                "estado": trabalho.estado,
                "sala": sala.pk,
                "objetivo": sala.objetivo.codigo,
            },
            # Guardado como texto puro; a exibição no AVA remove marcação e
            # escapa o conteúdo (``striptags|linebreaksbr``).
            conteudo_html=texto,
            autor=usuario,
        )
        comentario.save()
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="comments.Comentario",
            entidade_id=comentario.pk,
            acao="comentario_gt_criado",
            diff={"trabalho": trabalho.pk, "campo": campo, "version": trabalho.version},
        )
        return comentario

    @staticmethod
    def resolver(trabalho: TrabalhoGT, usuario, comentario_id: int) -> Comentario | None:
        """Marca o comentário como resolvido (coordenação, administração ou autor)."""

        sala = trabalho.sala
        ComentarioGTService._exigir_flag(sala.cliente)
        comentario = Comentario.raw_objects.filter(
            is_deleted=False,
            cliente_id=trabalho.cliente_id,
            alvo_tipo=ALVO_TIPO,
            alvo_id=str(trabalho.pk),
            pk=comentario_id,
        ).first()
        if comentario is None:
            return None

        acesso = acesso_a_sala(usuario, sala)
        if not acesso.pode_solicitar_ajustes and comentario.autor_id != usuario.pk:
            raise PermissionDenied(
                "Apenas a coordenação, a administração ou quem escreveu pode resolver o comentário."
            )
        if comentario.resolvido:
            return comentario

        comentario.resolvido = True
        comentario.resolvido_por = usuario
        comentario.resolved_at = timezone.now()
        comentario.save(update_fields=["resolvido", "resolvido_por", "resolved_at", "updated_at"])
        AVAAuditService.registrar(
            cliente_id=trabalho.cliente_id,
            usuario=usuario,
            entidade="comments.Comentario",
            entidade_id=comentario.pk,
            acao="comentario_gt_resolvido",
            diff={"trabalho": trabalho.pk},
        )
        return comentario

    @staticmethod
    def campos_para_formulario() -> list[tuple[str, str]]:
        return list(CAMPOS_COMENTAVEIS.items())
