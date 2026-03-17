from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ava.models import Atividade, Aula, ConteudoAula, Curso, CursoModulo
from core.models import Cliente, Usuario


CURSO_TITULO_PADRAO = "Formacao Continuada para Profissionais de Apoio Escolar na Educacao Especial"
CURSO_SLUG_PADRAO = "formacao-continuada-apoio-escolar-educacao-especial"

MODULOS_TEMATICOS = [
    "Gestao Emocional e Construcao de Vinculos e Afetividade",
    "Fundamentos da Educacao Inclusiva",
    "Desenvolvimento Humano e Processos de Aprendizagem",
    "Mediacao Pedagogica e Estrategias de Aprendizagem",
    "Alimentacao Escolar: Nutricao e Seletividade Alimentar",
    "Acessibilidade e Tecnologia Assistiva",
    "Primeiros Socorros no Ambiente Escolar",
    "Avaliacao Continua da Aprendizagem e Praticas Inclusivas",
]

CONTEUDOS_POR_MODULO = {
    1: [
        "Tema: Eu cuido de mim para cuidar de voce.",
        "Gestao emocional na rotina escolar inclusiva.",
        "Construcao de vinculos e afetividade no acompanhamento aos estudantes.",
    ],
    2: [
        "Conceitos centrais e marcos da educacao inclusiva.",
        "Papel do profissional de apoio escolar no processo inclusivo.",
    ],
    3: [
        "Desenvolvimento humano no contexto da educacao especial.",
        "Processos de aprendizagem e necessidades especificas dos estudantes.",
    ],
    4: [
        "Mediacao pedagogica no apoio escolar.",
        "Estrategias para favorecer participacao e aprendizagem.",
    ],
    5: [
        "Alimentacao escolar e nutricao no contexto inclusivo.",
        "Seletividade alimentar e manejo no ambiente escolar.",
    ],
    6: [
        "Principios de acessibilidade no espaco escolar.",
        "Recursos de tecnologia assistiva para autonomia e participacao.",
    ],
    7: [
        "Primeiros socorros no ambiente escolar.",
        "Procedimentos iniciais e encaminhamentos seguros.",
    ],
    8: [
        "Avaliacao continua da aprendizagem.",
        "Praticas inclusivas para desenvolvimento integral dos estudantes.",
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
        "Formacao voltada para o fortalecimento da atuacao do profissional de apoio escolar na educacao inclusiva "
        "e no desenvolvimento integral dos estudantes.\n\n"
        "2. Boas-vindas ao Curso\n"
        "Mensagem de acolhimento e valorizacao do papel dos profissionais de apoio escolar, "
        "com incentivo a participacao ativa em todo o percurso.\n\n"
        "4. Tutoriais para Navegacao no Curso\n"
        "- Tutorial de acesso a plataforma\n"
        "- Tutorial de navegacao entre modulos\n"
        "- Tutorial de envio de atividades\n"
        "- Tutorial de participacao nas atividades\n"
        "- Tutorial de acompanhamento de desempenho\n\n"
        "Observacoes para organizacao na plataforma\n"
        "- Forum geral do curso\n"
        "- Espaco de duvidas por modulo\n"
        "- Avaliacao final\n"
        "- Certificacao"
    )


def _ementa_curso() -> str:
    return (
        "3. Ementa do Curso\n"
        "Formacao voltada ao desenvolvimento de competencias socioemocionais, pedagogicas e praticas para "
        "atuacao na educacao inclusiva, abordando diferentes dimensoes do trabalho no ambiente escolar."
    )


def _objetivos_curso() -> str:
    return (
        "5. Objetivos do Curso\n"
        "Objetivo Geral:\n"
        "Fortalecer a atuacao dos profissionais de apoio escolar no contexto da educacao inclusiva.\n\n"
        "Objetivos Especificos:\n"
        "- Desenvolver competencias para atuacao no ambiente escolar\n"
        "- Compreender praticas inclusivas\n"
        "- Fortalecer a mediacao pedagogica\n"
        "- Promover o desenvolvimento integral dos estudantes"
    )


class Command(BaseCommand):
    help = "Injeta o curso de Formacao Continuada para Profissionais de Apoio Escolar (SATUBA) no AVA."

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
                    "descricao_curta": "Formacao continuada para profissionais de apoio escolar na educacao especial.",
                    "descricao_longa": _descricao_longa_curso(),
                    "ementa": _ementa_curso(),
                    "objetivos": _objetivos_curso(),
                    "publico_alvo": "Profissionais de apoio escolar da Educacao Basica.",
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

            # Recria estrutura para garantir padrao exato sem duplicidade.
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
        lista = " ".join(f"- {item}" for item in itens)
        return f"Modulo {ordem_modulo}: {nome_modulo}. Conteudo: {lista}"

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
                    titulo="Espaco de duvidas do modulo",
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
                "Organize seu percurso de estudos e participe ativamente das atividades."
            )
        if titulo_aula == "Apresentacao do Modulo":
            return (
                f"Neste modulo, voce estudara '{nome_modulo}' com foco na pratica de apoio escolar inclusivo."
            )
        if titulo_aula == "Materiais para apoio aos estudos":
            itens = CONTEUDOS_POR_MODULO.get(ordem_modulo, [])
            base = "Consulte textos orientadores, referencias praticas e materiais complementares do modulo."
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
                "Leia criterios e objetivos da atividade. Considere a realidade da escola e dos estudantes."
            )
        if titulo_aula == "Atividade":
            return (
                "Realize a atividade articulando conhecimentos socioemocionais, pedagogicos e praticas inclusivas."
            )
        if titulo_aula == "Atividade corrigida - Prof. Redator":
            return "Consulte a devolutiva comentada com orientacoes de melhoria."
        return "Etapa do modulo."

    def _descricao_atividade(self, *, nome_modulo: str, ordem_modulo: int) -> str:
        if ordem_modulo == 8:
            return "Avaliacao final do curso com foco em praticas inclusivas e desenvolvimento integral."
        return f"Atividade pratica do modulo {nome_modulo}."

    def _inserir_itens_finais(self, *, cliente: Cliente, aula: Aula):
        itens = [
            (
                "Forum geral do curso",
                "Espaco coletivo para troca de experiencias e boas praticas entre os participantes.",
            ),
            (
                "Avaliacao final",
                "Etapa de fechamento para consolidacao dos conhecimentos desenvolvidos no curso.",
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

