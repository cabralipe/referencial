import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useRevisoes } from '@/hooks/useRevisoes';
import type { Revisao, RevisaoAlvoPreview } from '@/api/types';

import './RedatorInboxPage.css';

const formatDate = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('pt-BR');
};

type TabKey = 'novo' | 'em_revisao' | 'devolvido' | 'validado';

const TAB_LABELS: Record<TabKey, string> = {
  novo: 'Novo',
  em_revisao: 'Em revisão',
  devolvido: 'Devolvido',
  validado: 'Validado',
};

export function RedatorInboxPage() {
  const [tab, setTab] = useState<TabKey>('novo');
  const revisoesEmRevisao = useRevisoes({ status: 'em_revisao', pageSize: 300 });
  const revisoesReprovadas = useRevisoes({ status: 'reprovado', pageSize: 300 });
  const revisoesAprovadas = useRevisoes({ status: 'aprovado', pageSize: 300 });

  const loading = revisoesEmRevisao.isLoading || revisoesReprovadas.isLoading || revisoesAprovadas.isLoading;

  const [novas, emRevisao] = useMemo(() => {
    const list = revisoesEmRevisao.data ?? [];
    const novasItems = list.filter((item) => !item.revisor);
    const emRevisaoItems = list.filter((item) => Boolean(item.revisor));
    return [novasItems, emRevisaoItems];
  }, [revisoesEmRevisao.data]);

  const tabData: Record<TabKey, Revisao[]> = {
    novo: novas,
    em_revisao: emRevisao,
    devolvido: revisoesReprovadas.data ?? [],
    validado: revisoesAprovadas.data ?? [],
  };

  if (loading) {
    return <FullPageLoader message="Carregando revisões..." />;
  }

  return (
    <div className="redator-inbox">
      <PageHeader
        title="Inbox de Revisões"
        description="Acompanhe as entregas dos GTs e acelere as devolutivas."
      />

      <div className="redator-inbox__tabs">
        {(Object.keys(TAB_LABELS) as TabKey[]).map((key) => (
          <button
            key={key}
            type="button"
            className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}
          >
            {TAB_LABELS[key]} <span>{tabData[key].length}</span>
          </button>
        ))}
      </div>

      <div className="redator-inbox__list">
        {tabData[tab].map((rev) => {
          const preview = rev.alvo_preview as RevisaoAlvoPreview | null;
          const tarefaNome = preview && 'tarefa_nome' in preview ? preview.tarefa_nome : null;
          const tarefaEtapa = preview && 'tarefa_etapa' in preview ? preview.tarefa_etapa : null;
          const autor = preview && 'autor_nome' in preview ? preview.autor_nome : null;
          const titulo = tarefaNome || `Trilha #${preview && 'tarefa' in preview ? preview.tarefa : '—'}`;
          return (
            <Card key={rev.id}>
              <div className="redator-inbox__item">
                <div>
                  <strong>{titulo}</strong>
                  <span>{tarefaEtapa ? `Etapa: ${tarefaEtapa}` : 'Etapa não definida'}</span>
                  <span>Autor: {autor || 'Não informado'}</span>
                </div>
                <div className="redator-inbox__meta">
                  <span>Status: {rev.status}</span>
                  <span>Atualizado: {formatDate(rev.updated_at)}</span>
                  {preview && (
                    <Link to={`/redator/revisoes/${preview.type}/${preview.id}`}>
                      Abrir
                    </Link>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
        {tabData[tab].length === 0 && (
          <Card>
            <p>Sem itens nesta etapa.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
