"""Serializers da API pública v1."""

from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from urllib.parse import urlparse

from core.models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, ThrottleBlock, UserSessionLog
from core.utils import coletar_contexto_do_cliente
from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Area, Anexo, GT, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from reviews.models import Revisao, ReviewDecision
from workshop.models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha
from meb.models import MebMessage, MebThread
from meb.services import ensure_thread_for_user


class ClienteTemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteTema
        fields = (
            "logo_url",
            "meb_avatar_url",
            "cor_primaria",
            "cor_secundaria",
            "rodape_html",
            "cabecalho_html",
        )


class ClienteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteConfig
        fields = ("chave", "valor_texto")


class ClienteFeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteFeatureFlag
        fields = ("flag", "ativo")


class ClienteMeSerializer(serializers.Serializer):
    cliente = serializers.DictField()
    configs = serializers.DictField()
    flags = serializers.DictField()
    tema = serializers.DictField()

    @classmethod
    def from_cliente(cls, cliente: Cliente):
        return cls(coletar_contexto_do_cliente(cliente))


class TarefaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarefa
        fields = ("id", "nome", "ordem", "etapa", "tipo", "status", "created_at")


class GTSerializer(serializers.ModelSerializer):
    class Meta:
        model = GT
        fields = ("id", "nome", "etapa")


class AreaSerializer(serializers.ModelSerializer):
    gts = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Area
        fields = ("id", "nome", "descricao_html", "gts")


class PerguntaSerializer(serializers.ModelSerializer):
    gts = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Pergunta
        fields = (
            "id",
            "tarefa",
            "ordem",
            "texto",
            "permite_upload",
            "obrigatoria",
            "gts",
        )
        read_only_fields = ("tarefa",)


class PerguntaWriteSerializer(serializers.ModelSerializer):
    gts = serializers.PrimaryKeyRelatedField(many=True, queryset=GT.objects.all(), required=False)

    class Meta:
        model = Pergunta
        fields = (
            "id",
            "tarefa",
            "ordem",
            "texto",
            "permite_upload",
            "obrigatoria",
            "gts",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        if not request:
            return attrs
        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        tarefa = attrs.get("tarefa")
        if tarefa and getattr(tarefa, "cliente_id", None) != cliente_id:
            raise serializers.ValidationError("Tarefa não pertence ao cliente.")
        gts = attrs.get("gts") or []
        for gt in gts:
            if gt.cliente_id != cliente_id:
                raise serializers.ValidationError("GT não pertence ao cliente.")
        return attrs


class AnexoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anexo
        fields = ("id", "resposta", "url", "legenda", "ordem")
        read_only_fields = ("id",)


class RespostaSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)
    gt_nome = serializers.SerializerMethodField()
    autor_nome = serializers.SerializerMethodField()
    tarefa_status = serializers.SerializerMethodField()
    pergunta_ordem = serializers.SerializerMethodField()
    pergunta_texto = serializers.SerializerMethodField()
    tarefa_id = serializers.SerializerMethodField()

    class Meta:
        model = Resposta
        fields = (
            "id",
            "gt",
            "gt_nome",
            "pergunta",
            "pergunta_ordem",
            "pergunta_texto",
            "tarefa_id",
            "conteudo_html",
            "autor",
            "autor_nome",
            "version",
            "updated_at",
            "etag",
            "tarefa_status",
        )
        read_only_fields = ("id", "version", "updated_at", "autor", "etag")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["autor"] = request.user
        try:
            return super().create(validated_data)
        except IntegrityError:
            cliente_id = validated_data.get("cliente_id")
            gt = validated_data.get("gt")
            pergunta = validated_data.get("pergunta")
            existing = None
            if cliente_id and gt and pergunta:
                existing = Resposta.raw_objects.filter(
                    cliente_id=cliente_id,
                    gt_id=getattr(gt, "pk", gt),
                    pergunta_id=getattr(pergunta, "pk", pergunta),
                ).first()
            if not existing:
                raise
            for field in ("conteudo_html", "autor"):
                if field in validated_data:
                    setattr(existing, field, validated_data[field])
            existing.save(update_fields=["conteudo_html", "autor", "updated_at"])
            return existing

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["autor"] = request.user
        return super().update(instance, validated_data)

    def get_gt_nome(self, obj):
        if hasattr(obj, "gt") and obj.gt:
            return obj.gt.nome
        return None

    def get_autor_nome(self, obj):
        autor = getattr(obj, "autor", None)
        if not autor:
            return None
        return autor.nome or autor.email

    def get_tarefa_status(self, obj):
        pergunta = getattr(obj, "pergunta", None)
        if not pergunta:
            return None
        tarefa = getattr(pergunta, "tarefa", None)
        return getattr(tarefa, "status", None)

    def get_pergunta_ordem(self, obj):
        pergunta = getattr(obj, "pergunta", None)
        return getattr(pergunta, "ordem", None)

    def get_pergunta_texto(self, obj):
        pergunta = getattr(obj, "pergunta", None)
        if not pergunta:
            return None
        texto = getattr(pergunta, "texto", "") or ""
        return texto if len(texto) <= 500 else texto[:500] + "..."

    def get_tarefa_id(self, obj):
        pergunta = getattr(obj, "pergunta", None)
        tarefa = getattr(pergunta, "tarefa", None) if pergunta else None
        return getattr(tarefa, "id", None)


class TextoUnicoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = TextoUnico
        fields = (
            "id",
            "gt",
            "tarefa",
            "conteudo_html",
            "responsavel",
            "version",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "version", "updated_at", "responsavel", "etag")


class TextoColaborativoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = TextoColaborativo
        fields = (
            "id",
            "gt",
            "pergunta",
            "titulo",
            "conteudo_html",
            "autor",
            "version",
            "created_at",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "version", "created_at", "updated_at", "autor", "etag")

    def validate(self, attrs):
        gt = attrs.get("gt") or getattr(self.instance, "gt", None)
        pergunta = attrs.get("pergunta") or getattr(self.instance, "pergunta", None)
        if pergunta and gt:
            if pergunta.cliente_id != gt.cliente_id:
                raise serializers.ValidationError("Pergunta e GT devem pertencer ao mesmo cliente.")
            if pergunta.gts.exists() and not pergunta.gts.filter(pk=gt.pk).exists():
                raise serializers.ValidationError("Pergunta não está vinculada a este GT.")
        return super().validate(attrs)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["autor"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["autor"] = request.user
        return super().update(instance, validated_data)


class CelulaQuadroSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelulaQuadro
        fields = ("id", "quadro", "linha", "coluna", "valor_html")
        read_only_fields = ("id", "quadro")


class QuadroLinhaSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuadroLinha
        fields = ("id", "linha", "nome", "ordem")


class QuadroColunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuadroColuna
        fields = ("id", "coluna", "nome", "ordem")


class QuadroSerializer(serializers.ModelSerializer):
    celulas = CelulaQuadroSerializer(many=True, read_only=True)
    linhas = QuadroLinhaSerializer(many=True, read_only=True)
    colunas = QuadroColunaSerializer(many=True, read_only=True)

    class Meta:
        model = Quadro
        fields = ("id", "gt", "area", "template", "version", "celulas", "linhas", "colunas")


class FormularioDinamicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormularioDinamico
        fields = ("id", "nome", "descricao", "ativo")


class CampoDinamicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampoDinamico
        fields = (
            "id",
            "formulario",
            "chave",
            "tipo",
            "config_json",
            "obrigatorio",
            "ordem",
        )
        read_only_fields = ("formulario",)


class RespostaCampoDinamicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RespostaCampoDinamico
        fields = (
            "id",
            "formulario",
            "campo",
            "valor_texto",
            "valor_num",
            "valor_bool",
            "url_arquivo",
            "owner_type",
            "owner_id",
        )
        read_only_fields = ("id",)


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = (
            "id",
            "alvo_tipo",
            "alvo_id",
            "payload_json",
            "formato",
            "status",
            "url_resultado",
            "created_at",
            "finished_at",
        )
        read_only_fields = ("id", "status", "url_resultado", "created_at", "finished_at")

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        cliente_id = getattr(user, "cliente_id", None)
        if not cliente_id:
            raise serializers.ValidationError("Cliente do usuário não encontrado.")
        allowed_gt_ids = None
        if user and getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            allowed_gt_ids = set(GT.objects.filter(membros=user).values_list("id", flat=True))
            if not allowed_gt_ids:
                raise serializers.ValidationError("Usuário sem GT vinculado.")

        alvo_tipo = attrs.get("alvo_tipo")
        alvo_id = attrs.get("alvo_id")
        if not alvo_tipo:
            return attrs
        if alvo_tipo != ExportJob.AlvoTipo.COLECAO and not alvo_id:
            if alvo_tipo != ExportJob.AlvoTipo.RELATORIO:
                return attrs

        modelo_por_tipo = {
            ExportJob.AlvoTipo.TEXTO_UNICO: TextoUnico,
            ExportJob.AlvoTipo.QUADRO: Quadro,
            ExportJob.AlvoTipo.RESPOSTA: Resposta,
        }
        if alvo_tipo == ExportJob.AlvoTipo.RELATORIO:
            if user and getattr(user, "role", None) not in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN, user.Role.ARTICULADOR}:
                raise serializers.ValidationError("Somente administradores ou articuladores podem exportar relatórios.")
            payload = attrs.get("payload_json") or {}
            conteudo_html = payload.get("conteudo_html") if isinstance(payload, dict) else None
            if not isinstance(conteudo_html, str) or not conteudo_html.strip():
                raise serializers.ValidationError({"payload_json": "Informe o conteudo_html do relatório."})
            attrs["alvo_id"] = attrs.get("alvo_id") or "relatorio"
            return attrs
        if alvo_tipo == ExportJob.AlvoTipo.COLECAO:
            secoes = (attrs.get("payload_json") or {}).get("secoes", [])
            if not secoes:
                raise serializers.ValidationError({"payload_json": "Informe ao menos uma seção para exportar."})
            modelo_por_secao = {**modelo_por_tipo}
            secoes_limpa = []
            gt_ids = set()
            for idx, secao in enumerate(secoes):
                tipo = (secao or {}).get("tipo")
                try:
                    secao_id = int((secao or {}).get("id"))
                except (TypeError, ValueError):
                    raise serializers.ValidationError({"payload_json": f"ID inválido na seção {idx + 1}."})
                modelo = modelo_por_secao.get(tipo)
                if not modelo:
                    raise serializers.ValidationError({"payload_json": f"Tipo de seção inválido na posição {idx + 1}."})
                lookup = {"cliente_id": cliente_id, "pk": secao_id}
                if any(field.attname == "is_deleted" for field in modelo._meta.fields):
                    lookup["is_deleted"] = False
                alvo = modelo.raw_objects.filter(**lookup).values_list("gt_id", flat=True).first()
                if alvo is None:
                    raise serializers.ValidationError(
                        {"payload_json": f"Registro {secao_id} não encontrado para o cliente."}
                    )
                if allowed_gt_ids is not None and alvo not in allowed_gt_ids:
                    raise serializers.ValidationError(
                        {"payload_json": f"Registro {secao_id} não pertence aos seus GTs."}
                    )
                gt_ids.add(int(alvo))
                secoes_limpa.append({"tipo": tipo, "id": secao_id, "titulo": (secao or {}).get("titulo")})
            payload = attrs.get("payload_json") or {}
            payload["secoes"] = secoes_limpa
            payload["gt_ids"] = sorted(gt_ids)
            attrs["payload_json"] = payload
            attrs["alvo_id"] = attrs.get("alvo_id") or "colecao"
        else:
            modelo = modelo_por_tipo.get(alvo_tipo)
            if not modelo:
                raise serializers.ValidationError({"alvo_tipo": "Tipo de alvo inválido."})

            lookup = {"cliente_id": cliente_id, "pk": alvo_id}
            if any(field.attname == "is_deleted" for field in modelo._meta.fields):
                lookup["is_deleted"] = False

            alvo = modelo.raw_objects.filter(**lookup).values_list("gt_id", flat=True).first()
            if alvo is None:
                raise serializers.ValidationError({"alvo_id": "Alvo não encontrado para este cliente."})
            if allowed_gt_ids is not None and alvo not in allowed_gt_ids:
                raise serializers.ValidationError({"alvo_id": "Alvo não pertence aos seus GTs."})

            attrs["alvo_id"] = str(alvo_id)
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    usuario_last_login = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "cliente",
            "usuario_id",
            "usuario_nome",
            "usuario_email",
            "usuario_last_login",
            "entidade",
            "entidade_id",
            "acao",
            "diff_json",
            "timestamp",
        )
        read_only_fields = fields

    def get_usuario_nome(self, obj):
        from core.models import Usuario
        if not obj.usuario_id:
            return None
        usuario = Usuario.objects.filter(pk=obj.usuario_id).only("nome").first()
        return getattr(usuario, "nome", None)

    def get_usuario_email(self, obj):
        from core.models import Usuario
        if not obj.usuario_id:
            return None
        usuario = Usuario.objects.filter(pk=obj.usuario_id).only("email").first()
        return getattr(usuario, "email", None)

    def get_usuario_last_login(self, obj):
        from core.models import Usuario
        if not obj.usuario_id:
            return None
        usuario = Usuario.objects.filter(pk=obj.usuario_id).only("last_login").first()
        return getattr(usuario, "last_login", None)


class ThrottleBlockSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()

    class Meta:
        model = ThrottleBlock
        fields = (
            "id",
            "cliente",
            "usuario",
            "usuario_nome",
            "usuario_email",
            "scope",
            "ident",
            "wait_seconds",
            "blocked_until",
            "created_at",
        )
        read_only_fields = fields

    def get_usuario_nome(self, obj):
        if obj.usuario:
            return obj.usuario.nome
        return None

    def get_usuario_email(self, obj):
        if obj.usuario:
            return obj.usuario.email
        return None


class OnlineUserSerializer(serializers.ModelSerializer):
    usuario_id = serializers.IntegerField(read_only=True)
    usuario_nome = serializers.SerializerMethodField()
    usuario_email = serializers.SerializerMethodField()
    usuario_role = serializers.SerializerMethodField()
    session_duration_seconds = serializers.SerializerMethodField()
    device_label = serializers.SerializerMethodField()

    class Meta:
        model = UserSessionLog
        fields = (
            "id",
            "usuario_id",
            "usuario_nome",
            "usuario_email",
            "usuario_role",
            "cliente",
            "first_seen_at",
            "last_seen_at",
            "session_duration_seconds",
            "device_label",
        )
        read_only_fields = fields

    def get_usuario_nome(self, obj):
        if obj.usuario:
            return obj.usuario.nome
        return None

    def get_usuario_email(self, obj):
        if obj.usuario:
            return obj.usuario.email
        return None

    def get_usuario_role(self, obj):
        if obj.usuario:
            return obj.usuario.role
        return None

    def get_session_duration_seconds(self, obj):
        try:
            delta = obj.last_seen_at - obj.first_seen_at
            seconds = int(delta.total_seconds())
            return max(seconds, 0)
        except Exception:
            return 0

    def get_device_label(self, obj):
        ua = (obj.user_agent or "").lower()
        if not ua:
            return None
        if "mobi" in ua:
            return "mobile"
        if "tablet" in ua:
            return "tablet"
        if "windows" in ua or "macintosh" in ua or "linux" in ua:
            return "desktop"
        return "desconhecido"


class UsuarioLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "nome", "email", "role")
        read_only_fields = fields


class RevisaoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)
    alvo_preview = serializers.SerializerMethodField()
    reviewer_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = Revisao
        fields = (
            "id",
            "alvo_tipo",
            "alvo_id",
            "alvo_preview",
            "status",
            "parecer_html",
            "revisor",
            "solicitante",
            "reviewer_recommendation",
            "created_at",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "created_at", "updated_at", "solicitante", "etag")

    def _build_resposta_preview(self, alvo_id: str | int):
        try:
            resposta = Resposta.raw_objects.select_related(
                "gt",
                "pergunta",
                "pergunta__tarefa",
                "autor",
            ).get(pk=alvo_id)
        except Resposta.DoesNotExist:
            return None
        tarefa = getattr(resposta.pergunta, "tarefa", None)
        return {
            "type": "resposta",
            "id": resposta.pk,
            "gt": resposta.gt_id,
            "gt_nome": getattr(resposta.gt, "nome", None),
            "pergunta": resposta.pergunta_id,
            "pergunta_ordem": getattr(resposta.pergunta, "ordem", None),
            "tarefa": getattr(tarefa, "id", None),
            "tarefa_nome": getattr(tarefa, "nome", None),
            "tarefa_etapa": getattr(tarefa, "etapa", None),
            "autor_nome": getattr(getattr(resposta, "autor", None), "nome", None),
            "conteudo_html": resposta.conteudo_html,
        }

    def _build_texto_unico_preview(self, alvo_id: str | int):
        try:
            texto = TextoUnico.raw_objects.select_related("gt", "tarefa").get(pk=alvo_id)
        except TextoUnico.DoesNotExist:
            return None
        return {
            "type": "texto_unico",
            "id": texto.pk,
            "gt": texto.gt_id,
            "gt_nome": getattr(texto.gt, "nome", None),
            "tarefa": texto.tarefa_id,
            "conteudo_html": texto.conteudo_html,
        }

    def _build_quadro_preview(self, alvo_id: str | int):
        try:
            quadro = Quadro.raw_objects.select_related("gt").get(pk=alvo_id)
        except Quadro.DoesNotExist:
            return None
        return {
            "type": "quadro",
            "id": quadro.pk,
            "gt": quadro.gt_id,
            "gt_nome": getattr(quadro.gt, "nome", None),
            "template": quadro.template,
        }

    def get_alvo_preview(self, obj):
        if obj.alvo_tipo == Revisao.AlvoTipo.RESPOSTA:
            return self._build_resposta_preview(obj.alvo_id)
        if obj.alvo_tipo == Revisao.AlvoTipo.TEXTO_UNICO:
            return self._build_texto_unico_preview(obj.alvo_id)
        if obj.alvo_tipo == Revisao.AlvoTipo.QUADRO:
            return self._build_quadro_preview(obj.alvo_id)
        return None

    def get_reviewer_recommendation(self, obj):
        decision = (
            ReviewDecision.objects.filter(
                cliente_id=obj.cliente_id,
                target_type=obj.alvo_tipo,
                target_id=obj.alvo_id,
                actor_role=ReviewDecision.ActorRole.REVIEWER,
            )
            .exclude(decision_type=ReviewDecision.DecisionType.IN_PROGRESS)
            .first()
        )
        if not decision:
            return None
        return {
            "id": decision.id,
            "decision_type": decision.decision_type,
            "checklist": decision.checklist,
            "note": decision.note,
            "created_at": decision.created_at,
            "actor_id": decision.actor_id,
        }


class ComentarioSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)
    mentions = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True, write_only=True)
    mentions_ids = serializers.SerializerMethodField(read_only=True)
    alvo_preview = serializers.SerializerMethodField()

    class Meta:
        model = Comentario
        fields = (
            "id",
            "alvo_tipo",
            "alvo_id",
            "alvo_preview",
            "anchor_json",
            "conteudo_html",
            "autor",
            "resolvido",
            "resolvido_por",
            "resolved_at",
            "mentions",
            "mentions_ids",
            "alvo_preview",
            "created_at",
            "updated_at",
            "etag",
        )
        read_only_fields = (
            "id",
            "autor",
            "resolvido_por",
            "resolved_at",
            "mentions_ids",
            "created_at",
            "updated_at",
            "etag",
        )

    def _shorten(self, value: str | None, limit: int = 240) -> str | None:
        if not value:
            return None
        text = value.strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "..."

    def _build_resposta_preview(self, alvo_id: str | int):
        try:
            resposta = Resposta.raw_objects.select_related("gt", "pergunta", "pergunta__tarefa").get(pk=alvo_id)
        except Resposta.DoesNotExist:
            return None
        pergunta = getattr(resposta, "pergunta", None)
        tarefa = getattr(pergunta, "tarefa", None) if pergunta else None
        return {
            "type": "resposta",
            "id": resposta.pk,
            "gt": resposta.gt_id,
            "gt_nome": getattr(resposta.gt, "nome", None),
            "tarefa": getattr(tarefa, "id", None),
            "tarefa_nome": getattr(tarefa, "nome", None),
            "pergunta": resposta.pergunta_id,
            "pergunta_ordem": getattr(pergunta, "ordem", None),
            "pergunta_texto": self._shorten(getattr(pergunta, "texto", None)),
        }

    def _build_texto_unico_preview(self, alvo_id: str | int):
        try:
            texto = TextoUnico.raw_objects.select_related("gt", "tarefa").get(pk=alvo_id)
        except TextoUnico.DoesNotExist:
            return None
        tarefa = getattr(texto, "tarefa", None)
        return {
            "type": "texto_unico",
            "id": texto.pk,
            "gt": texto.gt_id,
            "gt_nome": getattr(texto.gt, "nome", None),
            "tarefa": texto.tarefa_id,
            "tarefa_nome": getattr(tarefa, "nome", None),
            "tarefa_etapa": getattr(tarefa, "etapa", None),
        }

    def _build_quadro_preview(self, alvo_id: str | int):
        try:
            quadro = Quadro.raw_objects.select_related("gt").get(pk=alvo_id)
        except Quadro.DoesNotExist:
            return None
        return {
            "type": "quadro",
            "id": quadro.pk,
            "gt": quadro.gt_id,
            "gt_nome": getattr(quadro.gt, "nome", None),
            "template": quadro.template,
        }

    def get_alvo_preview(self, obj):
        if obj.alvo_tipo == Comentario.AlvoTipo.RESPOSTA:
            return self._build_resposta_preview(obj.alvo_id)
        if obj.alvo_tipo == Comentario.AlvoTipo.TEXTO_UNICO:
            return self._build_texto_unico_preview(obj.alvo_id)
        if obj.alvo_tipo == Comentario.AlvoTipo.QUADRO:
            return self._build_quadro_preview(obj.alvo_id)
        return None

    def get_mentions_ids(self, obj):
        return list(obj.mentions.values_list("id", flat=True))


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ("id", "tipo", "payload_json", "lida", "created_at")
        read_only_fields = ("id", "tipo", "payload_json", "created_at")


