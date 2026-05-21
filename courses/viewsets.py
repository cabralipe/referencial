"""Viewsets DRF do módulo de cursos."""

from __future__ import annotations

from django.db import models, transaction
from django.utils import timezone
from django.db.models import Prefetch
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.permissions import HasClientScope
from core.models import Usuario
from curriculum.models import GT

from .models import (
    Curso,
    CursoCertificadoEmitido,
    CursoItem,
    CursoModulo,
    CursoParticipacao,
    CursoProgresso,
    CursoProgressoItem,
    PlanoAulaPublicacao,
    PlanoAulaResposta,
)
from .serializers import (
    CertificacaoEmitirSerializer,
    CertificacaoStatusSerializer,
    CursoDetailSerializer,
    CursoListSerializer,
    CursoProgressoMarkSerializer,
    CursoWriteSerializer,
    PlanoAulaEnviarSerializer,
    PlanoAulaPublicacaoSerializer,
    PlanoAulaPublicacaoUpdateSerializer,
    PlanoAulaRespostaReadSerializer,
    PlanoAulaRespostaWriteSerializer,
    DEFAULT_CERT_RULES,
    ensure_plano_aula_template,
    flatten_plano_resposta_campos,
    normalize_cert_rules,
    save_plano_resposta_campos,
)


def _get_request_cliente_id(request) -> int:
    cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
    if not cliente_id and getattr(request.user, "role", None) == Usuario.Role.SUPER_ADMIN:
        header_cliente = request.headers.get("X-Cliente-ID")
        if header_cliente:
            cliente_id = header_cliente
    if cliente_id:
        return int(cliente_id)
    body_cliente = request.data.get("cliente_id") if hasattr(request, "data") else None
    if body_cliente:
        return int(body_cliente)
    raise ValidationError("Cliente não associado")


def _is_admin_or_super(user) -> bool:
    return getattr(user, "role", None) in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}


def _is_tutor_or_admin(user) -> bool:
    return getattr(user, "role", None) in {user.Role.ARTICULADOR, user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}


def _assert_admin_or_super(user) -> None:
    if not _is_admin_or_super(user):
        raise PermissionDenied("Ação permitida apenas para admin do cliente.")


def _assert_tutor_or_admin(user) -> None:
    if not _is_tutor_or_admin(user):
        raise PermissionDenied("Ação permitida apenas para tutor/admin.")


def _get_user_gt_ids(user) -> list[int]:
    if not getattr(user, "is_authenticated", False):
        return []
    return list(GT.objects.filter(membros=user).values_list("id", flat=True))


def _get_or_create_progress(curso: Curso, user) -> CursoProgresso:
    progresso, _ = CursoProgresso.objects.get_or_create(
        cliente_id=curso.cliente_id,
        curso=curso,
        usuario=user,
        defaults={"percentual": 0},
    )
    return progresso


def _recalculate_progress(progresso: CursoProgresso) -> CursoProgresso:
    total_itens = CursoItem.objects.filter(modulo__curso=progresso.curso).count()
    concluidos = CursoProgressoItem.objects.filter(progresso=progresso, item__isnull=False).count()
    percentual = 0
    if total_itens > 0:
        percentual = int((concluidos * 100) / total_itens)
    progresso.percentual = percentual
    progresso.save(update_fields=["percentual", "updated_at"])
    return progresso


