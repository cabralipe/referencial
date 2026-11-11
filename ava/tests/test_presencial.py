from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ava.models import MatriculaCurso, RegistroSeminario, RepasseFrequencia
from ava.tests.test_diario_bordo import DiarioBordoBaseTests, User


class PresencialTests(DiarioBordoBaseTests):
    def setUp(self):
        super().setUp()
        aluno = User.objects.create_user(email='cursista-presencial@example.com', nome='Cursista Teste', password='123456', cliente=self.cliente)
        self.matricula = MatriculaCurso.objects.create(cliente=self.cliente, curso=self.curso, aluno=aluno)
        self.client.force_login(self.admin)

    def test_crud_atividade_e_relatorio(self):
        url = reverse('ava:presencial_registro_novo', args=[self.curso.pk])
        response = self.client.post(url, {'matricula': self.matricula.pk, 'tipo': 'seminario', 'atividade': 'Apresentação', 'data_realizacao': '2026-11-01', 'nota': '8.5', 'observacoes': ''})
        self.assertEqual(response.status_code, 302)
        registro = RegistroSeminario.raw_objects.get(matricula=self.matricula)
        response = self.client.post(reverse('ava:presencial_registro_editar', args=[self.curso.pk, registro.pk]), {'matricula': self.matricula.pk, 'tipo': 'pratica', 'atividade': 'Prática revisada', 'data_realizacao': '2026-11-02', 'nota': '9', 'observacoes': ''})
        self.assertEqual(response.status_code, 302)
        registro.refresh_from_db()
        self.assertEqual(registro.atividade, 'Prática revisada')
        response = self.client.get(reverse('ava:presencial_relatorio', args=[self.curso.pk]))
        self.assertContains(response, 'Prática revisada')
        response = self.client.post(reverse('ava:presencial_remover', args=[self.curso.pk, 'registro', registro.pk]))
        self.assertEqual(response.status_code, 302)
        registro.refresh_from_db()
        self.assertTrue(registro.is_deleted)

    def test_repasse_pdf_e_restricao_curso(self):
        response = self.client.get(reverse('ava:presencial_pdf', args=[self.curso.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        response = self.client.post(reverse('ava:presencial_repasse_novo', args=[self.curso.pk]), {'data_encontro': '2026-11-01', 'descricao': 'Encontro', 'arquivo': SimpleUploadedFile('lista.pdf', b'%PDF-1.4\n%%EOF', content_type='application/pdf')})
        self.assertEqual(response.status_code, 302)
        repasse = RepasseFrequencia.raw_objects.get(curso=self.curso)
        response = self.client.get(reverse('ava:presencial_arquivo', args=[self.curso.pk, repasse.pk]))
        self.assertEqual(response.status_code, 200)
        response.close()
        response = self.client.post(reverse('ava:presencial_repasse_editar', args=[self.curso.pk, repasse.pk]), {'data_encontro': '2026-11-02', 'descricao': 'Encontro revisado'})
        self.assertEqual(response.status_code, 302)
        repasse.refresh_from_db()
        self.assertEqual(repasse.descricao, 'Encontro revisado')
        response = self.client.post(reverse('ava:presencial_remover', args=[self.curso.pk, 'repasse', repasse.pk]))
        self.assertEqual(response.status_code, 302)
        repasse.refresh_from_db()
        self.assertTrue(repasse.is_deleted)
        self.client.force_login(self.professor_outro)
        self.assertEqual(self.client.get(reverse('ava:presencial_pdf', args=[self.curso.pk])).status_code, 404)
