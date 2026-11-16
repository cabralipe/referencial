"""Presença retroativa, lista nominal e exclusão consistente dos registros."""
from datetime import timedelta
from unittest.mock import patch

from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ava.models import DiarioBordo, DiarioBordoMidia, EncontroCurso, MatriculaCurso, PresencaCurso
from ava.services.attendance_service import registrar_presenca, resumo_frequencia
from ava.tests.test_diario_bordo import DiarioBordoBaseTests, PNG_MINIMO
from core.models import AuditLog


class PresencaRetroativaBaseTests(DiarioBordoBaseTests):
    def setUp(self):
        super().setUp()
        self.matricula = MatriculaCurso.objects.create(
            cliente=self.cliente, curso=self.curso, aluno=self.professor_b,
        )
        self.outra_matricula = MatriculaCurso.objects.create(
            cliente=self.cliente, curso=self.curso, aluno=self.professor_a,
        )
        self.client.force_login(self.professor_a)
        self.data_encontro = timezone.localdate() - timedelta(days=15)

    def dados_diario(self, **extras):
        dados = {
            "municipio": self.cliente.pk, "origem": "no_sistema",
            "curso": self.curso.pk, "data_aula": self.data_encontro.isoformat(),
            "titulo": "Encontro com presença retroativa", "conteudo_trabalhado": "Leitura",
            "modo_frequencia": "retroativa",
        }
        dados.update(extras)
        return dados

    def novo_diario(self, **extras):
        resposta = self.client.post(reverse("ava:diario_novo"), self.dados_diario(**extras))
        self.assertEqual(resposta.status_code, 302)
        diario = DiarioBordo.objects.get(titulo="Encontro com presença retroativa")
        return diario, EncontroCurso.objects.get(diario=diario)

    def chamada(self, encontro, presentes=(), **extras):
        dados = {
            "registro_retroativo": "on", "titulo": encontro.titulo,
            "data_aula": self.data_encontro.isoformat(),
            "presentes": [m.pk for m in presentes],
        }
        dados.update(extras)
        return self.client.post(reverse("ava:frequencia_checklist", args=[encontro.pk]), dados)


