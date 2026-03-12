from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models import Cliente
from ava.models import (
    Curso, CursoModulo, Aula, ConteudoAula, Atividade, 
    MatriculaCurso, ProgressoAula, ProgressoConteudo
)
from ava.services import ProgressoService, InscricaoService

User = get_user_model()

class AVAServiceTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(name="Escola Teste", schema_name="public")
        self.user = User.objects.create_user(username="aluno1", email="aluno@teste.com", password="123")
        
        # Setup Curso
        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Curso Básico de Teste",
            slug="curso-basico-teste",
            carga_horaria=10,
            status=Curso.Status.PUBLICADO,
            is_aberto=True
        )
        
        # Setup Módulo e Aula
        self.modulo = CursoModulo.objects.create(curso=self.curso, titulo="Módulo 1", ordem=1)
        self.aula = Aula.objects.create(modulo=self.modulo, titulo="Aula 1", ordem=1)
        
        # Setup Conteúdos
        self.conteudo1 = ConteudoAula.objects.create(
            aula=self.aula, 
            titulo="Texto Base", 
            tipo=ConteudoAula.Tipo.TEXTO, 
            ordem=1
        )
        
    def test_inscricao_aluno_curso_aberto(self):
        """Testa se o serviço de inscrição matricula o aluno corretamente."""
        status_ok, msg = InscricaoService.matricular_aluno_curso(self.user, self.curso)
        self.assertTrue(status_ok)
        self.assertTrue(MatriculaCurso.objects.filter(aluno=self.user, curso=self.curso).exists())
        
    def test_inscricao_duplicada(self):
        """Testa se o sistema previne dupla matrícula."""
        InscricaoService.matricular_aluno_curso(self.user, self.curso)
        status_ok, msg = InscricaoService.matricular_aluno_curso(self.user, self.curso)
        self.assertFalse(status_ok)
        self.assertEqual(msg, "Aluno já está matriculado neste curso.")
        
    def test_progresso_conteudo_marca_aula_como_concluida(self):
        """Testa se ao consumir todos os conteúdos de uma aula, ela é marcada como concluída."""
        # Inscreve aluno
        matricula, _ = InscricaoService.matricular_aluno_curso(self.user, self.curso)
        
        # Marca conteúdo 1 como visto
        ProgressoService.marcar_conteudo_visualizado(self.user, self.conteudo1.id)
        
        # Verifica se o conteúdo foi marcado
        prog_conteudo = ProgressoConteudo.objects.get(aluno=self.user, conteudo=self.conteudo1)
        self.assertTrue(prog_conteudo.is_concluido)
        
        # Verifica se a aula também foi concluída, já que só tem 1 conteúdo
        prog_aula = ProgressoAula.objects.get(aluno=self.user, aula=self.aula)
        self.assertTrue(prog_aula.is_concluido)
        
        # Verifica progresso do curso (deve ser 100% pois só tem 1 aula)
        matr_atualizada = MatriculaCurso.objects.get(id=matricula[0].id)
        self.assertEqual(matr_atualizada.status, MatriculaCurso.Status.CONCLUIDA)
        self.assertEqual(matr_atualizada.progresso_percentual, 100)
