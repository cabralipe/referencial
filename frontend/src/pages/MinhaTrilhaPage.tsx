import { useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useTarefas } from '@/hooks/useTarefas';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import { fetchAllPaginated } from '@/utils/pagination';
import { useContinuar } from '@/hooks/useContinuar';
import type { Pergunta, Resposta } from '@/api/types';

import './MinhaTrilhaPage.css';

type StatusTrilha = 'nao_iniciado' | 'em_andamento' | 'em_revisao' | 'devolvido' | 'concluido';

const statusLabel: Record<StatusTrilha, string> = {
  nao_iniciado: 'Não iniciado',
  em_andamento: 'Em andamento',
  em_revisao: 'Em revisão',
  devolvido: 'Devolvido',
  concluido: 'Concluído',
};

const normalizeDate = (value?: string | null) => {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
};

export function MinhaTrilhaPage() {
  const navigate = useNavigate();
  const client = useApiClient();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;
  const continuar = useContinuar();

  const { data: tarefas, isLoading: tarefasLoading } = useTarefas({ tipo: 'PERGUNTAS' });
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { data: revisoes, isLoading: revisoesLoading } = useRevisoes({ alvoTipo: 'resposta', pageSize: 300 });

  const perguntasQuery = useQuery({
    queryKey: ['perguntas', 'todas', tarefas?.map((t) => t.id)],
    enabled: Boolean(tarefas?.length),
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

  const progressoTrilhas = useMemo(() => {
    return (tarefas ?? []).map((tarefa) => {
      const perguntas = (perguntaMap.get(tarefa.id) ?? []).filter((pergunta) => {
        if (!selectedGtId) return true;
        if (!pergunta.gts || pergunta.gts.length === 0) return true;
        return pergunta.gts.includes(selectedGtId);
      });
      const respostasDaTrilha = (respostas ?? []).filter((resp) => resp.tarefa_id === tarefa.id);
      const respondidas = respostasDaTrilha.filter((resp) => resp.conteudo_html?.trim()).length;
      const total = perguntas.length;
      let status: StatusTrilha = 'nao_iniciado';
      const devolvidos = respostasDaTrilha.some((resp) => revisoesMap.get(resp.id) === 'reprovado');
      const emRevisao = respostasDaTrilha.some((resp) => revisoesMap.get(resp.id) === 'em_revisao');
      const aprovados = respostasDaTrilha.filter((resp) => revisoesMap.get(resp.id) === 'aprovado').length;
      if (devolvidos) status = 'devolvido';
      else if (emRevisao) status = 'em_revisao';
      else if (total > 0 && aprovados === total) status = 'concluido';
      else if (respondidas > 0) status = 'em_andamento';
      return {
        tarefa,
        total,
        respondidas,
        status,
        percentual: total ? Math.round((respondidas / total) * 100) : 0,
      };
    });
  }, [tarefas, perguntaMap, respostas, revisoesMap, selectedGtId]);

  const ultimaResposta = useMemo<Resposta | null>(() => {
    if (!respostas?.length) return null;
    return respostas.slice().sort((a, b) => normalizeDate(b.updated_at) - normalizeDate(a.updated_at))[0] ?? null;
  }, [respostas]);

  const continuarLink = ultimaResposta?.tarefa_id
    ? `/minha-trilha/${ultimaResposta.tarefa_id}?gt=${ultimaResposta.gt}`
    : null;

  const carregando = gtsLoading || tarefasLoading || respostasLoading || revisoesLoading || perguntasQuery.isLoading;

  if (carregando) {
    return <FullPageLoader message="Carregando suas trilhas..." />;
  }

  return (
    <div className="minha-trilha">
      <PageHeader
        title="Minha Trilha"
        description="Veja o andamento das trilhas do seu GT e continue de onde parou."
        actions={continuarLink ? (
          <Link to={continuarLink}>
            <Button variant="primary">Continuar de onde parei</Button>
          </Link>
        ) : (
          <Button
            variant="primary"
            onClick={async () => {
              const data = await continuar.mutateAsync();
              if (data?.url) {
                navigate(data.url);
              }
            }}
            disabled={continuar.isPending}
          >
            {continuar.isPending ? 'Carregando...' : 'Continuar'}
          </Button>
        )}
      />

      <div className="minha-trilha__filters">
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
            <option value="">Selecione um GT</option>
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="minha-trilha__grid">
        {progressoTrilhas.map((item) => (
          <Card key={item.tarefa.id}>
            <div className="minha-trilha__card">
              <div>
                <h2>{item.tarefa.nome || `Trilha #${item.tarefa.id}`}</h2>
                <p>{item.tarefa.etapa ? `Etapa: ${item.tarefa.etapa}` : 'Etapa não definida'}</p>
              </div>
              <span className={`minha-trilha__status status-${item.status}`}>{statusLabel[item.status]}</span>
            </div>
            <div className="minha-trilha__progress">
              <div className="minha-trilha__progress-bar" style={{ width: `${item.percentual}%` }} />
            </div>
            <div className="minha-trilha__meta">
              <span>{item.respondidas}/{item.total} blocos respondidos</span>
              <span>{item.percentual}% concluído</span>
            </div>
            <Link to={`/minha-trilha/${item.tarefa.id}?gt=${selectedGtId ?? ''}`}>
              <Button size="sm" variant="secondary">Abrir trilha</Button>
            </Link>
          </Card>
        ))}
        {progressoTrilhas.length === 0 && (
          <p className="minha-trilha__empty">Nenhuma trilha disponível para este GT.</p>
        )}
      </div>
    </div>
  );
}
