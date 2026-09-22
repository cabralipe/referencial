"""Testes do Diário de Bordo: fluxo, permissões, mídias e frequência."""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ava.models import (
    Aula,
    Curso,
    CursoModulo,
    DiarioBordo,
    DiarioBordoMidia,
    DiarioBordoParticipante,
)
from ava.models.diario import OrigemAula
from ava.services import DiarioBordoService
from core.models import AuditLog, Cliente
from curriculum.models import Escola


User = get_user_model()

PNG_MINIMO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)
class DiarioBordoBaseTests(TestCase):
    """Cenário comum: dois municípios, duas escolas, professores isolados."""

    def setUp(self):
        self.cliente = Cliente.objects.create(nome="Município A", slug="municipio-a")
        self.outro_cliente = Cliente.objects.create(
            nome="Município B", slug="municipio-b"
        )
        self.escola_a = Escola.objects.create(cliente=self.cliente, nome="Escola A")
        self.escola_b = Escola.objects.create(cliente=self.cliente, nome="Escola B")
        self.escola_outro = Escola.objects.create(
            cliente=self.outro_cliente, nome="Escola Outro Município"
        )

        self.admin = User.objects.create_user(
            email="admin-diario@example.com",
            nome="Admin",
            password="123456",
            cliente=self.cliente,
            role=User.Role.ADMIN_CLIENTE,
        )
        self.professor_a = User.objects.create_user(
            email="prof-a-diario@example.com",
            nome="Professor A",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_a,
            role=User.Role.PROFESSOR,
        )
        self.professor_b = User.objects.create_user(
            email="prof-b-diario@example.com",
            nome="Professor B",
            password="123456",
            cliente=self.cliente,
            escola=self.escola_b,
            role=User.Role.PROFESSOR,
        )
        self.professor_outro = User.objects.create_user(
            email="prof-outro-diario@example.com",
            nome="Professor Outro",
            password="123456",
            cliente=self.outro_cliente,
            escola=self.escola_outro,
            role=User.Role.PROFESSOR,
        )

        self.curso = Curso.objects.create(
            cliente=self.cliente,
            titulo="Formação Continuada",
            slug="formacao-continuada-diario",
            status=Curso.Status.PUBLICADO,
            autor_principal=self.admin,
        )
        self.modulo = CursoModulo.objects.create(
            cliente=self.cliente, curso=self.curso, titulo="Módulo 1", ordem=1
        )
        self.aula = Aula.objects.create(
            cliente=self.cliente,
            modulo=self.modulo,
            titulo="Aula inaugural",
            resumo="Apresentação do percurso formativo.",
            ordem=1,
        )

    # -- helpers -------------------------------------------------------
    def criar_diario(self, **kwargs):
        dados = {
            "cliente": self.cliente,
            "escola": self.escola_a,
            "professor": self.professor_a,
            "created_by": self.professor_a,
            "origem": OrigemAula.NO_SISTEMA,
            "curso": self.curso,
            "modulo": self.modulo,
            "aula": self.aula,
            "data_aula": date(2026, 3, 10),
            "titulo": "Encontro de abertura",
            "conteudo_trabalhado": "Alinhamento do plano de trabalho.",
            "participantes_presentes": 12,
        }
        dados.update(kwargs)
        return DiarioBordo.objects.create(**dados)


