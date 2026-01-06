import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAuditLogs, useOnlineUsers, useSessionHistory } from '@/hooks/useAuditLogs';
import { useUsuariosLookup } from '@/hooks/useUsuariosLookup';
import { useAuth } from '@/context/AuthContext';
import type { AuditLog, OnlineUser } from '@/api/types';
type UsuarioSuggestion = { id: number; nome: string; email: string };

import './AuditLogsPage.css';

const ADMIN_ROLES = new Set(['super_admin', 'admin_cliente']);
const EXTENDED_ACCESS_FLAG = 'ff.audit.access.extend';
const ENTIDADE_OPTIONS = [
  { value: '', label: 'Todas' },
  { value: 'resposta', label: 'Resposta' },
  { value: 'texto_unico', label: 'Texto Único' },
  { value: 'texto_colaborativo', label: 'Texto Colaborativo' },
  { value: 'quadro', label: 'Quadro' },
  { value: 'comentario', label: 'Comentário' },
  { value: 'revisao', label: 'Revisão' },
  { value: 'export', label: 'Exportação' },
];

const ENTIDADE_LABELS: Record<string, string> = {
  'curriculum.Resposta': 'Resposta de trilha',
  'curriculum.TextoUnico': 'Texto Único',
  'curriculum.TextoColaborativo': 'Texto colaborativo',
  'workshop.Quadro': 'Quadro',
  'comments.Comentario': 'Comentário',
  'reviews.Revisao': 'Revisão',
  export: 'Exportação',
};

const ENTIDADE_VALUE_TO_DB: Record<string, string> = {
  resposta: 'curriculum.Resposta',
  texto_unico: 'curriculum.TextoUnico',
  texto_colaborativo: 'curriculum.TextoColaborativo',
  quadro: 'workshop.Quadro',
  comentario: 'comments.Comentario',
  revisao: 'reviews.Revisao',
  export: 'export',
};

const ACTION_LABELS: Record<string, string> = {
  created: 'criou',
  updated: 'atualizou',
  deleted: 'removeu',
};

function actionSentence(log: AuditLog) {
  const entidadeLabel = ENTIDADE_LABELS[log.entidade] ?? log.entidade;
  const action = ACTION_LABELS[log.acao.toLowerCase()] ?? log.acao;
  const usuario = log.usuario_nome || log.usuario_email || `Usuário #${log.usuario_id ?? 'desconhecido'}`;
  return `${usuario} ${action} ${entidadeLabel} #${log.entidade_id}`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleString('pt-BR');
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .toLowerCase()
    .replace(/(^|\s)\w/g, (match) => match.toUpperCase());
}

