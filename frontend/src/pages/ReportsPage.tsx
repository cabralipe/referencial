import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { StatCard } from '@/components/dashboard/StatCard';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAuditLogs, useOnlineUsers, useSessionHistory } from '@/hooks/useAuditLogs';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useRespostas } from '@/hooks/useRespostas';
import { useUsuariosLookup } from '@/hooks/useUsuariosLookup';
import { useAuth } from '@/context/AuthContext';
import { fetchAllPaginated } from '@/utils/pagination';
import { useCreateExportJob } from '@/hooks/useExportJobs';
import type { Pergunta, Revisao } from '@/api/types';

import './ReportsPage.css';

type RankedItem = { total: number };

interface EscolaMetric extends RankedItem {
  escola: string;
}

interface ComponenteMetric extends RankedItem {
  componente_curricular: string;
}

interface StatusMetric extends RankedItem {
  status: string;
}

interface AutorMetric extends RankedItem {
  autor_id: number;
  nome: string;
  email: string;
}

interface CuradoriaMetric extends RankedItem {
  status_curadoria: string;
}

interface ProducaoMensalMetric extends RankedItem {
  mes: string;
}

interface AnalyticsAdminDashboardData {
  engajamento_por_escola: EscolaMetric[];
  producao_por_componente: ComponenteMetric[];
  producao_por_status?: StatusMetric[];
  top_autores?: AutorMetric[];
  curadoria_por_status?: CuradoriaMetric[];
  producao_mensal?: ProducaoMensalMetric[];
  media_avaliacao_rubrica: number;
  media_progresso_cursos?: number;
  total_avaliacoes?: number;
  cursos_concluidos?: number;
  cursos_em_andamento?: number;
  planos_publicados: number;
  certificados_emitidos: number;
  totais?: {
    total_planos: number;
    planos_ultimos_30_dias: number;
    autores_ativos: number;
  };
}

