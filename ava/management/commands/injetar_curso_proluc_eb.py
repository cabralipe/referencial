from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ava.models import Atividade, Aula, ConteudoAula, Curso, CursoModulo
from core.models import Cliente, Usuario


CURSO_TITULO_PADRAO = "PROLUC - Ambiente Virtual para Professores da Educacao Basica"
CURSO_SLUG_PADRAO = "proluc-ambiente-virtual-professores-educacao-basica"

MODULOS_TEMATICOS = [
    "Estudo do Referencial Curricular",
    "Cadernos do Referencial Curricular",
    "Educacao Especial",
    "Tecnologia e Educacao",
    "Organizacao Curricular",
    "Planejamento Educacional",
    "Temas Contemporaneos e Integradores",
    "Construcao Coletiva",
]

CONTEUDOS_POR_MODULO = {
    1: [
        "Estudo do Texto Introdutorio Geral do Referencial Curricular.",
    ],
    2: [
        "Estudo dos textos introdutorios das etapas: Educacao Infantil.",
        "Ensino Fundamental Anos Iniciais.",
        "Ensino Fundamental Anos Finais.",
        "Educacao de Jovens e Adultos.",
        "BNCC Computacao.",
    ],
    3: [
        "Educacao Especial nos cadernos das etapas do Referencial Curricular.",
    ],
    4: [
        "Estudo da BNCC e Computacao.",
    ],
    5: [
        "Organizador curricular por etapa: Educacao Infantil.",
        "Ensino Fundamental I.",
        "Ensino Fundamental II.",
        "Educacao de Jovens e Adultos.",
    ],
    6: [
        "Do Projeto Politico-Pedagogico ao Plano de Aula.",
        "Formacao do estudante no contexto educacional.",
    ],
    7: [
        "Temas contemporaneos e transversais.",
        "Temas integradores.",
        "Projetos pedagogicos do territorio.",
    ],
    8: [
        "Plano de aula - construcao coletiva.",
    ],
}

AULAS_PADRAO_MODULO = [
    "Boas-vindas ao Modulo",
    "Apresentacao do Modulo",
    "Materiais para apoio aos estudos",
    "Video facultativo",
    "Orientacoes para atividade",
    "Atividade",
    "Atividade corrigida - Prof. Redator",
]


def _descricao_longa_curso() -> str:
    return (
        "1. Apresentacao do Curso\n"
        "Curso voltado a professores da Educacao Basica para estudo e aplicacao do Referencial Curricular.\n\n"
        "2. Boas-vindas ao Curso\n"
        "Mensagem de acolhimento aos professores, com incentivo ao engajamento nas atividades propostas.\n\n"
        "4. Tutoriais para Navegacao no Curso\n"
        "- Tutorial de acesso a plataforma\n"
        "- Tutorial de navegacao entre modulos\n"
        "- Tutorial de participacao nas atividades\n"
        "- Tutorial de envio de tarefas\n"
        "- Tutorial de acompanhamento do progresso\n\n"
        "Observacoes para a Plataforma\n"
        "- Forum geral\n"
        "- Espaco para duvidas por modulo\n"
        "- Avaliacao final\n"
        "- Certificacao"
    )


def _ementa_curso() -> str:
    return (
        "3. Ementa do Curso\n"
        "Estudo do Referencial Curricular do territorio, contemplando suas etapas, organizacao curricular, "
        "educacao especial, tecnologia educacional, planejamento pedagogico e praticas integradoras, "
        "com foco na aplicacao em sala de aula."
    )


def _objetivos_curso() -> str:
    return (
        "5. Objetivos do Curso\n"
        "Objetivo Geral:\n"
        "Compreender e aplicar o Referencial Curricular no planejamento e desenvolvimento das praticas "
        "pedagogicas na Educacao Basica.\n\n"
        "Objetivos Especificos:\n"
        "- Estudar os fundamentos do Referencial Curricular\n"
        "- Analisar os cadernos das diferentes etapas de ensino\n"
        "- Compreender a organizacao curricular\n"
        "- Integrar tecnologia e educacao nas praticas pedagogicas\n"
        "- Planejar acoes educativas alinhadas ao curriculo\n"
        "- Desenvolver praticas inclusivas\n"
        "- Trabalhar temas contemporaneos e integradores\n"
        "- Construir coletivamente estrategias pedagogicas"
    )


