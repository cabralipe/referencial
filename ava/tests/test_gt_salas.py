"""Testes das salas de GT: autorização, capacidade, frequência, fluxo e DOCX."""

from __future__ import annotations

import io
import tempfile
import zipfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from ava.models.gt_sala import (
    AtaReuniaoGT,
    CicloReferencial,
    EstrategiaGT,
    InscricaoSalaGT,
    MetaGT,
    ObjetivoReferencial,
    PresencaReuniaoGT,
    ReuniaoGT,
    SalaGT,
    TrabalhoGT,
    VersaoTrabalhoGT,
)
from ava.services.gt_documento_service import DocumentoGTService
from ava.services.gt_reuniao_service import AtaGTService, ReuniaoGTService
from ava.services.gt_sala_service import SalaGTService
from ava.services.gt_trabalho_service import TrabalhoGTService
from core.models import AuditLog, Cliente
from exports.models import ExportJob


User = get_user_model()

TOTAL_OBJETIVOS = 19

_ARMAZENAMENTO_TEMPORARIO = tempfile.mkdtemp(prefix="gt-docs-")

STORAGES_DE_TESTE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _ARMAZENAMENTO_TEMPORARIO},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def texto_do_docx(conteudo: bytes) -> str:
    """Extrai o texto do DOCX direto do XML, sem depender do leitor."""

    with zipfile.ZipFile(io.BytesIO(conteudo)) as pacote:
        partes = [nome for nome in pacote.namelist() if nome == "word/document.xml"]
        assert partes, "DOCX sem word/document.xml"
        xml = pacote.read("word/document.xml").decode("utf-8")
    # Remove as tags preservando a ordem do texto.
    import re

    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    STORAGES=STORAGES_DE_TESTE,
)
class SalaGTBaseTests(TestCase):
    """Cenário comum: um município com o ciclo e os 19 objetivos cadastrados."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Município GT", slug="municipio-gt")
        self.outro_cliente = Cliente.objects.create(nome="Outro GT", slug="outro-gt")

        self.admin = User.objects.create_user(
            email="admin-gt@example.com",
            nome="Ana Administradora",
            password="123456",
            cliente=self.cliente,
            role=User.Role.ADMIN_CLIENTE,
        )
        self.coordenador = User.objects.create_user(
            email="coord-gt@example.com",
            nome="Carla Coordenadora",
            password="123456",
            cliente=self.cliente,
            role=User.Role.MEMBRO_GT,
        )
        self.relator = User.objects.create_user(
            email="relator-gt@example.com",
            nome="Rui Relator",
            password="123456",
            cliente=self.cliente,
            role=User.Role.MEMBRO_GT,
        )
        self.participante = User.objects.create_user(
            email="participante-gt@example.com",
            nome="Paula Participante",
            password="123456",
            cliente=self.cliente,
            role=User.Role.MEMBRO_GT,
        )
        self.externo = User.objects.create_user(
            email="externo-gt@example.com",
            nome="Edu Externo",
            password="123456",
            cliente=self.cliente,
            role=User.Role.MEMBRO_GT,
        )

        self.ciclo = CicloReferencial.objects.create(
            cliente=self.cliente,
            nome="Ciclo 2026",
            ativo=True,
            inscricoes_abertas=True,
            confirmacao_automatica=True,
            min_metas_para_aprovacao=1,
            min_estrategias_para_aprovacao=1,
        )
        for numero in range(1, TOTAL_OBJETIVOS + 1):
            ObjetivoReferencial.objects.create(
                cliente=self.cliente,
                codigo=f"{numero:02d}",
                ordem=numero,
                titulo=f"Objetivo {numero} da educação municipal",
                texto=f"Redação oficial do objetivo {numero}: ampliar a formação continuada.",
            )
        SalaGTService.gerar_salas_do_ciclo(
            self.ciclo, self.admin, criar_gt_ausente=True, capacidade=None
        )
        self.sala = (
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo)
            .select_related("objetivo", "gt", "ciclo", "cliente")
            .order_by("objetivo__ordem")
            .first()
        )
        self.outra_sala = (
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo)
            .exclude(pk=self.sala.pk)
            .select_related("objetivo", "gt", "ciclo", "cliente")
            .order_by("objetivo__ordem")
            .first()
        )

    # -- helpers -------------------------------------------------------
    def inscrever(self, usuario, sala=None, papel=InscricaoSalaGT.Papel.PARTICIPANTE):
        sala = sala or self.sala
        inscricao = SalaGTService.solicitar_inscricao(
            sala, self.admin, usuario_alvo=usuario, forcar_confirmacao=True
        )
        if papel != InscricaoSalaGT.Papel.PARTICIPANTE:
            inscricao = SalaGTService.definir_papel(inscricao, self.admin, papel=papel)
        return inscricao

    def montar_equipe(self, sala=None):
        sala = sala or self.sala
        self.inscrever(self.coordenador, sala, InscricaoSalaGT.Papel.COORDENACAO)
        self.inscrever(self.relator, sala, InscricaoSalaGT.Papel.RELATORIA)
        self.inscrever(self.participante, sala)
        return SalaGTService.garantir_trabalho(sala)

    def preencher_conteudo(self, trabalho, usuario=None):
        usuario = usuario or self.relator
        TrabalhoGTService.salvar_diagnostico(
            trabalho,
            usuario,
            {
                "diagnostico_situacao": "Situação atual com índices de alfabetização.",
                "diagnostico_evidencias": "- Censo escolar 2025\n- Avaliação diagnóstica",
                "diagnostico_desafios": "Infraestrutura insuficiente.",
                "diagnostico_potencialidades": "Equipe experiente e articulada.",
                "diagnostico_publico": "Estudantes dos anos iniciais.",
            },
        )
        TrabalhoGTService.salvar_meta(
            trabalho,
            usuario,
            dados={
                "descricao": "Ampliar a formação continuada em 30%.",
                "indicador": "Percentual de professores formados",
                "prazo": "2026",
            },
        )
        meta = MetaGT.raw_objects.filter(is_deleted=False, trabalho=trabalho).first()
        TrabalhoGTService.salvar_estrategia(
            trabalho,
            usuario,
            dados={
                "descricao": "Realizar oficinas mensais com acompanhamento pedagógico.",
                "responsavel": "Coordenação pedagógica",
                "prazo": "Março a dezembro de 2026",
                "indicador": "Lista de presença das oficinas",
            },
            metas_ids=[meta.pk],
        )
        return trabalho


class GeracaoDeSalasTests(SalaGTBaseTests):
    def test_gera_uma_sala_por_objetivo_sem_duplicar(self):
        self.assertEqual(
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo).count(),
            TOTAL_OBJETIVOS,
        )
        resultado = SalaGTService.gerar_salas_do_ciclo(
            self.ciclo, self.admin, criar_gt_ausente=True
        )
        self.assertEqual(resultado["criadas"], 0)
        self.assertEqual(resultado["existentes"], TOTAL_OBJETIVOS)
        self.assertEqual(
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo).count(),
            TOTAL_OBJETIVOS,
        )

    def test_salas_seguem_a_ordem_oficial_dos_objetivos(self):
        codigos = list(
            SalaGT.raw_objects.filter(is_deleted=False, ciclo=self.ciclo)
            .order_by("objetivo__ordem")
            .values_list("objetivo__codigo", flat=True)
        )
        self.assertEqual(codigos, [f"{n:02d}" for n in range(1, TOTAL_OBJETIVOS + 1)])

    def test_participante_nao_gera_salas(self):
        outro_ciclo = CicloReferencial.objects.create(
            cliente=self.cliente, nome="Ciclo 2027", ativo=True
        )
        with self.assertRaises(PermissionDenied):
            SalaGTService.gerar_salas_do_ciclo(outro_ciclo, self.participante)


class InscricaoECapacidadeTests(SalaGTBaseTests):
    def test_inscricao_confirmada_vira_membro_do_gt(self):
        inscricao = SalaGTService.solicitar_inscricao(self.sala, self.participante)
        self.assertEqual(inscricao.estado, InscricaoSalaGT.Estado.CONFIRMADA)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)
        self.assertTrue(self.sala.gt.membros.filter(pk=self.participante.pk).exists())

    def test_nao_duplica_inscricao_do_mesmo_usuario(self):
        SalaGTService.solicitar_inscricao(self.sala, self.participante)
        with self.assertRaises(ValidationError):
            SalaGTService.solicitar_inscricao(self.sala, self.participante)
        self.assertEqual(
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala=self.sala, usuario=self.participante
            ).count(),
            1,
        )

    def test_limite_de_vagas_envia_para_lista_de_espera(self):
        self.sala.capacidade = 1
        self.sala.save(update_fields=["capacidade"])

        primeira = SalaGTService.solicitar_inscricao(self.sala, self.participante)
        segunda = SalaGTService.solicitar_inscricao(self.sala, self.relator)

        self.assertEqual(primeira.estado, InscricaoSalaGT.Estado.CONFIRMADA)
        self.assertEqual(segunda.estado, InscricaoSalaGT.Estado.LISTA_ESPERA)
        self.assertEqual(segunda.ordem_espera, 1)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)

    def test_reserva_de_vaga_e_atomica_sob_concorrencia(self):
        """Duas reservas simultâneas com uma vaga: só uma pode vencer.

        A reserva é feita por ``UPDATE ... WHERE vagas_ocupadas < capacidade``,
        então duas leituras que viram a sala vazia não conseguem ocupar a mesma
        vaga.
        """

        self.sala.capacidade = 1
        self.sala.save(update_fields=["capacidade"])

        copia_a = SalaGT.raw_objects.get(pk=self.sala.pk)
        copia_b = SalaGT.raw_objects.get(pk=self.sala.pk)
        self.assertEqual(copia_a.vagas_ocupadas, 0)
        self.assertEqual(copia_b.vagas_ocupadas, 0)

        self.assertTrue(SalaGTService._reservar_vaga(copia_a))
        self.assertFalse(SalaGTService._reservar_vaga(copia_b))

        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)

    def test_sala_lotada_sem_lista_de_espera_recusa(self):
        self.sala.capacidade = 1
        self.sala.permite_lista_espera = False
        self.sala.save(update_fields=["capacidade", "permite_lista_espera"])
        SalaGTService.solicitar_inscricao(self.sala, self.participante)
        with self.assertRaises(ValidationError):
            SalaGTService.solicitar_inscricao(self.sala, self.relator)

    def test_promocao_da_lista_de_espera_respeita_vaga_e_ordem(self):
        self.sala.capacidade = 1
        self.sala.save(update_fields=["capacidade"])
        SalaGTService.solicitar_inscricao(self.sala, self.participante)
        espera_1 = SalaGTService.solicitar_inscricao(self.sala, self.relator)
        espera_2 = SalaGTService.solicitar_inscricao(self.sala, self.externo)
        self.assertEqual([espera_1.ordem_espera, espera_2.ordem_espera], [1, 2])

        # Sem vaga livre, ninguém é promovido (nada é prometido antes da vaga).
        self.assertEqual(SalaGTService.promover_lista_espera(self.sala, self.admin), [])

        confirmada = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.participante)
        SalaGTService.cancelar_inscricao(confirmada, self.participante)
        self.sala.refresh_from_db()

        promovidas = SalaGTService.promover_lista_espera(self.sala, self.admin)
        self.assertEqual(len(promovidas), 1)
        self.assertEqual(promovidas[0].usuario_id, self.relator.pk)
        espera_2.refresh_from_db()
        self.assertEqual(espera_2.estado, InscricaoSalaGT.Estado.LISTA_ESPERA)

    def test_limite_de_gts_por_participante(self):
        self.ciclo.max_salas_por_participante = 1
        self.ciclo.save(update_fields=["max_salas_por_participante"])
        # Recarrega as duas salas para que leiam a regra atual do ciclo.
        self.sala.refresh_from_db()
        self.outra_sala.refresh_from_db()
        SalaGTService.solicitar_inscricao(self.sala, self.participante)
        with self.assertRaises(ValidationError):
            SalaGTService.solicitar_inscricao(self.outra_sala, self.participante)

    def test_inscricao_com_inscricoes_fechadas_e_recusada(self):
        self.ciclo.inscricoes_abertas = False
        self.ciclo.save(update_fields=["inscricoes_abertas"])
        self.sala.refresh_from_db()
        with self.assertRaises(ValidationError):
            SalaGTService.solicitar_inscricao(self.sala, self.participante)

    def test_participante_nao_inscreve_outra_pessoa(self):
        with self.assertRaises(PermissionDenied):
            SalaGTService.solicitar_inscricao(
                self.sala, self.participante, usuario_alvo=self.externo
            )

    def test_cancelamento_libera_vaga(self):
        self.sala.capacidade = 2
        self.sala.save(update_fields=["capacidade"])
        inscricao = SalaGTService.solicitar_inscricao(self.sala, self.participante)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)
        SalaGTService.cancelar_inscricao(inscricao, self.participante)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 0)
        self.assertFalse(self.sala.gt.membros.filter(pk=self.participante.pk).exists())

    def test_ciclo_sem_confirmacao_automatica_deixa_pedido_pendente(self):
        self.ciclo.confirmacao_automatica = False
        self.ciclo.save(update_fields=["confirmacao_automatica"])
        self.sala.refresh_from_db()
        inscricao = SalaGTService.solicitar_inscricao(self.sala, self.participante)
        self.assertEqual(inscricao.estado, InscricaoSalaGT.Estado.SOLICITADA)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 0)

        confirmada = SalaGTService.aprovar_inscricao(inscricao, self.admin)
        self.assertEqual(confirmada.estado, InscricaoSalaGT.Estado.CONFIRMADA)
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.vagas_ocupadas, 1)


class PapeisEAutorizacaoTests(SalaGTBaseTests):
    def test_relator_edita_apenas_o_gt_autorizado(self):
        trabalho = self.montar_equipe()
        TrabalhoGTService.salvar_diagnostico(
            trabalho, self.relator, {"diagnostico_situacao": "Situação registrada."}
        )
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.diagnostico_situacao, "Situação registrada.")

        outro_trabalho = SalaGTService.garantir_trabalho(self.outra_sala)
        with self.assertRaises(PermissionDenied):
            TrabalhoGTService.salvar_diagnostico(
                outro_trabalho, self.relator, {"diagnostico_situacao": "Invasão."}
            )

    def test_participante_sem_autorizacao_nao_edita_conteudo(self):
        trabalho = self.montar_equipe()
        with self.assertRaises(PermissionDenied):
            TrabalhoGTService.salvar_diagnostico(
                trabalho, self.participante, {"diagnostico_situacao": "Tentativa."}
            )

    def test_participante_edita_quando_a_sala_permite(self):
        trabalho = self.montar_equipe()
        self.sala.participantes_editam_conteudo = True
        self.sala.save(update_fields=["participantes_editam_conteudo"])
        trabalho = TrabalhoGT.raw_objects.get(pk=trabalho.pk)
        TrabalhoGTService.salvar_diagnostico(
            trabalho, self.participante, {"diagnostico_situacao": "Colaboração permitida."}
        )
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.diagnostico_situacao, "Colaboração permitida.")

    def test_relator_nao_concede_papel_a_si_mesmo(self):
        self.montar_equipe()
        inscricao = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.relator)
        with self.assertRaises(PermissionDenied):
            SalaGTService.definir_papel(
                inscricao, self.relator, papel=InscricaoSalaGT.Papel.COORDENACAO
            )

    def test_coordenacao_nao_define_coordenacao(self):
        self.montar_equipe()
        inscricao = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.participante)
        with self.assertRaises(PermissionDenied):
            SalaGTService.definir_papel(
                inscricao, self.coordenador, papel=InscricaoSalaGT.Papel.COORDENACAO
            )
        atualizada = SalaGTService.definir_papel(
            inscricao, self.coordenador, papel=InscricaoSalaGT.Papel.RELATORIA
        )
        self.assertEqual(atualizada.papel, InscricaoSalaGT.Papel.RELATORIA)

    def test_coordenacao_de_outro_gt_nao_gerencia_inscricoes(self):
        self.montar_equipe()
        inscricao = SalaGTService.solicitar_inscricao(
            self.outra_sala, self.admin, usuario_alvo=self.externo, forcar_confirmacao=True
        )
        with self.assertRaises(PermissionDenied):
            SalaGTService.cancelar_inscricao(inscricao, self.coordenador)


class ApiEUrlsTests(SalaGTBaseTests):
    def test_sala_restrita_a_quem_tem_vinculo(self):
        self.montar_equipe()
        self.client.force_login(self.externo)
        resposta = self.client.get(reverse("ava:gt_sala", kwargs={"sala_id": self.sala.pk}))
        self.assertEqual(resposta.status_code, 403)

    def test_catalogo_de_salas_fica_acessivel_sem_vinculo(self):
        self.client.force_login(self.externo)
        resposta = self.client.get(reverse("ava:gt_salas"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Objetivo 01")

    def test_participante_nao_abre_area_administrativa(self):
        self.client.force_login(self.participante)
        resposta = self.client.get(reverse("ava:gt_admin"))
        self.assertEqual(resposta.status_code, 403)

    def test_post_direto_de_diagnostico_sem_vinculo_e_bloqueado(self):
        trabalho = self.montar_equipe()
        self.client.force_login(self.externo)
        resposta = self.client.post(
            reverse("ava:gt_trabalho_diagnostico", kwargs={"sala_id": self.sala.pk}),
            {"diagnostico_situacao": "Tentativa direta na API."},
        )
        self.assertEqual(resposta.status_code, 403)
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.diagnostico_situacao, "")

    def test_post_direto_de_frequencia_sem_permissao_e_bloqueado(self):
        self.montar_equipe()
        reuniao = self.criar_reuniao()
        self.client.force_login(self.participante)
        resposta = self.client.post(
            reverse("ava:gt_frequencia_validar", kwargs={"reuniao_id": reuniao.pk})
        )
        self.assertEqual(resposta.status_code, 403)
        reuniao.refresh_from_db()
        self.assertFalse(reuniao.frequencia_validada)

    def test_download_de_documento_de_outro_gt_e_bloqueado(self):
        trabalho = self.montar_equipe()
        self.preencher_conteudo(trabalho)
        job = DocumentoGTService.gerar_documento_objetivo(self.sala, self.coordenador)

        self.client.force_login(self.externo)
        resposta = self.client.get(
            reverse("ava:gt_documento_download", kwargs={"job_id": job.pk})
        )
        self.assertEqual(resposta.status_code, 403)

        self.client.force_login(self.coordenador)
        resposta = self.client.get(
            reverse("ava:gt_documento_download", kwargs={"job_id": job.pk})
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Cache-Control"], "private, no-store")

    def criar_reuniao(self, sala=None):
        sala = sala or self.sala
        reuniao = ReuniaoGT(
            cliente_id=sala.cliente_id,
            sala=sala,
            titulo="Primeira reunião do GT",
            data_hora=timezone.now() - timedelta(days=1),
            modalidade=ReuniaoGT.Modalidade.PRESENCIAL,
            local="Secretaria de Educação",
            pauta="Alinhamento inicial",
            responsavel_registro=self.coordenador,
        )
        return ReuniaoGTService.salvar_reuniao(reuniao, self.coordenador, criando=True)


class FrequenciaTests(SalaGTBaseTests):
    def setUp(self):
        super().setUp()
        self.trabalho = self.montar_equipe()
        reuniao = ReuniaoGT(
            cliente_id=self.sala.cliente_id,
            sala=self.sala,
            titulo="Reunião de diagnóstico",
            data_hora=timezone.now() - timedelta(days=2),
            modalidade=ReuniaoGT.Modalidade.ONLINE,
            link="https://exemplo.gov.br/reuniao",
            responsavel_registro=self.coordenador,
        )
        self.reuniao = ReuniaoGTService.salvar_reuniao(reuniao, self.coordenador, criando=True)

    def test_lista_de_presenca_vem_dos_membros_confirmados(self):
        usuarios = set(
            PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao=self.reuniao
            ).values_list("usuario_id", flat=True)
        )
        self.assertEqual(
            usuarios, {self.coordenador.pk, self.relator.pk, self.participante.pk}
        )
        self.assertNotIn(self.externo.pk, usuarios)

    def test_presenca_nao_e_inferida_por_acesso(self):
        situacoes = set(
            PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao=self.reuniao
            ).values_list("situacao", flat=True)
        )
        self.assertEqual(situacoes, {PresencaReuniaoGT.Situacao.AUSENTE})

    def test_lancamento_valida_justificativa_de_ausencia(self):
        with self.assertRaises(ValidationError):
            ReuniaoGTService.lancar_presencas(
                self.reuniao,
                self.coordenador,
                {
                    self.participante.pk: {
                        "situacao": PresencaReuniaoGT.Situacao.JUSTIFICADA,
                        "justificativa": "",
                    }
                },
            )

    def test_lancamento_ignora_quem_nao_e_membro(self):
        ReuniaoGTService.lancar_presencas(
            self.reuniao,
            self.coordenador,
            {self.externo.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE}},
        )
        self.assertFalse(
            PresencaReuniaoGT.raw_objects.filter(
                is_deleted=False, reuniao=self.reuniao, usuario=self.externo
            ).exists()
        )

    def test_validacao_bloqueia_alteracao_e_exige_justificativa_para_reabrir(self):
        ReuniaoGTService.lancar_presencas(
            self.reuniao,
            self.coordenador,
            {
                self.coordenador.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE},
                self.relator.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE},
                self.participante.pk: {
                    "situacao": PresencaReuniaoGT.Situacao.JUSTIFICADA,
                    "justificativa": "Atestado apresentado",
                },
            },
        )
        resumo = self.reuniao.resumo_frequencia()
        self.assertEqual(resumo["presentes"], 2)
        self.assertEqual(resumo["justificadas"], 1)

        ReuniaoGTService.validar_frequencia(self.reuniao, self.coordenador)
        self.reuniao.refresh_from_db()
        self.assertTrue(self.reuniao.frequencia_validada)
        self.assertEqual(self.reuniao.situacao, ReuniaoGT.Situacao.REALIZADA)

        with self.assertRaises(ValidationError):
            ReuniaoGTService.lancar_presencas(
                self.reuniao,
                self.coordenador,
                {self.participante.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE}},
            )
        with self.assertRaises(ValidationError):
            ReuniaoGTService.reabrir_frequencia(self.reuniao, self.coordenador, justificativa="")

        ReuniaoGTService.reabrir_frequencia(
            self.reuniao, self.coordenador, justificativa="Erro de digitação na presença."
        )
        self.reuniao.refresh_from_db()
        self.assertFalse(self.reuniao.frequencia_validada)
        self.assertTrue(
            AuditLog.raw_objects.filter(
                cliente=self.cliente,
                entidade="ava.ReuniaoGT",
                entidade_id=str(self.reuniao.pk),
                acao="frequencia_reaberta",
            ).exists()
        )

    def test_relator_lanca_mas_nao_valida_frequencia(self):
        ReuniaoGTService.lancar_presencas(
            self.reuniao,
            self.relator,
            {self.relator.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE}},
        )
        with self.assertRaises(PermissionDenied):
            ReuniaoGTService.validar_frequencia(self.reuniao, self.relator)

    def test_participante_nao_lanca_frequencia(self):
        with self.assertRaises(PermissionDenied):
            ReuniaoGTService.lancar_presencas(
                self.reuniao,
                self.participante,
                {self.participante.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE}},
            )

    def test_participante_consulta_apenas_a_propria_frequencia(self):
        ReuniaoGTService.lancar_presencas(
            self.reuniao,
            self.coordenador,
            {
                self.coordenador.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE},
                self.participante.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE},
            },
        )
        self.client.force_login(self.participante)
        resposta = self.client.get(
            reverse("ava:gt_reuniao", kwargs={"reuniao_id": self.reuniao.pk})
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.participante.nome)
        # A lista servida contém apenas o próprio registro: a frequência de
        # terceiros não é exposta. (O nome de quem lançou a presença aparece,
        # de propósito, como rastreabilidade do próprio registro.)
        self.assertEqual(
            [presenca.usuario_id for presenca in resposta.context["presencas"]],
            [self.participante.pk],
        )
        self.assertIsNone(resposta.context["resumo"])


class FluxoDeConteudoTests(SalaGTBaseTests):
    def setUp(self):
        super().setUp()
        self.trabalho = self.montar_equipe()

    def test_aprovacao_exige_validacoes_minimas(self):
        TrabalhoGTService.submeter_revisao(self.trabalho, self.relator)
        self.trabalho.refresh_from_db()
        with self.assertRaises(ValidationError) as contexto:
            TrabalhoGTService.aprovar(self.trabalho, self.coordenador)
        mensagens = " ".join(contexto.exception.messages)
        self.assertIn("diagnóstico", mensagens.lower())
        self.assertIn("meta", mensagens.lower())

    def test_diagnostico_nao_aplicavel_satisfaz_a_validacao(self):
        TrabalhoGTService.salvar_diagnostico(
            self.trabalho, self.relator, {"diagnostico_nao_aplicavel": True}
        )
        self.trabalho.refresh_from_db()
        pendencias = TrabalhoGTService.pendencias_para_aprovacao(self.trabalho)
        self.assertFalse(any("diagnóstico" in item.lower() for item in pendencias))

    def test_fluxo_completo_congela_versao_e_bloqueia_edicao(self):
        self.preencher_conteudo(self.trabalho)
        self.trabalho.refresh_from_db()
        TrabalhoGTService.submeter_revisao(self.trabalho, self.relator)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.estado, TrabalhoGT.Estado.EM_REVISAO)

        # Em revisão o conteúdo não aceita edição.
        with self.assertRaises(ValidationError):
            TrabalhoGTService.salvar_quadro(
                self.trabalho, self.relator, {"objetivo_proposto": "Nova redação."}
            )

        TrabalhoGTService.solicitar_ajustes(
            self.trabalho, self.coordenador, parecer="Detalhar os indicadores."
        )
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.estado, TrabalhoGT.Estado.AJUSTES_SOLICITADOS)

        TrabalhoGTService.salvar_quadro(
            self.trabalho, self.relator, {"objetivo_proposto": "Redação revisada pelo GT."}
        )
        self.trabalho.refresh_from_db()
        TrabalhoGTService.submeter_revisao(self.trabalho, self.relator)
        self.trabalho.refresh_from_db()
        TrabalhoGTService.aprovar(self.trabalho, self.coordenador)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.estado, TrabalhoGT.Estado.APROVADO)

        versoes = VersaoTrabalhoGT.raw_objects.filter(
            is_deleted=False, trabalho=self.trabalho
        ).order_by("numero")
        self.assertGreaterEqual(versoes.count(), 2)
        aprovada = versoes.filter(estado=TrabalhoGT.Estado.APROVADO).first()
        self.assertIsNotNone(aprovada)
        self.assertEqual(
            aprovada.conteudo_json["objetivo"]["proposta_do_gt"],
            "Redação revisada pelo GT.",
        )

        with self.assertRaises(ValidationError):
            TrabalhoGTService.salvar_quadro(
                self.trabalho, self.relator, {"objetivo_proposto": "Alteração proibida."}
            )

        TrabalhoGTService.publicar(self.trabalho, self.coordenador)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.estado, TrabalhoGT.Estado.PUBLICADO)
        self.assertTrue(self.trabalho.consolidavel)

    def test_reabertura_apenas_pela_administracao_com_justificativa(self):
        self.preencher_conteudo(self.trabalho)
        self.trabalho.refresh_from_db()
        TrabalhoGTService.submeter_revisao(self.trabalho, self.relator)
        self.trabalho.refresh_from_db()
        TrabalhoGTService.aprovar(self.trabalho, self.coordenador)
        self.trabalho.refresh_from_db()

        with self.assertRaises(PermissionDenied):
            TrabalhoGTService.reabrir(
                self.trabalho, self.coordenador, justificativa="Quero editar."
            )
        with self.assertRaises(ValidationError):
            TrabalhoGTService.reabrir(self.trabalho, self.admin, justificativa="")

        TrabalhoGTService.reabrir(
            self.trabalho, self.admin, justificativa="Correção solicitada pelo conselho."
        )
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.estado, TrabalhoGT.Estado.RASCUNHO)
        self.assertTrue(
            AuditLog.raw_objects.filter(
                cliente=self.cliente,
                entidade="ava.TrabalhoGT",
                entidade_id=str(self.trabalho.pk),
                acao="reaberto",
            ).exists()
        )

    def test_edicao_concorrente_avisa_conflito(self):
        TrabalhoGTService.salvar_quadro(
            self.trabalho, self.relator, {"objetivo_proposto": "Primeira gravação."}
        )
        self.trabalho.refresh_from_db()
        with self.assertRaises(ValidationError):
            TrabalhoGTService.salvar_quadro(
                self.trabalho,
                self.relator,
                {"objetivo_proposto": "Gravação a partir de tela antiga."},
                version_esperada=self.trabalho.version - 1,
            )

    def test_estrategia_fica_vinculada_as_metas_escolhidas(self):
        self.preencher_conteudo(self.trabalho)
        estrategia = EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho=self.trabalho
        ).first()
        meta = MetaGT.raw_objects.filter(is_deleted=False, trabalho=self.trabalho).first()
        self.assertEqual(list(estrategia.metas.values_list("id", flat=True)), [meta.pk])

    def test_estrategia_nao_aceita_meta_de_outro_gt(self):
        self.preencher_conteudo(self.trabalho)
        outro_trabalho = SalaGTService.garantir_trabalho(self.outra_sala)
        TrabalhoGTService.salvar_meta(
            outro_trabalho, self.admin, dados={"descricao": "Meta de outro GT."}
        )
        meta_alheia = MetaGT.raw_objects.filter(
            is_deleted=False, trabalho=outro_trabalho
        ).first()
        estrategia = EstrategiaGT.raw_objects.filter(
            is_deleted=False, trabalho=self.trabalho
        ).first()
        TrabalhoGTService.salvar_estrategia(
            self.trabalho,
            self.relator,
            estrategia=estrategia,
            dados={"descricao": estrategia.descricao},
            metas_ids=[meta_alheia.pk],
        )
        estrategia.refresh_from_db()
        self.assertEqual(list(estrategia.metas.all()), [])

    def test_objetivo_oficial_permanece_separado_da_proposta(self):
        TrabalhoGTService.salvar_quadro(
            self.trabalho, self.relator, {"objetivo_proposto": "Proposta do GT."}
        )
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.objetivo_proposto, "Proposta do GT.")
        self.assertNotIn("Proposta do GT", self.sala.objetivo.texto)


class AtaTests(SalaGTBaseTests):
    def setUp(self):
        super().setUp()
        self.trabalho = self.montar_equipe()
        reuniao = ReuniaoGT(
            cliente_id=self.sala.cliente_id,
            sala=self.sala,
            titulo="Reunião com deliberações",
            data_hora=timezone.now() - timedelta(days=3),
            modalidade=ReuniaoGT.Modalidade.PRESENCIAL,
            local="Escola Municipal Central",
            pauta="1. Diagnóstico\n2. Metas",
            responsavel_registro=self.coordenador,
        )
        self.reuniao = ReuniaoGTService.salvar_reuniao(reuniao, self.coordenador, criando=True)

    def test_minuta_usa_modelo_versionado_e_preenche_dados_seguros(self):
        ata = AtaGTService.garantir_minuta(self.reuniao, self.relator)
        self.assertEqual(ata.estado, AtaReuniaoGT.Estado.MINUTA)
        self.assertEqual(ata.pauta, "1. Diagnóstico\n2. Metas")
        self.assertEqual(ata.modelo_versao, 1)
        self.assertTrue(ata.estrutura_json["secoes"])
        self.assertEqual(ata.sintese, "")

    def test_modelo_publicado_nao_altera_ata_ja_gerada(self):
        from ava.services.gt_reuniao_service import ModeloAtaGTService

        ModeloAtaGTService.publicar_versao(
            self.cliente.id,
            self.admin,
            nome="Ata institucional",
            secoes=[{"chave": "pauta", "titulo": "Pauta", "orientacao": ""}],
        )
        ata = AtaGTService.garantir_minuta(self.reuniao, self.relator)
        self.assertEqual(ata.modelo_nome, "Ata institucional")
        self.assertEqual(ata.modelo_versao, 1)

        ModeloAtaGTService.publicar_versao(
            self.cliente.id,
            self.admin,
            nome="Ata institucional",
            secoes=[
                {"chave": "pauta", "titulo": "Pauta revisada", "orientacao": ""},
                {"chave": "sintese", "titulo": "Síntese", "orientacao": ""},
            ],
        )
        ata.refresh_from_db()
        self.assertEqual(ata.modelo_versao, 1)
        self.assertEqual(ata.estrutura_json["secoes"][0]["titulo"], "Pauta")

    def test_minuta_e_ata_validada_sao_distinguiveis(self):
        ata = AtaGTService.garantir_minuta(self.reuniao, self.relator)
        with self.assertRaises(ValidationError):
            AtaGTService.validar(ata, self.coordenador)

        AtaGTService.salvar(
            ata,
            self.relator,
            {
                "sintese": "O grupo discutiu o diagnóstico e aprovou as metas.",
                "decisoes": "Aprovada a meta 1.",
            },
        )
        ata.refresh_from_db()
        self.assertFalse(ata.validada)

        with self.assertRaises(PermissionDenied):
            AtaGTService.validar(ata, self.participante)

        AtaGTService.validar(ata, self.coordenador)
        ata.refresh_from_db()
        self.assertTrue(ata.validada)
        with self.assertRaises(ValidationError):
            AtaGTService.salvar(ata, self.relator, {"sintese": "Alteração proibida."})

        AtaGTService.reabrir(ata, self.coordenador, justificativa="Ajuste de redação.")
        ata.refresh_from_db()
        self.assertEqual(ata.estado, AtaReuniaoGT.Estado.EM_REVISAO)


class DocumentosDocxTests(SalaGTBaseTests):
    def setUp(self):
        super().setUp()
        self.trabalho = self.montar_equipe()
        self.preencher_conteudo(self.trabalho)
        self.trabalho.refresh_from_db()

    def test_documento_do_objetivo_e_docx_valido_com_acentuacao(self):
        conteudo = DocumentoGTService.render_objetivo(self.sala, self.trabalho)
        self.assertTrue(conteudo.startswith(b"PK"))
        texto = texto_do_docx(conteudo)
        self.assertIn("Documento do objetivo do Referencial", texto)
        self.assertIn("Diagnóstico", texto)
        self.assertIn("Metas e resultados esperados", texto)
        self.assertIn("Estratégias e ações", texto)
        self.assertIn("Redação oficial do objetivo 1", texto)
        self.assertIn("Ampliar a formação continuada em 30%.", texto)
        self.assertIn("Realizar oficinas mensais", texto)

    def test_geracao_registra_exportjob_e_arquivo_privado(self):
        job = DocumentoGTService.gerar_documento_objetivo(self.sala, self.coordenador)
        self.assertEqual(job.alvo_tipo, ExportJob.AlvoTipo.GT_OBJETIVO)
        self.assertEqual(job.status, ExportJob.Status.DONE)
        self.assertEqual(job.formato, ExportJob.Formato.DOCX)
        self.assertEqual(job.url_resultado, "")
        nome = DocumentoGTService.nome_do_arquivo(job)
        self.assertTrue(nome.endswith(".docx"))
        self.assertIn("obj-01", nome)
        for parte in (self.coordenador.nome, self.coordenador.email):
            self.assertNotIn(parte, nome)
        with DocumentoGTService.abrir_arquivo(job) as arquivo:
            self.assertTrue(arquivo.read(2).startswith(b"PK"))

    def test_ata_gerada_identifica_minuta_e_ata_validada(self):
        reuniao = ReuniaoGT(
            cliente_id=self.sala.cliente_id,
            sala=self.sala,
            titulo="Reunião ordinária",
            data_hora=timezone.now() - timedelta(days=1),
            modalidade=ReuniaoGT.Modalidade.PRESENCIAL,
            local="Secretaria",
            responsavel_registro=self.coordenador,
        )
        reuniao = ReuniaoGTService.salvar_reuniao(reuniao, self.coordenador, criando=True)
        ReuniaoGTService.lancar_presencas(
            reuniao,
            self.coordenador,
            {
                self.coordenador.pk: {"situacao": PresencaReuniaoGT.Situacao.PRESENTE},
                self.participante.pk: {
                    "situacao": PresencaReuniaoGT.Situacao.JUSTIFICADA,
                    "justificativa": "Atestado médico apresentado",
                },
            },
        )
        ata = AtaGTService.garantir_minuta(reuniao, self.coordenador)
        AtaGTService.salvar(
            ata, self.coordenador, {"sintese": "Discussão sobre as metas do objetivo."}
        )
        ata.refresh_from_db()

        texto = texto_do_docx(DocumentoGTService.render_ata(reuniao, ata))
        self.assertIn("Minuta de ata de reunião", texto)
        self.assertIn("Discussão sobre as metas do objetivo.", texto)
        self.assertIn(self.coordenador.nome, texto)
        # A ata registra presença/ausência, nunca a justificativa pessoal.
        self.assertNotIn("Atestado médico apresentado", texto)

        AtaGTService.validar(ata, self.coordenador)
        ata.refresh_from_db()
        texto_validado = texto_do_docx(DocumentoGTService.render_ata(reuniao, ata))
        self.assertIn("Ata de reunião", texto_validado)
        self.assertNotIn("Minuta de ata de reunião", texto_validado)

    def test_consolidacao_traz_os_19_objetivos_na_ordem_e_marca_pendentes(self):
        TrabalhoGTService.submeter_revisao(self.trabalho, self.relator)
        self.trabalho.refresh_from_db()
        TrabalhoGTService.aprovar(self.trabalho, self.coordenador)
        self.trabalho.refresh_from_db()

        conteudo, resumo = DocumentoGTService.render_consolidado(self.ciclo)
        self.assertEqual(resumo["total"], TOTAL_OBJETIVOS)
        self.assertEqual(resumo["consolidados"], 1)
        self.assertEqual(resumo["pendentes"], TOTAL_OBJETIVOS - 1)

        texto = texto_do_docx(conteudo)
        posicoes = []
        for numero in range(1, TOTAL_OBJETIVOS + 1):
            marcador = f"Objetivo {numero:02d} —"
            self.assertIn(marcador, texto, f"objetivo {numero} ausente da consolidação")
            posicoes.append(texto.index(marcador))
        self.assertEqual(posicoes, sorted(posicoes), "objetivos fora da ordem oficial")

        self.assertIn("Pendente de consolidação", texto)
        self.assertIn("Ampliar a formação continuada em 30%.", texto)
        # Nenhum dado pessoal de frequência entra na consolidação.
        self.assertNotIn(self.participante.email, texto)

    def test_consolidacao_nao_inclui_rascunho_de_conteudo(self):
        conteudo, resumo = DocumentoGTService.render_consolidado(self.ciclo)
        self.assertEqual(resumo["consolidados"], 0)
        texto = texto_do_docx(conteudo)
        self.assertNotIn("Ampliar a formação continuada em 30%.", texto)
        self.assertIn("Pendente de consolidação", texto)

    def test_consolidacao_restrita_ao_acompanhamento_institucional(self):
        with self.assertRaises(PermissionDenied):
            DocumentoGTService.gerar_consolidado(self.ciclo, self.coordenador)
        job = DocumentoGTService.gerar_consolidado(self.ciclo, self.admin)
        self.assertEqual(job.alvo_tipo, ExportJob.AlvoTipo.GT_CONSOLIDADO)
        self.assertEqual(job.payload_json["resumo"]["total"], TOTAL_OBJETIVOS)


class IsolamentoEntreClientesTests(SalaGTBaseTests):
    def test_sala_de_outro_municipio_nao_aparece_nem_abre(self):
        objetivo = ObjetivoReferencial.objects.create(
            cliente=self.outro_cliente, codigo="01", ordem=1, titulo="Objetivo de outro município"
        )
        from curriculum.models import GT

        gt = GT.objects.create(cliente=self.outro_cliente, nome="GT externo", etapa="I")
        ciclo = CicloReferencial.objects.create(
            cliente=self.outro_cliente, nome="Ciclo externo", ativo=True
        )
        sala_externa = SalaGT.objects.create(
            cliente=self.outro_cliente, ciclo=ciclo, objetivo=objetivo, gt=gt
        )

        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("ava:gt_salas"))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, "Objetivo de outro município")

        resposta = self.client.get(
            reverse("ava:gt_sala", kwargs={"sala_id": sala_externa.pk})
        )
        self.assertEqual(resposta.status_code, 404)

    def test_mover_participante_entre_ciclos_diferentes_e_bloqueado(self):
        self.montar_equipe()
        outro_ciclo = CicloReferencial.objects.create(
            cliente=self.cliente, nome="Ciclo 2027", ativo=True, inscricoes_abertas=True
        )
        objetivo = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=self.cliente
        ).order_by("ordem").first()
        from curriculum.models import GT

        gt = GT.objects.create(cliente=self.cliente, nome="GT do ciclo 2027", etapa="II")
        destino = SalaGT.objects.create(
            cliente=self.cliente, ciclo=outro_ciclo, objetivo=objetivo, gt=gt
        )
        inscricao = InscricaoSalaGT.raw_objects.get(sala=self.sala, usuario=self.participante)
        with self.assertRaises(ValidationError):
            SalaGTService.mover_inscricao(inscricao, destino, self.admin)


class ObjetivosAdministraveisTests(SalaGTBaseTests):
    def test_importacao_por_csv_atualiza_sem_duplicar(self):
        self.client.force_login(self.admin)
        csv_conteudo = (
            "codigo;titulo;texto;ordem\n"
            "01;Objetivo 1 revisado;Nova redação oficial;1\n"
            "20;Objetivo 20;Redação do objetivo 20;20\n"
        )
        resposta = self.client.post(
            reverse("ava:gt_objetivos_importar"),
            {"conteudo": csv_conteudo, "municipio": self.cliente.id},
            follow=True,
        )
        self.assertEqual(resposta.status_code, 200)
        objetivos = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=self.cliente
        )
        self.assertEqual(objetivos.count(), TOTAL_OBJETIVOS + 1)
        atualizado = objetivos.get(codigo="01")
        self.assertEqual(atualizado.titulo, "Objetivo 1 revisado")
        self.assertEqual(atualizado.texto, "Nova redação oficial")

    def test_importacao_exige_perfil_administrativo(self):
        self.client.force_login(self.participante)
        resposta = self.client.post(
            reverse("ava:gt_objetivos_importar"),
            {"conteudo": "01;Tentativa;Texto;1"},
        )
        self.assertEqual(resposta.status_code, 403)

    def test_municipio_sem_objetivos_mostra_estado_vazio_instrutivo(self):
        """Os textos vêm do cadastro: nenhum objetivo é inventado pelo sistema."""

        admin_outro = User.objects.create_user(
            email="admin-outro-gt@example.com",
            nome="Otavio Outro",
            password="123456",
            cliente=self.outro_cliente,
            role=User.Role.ADMIN_CLIENTE,
        )
        self.client.force_login(admin_outro)
        resposta = self.client.get(reverse("ava:gt_objetivos"))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Nenhum objetivo cadastrado")
