import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ApiError, useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import Icon from '@/components/common/Icon';
import { StatCard } from '@/components/dashboard/StatCard';
import { SimpleBarChart, SimpleDonutChart, SimpleHorizontalBarChart } from '@/components/dashboard/SimpleCharts';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useOnlineUsers, useSessionHistory } from '@/hooks/useAuditLogs';
import { usePainelRespostas } from '@/hooks/usePainelRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import { useRespostas } from '@/hooks/useRespostas';
import { useScoreSummary } from '@/hooks/useScore';
import { useTarefas } from '@/hooks/useTarefas';
import { useAuth } from '@/context/AuthContext';
import { fetchAllPaginated } from '@/utils/pagination';
import type { PaginatedResponse, Pergunta, Resposta, Revisao } from '@/api/types';

import './DashboardPage.css';

const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Admin',
  admin_cliente: 'Admin',
  articulador: 'Redator',
  membro_gt: 'Membro GT',
  leitor: 'Leitor',
};

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

const stripHtml = (html?: string | null) => {
  if (!html) return '';
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
};

const htmlToPlainText = (html?: string | null) => {
  if (!html) return '';
  const normalized = html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n');
  return normalized
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s+/g, '\n')
    .trim();
};

const buildPreview = (html?: string | null, limit = 160) => {
  const text = stripHtml(html);
  if (!text) return 'Sem conteúdo.';
  if (text.length <= limit) return text;
  return `${text.slice(0, limit)}…`;
};

export function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return <FullPageLoader message="Carregando dashboard..." />;
  }

  if (user.role === 'admin_cliente' || user.role === 'super_admin') {
    return <AdminDashboard />;
  }

  if (user.role === 'articulador') {
    return <ArticuladorDashboard />;
  }

  if (user.role === 'membro_gt') {
    return <Navigate to="/inicio" replace />;
  }

  return (
    <div className="dashboard-container">
      <PageHeader
        title="Dashboard"
        description="Acompanhe as trilhas e atualizações mais recentes por aqui."
      />
      <Card>
        <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <h2 style={{ marginBottom: '0.5rem', fontSize: '1.5rem' }}>Sem dados para este perfil</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>Se precisar de acesso a relatórios específicos, fale com a equipe responsável.</p>
        </div>
      </Card>
    </div>
  );
}

