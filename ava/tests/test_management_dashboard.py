from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ava.models import (
    Atividade,
    AtividadeTentativa,
    Aula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    QuizAlternativa,
    QuizQuestao,
    QuizRespostaItem,
)
from core.models import Cliente


User = get_user_model()


class AVAManagementDashboardTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Gestao", slug="cliente-gestao")
        self.admin = User.objects.create_user(
            email="admin@gestao.com",
            nome="Admin Gestao",
            password="123456",
            cliente=self.cliente,
            role=User.Role.ADMIN_CLIENTE,
        )
        self.redator = User.objects.create_user(
            email="redator@gestao.com",
            nome="Redator Gestao",
            password="123456",
            cliente=self.cliente,
            role=User.Role.ARTICULADOR,
        )
        self.leitor = User.objects.create_user(
            email="leitor@gestao.com",
            nome="Leitor Gestao",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )
        self.aluno_1 = User.objects.create_user(
            email="aluno1@gestao.com",
            nome="Aluno Um",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )
        self.aluno_2 = User.objects.create_user(
            email="aluno2@gestao.com",
            nome="Aluno Dois",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )

        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Curso Gestao AVA",
            slug="curso-gestao-ava",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            autor_principal=self.admin,
        )
        self.modulo = CursoModulo.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            titulo="Modulo Gestao",
            ordem=1,
            is_active=True,
        )
        self.aula = Aula.objects.create(
            cliente=self.cliente,
            modulo=self.modulo,
            titulo="Aula Gestao",
            ordem=1,
            is_active=True,
        )
        self.atividade_quiz = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula,
            tipo=Atividade.Tipo.QUIZ,
            titulo="Quiz Gestao",
        )
        self.atividade_tarefa = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula,
            tipo=Atividade.Tipo.TAREFA,
            titulo="Tarefa Gestao",
        )

        self.questao = QuizQuestao.objects.create(
            cliente=self.cliente,
            atividade=self.atividade_quiz,
            enunciado="Questao da gestao?",
            ordem=1,
        )
        self.alt_correta = QuizAlternativa.objects.create(
            cliente=self.cliente,
            questao=self.questao,
            texto="Alternativa correta",
            is_correta=True,
            ordem=1,
        )
        self.alt_errada = QuizAlternativa.objects.create(
            cliente=self.cliente,
            questao=self.questao,
            texto="Alternativa errada",
            is_correta=False,
            ordem=2,
        )

        MatriculaCurso.objects.create(cliente=self.cliente, curso=self.curso, aluno=self.aluno_1, matriculado_por=self.admin)
        MatriculaCurso.objects.create(cliente=self.cliente, curso=self.curso, aluno=self.aluno_2, matriculado_por=self.admin)

        self.tentativa_1 = AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=self.atividade_quiz,
            aluno=self.aluno_1,
            status=AtividadeTentativa.Status.CORRIGIDA,
            nota_obtida=100,
        )
        self.tentativa_2 = AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=self.atividade_tarefa,
            aluno=self.aluno_2,
            status=AtividadeTentativa.Status.ENVIADA,
            texto_resposta="Minha resposta discursiva",
        )
        QuizRespostaItem.objects.create(
            cliente=self.cliente,
            tentativa=self.tentativa_1,
            questao=self.questao,
            alternativa_selecionada=self.alt_correta,
            is_correta=True,
            nota_item=100,
        )

    def test_dashboard_requires_admin_or_redator_role(self):
        self.client.force_login(self.leitor)
        response = self.client.get(reverse("ava:gestao_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allows_admin_and_redator(self):
        self.client.force_login(self.admin)
        response_admin = self.client.get(reverse("ava:gestao_dashboard"))
        self.assertEqual(response_admin.status_code, 200)
        self.assertContains(response_admin, "Dashboard de respostas e utilizacao")

        self.client.force_login(self.redator)
        response_redator = self.client.get(reverse("ava:gestao_dashboard"))
        self.assertEqual(response_redator.status_code, 200)
        self.assertContains(response_redator, "Tentativas e respostas dos usuarios")

    def test_dashboard_can_filter_by_usuario(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("ava:gestao_dashboard"), {"usuario": str(self.aluno_1.id)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["metricas"]["total_tentativas"], 1)
        tentativa_ids = {tentativa.id for tentativa in response.context["page_obj"].object_list}
        self.assertEqual(tentativa_ids, {self.tentativa_1.id})

    def test_tentativa_detalhe_shows_quiz_resposta(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("ava:gestao_tentativa_detalhe", args=[self.tentativa_1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Questao da gestao?")
        self.assertContains(response, "Alternativa correta")
