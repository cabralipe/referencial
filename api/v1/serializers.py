"""Serializers da API pública v1."""

from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from core.models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema
from core.utils import coletar_contexto_do_cliente
from curriculum.models import Anexo, Pergunta, Resposta, Tarefa, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request=request, email=attrs.get("email"), password=attrs.get("password"))
        if not user:
            raise serializers.ValidationError("Credenciais inválidas")
        attrs["user"] = user
        return attrs