class DiarioBordoModeloTests(DiarioBordoBaseTests):
    def test_registro_interno_vinculado_a_aula_existente(self):
        diario = self.criar_diario()
        self.assertEqual(diario.aula, self.aula)
        self.assertEqual(diario.curso, self.curso)
        self.assertEqual(diario.status, DiarioBordo.Status.RASCUNHO)

    def test_aplicar_dados_da_aula_preenche_curso_modulo_e_titulo(self):
        diario = DiarioBordo(
            cliente=self.cliente,
            escola=self.escola_a,
            professor=self.professor_a,
            created_by=self.professor_a,
            data_aula=date(2026, 4, 1),
        )
        diario.aplicar_dados_da_aula(self.aula)
        self.assertEqual(diario.titulo, "Aula inaugural")
        self.assertEqual(diario.modulo, self.modulo)
        self.assertEqual(diario.curso, self.curso)
        self.assertEqual(
            diario.conteudo_trabalhado, "Apresentação do percurso formativo."
        )

    def test_registro_externo_nao_exige_vinculo_com_curso(self):
        diario = self.criar_diario(
            origem=OrigemAula.ATIVIDADE_EXTERNA,
            curso=None,
            modulo=None,
            aula=None,
            tipo_atividade=DiarioBordo.TipoAtividade.VISITA_TECNICA,
            local_realizacao="Museu da Cidade",
        )
        diario.full_clean()
        self.assertIsNone(diario.curso_id)

    def test_registro_externo_exige_local_e_tipo(self):
        diario = DiarioBordo(
            cliente=self.cliente,
            escola=self.escola_a,
            professor=self.professor_a,
            created_by=self.professor_a,
            origem=OrigemAula.PRESENCIAL_EXTERNA,
            data_aula=date(2026, 5, 2),
            titulo="Oficina na praça",
            conteudo_trabalhado="Leitura coletiva.",
        )
        with self.assertRaises(ValidationError) as ctx:
            diario.full_clean()
        self.assertIn("local_realizacao", ctx.exception.message_dict)
        self.assertIn("tipo_atividade", ctx.exception.message_dict)

    def test_registro_no_sistema_exige_curso(self):
        diario = DiarioBordo(
            cliente=self.cliente,
            escola=self.escola_a,
            professor=self.professor_a,
            created_by=self.professor_a,
            origem=OrigemAula.NO_SISTEMA,
            data_aula=date(2026, 5, 2),
            titulo="Aula do sistema",
            conteudo_trabalhado="Conteúdo.",
        )
        with self.assertRaises(ValidationError) as ctx:
            diario.full_clean()
        self.assertIn("curso", ctx.exception.message_dict)

    def test_registro_hibrido_aceita_curso_e_dados_externos(self):
        diario = self.criar_diario(
            origem=OrigemAula.HIBRIDA,
            tipo_atividade=DiarioBordo.TipoAtividade.OFICINA,
            local_realizacao="Quadra da escola",
        )
        diario.full_clean()
        self.assertTrue(diario.usa_estrutura_do_sistema)
        self.assertTrue(diario.usa_dados_externos)

    def test_registro_externo_rejeita_vinculo_com_aula_do_sistema(self):
        diario = DiarioBordo(
            cliente=self.cliente,
            escola=self.escola_a,
            professor=self.professor_a,
            created_by=self.professor_a,
            origem=OrigemAula.ATIVIDADE_EXTERNA,
            curso=self.curso,
            data_aula=date(2026, 5, 2),
            titulo="Atividade externa",
            conteudo_trabalhado="Conteúdo.",
            tipo_atividade=DiarioBordo.TipoAtividade.REUNIAO,
            local_realizacao="Secretaria",
        )
        with self.assertRaises(ValidationError) as ctx:
            diario.full_clean()
        self.assertIn("origem", ctx.exception.message_dict)

    def test_presentes_nao_pode_superar_previstos(self):
        diario = self.criar_diario(
            participantes_previstos=5, participantes_presentes=9
        )
        with self.assertRaises(ValidationError) as ctx:
            diario.full_clean()
        self.assertIn("participantes_presentes", ctx.exception.message_dict)