class MuralPostSerializer(serializers.Serializer):
    id = serializers.CharField()
    titulo = serializers.CharField()
    conteudo_html = serializers.CharField()
    link_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    anexos = serializers.ListField(child=serializers.DictField(), required=False)
    fixado = serializers.BooleanField(default=False)
    gt_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    criado_por = serializers.DictField(required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class MuralPostCreateSerializer(serializers.Serializer):
    titulo = serializers.CharField()
    conteudo_html = serializers.CharField()
    link_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    anexos = serializers.ListField(child=serializers.DictField(), required=False)
    fixado = serializers.BooleanField(required=False)
    include_all = serializers.BooleanField(required=False)
    gt_ids = serializers.ListField(child=serializers.IntegerField(), required=False)


class MidiaSerializer(serializers.ModelSerializer):
    def validate_url(self, value):
        parsed = urlparse(value)
        if not parsed.scheme:
            value = f"https://{value}"
        return value

    class Meta:
        model = Midia
        fields = ("id", "titulo", "url", "descricao", "tags", "gt", "pergunta", "uploaded_by", "created_at")
        read_only_fields = ("id", "uploaded_by", "created_at")
        extra_kwargs = {
            "titulo": {"required": True, "allow_blank": False},
        }


class BlocoTextoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = BlocoTexto
        fields = ("id", "titulo", "conteudo_html", "tags", "gt", "pergunta", "created_by", "updated_at", "etag")
        read_only_fields = ("id", "created_by", "updated_at", "etag")


class DiffResponseSerializer(serializers.Serializer):
    html = serializers.CharField()


class MebThreadSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome", read_only=True)
    usuario_email = serializers.CharField(source="usuario.email", read_only=True)
    last_message_preview = serializers.SerializerMethodField()
    last_message_origin = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    total_messages = serializers.SerializerMethodField()

    class Meta:
        model = MebThread
        fields = (
            "id",
            "usuario",
            "usuario_nome",
            "usuario_email",
            "created_at",
            "updated_at",
            "last_message_preview",
            "last_message_origin",
            "last_message_at",
            "total_messages",
        )
        read_only_fields = fields

    def get_last_message_preview(self, obj):
        return getattr(obj, "last_message_text", None)

    def get_last_message_origin(self, obj):
        return getattr(obj, "last_message_origin", None)

    def get_last_message_at(self, obj):
        timestamp = getattr(obj, "last_message_at", None)
        if timestamp:
            return timestamp
        return None

    def get_total_messages(self, obj):
        value = getattr(obj, "total_messages", None)
        if value is not None:
            return value
        return obj.messages.count()


class MebMessageSerializer(serializers.ModelSerializer):
    autor_nome = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    usuario = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = MebMessage
        fields = (
            "id",
            "thread",
            "usuario",
            "conteudo",
            "origem",
            "autor",
            "autor_nome",
            "created_at",
            "is_mine",
        )
        read_only_fields = (
            "id",
            "thread",
            "origem",
            "autor",
            "autor_nome",
            "created_at",
            "is_mine",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Usuário não autenticado.")

        usuario_id = validated_data.pop("usuario", None)
        conteudo = validated_data.get("conteudo", "").strip()
        if not conteudo:
            raise serializers.ValidationError({"conteudo": "Envie uma mensagem antes de enviar."})

        cliente_id = getattr(request, "cliente_id", None) or getattr(request.user, "cliente_id", None)
        if not cliente_id and usuario_id is None:
            raise serializers.ValidationError("Cliente não associado ao usuário.")

        target_user = request.user
        if usuario_id is not None:
            if not self._user_can_manage(request.user):
                raise serializers.ValidationError({"usuario": "Somente administradores podem responder clientes."})
            user_model = get_user_model()
            target_user = user_model.objects.filter(id=usuario_id, cliente_id=cliente_id).first()
            if not target_user:
                raise serializers.ValidationError({"usuario": "Usuário não encontrado para este cliente."})
            cliente_id = target_user.cliente_id
        else:
            if not getattr(target_user, "cliente_id", None):
                raise serializers.ValidationError("Usuário não associado a um cliente.")
            cliente_id = cliente_id or target_user.cliente_id

        thread = ensure_thread_for_user(target_user, cliente_id)
        origem = (
            MebMessage.Origem.ADMIN
            if self._user_can_manage(request.user) and target_user.id != request.user.id
            else MebMessage.Origem.CLIENTE
        )

        message = MebMessage.objects.create(
            cliente_id=thread.cliente_id,
            thread=thread,
            autor=request.user,
            origem=origem,
            conteudo=conteudo,
        )
        thread.save(update_fields=["updated_at"])
        return message

    def get_autor_nome(self, obj):
        if obj.autor_id:
            return getattr(obj.autor, "nome", None) or getattr(obj.autor, "email", None)
        if obj.origem == MebMessage.Origem.MASCOTE:
            return "MEB"
        return None

    def get_is_mine(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request.user, "is_authenticated", False):
            return False
        return obj.autor_id == request.user.id

    def _user_can_manage(self, user) -> bool:
        role = getattr(user, "role", "")
        return role in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}


class ConsultaPublicaSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    total_manifestacoes = serializers.SerializerMethodField()

    class Meta:
        model = ConsultaPublica
        fields = (
            "id",
            "titulo",
            "slug",
            "token_acesso",
            "descricao",
            "pdf",
            "pdf_url",
            "data_publicacao",
            "data_validade",
            "data_fechamento",
            "perguntas_votacao",
            "ativa",
            "public_url",
            "total_manifestacoes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "token_acesso", "pdf_url", "public_url", "total_manifestacoes", "created_at", "updated_at")

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if not obj.pdf:
            return None
        try:
            if not obj.pdf.storage.exists(obj.pdf.name):
                # Fallback: tenta achar o arquivo apenas pelo nome na raiz do MEDIA_ROOT
                fallback_name = Path(obj.pdf.name).name
                if obj.pdf.storage.exists(fallback_name):
                    url = obj.pdf.storage.url(fallback_name)
                    return self._build_url(request, url)
                return None
        except Exception:
            return None
        url = str(obj.pdf.url).strip()
        return self._build_url(request, url)

    @staticmethod
    def _build_url(request, url: str) -> str:
        if url.startswith("http"):
            dup_idx = url.find("http", 8)
            if dup_idx != -1:
                url = url[:dup_idx]
        if request and url.startswith("/"):
            url = request.build_absolute_uri(url)
        return url

    def get_public_url(self, obj):
        request = self.context.get("request")
        path = f"/consultas-publicas/{obj.token_acesso}"
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_total_manifestacoes(self, obj):
        if hasattr(obj, "manifestacoes_count"):
            return obj.manifestacoes_count
        return obj.manifestacoes.count()

    def validate_perguntas_votacao(self, value):
        if value is None or value == "" or value == []:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError("Forneça uma lista de perguntas de votação.")
        perguntas = []
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Cada pergunta deve ser um objeto com 'pergunta' e 'opcoes'.")
            pergunta = str(item.get("pergunta", "")).strip()
            opcoes_raw = item.get("opcoes", [])
            if isinstance(opcoes_raw, str):
                opcoes_raw = [l.strip() for l in opcoes_raw.splitlines() if l.strip()]
            opcoes = [str(o).strip() for o in opcoes_raw if str(o).strip()]
            if pergunta:
                perguntas.append({"pergunta": pergunta, "opcoes": opcoes})
        return perguntas

    def validate(self, attrs):
        attrs = super().validate(attrs)
        cliente_id = self.context.get("cliente_id")
        instance = getattr(self, "instance", None)
        slug = attrs.get("slug") or getattr(instance, "slug", "") or ""
        titulo = attrs.get("titulo") or getattr(instance, "titulo", "")
        if not slug:
            slug = slugify(titulo)
            attrs["slug"] = slug
        if not slug:
            raise serializers.ValidationError({"slug": "Informe um título ou slug válido."})
        if cliente_id:
            qs = ConsultaPublica.raw_objects.filter(cliente_id=cliente_id, slug=slug)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"slug": "Já existe uma consulta com este slug para o cliente."})
        return attrs


class ConsultaPublicaPublicSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    esta_disponivel = serializers.SerializerMethodField()
    total_manifestacoes = serializers.SerializerMethodField()

    class Meta:
        model = ConsultaPublica
        fields = (
            "titulo",
            "descricao",
            "pdf_url",
            "data_publicacao",
            "data_validade",
            "data_fechamento",
            "perguntas_votacao",
            "esta_disponivel",
            "total_manifestacoes",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if not obj.pdf:
            return None
        try:
            if not obj.pdf.storage.exists(obj.pdf.name):
                # Fallback: tenta achar o arquivo apenas pelo nome na raiz do MEDIA_ROOT
                fallback_name = Path(obj.pdf.name).name
                if obj.pdf.storage.exists(fallback_name):
                    url = obj.pdf.storage.url(fallback_name)
                    return ConsultaPublicaSerializer._build_url(request, url)
                return None
        except Exception:
            return None
        url = str(obj.pdf.url).strip()
        return ConsultaPublicaSerializer._build_url(request, url)

    def get_esta_disponivel(self, obj):
        return obj.esta_disponivel

    def get_total_manifestacoes(self, obj):
        return obj.manifestacoes.count()


class ManifestacaoPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManifestacaoPublica
        fields = (
            "id",
            "consulta",
            "pagina",
            "comentario",
            "votos",
            "nome_completo",
            "cpf",
            "cidade",
            "estado",
            "contato_email",
            "ip_address",
            "user_agent",
            "created_at",
        )
        read_only_fields = ("id", "consulta", "ip_address", "user_agent", "created_at")


class ManifestacaoPublicaPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManifestacaoPublica
        fields = (
            "id",
            "pagina",
            "comentario",
            "votos",
            "nome_completo",
            "cidade",
            "estado",
            "created_at",
        )
        read_only_fields = fields


class ManifestacaoPublicaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManifestacaoPublica
        fields = (
            "pagina",
            "comentario",
            "votos",
            "nome_completo",
            "cpf",
            "cidade",
            "estado",
            "contato_email",
        )

    def validate_estado(self, value):
        sigla = (value or "").strip().upper()
        if len(sigla) != 2:
            raise serializers.ValidationError("Informe a sigla do estado (ex.: AL).")
        return sigla

    def validate_cpf(self, value):
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if len(digits) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos.")
        return digits

    def validate_nome_completo(self, value):
        nome = (value or "").strip()
        if not nome:
            raise serializers.ValidationError("Informe seu nome completo.")
        return nome

    def validate_cidade(self, value):
        cidade = (value or "").strip()
        if not cidade:
            raise serializers.ValidationError("Informe a cidade.")
        return cidade

    def validate_votos(self, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError("Forneça uma lista de votos.")
        return [str(v).strip() for v in value]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        comentario = (attrs.get("comentario") or "").strip()
        votos = attrs.get("votos") or []
        attrs["comentario"] = comentario
        attrs["votos"] = votos
        has_any_vote = any(v for v in votos)
        if not comentario and not has_any_vote:
            raise serializers.ValidationError("Adicione um comentário ou selecione uma opção de voto.")
        consulta: ConsultaPublica | None = self.context.get("consulta")
        if consulta and consulta.perguntas_votacao:
            for i, v in enumerate(votos):
                if not v:
                    continue
                if i < len(consulta.perguntas_votacao):
                    opcoes = consulta.perguntas_votacao[i].get("opcoes", [])
                    if opcoes and v not in opcoes:
                        raise serializers.ValidationError({"votos": f"Opção inválida para a pergunta {i + 1}."})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(required=False, allow_blank=True)

    @staticmethod
    def _normalize_role(value: str | None) -> str | None:
        if not value:
            return None
        return value.strip().lower()

    @staticmethod
    def _validate_role_for_user(user, role: str | None) -> None:
        if not role:
            return
        allowed_roles = {
            user.Role.MEMBRO_GT,
            user.Role.REVISOR,
            user.Role.ARTICULADOR,
        }
        if role not in allowed_roles:
            raise serializers.ValidationError("Perfil inválido.")
        if user.role in {user.Role.ADMIN_CLIENTE, user.Role.SUPER_ADMIN}:
            return
        if user.role != role:
            raise serializers.ValidationError("Seu usuário não possui acesso ao perfil selecionado.")

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs.get("email")
        password = attrs.get("password")
        role = self._normalize_role(attrs.get("role"))
        if email:
            email = email.strip().lower()
            attrs["email"] = email
        if role:
            attrs["role"] = role
        user = authenticate(request=request, username=email, password=password)
        if not user:
            raise serializers.ValidationError("E-mail ou senha inválidos. Tente novamente.")
        self._validate_role_for_user(user, role)
        attrs["user"] = user
        return attrs


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    role = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        role = LoginSerializer._normalize_role(attrs.get("role"))
        if role:
            attrs["role"] = role
        data = super().validate(attrs)
        LoginSerializer._validate_role_for_user(self.user, role)
        return data


class AiAssistSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=["draft", "grammar", "review"])
    text = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True)