class PresencaRetroativaTests(PresencaRetroativaBaseTests):
    def test_modo_retroativo_abre_checklist_com_turma_e_data_passada(self):
        resposta = self.client.post(reverse("ava:diario_novo"), self.dados_diario())
        diario = DiarioBordo.objects.get()
        encontro = EncontroCurso.objects.get(diario=diario)
        self.assertRedirects(resposta, reverse("ava:frequencia_checklist", args=[encontro.pk]))
        self.assertEqual(diario.modo_frequencia, "retroativa")
        self.assertTrue(encontro.registro_retroativo)
        self.assertTrue(encontro.realizado)
        self.assertFalse(encontro.link_aberto)
        self.assertEqual(diario.data_aula, self.data_encontro)
        self.assertEqual(timezone.localtime(diario.created_at).date(), timezone.localdate())
        self.assertEqual(diario.participantes.count(), 2)
        self.assertEqual(diario.participantes_presentes, 0)

    def test_data_futura_retroativa_rejeitada_sem_gravar(self):
        resposta = self.client.post(reverse("ava:diario_novo"), self.dados_diario(
            data_aula=(timezone.localdate() + timedelta(days=1)).isoformat(),
        ))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("data_aula", resposta.context["form"].errors)
        self.assertFalse(DiarioBordo.objects.exists())
        self.assertFalse(EncontroCurso.objects.exists())

    def test_selecao_de_presentes_mostra_lista_nominal_e_atualiza_diario(self):
        diario, encontro = self.novo_diario()
        resposta = self.chamada(encontro, [self.matricula], titulo="Registro atualizado")
        self.assertEqual(resposta.status_code, 302)
        diario.refresh_from_db()
        encontro.refresh_from_db()
        self.assertEqual(diario.titulo, "Registro atualizado")
        self.assertEqual(diario.data_aula, encontro.data_aula)
        self.assertEqual(diario.participantes_presentes, 1)
        self.assertTrue(diario.participantes.get(usuario=self.professor_b).presente)
        self.assertFalse(diario.participantes.get(usuario=self.professor_a).presente)
        self.assertEqual(resumo_frequencia(self.matricula)["percentual"], 100)
        self.assertEqual(resumo_frequencia(self.outra_matricula)["percentual"], 0)
        tela = self.client.get(resposta.url)
        self.assertEqual([m.pk for m in tela.context["presentes_registrados"]], [self.matricula.pk])
        self.assertContains(tela, "Lista nominal de presentes")
        detalhe = self.client.get(reverse("ava:diario_detalhe", args=[diario.pk]))
        self.assertEqual([p.usuario_id for p in detalhe.context["presentes"]], [self.professor_b.pk])
        self.assertEqual([p.usuario_id for p in detalhe.context["ausentes"]], [self.professor_a.pk])
        auditoria = AuditLog.objects.filter(acao="frequencia_checklist").latest("pk")
        self.assertEqual(auditoria.usuario_id, self.professor_a.pk)
        self.assertTrue(auditoria.diff_json["registro_retroativo"])
        self.assertEqual(auditoria.diff_json["data_aula"], self.data_encontro.isoformat())

    def test_corrigir_lista_e_data_nao_duplica_e_preserva_registro_retroativo(self):
        diario, encontro = self.novo_diario()
        self.chamada(encontro, [self.matricula])
        nova_data = (self.data_encontro - timedelta(days=1)).isoformat()
        self.chamada(encontro, [self.outra_matricula], data_aula=nova_data)
        diario.refresh_from_db()
        self.assertEqual(diario.data_aula.isoformat(), nova_data)
        self.assertEqual(diario.participantes_presentes, 1)
        self.assertEqual(PresencaCurso.objects.count(), 2)
        self.assertFalse(diario.participantes.get(usuario=self.professor_b).presente)
        self.assertTrue(diario.participantes.get(usuario=self.professor_a).presente)
        self.assertEqual(diario.modo_frequencia, "retroativa")

    def test_checklist_retroativo_rejeita_futuro_e_nao_altera_chamada(self):
        diario, encontro = self.novo_diario()
        resposta = self.chamada(encontro, [self.matricula], data_aula=(timezone.localdate() + timedelta(days=1)).isoformat())
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("data_aula", resposta.context["form"].errors)
        encontro.refresh_from_db()
        self.assertEqual(encontro.data_aula, self.data_encontro)
        self.assertFalse(PresencaCurso.objects.exists())

    def test_retroativo_fecha_link_previamente_aberto(self):
        diario, encontro = self.novo_diario(modo_frequencia="link")
        self.chamada(encontro, [self.matricula], link_aberto="on", link_expira_em=(timezone.now() - timedelta(days=1)).isoformat())
        encontro.refresh_from_db()
        diario.refresh_from_db()
        self.assertTrue(encontro.registro_retroativo)
        self.assertFalse(encontro.link_aberto)
        self.assertIsNone(encontro.link_expira_em)
        self.assertEqual(diario.modo_frequencia, "retroativa")
        resposta = Client().post(reverse("ava:confirmar_presenca", args=[encontro.token]), {"matricula": self.outra_matricula.pk})
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(PresencaCurso.objects.filter(matricula=self.outra_matricula, presente=True).exists())

    def test_criar_retroativo_na_area_de_frequencia(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse("ava:frequencia_lista") + f"?curso={self.curso.pk}", {
            "registro_retroativo": "on", "titulo": "Chamada antiga",
            "data_aula": self.data_encontro.isoformat(),
        })
        self.assertEqual(resposta.status_code, 302)
        encontro = EncontroCurso.objects.get(titulo="Chamada antiga")
        self.assertTrue(encontro.registro_retroativo)
        self.assertTrue(encontro.realizado)
        self.assertFalse(encontro.link_aberto)
        self.assertContains(self.client.get(resposta.url), self.professor_b.nome)

    def test_aula_futura_comum_nao_entra_antecipadamente_na_frequencia(self):
        diario, encontro = self.novo_diario(modo_frequencia="presencial", data_aula=(timezone.localdate() + timedelta(days=1)).isoformat())
        self.assertFalse(encontro.realizado)
        self.assertEqual(resumo_frequencia(self.matricula)["total"], 0)

    def test_diario_bloqueado_nao_aceita_presenca_por_qr(self):
        diario, encontro = self.novo_diario(modo_frequencia="link")
        diario.status = DiarioBordo.Status.BLOQUEADO
        diario.save()
        Client().post(reverse("ava:confirmar_presenca", args=[encontro.token]), {"matricula": self.matricula.pk})
        self.assertFalse(PresencaCurso.objects.exists())

    def test_presenca_retroativa_exige_curso(self):
        resposta = self.client.post(reverse("ava:diario_novo"), self.dados_diario(
            origem="atividade_externa", curso="", tipo_atividade="oficina", local_realizacao="Escola",
        ))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("curso", resposta.context["form"].errors)
        self.assertFalse(DiarioBordo.objects.exists())


