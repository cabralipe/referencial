"""Serializers da API de cursos."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from curriculum.models import Tarefa
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico

from .models import (
    Curso,
    CursoAviso,
    CursoCertificadoEmitido,
    CursoCronogramaItem,
    CursoItem,
    CursoModulo,
    CursoParticipacao,
    CursoProgresso,
    CursoProgressoItem,
    PlanoAulaPublicacao,
    PlanoAulaResposta,
)


DEFAULT_CERT_RULES = {
    "presenca_presencial_obrigatoria": True,
    "min_sincronos": 4,
    "min_planos": 1,
    "entrega_final_obrigatoria": True,
    "compartilhar_banco_obrigatorio": True,
}

PLANO_AULA_TEMPLATE_NAME = "Plano de Aula Padrão"
PLANO_AULA_TEMPLATE_DESCRIPTION = "Template padrão para produção orientada de plano de aula no curso."
PLANO_AULA_FIELD_SPECS = [
    ("escola", "Escola"),
    ("professor", "Professor"),
    ("etapa_modalidade", "Etapa/Modalidade"),
    ("componente_curricular", "Componente Curricular"),
    ("unidade_tematica", "Unidade Temática"),
    ("habilidades_referencial", "Habilidades (código do Referencial)"),
    ("objetivos_aprendizagem", "Objetivos de Aprendizagem"),
    ("conteudos", "Conteúdos"),
    ("metodologia", "Metodologia"),
    ("recursos", "Recursos"),
    ("avaliacao", "Avaliação"),
    ("estrategias_recomposicao", "Estratégias de Recomposição"),
    ("estrategias_inclusivas_aee", "Estratégias Inclusivas (AEE)"),
    ("referencias", "Referências"),
]


def normalize_cert_rules(payload) -> dict:
    rules = dict(DEFAULT_CERT_RULES)
    if not isinstance(payload, dict):
        return rules
    for key in ("presenca_presencial_obrigatoria", "entrega_final_obrigatoria", "compartilhar_banco_obrigatorio"):
        if key in payload:
            rules[key] = bool(payload.get(key))
    for key in ("min_sincronos", "min_planos"):
        if key in payload:
            try:
                rules[key] = max(0, int(payload.get(key)))
            except (TypeError, ValueError):
                pass
    return rules


def ensure_plano_aula_template(cliente_id: int) -> FormularioDinamico:
    formulario, _ = FormularioDinamico.objects.update_or_create(
        cliente_id=cliente_id,
        nome=PLANO_AULA_TEMPLATE_NAME,
        defaults={
            "descricao": PLANO_AULA_TEMPLATE_DESCRIPTION,
            "ativo": True,
        },
    )
    existing = {c.chave: c for c in CampoDinamico.objects.filter(formulario=formulario)}
    for ordem, (chave, label) in enumerate(PLANO_AULA_FIELD_SPECS, start=1):
        defaults = {
            "tipo": CampoDinamico.Tipo.TEXTO,
            "config_json": {"label": label},
            "obrigatorio": True,
            "ordem": ordem,
        }
        campo = existing.get(chave)
        if campo:
            changed = False
            for attr, value in defaults.items():
                if getattr(campo, attr) != value:
                    setattr(campo, attr, value)
                    changed = True
            if changed:
                campo.save(update_fields=["tipo", "config_json", "obrigatorio", "ordem", "updated_at"])
            continue
        CampoDinamico.objects.create(
            cliente_id=cliente_id,
            formulario=formulario,
            chave=chave,
            **defaults,
        )
    return formulario


def flatten_plano_resposta_campos(resposta: PlanoAulaResposta) -> dict[str, str]:
    rows = RespostaCampoDinamico.objects.filter(
        cliente_id=resposta.cliente_id,
        formulario_id=resposta.formulario_id,
        owner_type=RespostaCampoDinamico.OwnerType.CURSO_PLANO,
        owner_id=str(resposta.id),
    ).select_related("campo")
    data: dict[str, str] = {}
    for row in rows:
        value = row.valor_texto
        if row.valor_num is not None:
            value = str(row.valor_num)
        elif row.valor_bool is not None:
            value = "true" if row.valor_bool else "false"
        elif row.url_arquivo:
            value = row.url_arquivo
        data[row.campo.chave] = value or ""
    return data


def save_plano_resposta_campos(resposta: PlanoAulaResposta, campos_payload: dict) -> dict:
    if not isinstance(campos_payload, dict):
        raise serializers.ValidationError({"campos": "Envie um objeto com chave/valor dos campos."})
    campos = list(CampoDinamico.objects.filter(formulario_id=resposta.formulario_id).order_by("ordem"))
    fields_by_key = {c.chave: c for c in campos}
    invalid_keys = sorted(set(campos_payload.keys()) - set(fields_by_key.keys()))
    if invalid_keys:
        raise serializers.ValidationError({"campos": f"Campos inválidos: {', '.join(invalid_keys)}"})

    saved: dict[str, str] = flatten_plano_resposta_campos(resposta)
    for key, raw in campos_payload.items():
        campo = fields_by_key[key]
        value = "" if raw is None else str(raw).strip()
        instance = RespostaCampoDinamico.objects.filter(
            cliente_id=resposta.cliente_id,
            formulario_id=resposta.formulario_id,
            campo=campo,
            owner_type=RespostaCampoDinamico.OwnerType.CURSO_PLANO,
            owner_id=str(resposta.id),
        ).first()
        payload = {
            "cliente_id": resposta.cliente_id,
            "formulario_id": resposta.formulario_id,
            "campo": campo,
            "owner_type": RespostaCampoDinamico.OwnerType.CURSO_PLANO,
            "owner_id": str(resposta.id),
            "valor_texto": value,
            "valor_num": None,
            "valor_bool": None,
            "url_arquivo": "",
        }
        if instance:
            for attr, attr_value in payload.items():
                setattr(instance, attr, attr_value)
            instance.save(update_fields=["valor_texto", "valor_num", "valor_bool", "url_arquivo", "updated_at"])
        else:
            RespostaCampoDinamico.objects.create(**payload)
        saved[key] = value
    resposta.dados_cache_json = saved
    resposta.save(update_fields=["dados_cache_json", "updated_at"])
    return saved


class CursoAvisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CursoAviso
        fields = ("id", "titulo", "corpo", "publicado_em")


class CursoCronogramaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CursoCronogramaItem
        fields = ("id", "semana", "titulo", "descricao", "ordem")


class CursoItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CursoItem
        fields = ("id", "ordem", "tipo", "titulo", "payload_json")


class CursoModuloSerializer(serializers.ModelSerializer):
    itens = CursoItemSerializer(many=True, read_only=True)

    class Meta:
        model = CursoModulo
        fields = ("id", "titulo", "ordem", "tipo", "itens")


class CursoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = (
            "id",
            "nome",
            "categoria",
            "descricao",
            "carga_horaria_total",
            "publicado",
            "created_at",
            "updated_at",
        )


class CursoItemWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    ordem = serializers.IntegerField(required=False, min_value=0)
    tipo = serializers.ChoiceField(choices=CursoItem.Tipo.choices)
    titulo = serializers.CharField(max_length=255)
    payload_json = serializers.JSONField(required=False)


class CursoModuloWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    titulo = serializers.CharField(max_length=255)
    ordem = serializers.IntegerField(required=False, min_value=0)
    tipo = serializers.ChoiceField(choices=CursoModulo.Tipo.choices)
    itens = CursoItemWriteSerializer(many=True, required=False)


class CursoAvisoWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    titulo = serializers.CharField(max_length=255)
    corpo = serializers.CharField()
    publicado_em = serializers.DateTimeField(required=False, allow_null=True)


class CursoCronogramaItemWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    semana = serializers.CharField(required=False, allow_blank=True, max_length=120)
    titulo = serializers.CharField(max_length=255)
    descricao = serializers.CharField(required=False, allow_blank=True)
    ordem = serializers.IntegerField(required=False, min_value=0)


class CursoWriteSerializer(serializers.ModelSerializer):
    modulos = CursoModuloWriteSerializer(many=True, required=False)
    avisos = CursoAvisoWriteSerializer(many=True, required=False)
    cronograma = CursoCronogramaItemWriteSerializer(many=True, required=False)
    regras_certificacao_json = serializers.JSONField(required=False)

    class Meta:
        model = Curso
        fields = (
            "id",
            "nome",
            "categoria",
            "descricao",
            "objetivos",
            "carga_horaria_total",
            "carga_presencial",
            "carga_sincrona",
            "carga_producao",
            "publicado",
            "regras_certificacao_json",
            "modulos",
            "avisos",
            "cronograma",
        )

    def validate_regras_certificacao_json(self, value):
        return normalize_cert_rules(value)

    def validate(self, attrs):
        request = self.context.get("request")
        cliente_id = self.context.get("cliente_id")
        if not cliente_id and request and getattr(request.user, "cliente_id", None):
            cliente_id = int(request.user.cliente_id)
        modulos = attrs.get("modulos")
        if modulos is None:
            return attrs

        for modulo in modulos:
            for item in modulo.get("itens", []):
                payload = item.get("payload_json") or {}
                if not isinstance(payload, dict):
                    raise serializers.ValidationError({"modulos": "payload_json de item deve ser objeto JSON."})
                tarefa_id = payload.get("tarefa_id")
                if tarefa_id is not None and not Tarefa.objects.filter(cliente_id=cliente_id, pk=tarefa_id).exists():
                    raise serializers.ValidationError({"modulos": f"tarefa_id inválido para o cliente: {tarefa_id}"})
                formulario_id = payload.get("formulario_id")
                if formulario_id is not None and not FormularioDinamico.objects.filter(
                    cliente_id=cliente_id, pk=formulario_id
                ).exists():
                    raise serializers.ValidationError({"modulos": f"formulario_id inválido para o cliente: {formulario_id}"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        modulos_data = validated_data.pop("modulos", [])
        avisos_data = validated_data.pop("avisos", [])
        cronograma_data = validated_data.pop("cronograma", [])
        curso = Curso.objects.create(**validated_data)
        self._replace_nested(curso, modulos_data, avisos_data, cronograma_data)
        return curso

    @transaction.atomic
    def update(self, instance, validated_data):
        modulos_data = validated_data.pop("modulos", None)
        avisos_data = validated_data.pop("avisos", None)
        cronograma_data = validated_data.pop("cronograma", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if modulos_data is not None:
            self._replace_modulos(instance, modulos_data)
        if avisos_data is not None:
            self._replace_avisos(instance, avisos_data)
        if cronograma_data is not None:
            self._replace_cronograma(instance, cronograma_data)
        return instance

    def _replace_nested(self, curso: Curso, modulos_data, avisos_data, cronograma_data):
        self._replace_modulos(curso, modulos_data)
        self._replace_avisos(curso, avisos_data)
        self._replace_cronograma(curso, cronograma_data)

    def _replace_modulos(self, curso: Curso, modulos_data):
        cliente_id = curso.cliente_id
        CursoItem.objects.filter(modulo__curso=curso).delete()
        CursoModulo.objects.filter(curso=curso).delete()
        for idx, modulo_data in enumerate(modulos_data or [], start=1):
            modulo = CursoModulo.objects.create(
                cliente_id=cliente_id,
                curso=curso,
                titulo=modulo_data["titulo"],
                ordem=modulo_data.get("ordem", idx),
                tipo=modulo_data["tipo"],
            )
            for jdx, item_data in enumerate(modulo_data.get("itens", []), start=1):
                payload = item_data.get("payload_json") or {}
                if item_data["tipo"] == CursoItem.Tipo.FORMULARIO and not payload.get("formulario_id"):
                    formulario = ensure_plano_aula_template(cliente_id)
                    payload = {**payload, "formulario_id": formulario.id}
                CursoItem.objects.create(
                    cliente_id=cliente_id,
                    modulo=modulo,
                    ordem=item_data.get("ordem", jdx),
                    tipo=item_data["tipo"],
                    titulo=item_data["titulo"],
                    payload_json=payload,
                )

    def _replace_avisos(self, curso: Curso, avisos_data):
        CursoAviso.objects.filter(curso=curso).delete()
        for aviso_data in avisos_data or []:
            CursoAviso.objects.create(cliente_id=curso.cliente_id, curso=curso, **aviso_data)

    def _replace_cronograma(self, curso: Curso, cronograma_data):
        CursoCronogramaItem.objects.filter(curso=curso).delete()
        for idx, item_data in enumerate(cronograma_data or [], start=1):
            CursoCronogramaItem.objects.create(
                cliente_id=curso.cliente_id,
                curso=curso,
                semana=item_data.get("semana", ""),
                titulo=item_data["titulo"],
                descricao=item_data.get("descricao", ""),
                ordem=item_data.get("ordem", idx),
            )


class CursoProgressoItemSerializer(serializers.ModelSerializer):
    item_id = serializers.IntegerField(source="item.id", read_only=True)

    class Meta:
        model = CursoProgressoItem
        fields = ("id", "item_id", "referencia_tipo", "referencia_id", "concluido_em")


class CursoProgressoSerializer(serializers.ModelSerializer):
    itens = CursoProgressoItemSerializer(many=True, read_only=True)

    class Meta:
        model = CursoProgresso
        fields = ("id", "percentual", "itens")


class CursoDetailSerializer(serializers.ModelSerializer):
    avisos = CursoAvisoSerializer(many=True, read_only=True)
    cronograma = serializers.SerializerMethodField()
    menu = serializers.SerializerMethodField()
    modulos = serializers.SerializerMethodField()
    progresso = serializers.SerializerMethodField()
    regras_certificacao = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = (
            "id",
            "nome",
            "categoria",
            "descricao",
            "objetivos",
            "carga_horaria_total",
            "carga_presencial",
            "carga_sincrona",
            "carga_producao",
            "publicado",
            "avisos",
            "cronograma",
            "menu",
            "modulos",
            "progresso",
            "regras_certificacao",
            "created_at",
            "updated_at",
        )

    def get_cronograma(self, obj):
        return CursoCronogramaItemSerializer(obj.cronograma_itens.all(), many=True).data

    def get_menu(self, obj):
        modulos = obj.modulos.all().order_by("ordem", "id")
        return [{"id": m.id, "titulo": m.titulo, "ordem": m.ordem, "tipo": m.tipo} for m in modulos]

    def get_modulos(self, obj):
        modulos = obj.modulos.all().prefetch_related("itens").order_by("ordem", "id")
        return CursoModuloSerializer(modulos, many=True).data

    def get_progresso(self, obj):
        progresso = self.context.get("progresso")
        if not progresso:
            return {"percentual": "0.00", "itens": []}
        return CursoProgressoSerializer(progresso).data

    def get_regras_certificacao(self, obj):
        return normalize_cert_rules(obj.regras_certificacao_json)


class CursoProgressoMarkSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()


class PlanoAulaRespostaReadSerializer(serializers.ModelSerializer):
    campos = serializers.SerializerMethodField()
    publicacao = serializers.SerializerMethodField()

    class Meta:
        model = PlanoAulaResposta
        fields = (
            "id",
            "curso",
            "usuario",
            "formulario",
            "titulo",
            "status",
            "compartilhado_banco",
            "dados_cache_json",
            "campos",
            "publicacao",
            "enviado_em",
            "bloqueado_em",
            "created_at",
            "updated_at",
        )

    def get_campos(self, obj):
        return obj.dados_cache_json or flatten_plano_resposta_campos(obj)

    def get_publicacao(self, obj):
        pub = obj.publicacoes.order_by("-updated_at").first()
        if not pub:
            return None
        return {
            "id": pub.id,
            "status": pub.status,
            "allow_comments": pub.allow_comments,
            "updated_at": pub.updated_at,
        }


class PlanoAulaRespostaWriteSerializer(serializers.Serializer):
    curso = serializers.IntegerField()
    titulo = serializers.CharField(required=False, allow_blank=True, max_length=255)
    campos = serializers.JSONField(required=False)


class PlanoAulaEnviarSerializer(serializers.Serializer):
    compartilhar_no_banco = serializers.BooleanField(required=False, default=False)
    allow_comments = serializers.BooleanField(required=False, default=True)


class PlanoAulaPublicacaoSerializer(serializers.ModelSerializer):
    autor_nome = serializers.SerializerMethodField()
    resposta_formulario_id = serializers.IntegerField(source="resposta_formulario.id", read_only=True)

    class Meta:
        model = PlanoAulaPublicacao
        fields = (
            "id",
            "resposta_formulario_id",
            "autor",
            "autor_nome",
            "status",
            "allow_comments",
            "payload_json",
            "created_at",
            "updated_at",
        )

    def get_autor_nome(self, obj):
        return getattr(obj.autor, "nome", None) or getattr(obj.autor, "email", None)


class PlanoAulaPublicacaoUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PlanoAulaPublicacao.Status.choices)
    allow_comments = serializers.BooleanField(required=False)


class CertificacaoEmitirSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)


class CertificacaoStatusSerializer(serializers.Serializer):
    regras = serializers.DictField()
    checks = serializers.DictField()
    pode_emitir_certificado = serializers.BooleanField()
    certificado_emitido = serializers.BooleanField()
    certificado = serializers.DictField(required=False, allow_null=True)