def _build_certification_status(curso: Curso, user) -> dict:
    rules = normalize_cert_rules(curso.regras_certificacao_json)
    participacao = CursoParticipacao.objects.filter(curso=curso, usuario=user).first()
    presenca_presencial = bool(getattr(participacao, "presenca_presencial", False))
    sincronos_presentes = int(getattr(participacao, "encontros_sincronos_presentes", 0) or 0)
    min_sincronos = int(rules.get("min_sincronos", DEFAULT_CERT_RULES["min_sincronos"]))
    min_planos = int(rules.get("min_planos", DEFAULT_CERT_RULES["min_planos"]))

    planos_enviados_qs = PlanoAulaResposta.objects.filter(
        cliente_id=curso.cliente_id,
        curso=curso,
        usuario=user,
        status=PlanoAulaResposta.Status.ENVIADO,
    )
    planos_enviados = planos_enviados_qs.count()
    compartilhados = PlanoAulaPublicacao.objects.filter(
        cliente_id=curso.cliente_id,
        autor=user,
        resposta_formulario__curso=curso,
        status__in=[
            PlanoAulaPublicacao.Status.ENVIADO,
            PlanoAulaPublicacao.Status.APROVADO,
            PlanoAulaPublicacao.Status.PUBLICADO,
        ],
    ).count()

    entrega_final_concluida = CursoProgressoItem.objects.filter(
        cliente_id=curso.cliente_id,
        progresso__curso=curso,
        progresso__usuario=user,
        item__modulo__tipo=CursoModulo.Tipo.ENTREGA_FINAL,
    ).exists()

    checks = {
        "presenca_presencial": {
            "required": bool(rules.get("presenca_presencial_obrigatoria", True)),
            "ok": (not rules.get("presenca_presencial_obrigatoria", True)) or presenca_presencial,
            "value": presenca_presencial,
        },
        "encontros_sincronos": {
            "required": min_sincronos,
            "ok": sincronos_presentes >= min_sincronos,
            "value": sincronos_presentes,
        },
        "min_planos": {
            "required": min_planos,
            "ok": planos_enviados >= min_planos,
            "value": planos_enviados,
        },
        "entrega_final": {
            "required": bool(rules.get("entrega_final_obrigatoria", True)),
            "ok": (not rules.get("entrega_final_obrigatoria", True)) or entrega_final_concluida,
            "value": entrega_final_concluida,
        },
        "compartilhar_banco": {
            "required": bool(rules.get("compartilhar_banco_obrigatorio", True)),
            "ok": (not rules.get("compartilhar_banco_obrigatorio", True)) or compartilhados > 0,
            "value": compartilhados,
        },
    }
    emitted = CursoCertificadoEmitido.objects.filter(curso=curso, usuario=user).first()
    can_emit = all(bool(item["ok"]) for item in checks.values())
    return {
        "regras": rules,
        "checks": checks,
        "pode_emitir_certificado": can_emit,
        "certificado_emitido": bool(emitted),
        "certificado": {"id": emitted.id, "codigo": emitted.codigo, "emitido_em": emitted.created_at} if emitted else None,
    }


