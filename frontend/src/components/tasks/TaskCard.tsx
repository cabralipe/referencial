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

  const handleActionClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <div className="task-card">
      <Link to={`/tarefas/${tarefa.id}`} className="task-card__main">
        <div className="task-card__header">
          <span className="task-card__order">#{tarefa.ordem}</span>
          <TaskStatusBadge status={tarefa.status} />
        </div>
        <div className="task-card__body">
          <p className="task-card__title">{label}</p>
          {tarefa.etapa && <p className="task-card__subtitle">Etapa: {tarefa.etapa}</p>}
        </div>
      </Link>
      
      <div className="task-card__actions" onClick={handleActionClick}>
        {tarefa.tipo === 'OFICINA' && (
          <Link 
            to={`/quadros/${tarefa.id}`} 
            className="task-card__action-btn task-card__action-btn--quadros"
            title="Acessar Sistema de Quadros"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
              <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2"/>
            </svg>
            Quadros
          </Link>
        )}
        <Link 
          to={`/tarefas/${tarefa.id}`} 
          className="task-card__action-btn task-card__action-btn--details"
          title="Ver detalhes da tarefa"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2"/>
          </svg>
          Detalhes
        </Link>
      </div>
    </div>
  );
}
