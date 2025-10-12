import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useTarefas } from '@/hooks/useTarefas';

import './TasksPage.css';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_revisao', label: 'Em revisão' },
  { value: 'concluida', label: 'Concluída' },
];

const TIPO_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'PERGUNTAS', label: 'Questionário' },
  { value: 'OFICINA', label: 'Oficina' },
];

const TipoLabel: Record<string, string> = {
  PERGUNTAS: 'Questionário',
  OFICINA: 'Oficina',
};

export function TasksPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [etapaFilter, setEtapaFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

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

  const filteredTarefas = useMemo(() => {
    if (!tarefas) {
      return [];
    }
    const term = searchTerm.trim().toLowerCase();
    if (!term) {
      return tarefas;
    }
    return tarefas.filter((tarefa) => {
      const etapa = tarefa.etapa?.toLowerCase() ?? '';
      const tipo = TipoLabel[tarefa.tipo] ?? tarefa.tipo;
      const ordem = String(tarefa.ordem);
      return etapa.includes(term) || tipo.toLowerCase().includes(term) || ordem.includes(term);
    });
  }, [tarefas, searchTerm]);

  if (isLoading) {
    return <FullPageLoader message="Carregando lista de tarefas..." />;
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Erro ao carregar tarefas';
    return (
      <div className="tasks__error">
        <h2>Não foi possível carregar as tarefas</h2>
        <p>{message}</p>
        <button type="button" onClick={() => refetch()}>
          Tentar novamente
        </button>
      </div>
    );
  }

  return (
    <div className="tasks">
      <header className="tasks__header">
        <div>
          <h1>Tarefas</h1>
          <p>Acesse o detalhamento de cada tarefa e organize as entregas por GT.</p>
        </div>
      </header>

      <PageInstructions
        title="Como encontrar a tarefa certa"
        description="Combine filtros com a busca livre para chegar rapidamente ao conteúdo desejado."
        items={[
          {
            title: 'Filtre por status',
            description: 'Isolar tarefas em revisão ou concluídas ajuda a organizar mutirões de acompanhamento.',
          },
          {
            title: 'Busque por etapa',
            description: 'Digite o nome da etapa ou número da tarefa no campo de busca para reduzir a lista.',
          },
          {
            title: 'Abra o detalhe',
            description: 'Use o link “Abrir” para navegar até a página de perguntas e editar as respostas do GT.',
          },
        ]}
        footer="A lista retorna no máximo 200 tarefas por vez. Ajuste os filtros caso não encontre o que procura."
      />

      <div className="tasks__controls">
        <label>
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Tipo</span>
          <select value={tipoFilter} onChange={(event) => setTipoFilter(event.target.value)}>
            {TIPO_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
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

        <label className="tasks__search">
          <span>Busca rápida</span>
          <input
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Ex.: etapa 3 ou 12"
          />
        </label>
      </div>

      {filteredTarefas.length === 0 ? (
        <div className="tasks__empty">
          <h3>Nenhum resultado</h3>
          <p>Ajuste os filtros ou refine a busca para encontrar outras tarefas.</p>
        </div>
      ) : (
        <div className="tasks__table-wrapper">
          <table className="tasks__table">
            <thead>
              <tr>
                <th>#</th>
                <th>Tipo</th>
                <th>Etapa</th>
                <th>Status</th>
                <th aria-label="Ações" />
              </tr>
            </thead>
            <tbody>
              {filteredTarefas.map((tarefa) => (
                <tr key={tarefa.id}>
                  <td>{tarefa.ordem}</td>
                  <td>{TipoLabel[tarefa.tipo] ?? tarefa.tipo}</td>
                  <td>{tarefa.etapa}</td>
                  <td>
                    <TaskStatusBadge status={tarefa.status} />
                  </td>
                  <td>
                    <Link to={`/tarefas/${tarefa.id}`}>Abrir</Link>
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
