"""Testes da aba “Tutorial guiado”: roteiro com estado real e exemplo guiado."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from ava.models.gt_sala import (
    CicloReferencial,
    InscricaoSalaGT,
    ObjetivoReferencial,
    PresencaReuniaoGT,
    ReuniaoGT,
    SalaGT,
    TrabalhoGT,
)
from ava.services.gt_tutorial_service import (
    NOME_CICLO_EXEMPLO,
    PREFIXO_CODIGO_EXEMPLO,
    TutorialGTService,
)
from ava.tests.test_gt_salas import TOTAL_OBJETIVOS, SalaGTBaseTests


class TutorialGuiadoTests(SalaGTBaseTests):
    """O roteiro mostra o que já existe no município e o que falta fazer."""

    def test_roteiro_reflete_o_que_ja_existe_no_municipio(self):
        passos = TutorialGTService.montar_roteiro(self.cliente, self.ciclo)
        por_numero = {passo.numero: passo for passo in passos}

        self.assertEqual(len(passos), 10)
        # Objetivos, ciclo e salas já existem no cenário base.
        self.assertTrue(por_numero[1].concluido)
        self.assertTrue(por_numero[2].concluido)
        self.assertTrue(por_numero[3].concluido)
        # Ainda não há coordenação, diagnóstico, reunião nem documento.
        self.assertFalse(por_numero[4].concluido)
        self.assertFalse(por_numero[6].concluido)
        self.assertFalse(por_numero[7].concluido)
        self.assertFalse(por_numero[10].concluido)
        self.assertIn(f"{TOTAL_OBJETIVOS} objetivo", por_numero[1].situacao)

    def test_passos_apontam_para_as_paginas_certas(self):
        passos = TutorialGTService.montar_roteiro(self.cliente, self.ciclo)
        por_numero = {passo.numero: passo for passo in passos}
        self.assertIn(reverse("ava:gt_objetivos"), por_numero[1].url)
        self.assertIn(reverse("ava:gt_ciclo_novo"), por_numero[2].url)
        self.assertIn(reverse("ava:gt_admin"), por_numero[3].url)
        self.assertIn(
            reverse("ava:gt_sala_inscricoes", kwargs={"sala_id": self.sala.pk}),
            por_numero[4].url,
        )
        self.assertIn(f"municipio={self.cliente.id}", por_numero[1].url)

    def test_roteiro_avanca_conforme_o_trabalho_do_gt(self):
        trabalho = self.montar_equipe()
        self.preencher_conteudo(trabalho)
        passos = TutorialGTService.montar_roteiro(self.cliente, self.ciclo)
        por_numero = {passo.numero: passo for passo in passos}
        self.assertTrue(por_numero[4].concluido)
        self.assertTrue(por_numero[6].concluido)
        self.assertGreaterEqual(TutorialGTService.progresso(passos)["concluidos"], 5)

    def test_passo_bloqueado_quando_falta_pre_requisito(self):
        ciclo_vazio = CicloReferencial.objects.create(
            cliente=self.outro_cliente, nome="Ciclo sem objetivos", ativo=True
        )
        passos = TutorialGTService.montar_roteiro(self.outro_cliente, ciclo_vazio)
        por_numero = {passo.numero: passo for passo in passos}
        self.assertFalse(por_numero[1].concluido)
        self.assertTrue(por_numero[3].bloqueado_por)
        self.assertEqual(por_numero[4].url, "")

    def test_aba_do_tutorial_e_restrita_a_administracao(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("ava:gt_tutorial"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Tutorial guiado")
        self.assertContains(resposta, "Cadastrar os objetivos oficiais do Referencial")
        self.assertContains(resposta, "Criar exemplo de demonstração")

        self.client.force_login(self.participante)
        self.assertEqual(self.client.get(reverse("ava:gt_tutorial")).status_code, 403)

    def test_exemplo_de_demonstracao_e_criado_sem_tocar_nos_dados_oficiais(self):
        ciclo = TutorialGTService.criar_exemplo(self.cliente, self.admin)
        self.assertEqual(ciclo.nome, NOME_CICLO_EXEMPLO)

        salas = SalaGT.raw_objects.filter(is_deleted=False, ciclo=ciclo)
        self.assertEqual(salas.count(), 2)
        for sala in salas:
            self.assertTrue(sala.objetivo.codigo.startswith(PREFIXO_CODIGO_EXEMPLO))
            self.assertTrue(
                TrabalhoGT.raw_objects.filter(is_deleted=False, sala=sala).exists()
            )

        primeira = salas.order_by("objetivo__ordem").first()
        inscricao = InscricaoSalaGT.raw_objects.get(sala=primeira, usuario=self.admin)
        self.assertEqual(inscricao.papel, InscricaoSalaGT.Papel.COORDENACAO)
        self.assertEqual(inscricao.estado, InscricaoSalaGT.Estado.CONFIRMADA)

        reuniao = ReuniaoGT.raw_objects.filter(is_deleted=False, sala=primeira).first()
        self.assertIsNotNone(reuniao)
        self.assertTrue(
            PresencaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao=reuniao).exists()
        )

        # O ciclo e os objetivos oficiais seguem intactos.
        self.assertEqual(
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo).count(),
            TOTAL_OBJETIVOS,
        )
        self.assertEqual(
            ObjetivoReferencial.raw_objects.filter(is_deleted=False, cliente=self.cliente)
            .exclude(codigo__startswith=PREFIXO_CODIGO_EXEMPLO)
            .count(),
            TOTAL_OBJETIVOS,
        )

    def test_criar_exemplo_duas_vezes_nao_duplica(self):
        TutorialGTService.criar_exemplo(self.cliente, self.admin)
        TutorialGTService.criar_exemplo(self.cliente, self.admin)
        self.assertEqual(
            CicloReferencial.raw_objects.filter(
                is_deleted=False, cliente=self.cliente, nome=NOME_CICLO_EXEMPLO
            ).count(),
            1,
        )
        ciclo = TutorialGTService.ciclo_exemplo(self.cliente)
        self.assertEqual(SalaGT.raw_objects.filter(is_deleted=False, ciclo=ciclo).count(), 2)
        self.assertEqual(
            ReuniaoGT.raw_objects.filter(is_deleted=False, sala__ciclo=ciclo).count(), 1
        )

    def test_remover_exemplo_limpa_tudo_e_preserva_o_oficial(self):
        TutorialGTService.criar_exemplo(self.cliente, self.admin)
        removidos = TutorialGTService.remover_exemplo(self.cliente, self.admin)

        self.assertEqual(removidos["ciclo"], 1)
        self.assertEqual(removidos["salas"], 2)
        self.assertEqual(removidos["objetivos"], 2)
        self.assertIsNone(TutorialGTService.ciclo_exemplo(self.cliente))
        self.assertEqual(
            ObjetivoReferencial.raw_objects.filter(
                is_deleted=False, cliente=self.cliente
            ).count(),
            TOTAL_OBJETIVOS,
        )
        self.assertEqual(
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo).count(),
            TOTAL_OBJETIVOS,
        )

    def test_participante_nao_cria_nem_remove_exemplo(self):
        with self.assertRaises(PermissionDenied):
            TutorialGTService.criar_exemplo(self.cliente, self.participante)
        with self.assertRaises(PermissionDenied):
            TutorialGTService.remover_exemplo(self.cliente, self.participante)

        self.client.force_login(self.participante)
        self.assertEqual(
            self.client.post(reverse("ava:gt_tutorial_exemplo_criar")).status_code, 403
        )

    def test_exemplo_pela_tela_cria_e_remove(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(
            reverse("ava:gt_tutorial_exemplo_criar"),
            {"municipio": self.cliente.id},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNotNone(TutorialGTService.ciclo_exemplo(self.cliente))
        self.assertContains(resposta, "Remover o exemplo")

        resposta = self.client.post(
            reverse("ava:gt_tutorial_exemplo_remover"),
            {"municipio": self.cliente.id},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertIsNone(TutorialGTService.ciclo_exemplo(self.cliente))
