from datetime import datetime, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ava.models import EncontroCurso, PresencaCurso
from ava.tests.test_diario_retroativo import PresencaRetroativaBaseTests
from ava.views.attendance import EncontroForm


@override_settings(TIME_ZONE="America/Maceio")
class ExpirationFormTests(SimpleTestCase):
    def payload(self, **changes):
        data = {
            "titulo": "Reunião", "data_aula": "2026-01-01", "link_aberto": "on",
            "link_expira_em_0": "2099-01-01", "link_expira_em_1": "14:35",
        }
        data.update(changes)
        return data

    def test_date_and_time_are_combined_in_local_timezone(self):
        form = EncontroForm(self.payload())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["link_expira_em"], timezone.make_aware(datetime(2099, 1, 1, 14, 35)))

    def test_open_link_requires_both_date_and_time(self):
        for field in ("link_expira_em_0", "link_expira_em_1"):
            with self.subTest(field=field):
                form = EncontroForm(self.payload(**{field: ""}))
                self.assertFalse(form.is_valid())
                self.assertIn("link_expira_em", form.errors)

    def test_past_hour_today_is_rejected(self):
        now = timezone.make_aware(datetime(2026, 11, 16, 15, 0))
        with patch("ava.views.attendance.timezone.now", return_value=now):
            form = EncontroForm(self.payload(link_expira_em_0="2026-11-16", link_expira_em_1="14:59"))
            self.assertFalse(form.is_valid())
            self.assertIn("link_expira_em", form.errors)

    def test_malformed_legacy_datetime_is_a_form_error(self):
        data = self.payload()
        del data["link_expira_em_0"], data["link_expira_em_1"]
        data["link_expira_em"] = "invalid"
        self.assertFalse(EncontroForm(data).is_valid())


class ExpirationFlowTests(PresencaRetroativaBaseTests):
    def test_diary_saves_explicit_deadline_and_preserves_it_on_edit(self):
        deadline = timezone.localtime(timezone.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
        diario, encontro = self.novo_diario(
            modo_frequencia="link", link_expira_em_0=deadline.strftime("%Y-%m-%d"),
            link_expira_em_1=deadline.strftime("%H:%M"),
        )
        self.assertEqual(encontro.link_expira_em, deadline)
        from ava.views.diario import _configurar_frequencia_do_diario
        with patch("ava.views.diario.timezone.now", return_value=deadline + timedelta(minutes=1)):
            _configurar_frequencia_do_diario(diario, self.professor_a)
            response = self.client.post(reverse("ava:diario_editar", args=[diario.pk]), self.dados_diario(
                modo_frequencia="link", link_expira_em_0=deadline.strftime("%Y-%m-%d"),
                link_expira_em_1=deadline.strftime("%H:%M"),
            ))
            self.assertEqual(response.status_code, 302)
        encontro.refresh_from_db()
        self.assertEqual(encontro.link_expira_em, deadline)

    def test_public_link_closes_at_exact_deadline(self):
        _, encontro = self.novo_diario(modo_frequencia="link")
        deadline = timezone.now() + timedelta(hours=1)
        EncontroCurso.raw_objects.filter(pk=encontro.pk).update(link_expira_em=deadline)
        url = reverse("ava:confirmar_presenca", args=[encontro.token])
        with patch("ava.views.attendance.timezone.now", return_value=deadline - timedelta(seconds=1)):
            self.assertContains(self.client.get(url), "Confirmar minha presença")
        with patch("ava.views.attendance.timezone.now", return_value=deadline):
            self.assertContains(self.client.get(url), "O link de presença está fechado ou expirou")
            self.client.post(url, {"matricula": self.matricula.pk})
        self.assertFalse(PresencaCurso.objects.filter(encontro=encontro, presente=True).exists())

    def test_checklist_renders_separate_fields_and_saves_local_hour(self):
        _, encontro = self.novo_diario(modo_frequencia="link")
        url = reverse("ava:frequencia_checklist", args=[encontro.pk])
        response = self.client.get(url)
        self.assertContains(response, 'type="date" name="link_expira_em_0"')
        self.assertContains(response, 'type="time" name="link_expira_em_1"')
        deadline = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=17, minute=45, second=0, microsecond=0)
        response = self.client.post(url, {
            "titulo": encontro.titulo, "data_aula": encontro.data_aula.isoformat(),
            "link_aberto": "on", "link_expira_em_0": deadline.strftime("%Y-%m-%d"),
            "link_expira_em_1": "17:45",
        })
        self.assertEqual(response.status_code, 302)
        encontro.refresh_from_db()
        self.assertEqual(encontro.link_expira_em, deadline)
