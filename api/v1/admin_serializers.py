"""Serializers para o Admin Console (CRUD completo)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from core.models import (
    AuditLog,
    Cliente,
    ClienteConfig,
    ClienteFeatureFlag,
    ClienteTema,
    Eixo,
    ScoreEntry,
    ThrottleBlock,
    UserSessionLog,
)
from curriculum.models import (
    Anexo,
    Area,
    Escola,
    GT,
    Pergunta,
    Resposta,
    Tarefa,
    TextoColaborativo,
    TextoUnico,
)
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from meb.models import MebMessage, MebThread
from notifications.models import Notificacao
from reviews.models import Revisao, ReviewDecision, ReviewerAssignment
from workshop.models import CelulaQuadro, Quadro, QuadroColuna, QuadroLinha

UserModel = get_user_model()


class ClienteAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"


class ClienteConfigAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteConfig
        fields = "__all__"


class ClienteFeatureFlagAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteFeatureFlag
        fields = "__all__"


class ClienteTemaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteTema
        fields = "__all__"


class EixoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eixo
        fields = "__all__"


class UsuarioAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = UserModel
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
        }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        request = self.context.get("request")

        role = attrs.get("role", getattr(instance, "role", UserModel.Role.LEITOR))
        cliente = attrs.get("cliente", getattr(instance, "cliente", None))
        clientes = attrs.get("clientes")
        escola = attrs.get("escola", getattr(instance, "escola", None))
        eixos = attrs.get("eixos")
        scope_cliente_id = getattr(request, "cliente_id", None) if request else None
        cliente_id = getattr(cliente, "id", None)
        clientes_list = list(clientes) if clientes is not None else None
        eixos_list = list(eixos) if eixos is not None else None

        if not cliente_id and clientes_list:
            cliente = clientes_list[0]
            cliente_id = getattr(cliente, "id", None)
            attrs["cliente"] = cliente

        if (
            not cliente_id
            and scope_cliente_id
            and request
            and getattr(request.user, "role", None) != request.user.Role.SUPER_ADMIN
        ):
            cliente_id = scope_cliente_id

        if role != UserModel.Role.SUPER_ADMIN and not cliente_id:
            raise serializers.ValidationError({"cliente": "Usuários que não são super_admin devem possuir cliente."})

        if role != UserModel.Role.SUPER_ADMIN and clientes_list is not None:
            if cliente and all(item.id != cliente.id for item in clientes_list):
                clientes_list.append(cliente)
            attrs["clientes"] = clientes_list

        if role in UserModel.ESCOLA_REQUIRED_ROLES and not escola:
            raise serializers.ValidationError(
                {"escola": "Diretor, Coordenador Pedagogico e Professor devem possuir escola."}
            )

        if role == UserModel.Role.SUPER_ADMIN:
            if cliente_id:
                raise serializers.ValidationError({"cliente": "Super admin não pode possuir cliente."})
            if escola:
                raise serializers.ValidationError({"escola": "Super admin não pode possuir escola."})
            attrs["cliente"] = None
            if clientes is not None:
                attrs["clientes"] = []

        if escola and cliente_id and escola.cliente_id != cliente_id:
            raise serializers.ValidationError({"escola": "Escola deve pertencer ao mesmo cliente do usuario."})

        if eixos_list is not None:
            target_cliente_id = cliente_id or scope_cliente_id
            if target_cliente_id and any(eixo.cliente_id != target_cliente_id for eixo in eixos_list):
                raise serializers.ValidationError({"eixos": "Eixos devem pertencer ao mesmo cliente do usuario."})

        return attrs


class AuditLogAdminSerializer(serializers.ModelSerializer):
    usuario_id = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        exclude = ["created_at", "updated_at"]

    def get_usuario_id(self, obj) -> str | int | None:
        if not obj.usuario_id:
            return None
        user = UserModel.objects.filter(id=obj.usuario_id).first()
        if user:
            return f"{user.nome} ({user.email})"
        return obj.usuario_id


class ThrottleBlockAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThrottleBlock
        fields = "__all__"


class ScoreEntryAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreEntry
        fields = "__all__"


class UserSessionLogAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSessionLog
        fields = "__all__"


class GTAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = GT
        fields = "__all__"


class AreaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = "__all__"


class EscolaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Escola
        fields = "__all__"


class TarefaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarefa
        fields = "__all__"


class PerguntaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pergunta
        fields = "__all__"


class RespostaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resposta
        fields = "__all__"


class AnexoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anexo
        fields = "__all__"


class TextoUnicoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextoUnico
        fields = "__all__"


class TextoColaborativoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextoColaborativo
        fields = "__all__"


class QuadroAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quadro
        fields = "__all__"


class QuadroLinhaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuadroLinha
        fields = "__all__"


class QuadroColunaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuadroColuna
        fields = "__all__"


class CelulaQuadroAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelulaQuadro
        fields = "__all__"


class FormularioDinamicoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormularioDinamico
        fields = "__all__"


class CampoDinamicoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampoDinamico
        fields = "__all__"


class RespostaCampoDinamicoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = RespostaCampoDinamico
        fields = "__all__"


class RevisaoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revisao
        fields = "__all__"


class ReviewerAssignmentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewerAssignment
        fields = "__all__"


class ReviewDecisionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewDecision
        fields = "__all__"


class ExportJobAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = "__all__"


class NotificacaoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = "__all__"


class ComentarioAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = "__all__"


class MidiaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Midia
        fields = "__all__"


class BlocoTextoAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlocoTexto
        fields = "__all__"


class ConsultaPublicaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultaPublica
        fields = "__all__"


class ManifestacaoPublicaAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManifestacaoPublica
        fields = "__all__"


class MebThreadAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = MebThread
        fields = "__all__"


class MebMessageAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = MebMessage
        fields = "__all__"
