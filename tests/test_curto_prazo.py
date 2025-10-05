import json

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from comments.models import Comentario
from core.models import ClienteFeatureFlag
from curriculum.models import Resposta, TextoUnico
from library.models import BlocoTexto, Midia
from notifications.models import Notificacao
from notifications.services import criar_notificacao
from reviews.models import Revisao
from tasks.diffs import render_and_cache_diff
from tasks.notifications import send_email_notification


@pytest.mark.django_db
def test_revisao_fluxo(monkeypatch, cliente, articulador, usuario, gt, pergunta):
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Versão 1</p>",
        autor=usuario,
    )
    tracked = {}
    monkeypatch.setattr(
        "api.v1.viewsets.broadcast_stream_event",
        lambda alvo_tipo, alvo_id, event, payload: tracked.setdefault("events", []).append((event, payload)),
    )

    client = APIClient()
    client.force_authenticate(articulador)
    payload = {
        "alvo_tipo": "resposta",
        "alvo_id": resposta.id,
        "status": "rascunho",
        "revisor": usuario.id,
    }
    resp = client.post("/api/v1/revisoes", payload, format="json")
    assert resp.status_code == 201
    revisao_id = resp.json()["id"]
    etag = resp["ETag"]

    resp_put = client.put(
        f"/api/v1/revisoes/{revisao_id}",
        {"status": "aprovado"},
        format="json",
        HTTP_IF_MATCH=etag,
    )
    assert resp_put.status_code == 200
    assert resp_put.json()["status"] == "aprovado"

    notif_users = set(Notificacao.objects.values_list("usuario_id", flat=True))
    assert usuario.id in notif_users
    assert articulador.id in notif_users
    assert any(event == "review:status_changed" for event, _ in tracked.get("events", []))


@pytest.mark.django_db
def test_comentario_resolve(monkeypatch, cliente, membro_gt, articulador, usuario, gt, pergunta):
    gt.membros.add(membro_gt)
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Conteúdo</p>",
        autor=usuario,
    )
    events = []
    monkeypatch.setattr(
        "api.v1.viewsets.broadcast_stream_event",
        lambda alvo_tipo, alvo_id, event, payload: events.append(event),
    )

    client_member = APIClient()
    client_member.force_authenticate(membro_gt)
    create_resp = client_member.post(
        "/api/v1/comentarios",
        {
            "alvo_tipo": "resposta",
            "alvo_id": resposta.id,
            "anchor_json": {"start": 0},
            "conteudo_html": "<p>Comentário</p>",
            "mentions": [usuario.id],
        },
        format="json",
    )
    assert create_resp.status_code == 201, create_resp.json()
    comentario_id = create_resp.json()["id"]
    assert create_resp["ETag"]
    comentario = Comentario.objects.get(pk=comentario_id)
    assert comentario.mentions.filter(pk=usuario.id).exists()
    assert Notificacao.objects.filter(usuario=usuario, tipo="comentario.mention").exists()

    client_art = APIClient()
    client_art.force_authenticate(articulador)
    resolve_resp = client_art.put(
        f"/api/v1/comentarios/{comentario_id}",
        {"resolvido": True},
        format="json",
        HTTP_IF_MATCH=create_resp["ETag"],
    )
    assert resolve_resp.status_code == 200
    comentario.refresh_from_db()
    assert comentario.resolvido is True
    assert comentario.resolvido_por_id == articulador.id
    assert "comment:resolved" in events


@pytest.mark.django_db
def test_diff_endpoint(auth_client, cliente, gt, tarefa, pergunta, usuario):
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Primeira</p>",
        autor=usuario,
    )
    resposta.conteudo_html = "<p>Segunda versão</p>"
    resposta.save()

    resp = auth_client.get(
        "/api/v1/diff",
        {
            "alvo_tipo": "resposta",
            "alvo_id": resposta.id,
            "from": 1,
            "to": 2,
        },
    )
    assert resp.status_code == 200
    assert "<ins>" in resp.json()["html"] or "<del>" in resp.json()["html"]


