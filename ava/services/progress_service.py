from django.db.models import Prefetch, Q
from django.utils import timezone

from ava.models import (
    Atividade,
    Aula,
    ConteudoAula,
    CursoModulo,
    MatriculaCurso,
    ProgressoAula,
    ProgressoConteudo,
    ProgressoModulo,
)
from ava.services.access_control import user_can_access_activity_by_eixo, user_can_access_module_by_eixo


class ProgressoService:
    """
    Servico central de calculo e registro de progressos no AVA.
    """

    @staticmethod
    def modulo_disponivel(matricula: MatriculaCurso, modulo: CursoModulo, agora=None) -> bool:
        """
        Define se um modulo pode aparecer/acessar para a matricula informada.

        A liberacao pode depender de uma data/hora programada e/ou da conclusao
        de um modulo pre-requisito. Quando os dois campos existem, ambos devem
        estar satisfeitos.
        """
        if not modulo.is_active:
            return False

        if not user_can_access_module_by_eixo(matricula.aluno, modulo):
            return False

        agora = agora or timezone.now()
        if modulo.data_liberacao_programada and modulo.data_liberacao_programada > agora:
            return False

        if modulo.pre_requisito_modulo_id:
            return ProgressoModulo.objects.filter(
                matricula=matricula,
                modulo_id=modulo.pre_requisito_modulo_id,
                is_concluido=True,
            ).exists()

        return True

    @staticmethod
    def filtrar_modulos_disponiveis(matricula: MatriculaCurso, modulos, agora=None):
        return [modulo for modulo in modulos if ProgressoService.modulo_disponivel(matricula, modulo, agora)]

    @staticmethod
    def marcar_conteudo_visualizado(aluno, conteudo_id: int):
        try:
            conteudo = ConteudoAula.objects.select_related("aula__modulo__curso").get(id=conteudo_id)
            matricula = MatriculaCurso.objects.get(curso=conteudo.aula.modulo.curso, aluno=aluno)
        except (ConteudoAula.DoesNotExist, MatriculaCurso.DoesNotExist):
            return False

        # Cria a árvore de progresso se não existir.
        ProgressoService._garantir_progressos(matricula, conteudo.aula)

        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=conteudo.aula)
        prog_conteudo, _ = ProgressoConteudo.objects.get_or_create(
            progresso_aula=prog_aula,
            conteudo=conteudo,
            defaults={"cliente_id": matricula.cliente_id},
        )

        if not prog_conteudo.is_visualizado:
            prog_conteudo.is_visualizado = True
            prog_conteudo.data_visualizacao = timezone.now()
            prog_conteudo.save(update_fields=["is_visualizado", "data_visualizacao"])

            # Recalcula aula, modulo e curso.
            ProgressoService.recalcular_aula(matricula, conteudo.aula)
            return True
        return False

    @staticmethod
    def marcar_aula_visualizada(matricula: MatriculaCurso, aula: Aula):
        """
        Registra automaticamente a visualização dos conteúdos da aula.

        O AVA passa a considerar o acesso/avanco pela aula como consumo do
        conteudo, sem exigir que o aluno clique manualmente em "marcar como
        lido" para que o progresso avance.
        """
        ProgressoService._garantir_progressos(matricula, aula)

        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=aula)
        conteudos = list(ConteudoAula.objects.filter(aula=aula).order_by("ordem", "id"))
        if not conteudos:
            ProgressoService.recalcular_aula(matricula, aula)
            return 0

        agora = timezone.now()
        marcados = 0
        for conteudo in conteudos:
            prog_conteudo, _ = ProgressoConteudo.objects.get_or_create(
                progresso_aula=prog_aula,
                conteudo=conteudo,
                defaults={"cliente_id": matricula.cliente_id},
            )
            if prog_conteudo.is_visualizado:
                continue
            prog_conteudo.is_visualizado = True
            prog_conteudo.data_visualizacao = agora
            prog_conteudo.save(update_fields=["is_visualizado", "data_visualizacao"])
            marcados += 1

        ProgressoService.recalcular_aula(matricula, aula)
        return marcados

    @staticmethod
    def _garantir_progressos(matricula, aula):
        ProgressoModulo.objects.get_or_create(
            matricula=matricula,
            modulo=aula.modulo,
            defaults={"cliente_id": matricula.cliente_id},
        )
        ProgressoAula.objects.get_or_create(
            matricula=matricula,
            aula=aula,
            defaults={"cliente_id": matricula.cliente_id},
        )

    @staticmethod
    def sincronizar_matricula(matricula: MatriculaCurso):
        """
        Recalcula a matrícula contra a estrutura atual do curso.

        Isso cobre cenários em que módulos, aulas ou conteúdos obrigatórios
        foram adicionados após o aluno já ter concluído o curso.
        """
        modulos = list(
            matricula.curso.modulos.filter(is_active=True)
            .prefetch_related("aulas")
            .order_by("ordem", "id")
        )

        for modulo in modulos:
            if not ProgressoService.modulo_disponivel(matricula, modulo):
                continue
            ProgressoModulo.objects.get_or_create(
                matricula=matricula,
                modulo=modulo,
                defaults={"cliente_id": matricula.cliente_id},
            )
            aulas = list(modulo.aulas.filter(is_active=True).order_by("ordem", "id"))
            for aula in aulas:
                ProgressoService._garantir_progressos(matricula, aula)
                ProgressoService.recalcular_aula(matricula, aula)
            ProgressoService.recalcular_modulo(matricula, modulo)

        ProgressoService.recalcular_curso(matricula)
        matricula.refresh_from_db(fields=["status", "progresso_percentual", "data_conclusao"])
        return matricula

    @staticmethod
    def sincronizar_matricula_rapida(matricula: MatriculaCurso):
        """
        Sincronizacao leve para telas de navegacao.

        Evita recalcular todas as aulas/atividades em cada GET. Garante apenas
        que a arvore de progresso exista para modulos/aulas disponiveis e
        atualiza o percentual do curso a partir dos percentuais ja calculados.
        Recalculos completos continuam acontecendo quando o aluno consome aula,
        envia atividade ou quando uma rotina administrativa chamar
        sincronizar_matricula().
        """
        if (
            matricula.status == MatriculaCurso.Status.CONCLUIDA
            and ProgressoService._matricula_concluida_precisa_resync(matricula)
        ):
            return ProgressoService.sincronizar_matricula(matricula)

        modulos = list(
            matricula.curso.modulos.filter(is_active=True)
            .select_related("pre_requisito_modulo")
            .prefetch_related(
                "eixos",
                Prefetch("aulas", queryset=Aula.objects.filter(is_active=True).order_by("ordem", "id")),
            )
            .order_by("ordem", "id")
        )
        modulos = ProgressoService.filtrar_modulos_disponiveis(matricula, modulos)
        if not modulos:
            ProgressoService.recalcular_curso(matricula, modulos_disponiveis=modulos)
            matricula.refresh_from_db(fields=["status", "progresso_percentual", "data_conclusao"])
            return matricula

        modulo_ids = [modulo.id for modulo in modulos]
        progressos_modulos_existentes = set(
            ProgressoModulo.objects.filter(matricula=matricula, modulo_id__in=modulo_ids)
            .values_list("modulo_id", flat=True)
        )
        ProgressoModulo.objects.bulk_create(
            [
                ProgressoModulo(matricula=matricula, modulo=modulo, cliente_id=matricula.cliente_id)
                for modulo in modulos
                if modulo.id not in progressos_modulos_existentes
            ],
            ignore_conflicts=True,
        )

        aulas = [aula for modulo in modulos for aula in modulo.aulas.all()]
        aula_ids = [aula.id for aula in aulas]
        if aula_ids:
            progressos_aulas_existentes = set(
                ProgressoAula.objects.filter(matricula=matricula, aula_id__in=aula_ids)
                .values_list("aula_id", flat=True)
            )
            ProgressoAula.objects.bulk_create(
                [
                    ProgressoAula(matricula=matricula, aula=aula, cliente_id=matricula.cliente_id)
                    for aula in aulas
                    if aula.id not in progressos_aulas_existentes
                ],
                ignore_conflicts=True,
            )

        ProgressoService.recalcular_curso(matricula, modulos_disponiveis=modulos)
        matricula.refresh_from_db(fields=["status", "progresso_percentual", "data_conclusao"])
        return matricula

    @staticmethod
    def _matricula_concluida_precisa_resync(matricula: MatriculaCurso) -> bool:
        modulo_ids = list(
            matricula.curso.modulos.filter(is_active=True).values_list("id", flat=True)
        )
        if not modulo_ids:
            return False

        progressos_modulos = ProgressoModulo.objects.filter(
            matricula=matricula,
            modulo_id__in=modulo_ids,
        ).count()
        if progressos_modulos < len(modulo_ids):
            return True

        aula_ids = list(
            Aula.objects.filter(modulo_id__in=modulo_ids, is_active=True).values_list("id", flat=True)
        )
        if not aula_ids:
            return False

        progressos_aulas = ProgressoAula.objects.filter(
            matricula=matricula,
            aula_id__in=aula_ids,
        ).count()
        if progressos_aulas < len(aula_ids):
            return True

        conteudos_obrigatorios = ConteudoAula.objects.filter(
            aula_id__in=aula_ids,
            is_obrigatorio=True,
        ).count()
        if not conteudos_obrigatorios:
            return False

        progressos_conteudos = ProgressoConteudo.objects.filter(
            progresso_aula__matricula=matricula,
            conteudo__aula_id__in=aula_ids,
            conteudo__is_obrigatorio=True,
        ).count()
        return progressos_conteudos < conteudos_obrigatorios

    @staticmethod
    def recalcular_aula(matricula: MatriculaCurso, aula: Aula):
        """
        Verifica se a aula foi concluída com base nos conteúdos obrigatórios.
        e atividades obrigatorias validas.
        """
        prog_aula = ProgressoAula.objects.get(matricula=matricula, aula=aula)

        qt_conteudos = ConteudoAula.objects.filter(aula=aula, is_obrigatorio=True).count()
        qt_visualizados = ProgressoConteudo.objects.filter(
            progresso_aula=prog_aula,
            conteudo__is_obrigatorio=True,
            is_visualizado=True,
        ).count()

        # Para ENVIO_ARQUIVO, so conta se houver arquivo anexado.
        atividades_obrigatorias = [
            atividade
            for atividade in Atividade.objects.filter(aula=aula, is_obrigatoria=True).prefetch_related("eixos")
            if user_can_access_activity_by_eixo(matricula.aluno, atividade)
        ]
        atividade_ids = [atividade.id for atividade in atividades_obrigatorias]
        qt_atividades = len(atividade_ids)
        if atividade_ids:
            qt_tentativas = (
                Atividade.objects.filter(id__in=atividade_ids)
                .filter(
                    tentativas__aluno=matricula.aluno,
                    tentativas__status__in=["enviada", "corrigida"],
                )
                .filter(
                    ~Q(tipo=Atividade.Tipo.ENVIO_ARQUIVO)
                    | (
                        Q(tipo=Atividade.Tipo.ENVIO_ARQUIVO)
                        & (
                            Q(tentativas__arquivos__isnull=False)
                            | (Q(tentativas__arquivo_enviado__isnull=False) & ~Q(tentativas__arquivo_enviado=""))
                        )
                    )
                )
                .distinct()
                .count()
            )
        else:
            qt_tentativas = 0

        is_concluida = (qt_visualizados >= qt_conteudos) and (qt_tentativas >= qt_atividades)

        if is_concluida and not prog_aula.is_concluida:
            prog_aula.is_concluida = True
            prog_aula.data_conclusao = timezone.now()
            prog_aula.save(update_fields=["is_concluida", "data_conclusao"])
            ProgressoService.recalcular_modulo(matricula, aula.modulo)
        elif not is_concluida and prog_aula.is_concluida:
            prog_aula.is_concluida = False
            prog_aula.data_conclusao = None
            prog_aula.save(update_fields=["is_concluida", "data_conclusao"])
            ProgressoService.recalcular_modulo(matricula, aula.modulo)

    @staticmethod
    def recalcular_modulo(matricula: MatriculaCurso, modulo):
        aulas_modulo = list(Aula.objects.filter(modulo=modulo, is_obigatoria=True))
        for aula in aulas_modulo:
            prog_aula, _ = ProgressoAula.objects.get_or_create(
                matricula=matricula,
                aula=aula,
                defaults={"cliente_id": matricula.cliente_id},
            )
            tem_obrigacoes = ConteudoAula.objects.filter(aula=aula, is_obrigatorio=True).exists() or Atividade.objects.filter(
                aula=aula,
                is_obrigatoria=True,
            ).exists()
            if not tem_obrigacoes and not prog_aula.is_concluida:
                prog_aula.is_concluida = True
                prog_aula.data_conclusao = timezone.now()
                prog_aula.save(update_fields=["is_concluida", "data_conclusao"])

        prog_modulo = ProgressoModulo.objects.get(matricula=matricula, modulo=modulo)
        aulas_obrig = len(aulas_modulo)

        aulas_concluidas = ProgressoAula.objects.filter(
            matricula=matricula,
            aula__modulo=modulo,
            aula__is_obigatoria=True,
            is_concluida=True,
        ).count()

        percent = min(100, int((aulas_concluidas / aulas_obrig) * 100)) if aulas_obrig > 0 else 100
        prog_modulo.percentual = percent

        if percent >= 100 and not prog_modulo.is_concluido:
            prog_modulo.is_concluido = True
            prog_modulo.data_conclusao = timezone.now()
        elif percent < 100 and prog_modulo.is_concluido:
            prog_modulo.is_concluido = False
            prog_modulo.data_conclusao = None

        prog_modulo.save(update_fields=["percentual", "is_concluido", "data_conclusao"])

        # Propaga recalculo para o curso.
        ProgressoService.recalcular_curso(matricula)

    @staticmethod
    def recalcular_curso(matricula: MatriculaCurso, modulos_disponiveis=None):
        if modulos_disponiveis is None:
            modulos = list(matricula.curso.modulos.filter(is_active=True).prefetch_related("eixos").order_by("ordem", "id"))
            modulos_ids = [
                modulo.id for modulo in modulos if ProgressoService.modulo_disponivel(matricula, modulo)
            ]
        else:
            modulos_ids = [modulo.id for modulo in modulos_disponiveis]

        if modulos_ids:
            percentuais = {
                modulo_id: percentual
                for modulo_id, percentual in ProgressoModulo.objects.filter(
                    matricula=matricula,
                    modulo_id__in=modulos_ids,
                ).values_list("modulo_id", "percentual")
            }
            percent = min(100, int(sum(percentuais.get(modulo_id, 0) for modulo_id in modulos_ids) / len(modulos_ids)))
        elif matricula.status == MatriculaCurso.Status.CONCLUIDA:
            percent = 100
        else:
            percent = min(100, matricula.progresso_percentual)
        matricula.progresso_percentual = percent

        if percent >= matricula.curso.progresso_minimo and matricula.status != "concluida":
            # Poderia checar nota minima tambem.
            matricula.status = "concluida"
            matricula.data_conclusao = timezone.now()
        elif percent < matricula.curso.progresso_minimo and matricula.status == MatriculaCurso.Status.CONCLUIDA:
            matricula.status = MatriculaCurso.Status.ATIVA
            matricula.data_conclusao = None

        matricula.save(update_fields=["progresso_percentual", "status", "data_conclusao"])
