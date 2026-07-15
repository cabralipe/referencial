import pytest

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
