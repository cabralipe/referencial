import type { ReactNode } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useMarcarNotificacaoLida, useNotificacoes, useNotificationsRealtime } from '@/hooks/useNotificacoes';

import './NotificacoesPage.css';

const KEY_LABELS: Record<string, string> = {
  revisao_id: 'Revisão',
  status: 'Status',
  comentario_id: 'Comentário',
  alvo_tipo: 'Alvo',
  alvo_id: 'ID do alvo',
  gt: 'GT',
  texto_id: 'Texto',
  texto_titulo: 'Título',
  texto_tipo: 'Tipo do texto',
  texto_created_at: 'Criado em',
  texto_updated_at: 'Atualizado em',
};

const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}T/;

function humanizeKey(key: string): string {
  if (KEY_LABELS[key]) {
    return KEY_LABELS[key];
  }
  return key
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/(^|\s)\w/g, (match) => match.toUpperCase());
}

function looksLikeDate(key: string, value: string): boolean {
  if (!value) {
    return false;
  }
  if (/_at$|_on$|_date$/i.test(key) || ISO_DATE_REGEX.test(value)) {
    const parsed = new Date(value);
    return !Number.isNaN(parsed.getTime());
  }
  return false;
}

function formatValue(key: string, value: unknown): ReactNode {
  if (value == null) {
    return '—';
  }

  if (typeof value === 'boolean') {
    return value ? 'Sim' : 'Não';
  }

  if (typeof value === 'number') {
    return value.toLocaleString('pt-BR');
  }

  if (typeof value === 'string') {
    if (looksLikeDate(key, value)) {
      const date = new Date(value);
      if (!Number.isNaN(date.getTime())) {
        return date.toLocaleString('pt-BR');
      }
    }
    return value;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '—';
    }
    if (value.every((item) => item == null)) {
      return '—';
    }
    if (value.every((item) => typeof item === 'string' || typeof item === 'number')) {
      return value.map((item) => String(item)).join(', ');
    }
    return (
      <code className="notificacoes__payload-code">{JSON.stringify(value, null, 2)}</code>
    );
  }

  if (typeof value === 'object') {
    return (
      <code className="notificacoes__payload-code">{JSON.stringify(value, null, 2)}</code>
    );
  }

  return String(value);
}

function renderPayload(payload: Record<string, unknown> | null | undefined): ReactNode {
  if (!payload || Object.keys(payload).length === 0) {
    return <p className="notificacoes__payload-empty">Sem detalhes adicionais.</p>;
  }

  return (
    <dl className="notificacoes__payload">
      {Object.entries(payload)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, value]) => (
          <div key={key} className="notificacoes__payload-row">
            <dt className="notificacoes__payload-key">{humanizeKey(key)}</dt>
            <dd className="notificacoes__payload-value">{formatValue(key, value)}</dd>
          </div>
        ))}
    </dl>
  );
}

export function NotificacoesPage() {
  const { data: notificacoes, isLoading, refetch } = useNotificacoes();
  const marcarLida = useMarcarNotificacaoLida();
  const connection = useNotificationsRealtime();

  if (isLoading && !notificacoes) {
    return <FullPageLoader message="Carregando notificações..." />;
  }

  return (
    <div className="notificacoes">
      <header className="notificacoes__header">
        <div>
          <h1>Notificações</h1>
          <p>Fique por dentro de mudanças em tempo real para GTs, revisões e comentários.</p>
        </div>
      </header>

      <PageInstructions
        title="Organize seu fluxo"
        description="Centralize alertas da plataforma e marque como lido quando tratar cada item."
        items={[
          {
            title: 'Classifique por tipo',
            description: 'Use o campo “tipo” para entender de onde veio o evento e quem solicitou a ação.',
          },
          {
            title: 'Clique quando resolver',
            description: 'Marcar como lida remove o item da lista e limpa o contador no cabeçalho.',
          },
          {
            title: 'Atualize periodicamente',
            description: 'A lista é atualizada automaticamente a cada minuto; force uma recarga se necessário.',
          },
        ]}
      />

      <div className="notificacoes__actions">
        <span
          className={
            connection.status === 'open'
              ? 'notificacoes__status notificacoes__status--ok'
              : 'notificacoes__status notificacoes__status--warn'
          }
        >
          WebSocket: {connection.status === 'open' ? 'conectado' : connection.status === 'connecting' ? 'conectando…' : 'offline'}
        </span>
        <button type="button" className="ghost" onClick={() => refetch()}>
          Recarregar agora
        </button>
      </div>

      {notificacoes && notificacoes.length > 0 ? (
        <ul className="notificacoes__lista">
          {notificacoes.map((notificacao) => (
            <li key={notificacao.id} className={notificacao.lida ? '' : 'notificacoes__item--unread'}>
              <div>
                <strong>{notificacao.tipo}</strong>
                <span>{new Date(notificacao.created_at).toLocaleString('pt-BR')}</span>
                {renderPayload(notificacao.payload_json)}
              </div>
              <button
                type="button"
                onClick={() => marcarLida.mutate(notificacao.id)}
                disabled={notificacao.lida || marcarLida.isPending}
              >
                {notificacao.lida ? 'Lida' : 'Marcar como lida'}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="notificacoes__empty">
          <h3>Sem notificações pendentes</h3>
          <p>Quando houver novos eventos eles aparecerão aqui automaticamente.</p>
        </div>
      )}
    </div>
  );
}
