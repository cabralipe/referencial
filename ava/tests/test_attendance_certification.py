from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ava.models import (
    Certificado,
    ConfigCertificado,
    Curso,
    EncontroCurso,
    MatriculaCurso,
    PresencaCurso,
)
from ava.services.attendance_service import registrar_presenca, resumo_frequencia
from ava.services.certificate_service import CertificacaoService
from core.models import Cliente
from curriculum.models import Escola


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AttendanceCertificationTests(TestCase):
    def setUp(self):
        self.tenant = Cliente.objects.create(
            nome="Formação", slug="formacao-frequencia"
        )
        escola = Escola.objects.create(cliente=self.tenant, nome="Escola de formação")
        user_model = get_user_model()
        self.manager = user_model.objects.create_user(
            email="gestor@frequencia.test",
            nome="Gestor",
            password="test123",
            cliente=self.tenant,
            role=user_model.Role.ADMIN_CLIENTE,
        )
        self.student = user_model.objects.create_user(
            email="aluno@frequencia.test",
            nome="Cursista",
            password="test123",
            cliente=self.tenant,
            role=user_model.Role.PROFESSOR,
            escola=escola,
        )
        self.course = Curso.objects.create(
            cliente=self.tenant, titulo="Formação", slug="formacao-frequencia"
        )
        self.enrollment = MatriculaCurso.objects.create(
            cliente=self.tenant,
            curso=self.course,
            aluno=self.student,
            status="concluida",
            progresso_percentual=100,
            nota_final_obtida=90,
        )
        self.config = ConfigCertificado.objects.create(
            cliente=self.tenant, curso=self.course
        )
        self.meetings = [
            EncontroCurso.objects.create(
                cliente=self.tenant,
                curso=self.course,
                titulo=f"Encontro {i}",
                data_aula=timezone.localdate(),
                realizado=True,
                link_aberto=True,
                link_expira_em=timezone.now() + timedelta(hours=2),
            )
            for i in range(4)
        ]

    def mark(self, count):
        for meeting in self.meetings[:count]:
            registrar_presenca(
                meeting,
                self.enrollment,
                self.manager,
                presente=True,
                origem="checklist",
            )

    def test_login_on_meeting_link_preserves_meeting_without_marking_presence(self):
        url = reverse("ava:confirmar_presenca", args=[self.meetings[0].token])
        self.assertContains(self.client.get(url), "Entrar e continuar")
        self.assertEqual(
            self.client.post(
                url, {"username": self.student.email, "password": "incorreta"}
            ).status_code,
            200,
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(
            url, {"username": self.student.email, "password": "test123"}
        )
        self.assertRedirects(response, url)
        self.assertFalse(PresencaCurso.objects.exists())
        self.assertContains(self.client.get(url), "Confirmar minha presença")

    def test_exact_minimum_and_below_minimum(self):
        self.mark(2)
        self.assertEqual(resumo_frequencia(self.enrollment)["percentual"], 50)
        self.assertFalse(
            CertificacaoService.avaliar_matricula(self.enrollment).approved
        )
        self.mark(3)
        self.assertEqual(resumo_frequencia(self.enrollment)["percentual"], 75)
        cert, created, eligibility = CertificacaoService.emitir_para_matricula(
            self.enrollment,
            self.config,
            gerar_pdf=False,
        )
        self.assertTrue(eligibility.approved)
        self.assertTrue(created)
        self.assertIsNotNone(cert)

    def test_legacy_override_cannot_emit_for_pending_student(self):
        cert, created, eligibility = CertificacaoService.emitir_para_matricula(
            self.enrollment,
            self.config,
            aprovar_pendente=True,
            gerar_pdf=False,
        )
        self.assertIsNone(cert)
        self.assertFalse(created)
        self.assertFalse(eligibility.approved)
        self.assertFalse(Certificado.objects.exists())

    def test_planned_and_deleted_meetings_do_not_enter_denominator(self):
        self.mark(2)
        self.meetings[2].realizado = False
        self.meetings[2].save()
        self.meetings[3].delete()
        self.assertEqual(resumo_frequencia(self.enrollment)["percentual"], 100)

    def test_no_meetings_blocks_required_attendance_and_zero_waives_it(self):
        EncontroCurso.objects.update(realizado=False)
        self.assertFalse(
            CertificacaoService.avaliar_matricula(self.enrollment).approved
        )
        self.course.frequencia_minima = 0
        self.course.save()
        self.assertTrue(CertificacaoService.avaliar_matricula(self.enrollment).approved)

    def test_all_other_certificate_requirements_still_apply(self):
        self.mark(4)
        for field, value in [
            ("progresso_percentual", 10),
            ("nota_final_obtida", 0),
            ("status", "suspensa"),
        ]:
            old = getattr(self.enrollment, field)
            setattr(self.enrollment, field, value)
            self.assertFalse(
                CertificacaoService.avaliar_matricula(self.enrollment).approved
            )
            setattr(self.enrollment, field, old)
        self.course.permite_certificado = False
        self.assertFalse(
            CertificacaoService.avaliar_matricula(self.enrollment).approved
        )

    def test_link_get_does_not_mark_and_post_is_idempotent(self):
        self.client.force_login(self.student)
        url = reverse("ava:confirmar_presenca", args=[self.meetings[0].token])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(PresencaCurso.objects.exists())
        for _ in range(2):
            self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(
            PresencaCurso.objects.filter(presente=True, origem="link").count(), 1
        )

    def test_link_expired_closed_and_suspended_enrollment(self):
        self.client.force_login(self.student)
        meeting = self.meetings[0]
        url = reverse("ava:confirmar_presenca", args=[meeting.token])
        meeting.link_expira_em = timezone.now() - timedelta(minutes=1)
        meeting.save()
        self.client.post(url)
        self.assertFalse(PresencaCurso.objects.exists())
        meeting.link_expira_em = timezone.now() + timedelta(hours=1)
        meeting.link_aberto = False
        meeting.save()
        self.client.post(url)
        self.assertFalse(PresencaCurso.objects.exists())
        self.enrollment.status = "suspensa"
        self.enrollment.save()
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_checklist_renders_roster_saves_date_and_can_remove_presence(self):
        self.client.force_login(self.manager)
        meeting = self.meetings[0]
        url = reverse("ava:frequencia_checklist", args=[meeting.pk])
        self.assertContains(self.client.get(url), self.student.email)
        payload = {
            "titulo": "Reunião atualizada",
            "data_aula": "2026-01-01",
            "realizado": "on",
            "presentes": [self.enrollment.pk],
        }
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        meeting.refresh_from_db()
        self.assertEqual(meeting.data_aula.isoformat(), "2026-01-01")
        self.assertTrue(PresencaCurso.objects.get().presente)
        payload.pop("presentes")
        self.client.post(url, payload)
        self.assertFalse(PresencaCurso.objects.get().presente)
        self.assertContains(
            self.client.get(reverse("ava:frequencia_lista")),
            "Acompanhamento da frequência",
        )

    def test_unassigned_teacher_and_foreign_manager_cannot_edit(self):
        url = reverse("ava:frequencia_checklist", args=[self.meetings[0].pk])
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(url).status_code, 404)
        other = Cliente.objects.create(nome="Outro", slug="outro-frequencia")
        foreign = get_user_model().objects.create_user(
            email="outro@frequencia.test",
            nome="Outro gestor",
            password="test123",
            cliente=other,
            role=get_user_model().Role.ADMIN_CLIENTE,
        )
        self.client.force_login(foreign)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.post(
                reverse("ava:confirmar_presenca", args=[self.meetings[0].token])
            ).status_code,
            404,
        )

    def test_invalid_member_does_not_partially_save_checklist(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("ava:frequencia_checklist", args=[self.meetings[0].pk]),
            {
                "titulo": "Alterado indevidamente",
                "data_aula": "2026-01-01",
                "presentes": [999999],
            },
        )
        self.assertEqual(response.status_code, 400)
        self.meetings[0].refresh_from_db()
        self.assertEqual(self.meetings[0].titulo, "Encontro 0")
        self.assertFalse(PresencaCurso.objects.exists())

    def test_batch_emits_only_eligible_and_ignores_legacy_override(self):
        self.mark(3)
        other_student = get_user_model().objects.create_user(
            email="pendente@frequencia.test",
            nome="Pendente",
            cliente=self.tenant,
        )
        pending = MatriculaCurso.objects.create(
            cliente=self.tenant,
            curso=self.course,
            aluno=other_student,
            status="concluida",
            progresso_percentual=100,
            nota_final_obtida=90,
        )
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from ava.admin import CertificadoAdmin

        request = RequestFactory().post("/", {"confirmar": "1"})
        request.user = self.manager
        form = type(
            "Form",
            (),
            {
                "is_valid": lambda self: True,
                "cleaned_data": {
                    "config": self.config,
                    "liberar_agora": True,
                    "aprovar_pendentes": True,
                },
            },
        )()
        with (
            patch("ava.admin.CertificadoBatchEmitForm", return_value=form),
            patch(
                "ava.admin._candidate_queryset_from_form",
                return_value=[self.enrollment, pending],
            ),
            patch("ava.admin.messages.success"),
            patch("ava.admin.build_certificate_pdf.delay"),
        ):
            response = CertificadoAdmin(Certificado, AdminSite()).emitir_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(Certificado.objects.values_list("matricula_curso_id", flat=True)),
            [self.enrollment.pk],
        )
