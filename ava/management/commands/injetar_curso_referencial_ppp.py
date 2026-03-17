from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ava.models import Atividade, Aula, ConteudoAula, Curso, CursoModulo
from core.models import Cliente, Usuario


CURSO_TITULO_PADRAO = (
    "Implementação do Referencial Curricular - "
    "Elaboração e Atualização do Projeto Político-Pedagógico"
)
CURSO_SLUG_PADRAO = "implementacao-referencial-curricular-ppp"

MODULOS_TEMATICOS = [
    "Diagnóstico",
    "Identidade da Escola",
    "Organização Pedagógica",
    "Educação Inclusiva",
    "Organização do Atendimento",
    "Gestão e Funcionamento",
    "Monitoramento e Avaliação",
]

AULAS_PADRAO_MODULO = [
    "Boas-vindas ao Módulo",
    "Apresentação do Módulo",
    "Materiais para apoio aos estudos",
    "Vídeo facultativo",
    "Orientações para atividade",
    "Atividade",
    "Atividade corrigida - Prof. Redator",
]


def _descricao_longa_curso() -> str:
    return (
        "1. Apresentação do Curso\n"
        "Curso voltado à implementação do Referencial Curricular na elaboração e atualização do PPP.\n\n"
        "2. Boas-vindas ao Curso\n"
        "Mensagem acolhedora aos cursistas, com incentivo à participação em toda a formação.\n\n"
        "4. Tutoriais para Navegação no Curso\n"
        "- Tutorial de acesso à plataforma\n"
        "- Tutorial de navegação entre módulos\n"
        "- Tutorial de envio de atividades\n"
        "- Tutorial de acompanhamento de desempenho\n\n"
        "Observação Final\n"
        "- Fórum geral do curso\n"
        "- Espaço para dúvidas\n"
        "- Avaliação final do curso\n"
        "- Certificação"
    )


def _ementa_curso() -> str:
    return (
        "3. Ementa do Curso\n"
        "Estudo dos fundamentos do Referencial Curricular e aplicação prática na elaboração e atualização "
        "do Projeto Político-Pedagógico, com foco em diagnóstico institucional, identidade escolar, "
        "organização pedagógica, educação inclusiva, organização do atendimento, gestão e funcionamento, "
        "monitoramento e avaliação."
    )


def _objetivos_curso() -> str:
    return (
        "5. Objetivos do Curso\n"
        "Objetivo Geral:\n"
        "Promover a compreensão e a aplicação do Referencial Curricular na elaboração e atualização "
        "do Projeto Político-Pedagógico das instituições escolares.\n\n"
        "Objetivos Específicos:\n"
        "- Compreender os fundamentos do Referencial Curricular\n"
        "- Identificar os elementos constitutivos do PPP\n"
        "- Analisar a realidade escolar para construção do diagnóstico\n"
        "- Planejar ações pedagógicas alinhadas ao currículo\n"
        "- Fortalecer práticas inclusivas e organizacionais\n"
        "- Desenvolver estratégias de monitoramento e avaliação"
    )


