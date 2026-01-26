import { useEffect, useState } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useTarefas } from '@/hooks/useTarefas';
import { usePppConfig, useUpdatePppConfig } from '@/hooks/usePpp';

import './AdminPppPage.css';

export function AdminPppPage() {
  const { data: tarefas, isLoading: tarefasLoading } = useTarefas({ tipo: 'PERGUNTAS' });
  const { data: config, isLoading: configLoading } = usePppConfig();
  const updateConfig = useUpdatePppConfig();

  const [descricao, setDescricao] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  useEffect(() => {
    if (config) {
      setDescricao(config.descricao ?? '');
      setSelectedIds(config.tarefa_ids ?? []);
    }
  }, [config]);

  if (tarefasLoading || configLoading) {
    return <FullPageLoader message="Carregando PPP..." />;
  }

  return (
    <div className="admin-ppp">
      <PageHeader
        title="Admin · PPP"
        description="Selecione quais trilhas compõem o PPP do município."
      />

      <Card>
        <div className="admin-ppp__config">
          <label>
            <span>Descrição do PPP</span>
            <textarea value={descricao} onChange={(event) => setDescricao(event.target.value)} rows={3} />
          </label>
          <Button
            variant="secondary"
            onClick={() => updateConfig.mutate({ tarefa_ids: selectedIds, descricao })}
            disabled={updateConfig.isPending}
          >
            {updateConfig.isPending ? 'Salvando...' : 'Salvar configuração'}
          </Button>
        </div>
      </Card>

      <div className="admin-ppp__lista">
        {(tarefas ?? []).map((tarefa) => (
          <Card key={tarefa.id}>
            <label className="admin-ppp__item">
              <input
                type="checkbox"
                checked={selectedIds.includes(tarefa.id)}
                onChange={(event) => {
                  if (event.target.checked) {
                    setSelectedIds((prev) => [...prev, tarefa.id]);
                  } else {
                    setSelectedIds((prev) => prev.filter((id) => id !== tarefa.id));
                  }
                }}
              />
              <div>
                <strong>{tarefa.nome || `Trilha #${tarefa.id}`}</strong>
                <span>{tarefa.etapa || 'Sem etapa'}</span>
              </div>
            </label>
          </Card>
        ))}
      </div>
    </div>
  );
}
