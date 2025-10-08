import './TaskStatusBadge.css';

interface TaskStatusBadgeProps {
  status: string;
}

const STATUS_META: Record<string, { label: string; className: string }> = {
  rascunho: { label: 'Rascunho', className: 'status-badge--draft' },
  em_revisao: { label: 'Em revisão', className: 'status-badge--review' },
  concluida: { label: 'Concluída', className: 'status-badge--done' },
};

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  const normalized = status?.toLowerCase() ?? 'rascunho';
  const meta = STATUS_META[normalized] ?? {
    label: status,
    className: 'status-badge--default',
  };

  return <span className={`status-badge ${meta.className}`}>{meta.label}</span>;
}
