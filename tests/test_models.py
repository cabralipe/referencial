import pytest

from core.models import Cliente, ClienteConfig, ClienteFeatureFlag, ClienteTema, Usuario
from core.utils import coletar_contexto_do_cliente
from curriculum.models import Escola, Resposta, TextoUnico
from dynamicforms.models import CampoDinamico, FormularioDinamico, RespostaCampoDinamico
from workshop.models import CelulaQuadro, Quadro


@pytest.mark.django_db
def test_domain_models_linkage(cliente, usuario, gt, tarefa, pergunta):
    ClienteConfig.objects.create(cliente=cliente, chave="export_plugin", valor_texto="default")
    ClienteFeatureFlag.objects.create(cliente=cliente, flag="exports", ativo=True)
    ClienteTema.objects.create(cliente=cliente, logo_url="https://example.com/logo.png")

    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Conteúdo</p>",
        autor=usuario,
    )
    texto = TextoUnico.objects.create(
        cliente=cliente,
        gt=gt,
        tarefa=tarefa,
        responsavel=usuario,
        conteudo_html="<p>Texto</p>",
    )
    quadro = Quadro.objects.create(cliente=cliente, gt=gt, template="default")
    CelulaQuadro.objects.create(
        cliente=cliente,
        quadro=quadro,
        linha=1,
        coluna=1,
        valor_html="Cel",
    )

    formulario = FormularioDinamico.objects.create(cliente=cliente, nome="Form", descricao="Extra")
    campo = CampoDinamico.objects.create(
        cliente=cliente,
        formulario=formulario,
        chave="extra",
        tipo=CampoDinamico.Tipo.TEXTO,
        ordem=1,
    )
    RespostaCampoDinamico.objects.create(
        cliente=cliente,
        formulario=formulario,
        campo=campo,
        owner_type=RespostaCampoDinamico.OwnerType.RESPOSTA,
        owner_id=str(resposta.id),
        valor_texto="Algum valor",
    )

    contexto = coletar_contexto_do_cliente(cliente)

    assert resposta.etag.startswith("W/")
    assert texto.version == 1
    assert quadro.celulas.count() == 1
    assert contexto["configs"]["export_plugin"] == "default"
    assert contexto["flags"]["exports"] is True
    assert contexto["tema"]["logo_url"] == "https://example.com/logo.png"


@pytest.mark.django_db
def test_usuario_professor_exige_escola(cliente, django_user_model):
    with pytest.raises(ValueError):
        django_user_model.objects.create_user(
            email="prof-sem-escola@teste.com",
            password="senha123",
            nome="Professor Sem Escola",
            cliente=cliente,
            role=Usuario.Role.PROFESSOR,
        )


@pytest.mark.django_db
def test_usuario_escola_deve_pertencer_ao_mesmo_cliente(cliente, django_user_model):
    cliente_b = Cliente.objects.create(nome="Cliente B", slug="cliente-b")
    escola_b = Escola.objects.create(cliente=cliente_b, nome="Escola B")
    with pytest.raises(ValueError):
        django_user_model.objects.create_user(
            email="prof-escola-outra@teste.com",
            password="senha123",
            nome="Professor Inválido",
            cliente=cliente,
            escola=escola_b,
            role=Usuario.Role.PROFESSOR,
        )
