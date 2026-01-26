import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import { usePppTrilhas } from '@/hooks/usePpp';
import { useApiClient } from '@/api/client';
import { useQuery } from '@tanstack/react-query';
import { fetchAllPaginated } from '@/utils/pagination';
import type { Pergunta } from '@/api/types';

import './PppPage.css';

type StatusTrilha = 'nao_iniciado' | 'em_andamento' | 'em_revisao' | 'devolvido' | 'concluido';

const statusLabel: Record<StatusTrilha, string> = {
  nao_iniciado: 'Não iniciado',
  em_andamento: 'Em andamento',
  em_revisao: 'Em revisão',
  devolvido: 'Devolvido',
  concluido: 'Concluído',
};

export function PppPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { gtOptions } = useAvailableGts();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;

  const client = useApiClient();
  const { data: pppData, isLoading: pppLoading } = usePppTrilhas({ gtId: selectedGtId ?? undefined });
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { data: revisoes, isLoading: revisoesLoading } = useRevisoes({ alvoTipo: 'resposta', pageSize: 200 });

  const perguntasQuery = useQuery({
    queryKey: ['perguntas', 'ppp', pppData?.trilhas?.map((t) => t.id)],
    enabled: Boolean(pppData?.trilhas?.length),
    queryFn: async () => {
      return fetchAllPaginated<Pergunta>(client.get, '/perguntas', { query: { page_size: 500 } });
    },
  });

  const perguntaMap = useMemo(() => {
    const map = new Map<number, Pergunta[]>();
    (perguntasQuery.data ?? []).forEach((pergunta) => {
      const list = map.get(pergunta.tarefa) ?? [];
      list.push(pergunta);
      map.set(pergunta.tarefa, list);
    });
    return map;
  }, [perguntasQuery.data]);

  const revisoesMap = useMemo(() => {
    const map = new Map<number, string>();
    (revisoes ?? []).forEach((rev) => {
      if (rev.alvo_tipo !== 'resposta') return;
      if (!map.has(rev.alvo_id)) {
        map.set(rev.alvo_id, rev.status);
      }
    });
    return map;
  }, [revisoes]);

  const trilhas = useMemo(() => {
    return (pppData?.trilhas ?? []).map((tarefa) => {
      const perguntas = (perguntaMap.get(tarefa.id) ?? []).filter((pergunta) => {
        if (!selectedGtId) return true;
        if (!pergunta.gts || pergunta.gts.length === 0) return true;
        return pergunta.gts.includes(selectedGtId);
      });
      const respostasDaTrilha = (respostas ?? []).filter((resp) => resp.tarefa_id === tarefa.id);
      const respondidas = respostasDaTrilha.filter((resp) => resp.conteudo_html?.trim()).length;
      const total = perguntas.length || 1;
      let status: StatusTrilha = 'nao_iniciado';
      const devolvidos = respostasDaTrilha.some((resp) => revisoesMap.get(resp.id) === 'reprovado');
      const emRevisao = respostasDaTrilha.some((resp) => revisoesMap.get(resp.id) === 'em_revisao');
      const aprovados = respostasDaTrilha.filter((resp) => revisoesMap.get(resp.id) === 'aprovado').length;
      if (devolvidos) status = 'devolvido';
      else if (emRevisao) status = 'em_revisao';
      else if (aprovados && aprovados === total) status = 'concluido';
      else if (respondidas > 0) status = 'em_andamento';
      return {
        tarefa,
        total,
        respondidas,
        status,
        percentual: total ? Math.round((respondidas / total) * 100) : 0,
      };
    });
  }, [pppData?.trilhas, perguntaMap, respostas, revisoesMap, selectedGtId]);

  if (pppLoading || respostasLoading || revisoesLoading || perguntasQuery.isLoading) {
    return <FullPageLoader message="Carregando PPP..." />;
  }

  return (
    <div className="ppp">
      <PageHeader
        title="PPP"
        description={pppData?.config?.descricao || 'Trilhas do Projeto Político-Pedagógico.'}
      />

      <div className="ppp__filters">
        <label>
          <span>GT</span>
          <select
            value={selectedGtId ?? ''}
            onChange={(event) => {
              const value = event.target.value ? Number(event.target.value) : null;
              if (value) {
                setSearchParams({ gt: String(value) });
              } else {
                setSearchParams({});
              }
            }}
          >
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="ppp__grid">
        {trilhas.map((item) => (
          <Card key={item.tarefa.id}>
            <div className="ppp__card">
              <div>
                <h2>{item.tarefa.nome || `Trilha #${item.tarefa.id}`}</h2>
                <p>{item.tarefa.etapa ? `Etapa: ${item.tarefa.etapa}` : 'Etapa não definida'}</p>
              </div>
              <span className={`ppp__status status-${item.status}`}>{statusLabel[item.status]}</span>
            </div>
            <div className="ppp__progress">
              <div className="ppp__progress-bar" style={{ width: `${item.percentual}%` }} />
            </div>
            <div className="ppp__meta">
              <span>{item.respondidas}/{item.total} blocos respondidos</span>
              <span>{item.percentual}% concluído</span>
            </div>
            <Link to={`/ppp/${item.tarefa.id}?gt=${selectedGtId ?? ''}`}>Abrir trilha PPP</Link>
          </Card>
        ))}
        {trilhas.length === 0 && <p className="ppp__empty">Nenhuma trilha PPP configurada.</p>}
      </div>
    </div>
  );
}
