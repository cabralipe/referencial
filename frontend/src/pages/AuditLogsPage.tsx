import { FormEvent, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAuditLogs } from '@/hooks/useAuditLogs';

import './AuditLogsPage.css';

export function AuditLogsPage() {
  const [entidade, setEntidade] = useState('');
  const [entidadeId, setEntidadeId] = useState('');

  const { data: logs, isLoading, refetch, isFetching } = useAuditLogs({
    entidade: entidade || undefined,
    entidadeId: entidadeId ? Number(entidadeId) : undefined,
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    refetch();
  };

  if (isLoading && !logs) {
    return <FullPageLoader message="Carregando trilha de auditoria..." />;
  }

  return (
    <div className="audit">
      <header className="audit__header">
        <div>
          <h1>Auditoria</h1>
          <p>Rastreie ações recentes para auditar alterações e garantir conformidade.</p>
        </div>
      </header>

      <PageInstructions
        title="Use a trilha a seu favor"
        description="Combine filtros para encontrar eventos críticos rapidamente."
        items={[
          {
            title: 'Filtre por entidade',
            description: 'Informe o modelo (ex.: resposta, texto_unico) para reduzir o volume retornado.',
          },
          {
            title: 'Acompanhe IDs específicos',
            description: 'Use o ID da entidade para mapear quem alterou o registro e em qual horário.',
          },
          {
            title: 'Analise o diff JSON',
            description: 'O campo diff_json mostra o que mudou; útil para investigar regressões.',
          },
        ]}
      />

      <section className="audit__filters">
        <form onSubmit={handleSubmit}>
          <label>
            <span>Entidade</span>
            <input value={entidade} onChange={(event) => setEntidade(event.target.value)} placeholder="Ex.: resposta" />
          </label>
          <label>
            <span>Entidade ID</span>
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
        <table className="audit__tabela">
          <thead>
            <tr>
              <th>ID</th>
              <th>Entidade</th>
              <th>Ação</th>
              <th>Usuário</th>
              <th>Data</th>
              <th>Diff</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.id}</td>
                <td>
                  {log.entidade} #{log.entidade_id}
                </td>
                <td>{log.acao}</td>
                <td>{log.usuario_id ?? '—'}</td>
                <td>{new Date(log.timestamp).toLocaleString('pt-BR')}</td>
                <td>
                  <pre>{JSON.stringify(log.diff_json, null, 2)}</pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="audit__empty">
          <p>Nenhum evento encontrado para os filtros definidos.</p>
        </div>
      )}
    </div>
  );
}
