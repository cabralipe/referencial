from rest_framework import serializers

from .models import DocumentoPublicacao, DocumentoVersao, PlanoMetaPPP, ReferencialHabilidade


class PlanoMetaPPPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoMetaPPP
        fields = ("id", "codigo", "titulo", "descricao", "eixo")


class ReferencialHabilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferencialHabilidade
        fields = ("id", "codigo", "descricao", "componente_curricular", "etapa_modalidade")


class DocumentoVersaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoVersao
        fields = ("id", "tipo", "titulo", "conteudo_html", "versao", "autor", "created_at")
        read_only_fields = ("autor", "created_at")


class DocumentoPublicacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoPublicacao
        fields = ("id", "documento", "publicado_por", "publicado_em", "observacao")
        read_only_fields = ("publicado_por", "publicado_em")

