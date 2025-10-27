import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useTarefa } from '@/hooks/useTarefas';
import { usePerguntas } from '@/hooks/usePerguntas';
import { useAvailableGts, type GtOption } from '@/hooks/useAvailableGts';
import { useRespostas, useUpsertResposta } from '@/hooks/useRespostas';
import { usePresence } from '@/hooks/usePresence';
import { useAuth } from '@/context/AuthContext';
import type { Pergunta } from '@/api/types';

import './TaskDetailPage.css';

type FeedbackEntry = {
  type: 'success' | 'error' | 'info';
  message: string;
};

export function TaskDetailPage() {
  const { tarefaId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const gtParam = searchParams.get('gt');
  const selectedGtId = gtParam ? Number(gtParam) : null;

  const { user } = useAuth();

  const [gtInput, setGtInput] = useState('');
  const [gtSelectionError, setGtSelectionError] = useState<string | null>(null);
  const [savingQuestion, setSavingQuestion] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<Record<number, FeedbackEntry>>({});

  const { data: tarefa, isLoading: tarefaLoading, isError: tarefaError, error: tarefaErrorObj } =
    useTarefa(tarefaId);
  const {
    data: perguntas,
    isLoading: perguntasLoading,
    isError: perguntasError,
    error: perguntasErrorObj,
  } = usePerguntas(tarefaId);
  const { data: respostas, isFetching: respostasFetching } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { gtOptions } = useAvailableGts();
  const upsertResposta = useUpsertResposta(selectedGtId);

  const presence = usePresence({
    docType: 'tarefa',
    objectId: selectedGtId ? `${tarefaId}-${selectedGtId}` : undefined,
    enabled: Boolean(selectedGtId),
  });

  const otherParticipants = useMemo(() => {
    if (!user?.id) {
      return presence.participants;
    }
    return presence.participants.filter((participantId) => participantId !== user.id);
  }, [presence.participants, user?.id]);

  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [lastUpdated, setLastUpdated] = useState<Record<number, string>>({});

  useEffect(() => {
    if (!gtParam) {
      setGtInput('');
      setGtSelectionError(null);
      return;
    }
    const matched = gtOptions.find((option) => String(option.id) === gtParam);
    if (matched) {
      setGtInput(matched.displayName);
      setGtSelectionError(null);
    }
  }, [gtOptions, gtParam]);

  useEffect(() => {
    if (!perguntas) {
      return;
    }
    setDrafts((prev) => {
      const next = { ...prev } as Record<number, string>;
      perguntas.forEach((pergunta) => {
        const resposta = respostas?.find((item) => item.pergunta === pergunta.id);
        const conteudoServer = resposta?.conteudo_html ?? '';
        if (!(pergunta.id in prev) || prev[pergunta.id] === conteudoServer) {
          next[pergunta.id] = conteudoServer;
        }
      });
      return next;
    });
    setLastUpdated((prev) => {
      const next = { ...prev } as Record<number, string>;
      perguntas.forEach((pergunta) => {
        const resposta = respostas?.find((item) => item.pergunta === pergunta.id);
        if (resposta?.updated_at) {
          next[pergunta.id] = resposta.updated_at;
        }
      });
      return next;
    });
  }, [perguntas, respostas]);

  useEffect(() => {
    if (!gtParam && gtOptions.length > 0) {
      const first = gtOptions[0];
      setGtInput(first.displayName);
      setSearchParams({ gt: String(first.id) }, { replace: true });
    }
  }, [gtOptions, gtParam, setSearchParams]);

  const sortedPerguntas = useMemo(() => {
    return (perguntas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
  }, [perguntas]);

  const buildErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return fallback;
  };

  const handleSubmitGt = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = gtInput.trim();
    if (trimmed.length === 0) {
      setSearchParams({}, { replace: true });
      setGtSelectionError(null);
      return;
    }
    const normalized = trimmed.toLowerCase();
    let selected = gtOptions.find((option) => option.displayName.toLowerCase() === normalized);
    if (!selected) {
      const byName = gtOptions.filter((option) => option.nome.trim().toLowerCase() === normalized);
      if (byName.length === 1) {
        selected = byName[0];
      }
    }
    if (!selected) {
      setGtSelectionError('GT não encontrado. Selecione um nome válido da lista.');
      return;
    }
    setGtSelectionError(null);
    setSearchParams({ gt: String(selected.id) }, { replace: true });
  };

  const handleSelectGt = (gt: GtOption) => {
    setGtSelectionError(null);
    setGtInput(gt.displayName);
    setSearchParams({ gt: String(gt.id) }, { replace: true });
  };

  const handleChangeDraft = (perguntaId: number, value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [perguntaId]: value,
    }));
  };

  const handleResetDraft = (pergunta: Pergunta) => {
    const resposta = respostas?.find((item) => item.pergunta === pergunta.id);
    setDrafts((prev) => ({
      ...prev,
      [pergunta.id]: resposta?.conteudo_html ?? '',
    }));
    setFeedback((prev) => ({
      ...prev,
      [pergunta.id]: {
        type: 'info',
        message: 'Alterações descartadas.',
      },
    }));
  };

  const handleSaveResposta = async (pergunta: Pergunta) => {
    const conteudo = drafts[pergunta.id] ?? '';
    const respostaAtual = respostas?.find((item) => item.pergunta === pergunta.id);
    setSavingQuestion(pergunta.id);
    setFeedback((prev) => {
      const next = { ...prev };
      delete next[pergunta.id];
      return next;
    });
    try {
      await upsertResposta.mutateAsync({
        respostaId: respostaAtual?.id,
        perguntaId: pergunta.id,
        conteudoHtml: conteudo,
        etag: respostaAtual?.etag,
      });
      setFeedback((prev) => ({
        ...prev,
        [pergunta.id]: {
          type: 'success',
          message: 'Resposta salva com sucesso.',
        },
      }));
    } catch (err) {
      const message = buildErrorMessage(err, 'Não foi possível salvar a resposta.');
      setFeedback((prev) => ({
        ...prev,
        [pergunta.id]: {
          type: 'error',
          message,
        },
      }));
    } finally {
      setSavingQuestion(null);
    }
  };

  if (tarefaLoading || perguntasLoading) {
    return <FullPageLoader message="Carregando tarefa..." />;
  }

  if (tarefaError || perguntasError) {
    const message = buildErrorMessage(
      tarefaError ? tarefaErrorObj : perguntasErrorObj,
      'Erro ao carregar detalhes da tarefa.',
    );
    return (
      <div className="task-detail__error">
        <h2>Algo deu errado</h2>
        <p>{message}</p>
        <Link to="/tarefas">Voltar à lista</Link>
      </div>
    );
  }

  if (!tarefa) {
    return null;
  }

  const etapaLabel = tarefa.etapa ? `Etapa ${tarefa.etapa}` : 'Etapa não informada';

  const renderPergunta = (pergunta: Pergunta) => {
    const respostaAtual = respostas?.find((item) => item.pergunta === pergunta.id);
    const draft = drafts[pergunta.id] ?? '';
    const salvo = respostaAtual?.conteudo_html ?? '';
    const alterado = draft !== salvo;
    const feedbackEntry = feedback[pergunta.id];
    const atualizacao = lastUpdated[pergunta.id];
    const isSaving = savingQuestion === pergunta.id || upsertResposta.isPending;
    const cardClassName = alterado ? 'pergunta-card pergunta-card--dirty' : 'pergunta-card';

    const handleCopy = async () => {
      if (!draft) {
        return;
      }
      try {
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(draft);
          setFeedback((prev) => ({
            ...prev,
            [pergunta.id]: {
              type: 'info',
              message: 'Conteúdo copiado para a área de transferência.',
            },
          }));
        } else {
          throw new Error('clipboard-api-not-supported');
        }
      } catch (error) {
        setFeedback((prev) => ({
          ...prev,
          [pergunta.id]: {
            type: 'error',
            message: 'Não foi possível copiar automaticamente. Utilize Ctrl+C.',
          },
        }));
      }
    };

    return (
      <article key={pergunta.id} className={cardClassName}>
        <header className="pergunta-card__header">
          <div>
            <h2>
              Pergunta {pergunta.ordem}
              {pergunta.obrigatoria ? <span className="pergunta-card__badge">Obrigatória</span> : null}
              {pergunta.permite_upload ? (
                <span className="pergunta-card__badge pergunta-card__badge--upload">
                  Permite upload
                </span>
              ) : null}
            </h2>
            <div
              className="pergunta-card__texto"
              dangerouslySetInnerHTML={{ __html: pergunta.texto }}
            />
          </div>
          {atualizacao && (
            <span className="pergunta-card__meta">
              Última atualização: {new Date(atualizacao).toLocaleString('pt-BR')}
            </span>
          )}
        </header>

        <div className="pergunta-card__editor">
          <textarea
            value={draft}
            onChange={(event) => handleChangeDraft(pergunta.id, event.target.value)}
            rows={8}
            placeholder="Digite o conteúdo em texto simples..."
            disabled={!selectedGtId}
          />

          <div className="pergunta-card__actions">
            <div className="pergunta-card__actions-left">
              <button
                type="button"
                onClick={() => handleSaveResposta(pergunta)}
                disabled={!selectedGtId || isSaving || !alterado}
              >
                {isSaving ? 'Salvando...' : 'Salvar'}
              </button>
              <button
                type="button"
                onClick={() => handleResetDraft(pergunta)}
                disabled={!alterado}
                className="secondary"
              >
                Descartar alterações
              </button>
            </div>
            <button
              type="button"
              className="ghost"
              onClick={handleCopy}
              disabled={!draft}
            >
              Copiar conteúdo
            </button>
          </div>

          {feedbackEntry && (
            <p className={`pergunta-card__feedback pergunta-card__feedback--${feedbackEntry.type}`}>
              {feedbackEntry.message}
            </p>
          )}
        </div>

      </article>
    );
  };

  return (
    <div className="task-detail">
      <div className="task-detail__breadcrumb">
        <Link to="/tarefas">← Voltar</Link>
        <span>/</span>
        <span>Tarefa #{tarefa.ordem}</span>
      </div>

      <header className="task-detail__header">
        <div>
          <h1>{tarefa.tipo === 'OFICINA' ? 'Oficina' : 'Questionário'} #{tarefa.ordem}</h1>
          <p>{etapaLabel}</p>
        </div>
        <TaskStatusBadge status={tarefa.status} />
      </header>

      <PageInstructions
        title="Como trabalhar nesta tarefa"
        description="Selecione o GT e registre as respostas mantendo versões atualizadas."
        items={[
          {
            title: 'Escolha um GT válido',
            description: 'Use o campo ou atalhos para carregar as respostas do grupo antes de editar.',
          },
          {
            title: 'Edite e revise cada pergunta',
            description: 'Atualize o texto, salve para persistir no servidor e use a visualização para conferir o HTML.',
          },
          {
            title: 'Acompanhe feedbacks',
            description: 'Mensagens de sucesso ou erro aparecem abaixo do editor para cada pergunta.',
          },
        ]}
      />

      {selectedGtId && (
        <div className="task-detail__presence">
          {otherParticipants.length > 0 ? (
            <span>
              {otherParticipants.length} participante(s) conectados além de você.
            </span>
          ) : (
            <span>Você é a única pessoa conectada neste GT agora.</span>
          )}
        </div>
      )}

      <section className="task-detail__selector">
        <div>
          <h2>Selecione o GT</h2>
          <p>Escolha o grupo de trabalho para visualizar e editar as respostas vinculadas.</p>
        </div>

        <form className="gt-selector" onSubmit={handleSubmitGt}>
          <label>
            <span>Nome do GT</span>
            <input
              type="text"
              value={gtInput}
              list="gt-selector-options"
              onChange={(event) => {
                setGtSelectionError(null);
                setGtInput(event.target.value);
              }}
              placeholder="Ex.: GT Norte"
            />
          </label>
          <button type="submit">Aplicar</button>
          <datalist id="gt-selector-options">
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.displayName} label={gt.nome} />
            ))}
          </datalist>
          {gtSelectionError && <p className="gt-selector__error">{gtSelectionError}</p>}
        </form>

        {gtOptions.length > 0 && (
          <div className="gt-selector__suggestions">
            <span>GTs recentes: </span>
            <div>
              {gtOptions.slice(0, 6).map((gt) => (
                <button
                  key={gt.id}
                  type="button"
                  onClick={() => handleSelectGt(gt)}
                  className={selectedGtId === gt.id ? 'active' : ''}
                >
                  {gt.displayName}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>

      {!selectedGtId && (
        <div className="task-detail__empty">
          <h3>Nenhum GT selecionado</h3>
          <p>Informe um GT para começar a editar as respostas desta tarefa.</p>
        </div>
      )}

      {selectedGtId && respostasFetching && (
        <div className="task-detail__loading">Atualizando respostas...</div>
      )}

      {selectedGtId && sortedPerguntas.map((pergunta) => renderPergunta(pergunta))}
    </div>
  );
}
