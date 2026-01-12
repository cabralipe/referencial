import { useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAuth } from '@/context/AuthContext';
import { useClearThrottleBlock, useThrottleBlocks } from '@/hooks/useThrottleBlocks';
import type { ThrottleBlock } from '@/api/types';

import './ThrottleBlocksPage.css';

const ADMIN_ROLES = new Set(['admin_cliente', 'super_admin']);

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR');
};

const formatWait = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return '—';
  const minutes = Math.ceil(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.ceil(minutes / 60);
  return `${hours} h`;
};

function renderUser(block: ThrottleBlock) {
  if (block.usuario_nome || block.usuario_email) {
    return `${block.usuario_nome ?? ''}${block.usuario_nome && block.usuario_email ? ' • ' : ''}${block.usuario_email ?? ''}`;
  }
  if (block.usuario) {
    return `Usuário #${block.usuario}`;
  }
  return 'Anônimo';
}

export function ThrottleBlocksPage() {
  const { user } = useAuth();
  const [showAll, setShowAll] = useState(false);
  const { data: blocks, isLoading, isError } = useThrottleBlocks({ showAll });
  const clearBlock = useClearThrottleBlock();

  const ordered = useMemo(() => {
    return (blocks ?? []).slice().sort((a, b) => {
      if (!a.blocked_until && !b.blocked_until) return 0;
      if (!a.blocked_until) return 1;
      if (!b.blocked_until) return -1;
      return new Date(b.blocked_until).getTime() - new Date(a.blocked_until).getTime();
    });
  }, [blocks]);

  if (!user) {
    return <FullPageLoader message="Carregando painel..." />;
  }

  if (!ADMIN_ROLES.has(user.role)) {
    return (
      <div className="throttle-blocks__empty">
        <h2>Acesso restrito</h2>
        <p>Somente admins podem visualizar bloqueios de limite.</p>
      </div>
    );
  }

  return (
    <div className="throttle-blocks">
      <header className="throttle-blocks__header">
        <div>
          <h1>Bloqueios de limite</h1>
          <p>Visualize e libere usuários que atingiram o limite de requisições.</p>
        </div>
        <label className="throttle-blocks__toggle">
          <input
            type="checkbox"
            checked={showAll}
            onChange={(event) => setShowAll(event.target.checked)}
          />
          Mostrar histórico
        </label>
      </header>

      <PageInstructions
        title="Como usar"
        description="Use esta tela para acompanhar bloqueios por limite e liberar acessos quando necessário."
        items={[
          {
            title: 'Bloqueios ativos',
            description: 'A lista mostra bloqueios ainda ativos. Use "Mostrar histórico" para ver todos.',
          },
          {
            title: 'Liberar acesso',
            description: 'Clique em "Liberar" para remover o bloqueio no cache imediatamente.',
          },
          {
            title: 'Contexto',
            description: 'Scope indica a regra de limite que foi acionada.',
          },
        ]}
      />

      {isLoading && <FullPageLoader message="Carregando bloqueios..." />}
      {isError && (
        <div className="throttle-blocks__error">
          <h2>Não foi possível carregar</h2>
          <p>Tente novamente em instantes.</p>
        </div>
      )}

      {!isLoading && !isError && ordered.length === 0 && (
        <div className="throttle-blocks__empty">
          <h3>Nenhum bloqueio encontrado</h3>
          <p>Não há bloqueios ativos registrados no momento.</p>
        </div>
      )}

      {!isLoading && !isError && ordered.length > 0 && (
        <div className="throttle-blocks__table">
          <table>
            <thead>
              <tr>
                <th>Usuário</th>
                <th>Scope</th>
                <th>Ident</th>
                <th>Bloqueado até</th>
                <th>Espera</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((block) => (
                <tr key={block.id}>
                  <td>{renderUser(block)}</td>
                  <td>{block.scope}</td>
                  <td>{block.ident || '—'}</td>
                  <td>{formatDateTime(block.blocked_until)}</td>
                  <td>{formatWait(block.wait_seconds)}</td>
                  <td>
                    <button
                      type="button"
                      className="throttle-blocks__action"
                      onClick={() => clearBlock.mutate(block.id)}
                      disabled={clearBlock.isPending}
                    >
                      {clearBlock.isPending ? 'Liberando...' : 'Liberar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
