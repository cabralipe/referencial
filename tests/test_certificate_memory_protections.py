import io
import zipfile

import pytest
from django.contrib.admin.sites import AdminSite
from django.core.files.base import ContentFile
from django.test import RequestFactory

from ava.admin import CertificadoAdmin, ConfigCertificadoAdminForm
from ava.models import Certificado, ConfigCertificado, Curso, MatriculaCurso
from ava.services.certificate_service import CertificacaoService
from tasks.certificates import build_certificate_pdf


@pytest.fixture
def certificate_context(cliente, usuario):
    curso = Curso.objects.create(
        cliente=cliente,
        titulo="Curso com certificado",
        slug="curso-com-certificado",
        status=Curso.Status.PUBLICADO,
        carga_horaria=20,
        autor_principal=usuario,
    )
    matricula = MatriculaCurso.objects.create(
        cliente=cliente,
        curso=curso,
        aluno=usuario,
        status=MatriculaCurso.Status.CONCLUIDA,
        progresso_percentual=100,
        nota_final_obtida=90,
        matriculado_por=usuario,
    )
    config = ConfigCertificado.objects.create(cliente=cliente, curso=curso)
    return matricula, config


@pytest.mark.django_db
def test_certificate_can_be_prepared_without_rendering_pdf(certificate_context, monkeypatch):
    matricula, config = certificate_context

    def fail_if_called(*args, **kwargs):
        pytest.fail("PDF nao deve ser gerado no processo web")

    monkeypatch.setattr(CertificacaoService, "gerar_pdf", fail_if_called)

    certificado, created, elegibilidade = CertificacaoService.emitir_para_matricula(
        matricula,
        config,
        gerar_pdf=False,
    )

    assert created is True
    assert elegibilidade.approved is True
    assert not certificado.arquivo_pdf


@pytest.mark.django_db
def test_certificate_task_generates_and_persists_pdf(certificate_context, monkeypatch):
    matricula, config = certificate_context
    certificado = Certificado.objects.create(
        cliente=matricula.cliente,
        matricula_curso=matricula,
        config=config,
        aluno=matricula.aluno,
    )
    received = {}

    def fake_generate(certificado_obj, config_obj, campos=None):
        received["certificado_id"] = certificado_obj.pk
        received["config_id"] = config_obj.pk
        received["campos"] = campos
        certificado_obj.arquivo_pdf.name = "ava/certificados/pdfs/protegido.pdf"

    monkeypatch.setattr(CertificacaoService, "gerar_pdf", fake_generate)

    build_certificate_pdf(certificado.pk, ["aluno_nome", "curso_nome"])
    certificado.refresh_from_db()

    assert received == {
        "certificado_id": certificado.pk,
        "config_id": config.pk,
        "campos": ["aluno_nome", "curso_nome"],
    }
    assert certificado.arquivo_pdf.name == "ava/certificados/pdfs/protegido.pdf"


@pytest.mark.django_db
def test_certificate_renders_optional_back_page(certificate_context):
    matricula, config = certificate_context
    config.verso_ativo = True
    config.verso_titulo = "Conteudo de {{curso_nome}}"
    config.verso_template_html = "<p>Cursista: {{aluno_nome}}</p>"

    html = CertificacaoService.renderizar_html(None, matricula, config)

    assert html.count('class="certificate ') == 2
    assert 'class="certificate certificate-back' in html
    assert "Conteudo de Curso com certificado" in html
    assert "Cursista: Admin Teste" in html


@pytest.mark.django_db
def test_certificate_does_not_render_back_page_by_default(certificate_context):
    matricula, config = certificate_context

    html = CertificacaoService.renderizar_html(None, matricula, config)

    assert html.count('class="certificate ') == 1
    assert "certificate-back" not in html


@pytest.mark.django_db
def test_certificate_admin_form_exposes_variable_picker(certificate_context):
    _, config = certificate_context

    form = ConfigCertificadoAdminForm(instance=config)

    for field_name in ("titulo", "subtitulo", "template_html", "verso_titulo", "verso_template_html"):
        attrs = form.fields[field_name].widget.attrs
        assert attrs["data-certificate-variable-picker"] == "1"
        assert '["aluno_nome", "Nome do cursista"]' in attrs["data-certificate-variables"]
    assert "ava/admin/certificate_variables.js" in str(form.media)


@pytest.mark.django_db
def test_batch_emission_does_not_return_500_when_queue_is_unavailable(
    certificate_context,
    usuario,
    client,
    monkeypatch,
):
    matricula, config = certificate_context
    usuario.is_staff = True
    usuario.save(update_fields=["is_staff"])
    client.force_login(usuario)

    def unavailable_queue(*args, **kwargs):
        raise ConnectionError("Redis indisponivel")

    monkeypatch.setattr("ava.admin.build_certificate_pdf.delay", unavailable_queue)

    response = client.post(
        "/admin/ava/certificado/emitir/",
        {
            "config": config.pk,
            "campos_variaveis": ["aluno_nome", "curso_nome"],
            "liberar_agora": "on",
            "confirmar": "1",
        },
    )

    assert response.status_code == 302
    certificado = Certificado.objects.get(matricula_curso=matricula)
    assert not certificado.arquivo_pdf


@pytest.mark.django_db
def test_admin_downloads_generated_certificates_with_student_name(certificate_context, usuario, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    matricula, config = certificate_context
    certificado = Certificado.objects.create(
        cliente=matricula.cliente,
        matricula_curso=matricula,
        config=config,
        aluno=matricula.aluno,
        dados_impressos={"aluno_nome": "Admin Teste", "curso_nome": "Curso com certificado"},
    )
    certificado.arquivo_pdf.save("certificado.pdf", ContentFile(b"pdf-do-certificado"))
    request = RequestFactory().get("/admin/ava/certificado/baixar-todos/")
    request.user = usuario
    model_admin = CertificadoAdmin(Certificado, AdminSite())

    response = model_admin._resposta_zip(
        request,
        Certificado.objects.filter(pk=certificado.pk),
        nome_arquivo="todos-os-certificados.zip",
    )
    payload = b"".join(response.streaming_content)

    with zipfile.ZipFile(io.BytesIO(payload)) as arquivo_zip:
        assert arquivo_zip.namelist() == ["admin-teste-curso-com-certificado.pdf"]
        assert arquivo_zip.read(arquivo_zip.namelist()[0]) == b"pdf-do-certificado"