export function ReportsPage() {
  const { user } = useAuth();
  const client = useApiClient();
  const { data: onlineUsers, isLoading: onlineLoading } = useOnlineUsers();
  const { data: sessionHistory, isLoading: sessionsLoading } = useSessionHistory();
  const aiAssist = useAiAssist();
  const criarExportacao = useCreateExportJob();

  const [redatorQuery, setRedatorQuery] = useState('');
  const [selectedRedator, setSelectedRedator] = useState<{ id: number; nome: string; email: string } | null>(null);
  const [periodDays, setPeriodDays] = useState(30);
  const [includeAuditDetails, setIncludeAuditDetails] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [detailLines, setDetailLines] = useState(10);
  const [aiTemplate, setAiTemplate] = useState<'curto' | 'executivo' | 'detalhado'>('curto');
  const [selectedGtId, setSelectedGtId] = useState<number | null>(null);
  const [reportMode, setReportMode] = useState<'resumo' | 'completo'>('resumo');
  const [exportFeedback, setExportFeedback] = useState('');
  const [activeTab, setActiveTab] = useState<'geral' | 'producao'>('geral');

  const { data: redatorSuggestions = [] } = useUsuariosLookup(redatorQuery);
  const { gtOptions } = useAvailableGts();

  const dateFrom = useMemo(() => {
    const date = new Date();
    date.setDate(date.getDate() - periodDays);
    return date.toISOString();
  }, [periodDays]);

  const { data: auditLogs = [], isLoading: auditLoading } = useAuditLogs({
    usuarioId: selectedRedator?.id,
    acao: actionFilter || undefined,
    dateFrom,
    pageSize: 200,
  });

  const { data: respostas = [], isLoading: respostasLoading } = useRespostas({ includeAll: true });
  const perguntasQuery = useQuery({
    queryKey: ['perguntas', 'report'],
    queryFn: async () =>
      fetchAllPaginated<Pergunta>(client.get, '/perguntas', {
        query: { page_size: 500 },
      }),
  });
  const revisoesQuery = useQuery({
    queryKey: ['revisoes', 'report'],
    queryFn: async () =>
      fetchAllPaginated<Revisao>(client.get, '/revisoes', {
        query: { page_size: 200 },
      }),
  });
  const analyticsDashboardQuery = useQuery({
    queryKey: ['analytics-admin-dashboard'],
    queryFn: async () => {
      const response = await client.get<AnalyticsAdminDashboardData>('/analytics/admin');
      return response.data;
    },
  });

  const [message, setMessage] = useState('');
  const [feedback, setFeedback] = useState('');

  const revisoesFiltradas = useMemo(() => {
    const revisoes = (revisoesQuery.data ?? []).filter((rev) => rev.status !== 'rascunho');
    if (!selectedRedator) return revisoes;
    const respostasIds = new Set(respostas.filter((r) => r.autor === selectedRedator.id).map((r) => r.id));
    return revisoes.filter(
      (rev) =>
        rev.revisor === selectedRedator.id ||
        (rev.alvo_tipo === 'resposta' && respostasIds.has(rev.alvo_id))
    );
  }, [revisoesQuery.data, selectedRedator, respostas]);

  const redatorRespostas = useMemo(() => {
    if (!selectedRedator) return [];
    return respostas.filter((r) => r.autor === selectedRedator.id);
  }, [selectedRedator, respostas]);

  const summary = useMemo(() => {
    const online = onlineUsers?.length ?? 0;
    const logins = sessionHistory?.length ?? 0;
    const respostasTotal = respostas.length;
    const pareceresTotal = revisoesFiltradas.length;
    return { online, logins, respostas: respostasTotal, pareceres: pareceresTotal };
  }, [onlineUsers, sessionHistory, respostas.length, revisoesFiltradas.length]);

  const auditSummary = useMemo(() => {
    const byAction = new Map<string, number>();
    const byEntity = new Map<string, number>();
    auditLogs.forEach((log) => {
      byAction.set(log.acao, (byAction.get(log.acao) ?? 0) + 1);
      byEntity.set(log.entidade, (byEntity.get(log.entidade) ?? 0) + 1);
    });
    const topActions = Array.from(byAction.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    const topEntities = Array.from(byEntity.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    const details = auditLogs
      .slice(0, detailLines)
      .map((log) => `${log.acao} - ${log.entidade} #${log.entidade_id}`);
    return { total: auditLogs.length, topActions, topEntities, details };
  }, [auditLogs, detailLines]);

  const gtSummary = useMemo(() => {
    const perguntas = perguntasQuery.data ?? [];
    const revisoes = revisoesFiltradas;
    const gtId = selectedGtId;
    const perguntasDoGt = gtId
      ? perguntas.filter((pergunta) => !pergunta.gts?.length || pergunta.gts.includes(gtId))
      : perguntas;
    const respostasDoGt = gtId ? respostas.filter((resp) => resp.gt === gtId) : respostas;
    const respostasComConteudo = respostasDoGt.filter((resp) => resp.conteudo_html?.trim().length);
    const totalPerguntas = perguntasDoGt.length;
    const totalRespostas = respostasComConteudo.length;
    const revisoesRespostas = revisoes.filter((rev) => rev.alvo_tipo === 'resposta');
    const revisoesDoGt = gtId
      ? revisoesRespostas.filter((rev) => rev.alvo_preview?.gt === gtId)
      : revisoesRespostas;
    const respostasComParecer = new Set(revisoesDoGt.map((rev) => rev.alvo_id));
    const pareceresEmitidos = respostasComParecer.size;
    const pareceresPendentes = Math.max(totalRespostas - pareceresEmitidos, 0);
    const faltamResponder = Math.max(totalPerguntas - totalRespostas, 0);
    const taxaConclusao = totalPerguntas > 0 ? Math.round((totalRespostas / totalPerguntas) * 100) : 0;

    return {
      totalPerguntas,
      totalRespostas,
      faltamResponder,
      taxaConclusao,
      pareceresEmitidos,
      pareceresPendentes,
      revisoesEmitidas: revisoesDoGt.length,
    };
  }, [perguntasQuery.data, revisoesFiltradas, respostas, selectedGtId]);

  const gtDetails = useMemo(() => {
    const perguntas = perguntasQuery.data ?? [];
    const revisoes = revisoesFiltradas.filter((rev) => rev.alvo_tipo === 'resposta');
    return gtOptions.map((gt) => {
      const perguntasDoGt = perguntas.filter((pergunta) => !pergunta.gts?.length || pergunta.gts.includes(gt.id));
      const respostasDoGt = respostas.filter((resp) => resp.gt === gt.id);
      const respostasComConteudo = respostasDoGt.filter((resp) => resp.conteudo_html?.trim().length);
      const revisoesDoGt = revisoes.filter((rev) => rev.alvo_preview?.gt === gt.id);
      const respostasComParecer = new Set(revisoesDoGt.map((rev) => rev.alvo_id));
      const totalPerguntas = perguntasDoGt.length;
      const totalRespostas = respostasComConteudo.length;
      const pareceresEmitidos = respostasComParecer.size;
      const pareceresPendentes = Math.max(totalRespostas - pareceresEmitidos, 0);
      const faltamResponder = Math.max(totalPerguntas - totalRespostas, 0);
      const taxaConclusao = totalPerguntas > 0 ? Math.round((totalRespostas / totalPerguntas) * 100) : 0;
      return {
        id: gt.id,
        nome: gt.displayName,
        totalPerguntas,
        totalRespostas,
        faltamResponder,
        taxaConclusao,
        pareceresEmitidos,
        pareceresPendentes,
        revisoesEmitidas: revisoesDoGt.length,
      };
    });
  }, [gtOptions, perguntasQuery.data, respostas, revisoesFiltradas]);

  const analyticsTopEscolas = useMemo(
    () => (analyticsDashboardQuery.data?.engajamento_por_escola ?? []).slice(0, 5),
    [analyticsDashboardQuery.data?.engajamento_por_escola],
  );

  const analyticsTopComponentes = useMemo(
    () => (analyticsDashboardQuery.data?.producao_por_componente ?? []).slice(0, 5),
    [analyticsDashboardQuery.data?.producao_por_componente],
  );

  const analyticsTopAutores = useMemo(
    () => (analyticsDashboardQuery.data?.top_autores ?? []).slice(0, 5),
    [analyticsDashboardQuery.data?.top_autores],
  );

  const analyticsTopEscolasLabel = useMemo(
    () =>
      analyticsTopEscolas.length > 0
        ? analyticsTopEscolas.map((item) => `${item.escola}:${item.total}`).join(', ')
        : 'sem dados',
    [analyticsTopEscolas],
  );

  const analyticsTopComponentesLabel = useMemo(
    () =>
      analyticsTopComponentes.length > 0
        ? analyticsTopComponentes.map((item) => `${item.componente_curricular}:${item.total}`).join(', ')
        : 'sem dados',
    [analyticsTopComponentes],
  );

  const analyticsTopStatusLabel = useMemo(() => {
    const status = (analyticsDashboardQuery.data?.producao_por_status ?? []).slice(0, 4);
    if (status.length === 0) return 'sem dados';
    return status.map((item) => `${item.status}:${item.total}`).join(', ');
  }, [analyticsDashboardQuery.data?.producao_por_status]);

  const analyticsTopAutoresLabel = useMemo(
    () =>
      analyticsTopAutores.length > 0
        ? analyticsTopAutores.map((item) => `${item.nome}:${item.total}`).join(', ')
        : 'sem dados',
    [analyticsTopAutores],
  );

  const analyticsSummary = useMemo(() => {
    const data = analyticsDashboardQuery.data;
    return {
      totalPlanos: data?.totais?.total_planos ?? 0,
      planos30Dias: data?.totais?.planos_ultimos_30_dias ?? 0,
      autoresAtivos: data?.totais?.autores_ativos ?? 0,
      mediaAvaliacaoRubrica: data?.media_avaliacao_rubrica ?? 0,
      mediaProgressoCursos: data?.media_progresso_cursos ?? 0,
      totalAvaliacoes: data?.total_avaliacoes ?? 0,
      cursosConcluidos: data?.cursos_concluidos ?? 0,
      cursosEmAndamento: data?.cursos_em_andamento ?? 0,
      planosPublicados: data?.planos_publicados ?? 0,
      certificados_emitidos: data?.certificados_emitidos ?? 0,
    };
  }, [analyticsDashboardQuery.data]);

  if (!user) {
    return <FullPageLoader message="Carregando relatorios..." />;
  }

  if (user.role !== 'admin_cliente' && user.role !== 'super_admin') {
    return (
      <div className="reports__empty">
        <h2>Acesso restrito</h2>
        <p>Somente admins podem gerar relatorios rapidos.</p>
      </div>
    );
  }

  const stripHtml = (value: string) => {
    if (!value.trim()) return '';
    const doc = new DOMParser().parseFromString(value, 'text/html');
    return (doc.body.textContent ?? '').replace(/\s+/g, ' ').trim();
  };

  const ensureHtml = (value: string) => {
    const text = value.trim();
    if (!text) return '';
    const hasHtmlTag = /<\/?[a-z][\s\S]*>/i.test(text);
    if (hasHtmlTag) {
      return value;
    }
    const paragraphs = text
      .split(/\n{2,}/)
      .map((block) => `<p>${block.replace(/\n/g, '<br />')}</p>`)
      .join('');
    return paragraphs || `<p>${text}</p>`;
  };

  const handleGenerate = () => {
    const today = new Date().toLocaleDateString('pt-BR');
    const redatorLabel = selectedRedator ? `${selectedRedator.nome} (${selectedRedator.email})` : 'Todos os redatores';
    const periodoLabel = `${periodDays} dias`;
    const actionLabel = actionFilter ? actionFilter : 'todas';
    const detalhesLabel = auditSummary.details.length > 0 ? auditSummary.details.join(' | ') : 'sem dados';
    const gtLabel = selectedGtId ? gtOptions.find((gt) => gt.id === selectedGtId)?.displayName || 'GT selecionado' : 'Todos os GTs';
    const text =
      `Resumo rapido - ${today}\n` +
      `Periodo: ${periodoLabel}\n` +
      `Filtro redator: ${redatorLabel}\n` +
      `Filtro GT: ${gtLabel}\n` +
      `Filtro acao: ${actionLabel}\n` +
      `Online agora: ${summary.online}\n` +
      `Logins (${periodoLabel}): ${summary.logins}\n` +
      `Respostas registradas: ${summary.respostas}\n` +
      `Pareceres emitidos: ${summary.pareceres}\n` +
      `Planos produzidos (total): ${analyticsSummary.totalPlanos}\n` +
      `Planos produzidos (30 dias): ${analyticsSummary.planos30Dias}\n` +
      `Autores ativos: ${analyticsSummary.autoresAtivos}\n` +
      `Planos publicados: ${analyticsSummary.planosPublicados}\n` +
      `Certificados emitidos: ${analyticsSummary.certificados_emitidos}\n` +
      `Media de avaliacao (rubrica): ${analyticsSummary.mediaAvaliacaoRubrica}\n` +
      `Media de progresso em cursos: ${analyticsSummary.mediaProgressoCursos}%\n` +
      `Perguntas (GT): ${gtSummary.totalPerguntas}\n` +
      `Respostas com conteudo (GT): ${gtSummary.totalRespostas}\n` +
      `Taxa de conclusao (GT): ${gtSummary.taxaConclusao}%\n` +
      `Pendentes responder (GT): ${gtSummary.faltamResponder}\n` +
      `Pareceres emitidos (GT): ${gtSummary.pareceresEmitidos}\n` +
      `Pareceres pendentes (GT): ${gtSummary.pareceresPendentes}\n` +
      `Top escolas: ${analyticsTopEscolasLabel}\n` +
      `Top componentes: ${analyticsTopComponentesLabel}\n` +
      `Distribuicao por status: ${analyticsTopStatusLabel}\n` +
      `Auditoria (${periodoLabel}): ${auditSummary.total} acao(oes)\n` +
      (includeAuditDetails
        ? `Top acoes: ${auditSummary.topActions.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}\n` +
        `Top entidades: ${auditSummary.topEntities.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}\n` +
        `Detalhes (max ${detailLines}): ${detalhesLabel}\n`
        : '');
    setMessage(ensureHtml(text));
    setFeedback('Mensagem gerada.');
  };

  const handleAiReport = async () => {
    const today = new Date().toLocaleDateString('pt-BR');
    const redatorLabel = selectedRedator ? `${selectedRedator.nome} (${selectedRedator.email})` : 'Todos os redatores';
    const periodoLabel = `${periodDays} dias`;
    const actionLabel = actionFilter ? actionFilter : 'todas';
    const detalhesLabel = auditSummary.details.length > 0 ? auditSummary.details.join(' | ') : 'sem dados';
    const gtLabel = selectedGtId ? gtOptions.find((gt) => gt.id === selectedGtId)?.displayName || 'GT selecionado' : 'Todos os GTs';
    const context = [
      `Data: ${today}`,
      `Periodo: ${periodoLabel}`,
      `Filtro redator: ${redatorLabel}`,
      `Filtro GT: ${gtLabel}`,
      `Filtro acao: ${actionLabel}`,
      `Online agora: ${summary.online}`,
      `Logins (${periodoLabel}): ${summary.logins}`,
      `Respostas registradas: ${summary.respostas}`,
      `Pareceres emitidos: ${summary.pareceres}`,
      `Planos produzidos (total): ${analyticsSummary.totalPlanos}`,
      `Planos produzidos (30 dias): ${analyticsSummary.planos30Dias}`,
      `Autores ativos: ${analyticsSummary.autoresAtivos}`,
      `Planos publicados: ${analyticsSummary.planosPublicados}`,
      `Certificados emitidos: ${analyticsSummary.certificados_emitidos}`,
      `Media de avaliacao (rubrica): ${analyticsSummary.mediaAvaliacaoRubrica}`,
      `Media de progresso em cursos: ${analyticsSummary.mediaProgressoCursos}%`,
      `Perguntas (GT): ${gtSummary.totalPerguntas}`,
      `Respostas com conteudo (GT): ${gtSummary.totalRespostas}`,
      `Taxa de conclusao (GT): ${gtSummary.taxaConclusao}%`,
      `Pendentes responder (GT): ${gtSummary.faltamResponder}`,
      `Pareceres emitidos (GT): ${gtSummary.pareceresEmitidos}`,
      `Pareceres pendentes (GT): ${gtSummary.pareceresPendentes}`,
      `Top escolas: ${analyticsTopEscolasLabel}`,
      `Top componentes: ${analyticsTopComponentesLabel}`,
      `Distribuicao por status: ${analyticsTopStatusLabel}`,
      `Top autores: ${analyticsTopAutoresLabel}`,
      `Auditoria (${periodoLabel}): ${auditSummary.total}`,
      `Top acoes: ${auditSummary.topActions.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}`,
      `Top entidades: ${auditSummary.topEntities.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}`,
      `Detalhes: ${detalhesLabel}`,
    ].join('\n');
    setFeedback('');
    try {
      const response = await aiAssist.mutateAsync({
        mode: 'draft',
        text: `Crie um resumo ${aiTemplate} para WhatsApp sobre a utilizacao da plataforma. Limite de 600 caracteres.`,
        context,
      });
      const output = (response.output || '').slice(0, 600);
      setMessage(ensureHtml(output));
      setFeedback('Mensagem gerada com IA.');
    } catch (err) {
      setFeedback('Nao foi possivel gerar o relatorio com IA.');
    }
  };

  const handleAiRewrite = async () => {
    if (!stripHtml(message)) return;
    setFeedback('');
    try {
      const response = await aiAssist.mutateAsync({
        mode: 'grammar',
        text: stripHtml(message),
      });
      setMessage(ensureHtml((response.output || stripHtml(message)).slice(0, 600)));
      setFeedback('Mensagem revisada pela IA.');
    } catch (err) {
      setFeedback('Nao foi possivel revisar a mensagem.');
    }
  };

  const handleCopy = async () => {
    const plainText = stripHtml(message);
    if (!plainText) return;
    try {
      await navigator.clipboard.writeText(plainText);
      setFeedback('Mensagem copiada para o WhatsApp.');
    } catch (err) {
      setFeedback('Nao foi possivel copiar automaticamente.');
    }
  };

  const escapeHtml = (value: string) =>
    value.replace(/[&<>\"']/g, (char) => {
      switch (char) {
        case '&':
          return '&amp;';
        case '<':
          return '&lt;';
        case '>':
          return '&gt;';
        case '"':
          return '&quot;';
        case "'":
          return '&#39;';
        default:
          return char;
      }
    });

  const buildReportHtml = (mode: 'resumo' | 'completo') => {
    const today = new Date();
    const todayLabel = today.toLocaleDateString('pt-BR');
    const redatorLabel = selectedRedator ? `${selectedRedator.nome} (${selectedRedator.email})` : 'Todos os redatores';
    const periodoLabel = `${periodDays} dias`;
    const actionLabel = actionFilter ? actionFilter : 'todas';
    const gtLabel = selectedGtId ? gtOptions.find((gt) => gt.id === selectedGtId)?.displayName || 'GT selecionado' : 'Todos os GTs';

    const overviewCards = [
      { label: 'Online agora', value: summary.online },
      { label: `Logins (${periodoLabel})`, value: summary.logins },
      { label: 'Respostas registradas', value: summary.respostas },
      { label: 'Pareceres emitidos', value: summary.pareceres },
      { label: 'Planos (total)', value: analyticsSummary.totalPlanos },
      { label: 'Planos (30 dias)', value: analyticsSummary.planos30Dias },
      { label: 'Autores ativos', value: analyticsSummary.autoresAtivos },
      { label: 'Planos publicados', value: analyticsSummary.planosPublicados },
    ];

    const auditDetails = mode === 'completo'
      ? auditLogs.map((log) => `${new Date(log.timestamp).toLocaleString('pt-BR')} - ${log.acao} - ${log.entidade} #${log.entidade_id}`)
      : auditSummary.details;

    const auditNotice =
      mode === 'completo' && auditLogs.length >= 200
        ? '<p class=\"report-meta\">Nota: relatorio limitado aos 200 registros mais recentes de auditoria.</p>'
        : '';

    const gtRows = (mode === 'completo' ? gtDetails : selectedGtId ? gtDetails.filter((gt) => gt.id === selectedGtId) : [])
      .map(
        (gt) =>
          `<tr>
            <td>${escapeHtml(gt.nome)}</td>
            <td>${gt.totalPerguntas}</td>
            <td>${gt.totalRespostas}</td>
            <td>${gt.faltamResponder}</td>
            <td>${gt.taxaConclusao}%</td>
            <td>${gt.pareceresEmitidos}</td>
            <td>${gt.pareceresPendentes}</td>
          </tr>`
      )
      .join('');

    return `
      <div class="report">
        <p class="report-meta">Gerado em ${todayLabel} - Modo: ${mode === 'resumo' ? 'Resumo executivo' : 'Relatorio completo'}</p>
        <section class="report-section">
          <h2>Filtros aplicados</h2>
          <ul class="report-list">
            <li><strong>Periodo:</strong> ${escapeHtml(periodoLabel)}</li>
            <li><strong>Redator:</strong> ${escapeHtml(redatorLabel)}</li>
            <li><strong>GT:</strong> ${escapeHtml(gtLabel)}</li>
            <li><strong>Acao:</strong> ${escapeHtml(actionLabel)}</li>
          </ul>
        </section>

        <section class="report-section">
          <h2>Visao geral</h2>
          <div class="report-grid">
            ${overviewCards
        .map(
          (card) =>
            `<div class="report-card"><span>${escapeHtml(card.label)}</span><strong>${card.value}</strong></div>`
        )
        .join('')}
          </div>
        </section>

        <section class="report-section">
          <h2>Painel de producao e formacao</h2>
          <div class="report-grid">
            <div class="report-card">
              <span>Media avaliacao rubrica</span>
              <strong>${analyticsSummary.mediaAvaliacaoRubrica}</strong>
            </div>
            <div class="report-card">
              <span>Media progresso cursos</span>
              <strong>${analyticsSummary.mediaProgressoCursos}%</strong>
            </div>
            <div class="report-card">
              <span>Total avaliacoes</span>
              <strong>${analyticsSummary.totalAvaliacoes}</strong>
            </div>
            <div class="report-card">
              <span>Certificados emitidos</span>
              <strong>${analyticsSummary.certificados_emitidos}</strong>
            </div>
            <div class="report-card">
              <span>Cursos concluidos</span>
              <strong>${analyticsSummary.cursosConcluidos}</strong>
            </div>
            <div class="report-card">
              <span>Cursos em andamento</span>
              <strong>${analyticsSummary.cursosEmAndamento}</strong>
            </div>
          </div>
          <ul class="report-list">
            <li><strong>Top escolas:</strong> ${escapeHtml(analyticsTopEscolasLabel)}</li>
            <li><strong>Top componentes:</strong> ${escapeHtml(analyticsTopComponentesLabel)}</li>
            <li><strong>Status de producao:</strong> ${escapeHtml(analyticsTopStatusLabel)}</li>
            <li><strong>Top autores:</strong> ${escapeHtml(analyticsTopAutoresLabel)}</li>
          </ul>
        </section>

        <section class="report-section">
          <h2>Indicadores por GT</h2>
          <div class="report-meta">Resumo geral: ${gtSummary.totalPerguntas} perguntas - ${gtSummary.totalRespostas} respostas - ${gtSummary.taxaConclusao}% conclusao</div>
          ${gtRows
        ? `<table class="report-table">
                  <thead>
                    <tr>
                      <th>GT</th>
                      <th>Perguntas</th>
                      <th>Respostas</th>
                      <th>Pendentes</th>
                      <th>Conclusao</th>
                      <th>Pareceres</th>
                      <th>Pareceres pendentes</th>
                    </tr>
                  </thead>
                  <tbody>${gtRows}</tbody>
                </table>`
        : '<p>Sem dados para este filtro.</p>'
      }
        </section>

        <section class="report-section">
          <h2>Auditoria</h2>
          <div class="report-meta">Total: ${auditSummary.total} acoes</div>
          <div class="report-grid">
            <div class="report-card">
              <span>Top acoes</span>
              <strong>${auditSummary.topActions.map(([name, count]) => `${escapeHtml(name)} (${count})`).join(' - ') || 'Sem dados'}</strong>
            </div>
            <div class="report-card">
              <span>Top entidades</span>
              <strong>${auditSummary.topEntities.map(([name, count]) => `${escapeHtml(name)} (${count})`).join(' - ') || 'Sem dados'}</strong>
            </div>
          </div>
          ${auditNotice}
          ${auditDetails.length
        ? `<ul class="report-list">${auditDetails.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
        : '<p>Sem detalhes de auditoria para o periodo selecionado.</p>'
      }
        </section>
      </div>
    `;
  };

  const handleExportPdf = async () => {
    if (
      onlineLoading ||
      sessionsLoading ||
      respostasLoading ||
      perguntasQuery.isLoading ||
      revisoesQuery.isLoading ||
      auditLoading ||
      analyticsDashboardQuery.isLoading
    ) {
      setExportFeedback('Aguarde o carregamento completo dos dados antes de exportar.');
      return;
    }
    setExportFeedback('');
    const now = new Date();
    const titulo = `Relatorio ${reportMode === 'resumo' ? 'Resumo' : 'Completo'} - ${now.toLocaleDateString('pt-BR')}`;
    try {
      await criarExportacao.mutateAsync({
        alvoTipo: 'relatorio',
        alvoId: 'relatorio',
        formato: 'pdf',
        payloadJson: {
          titulo,
          conteudo_html: buildReportHtml(reportMode),
          modo: reportMode,
        },
      });
      setExportFeedback('Exportacao solicitada. Confira o historico em Exportacoes.');
    } catch (err) {
      setExportFeedback('Nao foi possivel solicitar a exportacao.');
    }
  };
  const handleExportPdfProducao = async () => {
    if (!selectedRedator) return;
    setExportFeedback('Gerando PDF do redator...');
    const now = new Date().toLocaleDateString('pt-BR');
    const htmlContent = `
      <div style="font-family: sans-serif; padding: 20px;">
        <h1 style="color: #1e3a8a;">Relatório de Produção - ${selectedRedator.nome}</h1>
        <p><strong>Email:</strong> ${selectedRedator.email}</p>
        <p><strong>Gerado em:</strong> ${now}</p>
        <p><strong>Total de respostas:</strong> ${redatorRespostas.length}</p>
        <p><strong>Total de pareceres emitidos:</strong> ${revisoesFiltradas.length}</p>
        <hr style="margin: 20px 0; border: 0; border-top: 1px solid #ccc;">
        <h2>Respostas</h2>
        ${redatorRespostas.map((r: any) => `
          <div style="margin-bottom: 30px; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px;">
            <div style="background: #f3f4f6; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
              <strong>GT:</strong> ${r.gt_nome || 'N/A'} <br>
              <strong>Pergunta:</strong> ${r.pergunta_texto ? r.pergunta_texto : 'Pergunta #' + r.pergunta}
            </div>
            <div>${r.conteudo_html}</div>
          </div>
        `).join('')}
        <h2>Pareceres</h2>
        ${revisoesFiltradas.map((rev: any) => `
          <div style="margin-bottom: 30px; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px;">
            <div style="background: #f3f4f6; padding: 10px; border-radius: 4px; margin-bottom: 10px;">
              <strong>Parecer #${rev.id} - Status: ${rev.status} - Emitido em: ${rev.created_at ? new Date(rev.created_at).toLocaleDateString('pt-BR') : 'Sem data'}</strong>
            </div>
            <div>${rev.parecer_html}</div>
          </div>
        `).join('')}
      </div>
    `;

    try {
      await criarExportacao.mutateAsync({
        alvoTipo: 'relatorio',
        alvoId: String(selectedRedator.id),
        formato: 'pdf',
        payloadJson: {
          titulo: `Produção - ${selectedRedator.nome}`,
          conteudo_html: htmlContent,
          modo: 'completo',
        },
      });
      setExportFeedback('PDF de produção solicitado. Confira na aba de exportações.');
    } catch (err) {
      setExportFeedback('Nao foi possivel solicitar a exportacao.');
    }
  };

  const handleCopyProducao = async () => {
    if (!selectedRedator) return;
    const faltam = gtSummary.faltamResponder;
    const revisoesDetalhadas = revisoesFiltradas
      .map(
        (rev) =>
          `- Parecer #${rev.id} (${rev.status}) - Emitido em: ${rev.created_at ? new Date(
            rev.created_at
          ).toLocaleDateString('pt-BR') : 'Sem data'}`
      )
      .join('\n');
    const text =
      `*Produção de ${selectedRedator.nome}*\n\n` +
      `Estatísticas gerais:\n` +
      `- Respostas preenchidas: ${redatorRespostas.length}\n` +
      `- Faltam responder no GT selecionado: ${faltam}\n` +
      `- Total de pareceres emitidos: ${revisoesFiltradas.length}\n\n` +
      `Pareceres:\n${revisoesDetalhadas}\n`;
    try {
      await navigator.clipboard.writeText(text);
      setFeedback('Mensagem de produção copiada para o WhatsApp.');
    } catch (err) {
      setFeedback('Nao foi possivel copiar automaticamente.');
    }
  };

  return (
    <div className="reports">
      <header className="reports__header">
        <div>
          <h1>Relatorios rapidos</h1>
          <p>Gere mensagens curtas para WhatsApp com dados de utilizacao da plataforma.</p>
        </div>
      </header>

      <div className="reports__tabs">
        <button
          className={`reports__tab ${activeTab === 'geral' ? 'active' : ''}`}
          onClick={() => setActiveTab('geral')}
        >
          Visão Geral
        </button>
        <button
          className={`reports__tab ${activeTab === 'producao' ? 'active' : ''} `}
          onClick={() => setActiveTab('producao')}
        >
          Produção do Redator/Revisor
        </button>
      </div>

      {activeTab === 'geral' && (
        <>
          <PageInstructions
            title="Como usar"
            description="Atualize os dados, gere a mensagem e copie para enviar no WhatsApp."
            items={[
              {
                title: 'Atualize os dados',
                description: 'Os dados refletem o momento atual e os ultimos 30 dias.',
              },
              {
                title: 'Gere o texto',
                description: 'Clique em gerar mensagem para compilar o resumo automatico.',
              },
              {
                title: 'Compartilhe',
                description: 'Copie e envie rapidamente para o grupo ou equipe.',
              },
            ]}
          />

          <section className="reports__cards">
            <StatCard
              title="Online agora"
              value={onlineLoading ? '...' : summary.online}
              icon="group"
              color="blue"
            />
            <StatCard
              title="Logins (30 dias)"
              value={sessionsLoading ? '...' : summary.logins}
              icon="login"
              color="purple"
            />
            <StatCard
              title="Respostas"
              value={respostasLoading ? '...' : summary.respostas}
              icon="assignment"
              color="green"
            />
            <StatCard
              title="Pareceres"
              value={revisoesQuery.isLoading ? '...' : summary.pareceres}
              icon="rate_review"
              color="orange"
            />
          </section>

          <section className="reports__section">
            <div className="reports__section-header">
              <div>
                <h2>Painel de producao e formacao</h2>
                <p>Indicadores consolidados de producao pedagogica, avaliacao e formacao continuada.</p>
              </div>
              <span className="reports__pill">
                {analyticsDashboardQuery.isLoading ? '...' : `${analyticsSummary.totalPlanos} planos`}
              </span>
            </div>
            <div className="reports__cards reports__cards--gt">
              <StatCard
                title="Planos produzidos"
                value={analyticsDashboardQuery.isLoading ? '...' : analyticsSummary.totalPlanos}
                color="blue"
              />
              <StatCard
                title="Planos (30 dias)"
                value={analyticsDashboardQuery.isLoading ? '...' : analyticsSummary.planos30Dias}
                color="green"
              />
              <StatCard
                title="Autores ativos"
                value={analyticsDashboardQuery.isLoading ? '...' : analyticsSummary.autoresAtivos}
                color="purple"
              />
              <StatCard
                title="Media rubrica"
                value={analyticsDashboardQuery.isLoading ? '...' : analyticsSummary.mediaAvaliacaoRubrica}
                color="orange"
              />
              <StatCard
                title="Progresso medio cursos"
                value={analyticsDashboardQuery.isLoading ? '...' : `${analyticsSummary.mediaProgressoCursos}% `}
                color="green"
              />
              <StatCard
                title="Certificados emitidos"
                value={analyticsDashboardQuery.isLoading ? '...' : analyticsSummary.certificados_emitidos}
                color="red"
              />
            </div>
            <div className="reports__audit-grid">
              <div className="reports__audit-card">
                <h3>Top escolas</h3>
                {analyticsTopEscolas.length > 0 ? (
                  <ul>
                    {analyticsTopEscolas.map((item) => (
                      <li key={item.escola}>
                        <span>{item.escola}</span>
                        <strong>{item.total}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sem dados.</p>
                )}
              </div>
              <div className="reports__audit-card">
                <h3>Top componentes</h3>
                {analyticsTopComponentes.length > 0 ? (
                  <ul>
                    {analyticsTopComponentes.map((item) => (
                      <li key={item.componente_curricular}>
                        <span>{item.componente_curricular}</span>
                        <strong>{item.total}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sem dados.</p>
                )}
              </div>
              <div className="reports__audit-card">
                <h3>Top autores</h3>
                {analyticsTopAutores.length > 0 ? (
                  <ul>
                    {analyticsTopAutores.map((item) => (
                      <li key={`${item.autor_id} -${item.email} `}>
                        <span>{item.nome}</span>
                        <strong>{item.total}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sem dados.</p>
                )}
              </div>
            </div>
          </section>

          <section className="reports__section">
            <div className="reports__section-header">
              <div>
                <h2>Indicadores por GT</h2>
                <p>Filtre um grupo para acompanhar respostas, pendencias e pareceres.</p>
              </div>
              <span className="reports__pill">
                {selectedGtId
                  ? gtOptions.find((gt) => gt.id === selectedGtId)?.displayName || 'GT selecionado'
                  : 'Todos os GTs'}
              </span>
            </div>
            <div className="reports__cards reports__cards--gt">
              <StatCard
                title="Perguntas do GT"
                value={perguntasQuery.isLoading ? '...' : gtSummary.totalPerguntas}
                color="blue"
              />
              <StatCard
                title="Respostas com conteudo"
                value={respostasLoading ? '...' : gtSummary.totalRespostas}
                color="green"
              />
              <StatCard
                title="Taxa de conclusao"
                value={respostasLoading || perguntasQuery.isLoading ? '...' : `${gtSummary.taxaConclusao}% `}
                color="purple"
              />
              <StatCard
                title="Faltam responder"
                value={respostasLoading || perguntasQuery.isLoading ? '...' : gtSummary.faltamResponder}
                color="red"
              />
              <StatCard
                title="Pareceres emitidos"
                value={revisoesQuery.isLoading ? '...' : gtSummary.pareceresEmitidos}
                color="orange"
              />
              <StatCard
                title="Pareceres pendentes"
                value={revisoesQuery.isLoading || respostasLoading ? '...' : gtSummary.pareceresPendentes}
                color="red"
              />
            </div>
          </section>

          <section className="reports__filters">
            <div className="reports__filter">
              <label>
                <span>Periodo</span>
                <select value={periodDays} onChange={(event) => setPeriodDays(Number(event.target.value))}>
                  <option value={7}>Ultimos 7 dias</option>
                  <option value={30}>Ultimos 30 dias</option>
                  <option value={90}>Ultimos 90 dias</option>
                </select>
              </label>
            </div>
            <div className="reports__filter">
              <label>
                <span>Filtro de acao</span>
                <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)}>
                  <option value="">Todas</option>
                  <option value="created">created</option>
                  <option value="updated">updated</option>
                  <option value="deleted">deleted</option>
                </select>
              </label>
            </div>
            <div className="reports__filter">
              <label>
                <span>Filtro de GT (indicadores)</span>
                <select
                  value={selectedGtId ?? ''}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedGtId(value ? Number(value) : null);
                  }}
                >
                  <option value="">Todos</option>
                  {gtOptions.map((gt) => (
                    <option key={gt.id} value={gt.id}>
                      {gt.displayName}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="reports__filter">
              <label>
                <span>Template IA</span>
                <select value={aiTemplate} onChange={(event) => setAiTemplate(event.target.value as any)}>
                  <option value="curto">Curto</option>
                  <option value="executivo">Executivo</option>
                  <option value="detalhado">Detalhado</option>
                </select>
              </label>
            </div>
            <div className="reports__filter">
              <label>
                <span>Filtrar por redator</span>
                <input
                  type="search"
                  value={redatorQuery}
                  onChange={(event) => setRedatorQuery(event.target.value)}
                  placeholder="Digite o nome ou email"
                />
              </label>
              {redatorSuggestions.length > 0 && (
                <div className="reports__suggestions">
                  {redatorSuggestions.map((suggestion) => (
                    <button
                      key={suggestion.id}
                      type="button"
                      onClick={() => {
                        setSelectedRedator(suggestion);
                        setRedatorQuery(suggestion.nome);
                      }}
                    >
                      {suggestion.nome} - {suggestion.email}
                    </button>
                  ))}
                </div>
              )}
              {selectedRedator && (
                <div className="reports__selected">
                  <span>Redator selecionado:</span>
                  <strong>{selectedRedator.nome}</strong>
                  <button type="button" onClick={() => setSelectedRedator(null)}>
                    Limpar
                  </button>
                </div>
              )}
            </div>
            <label className="reports__toggle">
              <input
                type="checkbox"
                checked={includeAuditDetails}
                onChange={(event) => setIncludeAuditDetails(event.target.checked)}
              />
              <span>Incluir detalhes de auditoria na mensagem</span>
            </label>
            <div className="reports__filter">
              <label>
                <span>Linhas de detalhe</span>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={detailLines}
                  onChange={(event) => setDetailLines(Number(event.target.value))}
                />
              </label>
            </div>
            <div className="reports__filter reports__filter--link">
              <span>Auditoria completa</span>
              <Link to="/auditoria">Abrir auditoria detalhada</Link>
            </div>
          </section>

          <section className="reports__section">
            <div className="reports__section-header">
              <div>
                <h2>Auditoria</h2>
                <p>Resumo de acoes recentes com filtro por redator.</p>
              </div>
              <span className="reports__pill">{auditLoading ? '...' : `${auditSummary.total} acoes`}</span>
            </div>
            <div className="reports__audit-grid">
              <div className="reports__audit-card">
                <h3>Top acoes</h3>
                {auditSummary.topActions.length > 0 ? (
                  <ul>
                    {auditSummary.topActions.map(([name, count]) => (
                      <li key={name}>
                        <span>{name}</span>
                        <strong>{count}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sem dados.</p>
                )}
              </div>
              <div className="reports__audit-card">
                <h3>Top entidades</h3>
                {auditSummary.topEntities.length > 0 ? (
                  <ul>
                    {auditSummary.topEntities.map(([name, count]) => (
                      <li key={name}>
                        <span>{name}</span>
                        <strong>{count}</strong>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Sem dados.</p>
                )}
              </div>
            </div>
          </section>

          <section className="reports__composer">
            <div className="reports__actions">
              <button type="button" onClick={handleGenerate}>
                Gerar mensagem
              </button>
              <button type="button" className="secondary" onClick={handleAiReport} disabled={aiAssist.isPending}>
                {aiAssist.isPending ? 'IA em andamento...' : 'IA: gerar resumo'}
              </button>
              <button type="button" className="secondary" onClick={handleAiRewrite} disabled={!message || aiAssist.isPending}>
                {aiAssist.isPending ? 'IA em andamento...' : 'IA: revisar mensagem'}
              </button>
              <button type="button" className="secondary" onClick={handleCopy} disabled={!message}>
                Copiar para WhatsApp
              </button>
              <div className="reports__export">
                <select value={reportMode} onChange={(event) => setReportMode(event.target.value as 'resumo' | 'completo')}>
                  <option value="resumo">PDF resumido</option>
                  <option value="completo">PDF completo</option>
                </select>
                <button type="button" className="secondary" onClick={handleExportPdf} disabled={criarExportacao.isPending}>
                  {criarExportacao.isPending ? 'Exportando...' : 'Exportar PDF'}
                </button>
              </div>
              {feedback && <span className="reports__feedback">{feedback}</span>}
              {exportFeedback && <span className="reports__feedback">{exportFeedback}</span>}
            </div>
            <RichTextEditor
              value={message}
              onChange={setMessage}
              placeholder="Clique em gerar mensagem para ver o texto aqui."
              config={{
                toolbar: ['bold', 'italic', 'link', 'bulletedList', 'numberedList', 'undo', 'redo'],
              }}
            />
          </section>
        </>
      )}

      {activeTab === 'producao' && (
        <div className="reports__producao">
          <aside className="reports__producao-sidebar">
            <div className="reports__search-box">
              <label>Buscar Redator</label>
              <input
                type="search"
                placeholder="Busque por nome ou email..."
                value={redatorQuery}
                onChange={(e) => setRedatorQuery(e.target.value)}
              />
              {redatorSuggestions.length > 0 && (
                <div className="reports__suggestions-box">
                  {redatorSuggestions.map((suggestion) => (
                    <button
                      key={suggestion.id}
                      type="button"
                      className={selectedRedator?.id === suggestion.id ? 'active' : ''}
                      onClick={() => {
                        setSelectedRedator(suggestion);
                        setRedatorQuery('');
                      }}
                    >
                      <span>{suggestion.nome}</span>
                      <small>{suggestion.email}</small>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedRedator && (
              <div className="reports__producao-filter-gt">
                <label>Filtrar por GT (Indicador de Pêndencias)</label>
                <select
                  value={selectedGtId ?? ''}
                  onChange={(event) => {
                    const value = event.target.value;
                    setSelectedGtId(value ? Number(value) : null);
                  }}
                >
                  <option value="">Todos os GTs</option>
                  {gtOptions.map((gt) => (
                    <option key={gt.id} value={gt.id}>
                      {gt.displayName}
                    </option>
                  ))}
                </select>
                <button type="button" onClick={() => setSelectedRedator(null)} className="reports__clear-redator">
                  Remover seleção
                </button>
              </div>
            )}
          </aside>

          <main className="reports__producao-content">
            {selectedRedator ? (
              <div className="reports__producao-detail">
                <header className="reports__producao-header">
                  <div>
                    <h2>{selectedRedator.nome}</h2>
                    <p>
                      <strong>{redatorRespostas.length}</strong> respostas preenchidas | {' '}
                      <strong>{revisoesFiltradas.length}</strong> pareceres emitidos | {' '}
                      <strong>{gtSummary.faltamResponder}</strong> perguntas faltando responder no GT selecionado
                    </p>
                  </div>
                  <div className="reports__producao-actions">
                    <button className="secondary" onClick={handleCopyProducao}>Resumo WhatsApp</button>
                    <button className="secondary" onClick={handleExportPdfProducao} disabled={criarExportacao.isPending}>
                      {criarExportacao.isPending ? 'Exportando...' : 'Exportar PDF'}
                    </button>
                  </div>
                </header>
                {(feedback || exportFeedback) && (
                  <div className="reports__feedback-box">
                    {feedback} {exportFeedback}
                  </div>
                )}

                <div className="reports__producao-feed">
                  <h3>Respostas de Missões</h3>
                  {redatorRespostas.length === 0 ? (
                    <p className="reports__empty-feed">Nenhuma resposta submetida.</p>
                  ) : (
                    redatorRespostas.map(r => (
                      <div key={`resp - ${r.id} `} className="reports__feed-item">
                        <div className="reports__feed-meta">
                          <span className="reports__feed-badge">{r.gt_nome || 'GT'}</span>
                          <span className="reports__feed-meta-text">Missão #{r.pergunta}</span>
                        </div>
                        <div className="reports__feed-question" dangerouslySetInnerHTML={{ __html: r.pergunta_texto || '' }} />
                        <div className="reports__feed-body" dangerouslySetInnerHTML={{ __html: r.conteudo_html || '' }} />
                      </div>
                    ))
                  )}

                  <h3 className="reports__pareceres-title">Pareceres Emitidos</h3>
                  {revisoesFiltradas.length === 0 ? (
                    <p className="reports__empty-feed">Nenhum parecer emitido.</p>
                  ) : (
                    revisoesFiltradas.map(rev => (
                      <div key={`rev - ${rev.id} `} className="reports__feed-item">
                        <div className="reports__feed-meta">
                          <span className="reports__feed-badge reports__feed-badge--parecer">Parecer #{rev.id}</span>
                          <span className="reports__feed-meta-text">Status: {rev.status}</span>
                          <span className="reports__feed-meta-text">
                            Emitido em: {rev.created_at ? new Date(rev.created_at).toLocaleDateString('pt-BR') : 'Sem data'}
                          </span>
                          <Link
                            to={`/redator/revisoes/${rev.alvo_tipo}/${rev.alvo_id}`}
                            target="_blank"
                            className="reports__feed-open-link"
                            style={{ marginLeft: 'auto', fontSize: '12px', color: 'var(--color-primary, #0056b3)', textDecoration: 'underline' }}
                          >
                            Abrir Parecer
                          </Link>
                        </div>
                        <div className="reports__feed-body" dangerouslySetInnerHTML={{ __html: rev.parecer_html || '' }} />
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="reports__empty-state">
                <p>Selecione um redator na lista ao lado para acompanhar a sua formacao.</p>
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
