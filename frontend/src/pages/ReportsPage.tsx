import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAuditLogs, useOnlineUsers, useSessionHistory } from '@/hooks/useAuditLogs';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useUsuariosLookup } from '@/hooks/useUsuariosLookup';
import { useAuth } from '@/context/AuthContext';
import type { PaginatedResponse, Resposta, Revisao } from '@/api/types';

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

  const { data: redatorSuggestions = [] } = useUsuariosLookup(redatorQuery);

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

  const respostasCountQuery = useQuery({
    queryKey: ['respostas', 'count', 'report'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
        query: { page_size: 1 },
      });
      return response.data.count ?? 0;
    },
  });

  const revisoesCountQuery = useQuery({
    queryKey: ['revisoes', 'count', 'report'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Revisao>>('/revisoes', {
        query: { page_size: 1 },
      });
      return response.data.count ?? 0;
    },
  });

  const [message, setMessage] = useState('');
  const [feedback, setFeedback] = useState('');

  const summary = useMemo(() => {
    const online = onlineUsers?.length ?? 0;
    const logins = sessionHistory?.length ?? 0;
    const respostas = respostasCountQuery.data ?? 0;
    const pareceres = revisoesCountQuery.data ?? 0;
    return { online, logins, respostas, pareceres };
  }, [onlineUsers, sessionHistory, respostasCountQuery.data, revisoesCountQuery.data]);

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
    const text =
      `Resumo rapido - ${today}\n` +
      `Periodo: ${periodoLabel}\n` +
      `Filtro redator: ${redatorLabel}\n` +
      `Filtro acao: ${actionLabel}\n` +
      `Online agora: ${summary.online}\n` +
      `Logins (${periodoLabel}): ${summary.logins}\n` +
      `Respostas registradas: ${summary.respostas}\n` +
      `Pareceres emitidos: ${summary.pareceres}\n` +
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
    const context = [
      `Data: ${today}`,
      `Periodo: ${periodoLabel}`,
      `Filtro redator: ${redatorLabel}`,
      `Filtro acao: ${actionLabel}`,
      `Online agora: ${summary.online}`,
      `Logins (${periodoLabel}): ${summary.logins}`,
      `Respostas registradas: ${summary.respostas}`,
      `Pareceres emitidos: ${summary.pareceres}`,
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
          <strong>{respostasCountQuery.isLoading ? '...' : summary.respostas}</strong>
        </div>
        <div className="reports__card">
          <span>Pareceres emitidos</span>
          <strong>{revisoesCountQuery.isLoading ? '...' : summary.pareceres}</strong>
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