class ExclusaoRegistroTests(PresencaRetroativaBaseTests):
    def test_confirmar_exclusao_por_get_nao_altera_registro(self):
        diario, encontro = self.novo_diario()
        resposta = self.client.get(reverse("ava:diario_excluir", args=[diario.pk]))
        self.assertContains(resposta, "Confirmar exclusão")
        diario.refresh_from_db()
        encontro.refresh_from_db()
        self.assertFalse(diario.is_deleted)
        self.assertFalse(encontro.is_deleted)

    def test_excluir_diario_remove_chamada_lista_e_qr_do_calculo(self):
        diario, encontro = self.novo_diario()
        self.chamada(encontro, [self.matricula])
        storage = InMemoryStorage()
        with patch.object(DiarioBordoMidia._meta.get_field("arquivo"), "storage", storage):
            midia = DiarioBordoMidia.objects.create(
                cliente=self.cliente, diario=diario,
                arquivo=SimpleUploadedFile("foto.png", PNG_MINIMO, content_type="image/png"),
                created_by=self.professor_a,
            )
        resposta = self.client.post(reverse("ava:diario_excluir", args=[diario.pk]))
        self.assertEqual(resposta.status_code, 302)
        diario.refresh_from_db()
        encontro.refresh_from_db()
        self.assertTrue(diario.is_deleted)
        self.assertTrue(encontro.is_deleted)
        self.assertFalse(encontro.link_aberto)
        self.assertFalse(diario.participantes.exists())
        midia.refresh_from_db()
        self.assertTrue(midia.is_deleted)
        self.assertTrue(storage.exists(midia.arquivo.name))
        self.assertEqual(self.client.get(reverse("ava:diario_midia_arquivo", args=[diario.pk, midia.pk])).status_code, 404)
        self.assertEqual(diario.participantes_presentes, 0)
        self.assertFalse(PresencaCurso.objects.filter(encontro=encontro).exists())
        self.assertEqual(resumo_frequencia(self.matricula)["total"], 0)
        self.assertEqual(self.client.get(reverse("ava:diario_detalhe", args=[diario.pk])).status_code, 404)
        self.assertEqual(Client().get(reverse("ava:confirmar_presenca", args=[encontro.token])).status_code, 404)
        self.assertFalse(self.client.get(resposta.url).context["page_obj"].object_list)
        self.assertEqual(self.client.post(reverse("ava:diario_excluir", args=[diario.pk])).status_code, 404)
        self.assertTrue(AuditLog.objects.filter(entidade="ava.DiarioBordo", entidade_id=str(diario.pk), acao="excluido", usuario_id=self.professor_a.pk).exists())

    def test_professor_pode_excluir_sua_chamada_com_confirmacao(self):
        diario, encontro = self.novo_diario()
        self.chamada(encontro, [self.matricula])
        url = reverse("ava:frequencia_remover", args=[encontro.pk])
        self.assertContains(self.client.get(url), "Confirmar exclusão")
        self.assertFalse(EncontroCurso.objects.get(pk=encontro.pk).is_deleted)
        self.assertRedirects(self.client.post(url), reverse("ava:diario_editar", args=[diario.pk]))
        diario.refresh_from_db()
        self.assertFalse(diario.is_deleted)
        self.assertEqual(diario.participantes_presentes, 0)
        self.assertFalse(diario.participantes.exists())
        self.assertEqual(resumo_frequencia(self.matricula)["total"], 0)

    def test_recriar_chamada_gera_novo_token_sem_restaurar_presencas(self):
        diario, encontro = self.novo_diario(modo_frequencia="link")
        registrar_presenca(encontro, self.matricula, self.professor_a, presente=True, origem="checklist")
        token_antigo = encontro.token
        self.client.post(reverse("ava:frequencia_remover", args=[encontro.pk]))
        self.client.post(reverse("ava:diario_editar", args=[diario.pk]), self.dados_diario(modo_frequencia="link"))
        encontro.refresh_from_db()
        diario.refresh_from_db()
        self.assertFalse(encontro.is_deleted)
        self.assertNotEqual(encontro.token, token_antigo)
        self.assertEqual(diario.participantes_presentes, 0)
        self.assertFalse(PresencaCurso.objects.exists())
        self.assertEqual(Client().get(reverse("ava:confirmar_presenca", args=[token_antigo])).status_code, 404)

    def test_professor_de_outra_escola_nao_exclui_diario_ou_chamada(self):
        diario, encontro = self.novo_diario()
        self.client.force_login(self.professor_b)
        self.assertEqual(self.client.post(reverse("ava:diario_excluir", args=[diario.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("ava:frequencia_remover", args=[encontro.pk])).status_code, 404)
        diario.refresh_from_db()
        self.assertFalse(diario.is_deleted)

    def test_diario_bloqueado_nao_pode_ser_excluido_nem_por_admin(self):
        diario, encontro = self.novo_diario()
        diario.status = DiarioBordo.Status.BLOQUEADO
        diario.save()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("ava:diario_excluir", args=[diario.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("ava:frequencia_remover", args=[encontro.pk])).status_code, 403)
        self.assertFalse(DiarioBordo.objects.get(pk=diario.pk).is_deleted)

    def test_outro_professor_da_mesma_escola_nao_pode_excluir_registro(self):
        diario, encontro = self.novo_diario()
        outro = type(self.professor_a).objects.create_user(
            email="outro-professor-retroativo@example.com", nome="Outro professor",
            cliente=self.cliente, escola=self.escola_a, role="professor", password="123456",
        )
        self.client.force_login(outro)
        self.assertEqual(self.client.post(reverse("ava:diario_excluir", args=[diario.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("ava:frequencia_remover", args=[encontro.pk])).status_code, 403)
        self.assertFalse(DiarioBordo.objects.get(pk=diario.pk).is_deleted)
