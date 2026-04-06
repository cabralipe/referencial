from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ava.models import (
    Atividade,
    AtividadeForumAnexo,
    AtividadeForumMensagem,
    AtividadeTentativa,
    Aula,
    ConteudoAula,
    Curso,
    CursoModulo,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
    QuizAlternativa,
    QuizQuestao,
)
from ava.services import ProgressoService
from core.models import Cliente, TipoUsuarioCadastro
from curriculum.models import Escola


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

    def test_quiz_com_questao_aparece_na_tela_da_atividade(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.QUIZ,
            titulo="Quiz da aula",
            is_obrigatoria=True,
        )
        questao = QuizQuestao.objects.create(
            cliente=self.cliente,
            atividade=atividade,
            enunciado="Qual alternativa esta correta?",
            ordem=1,
        )
        QuizAlternativa.objects.create(
            cliente=self.cliente,
            questao=questao,
            texto="Alternativa A",
            ordem=1,
            is_correta=True,
        )

        url = reverse(
            "ava:aluno_responder_atividade",
            args=[self.curso.slug, self.aula_1.id, atividade.id],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Qual alternativa esta correta?")
        self.assertContains(response, "Alternativa A")

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

    def test_post_atividade_mostra_concluida_e_anexo_enviado(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.ENVIO_ARQUIVO,
            titulo="Entrega final",
            is_obrigatoria=True,
        )

        url = reverse(
            "ava:aluno_responder_atividade",
            args=[self.curso.slug, self.aula_1.id, atividade.id],
        )
        arquivo = SimpleUploadedFile("resposta.pdf", b"%PDF-1.4", content_type="application/pdf")

        response = self.client.post(url, {"arquivo_enviado": arquivo}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1][0], url)
        self.assertContains(response, "Atividade concluida")
        self.assertContains(response, "Anexo enviado:")
        self.assertContains(response, "resposta")
        self.assertContains(response, ".pdf")

    def test_forum_cria_mensagem_com_anexo_e_conclui_aula(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.FORUM,
            titulo="Forum da aula",
            is_obrigatoria=True,
        )
        url = reverse(
            "ava:aluno_responder_atividade",
            args=[self.curso.slug, self.aula_1.id, atividade.id],
        )
        arquivo = SimpleUploadedFile("forum.txt", b"anotacao", content_type="text/plain")

        response = self.client.post(
            url,
            {
                "mensagem": "Minha primeira contribuicao com link https://example.com",
                "arquivos": arquivo,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mensagem publicada no forum.")
        self.assertContains(response, "Participacao registrada")
        self.assertContains(response, "Minha primeira contribuicao")

        tentativa = AtividadeTentativa.objects.get(aluno=self.user, atividade=atividade)
        self.assertEqual(tentativa.status, AtividadeTentativa.Status.CORRIGIDA)

        mensagem = AtividadeForumMensagem.objects.get(atividade=atividade, autor=self.user)
        self.assertEqual(mensagem.texto, "Minha primeira contribuicao com link https://example.com")
        self.assertTrue(AtividadeForumAnexo.objects.filter(mensagem=mensagem, nome_original="forum.txt").exists())

        progresso = ProgressoAula.objects.get(matricula=self.matricula, aula=self.aula_1)
        self.assertTrue(progresso.is_concluida)

    def test_forum_permite_responder_sem_criar_nova_tentativa(self):
        atividade = Atividade.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=Atividade.Tipo.FORUM,
            titulo="Forum permanente",
            is_obrigatoria=True,
        )
        url = reverse(
            "ava:aluno_responder_atividade",
            args=[self.curso.slug, self.aula_1.id, atividade.id],
        )

        self.client.post(url, {"mensagem": "Mensagem inicial"}, follow=True)
        primeira = AtividadeForumMensagem.objects.get(atividade=atividade, autor=self.user)

        response = self.client.post(
            url,
            {
                "mensagem": "Resposta em thread",
                "resposta_para": str(primeira.id),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AtividadeTentativa.objects.filter(aluno=self.user, atividade=atividade).count(), 1)
        self.assertEqual(AtividadeForumMensagem.objects.filter(atividade=atividade, autor=self.user).count(), 2)

        resposta = AtividadeForumMensagem.objects.exclude(pk=primeira.pk).get(atividade=atividade, autor=self.user)
        self.assertEqual(resposta.resposta_para, primeira)
        self.assertContains(response, "Resposta em thread")

    def test_catalogo_exibe_botao_inscrever_se_para_curso_aberto_nao_matriculado(self):
        curso_aberto = Curso.objects.create(
            cliente=self.cliente,
            titulo="Curso Livre Novo",
            slug="curso-livre-novo",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            autor_principal=self.user,
        )
        self.assertIsNotNone(curso_aberto.id)

        response = self.client.get(reverse("ava:catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inscrever-se no curso")

    def test_catalogo_exibe_botao_acessar_quando_ja_matriculado(self):
        response = self.client.get(reverse("ava:catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acessar curso")

    def test_catalogo_exibe_botao_inscrever_se_quando_usuario_nao_logado(self):
        self.client.logout()

        response = self.client.get(reverse("ava:catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inscrever-se no curso")

    def test_dashboard_recalcula_curso_concluido_quando_novo_conteudo_obrigatorio_e_adicionado(self):
        conteudo = ConteudoAula.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Conteudo inicial",
            conteudo_texto="Base",
            ordem=1,
        )

        ProgressoService.marcar_conteudo_visualizado(self.user, conteudo.id)
        self.matricula.refresh_from_db()
        self.assertEqual(self.matricula.status, MatriculaCurso.Status.CONCLUIDA)
        self.assertEqual(self.matricula.progresso_percentual, 100)

        ConteudoAula.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Conteudo novo",
            conteudo_texto="Novo requisito",
            ordem=2,
        )

        response = self.client.get(reverse("ava:aluno_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.matricula.refresh_from_db()
        self.assertEqual(self.matricula.status, MatriculaCurso.Status.ATIVA)
        self.assertEqual(self.matricula.progresso_percentual, 0)

    def test_dashboard_recalcula_curso_concluido_quando_novo_modulo_e_adicionado(self):
        conteudo = ConteudoAula.objects.create(
            cliente=self.cliente,
            aula=self.aula_1,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Conteudo inicial modulo 1",
            conteudo_texto="Base",
            ordem=1,
        )

        ProgressoService.marcar_conteudo_visualizado(self.user, conteudo.id)
        self.matricula.refresh_from_db()
        self.assertEqual(self.matricula.status, MatriculaCurso.Status.CONCLUIDA)
        self.assertEqual(self.matricula.progresso_percentual, 100)

        modulo_2 = CursoModulo.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            titulo="Modulo 2",
            ordem=2,
            is_active=True,
        )
        aula_4 = Aula.objects.create(
            cliente=self.cliente,
            modulo=modulo_2,
            titulo="Aula 4",
            ordem=1,
            is_active=True,
        )
        ConteudoAula.objects.create(
            cliente=self.cliente,
            aula=aula_4,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Conteudo novo modulo 2",
            conteudo_texto="Novo requisito",
            ordem=1,
        )

        response = self.client.get(reverse("ava:aluno_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.matricula.refresh_from_db()
        self.assertEqual(self.matricula.status, MatriculaCurso.Status.ATIVA)
        self.assertEqual(self.matricula.progresso_percentual, 50)


class AVAEnrollmentFlowTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Matricula", slug="cliente-matricula")
        self.user = User.objects.create_user(
            email="aluno-matricula@teste.com",
            nome="Aluno Matricula",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )
        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Curso de Matricula",
            slug="curso-de-matricula",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            carga_horaria=12,
            autor_principal=self.user,
        )
        self.client.force_login(self.user)

    def test_auto_inscricao_cria_matricula_e_exibe_curso_no_painel(self):
        response = self.client.post(reverse("ava:matricular_curso", args=[self.curso.slug]), follow=True)

        self.assertEqual(response.status_code, 200)
        matricula = MatriculaCurso.objects.get(curso=self.curso, aluno=self.user)
        self.assertEqual(matricula.cliente_id, self.cliente.id)
        self.assertEqual(matricula.status, MatriculaCurso.Status.ATIVA)

        dashboard_response = self.client.get(reverse("ava:aluno_dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, self.curso.titulo)

    def test_catalogo_trata_matricula_concluida_como_curso_ja_disponivel(self):
        MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.user,
            status=MatriculaCurso.Status.CONCLUIDA,
            matriculado_por=self.user,
        )

        response = self.client.get(reverse("ava:catalogo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acessar curso")
        self.assertNotContains(response, "Inscrever-se no curso")

    def test_post_rematricula_reativa_matricula_concluida(self):
        MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.user,
            status=MatriculaCurso.Status.CONCLUIDA,
            matriculado_por=self.user,
        )

        response = self.client.post(reverse("ava:matricular_curso", args=[self.curso.slug]), follow=True)

        self.assertEqual(response.status_code, 200)
        matricula = MatriculaCurso.objects.get(curso=self.curso, aluno=self.user)
        self.assertEqual(matricula.status, MatriculaCurso.Status.ATIVA)

        dashboard_response = self.client.get(reverse("ava:aluno_dashboard"))
        self.assertContains(dashboard_response, self.curso.titulo)

    def test_dashboard_exibe_secao_de_cursos_concluidos(self):
        MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.user,
            status=MatriculaCurso.Status.CONCLUIDA,
            progresso_percentual=100,
            matriculado_por=self.user,
        )

        response = self.client.get(reverse("ava:aluno_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cursos concluidos (1)")
        self.assertContains(response, self.curso.titulo)
        self.assertContains(response, "Rever curso")


class AVATeacherCatalogFlowTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Cliente Professor", slug="cliente-professor")
        self.escola = Escola.objects.create(cliente=self.cliente, nome="Escola Teste")
        self.tipo_professor = TipoUsuarioCadastro.objects.create(
            cliente=self.cliente,
            nome="Professor - Anos Iniciais",
            slug="professor-anos-iniciais",
            role_interno=User.Role.PROFESSOR,
            seguimento=User.Seguimento.PROFESSOR_ANOS_INICIAIS,
            acesso_ppp=TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
            exibir_no_cadastro=True,
            ativo=True,
            ordem_exibicao=10,
        )
        self.tipo_apoio = TipoUsuarioCadastro.objects.create(
            cliente=self.cliente,
            nome="Profissional de Apoio",
            slug="profissional-apoio",
            role_interno=User.Role.PROFESSOR,
            seguimento=User.Seguimento.PROFISSIONAL_APOIO,
            acesso_ppp=TipoUsuarioCadastro.AcessoPPP.VISUALIZAR,
            exibir_no_cadastro=True,
            ativo=True,
            ordem_exibicao=20,
        )
        self.professor = User.objects.create_user(
            email="professor@teste.com",
            nome="Professor Teste",
            password="123456",
            cliente=self.cliente,
            escola=self.escola,
            tipo_cadastro=self.tipo_professor,
            role=User.Role.PROFESSOR,
        )
        self.leitor = User.objects.create_user(
            email="leitor@teste.com",
            nome="Leitor Teste",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )
        self.curso_ppp = Curso.objects.create(
            cliente=self.cliente,
            titulo="Implementação do Referencial Curricular - Elaboração e Atualização do Projeto Político-Pedagógico",
            slug="implementacao-referencial-curricular-ppp-2",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            autor_principal=self.professor,
        )
        self.curso_visivel = Curso.objects.create(
            cliente=self.cliente,
            titulo="Outro Curso",
            slug="outro-curso",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
            autor_principal=self.professor,
        )

    def test_catalogo_nao_exibe_modal_de_seguimento_para_professor(self):
        self.client.force_login(self.professor)

        response = self.client.get(reverse("ava:catalogo"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Qual seu seguimento?")

    def test_catalogo_nao_exibe_modal_para_nao_professor(self):
        self.client.force_login(self.leitor)

        response = self.client.get(reverse("ava:catalogo"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Qual seu seguimento?")

    def test_profissional_de_apoio_nao_visualiza_curso_ppp(self):
        self.professor.tipo_cadastro = self.tipo_apoio
        self.professor.save(update_fields=["tipo_cadastro"])
        self.client.force_login(self.professor)

        response = self.client.get(reverse("ava:catalogo"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response,
            "Implementação do Referencial Curricular - Elaboração e Atualização do Projeto Político-Pedagógico",
        )
        self.assertContains(response, self.curso_visivel.titulo)
