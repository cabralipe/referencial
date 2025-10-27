"""Serializers da API pública v1."""

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from core.models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema
from core.utils import coletar_contexto_do_cliente
from comments.models import Comentario
from curriculum.models import Anexo, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from reviews.models import Revisao
from workshop.models import CelulaQuadro, Quadro


class ClienteTemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteTema
        fields = (
            "logo_url",
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
        fields = ("id", "ordem", "etapa", "tipo", "status")


class PerguntaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pergunta
        fields = (
            "id",
            "tarefa",
            "ordem",
            "texto",
            "permite_upload",
            "obrigatoria",
        )
        read_only_fields = ("tarefa",)


class AnexoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anexo
        fields = ("id", "resposta", "url", "legenda", "ordem")
        read_only_fields = ("id",)


class RespostaSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = Resposta
        fields = (
            "id",
            "gt",
            "pergunta",
            "conteudo_html",
            "autor",
            "version",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "version", "updated_at", "autor", "etag")

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
            "titulo",
            "conteudo_html",
            "autor",
            "version",
            "created_at",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "version", "created_at", "updated_at", "autor", "etag")

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


class QuadroSerializer(serializers.ModelSerializer):
    celulas = CelulaQuadroSerializer(many=True, read_only=True)

    class Meta:
        model = Quadro
        fields = ("id", "gt", "template", "version", "celulas")


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
            "formato",
            "status",
            "url_resultado",
            "created_at",
            "finished_at",
        )
        read_only_fields = ("id", "status", "url_resultado", "created_at", "finished_at")

    def validate(self, attrs):
        request = self.context.get("request")
        cliente_id = getattr(getattr(request, "user", None), "cliente_id", None)
        if not cliente_id:
            raise serializers.ValidationError("Cliente do usuário não encontrado.")

        alvo_tipo = attrs.get("alvo_tipo")
        alvo_id = attrs.get("alvo_id")
        if not alvo_tipo or not alvo_id:
            return attrs

        modelo_por_tipo = {
            ExportJob.AlvoTipo.TEXTO_UNICO: TextoUnico,
            ExportJob.AlvoTipo.QUADRO: Quadro,
        }
        modelo = modelo_por_tipo.get(alvo_tipo)
        if not modelo:
            raise serializers.ValidationError({"alvo_tipo": "Tipo de alvo inválido."})

        lookup = {"cliente_id": cliente_id, "pk": alvo_id}
        if any(field.attname == "is_deleted" for field in modelo._meta.fields):
            lookup["is_deleted"] = False

        if not modelo.raw_objects.filter(**lookup).exists():
            raise serializers.ValidationError({"alvo_id": "Alvo não encontrado para este cliente."})

        attrs["alvo_id"] = str(alvo_id)
        return attrs


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "cliente",
            "usuario_id",
            "entidade",
            "entidade_id",
            "acao",
            "diff_json",
            "timestamp",
        )
        read_only_fields = fields


class RevisaoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = Revisao
        fields = (
            "id",
            "alvo_tipo",
            "alvo_id",
            "status",
            "parecer_html",
            "revisor",
            "solicitante",
            "created_at",
            "updated_at",
            "etag",
        )
        read_only_fields = ("id", "created_at", "updated_at", "solicitante", "etag")


class ComentarioSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)
    mentions = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True, write_only=True)
    mentions_ids = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comentario
        fields = (
            "id",
            "alvo_tipo",
            "alvo_id",
            "anchor_json",
            "conteudo_html",
            "autor",
            "resolvido",
            "resolvido_por",
            "resolved_at",
            "mentions",
            "mentions_ids",
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

    def get_mentions_ids(self, obj):
        return list(obj.mentions.values_list("id", flat=True))


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ("id", "tipo", "payload_json", "lida", "created_at")
        read_only_fields = ("id", "tipo", "payload_json", "created_at")


class MidiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Midia
        fields = ("id", "url", "legenda", "tags", "uploaded_by", "created_at")
        read_only_fields = ("id", "uploaded_by", "created_at")


class BlocoTextoSerializer(serializers.ModelSerializer):
    etag = serializers.CharField(read_only=True)

    class Meta:
        model = BlocoTexto
        fields = ("id", "titulo", "conteudo_html", "tags", "created_by", "updated_at", "etag")
        read_only_fields = ("id", "created_by", "updated_at", "etag")


class DiffResponseSerializer(serializers.Serializer):
    html = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        email = attrs.get("email")
        password = attrs.get("password")
        if email:
            email = email.strip().lower()
            attrs["email"] = email
        user = authenticate(request=request, username=email, password=password)
        if not user:
            raise serializers.ValidationError("Credenciais inválidas")
        attrs["user"] = user
        return attrs
