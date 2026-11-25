from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ava.models import CicloReferencial, MaterialReferenciaPlano
from core.models import Cliente


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "private": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class MaterialReferenciaPlanoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.municipio = Cliente.objects.create(nome="Cidade dos Materiais", slug="cidade-materiais")
        cls.outro = Cliente.objects.create(nome="Outra Cidade", slug="outra-materiais")
        cls.admin = User.objects.create_user(
            email="admin-materiais@example.com", nome="Administradora", password="teste",
            role="admin_cliente", cliente=cls.municipio, is_staff=True,
        )
        cls.pessoa = User.objects.create_user(
            email="pessoa-materiais@example.com", nome="Participante", password="teste",
            role="leitor", cliente=cls.municipio,
        )
        cls.externo = User.objects.create_user(
            email="externo-materiais@example.com", nome="Externo", password="teste",
            role="admin_cliente", cliente=cls.outro, is_staff=True,
        )
        cls.ciclo = CicloReferencial.raw_objects.create(cliente=cls.municipio, nome="Ciclo dos materiais")
        cls.ciclo2 = CicloReferencial.raw_objects.create(cliente=cls.municipio, nome="Segundo ciclo")
        cls.ciclo_externo = CicloReferencial.raw_objects.create(cliente=cls.outro, nome="Ciclo externo")

    def setUp(self):
        campo = MaterialReferenciaPlano._meta.get_field("arquivo")
        anterior = campo.storage
        campo.storage = InMemoryStorage()
        self.addCleanup(setattr, campo, "storage", anterior)

    def material(self, **kwargs):
        dados = {"cliente": self.municipio, "titulo": "Material de apoio", "link": "https://example.com/apoio"}
        dados.update(kwargs)
        return MaterialReferenciaPlano.raw_objects.create(**dados)

    def test_admin_cadastra_link_e_define_municipio_automaticamente(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("admin:ava_materialreferenciaplano_add"), {
            "titulo": "Orientações municipais", "link": "https://example.com/orientacoes",
            "ordem": 2, "ativo": "on", "cliente": self.outro.pk,
        })
        self.assertEqual(resposta.status_code, 302)
        material = MaterialReferenciaPlano.raw_objects.get(titulo="Orientações municipais")
        self.assertEqual(material.cliente_id, self.municipio.pk)
        self.assertTrue(material.ativo)
        self.assertIsNone(material.ciclo_id)

    def test_admin_envia_anexo_e_participante_baixa_arquivo(self):
        self.client.force_login(self.admin)
        conteudo = b"%PDF-1.4 arquivo de teste"
        resposta = self.client.post(reverse("admin:ava_materialreferenciaplano_add"), {
            "titulo": "Guia para a sala", "arquivo": SimpleUploadedFile("guia.pdf", conteudo, "application/pdf"),
            "ciclo": self.ciclo.pk, "ordem": 0, "ativo": "on",
        })
        self.assertEqual(resposta.status_code, 302)
        material = MaterialReferenciaPlano.raw_objects.get(titulo="Guia para a sala")
        self.assertEqual(material.nome_original, "guia.pdf")
        self.assertIn(f"ava/plano/materiais/{self.municipio.pk}/", material.arquivo.name)
        edicao = self.client.get(reverse("admin:ava_materialreferenciaplano_change", args=[material.pk]))
        self.assertContains(edicao, f'href="{reverse("ava:gt_material_download", args=[material.pk])}"')
        self.assertContains(edicao, ">guia.pdf</a>")
        self.client.force_login(self.pessoa)
        resposta = self.client.get(reverse("ava:gt_material_download", args=[material.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(b"".join(resposta.streaming_content), conteudo)
        self.assertIn('filename="guia.pdf"', resposta["Content-Disposition"])
        self.assertEqual(resposta["X-Content-Type-Options"], "nosniff")

    def test_exibicao_por_ciclo_ordem_e_ativacao(self):
        self.material(titulo="Primeira referência", ordem=1)
        self.material(titulo="Referência do ciclo", ciclo=self.ciclo, ordem=2)
        self.material(titulo="Outro ciclo não aparece", ciclo=self.ciclo2)
        self.material(titulo="Inativo não aparece", ativo=False)
        self.material(titulo="Excluído não aparece", is_deleted=True)
        self.material(titulo="Outro município não aparece", cliente=self.outro)
        self.client.force_login(self.pessoa)
        resposta = self.client.get(reverse("ava:gt_salas"), {"ciclo": self.ciclo.pk})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([m.titulo for m in resposta.context["materiais_referencia"]], ["Primeira referência", "Referência do ciclo"])
        self.assertContains(resposta, "Consultar documento nacional")
        self.assertContains(resposta, 'aria-label="Materiais de referência"')
        self.assertNotContains(resposta, "Outro ciclo não aparece")
        self.assertNotContains(resposta, "Outro município não aparece")

    def test_link_e_anexo_no_mesmo_material(self):
        material = self.material(arquivo=SimpleUploadedFile("anexo.txt", b"Apoio"))
        material.full_clean()
        self.client.force_login(self.pessoa)
        resposta = self.client.get(reverse("ava:gt_salas"), {"ciclo": self.ciclo.pk})
        self.assertContains(resposta, 'href="https://example.com/apoio"')
        self.assertContains(resposta, reverse("ava:gt_material_download", args=[material.pk]))
        self.assertContains(resposta, "Baixar anexo de Material de apoio")

    def test_download_exige_login_municipio_e_material_ativo(self):
        material = self.material(arquivo=SimpleUploadedFile("anexo.txt", b"Apoio"))
        url = reverse("ava:gt_material_download", args=[material.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.externo)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.pessoa)
        material.ativo = False
        material.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        material.ativo = True
        material.is_deleted = True
        material.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_admin_isola_municipios_e_ciclos(self):
        externo = self.material(titulo="Documento externo", cliente=self.outro)
        self.client.force_login(self.admin)
        lista = self.client.get(reverse("admin:ava_materialreferenciaplano_changelist"))
        self.assertNotContains(lista, "Documento externo")
        self.assertEqual(self.client.get(reverse("admin:ava_materialreferenciaplano_change", args=[externo.pk])).status_code, 302)
        resposta = self.client.post(reverse("admin:ava_materialreferenciaplano_add"), {
            "titulo": "Ciclo inválido", "link": "https://example.com/apoio", "ciclo": self.ciclo_externo.pk,
            "ordem": 0, "ativo": "on",
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(MaterialReferenciaPlano.raw_objects.filter(titulo="Ciclo inválido").exists())
        self.client.force_login(self.pessoa)
        self.assertEqual(self.client.get(reverse("admin:ava_materialreferenciaplano_add")).status_code, 302)

    def test_validacao_do_material_e_dos_arquivos(self):
        dados = {"cliente": self.municipio, "titulo": "Material"}
        casos = [
            {}, {"link": "javascript:alert(1)"}, {"link": "ftp://example.com/anexo.pdf"},
            {"arquivo": SimpleUploadedFile("pagina.html", b"<html></html>")},
            {"arquivo": UploadedFile(file=BytesIO(b"a"), name="grande.pdf", size=21 * 1024 * 1024)},
            {"link": "https://example.com", "ciclo": self.ciclo_externo},
        ]
        for caso in casos:
            with self.subTest(caso=caso), self.assertRaises(ValidationError):
                MaterialReferenciaPlano(**dados, **caso).full_clean()

    def test_download_sem_arquivo_ou_arquivo_ausente(self):
        self.client.force_login(self.pessoa)
        material = self.material()
        self.assertEqual(self.client.get(reverse("ava:gt_material_download", args=[material.pk])).status_code, 404)
        material.arquivo = "ava/plano/materiais/ausente.pdf"
        material.save()
        self.assertEqual(self.client.get(reverse("ava:gt_material_download", args=[material.pk])).status_code, 404)
