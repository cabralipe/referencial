import { useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { Card } from '@/components/common/Card';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useTarefas } from '@/hooks/useTarefas';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import { fetchAllPaginated } from '@/utils/pagination';
import { useContinuar } from '@/hooks/useContinuar';
import { useAuth } from '@/context/AuthContext';
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
  const { user } = useAuth();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;
  const continuar = useContinuar();

  const { data: tarefas, isLoading: tarefasLoading } = useTarefas({
    tipo: 'PERGUNTAS',
    gtId: selectedGtId ?? undefined,
  });
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { data: revisoes, isLoading: revisoesLoading } = useRevisoes({ alvoTipo: 'resposta', pageSize: 300 });

  const perguntasQuery = useQuery({
    queryKey: ['perguntas', 'todas', selectedGtId ?? null, tarefas?.map((t) => t.id)],
    enabled: Boolean(tarefas?.length),
    queryFn: async () => {
      return fetchAllPaginated<Pergunta>(client.get, '/perguntas', {
        query: {
          page_size: 500,
          gt_id: selectedGtId ?? undefined,
        },
      });
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
        return pergunta.gts.includes(selectedGtId);
      });
      const respostasDaTarefa = (respostas ?? []).filter((resp) => resp.tarefa_id === tarefa.id);
      // Filtra pelo GT selecionado para evitar dupla contagem quando uma pergunta
      // pertence a múltiplos GTs e o usuário tem respostas em mais de um GT.
      const respostasDaTrilha = selectedGtId
        ? respostasDaTarefa.filter((resp) => resp.gt === selectedGtId)
        : respostasDaTarefa;
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
        percentual: total ? Math.min(100, Math.round((respondidas / total) * 100)) : 0,
      };
    });
  }, [tarefas, perguntaMap, respostas, revisoesMap, selectedGtId]);

  const tarefasLookup = useMemo(() => {
    return new Map((tarefas ?? []).map((tarefa) => [tarefa.id, tarefa]));
  }, [tarefas]);

  const ultimaResposta = useMemo<Resposta | null>(() => {
    if (!respostas?.length) return null;
    return respostas.slice().sort((a, b) => normalizeDate(b.updated_at) - normalizeDate(a.updated_at))[0] ?? null;
  }, [respostas]);

  const continuarLink = ultimaResposta?.tarefa_id
    ? `/minha-trilha/${ultimaResposta.tarefa_id}?gt=${ultimaResposta.gt}`
    : null;
  const tarefaContinuar = ultimaResposta?.tarefa_id ? tarefasLookup.get(ultimaResposta.tarefa_id) : null;

  const carregando = gtsLoading || tarefasLoading || respostasLoading || revisoesLoading || perguntasQuery.isLoading;

  if (carregando) {
    return <FullPageLoader message="Carregando suas trilhas..." />;
  }

  return (
    <div className="minha-trilha">
      <header className="minha-trilha__header">
        <div className="minha-trilha__header-left">
          <div className="minha-trilha__avatar" aria-hidden="true">
            {(user?.nome || 'U')[0]?.toUpperCase()}
            <span className="minha-trilha__online-dot" />
          </div>
          <div>
            <span className="minha-trilha__welcome">Bem-vindo(a) de volta</span>
            <h1>{user?.nome || 'Participante'}</h1>
          </div>
        </div>
      </header>

      <section className="minha-trilha__title">
        <h2>Minha Trilha</h2>
        <p>Acompanhe seu progresso didático.</p>
      </section>

      <section className="minha-trilha__continue">
        <div className="minha-trilha__continue-card">
          <div className="minha-trilha__continue-content">
            <span className="minha-trilha__continue-label">Continuar onde parou</span>
            <h3>{tarefaContinuar?.nome || 'Sua próxima trilha'}</h3>
            <p>
              {tarefaContinuar?.etapa ? `${tarefaContinuar.etapa}` : 'Escolha uma trilha para avançar'}
            </p>
            {continuarLink ? (
              <Link to={continuarLink} className="minha-trilha__primary-button">
                Retomar atividade
              </Link>
            ) : (
              <button
                type="button"
                className="minha-trilha__primary-button"
                onClick={async () => {
                  const data = await continuar.mutateAsync();
                  if (data?.url) {
                    navigate(data.url);
                  }
                }}
                disabled={continuar.isPending}
              >
                {continuar.isPending ? 'Carregando...' : 'Continuar'}
              </button>
            )}
          </div>
        </div>
      </section>

      <section className="minha-trilha__gt-section">
        <div className="minha-trilha__section-header">
          <h3>Seu Grupo de Trabalho</h3>
          <span>Ver todos</span>
        </div>
        <div className="minha-trilha__gt-chips">
          {gtOptions.map((gt) => {
            const isActive = gt.id === selectedGtId;
            return (
              <button
                key={gt.id}
                type="button"
                className={`minha-trilha__chip ${isActive ? 'is-active' : ''}`}
                onClick={() => {
                  setSearchParams({ gt: String(gt.id) });
                }}
              >
                {gt.displayName}
              </button>
            );
          })}
        </div>
      </section>

      <div className="minha-trilha__grid">
        {progressoTrilhas.map((item) => (
          <Card key={item.tarefa.id}>
            <div className="minha-trilha__card">
              <div className="minha-trilha__card-head">
                <div>
                  <span className="minha-trilha__card-stage">
                    {item.tarefa.etapa ? `Etapa ${item.tarefa.etapa}` : 'Etapa'}
                  </span>
                  <h3>{item.tarefa.nome || `Trilha #${item.tarefa.id}`}</h3>
                </div>
                <span className={`minha-trilha__status status-${item.status}`}>
                  {statusLabel[item.status]}
                </span>
              </div>
              <div className="minha-trilha__progress-meta">
                <span>{item.respondidas} de {item.total} blocos concluídos</span>
                <strong>{item.percentual}%</strong>
              </div>
              <div className="minha-trilha__progress">
                <div className="minha-trilha__progress-bar" style={{ width: `${item.percentual}%` }} />
              </div>
              <Link to={`/minha-trilha/${item.tarefa.id}?gt=${selectedGtId ?? ''}`} className="minha-trilha__secondary-button">
                Abrir trilha
              </Link>
            </div>
          </Card>
        ))}
        {progressoTrilhas.length === 0 && (
          <p className="minha-trilha__empty">Nenhuma trilha disponível para este GT.</p>
        )}
      </div>
    </div>
  );
}