function AdminDashboard() {
  const client = useApiClient();
  const { data: tarefas, isLoading, isError, error, refetch } = useTarefas();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts({ scope: 'all' });
  const {
    data: painelRespostas,
    isLoading: painelLoading,
    isError: painelError,
    error: painelErrorObj,
    refetch: refetchPainel,
  } = usePainelRespostas();
  const { data: onlineUsers, isLoading: onlineLoading, isFetching: onlineFetching } = useOnlineUsers();
  const { data: sessionHistory, isLoading: sessionsLoading, isFetching: sessionsFetching } = useSessionHistory();

  const respostasCountQuery = useQuery({
    queryKey: ['respostas', 'count'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
        query: { page_size: 1 },
      });
      return response.data.count ?? 0;
    },
  });

  const revisoesCountQuery = useQuery({
    queryKey: ['revisoes', 'count'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Revisao>>('/revisoes', {
        query: { page_size: 1 },
      });
      return response.data.count ?? 0;
    },
  });

  const perguntasSummaryQuery = useQuery({
    queryKey: ['perguntas', 'summary', tarefas?.map((tarefa) => tarefa.id)],
    enabled: Boolean(tarefas?.length),
    refetchOnWindowFocus: false,
    staleTime: 10 * 60 * 1000,
    queryFn: async () => {
      if (!tarefas?.length) {
        return [];
      }
      const tarefaIdSet = new Set(tarefas.map((tarefa) => tarefa.id));
      const todasPerguntas = await fetchAllPaginated<Pergunta>(client.get, '/perguntas', {
        query: { page_size: 500 },
      });
      const agrupadas = new Map<number, Pergunta[]>();
      todasPerguntas.forEach((pergunta) => {
        if (!tarefaIdSet.has(pergunta.tarefa)) {
          return;
        }
        const lista = agrupadas.get(pergunta.tarefa) ?? [];
        lista.push(pergunta);
        agrupadas.set(pergunta.tarefa, lista);
      });
      return Array.from(agrupadas.entries()).map(([tarefaId, perguntas]) => ({
        tarefaId,
        perguntas,
      }));
    },
  });

  const onlineList = useMemo(() => {
    return (onlineUsers ?? [])
      .slice()
      .sort((a, b) => new Date(b.last_seen_at).getTime() - new Date(a.last_seen_at).getTime())
      .slice(0, 6);
  }, [onlineUsers]);

  const perguntasStats = useMemo(() => {
    const totalPerguntas = (perguntasSummaryQuery.data ?? []).reduce(
      (acc, item) => acc + item.perguntas.length,
      0,
    );
    const gtCount = gtOptions.length || 0;
    const expectedRespostas = (perguntasSummaryQuery.data ?? []).reduce((acc, item) => {
      item.perguntas.forEach((pergunta) => {
        if (pergunta.gts && pergunta.gts.length > 0) {
          acc += pergunta.gts.length;
        } else {
          acc += gtCount;
        }
      });
      return acc;
    }, 0);
    return {
      totalPerguntas,
      expectedRespostas,
    };
  }, [perguntasSummaryQuery.data, gtOptions.length]);

  const usageByRole = useMemo(() => {
    const totals = new Map<string, { duration: number; sessions: number; users: Map<number, { name: string; email: string; duration: number; sessions: number }> }>();
    let totalDuration = 0;

    (sessionHistory ?? []).forEach((session) => {
      const role = session.usuario_role ?? 'leitor';
      const duration = session.session_duration_seconds ?? 0;
      totalDuration += duration;
      if (!totals.has(role)) {
        totals.set(role, { duration: 0, sessions: 0, users: new Map() });
      }
      const bucket = totals.get(role);
      if (!bucket) return;
      bucket.duration += duration;
      bucket.sessions += 1;
      const userId = session.usuario_id ?? session.id;
      const currentUser = bucket.users.get(userId) ?? {
        name: session.usuario_nome || 'Usuário sem nome',
        email: session.usuario_email || 'E-mail não informado',
        duration: 0,
        sessions: 0,
      };
      currentUser.duration += duration;
      currentUser.sessions += 1;
      bucket.users.set(userId, currentUser);
    });

    const buildTopUsers = (role: string) => {
      const bucket = totals.get(role);
      if (!bucket) return [] as Array<{ name: string; email: string; duration: number; sessions: number }>;
      return Array.from(bucket.users.values())
        .sort((a, b) => b.duration - a.duration)
        .slice(0, 5);
    };

    return {
      totals,
      totalDuration,
      topArticuladores: buildTopUsers('articulador'),
      topMembros: buildTopUsers('membro_gt'),
    };
  }, [sessionHistory]);

  const totalRespostas = respostasCountQuery.data ?? 0;
  const totalRevisoes = revisoesCountQuery.data ?? 0;
  const expectedRespostas = perguntasStats.expectedRespostas;
  const respostaRate = expectedRespostas > 0 ? Math.min(totalRespostas / expectedRespostas, 1) : 0;
  const respostaRateLabel = expectedRespostas > 0 ? `${Math.round(respostaRate * 100)}%` : '—';

  const roleUsage = (role: string) => {
    const totalDuration = usageByRole.totalDuration || 0;
    const bucket = usageByRole.totals.get(role);
    if (!bucket || totalDuration === 0) {
      return { percent: 0, duration: 0, sessions: 0 };
    }
    return {
      percent: Math.round((bucket.duration / totalDuration) * 100),
      duration: bucket.duration,
      sessions: bucket.sessions,
    };
  };

  const articuladorUsage = roleUsage('articulador');
  const membroUsage = roleUsage('membro_gt');

  if (isLoading || gtsLoading) {
    return <FullPageLoader message="Carregando dashboard administrativo..." />;
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Erro ao carregar trilhas pedagógicas';
    return (
      <div className="dashboard-error">
        <h2>Não foi possível carregar o dashboard</h2>
        <p>{message}</p>
        <button type="button" onClick={() => refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  const chartData = [
    { label: 'Redatores', value: articuladorUsage.sessions, color: '#f97316' },
    { label: 'Membros GT', value: membroUsage.sessions, color: '#10b981' },
  ];

  return (
    <div className="dashboard-container">
      <PageHeader
        title="Dashboard administrativo"
        description="Visão geral e indicadores de performance."
        actions={
          <>
            <Link to="/auditoria">
              <Button variant="outline" leftIcon={<Icon name="audit" />}>Auditoria</Button>
            </Link>
            <Link to="/revisoes">
              <Button variant="primary" leftIcon={<Icon name="review" />}>Revisões</Button>
            </Link>
          </>
        }
      />

      <div className="dashboard-grid">
        {/* KPI Cards */}
        <div className="dashboard-grid__kpi">
          <StatCard
            title="Online Agora"
            value={onlineUsers?.length ?? 0}
            icon="group"
            color="blue"
            loading={onlineFetching}
          />
        </div>
        <div className="dashboard-grid__kpi">
          <StatCard
            title="Respostas"
            value={totalRespostas}
            icon="assignment"
            color="green"
            trend={{ value: 12, label: 'vs. mês anterior', direction: 'up' }}
          />
        </div>
        <div className="dashboard-grid__kpi">
          <StatCard
            title="Pareceres"
            value={totalRevisoes}
            icon="rate_review"
            color="purple"
          />
        </div>
        <div className="dashboard-grid__kpi">
          <StatCard
            title="Conclusão"
            value={respostaRateLabel}
            icon="pie_chart"
            color="orange"
          />
        </div>

        {/* Main Charts */}
        <div className="dashboard-grid__main-chart">
          <div className="dashboard-card-header">
            <h2>Engajamento por Perfil</h2>
            <p>Sessões ativas nos últimos 30 dias</p>
          </div>
          <SimpleBarChart data={chartData} height={240} />
        </div>

        <div className="dashboard-grid__side-chart">
          <div className="dashboard-card-header">
            <h2>Taxa de Resposta</h2>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem 0' }}>
            <SimpleDonutChart
              percent={respostaRate * 100}
              label={`${Math.round(respostaRate * 100)}%`}
              subLabel="Concluído"
              color="#3b82f6"
              size={180}
            />
          </div>
          <div style={{ textAlign: 'center', marginTop: '1rem', color: '#64748b', fontSize: '0.9rem' }}>
            {totalRespostas} de {expectedRespostas} respostas esperadas
          </div>
        </div>

        {/* Details Tables */}
        <div className="dashboard-grid__details">
          <div className="dashboard-card-header">
            <h2>Presença em Tempo Real</h2>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
              {onlineUsers?.length ?? 0} usuários online
            </span>
          </div>
          {onlineList.length > 0 ? (
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Perfil</th>
                  <th>Última atividade</th>
                </tr>
              </thead>
              <tbody>
                {onlineList.map((session) => (
                  <tr key={session.id}>
                    <td>
                      <div className="dashboard-table__user">
                        <strong>{session.usuario_nome || 'Usuário sem nome'}</strong>
                        <span>{session.usuario_email}</span>
                      </div>
                    </td>
                    <td>{ROLE_LABELS[session.usuario_role ?? 'leitor'] ?? session.usuario_role}</td>
                    <td>{formatDateTime(session.last_seen_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="dashboard-empty">Nenhum usuário online no momento.</div>
          )}
        </div>

        <div className="dashboard-grid__details">
          <div className="dashboard-card-header">
            <h2>Respostas Recentes</h2>
            <button className="dashboard-card-action" onClick={() => refetchPainel()}>
              Atualizar
            </button>
          </div>
          {(painelRespostas ?? []).length > 0 ? (
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th>GT</th>
                  <th>Autor</th>
                  <th>Atualização</th>
                </tr>
              </thead>
              <tbody>
                {painelRespostas?.slice(0, 5).map((resposta) => (
                  <tr key={`painel-${resposta.id}`}>
                    <td>{resposta.gt_nome ?? `GT #${resposta.gt}`}</td>
                    <td>
                      <div className="dashboard-table__user">
                        <strong>{resposta.autor_nome || 'Autor não informado'}</strong>
                      </div>
                    </td>
                    <td>{formatDateTime(resposta.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="dashboard-empty">Nenhuma resposta recente.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ArticuladorDashboard() {
  const client = useApiClient();
  const { data: tarefas, isLoading, isError, error, refetch } = useTarefas();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts({ scope: 'member' });
  const { data: painelRespostas, isLoading: painelLoading, refetch: refetchPainel } = usePainelRespostas();
  const { data: scoreSummary, isLoading: scoreLoading, refetch: refetchScore } = useScoreSummary();

  const [gtSearch, setGtSearch] = useState('');
  const [selectedGtId, setSelectedGtId] = useState<number | null>(null);
  const [modalRespostaId, setModalRespostaId] = useState<number | null>(null);
  const { data: respostasDoGt, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId });
  const trilhaSearch = '';

  useEffect(() => {
    if (!selectedGtId && gtOptions.length > 0) {
      setSelectedGtId(gtOptions[0].id);
    }
  }, [gtOptions, selectedGtId]);

  const perguntasSummaryQuery = useQuery({
    queryKey: ['perguntas', 'summary', tarefas?.map((tarefa) => tarefa.id)],
    enabled: Boolean(tarefas?.length),
    refetchOnWindowFocus: false,
    staleTime: 10 * 60 * 1000,
    queryFn: async () => {
      if (!tarefas?.length) {
        return [];
      }
      const tarefaIdSet = new Set(tarefas.map((tarefa) => tarefa.id));
      const todasPerguntas = await fetchAllPaginated<Pergunta>(client.get, '/perguntas', {
        query: { page_size: 500 },
      });
      const agrupadas = new Map<number, Pergunta[]>();
      todasPerguntas.forEach((pergunta) => {
        if (!tarefaIdSet.has(pergunta.tarefa)) {
          return;
        }
        const lista = agrupadas.get(pergunta.tarefa) ?? [];
        lista.push(pergunta);
        agrupadas.set(pergunta.tarefa, lista);
      });
      return Array.from(agrupadas.entries()).map(([tarefaId, perguntas]) => ({
        tarefaId,
        perguntas,
      }));
    },
  });

  const perguntasByTarefa = useMemo(() => {
    const map = new Map<number, number>();
    (perguntasSummaryQuery.data ?? []).forEach((item) => {
      const count = (item.perguntas ?? []).filter((pergunta) => {
        if (!selectedGtId) {
          return true;
        }
        return !pergunta.gts || pergunta.gts.length === 0 || pergunta.gts.includes(selectedGtId);
      }).length;
      map.set(item.tarefaId, count);
    });
    return map;
  }, [perguntasSummaryQuery.data, selectedGtId]);

  const gtIdSet = useMemo(() => new Set(gtOptions.map((gt) => gt.id)), [gtOptions]);

  const painelRespostasFiltradas = useMemo(() => {
    if (!painelRespostas || gtIdSet.size === 0) {
      return [];
    }
    return painelRespostas.filter((resp) => gtIdSet.has(resp.gt));
  }, [painelRespostas, gtIdSet]);

  const respostaAtiva = useMemo(() => {
    if (!modalRespostaId) return null;
    return painelRespostasFiltradas.find((resp) => resp.id === modalRespostaId) ?? null;
  }, [modalRespostaId, painelRespostasFiltradas]);

  const respostasPorGtMap = useMemo(() => {
    const map = new Map<number, number>();
    painelRespostasFiltradas.forEach((resp) => {
      map.set(resp.gt, (map.get(resp.gt) ?? 0) + 1);
    });
    return map;
  }, [painelRespostasFiltradas]);

  const filteredGts = useMemo(() => {
    const term = gtSearch.trim().toLowerCase();
    if (!term) return gtOptions;
    return gtOptions.filter((gt) => gt.displayName.toLowerCase().includes(term));
  }, [gtOptions, gtSearch]);

  useEffect(() => {
    if (!selectedGtId && filteredGts.length > 0) {
      setSelectedGtId(filteredGts[0].id);
    }
  }, [filteredGts, selectedGtId]);

  const selectedGt = gtOptions.find((gt) => gt.id === selectedGtId) ?? null;

  const tarefasFiltradas = useMemo(() => {
    const term = trilhaSearch.trim().toLowerCase();
    const ordered = (tarefas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
    const base = term
      ? ordered.filter((tarefa) => {
        const nome = tarefa.nome?.toLowerCase() ?? '';
        const etapa = tarefa.etapa?.toLowerCase() ?? '';
        return nome.includes(term) || etapa.includes(term) || String(tarefa.ordem).includes(term);
      })
      : ordered;
    if (!selectedGtId) {
      return base;
    }
    return base.filter((tarefa) => (perguntasByTarefa.get(tarefa.id) ?? 0) > 0);
  }, [tarefas, trilhaSearch, perguntasByTarefa, selectedGtId]);

  const tarefasRespondidas = useMemo(() => {
    if (!respostasDoGt) {
      return new Set<number>();
    }
    const ids = new Set<number>();
    respostasDoGt.forEach((resp) => {
      if (resp.tarefa_id) {
        ids.add(resp.tarefa_id);
      }
    });
    return ids;
  }, [respostasDoGt]);

  const tarefasOrdenadas = useMemo(() => {
    if (!selectedGtId) {
      return tarefasFiltradas;
    }
    return tarefasFiltradas
      .slice()
      .sort((a, b) => {
        const aRespondida = tarefasRespondidas.has(a.id);
        const bRespondida = tarefasRespondidas.has(b.id);
        if (aRespondida === bRespondida) {
          return a.ordem - b.ordem;
        }
        return aRespondida ? -1 : 1;
      });
  }, [tarefasFiltradas, tarefasRespondidas, selectedGtId]);

  const pontosAtuais = scoreSummary?.current_points ?? 0;
  const metaMensal = scoreSummary?.monthly_limit ?? 0;
  const progressoBase = metaMensal > 0 ? pontosAtuais / metaMensal : scoreSummary?.progress ?? 0;
  const progresso = Math.min(Math.max(progressoBase, 0), 1);
  const progressoPercentual = Math.round(progresso * 1000) / 10;
  const pontosRestantes = Math.max(metaMensal - pontosAtuais, 0);

  const dataHojeBase = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
  const dataHoje = dataHojeBase.charAt(0).toUpperCase() + dataHojeBase.slice(1);

  const respostasOrdenadas = useMemo(() => {
    return painelRespostasFiltradas
      .slice()
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [painelRespostasFiltradas]);

  const respostasRecentes = respostasOrdenadas.slice(0, 2);
  const trilhasPrioritarias = tarefasOrdenadas.slice(0, 2);

  if (isLoading || gtsLoading || respostasLoading) {
    return <FullPageLoader message="Carregando painel do redator..." />;
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Erro ao carregar trilhas pedagógicas';
    return (
      <div className="dashboard-error">
        <h2>Não foi possível carregar o painel</h2>
        <p>{message}</p>
        <button type="button" onClick={() => refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="redator-dashboard">
      <header className="redator-dashboard__header">
        <div>
          <h1>Painel do Redator</h1>
          <p>{dataHoje}</p>
        </div>
        <div className="redator-dashboard__actions">
          <Link to="/redator/revisoes" className="redator-action primary">
            Abrir revisões
          </Link>
          <button
            type="button"
            className="redator-action ghost"
            onClick={() => refetchPainel()}
            disabled={painelLoading}
          >
            Atualizar respostas
          </button>
          <button
            type="button"
            className="redator-action outline"
            onClick={() => refetchScore()}
            disabled={scoreLoading}
          >
            Atualizar score
          </button>
        </div>
      </header>

      <div className="redator-dashboard__grid">
        <div className="redator-dashboard__main">
          <section className="redator-card redator-card--score">
            <div className="redator-card__top">
              <div>
                <span className="redator-chip">Desempenho Atual</span>
                <h2>Score do Mês</h2>
              </div>
              <div className="redator-score">
                <div>
                  <span className="redator-score__value">{pontosAtuais}</span>
                  <span className="redator-score__meta">/ {metaMensal} pts</span>
                </div>
                <p>{metaMensal ? `${progressoPercentual}% da meta mensal` : 'Meta mensal não definida'}</p>
              </div>
            </div>
            <div className="redator-progress">
              <div className="redator-progress__labels">
                <span>Progresso</span>
                <span>{pontosRestantes} pts restantes</span>
              </div>
              <div className="redator-progress__bar">
                <span style={{ width: `${progresso * 100}%` }} />
              </div>
            </div>
            <div className="redator-card__kpis">
              <div>
                <p>GTs ativos</p>
                <strong>{gtOptions.length}</strong>
              </div>
              <div>
                <p>Respostas recentes</p>
                <strong>{painelRespostasFiltradas.length}</strong>
              </div>
              <div>
                <p>Trilhas disponíveis</p>
                <strong>{tarefasOrdenadas.length}</strong>
              </div>
            </div>
          </section>

          <section className="redator-section">
            <div className="redator-section__header">
              <h3>Respostas Recentes</h3>
              <Link to="/redator/revisoes" className="redator-link">
                Ver histórico completo
              </Link>
            </div>
            <div className="redator-list">
              {respostasRecentes.map((resp) => (
                <article key={resp.id} className="redator-list__card">
                  <div className="redator-list__icon" aria-hidden="true">
                    <span>*</span>
                  </div>
                  <div className="redator-list__content">
                    <div className="redator-list__header">
                      <div>
                        <h4>{resp.gt_nome ?? `GT #${resp.gt}`}</h4>
                        <p>{resp.autor_nome ?? (resp.autor ? `Usuário #${resp.autor}` : 'Autor não informado')}</p>
                      </div>
                      <span>{formatDateTime(resp.updated_at)}</span>
                    </div>
                    <div className="redator-list__preview">
                      <p>{buildPreview(resp.conteudo_html)}</p>
                    </div>
                    <div className="redator-list__actions">
                      <button type="button" onClick={() => setModalRespostaId(resp.id)}>
                        Abrir Revisão
                      </button>
                    </div>
                  </div>
                </article>
              ))}
              {!respostasRecentes.length && (
                <div className="redator-empty">Nenhuma resposta registrada ainda.</div>
              )}
            </div>
          </section>
        </div>

        <div className="redator-dashboard__side">
          <section className="redator-panel">
            <div className="redator-panel__header">
              <h3>GTs Disponíveis</h3>
              <p>Grupos de trabalho ativos para seleção</p>
              <div className="redator-search">
                <input
                  type="search"
                  placeholder="Buscar por componente ou nível..."
                  value={gtSearch}
                  onChange={(event) => setGtSearch(event.target.value)}
                />
              </div>
            </div>
            <div className="redator-panel__list">
              {filteredGts.map((gt) => {
                const responses = respostasPorGtMap.get(gt.id) ?? 0;
                return (
                  <button
                    key={gt.id}
                    type="button"
                    className={`redator-gt ${selectedGtId === gt.id ? 'is-active' : ''}`}
                    onClick={() => setSelectedGtId(gt.id)}
                  >
                    <div>
                      <h4>{gt.displayName}</h4>
                      <p>{responses} respostas aguardando</p>
                    </div>
                    <span>{'>'}</span>
                  </button>
                );
              })}
              {!filteredGts.length && <div className="redator-empty">Nenhum GT encontrado.</div>}
            </div>
            {selectedGt && (
              <div className="redator-panel__footer">
                <span>Selecionado: {selectedGt.displayName}</span>
              </div>
            )}
          </section>

          <section className="redator-panel redator-panel--compact">
            <div className="redator-panel__header row">
              <h3>Trilhas Prioritárias</h3>
              <span className="redator-tag">Novo</span>
            </div>
            <div className="redator-panel__stack">
              {trilhasPrioritarias.map((tarefa) => {
                const respondida = tarefasRespondidas.has(tarefa.id);
                return (
                  <div key={tarefa.id} className="redator-track">
                    <div className="redator-track__meta">
                      <span>Trilha #{tarefa.ordem}</span>
                      <span className={`redator-status ${respondida ? 'ok' : 'pending'}`}>
                        {respondida ? 'Completa' : 'Em análise'}
                      </span>
                    </div>
                    <h4>{tarefa.nome}</h4>
                    <p>{perguntasByTarefa.get(tarefa.id) ?? 0} missões pendentes</p>
                    <Link to={`/tarefas/${tarefa.id}?gt=${selectedGtId ?? ''}`} className="redator-track__action">
                      Abrir Trilha
                    </Link>
                  </div>
                );
              })}
              {!trilhasPrioritarias.length && (
                <div className="redator-empty">Nenhuma trilha disponível.</div>
              )}
            </div>
          </section>
        </div>
      </div>

      {respostaAtiva && (
        <div
          className="dashboard__modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="dashboard-modal-title"
          onClick={() => setModalRespostaId(null)}
        >
          <div className="dashboard__modal" onClick={(event) => event.stopPropagation()}>
            <header className="dashboard__modal-header">
              <div>
                <p className="dashboard__modal-eyebrow">{respostaAtiva.gt_nome ?? `GT #${respostaAtiva.gt}`}</p>
                <h3 id="dashboard-modal-title">
                  Missão {respostaAtiva.pergunta_ordem ?? respostaAtiva.pergunta} · Trilha{' '}
                  {respostaAtiva.tarefa_id ?? '—'}
                </h3>
                <div className="dashboard__modal-meta">
                  <span>Atualizado {formatDateTime(respostaAtiva.updated_at)}</span>
                  <span>{respostaAtiva.autor_nome ?? (respostaAtiva.autor ? `Usuário #${respostaAtiva.autor}` : 'Autor não informado')}</span>
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={() => setModalRespostaId(null)}
                aria-label="Fechar modal de resposta"
              >
                Fechar
              </Button>
            </header>
            <div className="dashboard__modal-body">
              {respostaAtiva.pergunta_texto && (
                <div className="dashboard__modal-block">
                  <div className="dashboard__modal-label">Missão</div>
                  <div
                    className="dashboard__modal-content"
                    dangerouslySetInnerHTML={{ __html: respostaAtiva.pergunta_texto }}
                  />
                </div>
              )}
              <div className="dashboard__modal-block">
                <div className="dashboard__modal-label">Resposta</div>
                <p className="dashboard__modal-content dashboard__modal-content--plain">
                  {htmlToPlainText(respostaAtiva.conteudo_html) || 'Sem conteúdo.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MembroDashboard() {
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts();
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ includeAll: true });
  const { data: revisoes, isLoading: revisoesLoading, refetch } = useRevisoes({ alvoTipo: 'resposta', pageSize: 200 });

  const respostaIds = useMemo(() => new Set((respostas ?? []).map((resp) => resp.id)), [respostas]);

  const pareceres = useMemo(() => {
    return (revisoes ?? [])
      .filter((rev) => rev.alvo_tipo === 'resposta' && respostaIds.has(rev.alvo_id))
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 10);
  }, [revisoes, respostaIds]);

  if (gtsLoading || respostasLoading || revisoesLoading) {
    return <FullPageLoader message="Carregando seu dashboard..." />;
  }

  return (
    <div className="dashboard-container">
      <PageHeader
        title="Meu dashboard"
        description="Veja os pareceres mais recentes enviados pelo redator."
        actions={
          <Button variant="secondary" onClick={() => refetch()}>
            Atualizar pareceres
          </Button>
        }
      />

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <Card>
          <div className="dashboard__card-header">
            <span>GTs vinculados</span>
            <strong>{gtOptions.length}</strong>
          </div>
          <p>Use os pareceres abaixo para ajustar as missões e trilhas.</p>
        </Card>
        <Card>
          <div className="dashboard__card-header">
            <span>Pareceres recentes</span>
            <strong>{pareceres.length}</strong>
          </div>
          <p>Revisões mais recentes do redator associadas ao seu GT.</p>
        </Card>
      </section>

      <Card>
        <div className="dashboard__panel-header">
          <div>
            <h2>Pareceres do redator</h2>
            <p>Acesse o feedback e abra a trilha correspondente.</p>
          </div>
          <span className="dashboard__pill">{pareceres.length} itens</span>
        </div>
        {pareceres.length > 0 ? (
          <div className="dashboard__list">
            {pareceres.map((rev) => {
              const preview = rev.alvo_preview as Revisao['alvo_preview'];
              const previewText = stripHtml(rev.parecer_html) || 'Sem parecer detalhado.';
              const tarefaId = preview && 'tarefa' in preview ? preview.tarefa : null;
              const gtId = preview && 'gt' in preview ? preview.gt : null;
              const linkTo = tarefaId && gtId ? `/tarefas/${tarefaId}?gt=${gtId}` : null;
              return (
                <div key={rev.id} className="dashboard__list-item">
                  <div>
                    <strong>Revisao #{rev.id}</strong>
                    <span>{previewText.slice(0, 160) || 'Sem parecer detalhado.'}</span>
                  </div>
                  <div className="dashboard__list-meta">
                    <span>Status: {rev.status}</span>
                    <span>Atualizado {formatDateTime(rev.updated_at)}</span>
                    {linkTo && (
                      <Link to={linkTo}>
                        <Button size="sm" variant="primary">Abrir trilha</Button>
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="dashboard__empty-inline">
            Nenhum parecer disponível ainda. Assim que o redator publicar, ele aparece aqui.
          </div>
        )}
      </Card>
    </div>
  );
}
