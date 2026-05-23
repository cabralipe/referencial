import { useMemo } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useTarefa } from '@/hooks/useTarefas';
import { usePerguntas } from '@/hooks/usePerguntas';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import type { Pergunta, Resposta } from '@/api/types';

import './TrilhaDetailPage.css';

type BlocoStatus = 'nao_iniciado' | 'em_andamento' | 'em_revisao' | 'devolvido' | 'concluido';

const statusLabel: Record<BlocoStatus, string> = {
  nao_iniciado: 'Não iniciado',
  em_andamento: 'Em andamento',
  em_revisao: 'Em revisão',
  devolvido: 'Devolvido',
  concluido: 'Concluído',
};

export function TrilhaDetailPage() {
  const { trilhaId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const client = useApiClient();

  const { gtOptions } = useAvailableGts();
  const gtParam = searchParams.get('gt');
  const selectedGtId = gtParam ? Number(gtParam) : gtOptions[0]?.id ?? null;

  const { data: tarefa, isLoading: tarefaLoading } = useTarefa(trilhaId);
  const { data: perguntas, isLoading: perguntasLoading } = usePerguntas(trilhaId, selectedGtId ?? undefined);
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { data: revisoes, isLoading: revisoesLoading } = useRevisoes({ alvoTipo: 'resposta', pageSize: 300 });

  const createEmptyResposta = useMutation({
    mutationFn: async (pergunta: Pergunta) => {
      if (!selectedGtId) {
        throw new Error('Selecione um GT.');
      }
      const response = await client.post<Resposta>('/respostas', {
        body: {
          gt: selectedGtId,
          pergunta: pergunta.id,
          conteudo_html: '',
        },
      });
      return response.data;
    },
    onSuccess: (data) => {
      navigate(`/texto/${data.id}?gt=${data.gt}`);
    },
  });

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

  const blocos = useMemo(() => {
    const perguntasFiltradas = (perguntas ?? []).filter((pergunta) => {
      if (!selectedGtId) return true;
      return pergunta.gts.includes(selectedGtId);
    });

    return perguntasFiltradas.map((pergunta) => {
      const resposta = (respostas ?? []).find((resp) => resp.pergunta === pergunta.id);
      const revisaoStatus = resposta ? revisoesMap.get(resposta.id) : undefined;
      let status: BlocoStatus = 'nao_iniciado';
      if (revisaoStatus === 'reprovado') status = 'devolvido';
      else if (revisaoStatus === 'em_revisao') status = 'em_revisao';
      else if (revisaoStatus === 'aprovado') status = 'concluido';
      else if (resposta?.conteudo_html?.trim()) status = 'em_andamento';

      return {
        pergunta,
        resposta,
        status,
      };
    });
  }, [perguntas, respostas, revisoesMap, selectedGtId]);

  const proximoBloco = blocos.find((bloco) => bloco.status !== 'concluido') ?? blocos[0];

  const carregando = tarefaLoading || perguntasLoading || respostasLoading || revisoesLoading;

  if (carregando) {
    return <FullPageLoader message="Carregando trilha..." />;
  }

  return (
    <div className="trilha-detail">
      <PageHeader
        title={tarefa?.nome ?? `Trilha #${trilhaId}`}
        description="Siga os blocos em ordem e acompanhe o que já foi revisado."
        actions={(
          <label className="trilha-detail__gt">
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
        )}
      />

      {proximoBloco && (
        <Card>
          <div className="trilha-detail__next">
            <div>
              <strong>Passo atual</strong>
              <p>{proximoBloco.pergunta.texto}</p>
            </div>
            {proximoBloco.resposta ? (
              <Link to={`/texto/${proximoBloco.resposta.id}?gt=${selectedGtId ?? ''}`}>
                <Button variant="primary">Continuar</Button>
              </Link>
            ) : (
              <Button
                variant="primary"
                onClick={() => createEmptyResposta.mutate(proximoBloco.pergunta)}
                disabled={createEmptyResposta.isPending}
              >
                {createEmptyResposta.isPending ? 'Criando...' : 'Iniciar texto'}
              </Button>
            )}
          </div>
        </Card>
      )}

      <div className="trilha-detail__lista">
        {blocos.map((bloco) => (
          <Card key={bloco.pergunta.id}>
            <div className="trilha-detail__card">
              <header>
                <span className={`trilha-detail__status status-${bloco.status}`}>{statusLabel[bloco.status]}</span>
              </header>
              <div
                className="trilha-detail__texto"
                dangerouslySetInnerHTML={{ __html: bloco.pergunta.texto }}
              />

              <div className="trilha-detail__steps">
                {([
                  { label: 'Resposta registrada', done: Boolean(bloco.resposta?.conteudo_html?.trim()) },
                  { label: 'Em revisão', done: ['em_revisao', 'concluido'].includes(bloco.status) },
                  { label: 'Validado pelo redator', done: bloco.status === 'concluido' },
                ] as const).map(({ label, done }) => (
                  <div key={label} className={`trilha-detail__step${done ? ' is-done' : ''}`}>
                    <span className="trilha-detail__step-icon" aria-hidden="true">{done ? '✓' : '○'}</span>
                    <span>{label}</span>
                  </div>
                ))}
              </div>

              <div className="trilha-detail__actions">
                {bloco.resposta ? (
                  <Link to={`/texto/${bloco.resposta.id}?gt=${selectedGtId ?? ''}`}>
                    <Button size="sm" variant="secondary">Abrir texto</Button>
                  </Link>
                ) : (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => createEmptyResposta.mutate(bloco.pergunta)}
                    disabled={createEmptyResposta.isPending}
                  >
                    Criar texto
                  </Button>
                )}
              </div>
            </div>
          </Card>
        ))}
        {blocos.length === 0 && (
          <Card>
            <p>Nenhuma missão disponível para este GT.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
