"""Serializers da API pública v1."""

from __future__ import annotations

import json

from django.contrib.auth import authenticate, get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from core.models import AuditLog, Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, UserSessionLog
from core.utils import coletar_contexto_do_cliente
from comments.models import Comentario
from consultas.models import ConsultaPublica, ManifestacaoPublica
from curriculum.models import Anexo, GT, Pergunta, Resposta, Tarefa, TextoColaborativo, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from exports.models import ExportJob
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from reviews.models import Revisao
from workshop.models import CelulaQuadro, Quadro
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
        fields = ("id", "nome", "ordem", "etapa", "tipo", "status")


class GTSerializer(serializers.ModelSerializer):
    class Meta:
        model = GT
        fields = ("id", "nome", "etapa")


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
        fields = ("id", "nome", "email")
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
            "pergunta_votacao",
            "opcoes_votacao",
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
        url = obj.pdf.url
        if request:
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

    def validate_opcoes_votacao(self, value):
        if value is None or value == "" or value == []:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = [line.strip() for line in value.splitlines() if line.strip()]
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError("Forneça uma lista de opções de voto (um item por linha).")
        opcoes = []
        for item in value:
            texto = str(item).strip()
            if not texto:
                continue
            opcoes.append(texto)
        return opcoes

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
            "pergunta_votacao",
            "opcoes_votacao",
            "esta_disponivel",
            "total_manifestacoes",
        )
        read_only_fields = fields

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if not obj.pdf:
            return None
        url = obj.pdf.url
        if request:
            url = request.build_absolute_uri(url)
        return url

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
            "voto",
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
            "voto",
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
            "voto",
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        comentario = (attrs.get("comentario") or "").strip()
        voto = (attrs.get("voto") or "").strip()
        attrs["comentario"] = comentario
        attrs["voto"] = voto
        if not comentario and not voto:
            raise serializers.ValidationError("Adicione um comentário ou selecione uma opção de voto.")
        consulta: ConsultaPublica | None = self.context.get("consulta")
        if consulta and consulta.pergunta_votacao and consulta.opcoes_votacao:
            if voto and voto not in consulta.opcoes_votacao:
                raise serializers.ValidationError({"voto": "Opção inválida para esta votação."})
        return attrs


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
