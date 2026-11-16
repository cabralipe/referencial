import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
import subprocess
from django.test.runner import DiscoverRunner
from django.urls import reverse
from ava.tests.test_diario_bordo import DiarioBordoViewTests
from ava.views import diario


def preview(self):
    self.criar_diario()
    self.client.force_login(self.professor_a)
    response = self.client.get(reverse("ava:diario_lista"))
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, "Relatório de frequência")
    Path("tmp/diario-relatorios-preview.html").write_bytes(response.content)
    original = subprocess.run(
        ["git", "show", "HEAD:ava/views/diario.py"], check=True, capture_output=True
    ).stdout.decode("utf-8")
    exec(compile(original, "baseline_diario.py", "exec"), diario.__dict__)


DiarioBordoViewTests.test_aaa_preview = preview
prefix = "ava.tests.test_diario_bordo.DiarioBordoViewTests."
sys.exit(DiscoverRunner(verbosity=1, interactive=False).run_tests([
    prefix + "test_aaa_preview",
    prefix + "test_professor_cria_atividade_externa_sem_curso",
    prefix + "test_professor_cria_registro_hibrido",
    prefix + "test_professor_cria_registro_no_sistema_pela_interface",
]))
