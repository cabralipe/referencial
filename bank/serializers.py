from rest_framework import serializers

from .models import PlanoPublicado, PlanoPublicadoAvaliacao, PlanoPublicadoComentario


class PlanoPublicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoPublicado
        fields = (
            "id",
            "plano",
            "publicado_por",
            "data_publicacao",
            "visibilidade",
            "status_curadoria",
        )
        read_only_fields = ("publicado_por", "data_publicacao", "status_curadoria")


class PlanoPublicadoComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoPublicadoComentario
        fields = ("id", "plano_publicado", "autor", "comentario", "created_at")
        read_only_fields = ("autor", "created_at")


class PlanoPublicadoAvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoPublicadoAvaliacao
        fields = ("id", "plano_publicado", "avaliador", "nota", "comentario", "created_at")
        read_only_fields = ("avaliador", "created_at")