@pytest.mark.django_db
def test_notificacoes_api(auth_client, cliente, usuario):
    notificacao = criar_notificacao(
        cliente_id=cliente.id,
        usuario_id=usuario.id,
        tipo="teste",
        payload={"foo": "bar"},
    )
    resp = auth_client.get("/api/v1/notificacoes")
    assert resp.status_code == 200
    assert resp.json()["results"][0]["id"] == notificacao.id

    mark = auth_client.put(f"/api/v1/notificacoes/{notificacao.id}/lida")
    assert mark.status_code == 200
    notificacao.refresh_from_db()
    assert notificacao.lida is True

    ClienteFeatureFlag.objects.filter(cliente=cliente, flag="ff.notifications.enabled").update(ativo=False)
    forbidden = auth_client.get("/api/v1/notificacoes")
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_library_crud(auth_client, articulador):
    client = auth_client

    articulador_client = APIClient()
    articulador_client.force_authenticate(articulador)
    forbidden_media = articulador_client.post(
        "/api/v1/midias",
        {"url": "https://cdn.test/media.png", "legenda": "Logo", "tags": ["logo"]},
        format="json",
    )
    assert forbidden_media.status_code == 403

    media_resp = client.post(
        "/api/v1/midias",
        {"url": "https://cdn.test/media.png", "legenda": "Logo", "tags": ["logo"]},
        format="json",
    )
    assert media_resp.status_code == 201
    midia_id = media_resp.json()["id"]

    bloco_resp = client.post(
        "/api/v1/blocos",
        {"titulo": "Introdução", "conteudo_html": "<p>Texto</p>", "tags": ["intro"]},
        format="json",
    )
    assert bloco_resp.status_code == 201
    bloco_id = bloco_resp.json()["id"]
    etag = bloco_resp["ETag"]

    lista_midias = client.get("/api/v1/midias", {"tags": "logo"})
    assert lista_midias.status_code == 200
    assert lista_midias.json()["count"] == 1

    update_bloco = client.put(
        f"/api/v1/blocos/{bloco_id}",
        {"titulo": "Introdução atualizada", "conteudo_html": "<p>Novo</p>", "tags": ["intro", "revisado"]},
        format="json",
        HTTP_IF_MATCH=etag,
    )
    assert update_bloco.status_code == 200
    assert update_bloco["ETag"]
    delete_resp = client.delete(f"/api/v1/blocos/{bloco_id}")
    assert delete_resp.status_code == 204
    assert BlocoTexto.objects.filter(pk=bloco_id, is_deleted=True).exists()


@pytest.mark.django_db
def test_feature_flag_blocks_comments(auth_client, cliente, membro_gt, gt, pergunta, usuario):
    ClienteFeatureFlag.objects.filter(cliente=cliente, flag="ff.comments.enabled").update(ativo=False)
    client_member = APIClient()
    client_member.force_authenticate(membro_gt)
    gt.membros.add(membro_gt)
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>Texto</p>",
        autor=usuario,
    )
    resp = client_member.post(
        "/api/v1/comentarios",
        {"alvo_tipo": "resposta", "alvo_id": resposta.id, "conteudo_html": "<p>Oi</p>"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_send_email_notification(monkeypatch, cliente, usuario):
    notificacao = Notificacao.objects.create(
        cliente=cliente,
        usuario=usuario,
        tipo="teste",
        payload_json={"foo": "bar"},
    )
    sent = {}

    def fake_send_mail(subject, body, from_email, recipients, fail_silently=False):
        sent["subject"] = subject
        sent["body"] = body
        return 1

    monkeypatch.setattr("tasks.notifications.send_mail", fake_send_mail)
    send_email_notification(notificacao.id)
    assert "subject" in sent


@pytest.mark.django_db
def test_render_and_cache_diff(cliente, gt, tarefa, pergunta, usuario):
    resposta = Resposta.objects.create(
        cliente=cliente,
        gt=gt,
        pergunta=pergunta,
        conteudo_html="<p>antes</p>",
        autor=usuario,
    )
    resposta.conteudo_html = "<p>depois</p>"
    resposta.save()
    cache.clear()
    html = render_and_cache_diff("resposta", resposta.id, 1, 2)
    assert "depois" in html
    cached = render_and_cache_diff("resposta", resposta.id, 1, 2)
    assert cached == html
