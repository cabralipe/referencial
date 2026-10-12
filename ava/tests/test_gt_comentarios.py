"""Testes dos comentários/pedidos de ajuste no conteúdo do GT."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from ava.services.gt_comentario_service import ALVO_TIPO, ComentarioGTService
from ava.tests.test_gt_salas import SalaGTBaseTests
from comments.models import Comentario
from core.models import AuditLog, ClienteFeatureFlag


class ComentariosDoGTTests(SalaGTBaseTests):
    """Reaproveitam o app de comentários, ancorados no GT, campo e versão."""

    def setUp(self):
        super().setUp()
        self.trabalho = self.montar_equipe()
        # O cliente nasce com as flags padrão ativas; garantimos o estado.
        ClienteFeatureFlag.objects.update_or_create(
            cliente=self.cliente, flag="ff.comments.enabled", defaults={"ativo": True}
        )

    def test_comentario_fica_ancorado_no_gt_campo_e_versao(self):
        comentario = ComentarioGTService.criar(
            self.trabalho,
            self.coordenador,
            campo="diagnostico_situacao",
            texto="Detalhar a fonte dos dados de alfabetização.",
        )
        self.assertEqual(comentario.alvo_tipo, ALVO_TIPO)
        self.assertEqual(comentario.alvo_id, str(self.trabalho.pk))
        self.assertEqual(comentario.anchor_json["campo"], "diagnostico_situacao")
        self.assertEqual(comentario.anchor_json["version"], self.trabalho.version)
        self.assertEqual(comentario.anchor_json["objetivo"], self.sala.objetivo.codigo)
        self.assertEqual(comentario.autor_id, self.coordenador.pk)
        self.assertFalse(comentario.resolvido)
        self.assertEqual(ComentarioGTService.total_abertos(self.trabalho), 1)
        self.assertTrue(
            AuditLog.raw_objects.filter(
                cliente=self.cliente,
                entidade="comments.Comentario",
                acao="comentario_gt_criado",
            ).exists()
        )

    def test_campo_invalido_e_texto_vazio_sao_recusados(self):
        with self.assertRaises(ValidationError):
            ComentarioGTService.criar(
                self.trabalho, self.coordenador, campo="inexistente", texto="x"
            )
        with self.assertRaises(ValidationError):
            ComentarioGTService.criar(
                self.trabalho, self.coordenador, campo="geral", texto="   "
            )

    def test_quem_nao_participa_do_gt_nao_comenta(self):
        with self.assertRaises(PermissionDenied):
            ComentarioGTService.criar(
                self.trabalho, self.externo, campo="geral", texto="Comentário indevido."
            )

    def test_participante_comenta_mesmo_sem_poder_editar(self):
        comentario = ComentarioGTService.criar(
            self.trabalho, self.participante, campo="metas", texto="Falta indicador na meta 1."
        )
        self.assertEqual(comentario.autor_id, self.participante.pk)

    def test_resolucao_restrita_a_coordenacao_administracao_ou_autor(self):
        comentario = ComentarioGTService.criar(
            self.trabalho, self.participante, campo="geral", texto="Revisar a redação."
        )
        # Outro participante sem papel de gestão não resolve comentário alheio.
        with self.assertRaises(PermissionDenied):
            ComentarioGTService.resolver(self.trabalho, self.relator, comentario.pk)

        resolvido = ComentarioGTService.resolver(self.trabalho, self.coordenador, comentario.pk)
        self.assertTrue(resolvido.resolvido)
        self.assertEqual(resolvido.resolvido_por_id, self.coordenador.pk)
        self.assertIsNotNone(resolvido.resolved_at)
        self.assertEqual(ComentarioGTService.total_abertos(self.trabalho), 0)

    def test_autor_resolve_o_proprio_comentario(self):
        comentario = ComentarioGTService.criar(
            self.trabalho, self.relator, campo="estrategias", texto="Ajustar o prazo."
        )
        resolvido = ComentarioGTService.resolver(self.trabalho, self.relator, comentario.pk)
        self.assertTrue(resolvido.resolvido)

    def test_flag_desligada_bloqueia_comentarios(self):
        ClienteFeatureFlag.objects.update_or_create(
            cliente=self.cliente, flag="ff.comments.enabled", defaults={"ativo": False}
        )
        self.assertFalse(ComentarioGTService.habilitado(self.cliente))
        with self.assertRaises(PermissionDenied):
            ComentarioGTService.criar(
                self.trabalho, self.coordenador, campo="geral", texto="Comentário."
            )

    def test_comentario_pela_tela_aparece_no_quadro(self):
        self.client.force_login(self.coordenador)
        resposta = self.client.post(
            reverse("ava:gt_comentario_criar", kwargs={"sala_id": self.sala.pk}),
            {"campo": "objetivo_proposto", "texto": "Reescrever o verbo do objetivo."},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Reescrever o verbo do objetivo.")
        self.assertContains(resposta, "Proposta de redação do objetivo")

        comentario = Comentario.raw_objects.get(
            alvo_tipo=ALVO_TIPO, alvo_id=str(self.trabalho.pk)
        )
        resposta = self.client.post(
            reverse(
                "ava:gt_comentario_resolver",
                kwargs={"sala_id": self.sala.pk, "comentario_id": comentario.pk},
            ),
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        comentario.refresh_from_db()
        self.assertTrue(comentario.resolvido)

    def test_post_direto_sem_vinculo_e_bloqueado(self):
        self.client.force_login(self.externo)
        resposta = self.client.post(
            reverse("ava:gt_comentario_criar", kwargs={"sala_id": self.sala.pk}),
            {"campo": "geral", "texto": "Tentativa direta."},
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(
            Comentario.raw_objects.filter(
                alvo_tipo=ALVO_TIPO, alvo_id=str(self.trabalho.pk)
            ).exists()
        )

    def test_comentario_de_outro_gt_nao_e_resolvido_pela_sala_errada(self):
        comentario = ComentarioGTService.criar(
            self.trabalho, self.coordenador, campo="geral", texto="Comentário do GT 1."
        )
        from ava.services.gt_sala_service import SalaGTService

        outro_trabalho = SalaGTService.garantir_trabalho(self.outra_sala)
        self.assertIsNone(
            ComentarioGTService.resolver(outro_trabalho, self.admin, comentario.pk)
        )
        comentario.refresh_from_db()
        self.assertFalse(comentario.resolvido)