class Command(BaseCommand):
    help = "Injeta o curso PROLUC para professores da Educacao Basica com estrutura completa no AVA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cliente-id",
            type=int,
            default=None,
            help="ID do cliente para execucao nao interativa (opcional).",
        )
        parser.add_argument(
            "--cliente-slug",
            default="",
            help="Slug do cliente para execucao nao interativa (opcional).",
        )
        parser.add_argument(
            "--autor-email",
            default="",
            help="E-mail do autor principal do curso (opcional).",
        )
        parser.add_argument(
            "--slug",
            default=CURSO_SLUG_PADRAO,
            help="Slug do curso.",
        )
        parser.add_argument(
            "--titulo",
            default=CURSO_TITULO_PADRAO,
            help="Titulo do curso.",
        )
        parser.add_argument(
            "--rascunho",
            action="store_true",
            help="Cria/atualiza o curso como rascunho (padrao e publicado).",
        )
        parser.add_argument(
            "--fechado",
            action="store_true",
            help="Desabilita inscricao livre (padrao e curso aberto).",
        )
        parser.add_argument(
            "--nao-interativo",
            action="store_true",
            help="Executa uma unica vez sem perguntas no terminal.",
        )

    def handle(self, *args, **options):
        cliente_id = options["cliente_id"]
        cliente_slug = (options["cliente_slug"] or "").strip()
        autor_email = (options["autor_email"] or "").strip()
        slug_base = (options["slug"] or "").strip()
        titulo = (options["titulo"] or "").strip()
        status = Curso.Status.RASCUNHO if options["rascunho"] else Curso.Status.PUBLICADO
        is_aberto = not options["fechado"]
        nao_interativo = options["nao_interativo"]

        if not slug_base:
            raise CommandError("Informe um slug valido para o curso.")
        if not titulo:
            raise CommandError("Informe um titulo valido para o curso.")

        cliente = self._resolver_cliente_opcional(cliente_id=cliente_id, cliente_slug=cliente_slug)
        if nao_interativo and cliente is None:
            raise CommandError("No modo --nao-interativo, informe --cliente-id ou --cliente-slug.")

        slug_execucao = slug_base
        multiplas_execucoes = False

        while True:
            if cliente is None:
                cliente = self._perguntar_cliente_por_id()

            self._injetar_curso_para_cliente(
                cliente=cliente,
                slug=slug_execucao,
                titulo=titulo,
                autor_email=autor_email,
                status=status,
                is_aberto=is_aberto,
            )

            if nao_interativo:
                break

            if not self._perguntar_sim_nao("Deseja injetar em outro cliente? [s/N]: "):
                break

            slug_execucao = self._proximo_slug_incremental(slug_base)
            self.stdout.write(f"Proxima injecao usara slug: {slug_execucao}")
            cliente = None
            multiplas_execucoes = True

        if multiplas_execucoes:
            self.stdout.write("Execucoes em multiplos clientes finalizadas.")
        else:
            self.stdout.write("Execucao finalizada.")

    def _resolver_cliente_opcional(self, *, cliente_id: int | None, cliente_slug: str) -> Cliente | None:
        if cliente_id is not None:
            cliente = Cliente.objects.filter(id=cliente_id).first()
            if not cliente:
                raise CommandError(f"Cliente nao encontrado para id={cliente_id}.")
            return cliente
        if cliente_slug:
            cliente = Cliente.objects.filter(slug=cliente_slug).first()
            if not cliente:
                raise CommandError(f"Cliente nao encontrado para slug='{cliente_slug}'.")
            return cliente
        return None

    def _perguntar_cliente_por_id(self) -> Cliente:
        while True:
            valor = input("Informe o ID do cliente: ").strip()
            if not valor.isdigit():
                self.stdout.write(self.style.WARNING("ID invalido. Digite um numero inteiro."))
                continue
            cliente = Cliente.objects.filter(id=int(valor)).first()
            if cliente:
                self.stdout.write(f"Cliente selecionado: id={cliente.id} slug={cliente.slug} nome={cliente.nome}")
                return cliente
            self.stdout.write(self.style.WARNING(f"Cliente id={valor} nao encontrado."))

    def _perguntar_sim_nao(self, mensagem: str) -> bool:
        resposta = input(mensagem).strip().lower()
        return resposta in {"s", "sim", "y", "yes"}

    def _proximo_slug_incremental(self, slug_base: str) -> str:
        indice = 2
        while True:
            candidato = f"{slug_base}-{indice}"
            if not Curso.raw_objects.filter(slug=candidato).exists():
                return candidato
            indice += 1

    def _resolver_autor(self, cliente: Cliente, autor_email: str) -> Usuario | None:
        if autor_email:
            autor = Usuario.objects.filter(email=autor_email, cliente=cliente).first()
            if not autor:
                raise CommandError(
                    f"Autor nao encontrado com email='{autor_email}' para cliente='{cliente.slug}'."
                )
            return autor

        return (
            Usuario.objects.filter(cliente=cliente, role=Usuario.Role.ADMIN_CLIENTE)
            .order_by("id")
            .first()
        )

    def _injetar_curso_para_cliente(
        self,
        *,
        cliente: Cliente,
        slug: str,
        titulo: str,
        autor_email: str,
        status: str,
        is_aberto: bool,
    ):
        autor = self._resolver_autor(cliente=cliente, autor_email=autor_email)
        curso_conflitante = Curso.raw_objects.filter(slug=slug).exclude(cliente=cliente).first()
        if curso_conflitante:
            raise CommandError(
                "Ja existe um curso com esse slug em outro cliente. "
                f"Slug='{slug}', cliente_id_existente={curso_conflitante.cliente_id}."
            )

        with transaction.atomic():
            curso, criado = Curso.raw_objects.update_or_create(
                cliente=cliente,
                slug=slug,
                defaults={
                    "cliente": cliente,
                    "slug": slug,
                    "titulo": titulo,
                    "descricao_curta": (
                        "Formacao para professores da Educacao Basica com foco no Referencial Curricular."
                    ),
                    "descricao_longa": _descricao_longa_curso(),
                    "ementa": _ementa_curso(),
                    "objetivos": _objetivos_curso(),
                    "publico_alvo": "Professores da Educacao Basica.",
                    "nivel": "Formacao continuada",
                    "carga_horaria": 160,
                    "status": status,
                    "is_aberto": is_aberto,
                    "permite_certificado": True,
                    "progresso_minimo": 100,
                    "nota_minima": 70.0,
                    "autor_principal": autor,
                    "is_deleted": False,
                },
            )

            # Recria a estrutura para garantir padrao exato sem duplicidade.
            CursoModulo.raw_objects.filter(curso=curso).delete()

            total_aulas = 0
            total_atividades = 0
            for ordem_modulo, nome_modulo in enumerate(MODULOS_TEMATICOS, start=1):
                modulo = CursoModulo.objects.create(
                    cliente=cliente,
                    curso=curso,
                    titulo=f"Modulo {ordem_modulo} - {nome_modulo}",
                    descricao=self._descricao_modulo(ordem_modulo=ordem_modulo, nome_modulo=nome_modulo),
                    ordem=ordem_modulo,
                    is_active=True,
                )
                aulas_criadas, atividades_criadas = self._criar_aulas_padrao_modulo(
                    cliente=cliente,
                    modulo=modulo,
                    ordem_modulo=ordem_modulo,
                    nome_modulo=nome_modulo,
                )
                total_aulas += aulas_criadas
                total_atividades += atividades_criadas

        acao = "criado" if criado else "atualizado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Curso {acao} com sucesso. "
                f"cliente={cliente.slug} curso_id={curso.id} modulos={len(MODULOS_TEMATICOS)} "
                f"aulas={total_aulas} atividades={total_atividades} slug={slug}"
            )
        )
        self.stdout.write("Modulos tematicos: " + "; ".join(MODULOS_TEMATICOS))

    def _descricao_modulo(self, *, ordem_modulo: int, nome_modulo: str) -> str:
        itens = CONTEUDOS_POR_MODULO.get(ordem_modulo, [])
        if not itens:
            return f"Modulo {ordem_modulo}: {nome_modulo}."
        texto_itens = " ".join(f"- {item}" for item in itens)
        return f"Modulo {ordem_modulo}: {nome_modulo}. Conteudo: {texto_itens}"

    def _criar_aulas_padrao_modulo(
        self,
        *,
        cliente: Cliente,
        modulo: CursoModulo,
        ordem_modulo: int,
        nome_modulo: str,
    ) -> tuple[int, int]:
        total_atividades = 0
        aula_fechamento = None

        for ordem_aula, titulo_aula in enumerate(AULAS_PADRAO_MODULO, start=1):
            aula_tipo = Aula.Tipo.AVALIATIVA if titulo_aula == "Atividade" else Aula.Tipo.CONTEUDO
            aula = Aula.objects.create(
                cliente=cliente,
                modulo=modulo,
                titulo=titulo_aula,
                resumo=self._resumo_aula(nome_modulo=nome_modulo, titulo_aula=titulo_aula),
                ordem=ordem_aula,
                tipo=aula_tipo,
                duracao_estimada_minutos=30 if titulo_aula != "Atividade" else 60,
                is_obigatoria=True,
                is_active=True,
            )

            ConteudoAula.objects.create(
                cliente=cliente,
                aula=aula,
                tipo=ConteudoAula.Tipo.TEXTO,
                titulo=titulo_aula,
                descricao="Conteudo base da etapa.",
                ordem=1,
                is_obrigatorio=True,
                conteudo_texto=self._texto_base_aula(
                    ordem_modulo=ordem_modulo,
                    nome_modulo=nome_modulo,
                    titulo_aula=titulo_aula,
                ),
            )

            if titulo_aula == "Atividade":
                Atividade.objects.create(
                    cliente=cliente,
                    aula=aula,
                    tipo=Atividade.Tipo.TAREFA,
                    titulo="Avaliacao final" if ordem_modulo == 8 else "Atividade",
                    descricao=self._descricao_atividade(nome_modulo=nome_modulo, ordem_modulo=ordem_modulo),
                    instrucoes="Elabore a resposta com base no modulo e envie no campo de resposta.",
                    nota_maxima=100,
                    peso=1,
                    is_obrigatoria=True,
                    tentativas_permitidas=1,
                    correcao_automatica=False,
                    criterio_aprovacao=70,
                )
                total_atividades += 1

            if titulo_aula == "Atividade corrigida - Prof. Redator":
                aula_fechamento = aula
                ConteudoAula.objects.create(
                    cliente=cliente,
                    aula=aula,
                    tipo=ConteudoAula.Tipo.TEXTO,
                    titulo="Espaco para duvidas do modulo",
                    descricao="Canal de duvidas por modulo.",
                    ordem=2,
                    is_obrigatorio=False,
                    conteudo_texto=(
                        f"Registre aqui duvidas do modulo {ordem_modulo} - {nome_modulo} para acompanhamento."
                    ),
                )

        if ordem_modulo == 8 and aula_fechamento is not None:
            self._inserir_itens_finais(cliente=cliente, aula=aula_fechamento)

        return len(AULAS_PADRAO_MODULO), total_atividades

    def _resumo_aula(self, *, nome_modulo: str, titulo_aula: str) -> str:
        return f"{titulo_aula} do modulo {nome_modulo}."

    def _texto_base_aula(self, *, ordem_modulo: int, nome_modulo: str, titulo_aula: str) -> str:
        if titulo_aula == "Boas-vindas ao Modulo":
            return (
                f"Bem-vindo(a) ao modulo {nome_modulo}. "
                "Organize seus estudos e participe ativamente das atividades."
            )
        if titulo_aula == "Apresentacao do Modulo":
            return (
                f"Neste modulo, voce estudara '{nome_modulo}' com foco na aplicacao pratica "
                "do Referencial Curricular na Educacao Basica."
            )
        if titulo_aula == "Materiais para apoio aos estudos":
            itens = CONTEUDOS_POR_MODULO.get(ordem_modulo, [])
            base = (
                "Consulte os materiais de apoio, textos orientadores, cadernos e referencias "
                "pedagogicas do modulo."
            )
            if not itens:
                return base
            lista = "\n".join(f"- {item}" for item in itens)
            return f"{base}\n\nConteudo do modulo:\n{lista}"
        if titulo_aula == "Video facultativo":
            return (
                "Video complementar opcional para reforco dos conceitos do modulo. "
                "Insira o link ou embed quando houver material audiovisual."
            )
        if titulo_aula == "Orientacoes para atividade":
            return (
                "Leia criterios, objetivos da entrega e indicadores de avaliacao antes de enviar a atividade."
            )
        if titulo_aula == "Atividade":
            return (
                "Desenvolva a atividade proposta articulando teoria, pratica docente e contexto da sala de aula."
            )
        if titulo_aula == "Atividade corrigida - Prof. Redator":
            return "Consulte a devolutiva comentada da atividade com orientacoes de melhoria."
        return "Etapa do modulo."

    def _descricao_atividade(self, *, nome_modulo: str, ordem_modulo: int) -> str:
        if ordem_modulo == 8:
            return "Avaliacao final do curso com foco na construcao coletiva de estrategias pedagogicas."
        return f"Atividade pratica do modulo {nome_modulo}."

    def _inserir_itens_finais(self, *, cliente: Cliente, aula: Aula):
        itens = [
            (
                "Forum geral",
                "Espaco coletivo para troca de experiencias entre professores cursistas.",
            ),
            (
                "Avaliacao final",
                "Etapa de fechamento para consolidacao das aprendizagens desenvolvidas no curso.",
            ),
            (
                "Certificacao",
                "Informacoes sobre criterios para emissao do certificado ao final do percurso.",
            ),
        ]
        ordem = 3
        for titulo, texto in itens:
            ConteudoAula.objects.create(
                cliente=cliente,
                aula=aula,
                tipo=ConteudoAula.Tipo.TEXTO,
                titulo=titulo,
                descricao="Item final do curso.",
                ordem=ordem,
                is_obrigatorio=False,
                conteudo_texto=texto,
            )
            ordem += 1

