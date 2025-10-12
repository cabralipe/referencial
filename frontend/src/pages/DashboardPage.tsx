import { useMemo, useState } from 'react';

import { ApiError } from '@/api/client';
import { TaskCard } from '@/components/tasks/TaskCard';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useTarefas } from '@/hooks/useTarefas';

import './DashboardPage.css';

const STATUS_FILTERS = [
  { value: '', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_revisao', label: 'Em revisão' },
  { value: 'concluida', label: 'Concluída' },
];

const TIPO_FILTERS = [
  { value: '', label: 'Todos' },
  { value: 'PERGUNTAS', label: 'Questionário' },
  { value: 'OFICINA', label: 'Oficina' },
];

export function DashboardPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [etapaFilter, setEtapaFilter] = useState('');

  const { data: tarefas, isLoading, isError, error, refetch } = useTarefas({
    status: statusFilter || undefined,
    tipo: tipoFilter || undefined,
    etapa: etapaFilter || undefined,
  });

  const etapas = useMemo(() => {
    if (!tarefas) {
      return [] as string[];
    }
    const unique = new Set<string>();
    tarefas.forEach((tarefa) => {
      if (tarefa.etapa) {
        unique.add(tarefa.etapa);
      }
    });
    return Array.from(unique).sort((a, b) => a.localeCompare(b));
  }, [tarefas]);

  const resumo = useMemo(() => {
    if (!tarefas) {
      return {
        total: 0,
        rascunho: 0,
        emRevisao: 0,
        concluidas: 0,
      };
    }
    return tarefas.reduce(
      (acc, tarefa) => {
        acc.total += 1;
        const status = tarefa.status.toLowerCase();
        if (status === 'rascunho') acc.rascunho += 1;
        if (status === 'em_revisao') acc.emRevisao += 1;
        if (status === 'concluida') acc.concluidas += 1;
        return acc;
      },
      { total: 0, rascunho: 0, emRevisao: 0, concluidas: 0 },
    );
  }, [tarefas]);

  if (isLoading) {
    return <FullPageLoader message="Carregando tarefas..." />;
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Erro ao carregar tarefas';
    return (
      <div className="dashboard-error">
        <h2>Não foi possível carregar as tarefas</h2>
        <p>{message}</p>
        <button type="button" onClick={() => refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard__header">
        <div className="dashboard__title">
          <h1>Referencial Curricular</h1>
          <p>Acompanhe o andamento das tarefas e mergulhe no detalhe de cada GT.</p>
        </div>
        <div className="dashboard__summary">
          <div>
            <span className="summary__label">Total</span>
            <strong className="summary__value">{resumo.total}</strong>
          </div>
          <div>
            <span className="summary__label">Rascunho</span>
            <strong className="summary__value">{resumo.rascunho}</strong>
          </div>
          <div>
            <span className="summary__label">Em revisão</span>
            <strong className="summary__value">{resumo.emRevisao}</strong>
          </div>
          <div>
            <span className="summary__label">Concluídas</span>
            <strong className="summary__value">{resumo.concluidas}</strong>
          </div>
        </div>
      </div>

      <PageInstructions
        title="Como navegar pelo painel"
        description="Acompanhe o status geral das tarefas e identifique rapidamente onde atuar."
        items={[
          {
            title: 'Aplique filtros combinados',
            description: 'Use status, tipo e etapa para encontrar exatamente as tarefas que precisa revisar.',
          },
          {
            title: 'Abra o detalhe da tarefa',
            description: 'Clique em qualquer card para ver perguntas e respostas de um GT específico.',
          },
          {
            title: 'Monitore o progresso',
            description: 'Observe o resumo do topo para acompanhar a quantidade de tarefas por status.',
          },
        ]}
      />

      <div className="dashboard__filters">
        <label className="dashboard__filter">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="dashboard__filter">
          <span>Tipo</span>
          <select value={tipoFilter} onChange={(event) => setTipoFilter(event.target.value)}>
            {TIPO_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="dashboard__filter">
          <span>Etapa</span>
          <select value={etapaFilter} onChange={(event) => setEtapaFilter(event.target.value)}>
            <option value="">Todas</option>
            {etapas.map((etapa) => (
              <option key={etapa} value={etapa}>
                {etapa}
              </option>
            ))}
          </select>
        </label>
      </div>

      {tarefas && tarefas.length === 0 ? (
        <div className="dashboard__empty">
          <h2>Nenhuma tarefa encontrada</h2>
          <p>Ajuste os filtros ou aguarde a criação de novas tarefas.</p>
        </div>
      ) : (
        <div className="dashboard__grid">
          {tarefas?.map((tarefa) => (
            <TaskCard key={tarefa.id} tarefa={tarefa} />
          ))}
        </div>
      )}
    </div>
  );
}
