import csv
import io
import json
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ava.data.pne_2026 import CATEGORIAS_PNE, ESTRATEGIAS_PNE
from ava.models import CicloReferencial, InscricaoSalaGT, LinhaPlanoEducacao, SalaGT
from ava.services import plano_educacao_service as plano
from core.models import Cliente


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class PlanoEducacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.municipio = Cliente.objects.create(nome="Cidade do Plano", slug="cidade-plano")
        cls.outro = Cliente.objects.create(nome="Outra Cidade", slug="outra-plano")
        cls.admin = User.objects.create_user(email="admin-plano@test.com", nome="Administradora", password="teste", cliente=cls.municipio, role="admin_cliente")
        # O papel global de leitor também pode inscrever-se e começar a editar.
        cls.pessoa = User.objects.create_user(email="pessoa-plano@test.com", nome="Participante", password="teste", cliente=cls.municipio, role="leitor")
        cls.colega = User.objects.create_user(email="colega-plano@test.com", nome="Colega", password="teste", cliente=cls.municipio, role="membro_gt")
        cls.externo = User.objects.create_user(email="externo-plano@test.com", nome="Externo", password="teste", cliente=cls.outro, role="admin_cliente")
        cls.ciclo = CicloReferencial.raw_objects.create(cliente=cls.municipio, nome="Ciclo do plano")
        plano.preparar_ciclo(cls.ciclo)
        cls.sala = SalaGT.raw_objects.get(ciclo=cls.ciclo, objetivo__codigo="PNE-01")
        cls.principal = LinhaPlanoEducacao.raw_objects.get(sala=cls.sala, tipo="objetivo")
        cls.meta = LinhaPlanoEducacao.raw_objects.get(sala=cls.sala, codigo="1.a")

    def api(self, dados, sala=None):
        return self.client.post(reverse("ava:gt_plano_celulas", args=[(sala or self.sala).pk]), data=json.dumps(dados), content_type="application/json")

    def entrar(self, pessoa=None):
        self.client.force_login(pessoa or self.pessoa)
        return self.client.post(reverse("ava:gt_inscricao_solicitar", args=[self.sala.pk]))

    def test_estrutura_nacional_vazia_e_idempotente(self):
        salas = list(SalaGT.raw_objects.filter(ciclo=self.ciclo).order_by("objetivo__ordem"))
        self.assertEqual(len(salas), 19)
        for numero, (sala, (titulo, total)) in enumerate(zip(salas, CATEGORIAS_PNE), 1):
            self.assertIsNone(sala.gt_id)
            self.assertEqual(sala.objetivo.titulo, titulo)
            linhas = plano.linhas_da_sala(sala)
            self.assertEqual(
                [l.rotulo for l in linhas],
                [f"Objetivo {numero}"] + [f"Meta {numero}.{chr(97+i)}" for i in range(total)]
                + [f"Estratégia {numero}.{i}" for i in range(1, ESTRATEGIAS_PNE[numero - 1] + 1)],
            )
            self.assertTrue(all(l.texto == "" for l in linhas))
        self.assertEqual(LinhaPlanoEducacao.raw_objects.filter(sala__ciclo=self.ciclo, tipo="estrategia").count(), 372)
        self.meta.texto = "Texto já escrito"
        self.meta.save()
        plano.preparar_ciclo(self.ciclo)
        self.assertEqual(SalaGT.raw_objects.filter(ciclo=self.ciclo).count(), 19)
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.texto, "Texto já escrito")

    def test_catalogo_e_previa_sem_vazar_redacoes(self):
        self.client.force_login(self.pessoa)
        self.meta.texto = "Conteúdo reservado da sala"
        self.meta.save()
        pagina = self.client.get(reverse("ava:gt_salas"))
        self.assertEqual(len(pagina.context["cartoes"]), 19)
        self.assertContains(pagina, "Acesso à Educação Infantil")
        previa = self.client.get(reverse("ava:gt_sala", args=[self.sala.pk]))
        self.assertContains(previa, "Inscrever-se e começar")
        self.assertNotContains(previa, "Conteúdo reservado da sala")
        self.assertEqual(self.client.get(reverse("ava:gt_plano_celulas", args=[self.sala.pk])).status_code, 403)

    def test_inscricao_direta_sem_gt_limites_ou_aprovacao(self):
        self.ciclo.confirmacao_automatica = False
        self.ciclo.max_salas_por_participante = 1
        self.ciclo.save()
        self.sala.capacidade = 0
        self.sala.save()
        self.entrar()
        self.entrar()
        inscricao = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.pessoa)
        self.assertEqual(inscricao.estado, "confirmada")
        self.assertEqual(inscricao.papel, "participante")
        self.assertTrue(plano.pode_editar(self.pessoa, self.sala))
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)
        outra_sala = SalaGT.raw_objects.filter(ciclo=self.ciclo).exclude(pk=self.sala.pk).first()
        plano.inscrever(self.pessoa, outra_sala)

    def test_autosave_recarrega_e_permite_apagar(self):
        self.entrar()
        texto = "Ampliar o acesso.\nSegunda linha com acentuação."
        resposta = self.api({"id": self.meta.pk, "texto": texto, "revisao": 0})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["linha"]["revisao"], 1)
        self.assertContains(self.client.get(reverse("ava:gt_sala", args=[self.sala.pk])), "Ampliar o acesso.")
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "", "revisao": 1}).status_code, 200)
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.texto, "")

    def test_edicao_simultanea_por_celula_e_conflito_sem_perda(self):
        self.entrar()
        plano.inscrever(self.colega, self.sala)
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Primeira redação", "revisao": 0}).status_code, 200)
        self.client.force_login(self.colega)
        self.assertEqual(self.api({"id": self.principal.pk, "texto": "Outro campo", "revisao": 0}).status_code, 200)
        conflito = self.api({"id": self.meta.pk, "texto": "Segunda redação", "revisao": 0})
        self.assertEqual(conflito.status_code, 409)
        self.assertEqual(conflito.json()["linha"]["texto"], "Primeira redação")
        # Reenvio idempotente depois de perder a resposta HTTP.
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Primeira redação", "revisao": 0}).status_code, 200)
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Segunda redação", "revisao": 1}).status_code, 200)

    def test_adicionar_objetivo_e_metas(self):
        self.entrar()
        objetivo = self.api({"acao": "adicionar", "tipo": "objetivo"})
        self.assertEqual(objetivo.status_code, 201)
        self.assertEqual(objetivo.json()["linha"]["rotulo"], "Objetivo 1.2")
        extra = self.api({"acao": "adicionar", "tipo": "meta", "objetivo_id": objetivo.json()["linha"]["id"]})
        self.assertEqual(extra.json()["linha"]["rotulo"], "Meta 1.2.a")
        self.assertEqual(extra.json()["linha"]["texto"], "")
        self.assertEqual(self.api({"acao": "adicionar", "tipo": "meta", "objetivo_id": self.principal.pk}).json()["linha"]["rotulo"], "Meta 1.d")

    def test_admin_define_leitor_e_editor_sem_mudar_papel_global(self):
        self.entrar()
        vinculo = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.pessoa)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("ava:gt_participantes")), self.pessoa.nome)
        resposta = self.client.post(reverse("ava:gt_plano_papel", args=[self.sala.pk, vinculo.pk]), {"papel": "leitor"})
        self.assertEqual(resposta.status_code, 302)
        self.client.force_login(self.pessoa)
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Não permitido", "revisao": 0}).status_code, 403)
        self.assertEqual(self.client.get(reverse("ava:gt_plano_celulas", args=[self.sala.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("ava:gt_participantes")).status_code, 403)
        self.assertEqual(self.client.post(reverse("ava:gt_plano_papel", args=[self.sala.pk, vinculo.pk]), {"papel": "coordenacao"}).status_code, 403)

    def test_isolamento_de_municipio_linha_e_ciclo(self):
        self.entrar(self.externo)
        self.assertEqual(self.client.get(reverse("ava:gt_sala", args=[self.sala.pk])).status_code, 404)
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Invasão", "revisao": 0}).status_code, 404)
        self.entrar()
        outra = SalaGT.raw_objects.filter(ciclo=self.ciclo).exclude(pk=self.sala.pk).first()
        linha = LinhaPlanoEducacao.raw_objects.filter(sala=outra).first()
        self.assertEqual(self.api({"id": linha.pk, "texto": "Sala errada", "revisao": 0}).status_code, 404)
        self.assertEqual(self.api({"acao": "adicionar", "tipo": "meta", "objetivo_id": linha.pk}).status_code, 404)
        self.assertEqual(self.client.get(reverse("ava:gt_salas"), {"municipio": self.outro.pk}).status_code, 404)

    def test_exporta_rascunho_e_linhas_extras_word_csv(self):
        self.entrar()
        self.api({"id": self.meta.pk, "texto": "=Fórmula;\nTexto com acentuação", "revisao": 0})
        extra = plano.adicionar_linha(self.sala, self.pessoa, "meta", self.principal.pk)
        self.api({"id": extra.pk, "texto": "Meta extra", "revisao": 0})
        url = reverse("ava:gt_sala_documentos", args=[self.sala.pk])
        resposta = self.client.get(url, {"formato": "csv"})
        linhas = list(csv.reader(io.StringIO(resposta.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(linhas[2][2], "'=Fórmula;\nTexto com acentuação")
        self.assertIn([self.sala.objetivo.titulo, "Meta 1.d", "Meta extra"], linhas)
        docx = self.client.get(url, {"formato": "docx"})
        self.assertEqual(docx.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(docx.content)) as pacote:
            xml = pacote.read("word/document.xml").decode()
        self.assertIn("Meta extra", xml)
        self.assertIn("Acesso à Educação Infantil", xml)
        consolidado = self.client.get(reverse("ava:gt_exportar"))
        self.assertEqual(len(consolidado.context["salas_exportar"]), 1)

    def test_ciclo_novo_recebe_tabelas_e_ciclo_encerrado_bloqueia(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("ava:gt_ciclo_novo"), {"nome": "Próximo ciclo", "ativo": "on"})
        self.assertEqual(resposta.status_code, 302)
        ciclo = CicloReferencial.raw_objects.get(nome="Próximo ciclo")
        self.assertEqual(SalaGT.raw_objects.filter(ciclo=ciclo).count(), 19)
        self.entrar()
        self.ciclo.ativo = False
        self.ciclo.save()
        self.assertEqual(self.api({"id": self.meta.pk, "texto": "Encerrado", "revisao": 0}).status_code, 403)
        self.assertEqual(self.client.get(reverse("ava:gt_sala_documentos", args=[self.sala.pk]), {"formato": "docx"}).status_code, 200)

    def test_validacao_e_autenticacao(self):
        self.assertEqual(self.client.get(reverse("ava:gt_salas")).status_code, 302)
        self.entrar()
        for dados in [{"id": self.meta.pk, "texto": "x", "revisao": True}, {"id": self.meta.pk, "texto": "a" * 50001, "revisao": 0}, {"id": self.meta.pk, "texto": "\u0000", "revisao": 0}, []]:
            self.assertEqual(self.api(dados).status_code, 400)

    def test_estrategias_e_indicadores_numerados_abaixo_das_metas(self):
        self.entrar()
        estrategia = self.api({"acao": "adicionar", "tipo": "estrategia", "objetivo_id": self.principal.pk})
        self.assertEqual(estrategia.status_code, 201)
        self.assertEqual(estrategia.json()["linha"]["rotulo"], "Estratégia 1.14")
        for numero in (1, 2):
            resposta = self.api({"acao": "adicionar", "tipo": "indicador", "objetivo_id": self.principal.pk})
            self.assertEqual(resposta.status_code, 201)
            self.assertEqual(resposta.json()["linha"]["rotulo"], f"Indicador 1.{numero}")
            self.assertEqual(resposta.json()["linha"]["texto"], "")
        linhas = plano.linhas_da_sala(self.sala)
        self.assertEqual([l.tipo for l in linhas], ["objetivo"] + ["meta"] * 3 + ["estrategia"] * 14 + ["indicador"] * 2)
        self.assertEqual([l.rotulo for l in linhas[-3:]], ["Estratégia 1.14", "Indicador 1.1", "Indicador 1.2"])
        self.assertEqual(len(plano.linhas_serializadas(self.sala)), len(linhas))
        self.assertTrue(plano.linhas_serializadas(self.sala)[-1]["fim_objetivo"])
        pagina = self.client.get(reverse("ava:gt_sala", args=[self.sala.pk]))
        self.assertContains(pagina, "Adicionar indicador ao Objetivo 1")

    def test_numeracao_independente_por_tipo_e_objetivo(self):
        self.entrar()
        objetivo = self.api({"acao": "adicionar", "tipo": "objetivo"}).json()["linha"]
        # Objetivo 1.2, Estratégia 1.2 e Indicador 1.2 podem coexistir.
        self.assertEqual(objetivo["codigo"], "1.2")
        self.assertEqual(LinhaPlanoEducacao.raw_objects.filter(sala=self.sala, codigo="1.2").count(), 2)
        for tipo, rotulo in [("estrategia", "Estratégia"), ("indicador", "Indicador")]:
            resposta = self.api({"acao": "adicionar", "tipo": tipo, "objetivo_id": objetivo["id"]})
            self.assertEqual(resposta.status_code, 201)
            self.assertEqual(resposta.json()["linha"]["rotulo"], f"{rotulo} 1.2.1")
        self.assertEqual(plano.linhas_da_sala(self.sala)[-1].rotulo, "Indicador 1.2.1")

    def test_autosave_conflito_e_exportacao_dos_novos_tipos(self):
        self.entrar()
        estrategia = LinhaPlanoEducacao.raw_objects.get(sala=self.sala, tipo="estrategia", codigo="1.1")
        indicador = self.api({"acao": "adicionar", "tipo": "indicador", "objetivo_id": self.principal.pk}).json()["linha"]
        for linha_id, texto in [(estrategia.pk, "Estratégia produzida"), (indicador["id"], "Indicador produzido")]:
            self.assertEqual(self.api({"id": linha_id, "texto": texto, "revisao": 0}).status_code, 200)
            self.assertEqual(self.api({"id": linha_id, "texto": "Conflito", "revisao": 0}).status_code, 409)
        url = reverse("ava:gt_sala_documentos", args=[self.sala.pk])
        csv_exportado = self.client.get(url, {"formato": "csv"}).content.decode("utf-8-sig")
        self.assertIn("Estratégia 1.1;Estratégia produzida", csv_exportado)
        self.assertIn("Indicador 1.1;Indicador produzido", csv_exportado)
        self.assertLess(csv_exportado.index("Meta 1.c"), csv_exportado.index("Estratégia 1.1"))
        self.assertLess(csv_exportado.index("Estratégia 1.13"), csv_exportado.index("Indicador 1.1"))
        with zipfile.ZipFile(io.BytesIO(self.client.get(url, {"formato": "docx"}).content)) as pacote:
            xml = pacote.read("word/document.xml").decode()
        self.assertIn("Estratégia produzida", xml)
        self.assertIn("Indicador produzido", xml)

    def test_novos_tipos_respeitam_permissoes_e_escopo(self):
        self.entrar()
        outra_sala = SalaGT.raw_objects.filter(ciclo=self.ciclo).exclude(pk=self.sala.pk).first()
        outro_objetivo = LinhaPlanoEducacao.raw_objects.get(sala=outra_sala, tipo="objetivo")
        for tipo in ["estrategia", "indicador"]:
            self.assertEqual(self.api({"acao": "adicionar", "tipo": tipo, "objetivo_id": outro_objetivo.pk}).status_code, 404)
        InscricaoSalaGT.raw_objects.filter(sala=self.sala, usuario=self.pessoa).update(papel="leitor")
        for tipo in ["estrategia", "indicador"]:
            self.assertEqual(self.api({"acao": "adicionar", "tipo": tipo, "objetivo_id": self.principal.pk}).status_code, 403)
