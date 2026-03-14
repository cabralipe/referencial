from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ava.models import (
    Atividade,
    AtividadeTentativa,
    Aula,
    ConteudoAula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
)
from ava.services import ProgressoService
from core.models import Cliente


User = get_user_model()


class AVAStudentFlowTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Teste", slug="cliente-teste")
        self.user = User.objects.create_user(
            email="aluno@teste.com",
            nome="Aluno Teste",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )

        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Curso Teste",
            slug="curso-teste",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            carga_horaria=10,
            autor_principal=self.user,
        )
        self.modulo = CursoModulo.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            titulo="Modulo 1",
            ordem=1,
            is_active=True,
        )
        self.aula_1 = Aula.objects.create(
            cliente=self.cliente,
            modulo=self.modulo,
            titulo="Aula 1",
            ordem=1,
            is_active=True,
        )
        self.aula_2 = Aula.objects.create(
            cliente=self.cliente,
            modulo=self.modulo,
            titulo="Aula 2",
            ordem=2,
            is_active=True,
        )
        self.aula_3 = Aula.objects.create(
            cliente=self.cliente,
            modulo=self.modulo,
            titulo="Aula 3",
            ordem=3,
            is_active=True,
        )

        self.matricula = MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.user,
            matriculado_por=self.user,
        )

        self.client.force_login(self.user)

    def test_get_atividade_envio_arquivo_nao_cria_tentativa_e_mostra_formulario(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.ENVIO_ARQUIVO,
            titulo="Entrega de arquivo",
            is_obrigatoria=True,
        )

        url = reverse(
            "ava:aluno_responder_atividade",
            args=[self.curso.slug, self.aula_1.id, atividade.id],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="arquivo_enviado"', html=False)
        self.assertNotContains(response, "Atividade concluida")
        self.assertFalse(AtividadeTentativa.objects.filter(aluno=self.user, atividade=atividade).exists())

    def test_marcar_conteudo_visualizado_funciona(self):
        conteudo = ConteudoAula.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Texto base",
            conteudo_texto="Conteudo",
            ordem=1,
        )

        url = reverse("ava:aluno_marcar_conteudo", args=[conteudo.id])
        next_url = reverse("ava:aluno_acessar_aula", args=[self.curso.slug, self.aula_1.id])
        response = self.client.post(url, {"next": next_url})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, next_url)

        progresso = ProgressoConteudo.objects.get(
            progresso_aula__matricula=self.matricula,
            progresso_aula__aula=self.aula_1,
            conteudo=conteudo,
        )
        self.assertTrue(progresso.is_visualizado)

    def test_acessar_aula_define_anterior_e_proxima(self):
        url = reverse("ava:aluno_acessar_aula", args=[self.curso.slug, self.aula_2.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["aula_anterior"].id, self.aula_1.id)
        self.assertEqual(response.context["proxima_aula"].id, self.aula_3.id)

    def test_recalculo_aula_nao_conclui_com_duas_tentativas_da_mesma_atividade(self):
        atividade_1 = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.TAREFA,
            titulo="Atividade 1",
            is_obrigatoria=True,
        )
        atividade_2 = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.TAREFA,
            titulo="Atividade 2",
            is_obrigatoria=True,
        )

        ProgressoService._garantir_progressos(self.matricula, self.aula_1)

        AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=atividade_1,
            aluno=self.user,
            status=AtividadeTentativa.Status.ENVIADA,
        )
        AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=atividade_1,
            aluno=self.user,
            status=AtividadeTentativa.Status.CORRIGIDA,
        )

        ProgressoService.recalcular_aula(self.matricula, self.aula_1)
        progresso = ProgressoAula.objects.get(matricula=self.matricula, aula=self.aula_1)
        self.assertFalse(progresso.is_concluida)

        AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=atividade_2,
            aluno=self.user,
            status=AtividadeTentativa.Status.ENVIADA,
        )

        ProgressoService.recalcular_aula(self.matricula, self.aula_1)
        progresso.refresh_from_db()
        self.assertTrue(progresso.is_concluida)

    def test_recalculo_aula_envio_arquivo_exige_anexo(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.ENVIO_ARQUIVO,
            titulo="Entrega PDF",
            is_obrigatoria=True,
        )

        ProgressoService._garantir_progressos(self.matricula, self.aula_1)

        tentativa = AtividadeTentativa.objects.create(
            cliente=self.cliente,
            atividade=atividade,
            aluno=self.user,
            status=AtividadeTentativa.Status.ENVIADA,
        )

        ProgressoService.recalcular_aula(self.matricula, self.aula_1)
        progresso = ProgressoAula.objects.get(matricula=self.matricula, aula=self.aula_1)
        self.assertFalse(progresso.is_concluida)

        tentativa.arquivo_enviado = SimpleUploadedFile("tarefa.pdf", b"%PDF-1.4", content_type="application/pdf")
        tentativa.save(update_fields=["arquivo_enviado"])

        ProgressoService.recalcular_aula(self.matricula, self.aula_1)
        progresso.refresh_from_db()
        self.assertTrue(progresso.is_concluida)
