"""Tutorial guiado da área de GTs.

Monta um roteiro passo a passo que leva o administrador a cada página na ordem
correta, dizendo o que preencher, e opcionalmente cria um **exemplo de
demonstração** (claramente identificado) para a pessoa percorrer o fluxo
completo sem tocar nos dados oficiais.

O estado de cada passo é calculado a partir dos dados reais do município, então
o roteiro mostra o que já foi feito e o que falta — nada é marcado como pronto
sem existir no banco.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from ava.models.gt_sala import (
    AtaReuniaoGT,
    CicloReferencial,
    InscricaoSalaGT,
    ModeloAtaGT,
    ObjetivoReferencial,
    PresencaReuniaoGT,
    ReuniaoGT,
    SalaGT,
    TrabalhoGT,
)
from ava.services.audit_service import AVAAuditService
from ava.services.gt_access import e_admin_referencial
from ava.services.gt_sala_service import SalaGTService
from curriculum.models import GT
from exports.models import ExportJob


#: Marcadores do exemplo de demonstração — permitem identificar e remover tudo.
NOME_CICLO_EXEMPLO = "Ciclo de demonstração (exemplo)"
PREFIXO_CODIGO_EXEMPLO = "DEMO-"

OBJETIVOS_EXEMPLO = [
    {
        "codigo": f"{PREFIXO_CODIGO_EXEMPLO}01",
        "titulo": "Exemplo: ampliar a alfabetização na idade certa",
        "texto": (
            "Texto de demonstração. Substitua pela redação oficial do objetivo do "
            "Referencial da rede."
        ),
    },
    {
        "codigo": f"{PREFIXO_CODIGO_EXEMPLO}02",
        "titulo": "Exemplo: fortalecer a formação continuada dos professores",
        "texto": (
            "Texto de demonstração. Substitua pela redação oficial do objetivo do "
            "Referencial da rede."
        ),
    },
]


@dataclass
class Passo:
    """Um passo do roteiro, com link e estado calculado."""

    numero: int
    titulo: str
    objetivo: str
    como_fazer: list[str]
    exemplo: str = ""
    url: str = ""
    rotulo_acao: str = "Abrir a página"
    concluido: bool = False
    situacao: str = ""
    quem_faz: str = "Administração do Referencial"
    bloqueado_por: str = ""


def _url(nome: str, cliente, ciclo=None, **kwargs) -> str:
    """URL da página do passo, já com o município (e o ciclo) no contexto."""

    destino = reverse(nome, kwargs=kwargs or None)
    parametros = [f"municipio={cliente.id}"]
    if ciclo is not None:
        parametros.append(f"ciclo={ciclo.pk}")
    return f"{destino}?{'&'.join(parametros)}"


class TutorialGTService:
    """Estado do roteiro e criação/remoção do exemplo de demonstração."""

    # ------------------------------------------------------------------
    # Roteiro
    # ------------------------------------------------------------------
    @staticmethod
    def montar_roteiro(cliente, ciclo: CicloReferencial | None) -> list[Passo]:
        objetivos_ativos = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente, ativo=True
        ).count()

        salas = SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente)
        if ciclo is not None:
            salas = salas.filter(ciclo=ciclo)
        salas = list(salas.select_related("objetivo", "gt"))
        primeira_sala = salas[0] if salas else None

        salas_ids = [sala.pk for sala in salas]
        com_coordenacao = (
            InscricaoSalaGT.raw_objects.filter(
                is_deleted=False,
                sala_id__in=salas_ids,
                estado=InscricaoSalaGT.Estado.CONFIRMADA,
                papel=InscricaoSalaGT.Papel.COORDENACAO,
            )
            .values_list("sala_id", flat=True)
            .distinct()
            .count()
        )
        confirmadas = InscricaoSalaGT.raw_objects.filter(
            is_deleted=False, sala_id__in=salas_ids, estado=InscricaoSalaGT.Estado.CONFIRMADA
        ).count()
        trabalhos = list(
            TrabalhoGT.raw_objects.filter(is_deleted=False, sala_id__in=salas_ids)
        )
        com_diagnostico = sum(1 for item in trabalhos if item.diagnostico_preenchido)
        aprovados = sum(1 for item in trabalhos if item.consolidavel)
        reunioes = ReuniaoGT.raw_objects.filter(is_deleted=False, sala_id__in=salas_ids).count()
        frequencias_validadas = ReuniaoGT.raw_objects.filter(
            is_deleted=False, sala_id__in=salas_ids, frequencia_validada=True
        ).count()
        atas_validadas = AtaReuniaoGT.raw_objects.filter(
            is_deleted=False,
            reuniao__sala_id__in=salas_ids,
            estado=AtaReuniaoGT.Estado.VALIDADA,
        ).count()
        modelo = ModeloAtaGT.raw_objects.filter(
            is_deleted=False, cliente=cliente, ativo=True
        ).first()
        documentos = ExportJob.raw_objects.filter(
            is_deleted=False,
            cliente=cliente,
            alvo_tipo__in=[
                ExportJob.AlvoTipo.GT_OBJETIVO,
                ExportJob.AlvoTipo.GT_ATA,
            ],
        ).count()
        consolidacoes = ExportJob.raw_objects.filter(
            is_deleted=False, cliente=cliente, alvo_tipo=ExportJob.AlvoTipo.GT_CONSOLIDADO
        ).count()

        passos: list[Passo] = [
            Passo(
                numero=1,
                titulo="Cadastrar os objetivos oficiais do Referencial",
                objetivo=(
                    "As salas nascem dos objetivos. Nenhum texto de objetivo é inventado "
                    "pelo sistema: eles vêm do documento oficial da rede."
                ),
                como_fazer=[
                    "Abra “Objetivos” e use “Novo objetivo” para cadastrar um a um, ou",
                    "cole a lista inteira no bloco de importação (CSV ou JSON) e clique em “Importar”.",
                    "O campo “Código” é o identificador estável: não mude depois de publicado.",
                ],
                exemplo="01;Ampliar a alfabetização na idade certa;Redação oficial do objetivo;1",
                url=_url("ava:gt_objetivos", cliente),
                rotulo_acao="Cadastrar/importar objetivos",
                concluido=objetivos_ativos > 0,
                situacao=f"{objetivos_ativos} objetivo(s) ativo(s) cadastrado(s).",
            ),
            Passo(
                numero=2,
                titulo="Criar o ciclo de trabalho",
                objetivo=(
                    "O ciclo define o período, a janela de inscrição e as regras mínimas "
                    "para aprovar o conteúdo dos GTs."
                ),
                como_fazer=[
                    "Dê um nome ao ciclo (ex.: “Ciclo 2026”) e marque “Ciclo ativo”.",
                    "Defina a janela de inscrição e se a confirmação é automática.",
                    "Ajuste o limite de GTs por participante e os mínimos de metas/estratégias.",
                ],
                exemplo="Nome: Ciclo 2026 · inscrições de 01/03 a 31/03 · 1 GT por participante",
                url=_url("ava:gt_ciclo_novo", cliente),
                rotulo_acao="Criar ciclo",
                concluido=ciclo is not None,
                situacao=(
                    f"Ciclo selecionado: {ciclo.nome}." if ciclo else "Nenhum ciclo cadastrado."
                ),
            ),
            Passo(
                numero=3,
                titulo="Gerar uma sala por objetivo",
                objetivo=(
                    "Cada objetivo ganha uma sala de GT no ciclo. A geração reaproveita os "
                    "GTs já cadastrados no Referencial e ignora objetivos que já têm sala."
                ),
                como_fazer=[
                    "No painel de administração, informe o limite de participantes (opcional).",
                    "Marque “Criar o GT quando ainda não existir” se os GTs ainda não estiverem cadastrados.",
                    "Clique em “Criar uma sala por objetivo ativo”.",
                ],
                exemplo="Limite de 12 participantes por sala, criando os GTs que faltarem.",
                url=_url("ava:gt_admin", cliente, ciclo),
                rotulo_acao="Abrir o painel e gerar as salas",
                concluido=bool(salas),
                situacao=f"{len(salas)} sala(s) no ciclo selecionado.",
                bloqueado_por="" if (ciclo and objetivos_ativos) else "Conclua os passos 1 e 2.",
            ),
            Passo(
                numero=4,
                titulo="Definir a coordenação e a relatoria de cada sala",
                objetivo=(
                    "Coordenação valida frequência, ata e conteúdo; relatoria escreve o "
                    "diagnóstico, as metas e as estratégias. Só a administração concede "
                    "coordenação."
                ),
                como_fazer=[
                    "Abra a aba “Inscrições” da sala.",
                    "Use “Inscrever participante” escolhendo o papel Coordenação do GT.",
                    "Repita escolhendo Relatoria para quem vai redigir.",
                ],
                exemplo="Coordenação: coordenador(a) pedagógico(a) · Relatoria: professor(a) redator(a)",
                url=(
                    _url("ava:gt_sala_inscricoes", cliente, sala_id=primeira_sala.pk)
                    if primeira_sala
                    else ""
                ),
                rotulo_acao="Abrir inscrições da primeira sala",
                concluido=com_coordenacao > 0,
                situacao=(
                    f"{com_coordenacao} de {len(salas)} sala(s) com coordenação definida · "
                    f"{confirmadas} participante(s) confirmado(s)."
                ),
                bloqueado_por="" if primeira_sala else "Gere as salas no passo 3.",
            ),
            Passo(
                numero=5,
                titulo="Abrir as inscrições para a rede",
                objetivo=(
                    "Com as inscrições abertas, qualquer pessoa do município vê as salas e "
                    "pede participação; a capacidade e a lista de espera são respeitadas "
                    "automaticamente."
                ),
                como_fazer=[
                    "Edite o ciclo e marque “Inscrições abertas”.",
                    "Confira a janela de datas e a lista de espera.",
                    "Na lista de salas, confirme que aparece “Inscrições: Abertas”.",
                ],
                exemplo="Inscrições abertas com lista de espera habilitada.",
                url=(
                    _url("ava:gt_ciclo_editar", cliente, ciclo_id=ciclo.pk) if ciclo else ""
                ),
                rotulo_acao="Editar o ciclo",
                concluido=bool(ciclo and ciclo.inscricoes_abertas),
                situacao=(
                    "Inscrições abertas."
                    if (ciclo and ciclo.inscricoes_abertas)
                    else "Inscrições fechadas."
                ),
                bloqueado_por="" if ciclo else "Crie o ciclo no passo 2.",
            ),
            Passo(
                numero=6,
                titulo="Preencher o diagnóstico e o quadro do objetivo",
                objetivo=(
                    "É aqui que o GT registra a situação atual, a proposta de redação do "
                    "objetivo, as metas e as estratégias."
                ),
                como_fazer=[
                    "Abra a aba “Diagnóstico e quadro do objetivo” da sala.",
                    "Preencha o diagnóstico (ou marque que ele não se aplica) e salve.",
                    "Adicione pelo menos uma meta e uma estratégia, vinculando a estratégia à meta.",
                ],
                exemplo=(
                    "Meta: ampliar a formação continuada em 30% até 2026 · "
                    "Estratégia: oficinas mensais com acompanhamento pedagógico"
                ),
                url=(
                    _url("ava:gt_sala_trabalho", cliente, sala_id=primeira_sala.pk)
                    if primeira_sala
                    else ""
                ),
                rotulo_acao="Abrir o quadro da primeira sala",
                quem_faz="Relatoria ou coordenação do GT",
                concluido=com_diagnostico > 0,
                situacao=f"{com_diagnostico} de {len(salas)} sala(s) com diagnóstico registrado.",
                bloqueado_por="" if primeira_sala else "Gere as salas no passo 3.",
            ),
            Passo(
                numero=7,
                titulo="Registrar a reunião e lançar a frequência",
                objetivo=(
                    "A frequência é sempre ligada a uma reunião e aos membros confirmados do "
                    "GT — nunca inferida por login. Depois de validada, só muda com "
                    "justificativa registrada na auditoria."
                ),
                como_fazer=[
                    "Na aba “Reuniões e frequência”, crie a reunião (data, pauta, modalidade).",
                    "Marque presente/ausente/justificada para cada membro e salve.",
                    "Clique em “Conferir e validar” para fechar a frequência.",
                ],
                exemplo="Reunião de abertura · 10/03/2026 14:00 · presencial na Secretaria",
                url=(
                    _url("ava:gt_sala_reunioes", cliente, sala_id=primeira_sala.pk)
                    if primeira_sala
                    else ""
                ),
                rotulo_acao="Abrir reuniões da primeira sala",
                quem_faz="Coordenação do GT (relatoria pode lançar)",
                concluido=reunioes > 0,
                situacao=(
                    f"{reunioes} reunião(ões) registrada(s) · "
                    f"{frequencias_validadas} com frequência validada."
                ),
                bloqueado_por="" if primeira_sala else "Gere as salas no passo 3.",
            ),
            Passo(
                numero=8,
                titulo="Publicar o modelo de ata e validar a primeira ata",
                objetivo=(
                    "O modelo é comum a todos os GTs e versionado: publicar uma nova versão "
                    "não altera as atas já geradas."
                ),
                como_fazer=[
                    "Publique o modelo em “Administrar modelo de ata” (opcional: sem modelo, valem as seções padrão).",
                    "Na reunião, clique em “Criar minuta”, preencha a síntese e as decisões.",
                    "A coordenação clica em “Validar ata”.",
                ],
                exemplo="Modelo “Ata institucional” v1 com as seções padrão.",
                url=_url("ava:gt_modelo_ata", cliente),
                rotulo_acao="Administrar modelo de ata",
                concluido=bool(modelo) or atas_validadas > 0,
                situacao=(
                    (f"Modelo em uso: {modelo.nome} v{modelo.versao}. " if modelo else "Nenhum modelo publicado. ")
                    + f"{atas_validadas} ata(s) validada(s)."
                ),
            ),
            Passo(
                numero=9,
                titulo="Enviar para revisão, aprovar e publicar o conteúdo",
                objetivo=(
                    "A aprovação congela a versão do conteúdo. Depois disso, só a "
                    "administração reabre, com justificativa auditada."
                ),
                como_fazer=[
                    "A relatoria clica em “Enviar para revisão” no quadro do objetivo.",
                    "A coordenação resolve as pendências listadas e clica em “Aprovar conteúdo”.",
                    "Em seguida, “Publicar” libera a versão para leitura institucional.",
                ],
                exemplo="Pendências típicas: diagnóstico vazio, nenhuma meta, ata não validada.",
                url=(
                    _url("ava:gt_sala_trabalho", cliente, sala_id=primeira_sala.pk)
                    if primeira_sala
                    else ""
                ),
                rotulo_acao="Abrir o quadro para revisar",
                quem_faz="Relatoria envia · coordenação aprova",
                concluido=aprovados > 0,
                situacao=f"{aprovados} de {len(salas)} sala(s) com conteúdo aprovado ou publicado.",
                bloqueado_por="" if primeira_sala else "Gere as salas no passo 3.",
            ),
            Passo(
                numero=10,
                titulo="Gerar os documentos do GT e a consolidação institucional",
                objetivo=(
                    "Documento do objetivo, ata e consolidação saem em DOCX válido, com "
                    "download protegido por permissão."
                ),
                como_fazer=[
                    "Na aba “Documentos e histórico” da sala, clique em “Gerar documento do objetivo”.",
                    "Na reunião, use “Gerar DOCX” para a ata.",
                    "No painel do ciclo, clique em “Gerar consolidação DOCX” (padrão: todos os objetivos).",
                ],
                exemplo="referencial_ciclo-2026_obj-01_quadro-objetivo_v3_2026-03-20.docx",
                url=(
                    _url("ava:gt_sala_documentos", cliente, sala_id=primeira_sala.pk)
                    if primeira_sala
                    else ""
                ),
                rotulo_acao="Abrir documentos da primeira sala",
                concluido=documentos > 0 or consolidacoes > 0,
                situacao=(
                    f"{documentos} documento(s) de GT e {consolidacoes} consolidação(ões) geradas."
                ),
                bloqueado_por="" if primeira_sala else "Gere as salas no passo 3.",
            ),
        ]
        return passos

    @staticmethod
    def progresso(passos: list[Passo]) -> dict:
        concluidos = sum(1 for passo in passos if passo.concluido)
        total = len(passos) or 1
        proximo = next((passo for passo in passos if not passo.concluido), None)
        return {
            "concluidos": concluidos,
            "total": len(passos),
            "percentual": int(round(100 * concluidos / total)),
            "proximo": proximo,
        }

    # ------------------------------------------------------------------
    # Exemplo de demonstração
    # ------------------------------------------------------------------
    @staticmethod
    def ciclo_exemplo(cliente) -> CicloReferencial | None:
        return CicloReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente, nome=NOME_CICLO_EXEMPLO
        ).first()

    @staticmethod
    @transaction.atomic
    def criar_exemplo(cliente, usuario) -> CicloReferencial:
        """Cria um ciclo de demonstração completo, identificado como exemplo.

        Serve para percorrer o fluxo inteiro sem encostar nos dados oficiais:
        dois objetivos com código ``DEMO-``, as salas correspondentes, o usuário
        como coordenação e uma reunião com a lista de presença pronta.
        """

        if not e_admin_referencial(usuario):
            raise PermissionDenied("Apenas a administração do Referencial cria o exemplo.")

        ciclo = TutorialGTService.ciclo_exemplo(cliente)
        if ciclo is None:
            hoje = timezone.localdate()
            ciclo = CicloReferencial(
                cliente=cliente,
                nome=NOME_CICLO_EXEMPLO,
                descricao=(
                    "Ciclo criado pelo tutorial guiado para demonstração. "
                    "Pode ser removido a qualquer momento sem afetar os dados oficiais."
                ),
                inicio=hoje,
                fim=hoje + timedelta(days=90),
                ativo=True,
                inscricoes_abertas=True,
                confirmacao_automatica=True,
                permite_lista_espera=True,
                min_metas_para_aprovacao=1,
                min_estrategias_para_aprovacao=1,
            )
            ciclo.full_clean()
            ciclo.save()

        for posicao, dados in enumerate(OBJETIVOS_EXEMPLO, start=1):
            objetivo = ObjetivoReferencial.raw_objects.filter(
                is_deleted=False, cliente=cliente, codigo=dados["codigo"]
            ).first()
            if objetivo is None:
                objetivo = ObjetivoReferencial(cliente=cliente, codigo=dados["codigo"])
            objetivo.titulo = dados["titulo"]
            objetivo.texto = dados["texto"]
            # Ordem alta para o exemplo não se misturar à ordem oficial.
            objetivo.ordem = 900 + posicao
            objetivo.ativo = True
            objetivo.full_clean()
            objetivo.save()

            gt = GT.raw_objects.filter(
                is_deleted=False, cliente=cliente, nome=f"GT {objetivo.codigo} (exemplo)"
            ).first()
            if gt is None:
                gt = GT.objects.create(
                    cliente=cliente,
                    nome=f"GT {objetivo.codigo} (exemplo)",
                    etapa="Demonstração",
                )

            sala = SalaGT.raw_objects.filter(
                is_deleted=False, cliente=cliente, ciclo=ciclo, objetivo=objetivo
            ).first()
            if sala is None:
                sala = SalaGT(
                    cliente=cliente,
                    ciclo=ciclo,
                    objetivo=objetivo,
                    gt=gt,
                    capacidade=10,
                    observacoes="Sala de demonstração criada pelo tutorial guiado.",
                )
                sala.full_clean()
                sala.save()
            SalaGTService.garantir_trabalho(sala)

        primeira_sala = (
            SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente, ciclo=ciclo)
            .select_related("objetivo", "gt", "ciclo")
            .order_by("objetivo__ordem")
            .first()
        )
        if primeira_sala is not None:
            inscricao = InscricaoSalaGT.raw_objects.filter(
                is_deleted=False, sala=primeira_sala, usuario=usuario
            ).first()
            if inscricao is None:
                inscricao = SalaGTService.solicitar_inscricao(
                    primeira_sala, usuario, forcar_confirmacao=True
                )
            if inscricao.papel != InscricaoSalaGT.Papel.COORDENACAO:
                SalaGTService.definir_papel(
                    inscricao, usuario, papel=InscricaoSalaGT.Papel.COORDENACAO
                )

            if not ReuniaoGT.raw_objects.filter(is_deleted=False, sala=primeira_sala).exists():
                from ava.services.gt_reuniao_service import ReuniaoGTService

                reuniao = ReuniaoGT(
                    cliente=cliente,
                    sala=primeira_sala,
                    titulo="Reunião de demonstração",
                    data_hora=timezone.now(),
                    pauta="1. Apresentação do objetivo\n2. Diagnóstico inicial\n3. Encaminhamentos",
                    modalidade=ReuniaoGT.Modalidade.PRESENCIAL,
                    local="Secretaria Municipal de Educação (exemplo)",
                    responsavel_registro=usuario,
                )
                ReuniaoGTService.salvar_reuniao(reuniao, usuario, criando=True)

        AVAAuditService.registrar(
            cliente_id=cliente.id,
            usuario=usuario,
            entidade="ava.CicloReferencial",
            entidade_id=ciclo.pk,
            acao="exemplo_tutorial_criado",
            diff={"ciclo": ciclo.nome, "objetivos": [d["codigo"] for d in OBJETIVOS_EXEMPLO]},
        )
        return ciclo

    @staticmethod
    @transaction.atomic
    def remover_exemplo(cliente, usuario) -> dict:
        """Remove (soft delete) todo o exemplo de demonstração."""

        if not e_admin_referencial(usuario):
            raise PermissionDenied("Apenas a administração do Referencial remove o exemplo.")

        ciclo = TutorialGTService.ciclo_exemplo(cliente)
        removidos = {"salas": 0, "objetivos": 0, "ciclo": 0}
        if ciclo is None:
            return removidos

        salas = list(SalaGT.raw_objects.filter(is_deleted=False, cliente=cliente, ciclo=ciclo))
        for sala in salas:
            for reuniao in ReuniaoGT.raw_objects.filter(is_deleted=False, sala=sala):
                PresencaReuniaoGT.raw_objects.filter(
                    is_deleted=False, reuniao=reuniao
                ).update(is_deleted=True)
                AtaReuniaoGT.raw_objects.filter(is_deleted=False, reuniao=reuniao).update(
                    is_deleted=True
                )
                reuniao.delete()
            InscricaoSalaGT.raw_objects.filter(is_deleted=False, sala=sala).update(
                is_deleted=True
            )
            TrabalhoGT.raw_objects.filter(is_deleted=False, sala=sala).update(is_deleted=True)
            sala.delete()
            removidos["salas"] += 1

        objetivos = ObjetivoReferencial.raw_objects.filter(
            is_deleted=False, cliente=cliente, codigo__startswith=PREFIXO_CODIGO_EXEMPLO
        )
        removidos["objetivos"] = objetivos.count()
        for objetivo in objetivos:
            objetivo.delete()

        ciclo.delete()
        removidos["ciclo"] = 1

        AVAAuditService.registrar(
            cliente_id=cliente.id,
            usuario=usuario,
            entidade="ava.CicloReferencial",
            entidade_id=ciclo.pk,
            acao="exemplo_tutorial_removido",
            diff=removidos,
        )
        return removidos
