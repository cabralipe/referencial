import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';

import { ApiError, useApiClient } from '@/api/client';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useTarefas } from '@/hooks/useTarefas';
import { useAuth } from '@/context/AuthContext';
import type { Tarefa } from '@/api/types';

import './TasksPage.css';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos' },
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_desenvolvimento', label: 'Em desenvolvimento' },
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
  const { user } = useAuth();
  const client = useApiClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [tipoFilter, setTipoFilter] = useState('');
  const [etapaFilter, setEtapaFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [newNome, setNewNome] = useState('');
  const [newOrdem, setNewOrdem] = useState('');
  const [newEtapa, setNewEtapa] = useState('');
  const [newTipo, setNewTipo] = useState('PERGUNTAS');
  const [feedback, setFeedback] = useState('');

  const { data: tarefas, isLoading, isError, error, refetch } = useTarefas({
    status: statusFilter || undefined,
    tipo: tipoFilter || undefined,
    etapa: etapaFilter || undefined,
  });

  const canManage = user?.role === 'articulador' || user?.role === 'admin_cliente' || user?.role === 'super_admin';

  const createTarefa = useMutation({
    mutationFn: async (payload: Omit<Tarefa, 'id' | 'status'>) => {
      const response = await client.post<Tarefa>('/tarefas', { body: payload });
      return response.data;
    },
    onSuccess: () => {
      setNewNome('');
      setNewOrdem('');
      setNewEtapa('');
      setNewTipo('PERGUNTAS');
      setFeedback('Trilha criada com sucesso.');
      refetch();
    },
    onError: () => {
      setFeedback('Nao foi possivel criar a trilha.');
    },
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
      const nome = tarefa.nome?.toLowerCase() ?? '';
      const etapa = tarefa.etapa?.toLowerCase() ?? '';
      const tipo = TipoLabel[tarefa.tipo] ?? tarefa.tipo;
      const ordem = String(tarefa.ordem);
      return nome.includes(term) || etapa.includes(term) || tipo.toLowerCase().includes(term) || ordem.includes(term);
    });
  }, [tarefas, searchTerm]);

  if (isLoading) {
    return <FullPageLoader message="Carregando lista de trilhas pedagógicas..." />;
  }

  if (isError) {
    const message = error instanceof ApiError ? error.message : 'Erro ao carregar trilhas pedagógicas';
    return (
      <div className="tasks__error">
        <h2>Não foi possível carregar as trilhas pedagógicas</h2>
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
          <h1>Trilhas pedagógicas</h1>
          <p>Acesse o detalhamento de cada trilha e organize as entregas por GT.</p>
        </div>
      </header>

      {canManage && (
        <section className="tasks__create">
          <div>
            <h2>Criar trilha</h2>
            <p>Cadastre uma nova trilha diretamente pela plataforma.</p>
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setFeedback('');
              const ordemNumber = Number(newOrdem);
              if (!newNome.trim() || !Number.isFinite(ordemNumber) || ordemNumber <= 0) {
                setFeedback('Informe nome e ordem valida para criar a trilha.');
                return;
              }
              createTarefa.mutate({
                nome: newNome.trim(),
                ordem: ordemNumber,
                etapa: newEtapa.trim(),
                tipo: newTipo,
              });
            }}
          >
            <label>
              <span>Nome da trilha</span>
              <input value={newNome} onChange={(event) => setNewNome(event.target.value)} />
            </label>
            <label>
              <span>Ordem</span>
              <input
                type="number"
                min={1}
                value={newOrdem}
                onChange={(event) => setNewOrdem(event.target.value)}
              />
            </label>
            <label>
              <span>Etapa</span>
              <input value={newEtapa} onChange={(event) => setNewEtapa(event.target.value)} />
            </label>
            <label>
              <span>Tipo</span>
              <select value={newTipo} onChange={(event) => setNewTipo(event.target.value)}>
                {TIPO_OPTIONS.filter((option) => option.value).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" disabled={createTarefa.isPending}>
              {createTarefa.isPending ? 'Criando...' : 'Criar trilha'}
            </button>
            {feedback && <span className="tasks__feedback">{feedback}</span>}
          </form>
        </section>
      )}

      <PageInstructions
        title="Como encontrar a trilha certa"
        description="Combine filtros com a busca livre para chegar rapidamente ao conteúdo desejado."
        items={[
          {
            title: 'Filtre por status',
            description: 'Isolar trilhas em revisão ou concluídas ajuda a organizar mutirões de acompanhamento.',
          },
          {
            title: 'Busque por nome ou etapa',
            description: 'Digite o nome da trilha, etapa ou número da trilha no campo de busca para reduzir a lista.',
          },
          {
            title: 'Abra o detalhe',
            description: 'Use o link “Abrir” para navegar até a página de missões e editar as respostas do GT.',
          },
        ]}
        footer="A lista retorna no máximo 200 trilhas por vez. Ajuste os filtros caso não encontre o que procura."
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
            placeholder="Ex.: Ordem, Trilha ou Etapa"
          />
        </label>
      </div>

      {filteredTarefas.length === 0 ? (
        <div className="tasks__empty">
          <h3>Nenhum resultado</h3>
          <p>Ajuste os filtros ou refine a busca para encontrar outras trilhas.</p>
        </div>
      ) : (
        <div className="tasks__table-wrapper">
          <table className="tasks__table">
            <thead>
              <tr>
                <th>Ordem</th>
                <th>Trilha</th>
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
                  <td>{tarefa.nome}</td>
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
