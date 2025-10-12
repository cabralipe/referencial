import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useMarcarNotificacaoLida, useNotificacoes, useNotificationsRealtime } from '@/hooks/useNotificacoes';

import './NotificacoesPage.css';

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
                <pre>{JSON.stringify(notificacao.payload_json, null, 2)}</pre>
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
