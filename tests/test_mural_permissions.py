import pytest
import errno
from django.core.files.uploadedfile import SimpleUploadedFile

from curriculum.models import GT
from notifications.models import MuralArquivoEnvio


@pytest.mark.django_db
def test_redator_can_create_mural(api_client, articulador, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    api_client.force_authenticate(articulador)
    response = api_client.post(
        "/api/v1/mural",
        {"titulo": "Aviso", "conteudo_html": "<p>Conteúdo</p>"},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["titulo"] == "Aviso"


@pytest.mark.django_db
def test_redator_can_create_mural_com_anexo_e_modalidade_recebimento(api_client, articulador, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    api_client.force_authenticate(articulador)
    arquivo = SimpleUploadedFile("roteiro.pdf", b"%PDF-1.4", content_type="application/pdf")

    response = api_client.post(
        "/api/v1/mural",
        {
            "titulo": "Entrega de evidências",
            "conteudo_html": "<p>Envie o documento final.</p>",
            "modalidade": "recebimento_arquivo",
            "anexos_uploads": arquivo,
        },
        format="multipart",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["modalidade"] == "recebimento_arquivo"
    assert len(body["anexos"]) == 1
    assert body["anexos"][0]["titulo"] == "roteiro.pdf"


@pytest.mark.django_db
def test_membro_gt_cannot_create_mural(api_client, membro_gt):
    api_client.force_authenticate(membro_gt)
    response = api_client.post(
        "/api/v1/mural",
        {"titulo": "Aviso", "conteudo_html": "<p>Conteúdo</p>"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_membro_gt_envia_arquivo_em_post_de_recebimento(api_client, usuario, membro_gt, cliente, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    gt = GT.objects.create(cliente=cliente, nome="GT Alfabetização", etapa="I")
    gt.membros.add(membro_gt)

    api_client.force_authenticate(usuario)
    create_response = api_client.post(
        "/api/v1/mural",
        {
            "titulo": "Entrega de ata",
            "conteudo_html": "<p>Envie a ata consolidada.</p>",
            "modalidade": "recebimento_arquivo",
            "gt_ids": [gt.id],
            "include_all": False,
        },
        format="json",
    )
    assert create_response.status_code == 201
    mural_id = create_response.json()["id"]

    api_client.force_authenticate(membro_gt)
    arquivo = SimpleUploadedFile("ata-final.pdf", b"%PDF-1.4", content_type="application/pdf")
    send_response = api_client.post(
        f"/api/v1/mural/{mural_id}/envios",
        {
            "gt_id": str(gt.id),
            "arquivo": arquivo,
        },
        format="multipart",
    )

    assert send_response.status_code == 201
    envio = send_response.json()
    assert envio["gt_id"] == gt.id
    assert envio["nome_arquivo"] == "ata-final.pdf"

    list_response = api_client.get("/api/v1/mural")
    assert list_response.status_code == 200
    mural = list_response.json()[0]
    assert mural["modalidade"] == "recebimento_arquivo"
    assert len(mural["envios_arquivo"]) == 1
    assert mural["envios_arquivo"][0]["nome_arquivo"] == "ata-final.pdf"

    api_client.force_authenticate(usuario)
    admin_list_response = api_client.get("/api/v1/mural")
    assert admin_list_response.status_code == 200
    admin_mural = admin_list_response.json()[0]
    assert len(admin_mural["envios_arquivo"]) == 1
    assert admin_mural["envios_arquivo"][0]["usuario_nome"] == membro_gt.nome


@pytest.mark.django_db
def test_membro_gt_nao_envia_arquivo_quando_post_nao_permite(api_client, usuario, membro_gt, cliente, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    gt = GT.objects.create(cliente=cliente, nome="GT Ciências", etapa="II")
    gt.membros.add(membro_gt)

    api_client.force_authenticate(usuario)
    create_response = api_client.post(
        "/api/v1/mural",
        {
            "titulo": "Aviso simples",
            "conteudo_html": "<p>Sem recebimento.</p>",
            "gt_ids": [gt.id],
            "include_all": False,
        },
        format="json",
    )
    mural_id = create_response.json()["id"]

    api_client.force_authenticate(membro_gt)
    arquivo = SimpleUploadedFile("teste.pdf", b"%PDF-1.4", content_type="application/pdf")
    send_response = api_client.post(
        f"/api/v1/mural/{mural_id}/envios",
        {"gt_id": str(gt.id), "arquivo": arquivo},
        format="multipart",
    )

    assert send_response.status_code == 400


@pytest.mark.django_db
def test_membro_gt_recebe_507_quando_storage_sem_espaco(
    api_client,
    usuario,
    membro_gt,
    cliente,
    settings,
    tmp_path,
    monkeypatch,
):
    settings.MEDIA_ROOT = tmp_path
    gt = GT.objects.create(cliente=cliente, nome="GT Matemática", etapa="II")
    gt.membros.add(membro_gt)

    api_client.force_authenticate(usuario)
    create_response = api_client.post(
        "/api/v1/mural",
        {
            "titulo": "Entrega de evidências",
            "conteudo_html": "<p>Envie o arquivo.</p>",
            "modalidade": "recebimento_arquivo",
            "gt_ids": [gt.id],
            "include_all": False,
        },
        format="json",
    )
    mural_id = create_response.json()["id"]

    def fail_save(self, *args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(MuralArquivoEnvio, "save", fail_save)

    api_client.force_authenticate(membro_gt)
    arquivo = SimpleUploadedFile("evidencia.pdf", b"%PDF-1.4", content_type="application/pdf")
    send_response = api_client.post(
        f"/api/v1/mural/{mural_id}/envios",
        {"gt_id": str(gt.id), "arquivo": arquivo},
        format="multipart",
    )

    assert send_response.status_code == 507
    assert "espaço" in str(send_response.data["arquivo"])
