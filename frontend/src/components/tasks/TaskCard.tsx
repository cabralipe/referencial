import { Link } from 'react-router-dom';

import type { Tarefa } from '@/api/types';

import { TaskStatusBadge } from './TaskStatusBadge';
import './TaskCard.css';

interface TaskCardProps {
  tarefa: Tarefa;
}

const TIPO_LABEL: Record<string, string> = {
  PERGUNTAS: 'Questionário',
  OFICINA: 'Oficina',
};

export function TaskCard({ tarefa }: TaskCardProps) {
  const label = TIPO_LABEL[tarefa.tipo] ?? tarefa.tipo;

  return (
    <Link to={`/tarefas/${tarefa.id}`} className="task-card">
      <div className="task-card__header">
        <span className="task-card__order">#{tarefa.ordem}</span>
        <TaskStatusBadge status={tarefa.status} />
      </div>
      <div className="task-card__body">
        <p className="task-card__title">{tarefa.nome}</p>
        <p className="task-card__subtitle">{label}</p>
        {tarefa.etapa && <p className="task-card__subtitle">Etapa: {tarefa.etapa}</p>}
      </div>
    </Link>
  );
}
