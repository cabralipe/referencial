import pytest

from curriculum.models import Resposta, TextoUnico
from curriculum.services.synthesis import gerar_texto_unico


@pytest.mark.django_db
def test_gerar_texto_unico(cliente, gt, tarefa, pergunta, usuario):
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Conteúdo GT</p>",
        autor=usuario,
    )
    texto = TextoUnico.objects.create(cliente=cliente, gt=gt, tarefa=tarefa)
    gerar_texto_unico(texto)
    texto.refresh_from_db()
    assert "Conteúdo GT" in texto.conteudo_html
    assert str(pergunta.texto) in texto.conteudo_html