function formatValue(value: unknown): string {
  if (value == null) return '—';
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não';
  if (typeof value === 'number') return value.toLocaleString('pt-BR');
  if (typeof value === 'string') {
    const maybeDate = new Date(value);
    if (!Number.isNaN(maybeDate.getTime()) && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
      return maybeDate.toLocaleString('pt-BR');
    }
    return value;
  }
  if (Array.isArray(value)) return value.map((item) => formatValue(item)).join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function renderDiffSummary(diff: Record<string, unknown> | null | undefined) {
  const snapshot = (diff as { current?: Record<string, unknown> } | null)?.current ?? diff ?? {};
  const entries = Object.entries(snapshot);
  if (entries.length === 0) {
    return <p className="audit__helper">Sem detalhes capturados para este evento.</p>;
  }
  return (
    <dl className="audit__details">
      {entries.map(([key, value]) => (
        <div key={key} className="audit__details-row">
          <dt>{humanizeKey(key)}</dt>
          <dd>{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function AuditLogsPage() {
  const [entidade, setEntidade] = useState('');
  const [entidadeId, setEntidadeId] = useState('');
  const [usuarioId, setUsuarioId] = useState('');
  const [acao, setAcao] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [usuarioQuery, setUsuarioQuery] = useState('');
  const [pageSize, setPageSize] = useState('4');
  // Estados aplicados (usados na consulta)
  const [appliedEntidade, setAppliedEntidade] = useState<string>('');
  const [appliedEntidadeId, setAppliedEntidadeId] = useState<number | undefined>(undefined);
  const [appliedUsuarioId, setAppliedUsuarioId] = useState<number | undefined>(undefined);
  const [appliedAcao, setAppliedAcao] = useState<string>('');
  const [appliedDateFrom, setAppliedDateFrom] = useState<string>('');
  const [appliedDateTo, setAppliedDateTo] = useState<string>('');
  const [appliedPageSize, setAppliedPageSize] = useState<number>(Number('4'));
  const [dateFromDisplay, setDateFromDisplay] = useState('');
  const [dateToDisplay, setDateToDisplay] = useState('');
  const { user, cliente } = useAuth();

  const { data: logs, isLoading, refetch, isFetching } = useAuditLogs({
    entidade: appliedEntidade || undefined,
    entidadeId: appliedEntidadeId,
    usuarioId: appliedUsuarioId,
    acao: appliedAcao || undefined,
    dateFrom: appliedDateFrom || undefined,
    dateTo: appliedDateTo || undefined,
    pageSize: appliedPageSize || undefined,
  });
  const {
    data: onlineUsers,
    isLoading: isLoadingOnline,
    isFetching: isFetchingOnline,
  } = useOnlineUsers();
  const {
    data: sessionHistory,
    isLoading: isLoadingSessions,
    isFetching: isFetchingSessions,
  } = useSessionHistory({ days: 30, limit: 200 });
  const [onlineExpanded, setOnlineExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const mappedEntidade = entidade ? (ENTIDADE_VALUE_TO_DB[entidade] ?? entidade) : '';
    setAppliedEntidade(mappedEntidade);
    setAppliedEntidadeId(entidadeId ? Number(entidadeId) : undefined);
    setAppliedUsuarioId(usuarioId ? Number(usuarioId) : undefined);
    setAppliedAcao(acao || '');
    setAppliedDateFrom(dateFrom || '');
    setAppliedDateTo(dateTo || '');
    setAppliedPageSize(pageSize ? Number(pageSize) : 200);
  };

  const groupedLogs = useMemo(() => {
    if (!logs) return [];
    return logs.reduce(
      (acc, log) => {
        const date = new Date(log.timestamp);
        const dateKey = date.toLocaleDateString('pt-BR');
        const existing = acc.find((item) => item.date === dateKey);
        if (existing) {
          existing.items.push(log);
          return acc;
        }
        return [...acc, { date: dateKey, items: [log] }];
      },
      [] as { date: string; items: typeof logs }[],
    );
  }, [logs]);

  const sortedOnlineUsers = useMemo<OnlineUser[]>(() => {
    if (!onlineUsers) return [];
    return [...onlineUsers].sort(
      (a, b) => new Date(b.last_seen_at).getTime() - new Date(a.last_seen_at).getTime(),
    );
  }, [onlineUsers]);

  const sortedSessionHistory = useMemo<OnlineUser[]>(() => {
    if (!sessionHistory) return [];
    return [...sessionHistory].sort(
      (a, b) => new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime(),
    );
  }, [sessionHistory]);

  const isExtendedAccess = cliente?.flags?.[EXTENDED_ACCESS_FLAG];
  const isAuthorized = !!user && (ADMIN_ROLES.has(user.role) || isExtendedAccess);

  if (!isAuthorized) {
    return (
      <div className="audit audit--forbidden">
        <h1>Acesso restrito</h1>
        <p>Somente Super Admin/Admin Cliente têm permissão direta.</p>
        <p className="audit__hint">
          Um admin pode liberar leitura para demais perfis ativando a flag <code className="audit__code">{EXTENDED_ACCESS_FLAG}</code> no painel.
        </p>
      </div>
    );
  }

  if (isLoading && !logs) {
    return <FullPageLoader message="Carregando trilha de auditoria..." />;
  }

  return (
    <div className="audit">
      <header className="audit__header">
        <div>
          <h1>Auditoria</h1>
          <p>
            Rastreie ações recentes com linguagem clara. Mostramos quem fez, o que fez, quando entrou e os dados alterados.
            Admin pode liberar leitura para demais perfis ativando a flag
            <code className="audit__code">{EXTENDED_ACCESS_FLAG}</code> no painel.
          </p>
        </div>
      </header>

      <PageInstructions
        title="Use a trilha a seu favor"
        description="Combine filtros para encontrar eventos críticos rapidamente."
        items={[
          {
            title: 'Filtre por entidade',
            description: 'Selecione o tipo (Resposta, Texto Único, Quadro) sem termos técnicos.',
          },
          {
            title: 'Acompanhe IDs específicos',
            description: 'Use o ID quando quiser chegar direto em um registro; é opcional.',
          },
          {
            title: 'Leia o que mudou',
            description: 'Os detalhes já vêm traduzidos; use “Ver detalhes” para ver campos e valores registrados.',
          },
        ]}
      />

      <section className="audit__online">
        <div className="audit__online-header">
          <div>
            <span className="audit__badge">Presença em tempo real</span>
            <h2>Quem está online agora</h2>
            {onlineExpanded && (
              <p>
                Mostramos quem acessou a plataforma, o horário de entrada e a última atividade para facilitar relatórios
                rápidos.
              </p>
            )}
          </div>
          <div className="audit__online-count">
            <strong>{sortedOnlineUsers.length}</strong>
            <span>online</span>
            {onlineExpanded && (
              <small>{isFetchingOnline ? 'Atualizando...' : 'Atualiza a cada minuto'}</small>
            )}
          </div>
        </div>
        {isLoadingOnline ? (
          <p className="audit__helper">Carregando sessões ativas...</p>
        ) : onlineExpanded ? (
          sortedOnlineUsers.length > 0 ? (
            <ul className="audit__online-list">
              {sortedOnlineUsers.map((session) => (
                <li key={session.id} className="audit__online-card">
                  <div className="audit__online-main">
                    <div className="audit__online-name">
                      <span className="audit__status-dot" aria-hidden="true" />
                      <strong>{session.usuario_nome || 'Usuário sem nome'}</strong>
                    </div>
                    <span className="audit__muted">{session.usuario_email || 'E-mail não informado'}</span>
                  </div>
                  <div className="audit__online-meta">
                    <span>Perfil: {session.usuario_role ?? '—'}</span>
                    <span>Entrou: {formatDate(session.first_seen_at) ?? '—'}</span>
                    <span>Última atividade: {formatDate(session.last_seen_at) ?? '—'}</span>
                    {session.device_label && <span>Dispositivo: {session.device_label}</span>}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div className="audit__empty audit__empty--inline">
              <p>Ninguém online agora. Assim que alguém acessar, registramos horário e data aqui.</p>
            </div>
          )
        ) : null}
        <div className="audit__toggle">
          <button type="button" onClick={() => setOnlineExpanded((prev) => !prev)}>
            {onlineExpanded ? '▲ Minimizar' : '▼ Expandir'}
          </button>
        </div>
      </section>

      <section className="audit__online">
        <div className="audit__online-header">
          <div>
            <span className="audit__badge">Histórico</span>
            <h2>Logins recentes</h2>
            {historyExpanded && <p>Lista dos últimos acessos ao sistema pelo seu cliente.</p>}
          </div>
          <div className="audit__online-count">
            <strong>{sortedSessionHistory.length}</strong>
            <span>registros</span>
            {historyExpanded && (
              <small>{isFetchingSessions ? 'Atualizando...' : 'Últimos 30 dias'}</small>
            )}
          </div>
        </div>
        {isLoadingSessions ? (
          <p className="audit__helper">Carregando histórico de logins...</p>
        ) : historyExpanded ? (
          sortedSessionHistory.length > 0 ? (
            <div className="audit__table-wrapper">
              <table className="audit__table">
                <thead>
                  <tr>
                    <th>Usuário</th>
                    <th>Login</th>
                    <th>Duração</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSessionHistory.map((session) => {
                    const secs = session.session_duration_seconds ?? 0;
                    const hours = Math.floor(secs / 3600);
                    const minutes = Math.floor((secs % 3600) / 60);
                    const durationLabel = hours > 0 ? `${hours}h ${minutes}min` : `${minutes}min`;
                    return (
                      <tr key={`hist-${session.id}`}>
                        <td>
                          <div>
                            <strong>{session.usuario_nome || 'Usuário sem nome'}</strong>
                            <div className="audit__muted">{session.usuario_email || 'E-mail não informado'}</div>
                          </div>
                        </td>
                        <td>{formatDate(session.first_seen_at) ?? '—'}</td>
                        <td>{durationLabel}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="audit__empty audit__empty--inline">
              <p>Nenhum login registrado no período selecionado.</p>
            </div>
          )
        ) : null}
        <div className="audit__toggle">
          <button type="button" onClick={() => setHistoryExpanded((prev) => !prev)}>
            {historyExpanded ? '▲ Minimizar' : '▼ Expandir'}
          </button>
        </div>
      </section>

      <section className="audit__filters">
        <form onSubmit={handleSubmit}>
          <label>
            <span>Entidade</span>
            <select value={entidade} onChange={(event) => setEntidade(event.target.value)}>
              {ENTIDADE_OPTIONS.map((option) => (
                <option key={option.value || 'all'} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Usuário</span>
            <input
              type="text"
              value={usuarioQuery}
              onChange={(event) => setUsuarioQuery(event.target.value)}
              placeholder="Nome ou e-mail"
            />
            {usuarioQuery.trim().length >= 2 && (
              <UsuarioSuggestions query={usuarioQuery} onPick={(u) => { setUsuarioId(String(u.id)); setUsuarioQuery(`${u.nome} (${u.email})`); }} />
            )}
          </label>
          <label>
            <span>Ação</span>
            <select value={acao} onChange={(event) => setAcao(event.target.value)}>
              <option value="">Todas</option>
              <option value="created">Criou</option>
              <option value="updated">Atualizou</option>
              <option value="deleted">Removeu</option>
            </select>
          </label>
          <button type="submit" className="primary" disabled={isFetching}>
            {isFetching ? 'Atualizando...' : 'Aplicar filtros'}
          </button>
        </form>
      </section>

      {logs && logs.length > 0 ? (
        <div className="audit__summary">
          <div>
            <span className="audit__badge">Eventos</span>
            <strong>{logs.length}</strong>
            <small>total filtrado</small>
          </div>
          <div>
            <span className="audit__badge audit__badge--muted">Clientes</span>
            <strong>Inclui cliente {logs[0]?.cliente ? `#${logs[0].cliente}` : 'atual'}</strong>
            <small>Respeita isolamento por tenant</small>
          </div>
        </div>
      ) : null}


      {groupedLogs.length > 0 ? (
        <div className="audit__groups">
          {groupedLogs.map((group) => (
            <section key={group.date} className="audit__group">
              <header className="audit__group-header">
                <h3>{group.date}</h3>
                <span>{group.items.length} evento(s)</span>
              </header>
              <div className="audit__cards">
                {group.items.map((log) => {
                  const registro = formatDate(log.timestamp) ?? log.timestamp;
                  const ultimoAcesso = formatDate(log.usuario_last_login);
                  return (
                    <article key={log.id} className="audit__card">
                      <header>
                        <div>
                          <p className="audit__entity">{actionSentence(log)}</p>
                          <div className="audit__meta">
                            <span className={`audit__chip audit__chip--${log.acao.toLowerCase()}`}>
                              {ACTION_LABELS[log.acao.toLowerCase()] ?? log.acao}
                            </span>
                            <span>
                              Usuário: {log.usuario_nome || '—'} {log.usuario_email ? `(${log.usuario_email})` : ''}
                            </span>
                            <span>Cliente: #{log.cliente}</span>
                            <span>Registro: {registro}</span>
                            {ultimoAcesso && <span>Último acesso: {ultimoAcesso}</span>}
                          </div>
                        </div>
                        <span className="audit__id">Evento #{log.id}</span>
                      </header>
                      <details>
                        <summary>Ver detalhes</summary>
                        {renderDiffSummary(log.diff_json)}
                      </details>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <div className="audit__empty">
          <p>Nenhum evento encontrado para os filtros definidos.</p>
        </div>
      )}
    </div>
  );
}
function UsuarioSuggestions({ query, onPick }: { query: string; onPick: (u: UsuarioSuggestion) => void }) {
  const { data: suggestions = [] } = useUsuariosLookup(query);
  if (suggestions.length === 0) return null;
  return (
    <div className="audit__autocomplete">
      <ul>
        {suggestions.slice(0, 6).map((u) => (
          <li key={u.id}>
            <button type="button" onClick={() => onPick(u)}>
              <strong>{u.nome}</strong>
              <span>{u.email}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
function isoToBr(iso: string): string {
  if (!iso) return '';
  const parts = iso.split('-');
  if (parts.length !== 3) return '';
  const [y, m, d] = parts;
  if (!y || !m || !d) return '';
  return `${d}/${m}/${y}`;
}

function brToIso(br: string): string {
  const m = br.match(/^([0-9]{2})\/([0-9]{2})\/([0-9]{4})$/);
  if (!m) return '';
  const d = m[1];
  const mo = m[2];
  const y = m[3];
  return `${y}-${mo}-${d}`;
}

function normalizeBrInput(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  const a = digits.slice(0, 2);
  const b = digits.slice(2, 4);
  const c = digits.slice(4, 8);
  let out = a;
  if (b) out = `${out}/${b}`;
  if (c) out = `${out}/${c}`;
  return out;
}
