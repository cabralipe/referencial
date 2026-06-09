from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils.text import slugify

from ava.models import (
    Atividade,
    Aula,
    ConteudoAula,
    Curso,
    CursoCategoria,
    CursoModulo,
    QuizAlternativa,
    QuizQuestao,
    TrilhaFormativa,
)
from core.models import Cliente, Usuario


@dataclass
class CourseCopyOptions:
    curso_origem: Curso
    cliente_destino: Cliente
    novo_titulo: str = ""
    novo_slug: str = ""
    copiar_atividades: bool = False
    manter_status_publicacao: bool = False
    usuario_executor: Usuario | None = None


class CourseCloneService:
    @staticmethod
    def _unique_slug(base_slug: str) -> str:
        slug_base = slugify(base_slug or "curso-copiado") or "curso-copiado"
        candidate = slug_base
        suffix = 2
        while Curso.raw_objects.filter(slug=candidate).exists():
            candidate = f"{slug_base}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _copy_file_name(field_file) -> str:
        if not field_file:
            return ""
        return getattr(field_file, "name", "") or ""

    @staticmethod
    def _resolve_target_author(curso_origem: Curso, cliente_destino: Cliente, usuario_executor: Usuario | None):
        autor_origem = getattr(curso_origem, "autor_principal", None)
        if autor_origem and autor_origem.email:
            autor_destino = Usuario.objects.filter(cliente=cliente_destino, email=autor_origem.email).first()
            if autor_destino:
                return autor_destino

        if usuario_executor and getattr(usuario_executor, "cliente_id", None) == cliente_destino.id:
            return usuario_executor

        return Usuario.objects.filter(cliente=cliente_destino, role=Usuario.Role.ADMIN_CLIENTE).order_by("id").first()

    @staticmethod
    def _get_or_copy_categoria(curso_origem: Curso, cliente_destino: Cliente):
        if not curso_origem.categoria_id:
            return None
        categoria_origem = curso_origem.categoria
        categoria_destino = CursoCategoria.objects.filter(
            cliente=cliente_destino,
            nome=categoria_origem.nome,
        ).first()
        if categoria_destino:
            return categoria_destino
        return CursoCategoria.objects.create(
            cliente=cliente_destino,
            nome=categoria_origem.nome,
            descricao=categoria_origem.descricao,
        )

    @staticmethod
    def _copy_trilhas(curso_origem: Curso, curso_destino: Curso, cliente_destino: Cliente):
        trilhas_destino = []
        for trilha_origem in curso_origem.trilhas.all().order_by("ordem_exibicao", "id"):
            trilha_destino = TrilhaFormativa.objects.filter(
                cliente=cliente_destino,
                nome=trilha_origem.nome,
            ).first()
            if trilha_destino is None:
                trilha_destino = TrilhaFormativa.objects.create(
                    cliente=cliente_destino,
                    nome=trilha_origem.nome,
                    descricao=trilha_origem.descricao,
                    capa=CourseCloneService._copy_file_name(trilha_origem.capa),
                    ordem_exibicao=trilha_origem.ordem_exibicao,
                    is_active=trilha_origem.is_active,
                    carga_horaria_total=trilha_origem.carga_horaria_total,
                )
            trilhas_destino.append(trilha_destino)
        if trilhas_destino:
            curso_destino.trilhas.set(trilhas_destino)

    @staticmethod
    def _copy_atividade(atividade_origem: Atividade, aula_destino: Aula):
        atividade_destino = Atividade.objects.create(
            cliente_id=aula_destino.cliente_id,
            aula=aula_destino,
            tipo=atividade_origem.tipo,
            titulo=atividade_origem.titulo,
            descricao=atividade_origem.descricao,
            instrucoes=atividade_origem.instrucoes,
            nota_maxima=atividade_origem.nota_maxima,
            peso=atividade_origem.peso,
            is_obrigatoria=atividade_origem.is_obrigatoria,
            prazo_envio=atividade_origem.prazo_envio,
            tentativas_permitidas=atividade_origem.tentativas_permitidas,
            correcao_automatica=atividade_origem.correcao_automatica,
            criterio_aprovacao=atividade_origem.criterio_aprovacao,
        )

        if atividade_origem.tipo not in {Atividade.Tipo.QUIZ, Atividade.Tipo.QUESTIONARIO}:
            return

        for questao_origem in atividade_origem.questoes.all().order_by("ordem", "id"):
            questao_destino = QuizQuestao.objects.create(
                cliente_id=aula_destino.cliente_id,
                atividade=atividade_destino,
                enunciado=questao_origem.enunciado,
                peso=questao_origem.peso,
                ordem=questao_origem.ordem,
                feedback_acerto=questao_origem.feedback_acerto,
                feedback_erro=questao_origem.feedback_erro,
            )
            for alternativa_origem in questao_origem.alternativas.all().order_by("ordem", "id"):
                QuizAlternativa.objects.create(
                    cliente_id=aula_destino.cliente_id,
                    questao=questao_destino,
                    texto=alternativa_origem.texto,
                    is_correta=alternativa_origem.is_correta,
                    ordem=alternativa_origem.ordem,
                    feedback_especifico=alternativa_origem.feedback_especifico,
                )

    @staticmethod
    @transaction.atomic
    def clone_course(options: CourseCopyOptions) -> Curso:
        curso_origem = (
            Curso.raw_objects.select_related("categoria", "autor_principal", "cliente")
            .prefetch_related(
                "trilhas",
                "modulos__aulas__conteudos",
                "modulos__aulas__atividades__questoes__alternativas",
            )
            .get(pk=options.curso_origem.pk)
        )
        cliente_destino = options.cliente_destino
        titulo_destino = (options.novo_titulo or curso_origem.titulo).strip() or curso_origem.titulo
        slug_destino = CourseCloneService._unique_slug(
            (options.novo_slug or f"{curso_origem.slug}-{cliente_destino.slug}").strip()
        )

        curso_destino = Curso.objects.create(
            cliente=cliente_destino,
            titulo=titulo_destino,
            slug=slug_destino,
            descricao_curta=curso_origem.descricao_curta,
            descricao_longa=curso_origem.descricao_longa,
            capa=CourseCloneService._copy_file_name(curso_origem.capa),
            categoria=CourseCloneService._get_or_copy_categoria(curso_origem, cliente_destino),
            carga_horaria=curso_origem.carga_horaria,
            nivel=curso_origem.nivel,
            publico_alvo=curso_origem.publico_alvo,
            ementa=curso_origem.ementa,
            objetivos=curso_origem.objetivos,
            status=curso_origem.status if options.manter_status_publicacao else Curso.Status.RASCUNHO,
            is_aberto=curso_origem.is_aberto,
            permite_certificado=curso_origem.permite_certificado,
            nota_minima=curso_origem.nota_minima,
            progresso_minimo=curso_origem.progresso_minimo,
            autor_principal=CourseCloneService._resolve_target_author(
                curso_origem,
                cliente_destino,
                options.usuario_executor,
            ),
            data_inicio_disponibilidade=curso_origem.data_inicio_disponibilidade,
            data_fim_disponibilidade=curso_origem.data_fim_disponibilidade,
            ordem_na_trilha=curso_origem.ordem_na_trilha,
            eixos_restricao_roles=curso_origem.eixos_restricao_roles,
        )
        CourseCloneService._copy_trilhas(curso_origem, curso_destino, cliente_destino)

        modulo_map: dict[int, CursoModulo] = {}
        aula_map: dict[int, Aula] = {}

        modulos_origem = list(curso_origem.modulos.all().order_by("ordem", "id"))
        for modulo_origem in modulos_origem:
            modulo_destino = CursoModulo.objects.create(
                cliente=cliente_destino,
                curso=curso_destino,
                titulo=modulo_origem.titulo,
                descricao=modulo_origem.descricao,
                ordem=modulo_origem.ordem,
                is_active=modulo_origem.is_active,
                data_liberacao_programada=modulo_origem.data_liberacao_programada,
                eixos_restricao_roles=modulo_origem.eixos_restricao_roles,
            )
            modulo_map[modulo_origem.id] = modulo_destino

            for aula_origem in modulo_origem.aulas.all().order_by("ordem", "id"):
                aula_destino = Aula.objects.create(
                    cliente=cliente_destino,
                    modulo=modulo_destino,
                    titulo=aula_origem.titulo,
                    resumo=aula_origem.resumo,
                    ordem=aula_origem.ordem,
                    tipo=aula_origem.tipo,
                    duracao_estimada_minutos=aula_origem.duracao_estimada_minutos,
                    is_obigatoria=aula_origem.is_obigatoria,
                    is_active=aula_origem.is_active,
                    data_liberacao=aula_origem.data_liberacao,
                )
                aula_map[aula_origem.id] = aula_destino

                for conteudo_origem in aula_origem.conteudos.all().order_by("ordem", "id"):
                    ConteudoAula.objects.create(
                        cliente=cliente_destino,
                        aula=aula_destino,
                        tipo=conteudo_origem.tipo,
                        titulo=conteudo_origem.titulo,
                        descricao=conteudo_origem.descricao,
                        ordem=conteudo_origem.ordem,
                        is_obrigatorio=conteudo_origem.is_obrigatorio,
                        conteudo_texto=conteudo_origem.conteudo_texto,
                        url=conteudo_origem.url,
                        arquivo=CourseCloneService._copy_file_name(conteudo_origem.arquivo),
                        embed_code=conteudo_origem.embed_code,
                    )

                if options.copiar_atividades:
                    for atividade_origem in aula_origem.atividades.all().order_by("id"):
                        CourseCloneService._copy_atividade(atividade_origem, aula_destino)

        for modulo_origem in modulos_origem:
            if not modulo_origem.pre_requisito_modulo_id:
                continue
            modulo_destino = modulo_map[modulo_origem.id]
            modulo_destino.pre_requisito_modulo = modulo_map.get(modulo_origem.pre_requisito_modulo_id)
            modulo_destino.save(update_fields=["pre_requisito_modulo"])

        for aula_origem_id, aula_destino in aula_map.items():
            aula_origem = next(aula for modulo in modulos_origem for aula in modulo.aulas.all() if aula.id == aula_origem_id)
            if not aula_origem.pre_requisito_aula_id:
                continue
            aula_destino.pre_requisito_aula = aula_map.get(aula_origem.pre_requisito_aula_id)
            aula_destino.save(update_fields=["pre_requisito_aula"])

        return curso_destino
