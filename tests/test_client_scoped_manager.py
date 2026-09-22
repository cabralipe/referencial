"""Regressão do ``ClientScopedManager`` em managers de relacionamento reverso.

``obj.filhos.filter(is_deleted=False)`` passa pelo ramo ``with_deleted()`` do
manager. Antes da correção, esse ramo chamava ``super().get_queryset()`` e
descartava o filtro da relação, devolvendo registros de *outros* pais.
"""

import pytest

from ava.models import ColunaPlanilha, ModeloPlanilha
from core.models import Cliente, Usuario


@pytest.fixture
def cenario(db):
    cliente = Cliente.objects.create(nome="Município Manager", slug="municipio-manager")
    admin = Usuario.objects.create_user(
        email="admin-manager@example.com",
        nome="Admin Manager",
        password="senha123",
        cliente=cliente,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    primeiro = ModeloPlanilha.objects.create(
        cliente=cliente, nome="Primeiro", slug="primeiro", created_by=admin
    )
    segundo = ModeloPlanilha.objects.create(
        cliente=cliente, nome="Segundo", slug="segundo", created_by=admin
    )
    ColunaPlanilha.objects.create(
        cliente=cliente,
        modelo=primeiro,
        chave="coluna-a",
        titulo="Coluna A",
        tipo=ColunaPlanilha.Tipo.TEXTO,
    )
    ColunaPlanilha.objects.create(
        cliente=cliente,
        modelo=segundo,
        chave="coluna-b",
        titulo="Coluna B",
        tipo=ColunaPlanilha.Tipo.TEXTO,
    )
    return primeiro, segundo


def test_filtro_por_is_deleted_mantem_o_escopo_do_relacionamento(cenario):
    primeiro, segundo = cenario
    assert [c.titulo for c in primeiro.colunas.filter(is_deleted=False)] == ["Coluna A"]
    assert [c.titulo for c in segundo.colunas.filter(is_deleted=False)] == ["Coluna B"]


def test_soft_delete_some_do_relacionamento(cenario):
    primeiro, _ = cenario
    primeiro.colunas.first().delete()
    assert primeiro.colunas.filter(is_deleted=False).count() == 0
    assert primeiro.colunas.filter(is_deleted=True).count() == 1
