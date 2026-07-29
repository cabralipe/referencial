from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from ava.models import Curso, DocumentoAcompanhamento, MatriculaCurso
from core.models import Cliente
from curriculum.models import Escola


User = get_user_model()


class AcompanhamentoPedagogicoTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nome="Município Acompanhamento",
            slug="municipio-acompanhamento",
        )
        self.escola_a = Escola.objects.create(
            cliente=self.cliente,
            nome="Escola A",
        )
        self.escola_b = Escola.objects.create(
            cliente=self.cliente,
            nome="Escola B",
        )
        self.admin = User.objects.create_user(
            email="admin-acompanhamento@example.com",
            nome="Admin",
            password="123456",
            cliente=self.cliente,
            role=User.Role.ADMIN_CLIENTE,
        )
        self.professor_a = User.objects.create_user(
            email="professor-a@example.com",
            nome="Professor A",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_a,
            role=User.Role.PROFESSOR,
        )
        self.professor_b = User.objects.create_user(
            email="professor-b@example.com",
            nome="Professor B",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_b,
            role=User.Role.PROFESSOR,
        )
        self.cursista = User.objects.create_user(
            email="cursista@example.com",
            nome="Cursista",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_a,
            role=User.Role.LEITOR,
        )
        self.aluno_a = User.objects.create_user(
            email="aluno-a@example.com",
            nome="Aluno A",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_a,
            role=User.Role.LEITOR,
        )
        self.aluno_b = User.objects.create_user(
            email="aluno-b@example.com",
            nome="Aluno B",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_b,
            role=User.Role.LEITOR,
        )
        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Formação 2026",
            slug="formacao-2026-acompanhamento",
            status=Curso.Status.PUBLICADO,
            autor_principal=self.admin,
        )
        MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.aluno_a,
            matriculado_por=self.admin,
        )
        MatriculaCurso.objects.create(
            cliente=self.cliente,
            curso=self.curso,
            aluno=self.aluno_b,
            matriculado_por=self.admin,
        )
        self.documento_a = self._criar_documento(
            escola=self.escola_a,
            aluno=self.aluno_a,
            titulo="Relatório do aluno A",
            created_by=self.professor_a,
        )
        self.documento_b = self._criar_documento(
            escola=self.escola_b,
            aluno=self.aluno_b,
            titulo="Relatório do aluno B",
            created_by=self.professor_b,
        )

    def tearDown(self):
        for documento in DocumentoAcompanhamento.raw_objects.all():
            if documento.arquivo:
                documento.arquivo.storage.delete(documento.arquivo.name)

    def _criar_documento(self, *, escola, aluno, titulo, created_by):
        return DocumentoAcompanhamento.objects.create(
            cliente=self.cliente,
            escola=escola,
            curso=self.curso,
            aluno=aluno,
            categoria=DocumentoAcompanhamento.Categoria.RELATORIO,
            titulo=titulo,
            arquivo=SimpleUploadedFile(
                f"{aluno.id}.pdf",
                b"%PDF-1.4 acompanhamento",
                content_type="application/pdf",
            ),
            created_by=created_by,
        )

    def test_cursista_nao_acessa_lista_nem_arquivo(self):
        self.client.force_login(self.cursista)

        lista = self.client.get(reverse("ava:gestao_acompanhamento"))
        arquivo = self.client.get(
            reverse("ava:gestao_acompanhamento_arquivo", args=[self.documento_a.id])
        )

        self.assertEqual(lista.status_code, 403)
        self.assertEqual(arquivo.status_code, 403)

    def test_professor_visualiza_somente_documentos_da_propria_escola(self):
        self.client.force_login(self.professor_a)

        response = self.client.get(reverse("ava:gestao_acompanhamento"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.documento_a.titulo)
        self.assertNotContains(response, self.documento_b.titulo)

    def test_filtro_por_nome_do_aluno_aceita_busca_parcial(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("ava:gestao_acompanhamento"),
            {"nome_aluno": "Aluno A"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.documento_a.titulo)
        self.assertNotContains(response, self.documento_b.titulo)
        self.assertEqual(response.context["filtros"]["nome_aluno"], "Aluno A")

    def test_professor_nao_baixa_documento_de_outra_escola(self):
        self.client.force_login(self.professor_a)

        response = self.client.get(
            reverse("ava:gestao_acompanhamento_arquivo", args=[self.documento_b.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_visualiza_e_baixa_documentos_de_todas_as_escolas(self):
        self.client.force_login(self.admin)

        lista = self.client.get(reverse("ava:gestao_acompanhamento"))
        arquivo = self.client.get(
            reverse("ava:gestao_acompanhamento_arquivo", args=[self.documento_b.id]),
            {"download": "1"},
        )

        self.assertContains(lista, self.documento_a.titulo)
        self.assertContains(lista, self.documento_b.titulo)
        self.assertEqual(arquivo.status_code, 200)
        self.assertEqual(arquivo["Cache-Control"], "private, no-store")
        self.assertIn("attachment", arquivo["Content-Disposition"])
        arquivo.close()

    def test_professor_cadastra_documento_vinculado_a_escola_e_aluno(self):
        self.client.force_login(self.professor_a)

        response = self.client.post(
            reverse("ava:gestao_acompanhamento_novo"),
            {
                "municipio": self.cliente.id,
                "escola": self.escola_a.id,
                "curso": self.curso.id,
                "aluno": self.aluno_a.id,
                "categoria": DocumentoAcompanhamento.Categoria.FREQUENCIA,
                "titulo": "Frequência de julho",
                "descricao": "Registro mensal.",
                "periodo_referencia": "2026-07-01",
                "arquivo": SimpleUploadedFile(
                    "frequencia-julho.xlsx",
                    b"planilha privada",
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            },
        )

        self.assertRedirects(response, reverse("ava:gestao_acompanhamento"))
        documento = DocumentoAcompanhamento.raw_objects.get(titulo="Frequência de julho")
        self.assertEqual(documento.cliente, self.cliente)
        self.assertEqual(documento.escola, self.escola_a)
        self.assertEqual(documento.aluno, self.aluno_a)
        self.assertEqual(documento.created_by, self.professor_a)

    def test_formulario_exibe_busca_de_aluno_por_nome(self):
        self.client.force_login(self.professor_a)

        response = self.client.get(reverse("ava:gestao_acompanhamento_novo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buscar aluno pelo nome")
        self.assertContains(response, 'id="filtro_nome_aluno"')
        self.assertContains(response, "Digite parte do nome do aluno")

    def test_professor_nao_vincula_documento_a_aluno_de_outra_escola(self):
        self.client.force_login(self.professor_a)

        response = self.client.post(
            reverse("ava:gestao_acompanhamento_novo"),
            {
                "municipio": self.cliente.id,
                "escola": self.escola_a.id,
                "curso": self.curso.id,
                "aluno": self.aluno_b.id,
                "categoria": DocumentoAcompanhamento.Categoria.RELATORIO,
                "titulo": "Tentativa indevida",
                "arquivo": SimpleUploadedFile("relatorio.pdf", b"%PDF-1.4"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DocumentoAcompanhamento.raw_objects.filter(titulo="Tentativa indevida").exists()
        )

    def test_arquivamento_preserva_documento_e_remove_da_listagem_ativa(self):
        self.client.force_login(self.professor_a)

        response = self.client.post(
            reverse("ava:gestao_acompanhamento_arquivar", args=[self.documento_a.id])
        )

        self.assertRedirects(response, reverse("ava:gestao_acompanhamento"))
        self.documento_a.refresh_from_db()
        self.assertTrue(self.documento_a.arquivado)
        self.assertEqual(self.documento_a.arquivado_por, self.professor_a)

        lista = self.client.get(reverse("ava:gestao_acompanhamento"))
        self.assertNotContains(lista, self.documento_a.titulo)
