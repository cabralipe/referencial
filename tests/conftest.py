import pytest
from rest_framework.test import APIClient

from core.models import Cliente, Usuario


@pytest.fixture
def cliente(db):
    return Cliente.objects.create(nome="Prefeitura Teste", slug="prefeitura-teste")


@pytest.fixture
def usuario(cliente, django_user_model):
    user: Usuario = django_user_model.objects.create_user(
        email="admin@teste.com",
        password="senha123",
        nome="Admin Teste",
        cliente=cliente,
        role=Usuario.Role.ADMIN_CLIENTE,
    )
    return user


@pytest.fixture
def gt(cliente):
    from curriculum.models import GT

    return GT.objects.create(cliente=cliente, nome="GT Base", etapa="I")


@pytest.fixture
def tarefa(cliente):
    from curriculum.models import Tarefa

    return Tarefa.objects.create(cliente=cliente, ordem=1, etapa="I", tipo=Tarefa.Tipo.PERGUNTAS)


@pytest.fixture
def pergunta(cliente, tarefa):
    from curriculum.models import Pergunta

    return Pergunta.objects.create(
        cliente=cliente,
        tarefa=tarefa,
        ordem=1,
        texto="Qual a proposta pedagógica?",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, usuario):
    api_client.force_authenticate(usuario)
    return api_client