class CursoViewSet(viewsets.ModelViewSet):
    permission_classes = [HasClientScope]

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        qs = Curso.objects.filter(cliente_id=cliente_id).prefetch_related(
            "avisos",
            "cronograma_itens",
            Prefetch("modulos", queryset=curso_modulos_queryset(cliente_id)),
        )
        if _is_admin_or_super(self.request.user):
            return qs
        return qs.filter(publicado=True)

    def get_serializer_class(self):
        if self.action in {"list"}:
            return CursoListSerializer
        if self.action in {"create", "update", "partial_update"}:
            return CursoWriteSerializer
        return CursoDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        try:
            ctx["cliente_id"] = _get_request_cliente_id(self.request)
        except Exception:
            pass
        return ctx

    def perform_create(self, serializer):
        _assert_admin_or_super(self.request.user)
        cliente_id = _get_request_cliente_id(self.request)
        serializer.save(cliente_id=cliente_id)

    def perform_update(self, serializer):
        _assert_admin_or_super(self.request.user)
        serializer.save()

    def retrieve(self, request, *args, **kwargs):
        curso = self.get_object()
        progresso = None
        if not _is_admin_or_super(request.user):
            progresso = _get_or_create_progress(curso, request.user)
            _recalculate_progress(progresso)
        serializer = self.get_serializer(curso, context={**self.get_serializer_context(), "progresso": progresso})
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        curso = self.get_object()
        serializer = self.get_serializer(curso, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        curso = serializer.instance
        progresso = None
        if not _is_admin_or_super(request.user):
            progresso = _get_or_create_progress(curso, request.user)
            _recalculate_progress(progresso)
        return Response(CursoDetailSerializer(curso, context={**self.get_serializer_context(), "progresso": progresso}).data)

    @action(detail=True, methods=["post"], url_path="progresso")
    def marcar_progresso(self, request, pk=None):
        curso = self.get_object()
        serializer = CursoProgressoMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item_id = serializer.validated_data["item_id"]
        item = CursoItem.objects.filter(cliente_id=curso.cliente_id, modulo__curso=curso, pk=item_id).first()
        if not item:
            raise ValidationError({"item_id": "Item não pertence a este curso/cliente."})
        progresso = _get_or_create_progress(curso, request.user)
        CursoProgressoItem.objects.get_or_create(
            cliente_id=curso.cliente_id,
            progresso=progresso,
            item=item,
            defaults={"referencia_tipo": "curso_item", "referencia_id": str(item.id)},
        )
        _recalculate_progress(progresso)
        return Response({"ok": True, "progresso": {"id": progresso.id, "percentual": int(progresso.percentual)}})

    @action(detail=True, methods=["get"], url_path="certificacao/status")
    def certificacao_status(self, request, pk=None):
        curso = self.get_object()
        data = _build_certification_status(curso, request.user)
        serializer = CertificacaoStatusSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="certificacao/emitir")
    def certificacao_emitir(self, request, pk=None):
        curso = self.get_object()
        payload = CertificacaoEmitirSerializer(data=request.data or {})
        payload.is_valid(raise_exception=True)
        status_data = _build_certification_status(curso, request.user)
        if not status_data["pode_emitir_certificado"]:
            raise ValidationError({"detail": "Usuário ainda não elegível para certificação."})
        certificado, created = CursoCertificadoEmitido.objects.get_or_create(
            cliente_id=curso.cliente_id,
            curso=curso,
            usuario=request.user,
            defaults={"payload_json": {"stub": True, "curso": curso.nome}},
        )
        return Response(
            {
                "id": certificado.id,
                "codigo": certificado.codigo,
                "emitido_em": certificado.created_at,
                "created": created,
                "stub": True,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


def curso_modulos_queryset(cliente_id: int):
    return (
        CursoModulo.objects.filter(cliente_id=cliente_id)
        .order_by("ordem", "id")
        .prefetch_related(Prefetch("itens", queryset=CursoItem.objects.filter(cliente_id=cliente_id).order_by("ordem", "id")))
    )


class PlanoAulaViewSet(viewsets.ModelViewSet):
    permission_classes = [HasClientScope]
    serializer_class = PlanoAulaRespostaReadSerializer

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        qs = PlanoAulaResposta.objects.filter(cliente_id=cliente_id).select_related("curso", "usuario", "formulario").prefetch_related(
            "publicacoes"
        )
        curso_id = self.request.query_params.get("curso")
        if curso_id:
            qs = qs.filter(curso_id=curso_id)
        if _is_admin_or_super(self.request.user) or _is_tutor_or_admin(self.request.user):
            user_id = self.request.query_params.get("usuario_id")
            if user_id:
                qs = qs.filter(usuario_id=user_id)
            return qs
        return qs.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        payload = PlanoAulaRespostaWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cliente_id = _get_request_cliente_id(request)
        curso = Curso.objects.filter(cliente_id=cliente_id, pk=payload.validated_data["curso"]).first()
        if not curso:
            raise ValidationError({"curso": "Curso inválido para este cliente."})
        if not curso.publicado and not _is_admin_or_super(request.user):
            raise PermissionDenied("Curso não publicado.")
        formulario = ensure_plano_aula_template(cliente_id)
        resposta = PlanoAulaResposta.objects.create(
            cliente_id=cliente_id,
            curso=curso,
            usuario=request.user,
            formulario=formulario,
            titulo=payload.validated_data.get("titulo", ""),
        )
        if "campos" in payload.validated_data:
            save_plano_resposta_campos(resposta, payload.validated_data["campos"])
        PlanoAulaPublicacao.objects.get_or_create(
            cliente_id=cliente_id,
            autor=request.user,
            resposta_formulario=resposta,
            defaults={"status": PlanoAulaPublicacao.Status.RASCUNHO, "payload_json": resposta.dados_cache_json or {}},
        )
        return Response(PlanoAulaRespostaReadSerializer(resposta).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not (_is_admin_or_super(request.user) or instance.usuario_id == request.user.id):
            raise PermissionDenied("Sem permissão para editar este plano.")
        if instance.status == PlanoAulaResposta.Status.ENVIADO or instance.bloqueado_em:
            raise ValidationError({"detail": "Plano enviado está bloqueado para edição."})
        payload = PlanoAulaRespostaWriteSerializer(data={**request.data, "curso": instance.curso_id})
        payload.is_valid(raise_exception=True)
        if "titulo" in payload.validated_data:
            instance.titulo = payload.validated_data.get("titulo", "")
            instance.save(update_fields=["titulo", "updated_at"])
        if "campos" in payload.validated_data:
            save_plano_resposta_campos(instance, payload.validated_data["campos"])
        pub = instance.publicacoes.order_by("-updated_at").first()
        if pub:
            pub.payload_json = instance.dados_cache_json or flatten_plano_resposta_campos(instance)
            pub.save(update_fields=["payload_json", "updated_at"])
        return Response(PlanoAulaRespostaReadSerializer(instance).data)

    @action(detail=True, methods=["post"], url_path="enviar")
    def enviar(self, request, pk=None):
        instance = self.get_object()
        if not (_is_admin_or_super(request.user) or instance.usuario_id == request.user.id):
            raise PermissionDenied("Sem permissão para enviar este plano.")
        if instance.status == PlanoAulaResposta.Status.ENVIADO:
            return Response(PlanoAulaRespostaReadSerializer(instance).data)
        payload = PlanoAulaEnviarSerializer(data=request.data or {})
        payload.is_valid(raise_exception=True)

        campos = instance.dados_cache_json or flatten_plano_resposta_campos(instance)
        required_keys = [key for key, _label in self._template_specs()]
        missing = [key for key in required_keys if not str(campos.get(key, "")).strip()]
        if missing:
            raise ValidationError({"campos": f"Preencha os campos obrigatórios antes de enviar: {', '.join(missing)}"})

        instance.status = PlanoAulaResposta.Status.ENVIADO
        instance.compartilhado_banco = payload.validated_data["compartilhar_no_banco"]
        instance.enviado_em = timezone.now()
        instance.bloqueado_em = timezone.now()
        if not instance.titulo.strip():
            instance.titulo = campos.get("objetivos_aprendizagem", "")[:120] or f"Plano {instance.id}"
        instance.save(
            update_fields=[
                "status",
                "compartilhado_banco",
                "enviado_em",
                "bloqueado_em",
                "titulo",
                "updated_at",
            ]
        )

        pub, _ = PlanoAulaPublicacao.objects.update_or_create(
            cliente_id=instance.cliente_id,
            resposta_formulario=instance,
            defaults={
                "autor_id": instance.usuario_id,
                "status": (
                    PlanoAulaPublicacao.Status.ENVIADO
                    if instance.compartilhado_banco
                    else PlanoAulaPublicacao.Status.RASCUNHO
                ),
                "allow_comments": payload.validated_data.get("allow_comments", True),
                "payload_json": instance.dados_cache_json or campos,
                "is_deleted": False,
            },
        )
        return Response(
            {
                "plano": PlanoAulaRespostaReadSerializer(instance).data,
                "publicacao": PlanoAulaPublicacaoSerializer(pub).data,
            }
        )

    def _template_specs(self):
        from .serializers import PLANO_AULA_FIELD_SPECS

        return PLANO_AULA_FIELD_SPECS


class BancoPlanosViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [HasClientScope]
    serializer_class = PlanoAulaPublicacaoSerializer

    def get_queryset(self):
        cliente_id = _get_request_cliente_id(self.request)
        qs = PlanoAulaPublicacao.objects.filter(cliente_id=cliente_id).select_related("autor", "resposta_formulario", "resposta_formulario__curso")

        if not _is_tutor_or_admin(self.request.user):
            qs = qs.filter(status=PlanoAulaPublicacao.Status.PUBLICADO)
        else:
            status_filter = self.request.query_params.get("status")
            if status_filter:
                qs = qs.filter(status=status_filter)

        etapa = self.request.query_params.get("etapa_modalidade")
        if etapa:
            qs = qs.filter(payload_json__etapa_modalidade__icontains=etapa)
        componente = self.request.query_params.get("componente")
        if componente:
            qs = qs.filter(payload_json__componente_curricular__icontains=componente)
        return qs

    def partial_update(self, request, *args, **kwargs):
        _assert_tutor_or_admin(request.user)
        instance = self.get_object()
        serializer = PlanoAulaPublicacaoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.status = serializer.validated_data["status"]
        if "allow_comments" in serializer.validated_data:
            instance.allow_comments = serializer.validated_data["allow_comments"]
        instance.save(update_fields=["status", "allow_comments", "updated_at"])
        return Response(PlanoAulaPublicacaoSerializer(instance).data)
