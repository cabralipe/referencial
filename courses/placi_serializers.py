from rest_framework import serializers

from .models import AvaliacaoPlano, PlanoAula, Rubrica, RubricaCriterio


class PlanoAulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanoAula
        fields = (
            "id",
            "curso",
            "autor",
            "escola",
            "etapa_modalidade",
            "componente_curricular",
            "unidade_tematica",
            "habilidades",
            "objetivos",
            "conteudos",
            "metodologia",
            "recursos",
            "avaliacao",
            "estrategias_recomposicao",
            "estrategias_inclusivas",
            "referencias",
            "metas_ppp",
            "habilidades_referencial",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("autor", "created_at", "updated_at")


class RubricaCriterioSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubricaCriterio
        fields = ("id", "rubrica", "nome", "descricao", "pontuacao_maxima", "ordem")


class RubricaSerializer(serializers.ModelSerializer):
    criterios = RubricaCriterioSerializer(many=True, read_only=True)

    class Meta:
        model = Rubrica
        fields = ("id", "curso", "nome", "descricao", "criterios")


class AvaliacaoPlanoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvaliacaoPlano
        fields = ("id", "plano", "avaliador", "criterio", "pontuacao", "comentario", "created_at")
        read_only_fields = ("avaliador", "created_at")

