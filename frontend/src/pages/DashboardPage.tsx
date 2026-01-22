import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ApiError, useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import Icon from '@/components/common/Icon';
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
    return <MembroDashboard />;
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

  return (
    <div className="dashboard-container">
      <PageHeader
        title="Dashboard administrativo"
        description="Visibilidade completa de acesso, engajamento e progresso das trilhas pedagógicas."
        actions={
          <>
            <Link to="/auditoria">
              <Button variant="outline" leftIcon={<Icon name="audit" />}>Ver auditoria</Button>
            </Link>
            <Link to="/revisoes">
              <Button variant="primary" leftIcon={<Icon name="review" />}>Revisões em andamento</Button>
            </Link>
          </>
        }
      />

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <Card>
          <div className="dashboard__card-header">
            <span>Acesso em tempo real</span>
            <strong>{onlineUsers?.length ?? 0} online</strong>
          </div>
          <p>Última atualização {onlineFetching ? 'agora' : 'há menos de 1 minuto'}.</p>
          <div className="dashboard__progress">
            <div
              className="dashboard__progress-bar"
              style={{ width: `${Math.min((onlineUsers?.length ?? 0) * 10, 100)}%` }}
            />
          </div>
        </Card>

        <Card>
          <div className="dashboard__card-header">
            <span>Respostas registradas</span>
            <strong>{totalRespostas}</strong>
          </div>
          <p>Quantidade total de respostas enviadas.</p>
        </Card>

        <Card>
          <div className="dashboard__card-header">
            <span>Pareceres emitidos</span>
            <strong>{totalRevisoes}</strong>
          </div>
          <p>Total de pareceres e revisões registrados.</p>
        </Card>

        <Card>
          <div className="dashboard__card-header">
            <span>Taxa de resposta</span>
            <strong>{respostaRateLabel}</strong>
          </div>
          <p>
            {totalRespostas} resposta(s) registradas de {expectedRespostas || '—'} previstas.
          </p>
          <div className="dashboard__progress">
            <div className="dashboard__progress-bar" style={{ width: `${respostaRate * 100}%` }} />
          </div>
        </Card>

        <Card>
          <div className="dashboard__card-header">
            <span>Uso por redatores</span>
            <strong>{articuladorUsage.percent}%</strong>
          </div>
          <p>
            {articuladorUsage.sessions} sessões nos últimos 30 dias.
          </p>
          <div className="dashboard__progress">
            <div className="dashboard__progress-bar" style={{ width: `${articuladorUsage.percent}%` }} />
          </div>
        </Card>

        <Card>
          <div className="dashboard__card-header">
            <span>Uso por membros GT</span>
            <strong>{membroUsage.percent}%</strong>
          </div>
          <p>
            {membroUsage.sessions} sessões nos últimos 30 dias.
          </p>
          <div className="dashboard__progress">
            <div className="dashboard__progress-bar" style={{ width: `${membroUsage.percent}%` }} />
          </div>
        </Card>
      </section>

      <section className="dashboard__charts">
        <Card>
          <header style={{ marginBottom: '1rem' }}>
            <h2>Progresso das trilhas</h2>
            <span>{respostaRateLabel} concluído</span>
          </header>
          <div className="dashboard__chart-bar">
            <div
              className="dashboard__chart-bar-fill"
              style={{ width: `${respostaRate * 100}%` }}
            />
          </div>
          <div className="dashboard__chart-meta">
            <span>{totalRespostas} respostas</span>
            <span>{Math.max(expectedRespostas - totalRespostas, 0)} pendentes</span>
          </div>
        </Card>

        <Card>
          <header style={{ marginBottom: '1rem' }}>
            <h2>Uso por perfil</h2>
            <span>Distribuição do tempo ativo</span>
          </header>
          <div className="dashboard__chart-rows">
            <div className="dashboard__chart-row">
              <div>
                <strong>Redatores</strong>
                <span>{articuladorUsage.sessions} sessões</span>
              </div>
              <div className="dashboard__chart-bar">
                <div
                  className="dashboard__chart-bar-fill dashboard__chart-bar-fill--alt"
                  style={{ width: `${articuladorUsage.percent}%` }}
                />
              </div>
              <span className="dashboard__chart-percent">{articuladorUsage.percent}%</span>
            </div>
            <div className="dashboard__chart-row">
              <div>
                <strong>Membros GT</strong>
                <span>{membroUsage.sessions} sessões</span>
              </div>
              <div className="dashboard__chart-bar">
                <div
                  className="dashboard__chart-bar-fill dashboard__chart-bar-fill--secondary"
                  style={{ width: `${membroUsage.percent}%` }}
                />
              </div>
              <span className="dashboard__chart-percent">{membroUsage.percent}%</span>
            </div>
          </div>
        </Card>
      </section>

      <section className="dashboard__split">
        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Presença agora</h2>
              <p>Quem está na plataforma neste momento.</p>
            </div>
            <span className="dashboard__pill">{onlineLoading ? 'Carregando...' : `${onlineUsers?.length ?? 0} online`}</span>
          </div>
          {onlineLoading ? (
            <p className="dashboard__helper">Carregando sessões ativas...</p>
          ) : onlineList.length > 0 ? (
            <div className="dashboard__list">
              {onlineList.map((session) => (
                <div key={session.id} className="dashboard__list-item">
                  <div>
                    <strong>{session.usuario_nome || 'Usuário sem nome'}</strong>
                    <span>{session.usuario_email || 'E-mail não informado'}</span>
                  </div>
                  <div className="dashboard__list-meta">
                    <span>{ROLE_LABELS[session.usuario_role ?? 'leitor'] ?? session.usuario_role}</span>
                    <span>Última atividade {formatDateTime(session.last_seen_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="dashboard__empty-inline">Nenhum usuário online agora.</div>
          )}
        </Card>

        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Logins recentes</h2>
              <p>Histórico de acesso dos últimos 30 dias.</p>
            </div>
            <span className="dashboard__pill">{sessionsFetching ? 'Atualizando...' : `${sessionHistory?.length ?? 0} registros`}</span>
          </div>
          {sessionsLoading ? (
            <p className="dashboard__helper">Carregando histórico...</p>
          ) : (sessionHistory ?? []).length > 0 ? (
            <div className="dashboard__table">
              <table>
                <thead>
                  <tr>
                    <th>Usuário</th>
                    <th>Perfil</th>
                    <th>Login</th>
                    <th>Duração</th>
                  </tr>
                </thead>
                <tbody>
                  {sessionHistory?.slice(0, 6).map((session) => {
                    const secs = session.session_duration_seconds ?? 0;
                    const hours = Math.floor(secs / 3600);
                    const minutes = Math.floor((secs % 3600) / 60);
                    const durationLabel = hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`;
                    return (
                      <tr key={`sess-${session.id}`}>
                        <td>
                          <strong>{session.usuario_nome || 'Usuário sem nome'}</strong>
                          <span>{session.usuario_email || 'E-mail não informado'}</span>
                        </td>
                        <td>{ROLE_LABELS[session.usuario_role ?? 'leitor'] ?? session.usuario_role}</td>
                        <td>{formatDateTime(session.first_seen_at)}</td>
                        <td>{durationLabel}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="dashboard__empty-inline">Nenhum login registrado no período.</div>
          )}
        </Card>
      </section>

      <section className="dashboard__split">
        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Uso por redator</h2>
              <p>Top 5 com mais tempo ativo.</p>
            </div>
            <span className="dashboard__pill">{usageByRole.topArticuladores.length} perfis</span>
          </div>
          {usageByRole.topArticuladores.length > 0 ? (
            <div className="dashboard__list">
              {usageByRole.topArticuladores.map((user) => (
                <div key={`${user.email}-art`} className="dashboard__list-item">
                  <div>
                    <strong>{user.name}</strong>
                    <span>{user.email}</span>
                  </div>
                  <div className="dashboard__list-meta">
                    <span>{Math.round(user.duration / 60)} min ativos</span>
                    <span>{user.sessions} sessões</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="dashboard__empty-inline">Sem dados de uso por redatores.</div>
          )}
        </Card>

        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Uso por membro GT</h2>
              <p>Top 5 com mais tempo ativo.</p>
            </div>
            <span className="dashboard__pill">{usageByRole.topMembros.length} perfis</span>
          </div>
          {usageByRole.topMembros.length > 0 ? (
            <div className="dashboard__list">
              {usageByRole.topMembros.map((user) => (
                <div key={`${user.email}-gt`} className="dashboard__list-item">
                  <div>
                    <strong>{user.name}</strong>
                    <span>{user.email}</span>
                  </div>
                  <div className="dashboard__list-meta">
                    <span>{Math.round(user.duration / 60)} min ativos</span>
                    <span>{user.sessions} sessões</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="dashboard__empty-inline">Sem dados de uso por membros GT.</div>
          )}
        </Card>
      </section>

      <Card>
        <div className="dashboard__panel-header">
          <div>
            <h2>Respostas recentes</h2>
            <p>Últimos registros enviados por GT.</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => refetchPainel()}
            disabled={painelLoading}
            isLoading={painelLoading}
          >
            Atualizar
          </Button>
        </div>
        {painelError ? (
          <div className="dashboard__panel-error">
            <p>Não foi possível carregar as respostas recentes.</p>
            <p>{painelErrorObj instanceof ApiError ? painelErrorObj.message : 'Erro desconhecido'}</p>
          </div>
        ) : (painelRespostas ?? []).length === 0 ? (
          <div className="dashboard__panel-empty">Nenhuma resposta registrada ainda.</div>
        ) : (
          <div className="dashboard__table">
            <table>
              <thead>
                <tr>
                  <th>GT</th>
                  <th>Autor</th>
                  <th>Atualização</th>
                </tr>
              </thead>
              <tbody>
                {painelRespostas?.slice(0, 8).map((resposta) => (
                  <tr key={`painel-${resposta.id}`}>
                    <td>{resposta.gt_nome ?? `GT #${resposta.gt}`}</td>
                    <td>{resposta.autor_nome ?? (resposta.autor ? `Usuário #${resposta.autor}` : 'Autor não informado')}</td>
                    <td>{formatDateTime(resposta.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
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
  const [trilhaSearch, setTrilhaSearch] = useState('');
  const [selectedGtId, setSelectedGtId] = useState<number | null>(null);
  const [modalRespostaId, setModalRespostaId] = useState<number | null>(null);
  const { data: respostasDoGt, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId });

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
    <div className="dashboard-container">
      <PageHeader
        title="Dashboard do redator"
        description="Escolha um GT, revise missões e publique pareceres com rapidez."
        actions={
          <>
            <Link to="/revisoes">
              <Button variant="primary" leftIcon={<Icon name="review" />}>Abrir revisões</Button>
            </Link>
            <Button
              variant="secondary"
              onClick={() => refetchPainel()}
              disabled={painelLoading}
              isLoading={painelLoading}
            >
              Atualizar respostas
            </Button>
            <Button
              variant="outline"
              onClick={() => refetchScore()}
              disabled={scoreLoading}
              isLoading={scoreLoading}
            >
              Atualizar score
            </Button>
          </>
        }
      />

      <section style={{ marginBottom: '2rem' }}>
        <Card>
          <div className="dashboard__card-header">
            <span>Score do mês</span>
            <strong>{scoreSummary?.current_points ?? 0} pts</strong>
          </div>
          <p>Meta mensal: {scoreSummary?.monthly_limit ?? 0} pts.</p>
          <div className="dashboard__progress">
            <div
              className="dashboard__progress-bar"
              style={{ width: `${Math.min((scoreSummary?.progress ?? 0) * 100, 100)}%` }}
            />
          </div>
        </Card>
      </section>

      <section className="dashboard__spotlight">
        <Card>
          <div className="dashboard__spotlight-header" style={{ marginBottom: '1.5rem' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.25rem' }}>GTs disponíveis</h2>
              <p style={{ color: 'var(--color-text-secondary)' }}>Selecione um GT para abrir trilhas e revisar conteúdo rapidamente.</p>
            </div>
            <input
              type="search"
              className="dashboard__search"
              placeholder="Buscar GT"
              value={gtSearch}
              onChange={(event) => setGtSearch(event.target.value)}
            />
          </div>
          <div className="dashboard__gt-grid">
            {filteredGts.map((gt) => {
              const responses = respostasPorGtMap.get(gt.id) ?? 0;
              return (
                <button
                  key={gt.id}
                  type="button"
                  className={`dashboard__gt-card ${selectedGtId === gt.id ? 'is-active' : ''}`}
                  onClick={() => setSelectedGtId(gt.id)}
                  aria-pressed={selectedGtId === gt.id}
                >
                  <div>
                    <strong>{gt.displayName}</strong>
                    <span>{gt.etapa ? `Etapa ${gt.etapa}` : 'Etapa não informada'}</span>
                  </div>
                  <span className="dashboard__gt-meta">{responses} resposta(s) recentes</span>
                </button>
              );
            })}
          </div>
        </Card>
      </section>

      <section className="dashboard__split">
        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Trilhas para revisão</h2>
              <p>{selectedGt ? `GT selecionado: ${selectedGt.displayName}` : 'Selecione um GT para iniciar.'}</p>
            </div>
            <input
              type="search"
              className="dashboard__search"
              placeholder="Buscar trilha"
              value={trilhaSearch}
              onChange={(event) => setTrilhaSearch(event.target.value)}
            />
          </div>
          {selectedGtId ? (
            <div className="dashboard__trilhas">
              {tarefasOrdenadas.map((tarefa) => (
                <div key={tarefa.id} className="dashboard__trilha-card">
                  <div>
                    <strong>
                      Trilha #{tarefa.ordem}
                      {tarefasRespondidas.has(tarefa.id) && (
                        <span className="dashboard__trilha-badge">Respondida ✓</span>
                      )}
                    </strong>
                    <span>{tarefa.nome}</span>
                    <small>{tarefa.etapa ? `Etapa ${tarefa.etapa}` : 'Etapa não informada'}</small>
                  </div>
                  <div className="dashboard__trilha-meta">
                    <span>{perguntasByTarefa.get(tarefa.id) ?? 0} missões</span>
                    <Link to={`/tarefas/${tarefa.id}?gt=${selectedGtId}`}>
                      <Button size="sm" variant="primary">Abrir trilha</Button>
                    </Link>
                  </div>
                </div>
              ))}
              {tarefasOrdenadas.length === 0 && (
                <div className="dashboard__empty-inline">Nenhuma trilha encontrada.</div>
              )}
            </div>
          ) : (
            <div className="dashboard__empty-inline">Selecione um GT para visualizar as trilhas.</div>
          )}
        </Card>

        <Card>
          <div className="dashboard__panel-header">
            <div>
              <h2>Respostas recentes</h2>
              <p>Acesso rápido aos últimos envios.</p>
            </div>
            <span className="dashboard__pill">{painelRespostasFiltradas.length} registros</span>
          </div>
          {painelLoading ? (
            <p className="dashboard__helper">Carregando respostas...</p>
          ) : painelRespostasFiltradas.length > 0 ? (
            <div className="dashboard__list">
              {painelRespostasFiltradas.slice(0, 6).map((resp) => (
                <div key={resp.id} className="dashboard__list-item">
                  <div>
                    <strong>{resp.gt_nome ?? `GT #${resp.gt}`}</strong>
                    <span>{buildPreview(resp.conteudo_html)}</span>
                  </div>
                  <div className="dashboard__list-meta">
                    <span>Atualizado {formatDateTime(resp.updated_at)}</span>
                    <span>{resp.autor_nome ?? (resp.autor ? `Usuário #${resp.autor}` : 'Autor não informado')}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setModalRespostaId(resp.id)}
                    >
                      Expandir
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="dashboard__empty-inline">Nenhuma resposta registrada ainda.</div>
          )}
        </Card>
      </section>

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
