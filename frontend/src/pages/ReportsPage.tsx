import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAuditLogs, useOnlineUsers, useSessionHistory } from '@/hooks/useAuditLogs';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useRespostas } from '@/hooks/useRespostas';
import { useUsuariosLookup } from '@/hooks/useUsuariosLookup';
import { useAuth } from '@/context/AuthContext';
import { fetchAllPaginated } from '@/utils/pagination';
import type { Pergunta, Revisao } from '@/api/types';

import './ReportsPage.css';

export function ReportsPage() {
  const { user } = useAuth();
  const client = useApiClient();
  const { data: onlineUsers, isLoading: onlineLoading } = useOnlineUsers();
  const { data: sessionHistory, isLoading: sessionsLoading } = useSessionHistory();
  const aiAssist = useAiAssist();

  const [redatorQuery, setRedatorQuery] = useState('');
  const [selectedRedator, setSelectedRedator] = useState<{ id: number; nome: string; email: string } | null>(null);
  const [periodDays, setPeriodDays] = useState(30);
  const [includeAuditDetails, setIncludeAuditDetails] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [detailLines, setDetailLines] = useState(10);
  const [aiTemplate, setAiTemplate] = useState<'curto' | 'executivo' | 'detalhado'>('curto');
  const [selectedGtId, setSelectedGtId] = useState<number | null>(null);

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

  const [message, setMessage] = useState('');
  const [feedback, setFeedback] = useState('');

  const revisoesFiltradas = useMemo(() => {
    const revisoes = revisoesQuery.data ?? [];
    if (!selectedRedator) return revisoes;
    return revisoes.filter((rev) => rev.revisor === selectedRedator.id);
  }, [revisoesQuery.data, selectedRedator]);

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
      .map((log) => `${log.acao} · ${log.entidade} #${log.entidade_id}`);
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
      `Perguntas (GT): ${gtSummary.totalPerguntas}\n` +
      `Respostas com conteudo (GT): ${gtSummary.totalRespostas}\n` +
      `Taxa de conclusao (GT): ${gtSummary.taxaConclusao}%\n` +
      `Pendentes responder (GT): ${gtSummary.faltamResponder}\n` +
      `Pareceres emitidos (GT): ${gtSummary.pareceresEmitidos}\n` +
      `Pareceres pendentes (GT): ${gtSummary.pareceresPendentes}\n` +
      `Auditoria (${periodoLabel}): ${auditSummary.total} acao(oes)\n` +
      (includeAuditDetails
        ? `Top acoes: ${auditSummary.topActions.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}\n` +
          `Top entidades: ${auditSummary.topEntities.map(([name, count]) => `${name}:${count}`).join(', ') || 'sem dados'}\n` +
          `Detalhes (max ${detailLines}): ${detalhesLabel}\n`
        : '');
    setMessage(text);
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
      `Perguntas (GT): ${gtSummary.totalPerguntas}`,
      `Respostas com conteudo (GT): ${gtSummary.totalRespostas}`,
      `Taxa de conclusao (GT): ${gtSummary.taxaConclusao}%`,
      `Pendentes responder (GT): ${gtSummary.faltamResponder}`,
      `Pareceres emitidos (GT): ${gtSummary.pareceresEmitidos}`,
      `Pareceres pendentes (GT): ${gtSummary.pareceresPendentes}`,
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
      setMessage(output);
      setFeedback('Mensagem gerada com IA.');
    } catch (err) {
      setFeedback('Nao foi possivel gerar o relatorio com IA.');
    }
  };

  const handleAiRewrite = async () => {
    if (!message.trim()) return;
    setFeedback('');
    try {
      const response = await aiAssist.mutateAsync({
        mode: 'grammar',
        text: message,
      });
      setMessage((response.output || message).slice(0, 600));
      setFeedback('Mensagem revisada pela IA.');
    } catch (err) {
      setFeedback('Nao foi possivel revisar a mensagem.');
    }
  };

  const handleCopy = async () => {
    if (!message) return;
    try {
      await navigator.clipboard.writeText(message);
      setFeedback('Mensagem copiada para o WhatsApp.');
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
        <div className="reports__card">
          <span>Online agora</span>
          <strong>{onlineLoading ? '...' : summary.online}</strong>
        </div>
        <div className="reports__card">
          <span>Logins (30 dias)</span>
          <strong>{sessionsLoading ? '...' : summary.logins}</strong>
        </div>
        <div className="reports__card">
          <span>Respostas registradas</span>
          <strong>{respostasLoading ? '...' : summary.respostas}</strong>
        </div>
        <div className="reports__card">
          <span>Pareceres emitidos</span>
          <strong>{revisoesQuery.isLoading ? '...' : summary.pareceres}</strong>
        </div>
      </section>

      <section className="reports__gt">
        <div className="reports__gt-header">
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
          <div className="reports__card">
            <span>Perguntas do GT</span>
            <strong>{perguntasQuery.isLoading ? '...' : gtSummary.totalPerguntas}</strong>
          </div>
          <div className="reports__card">
            <span>Respostas com conteudo</span>
            <strong>{respostasLoading ? '...' : gtSummary.totalRespostas}</strong>
          </div>
          <div className="reports__card">
            <span>Taxa de conclusao</span>
            <strong>{respostasLoading || perguntasQuery.isLoading ? '...' : `${gtSummary.taxaConclusao}%`}</strong>
          </div>
          <div className="reports__card">
            <span>Faltam responder</span>
            <strong>{respostasLoading || perguntasQuery.isLoading ? '...' : gtSummary.faltamResponder}</strong>
          </div>
          <div className="reports__card">
            <span>Pareceres emitidos</span>
            <strong>{revisoesQuery.isLoading ? '...' : gtSummary.pareceresEmitidos}</strong>
          </div>
          <div className="reports__card">
            <span>Pareceres pendentes</span>
            <strong>{revisoesQuery.isLoading || respostasLoading ? '...' : gtSummary.pareceresPendentes}</strong>
          </div>
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
                  {suggestion.nome} · {suggestion.email}
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

      <section className="reports__audit">
        <div className="reports__audit-header">
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
          {feedback && <span className="reports__feedback">{feedback}</span>}
        </div>
        <textarea
          rows={6}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Clique em gerar mensagem para ver o texto aqui."
        />
      </section>
    </div>
  );
}