class DiarioBordoFluxoTests(DiarioBordoBaseTests):
    def test_envio_muda_status_e_registra_auditoria(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        self.assertEqual(diario.status, DiarioBordo.Status.ENVIADO)
        self.assertIsNotNone(diario.enviado_em)
        self.assertTrue(
            AuditLog.objects.filter(
                cliente=self.cliente,
                entidade="ava.DiarioBordo",
                entidade_id=str(diario.pk),
                acao="enviado",
            ).exists()
        )

    def test_envio_exige_frequencia_registrada(self):
        diario = self.criar_diario(participantes_presentes=0)
        with self.assertRaises(ValidationError):
            DiarioBordoService.enviar(diario, self.professor_a)

    def test_professor_nao_edita_registro_apos_envio(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        self.assertFalse(DiarioBordoService.pode_editar(diario, self.professor_a))

    def test_bloqueio_impede_edicao_ate_para_administrador(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        DiarioBordoService.revisar(diario, self.admin, parecer="Ok", bloquear=True)
        diario.refresh_from_db()
        self.assertEqual(diario.status, DiarioBordo.Status.BLOQUEADO)
        self.assertFalse(DiarioBordoService.pode_editar(diario, self.admin))
        self.assertFalse(DiarioBordoService.pode_editar(diario, self.professor_a))

    def test_professor_nao_pode_revisar(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            DiarioBordoService.revisar(diario, self.professor_a)

    def test_admin_reabre_registro_como_rascunho(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        DiarioBordoService.reabrir(diario, self.admin)
        diario.refresh_from_db()
        self.assertEqual(diario.status, DiarioBordo.Status.RASCUNHO)
        self.assertTrue(DiarioBordoService.pode_editar(diario, self.professor_a))


class DiarioBordoFrequenciaTests(DiarioBordoBaseTests):
    def test_lista_nominal_atualiza_quantidade_de_presentes(self):
        diario = self.criar_diario(
            frequencia_nominal=True, participantes_presentes=0
        )
        DiarioBordoService.registrar_presenca(
            diario, self.professor_a, nome="Maria Souza", identificacao="3A"
        )
        DiarioBordoService.registrar_presenca(
            diario, self.professor_a, nome="João Lima", presente=False
        )
        diario.refresh_from_db()
        self.assertEqual(diario.participantes_presentes, 1)
        self.assertEqual(
            DiarioBordoParticipante.objects.filter(diario=diario).count(), 2
        )

    def test_remover_participante_recalcula_frequencia(self):
        diario = self.criar_diario(
            frequencia_nominal=True, participantes_presentes=0
        )
        participante = DiarioBordoService.registrar_presenca(
            diario, self.professor_a, nome="Ana Paula"
        )
        diario.refresh_from_db()
        self.assertEqual(diario.participantes_presentes, 1)

        DiarioBordoService.remover_presenca(diario, self.professor_a, participante.pk)
        diario.refresh_from_db()
        self.assertEqual(diario.participantes_presentes, 0)

    def test_frequencia_apenas_por_quantidade_permanece_manual(self):
        diario = self.criar_diario(frequencia_nominal=False, participantes_presentes=27)
        diario.sincronizar_frequencia()
        self.assertEqual(diario.participantes_presentes, 27)


class DiarioBordoMidiaTests(DiarioBordoBaseTests):
    def test_upload_de_varias_fotos(self):
        diario = self.criar_diario()
        for indice in range(3):
            DiarioBordoService.adicionar_midia(
                diario,
                self.professor_a,
                SimpleUploadedFile(
                    f"foto-{indice}.png", PNG_MINIMO, content_type="image/png"
                ),
                legenda=f"Foto {indice}",
                consentimento=True,
            )
        self.assertEqual(
            DiarioBordoMidia.objects.filter(diario=diario).count(), 3
        )

    def test_rejeita_extensao_invalida(self):
        diario = self.criar_diario()
        with self.assertRaises(ValidationError):
            DiarioBordoService.adicionar_midia(
                diario,
                self.professor_a,
                SimpleUploadedFile(
                    "malicioso.exe", b"MZ\x90\x00", content_type="application/x-msdownload"
                ),
            )

    def test_rejeita_mime_incompativel_para_foto(self):
        diario = self.criar_diario()
        with self.assertRaises(ValidationError):
            DiarioBordoService.adicionar_midia(
                diario,
                self.professor_a,
                SimpleUploadedFile(
                    "relatorio.pdf", b"%PDF-1.4", content_type="application/pdf"
                ),
                tipo=DiarioBordoMidia.Tipo.FOTO,
            )

    def test_rejeita_arquivo_acima_do_limite(self):
        diario = self.criar_diario()
        enorme = SimpleUploadedFile(
            "grande.png", b"x" * (10 * 1024 * 1024 + 1), content_type="image/png"
        )
        with self.assertRaises(ValidationError):
            DiarioBordoService.adicionar_midia(diario, self.professor_a, enorme)

    def test_nao_aceita_anexo_em_registro_enviado(self):
        diario = self.criar_diario()
        DiarioBordoService.enviar(diario, self.professor_a)
        diario.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            DiarioBordoService.adicionar_midia(
                diario,
                self.professor_a,
                SimpleUploadedFile("tarde.png", PNG_MINIMO, content_type="image/png"),
            )


class DiarioBordoViewTests(DiarioBordoBaseTests):
    def test_professor_cria_registro_no_sistema_pela_interface(self):
        self.client.force_login(self.professor_a)
        resposta = self.client.post(
            reverse("ava:diario_novo"),
            {
                "municipio": self.cliente.id,
                "origem": OrigemAula.NO_SISTEMA,
                "curso": self.curso.id,
                "modulo": self.modulo.id,
                "aula": self.aula.id,
                "data_aula": "2026-03-12",
                "titulo": "Aula pela interface",
                "conteudo_trabalhado": "Conteúdo trabalhado na aula.",
                "metodologia": "Roda de conversa.",
                "participantes_presentes": "18",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        diario = DiarioBordo.objects.get(titulo="Aula pela interface")
        self.assertEqual(diario.escola, self.escola_a)
        self.assertEqual(diario.professor, self.professor_a)
        self.assertEqual(diario.aula, self.aula)

    def test_professor_cria_atividade_externa_sem_curso(self):
        self.client.force_login(self.professor_a)
        resposta = self.client.post(
            reverse("ava:diario_novo"),
            {
                "municipio": self.cliente.id,
                "origem": OrigemAula.ATIVIDADE_EXTERNA,
                "data_aula": "2026-03-20",
                "titulo": "Visita ao museu",
                "conteudo_trabalhado": "Patrimônio local.",
                "tipo_atividade": DiarioBordo.TipoAtividade.VISITA_TECNICA,
                "local_realizacao": "Museu Municipal",
                "grupo_participante": "Turma 5º ano",
                "participantes_presentes": "22",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        diario = DiarioBordo.objects.get(titulo="Visita ao museu")
        self.assertIsNone(diario.curso_id)
        self.assertEqual(diario.local_realizacao, "Museu Municipal")

    def test_professor_cria_registro_hibrido(self):
        self.client.force_login(self.professor_a)
        resposta = self.client.post(
            reverse("ava:diario_novo"),
            {
                "municipio": self.cliente.id,
                "origem": OrigemAula.HIBRIDA,
                "curso": self.curso.id,
                "modulo": self.modulo.id,
                "data_aula": "2026-03-22",
                "titulo": "Aula híbrida",
                "conteudo_trabalhado": "Parte online, parte na quadra.",
                "tipo_atividade": DiarioBordo.TipoAtividade.AULA,
                "local_realizacao": "Quadra da escola",
                "participantes_presentes": "20",
            },
        )
        self.assertEqual(resposta.status_code, 302)
        diario = DiarioBordo.objects.get(titulo="Aula híbrida")
        self.assertEqual(diario.curso, self.curso)
        self.assertEqual(diario.local_realizacao, "Quadra da escola")

    def test_professor_so_enxerga_registros_da_propria_escola(self):
        self.criar_diario(titulo="Registro da escola A")
        self.criar_diario(
            titulo="Registro da escola B",
            escola=self.escola_b,
            professor=self.professor_b,
            created_by=self.professor_b,
        )
        self.client.force_login(self.professor_a)
        resposta = self.client.get(reverse("ava:diario_lista"))
        self.assertEqual(resposta.status_code, 200)
        conteudo = resposta.content.decode()
        self.assertIn("Registro da escola A", conteudo)
        self.assertNotIn("Registro da escola B", conteudo)

    def test_administrador_enxerga_registros_de_varias_escolas(self):
        self.criar_diario(titulo="Registro da escola A")
        self.criar_diario(
            titulo="Registro da escola B",
            escola=self.escola_b,
            professor=self.professor_b,
            created_by=self.professor_b,
        )
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse("ava:diario_lista"))
        conteudo = resposta.content.decode()
        self.assertIn("Registro da escola A", conteudo)
        self.assertIn("Registro da escola B", conteudo)

    def test_professor_de_outra_escola_recebe_404_no_detalhe(self):
        diario = self.criar_diario()
        self.client.force_login(self.professor_b)
        resposta = self.client.get(reverse("ava:diario_detalhe", args=[diario.id]))
        self.assertEqual(resposta.status_code, 404)

    def test_isolamento_entre_municipios(self):
        diario = self.criar_diario()
        self.client.force_login(self.professor_outro)
        resposta = self.client.get(reverse("ava:diario_detalhe", args=[diario.id]))
        self.assertEqual(resposta.status_code, 404)

    def test_cursista_sem_permissao_recebe_403(self):
        leitor = User.objects.create_user(
            email="leitor-diario@example.com",
            nome="Leitor",
            password="123456",
            cliente=self.cliente,
            role=User.Role.LEITOR,
        )
        self.client.force_login(leitor)
        resposta = self.client.get(reverse("ava:diario_lista"))
        self.assertEqual(resposta.status_code, 403)

    def test_filtro_por_origem(self):
        self.criar_diario(titulo="Aula interna")
        self.criar_diario(
            titulo="Atividade fora",
            origem=OrigemAula.ATIVIDADE_EXTERNA,
            curso=None,
            modulo=None,
            aula=None,
            tipo_atividade=DiarioBordo.TipoAtividade.OFICINA,
            local_realizacao="Centro comunitário",
        )
        self.client.force_login(self.professor_a)
        resposta = self.client.get(
            reverse("ava:diario_lista"), {"origem": OrigemAula.ATIVIDADE_EXTERNA}
        )
        conteudo = resposta.content.decode()
        self.assertIn("Atividade fora", conteudo)
        self.assertNotIn("Aula interna", conteudo)

    def test_exportacao_xlsx_identifica_modalidade(self):
        self.criar_diario(titulo="Aula interna")
        self.client.force_login(self.professor_a)
        resposta = self.client.get(reverse("ava:diario_exportar", args=["xlsx"]))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("spreadsheetml", resposta["Content-Type"])
        self.assertTrue(len(resposta.content) > 0)

    def test_exportacao_csv_contem_a_origem(self):
        self.criar_diario(titulo="Aula interna")
        self.client.force_login(self.professor_a)
        resposta = self.client.get(reverse("ava:diario_exportar", args=["csv"]))
        self.assertEqual(resposta.status_code, 200)
        conteudo = resposta.content.decode("utf-8-sig")
        self.assertIn("No sistema", conteudo)
        self.assertIn("Aula interna", conteudo)

    def test_arquivo_de_midia_e_servido_pelo_django(self):
        diario = self.criar_diario()
        midia = DiarioBordoService.adicionar_midia(
            diario,
            self.professor_a,
            SimpleUploadedFile("foto.png", PNG_MINIMO, content_type="image/png"),
        )
        self.client.force_login(self.professor_a)
        resposta = self.client.get(
            reverse("ava:diario_midia_arquivo", args=[diario.id, midia.id])
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Cache-Control"], "private, no-store")
        self.assertEqual(resposta["X-Content-Type-Options"], "nosniff")

    def test_midia_nao_acessivel_por_professor_de_outra_escola(self):
        diario = self.criar_diario()
        midia = DiarioBordoService.adicionar_midia(
            diario,
            self.professor_a,
            SimpleUploadedFile("foto.png", PNG_MINIMO, content_type="image/png"),
        )
        self.client.force_login(self.professor_b)
        resposta = self.client.get(
            reverse("ava:diario_midia_arquivo", args=[diario.id, midia.id])
        )
        self.assertEqual(resposta.status_code, 404)

    def test_envio_pela_interface(self):
        diario = self.criar_diario()
        self.client.force_login(self.professor_a)
        resposta = self.client.post(reverse("ava:diario_enviar", args=[diario.id]))
        self.assertEqual(resposta.status_code, 302)
        diario.refresh_from_db()
        self.assertEqual(diario.status, DiarioBordo.Status.ENVIADO)

    def test_auditoria_guarda_criacao_e_alteracao(self):
        diario = self.criar_diario()
        DiarioBordoService.salvar(diario, self.professor_a, criando=False)
        acoes = set(
            AuditLog.objects.filter(
                cliente=self.cliente,
                entidade="ava.DiarioBordo",
                entidade_id=str(diario.pk),
            ).values_list("acao", flat=True)
        )
        self.assertIn("atualizado", acoes)
