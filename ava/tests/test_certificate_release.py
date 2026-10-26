"""Liberação de certificados pelo admin e download pelo painel do cursista."""

import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ava.models import Certificado, ConfigCertificado, Curso, MatriculaCurso
from ava.services.certificate_service import CertificacaoService
from core.models import Cliente
from curriculum.models import Escola


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    MEDIA_ROOT=tempfile.mkdtemp(prefix="certificados-liberacao-"),
)
class CertificateReleaseTests(TestCase):
    def setUp(self):
        self.tenant = Cliente.objects.create(nome="Rede", slug="rede-liberacao")
        escola = Escola.objects.create(cliente=self.tenant, nome="Escola Municipal")
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            email="coordenacao@liberacao.test",
            nome="Coordenação",
            password="test123",
            cliente=self.tenant,
            role=user_model.Role.ADMIN_CLIENTE,
            is_staff=True,
        )
        self.student = user_model.objects.create_user(
            email="cursista@liberacao.test",
            nome="Cursista Teste",
            password="test123",
            cliente=self.tenant,
            role=user_model.Role.PROFESSOR,
            escola=escola,
        )
        self.course = Curso.objects.create(
            cliente=self.tenant,
            titulo="Formação continuada",
            slug="formacao-continuada-liberacao",
            carga_horaria=40,
            frequencia_minima=0,
        )
        self.enrollment = MatriculaCurso.objects.create(
            cliente=self.tenant,
            curso=self.course,
            aluno=self.student,
            status=MatriculaCurso.Status.CONCLUIDA,
            progresso_percentual=100,
            nota_final_obtida=90,
        )
        self.config = ConfigCertificado.objects.create(cliente=self.tenant, curso=self.course)

    def criar_certificado(self, *, com_pdf=True, liberado_em=None, matricula=None):
        certificado = Certificado.objects.create(
            cliente=self.tenant,
            matricula_curso=matricula if matricula is not None else self.enrollment,
            config=self.config,
            aluno=self.student,
            liberado_em=liberado_em,
            dados_impressos={"aluno_nome": "Cursista Teste", "curso_nome": self.course.titulo},
        )
        if com_pdf:
            certificado.arquivo_pdf.save("certificado.pdf", ContentFile(b"%PDF-1.4 fake"), save=True)
        return certificado

    # ----------------------------------------------------------------- serviço
    def test_liberar_em_lote_libera_somente_quem_tem_pdf(self):
        com_pdf = self.criar_certificado()
        outra_matricula = MatriculaCurso.objects.create(
            cliente=self.tenant,
            curso=self.course,
            aluno=self.admin,
            status=MatriculaCurso.Status.CONCLUIDA,
            progresso_percentual=100,
            nota_final_obtida=100,
        )
        sem_pdf = Certificado.objects.create(
            cliente=self.tenant,
            matricula_curso=outra_matricula,
            config=self.config,
            aluno=self.admin,
        )

        with patch("tasks.certificates.build_certificate_pdf.delay") as fila:
            resultado = CertificacaoService.liberar_em_lote(Certificado.objects.all())

        self.assertEqual(resultado.liberados, 1)
        self.assertEqual(resultado.sem_pdf, 1)
        self.assertEqual(resultado.pdf_enfileirados, 1)
        fila.assert_called_once_with(sem_pdf.pk, None)

        com_pdf.refresh_from_db()
        sem_pdf.refresh_from_db()
        self.assertIsNotNone(com_pdf.liberado_em)
        self.assertIsNone(sem_pdf.liberado_em)

    def test_liberacao_programada_nao_fica_disponivel_antes_da_data(self):
        futuro = timezone.now() + timedelta(days=1)
        certificado = self.criar_certificado()
        CertificacaoService.liberar_em_lote(Certificado.objects.all(), quando=futuro)

        certificado.refresh_from_db()
        self.assertFalse(CertificacaoService.esta_liberado(certificado))
        self.assertFalse(CertificacaoService.disponivel_para_download(certificado))

    def test_revogar_em_lote_oculta_o_certificado(self):
        certificado = self.criar_certificado(liberado_em=timezone.now())
        self.assertEqual(CertificacaoService.revogar_em_lote(Certificado.objects.all()), 1)
        certificado.refresh_from_db()
        self.assertIsNone(certificado.liberado_em)

    def test_certificado_sem_pdf_nunca_entra_na_lista_do_aluno(self):
        self.criar_certificado(com_pdf=False, liberado_em=timezone.now())
        self.assertEqual(CertificacaoService.certificados_do_aluno(self.student).count(), 0)

    # ------------------------------------------------------------------- admin
    def test_changelist_mostra_situacao_atalhos_e_filtros(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:ava_certificado_changelist"))

        self.assertContains(response, "Liberar todos para os cursistas")
        self.assertContains(response, "Não liberado")
        self.assertContains(response, "Situação da liberação")
        self.assertContains(response, f"?ids={certificado.pk}")

        liberados = self.client.get(
            reverse("admin:ava_certificado_changelist"), {"situacao_liberacao": "liberado"}
        )
        self.assertEqual(liberados.context["cl"].result_count, 0)

        sem_pdf = self.client.get(reverse("admin:ava_certificado_changelist"), {"pdf": "nao"})
        self.assertEqual(sem_pdf.context["cl"].result_count, 0)

    def test_admin_libera_um_certificado_pela_tela_de_confirmacao(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.admin)
        url = reverse("admin:ava_certificado_liberar")

        self.assertContains(self.client.get(url, {"ids": certificado.pk}), "Liberar 1 certificado(s)")

        response = self.client.post(
            url,
            {"ids": str(certificado.pk), "acao": "liberar", "liberar_agora": "on", "confirmar": "1"},
        )
        self.assertRedirects(response, reverse("admin:ava_certificado_changelist"))
        certificado.refresh_from_db()
        self.assertTrue(CertificacaoService.esta_liberado(certificado))

    def test_admin_libera_todos_de_uma_vez(self):
        primeiro = self.criar_certificado()
        outra_matricula = MatriculaCurso.objects.create(
            cliente=self.tenant,
            curso=self.course,
            aluno=self.admin,
            status=MatriculaCurso.Status.CONCLUIDA,
            progresso_percentual=100,
            nota_final_obtida=100,
        )
        segundo = self.criar_certificado(matricula=outra_matricula)
        segundo.aluno = self.admin
        segundo.save(update_fields=["aluno"])

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:ava_certificado_liberar"),
            {"escopo": "todos", "acao": "liberar", "liberar_agora": "on", "confirmar": "1"},
        )
        self.assertRedirects(response, reverse("admin:ava_certificado_changelist"))
        for certificado in (primeiro, segundo):
            certificado.refresh_from_db()
            self.assertTrue(CertificacaoService.esta_liberado(certificado))

    def test_admin_action_de_liberacao_em_massa(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:ava_certificado_changelist"),
            {"action": "liberar_para_cursistas", "_selected_action": [str(certificado.pk)]},
        )
        self.assertEqual(response.status_code, 302)
        certificado.refresh_from_db()
        self.assertTrue(CertificacaoService.esta_liberado(certificado))

    def test_admin_action_de_revogacao_em_massa(self):
        certificado = self.criar_certificado(liberado_em=timezone.now())
        self.client.force_login(self.admin)
        self.client.post(
            reverse("admin:ava_certificado_changelist"),
            {"action": "revogar_liberacao", "_selected_action": [str(certificado.pk)]},
        )
        certificado.refresh_from_db()
        self.assertIsNone(certificado.liberado_em)

    def test_action_programar_leva_para_a_tela_sem_estourar_a_querystring(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:ava_certificado_changelist"),
            {"action": "programar_liberacao", "_selected_action": [str(certificado.pk)]},
        )
        destino = reverse("admin:ava_certificado_liberar")
        self.assertRedirects(response, f"{destino}?escopo=sessao")
        self.assertEqual(
            self.client.session["ava_certificado_liberacao_ids"], [certificado.pk]
        )
        self.assertContains(self.client.get(f"{destino}?escopo=sessao"), certificado.codigo_validacao)

    def test_liberacao_exige_data_quando_nao_for_imediata(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:ava_certificado_liberar"),
            {"ids": str(certificado.pk), "acao": "liberar", "confirmar": "1"},
        )
        self.assertEqual(response.status_code, 200)
        certificado.refresh_from_db()
        self.assertIsNone(certificado.liberado_em)

    def test_cursista_nao_acessa_a_tela_de_liberacao(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("admin:ava_certificado_liberar"), {"escopo": "todos"})
        self.assertIn(response.status_code, {302, 403})

    # ---------------------------------------------------------- painel do aluno
    def test_painel_do_cursista_mostra_download_somente_apos_liberacao(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.student)
        url = reverse("ava:aluno_dashboard")

        resposta_bloqueada = self.client.get(url)
        self.assertNotContains(resposta_bloqueada, "Baixar certificado")
        self.assertContains(resposta_bloqueada, "aguardando liberação")

        CertificacaoService.liberar_em_lote(Certificado.objects.filter(pk=certificado.pk))

        resposta_liberada = self.client.get(url)
        self.assertContains(resposta_liberada, "Baixar certificado")
        self.assertContains(
            resposta_liberada,
            reverse("ava:aluno_baixar_certificado", args=[certificado.pk]),
        )

    def test_download_bloqueado_antes_da_liberacao_e_liberado_depois(self):
        certificado = self.criar_certificado()
        self.client.force_login(self.student)
        url = reverse("ava:aluno_baixar_certificado", args=[certificado.pk])

        self.assertEqual(self.client.get(url).status_code, 404)

        CertificacaoService.liberar_em_lote(Certificado.objects.filter(pk=certificado.pk))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 fake")

    def test_download_bloqueado_depois_de_revogar(self):
        certificado = self.criar_certificado(liberado_em=timezone.now())
        self.client.force_login(self.student)
        url = reverse("ava:aluno_baixar_certificado", args=[certificado.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

        CertificacaoService.revogar_em_lote(Certificado.objects.all())
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cursista_nao_baixa_certificado_de_outra_pessoa(self):
        certificado = self.criar_certificado(liberado_em=timezone.now())
        self.client.force_login(self.admin)
        response = self.client.get(reverse("ava:aluno_baixar_certificado", args=[certificado.pk]))
        self.assertEqual(response.status_code, 404)
