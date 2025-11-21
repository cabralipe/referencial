import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAuditLogs } from '@/hooks/useAuditLogs';
import { useAuth } from '@/context/AuthContext';
import type { AuditLog } from '@/api/types';

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
  'curriculum.Resposta': 'Resposta de tarefa',
  'curriculum.TextoUnico': 'Texto Único',
  'curriculum.TextoColaborativo': 'Texto colaborativo',
  'workshop.Quadro': 'Quadro',
  'comments.Comentario': 'Comentário',
  'reviews.Revisao': 'Revisão',
  export: 'Exportação',
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
  const { user, cliente } = useAuth();

  const { data: logs, isLoading, refetch, isFetching } = useAuditLogs({
    entidade: entidade || undefined,
    entidadeId: entidadeId ? Number(entidadeId) : undefined,
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    refetch();
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
            <span>Entidade ID (opcional)</span>
            <input
              type="number"
              value={entidadeId}
              onChange={(event) => setEntidadeId(event.target.value)}
              placeholder="Ex.: 120"
            />
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
            <span className="audit__badge audit__badge--muted">Entidade</span>
            <strong>{entidade || 'Todas'}</strong>
            <small>ID {entidadeId || 'Todos'}</small>
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
                {group.items.map((log) => (
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
