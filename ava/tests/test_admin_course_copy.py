from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ava.models import Atividade, Aula, ConteudoAula, Curso, CursoModulo
from core.models import Cliente


User = get_user_model()


class AVACourseCopyAdminTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_superuser(
            email="super@proluc.com",
            password="123456",
            nome="Super Admin",
        )
        self.origem = Cliente.objects.create(nome="Municipio Origem", slug="municipio-origem")
        self.destino = Cliente.objects.create(nome="Municipio Destino", slug="municipio-destino")
        self.admin_destino = User.objects.create_user(
            email="admin@destino.com",
            password="123456",
            nome="Admin Destino",
            cliente=self.destino,
            role=User.Role.ADMIN_CLIENTE,
            is_staff=True,
        )

        self.curso_origem = Curso.objects.create(
            cliente=self.origem,
            titulo="Curso Base",
            slug="curso-base",
            status=Curso.Status.PUBLICADO,
            is_aberto=True,
        )
        self.modulo_1 = CursoModulo.objects.create(
            cliente=self.origem,
            curso=self.curso_origem,
            titulo="Modulo 1",
            ordem=1,
            is_active=True,
        )
        self.modulo_2 = CursoModulo.objects.create(
            cliente=self.origem,
            curso=self.curso_origem,
            titulo="Modulo 2",
            ordem=2,
            is_active=True,
            pre_requisito_modulo=self.modulo_1,
        )
        self.aula_1 = Aula.objects.create(
            cliente=self.origem,
            modulo=self.modulo_1,
            titulo="Aula 1",
            ordem=1,
            is_active=True,
        )
        self.aula_2 = Aula.objects.create(
            cliente=self.origem,
            modulo=self.modulo_2,
            titulo="Aula 2",
            ordem=1,
            is_active=True,
            pre_requisito_aula=self.aula_1,
        )
        ConteudoAula.objects.create(
            cliente=self.origem,
            aula=self.aula_1,
            tipo=ConteudoAula.Tipo.TEXTO,
            titulo="Conteudo 1",
            conteudo_texto="Texto de apoio",
            ordem=1,
        )
        Atividade.objects.create(
            cliente=self.origem,
            aula=self.aula_1,
            tipo=Atividade.Tipo.QUIZ,
            titulo="Quiz origem",
            is_obrigatoria=True,
        )

    def test_super_admin_copia_estrutura_sem_atividades_para_outro_cliente(self):
        self.client.force_login(self.super_admin)

        response = self.client.post(
            reverse("admin:ava_curso_copy_structure"),
            {
                "curso_origem": str(self.curso_origem.id),
                "cliente_destino": str(self.destino.id),
                "novo_titulo": "Curso Copiado",
                "novo_slug": "",
            },
        )

        self.assertEqual(response.status_code, 302)

        curso_copiado = Curso.objects.get(cliente=self.destino, titulo="Curso Copiado")
        self.assertEqual(curso_copiado.status, Curso.Status.RASCUNHO)
        self.assertEqual(curso_copiado.autor_principal, self.admin_destino)
        self.assertTrue(curso_copiado.slug.startswith("curso-base-municipio-destino"))

        self.assertEqual(curso_copiado.modulos.count(), 2)
        modulo_2_copiado = curso_copiado.modulos.get(ordem=2)
        self.assertIsNotNone(modulo_2_copiado.pre_requisito_modulo)
        self.assertEqual(modulo_2_copiado.pre_requisito_modulo.ordem, 1)

        aula_1_copiada = curso_copiado.modulos.get(ordem=1).aulas.get(ordem=1)
        aula_2_copiada = curso_copiado.modulos.get(ordem=2).aulas.get(ordem=1)
        self.assertEqual(aula_1_copiada.conteudos.count(), 1)
        self.assertEqual(aula_2_copiada.pre_requisito_aula, aula_1_copiada)
        self.assertEqual(aula_1_copiada.atividades.count(), 0)

    def test_copy_structure_view_bloqueia_admin_cliente(self):
        admin_cliente = User.objects.create_user(
            email="admin@origem.com",
            password="123456",
            nome="Admin Origem",
            cliente=self.origem,
            role=User.Role.ADMIN_CLIENTE,
            is_staff=True,
        )
        self.client.force_login(admin_cliente)

        response = self.client.get(reverse("admin:ava_curso_copy_structure"))
        self.assertEqual(response.status_code, 403)