class Command(BaseCommand):
    help = "Injeta o curso do Referencial Curricular (PPP) com estrutura completa no AVA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cliente-id",
            type=int,
            default=None,
            help="ID do cliente para execução não interativa (opcional).",
        )
        parser.add_argument(
            "--cliente-slug",
            default="",
            help="Slug do cliente para execução não interativa (opcional).",
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
            help="Título do curso.",
        )
        parser.add_argument(
            "--rascunho",
            action="store_true",
            help="Cria/atualiza o curso como rascunho (padrão é publicado).",
        )
        parser.add_argument(
            "--fechado",
            action="store_true",
            help="Desabilita inscrição livre (padrão é curso aberto).",
        )
        parser.add_argument(
            "--nao-interativo",
            action="store_true",
            help="Executa uma única vez sem perguntas no terminal.",
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
            raise CommandError("Informe um slug válido para o curso.")
        if not titulo:
            raise CommandError("Informe um título válido para o curso.")

        cliente = self._resolver_cliente_opcional(cliente_id=cliente_id, cliente_slug=cliente_slug)
        if nao_interativo and cliente is None:
            raise CommandError("No modo --nao-interativo, informe --cliente-id ou --cliente-slug.")

        slug_execucao = slug_base
        primeira_execucao = True

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
            self.stdout.write(f"Próxima injeção usará slug: {slug_execucao}")
            cliente = None
            primeira_execucao = False

        if primeira_execucao:
            self.stdout.write("Execução finalizada.")
        else:
            self.stdout.write("Execuções em múltiplos clientes finalizadas.")

    def _resolver_cliente_opcional(self, *, cliente_id: int | None, cliente_slug: str) -> Cliente | None:
        if cliente_id is not None:
            cliente = Cliente.objects.filter(id=cliente_id).first()
            if not cliente:
                raise CommandError(f"Cliente não encontrado para id={cliente_id}.")
            return cliente
        if cliente_slug:
            cliente = Cliente.objects.filter(slug=cliente_slug).first()
            if not cliente:
                raise CommandError(f"Cliente não encontrado para slug='{cliente_slug}'.")
            return cliente
        return None

    def _perguntar_cliente_por_id(self) -> Cliente:
        while True:
            valor = input("Informe o ID do cliente: ").strip()
            if not valor.isdigit():
                self.stdout.write(self.style.WARNING("ID inválido. Digite um número inteiro."))
                continue
            cliente = Cliente.objects.filter(id=int(valor)).first()
            if cliente:
                self.stdout.write(f"Cliente selecionado: id={cliente.id} slug={cliente.slug} nome={cliente.nome}")
                return cliente
            self.stdout.write(self.style.WARNING(f"Cliente id={valor} não encontrado."))

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
                "Já existe um curso com esse slug em outro cliente. "
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
                        "Formação para aplicação do Referencial Curricular na elaboração e "
                        "atualização do PPP."
                    ),
                    "descricao_longa": _descricao_longa_curso(),
                    "ementa": _ementa_curso(),
                    "objetivos": _objetivos_curso(),
                    "publico_alvo": (
                        "Gestores escolares, coordenadores pedagógicos, professores e "
                        "demais profissionais da educação."
                    ),
                    "nivel": "Formação continuada",
                    "carga_horaria": 120,
                    "status": status,
                    "is_aberto": is_aberto,
                    "permite_certificado": True,
                    "progresso_minimo": 100,
                    "nota_minima": 70.0,
                    "autor_principal": autor,
                    "is_deleted": False,
                },
            )

            # Recria a estrutura para garantir padrão exato, sem duplicidade.
            CursoModulo.raw_objects.filter(curso=curso).delete()

            total_aulas = 0
            total_atividades = 0
            for ordem_modulo, nome_modulo in enumerate(MODULOS_TEMATICOS, start=1):
                modulo = CursoModulo.objects.create(
                    cliente=cliente,
                    curso=curso,
                    titulo=f"Módulo {ordem_modulo} - {nome_modulo}",
                    descricao=(
                        f"Módulo {ordem_modulo} do curso: {nome_modulo}. "
                        "Siga as etapas de estudo e realização da atividade."
                    ),
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
                f"cliente={cliente.slug} curso_id={curso.id} módulos={len(MODULOS_TEMATICOS)} "
                f"aulas={total_aulas} atividades={total_atividades} slug={slug}"
            )
        )
        self.stdout.write("Módulos temáticos: " + "; ".join(MODULOS_TEMATICOS))

    def _resolver_autor(self, cliente: Cliente, autor_email: str) -> Usuario | None:
        if autor_email:
            autor = Usuario.objects.filter(email=autor_email, cliente=cliente).first()
            if not autor:
                raise CommandError(
                    f"Autor não encontrado com email='{autor_email}' para cliente='{cliente.slug}'."
                )
            return autor

        return (
            Usuario.objects.filter(cliente=cliente, role=Usuario.Role.ADMIN_CLIENTE)
            .order_by("id")
            .first()
        )

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
                descricao="Conteúdo base da etapa.",
                ordem=1,
                is_obrigatorio=True,
                conteudo_texto=self._texto_base_aula(nome_modulo=nome_modulo, titulo_aula=titulo_aula),
            )

            if titulo_aula == "Atividade":
                Atividade.objects.create(
                    cliente=cliente,
                    aula=aula,
                    tipo=Atividade.Tipo.TAREFA,
                    titulo="Avaliação final do curso" if ordem_modulo == 7 else "Atividade",
                    descricao=self._descricao_atividade(nome_modulo=nome_modulo, ordem_modulo=ordem_modulo),
                    instrucoes=(
                        "Elabore sua resposta com base nos estudos do módulo e envie no campo de resposta."
                    ),
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

        if ordem_modulo == 7 and aula_fechamento is not None:
            self._inserir_itens_finais(cliente=cliente, aula=aula_fechamento)

        return len(AULAS_PADRAO_MODULO), total_atividades

    def _resumo_aula(self, *, nome_modulo: str, titulo_aula: str) -> str:
        return f"{titulo_aula} do módulo {nome_modulo}."

    def _texto_base_aula(self, *, nome_modulo: str, titulo_aula: str) -> str:
        if titulo_aula == "Boas-vindas ao Módulo":
            return (
                f"Bem-vindo(a) ao módulo {nome_modulo}. "
                "Organize seu tempo de estudo e participe das atividades propostas."
            )
        if titulo_aula == "Apresentação do Módulo":
            return (
                f"Neste módulo, você estudará o tema '{nome_modulo}' "
                "com foco na elaboração e atualização do Projeto Político-Pedagógico."
            )
        if titulo_aula == "Materiais para apoio aos estudos":
            return (
                "Consulte os materiais de apoio (textos normativos, orientações pedagógicas e referências "
                "complementares) para aprofundar o estudo do tema."
            )
        if titulo_aula == "Vídeo facultativo":
            return (
                "Vídeo complementar opcional para reforçar os conceitos do módulo. "
                "Caso disponível, insira aqui o link ou embed do vídeo."
            )
        if titulo_aula == "Orientações para atividade":
            return (
                "Leia atentamente os critérios da atividade, os objetivos da entrega e os "
                "indicadores que serão considerados na correção."
            )
        if titulo_aula == "Atividade":
            return (
                "Realize a atividade proposta com base no conteúdo estudado no módulo e "
                "registre evidências aplicáveis à realidade da sua instituição."
            )
        if titulo_aula == "Atividade corrigida - Prof. Redator":
            return (
                "Após a entrega, consulte aqui a devolutiva comentada e a versão corrigida "
                "com orientações de melhoria."
            )
        return "Etapa do módulo."

    def _descricao_atividade(self, *, nome_modulo: str, ordem_modulo: int) -> str:
        if ordem_modulo == 7:
            return (
                "Avaliação final do curso, contemplando os conteúdos dos módulos e a aplicação "
                "do Referencial Curricular no PPP."
            )
        return f"Atividade prática do módulo {nome_modulo}."

    def _inserir_itens_finais(self, *, cliente: Cliente, aula: Aula):
        itens = [
            (
                "Fórum geral do curso",
                "Espaço coletivo para troca de experiências e socialização de práticas entre cursistas.",
            ),
            (
                "Espaço para dúvidas",
                "Canal para registro e acompanhamento de dúvidas pedagógicas e técnicas sobre o curso.",
            ),
            (
                "Certificação",
                "Informações sobre os critérios de certificação e emissão do certificado ao final do percurso.",
            ),
        ]
        ordem = 2
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
