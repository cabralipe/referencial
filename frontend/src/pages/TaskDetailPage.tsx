import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { ApiError, useApiClient } from '@/api/client';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useTarefa } from '@/hooks/useTarefas';
import { usePerguntas } from '@/hooks/usePerguntas';
import { useAvailableGts, type GtOption } from '@/hooks/useAvailableGts';
import { useRespostas, useUpsertResposta } from '@/hooks/useRespostas';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useCreateRevisao, useRevisoes } from '@/hooks/useRevisoes';
import { usePresence } from '@/hooks/usePresence';
import { useAuth } from '@/context/AuthContext';
import type { Pergunta } from '@/api/types';

import './TaskDetailPage.css';

type FeedbackEntry = {
  type: 'success' | 'error' | 'info';
  message: string;
};

type Snippet = {
  key: string;
  label: string;
  template: string;
};

const RESPOSTA_SNIPPETS: Snippet[] = [
  {
    key: 'resumo',
    label: 'Resumo estruturado',
    template:
      '<p><strong>Resumo:</strong> <em>contextualize em duas frases.</em></p><ul><li><strong>Pontos-chave:</strong> ...</li><li><strong>Evidências:</strong> ...</li></ul><p><strong>Próximos passos:</strong> ...</p>',
  },
  {
    key: 'checklist',
    label: 'Checklist de entrega',
    template:
      '<ul><li><strong>Ação</strong>: ...</li><li><strong>Responsável</strong>: ...</li><li><strong>Prazo</strong>: ...</li><li><strong>Status</strong>: concluído/em andamento</li></ul>',
  },
  {
    key: 'narrativa',
    label: 'Narrativa com impacto',
    template:
      '<p><strong>Cenário</strong>: ...</p><p><strong>Decisão</strong>: ...</p><p><strong>Impacto esperado</strong>: ...</p><p><strong>Métricas de sucesso</strong>: ...</p>',
  },
  {
    key: 'bullets',
    label: 'Lista em tópicos',
    template: '<ul><li><strong>Contexto:</strong> ...</li><li><strong>O que foi feito:</strong> ...</li><li><strong>Resultados:</strong> ...</li></ul>',
  },
];

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const decodeHtmlEntities = (value: string) => {
  if (!value) return '';
  const parser = new DOMParser();
  const doc = parser.parseFromString(value, 'text/html');
  return doc.documentElement.textContent ?? value;
};

const ensureHtml = (value: string) => {
  const raw = value ?? '';
  const text = raw.trim();
  if (!text) return '';
  const hasHtmlTag = /<\/?[a-z][\s\S]*>/i.test(text);
  if (hasHtmlTag) {
    return raw;
  }
  const decoded = decodeHtmlEntities(text);
  if (decoded !== text && /<\/?[a-z][\s\S]*>/i.test(decoded)) {
    return decoded;
  }
  const paragraphs = text
    .split(/\n{2,}/)
    .map((block) => `<p>${escapeHtml(block).replace(/\n/g, '<br />')}</p>`)
    .join('');
  return paragraphs || `<p>${escapeHtml(text)}</p>`;
};

const stripHtml = (value: string) => {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
};

const buildTextStats = (value: string) => {
  const trimmed = stripHtml(value);
  const words = trimmed ? trimmed.split(/\s+/).length : 0;
  return { words, chars: trimmed.length };
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;
const isNewTask = (createdAt?: string | null) => {
  if (!createdAt) return false;
  const created = new Date(createdAt);
  if (Number.isNaN(created.getTime())) return false;
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - created.getTime()) / MS_PER_DAY);
  return diffDays <= 7;
};

export function TaskDetailPage() {
  const { tarefaId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const gtParam = searchParams.get('gt');
  const selectedGtId = gtParam ? Number(gtParam) : null;

  const { user } = useAuth();

  const [savingQuestion, setSavingQuestion] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<Record<number, FeedbackEntry>>({});
  const [parecerDrafts, setParecerDrafts] = useState<Record<number, string>>({});
  const [parecerFeedback, setParecerFeedback] = useState<Record<number, FeedbackEntry>>({});

  const { data: tarefa, isLoading: tarefaLoading, isError: tarefaError, error: tarefaErrorObj } =
    useTarefa(tarefaId);
  const {
    data: perguntas,
    isLoading: perguntasLoading,
    isError: perguntasError,
    error: perguntasErrorObj,
    refetch: refetchPerguntas,
  } = usePerguntas(tarefaId, selectedGtId ?? undefined);
  const {
    data: respostas,
    isFetching: respostasFetching,
    isFetched: respostasFetched,
  } = useRespostas({ gtId: selectedGtId ?? undefined });
  const { data: revisoes } = useRevisoes({ alvoTipo: 'resposta', pageSize: 500 });
  const createRevisao = useCreateRevisao();
  const { gtOptions } = useAvailableGts();
  const upsertResposta = useUpsertResposta(selectedGtId);
  const client = useApiClient();
  const queryClient = useQueryClient();
  const aiAssist = useAiAssist();
  const [aiLoadingQuestion, setAiLoadingQuestion] = useState<number | null>(null);

  const canManage = user?.role === 'articulador' || user?.role === 'admin_cliente' || user?.role === 'super_admin';
  const canReview = canManage;
  const isGtMember = user?.role === 'membro_gt';
  const [novaOrdem, setNovaOrdem] = useState('');
  const [novaTexto, setNovaTexto] = useState('');
  const [novaObrigatoria, setNovaObrigatoria] = useState(true);
  const [novaUpload, setNovaUpload] = useState(false);
  const [novaGts, setNovaGts] = useState<number[]>([]);
  const [novaFeedback, setNovaFeedback] = useState('');

  const createPergunta = useMutation({
    mutationFn: async () => {
      const ordemNumber = Number(novaOrdem);
      if (!tarefaId || !Number.isFinite(ordemNumber) || ordemNumber <= 0) {
        throw new Error('ordem-invalida');
      }
      const response = await client.post<Pergunta>('/perguntas', {
        body: {
          tarefa: Number(tarefaId),
          ordem: ordemNumber,
          texto: novaTexto,
          permite_upload: novaUpload,
          obrigatoria: novaObrigatoria,
          gts: novaGts.length > 0 ? novaGts : undefined,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      setNovaOrdem('');
      setNovaTexto('');
      setNovaObrigatoria(true);
      setNovaUpload(false);
      setNovaGts([]);
      setNovaFeedback('Missao criada com sucesso.');
      queryClient.invalidateQueries({ queryKey: ['tarefas', tarefaId, 'perguntas'] });
      refetchPerguntas();
    },
    onError: () => {
      setNovaFeedback('Nao foi possivel criar a missao.');
    },
  });

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
    if (!perguntas || !respostasFetched) {
      return;
    }
    setDrafts((prev) => {
      const next = { ...prev } as Record<number, string>;
      perguntas.forEach((pergunta) => {
        const resposta = respostas?.find((item) => item.pergunta === pergunta.id);
        const conteudoServer = ensureHtml(resposta?.conteudo_html ?? '');
        if (!(pergunta.id in prev) || ensureHtml(prev[pergunta.id] ?? '') === conteudoServer) {
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
  }, [perguntas, respostas, respostasFetched]);

  useEffect(() => {
    if (gtOptions.length === 0) {
      if (gtParam) {
        setSearchParams({}, { replace: true });
      }
      return;
    }

    if (!gtParam) {
      setSearchParams({ gt: String(gtOptions[0].id) }, { replace: true });
      return;
    }

    const exists = gtOptions.some((option) => String(option.id) === gtParam);
    if (!exists) {
      setSearchParams({ gt: String(gtOptions[0].id) }, { replace: true });
    }
  }, [gtOptions, gtParam, setSearchParams]);

  const sortedPerguntas = useMemo(() => {
    return (perguntas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
  }, [perguntas]);

  const filteredPerguntas = useMemo(() => {
    if (!selectedGtId || !sortedPerguntas) {
      return sortedPerguntas;
    }
    
    return sortedPerguntas.filter((pergunta) => pergunta.gts.includes(selectedGtId));
  }, [sortedPerguntas, selectedGtId]);

  const buildErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return fallback;
  };

  const handleSelectGt = (gt: GtOption) => {
    setSearchParams({ gt: String(gt.id) }, { replace: true });
  };

  const handleChangeDraft = (perguntaId: number, value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [perguntaId]: value,
    }));
  };

  const handleInsertSnippet = (perguntaId: number, template: string) => {
    setDrafts((prev) => {
      const current = prev[perguntaId] ?? '';
      const separator = current.trim() ? '\n\n' : '';
      return {
        ...prev,
        [perguntaId]: `${current}${separator}${template}`,
      };
    });
    setFeedback((prev) => ({
      ...prev,
      [perguntaId]: {
        type: 'info',
        message: 'Modelo inserido. Ajuste o texto antes de salvar.',
      },
    }));
  };

  const handleResetDraft = (pergunta: Pergunta) => {
    const resposta = respostas?.find((item) => item.pergunta === pergunta.id);
    setDrafts((prev) => ({
      ...prev,
      [pergunta.id]: ensureHtml(resposta?.conteudo_html ?? ''),
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
        conteudoHtml: ensureHtml(conteudo),
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
    return <FullPageLoader message="Carregando trilha..." />;
  }

  if (tarefaError || perguntasError) {
    const message = buildErrorMessage(
      tarefaError ? tarefaErrorObj : perguntasErrorObj,
      'Erro ao carregar detalhes da trilha.',
    );
    return (
      <div className="task-detail__error">
        <h2>Algo deu errado</h2>
        <p>{message}</p>
        <Link to="/tarefas">Voltar às trilhas</Link>
      </div>
    );
  }

  if (!tarefa) {
    return null;
  }

  const etapaLabel = tarefa.etapa ? `Etapa ${tarefa.etapa}` : 'Etapa não informada';
  const tipoLabel = tarefa.tipo === 'OFICINA' ? 'Oficina' : 'Questionário';

  const renderPergunta = (pergunta: Pergunta) => {
    const respostaAtual = respostas?.find((item) => item.pergunta === pergunta.id);
    const draft = drafts[pergunta.id] ?? '';
    const salvo = ensureHtml(respostaAtual?.conteudo_html ?? '');
    const pendente = Boolean(isGtMember && selectedGtId && (!respostaAtual || !stripHtml(salvo)));
    const alterado = draft !== salvo;
    const feedbackEntry = feedback[pergunta.id];
    const atualizacao = lastUpdated[pergunta.id];
    const isSaving = savingQuestion === pergunta.id || upsertResposta.isPending;
    const cardClassName = alterado ? 'pergunta-card pergunta-card--dirty' : 'pergunta-card';
    const stats = buildTextStats(draft);
    const revisoesDaResposta = revisoes?.filter((rev) => rev.alvo_id === respostaAtual?.id) ?? [];
    const respostaId = respostaAtual?.id;
    const lastParecer =
      revisoesDaResposta
        .filter((rev) => rev.parecer_html)
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0]?.parecer_html ?? '';
    const parecerDraft = respostaId ? (parecerDrafts[respostaId] ?? lastParecer) : '';
    const parecerFeedbackEntry = respostaId ? parecerFeedback[respostaId] : undefined;

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

    const handleAiDraft = async () => {
      if (!pergunta.texto) return;
      setAiLoadingQuestion(pergunta.id);
      try {
        const response = await aiAssist.mutateAsync({
          mode: 'draft',
          text: stripHtml(pergunta.texto),
          context: tarefa.nome,
        });
        setDrafts((prev) => ({ ...prev, [pergunta.id]: response.output || '' }));
      } catch (err) {
        setFeedback((prev) => ({
          ...prev,
          [pergunta.id]: {
            type: 'error',
            message: 'Nao foi possivel gerar rascunho com IA.',
          },
        }));
      } finally {
        setAiLoadingQuestion(null);
      }
    };

    const handleAiGrammar = async () => {
      const current = drafts[pergunta.id] ?? '';
      if (!current.trim()) return;
      setAiLoadingQuestion(pergunta.id);
      try {
        const response = await aiAssist.mutateAsync({
          mode: 'grammar',
          text: current,
        });
        setDrafts((prev) => ({ ...prev, [pergunta.id]: response.output || current }));
      } catch (err) {
        setFeedback((prev) => ({
          ...prev,
          [pergunta.id]: {
            type: 'error',
            message: 'Nao foi possivel revisar a gramatica.',
          },
        }));
      } finally {
        setAiLoadingQuestion(null);
      }
    };

    return (
      <article key={pergunta.id} className={cardClassName}>
        <header className="pergunta-card__header">
          <div>
            <h2>
              Missão {pergunta.ordem}
              {pergunta.obrigatoria ? <span className="pergunta-card__badge">Obrigatória</span> : null}
              {pergunta.permite_upload ? (
                <span className="pergunta-card__badge pergunta-card__badge--upload">
                  Permite upload
                </span>
              ) : null}
              {pendente ? (
                <span className="pergunta-card__badge pergunta-card__badge--pendente">
                  Pendente
                </span>
              ) : null}
            </h2>
            <div
              className="pergunta-card__texto"
              dangerouslySetInnerHTML={{ __html: ensureHtml(pergunta.texto) }}
            />
          </div>
          {atualizacao && (
            <span className="pergunta-card__meta">
              Última atualização: {new Date(atualizacao).toLocaleString('pt-BR')}
            </span>
          )}
        </header>

        <div className="pergunta-card__editor">
          <RichTextEditor
            value={draft}
            onChange={(value) => handleChangeDraft(pergunta.id, value)}
            placeholder="Digite o conteúdo aqui."
            disabled={!selectedGtId}
          />

          <div className="pergunta-card__toolbar">
            <div className="pergunta-card__chips">
              {RESPOSTA_SNIPPETS.map((snippet) => (
                <button
                  key={snippet.key}
                  type="button"
                  onClick={() => handleInsertSnippet(pergunta.id, snippet.template)}
                  disabled={!selectedGtId || isSaving}
                >
                  {snippet.label}
                </button>
              ))}
              <button
                type="button"
                onClick={handleAiDraft}
                disabled={!selectedGtId || aiLoadingQuestion === pergunta.id}
              >
                {aiLoadingQuestion === pergunta.id ? 'IA em andamento...' : 'IA: rascunho'}
              </button>
              <button
                type="button"
                onClick={handleAiGrammar}
                disabled={!selectedGtId || aiLoadingQuestion === pergunta.id}
              >
                {aiLoadingQuestion === pergunta.id ? 'IA em andamento...' : 'IA: corrigir'}
              </button>
            </div>
            <div className="pergunta-card__stats">
              <span>{stats.words} palavra(s)</span>
              <span>·</span>
              <span>{stats.chars} caractere(s)</span>
            </div>
          </div>

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

          {revisoesDaResposta.length > 0 && (
            <div className="pergunta-card__revisoes">
              <strong>Revisões do articulador:</strong>
              {revisoesDaResposta.map((rev) => (
                <div key={rev.id} className="pergunta-card__revisao">
                  <span className={`pergunta-card__revisao-status status-${rev.status}`}>{rev.status}</span>
                  <div
                    dangerouslySetInnerHTML={{
                      __html: ensureHtml(rev.parecer_html || '<p>Sem parecer.</p>'),
                    }}
                  />
                  <small>Revisão #{rev.id}</small>
                </div>
              ))}
            </div>
          )}

          <details className="pergunta-card__preview">
            <summary>Pré-visualização</summary>
            <div
              dangerouslySetInnerHTML={{
                __html: ensureHtml(draft) || '<p>Sem conteúdo para exibir ainda.</p>',
              }}
            />
          </details>

          {canReview && (
            <div className="pergunta-card__parecer">
              <label>
                <span>Parecer do redator (HTML)</span>
                <RichTextEditor
                  value={parecerDraft}
                  onChange={(value) => {
                    if (!respostaId) {
                      return;
                    }
                    setParecerDrafts((prev) => ({ ...prev, [respostaId]: value }));
                  }}
                  placeholder="Registre aqui o parecer para o cliente."
                  disabled={!respostaId}
                />
              </label>
              <div className="pergunta-card__parecer-actions">
                <button
                  type="button"
                  onClick={async () => {
                    if (!respostaId) {
                      return;
                    }
                    const parecerHtml = ensureHtml(parecerDraft);
                    if (!parecerHtml.trim()) {
                      setParecerFeedback((prev) => ({
                        ...prev,
                        [respostaId]: {
                          type: 'error',
                          message: 'Informe o parecer antes de enviar.',
                        },
                      }));
                      return;
                    }
                    try {
                      await createRevisao.mutateAsync({
                        alvoTipo: 'resposta',
                        alvoId: respostaId,
                        parecerHtml,
                      });
                      setParecerFeedback((prev) => ({
                        ...prev,
                        [respostaId]: {
                          type: 'success',
                          message: 'Parecer enviado e visível para o cliente.',
                        },
                      }));
                      setParecerDrafts((prev) => {
                        const next = { ...prev };
                        delete next[respostaId];
                        return next;
                      });
                    } catch (err) {
                      const message = buildErrorMessage(err, 'Não foi possível enviar o parecer.');
                      setParecerFeedback((prev) => ({
                        ...prev,
                        [respostaId]: {
                          type: 'error',
                          message,
                        },
                      }));
                    }
                  }}
                  disabled={!respostaId || createRevisao.isPending}
                >
                  {createRevisao.isPending ? 'Enviando parecer...' : 'Enviar parecer'}
                </button>
              </div>
              {parecerFeedbackEntry && (
                <p className={`pergunta-card__feedback pergunta-card__feedback--${parecerFeedbackEntry.type}`}>
                  {parecerFeedbackEntry.message}
                </p>
              )}
            </div>
          )}
        </div>

      </article>
    );
  };

  return (
    <div className="task-detail">
      <div className="task-detail__breadcrumb">
        <Link to="/tarefas">← Voltar às trilhas</Link>
        <span>/</span>
        <span>Trilha #{tarefa.ordem}</span>
      </div>

      <header className="task-detail__header">
        <div>
          <div className="task-detail__title">
            <h1>Trilha pedagógica #{tarefa.ordem}</h1>
            {isNewTask(tarefa.created_at) && <span className="task-detail__new-badge">Atividade nova</span>}
          </div>
          <p>{etapaLabel} · {tipoLabel}</p>
        </div>
        <TaskStatusBadge status={tarefa.status} />
      </header>

      <PageInstructions
        title="Como trabalhar nesta trilha"
        description="Selecione o GT e registre as respostas mantendo versões atualizadas."
        items={[
          {
            title: 'Escolha um GT válido',
            description: 'Use o campo ou atalhos para carregar as respostas do grupo antes de editar.',
          },
          {
            title: 'Edite e revise cada missão',
            description: 'Atualize o texto, salve para persistir no servidor e use a visualização para conferir o HTML.',
          },
          {
            title: 'Acompanhe feedbacks',
            description: 'Mensagens de sucesso ou erro aparecem abaixo do editor para cada missão.',
          },
        ]}
      />

      {canManage && (
        <section className="task-detail__create">
          <details>
            <summary>Criar missao</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                setNovaFeedback('');
                if (!novaTexto.trim()) {
                  setNovaFeedback('Informe o texto da missao.');
                  return;
                }
                createPergunta.mutate();
              }}
            >
              <label>
                <span>Ordem</span>
                <input
                  type="number"
                  min={1}
                  value={novaOrdem}
                  onChange={(event) => setNovaOrdem(event.target.value)}
                />
              </label>
              <label className="full">
                <span>Texto da missao</span>
                <RichTextEditor
                  value={novaTexto}
                  onChange={setNovaTexto}
                  placeholder="Escreva o texto da missão."
                />
              </label>
              <label>
                <span>Obrigatoria</span>
                <select
                  value={novaObrigatoria ? 'sim' : 'nao'}
                  onChange={(event) => setNovaObrigatoria(event.target.value === 'sim')}
                >
                  <option value="sim">Sim</option>
                  <option value="nao">Nao</option>
                </select>
              </label>
              <label>
                <span>Permite upload</span>
                <select
                  value={novaUpload ? 'sim' : 'nao'}
                  onChange={(event) => setNovaUpload(event.target.value === 'sim')}
                >
                  <option value="nao">Nao</option>
                  <option value="sim">Sim</option>
                </select>
              </label>
              <label className="full">
                <span>GTs (opcional)</span>
                <select
                  multiple
                  value={novaGts.map(String)}
                  onChange={(event) => {
                    const values = Array.from(event.target.selectedOptions).map((opt) => Number(opt.value));
                    setNovaGts(values);
                  }}
                >
                  {gtOptions.map((gt) => (
                    <option key={gt.id} value={gt.id}>
                      {gt.displayName}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" disabled={createPergunta.isPending}>
                {createPergunta.isPending ? 'Criando...' : 'Criar missao'}
              </button>
              {novaFeedback && <span className="task-detail__feedback">{novaFeedback}</span>}
            </form>
          </details>
        </section>
      )}

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

        <div className="gt-selector">
          <label>
            <span>Nome do GT</span>
            <select
              value={selectedGtId ? String(selectedGtId) : ''}
              onChange={(event) => {
                const value = event.target.value;
                if (!value) {
                  setSearchParams({}, { replace: true });
                  return;
                }
                setSearchParams({ gt: value }, { replace: true });
              }}
              disabled={gtOptions.length === 0}
            >
              <option value="">
                {gtOptions.length === 0 ? 'Nenhum GT disponível' : 'Selecione'}
              </option>
              {gtOptions.map((gt) => (
                <option key={gt.id} value={gt.id}>
                  {gt.displayName}
                </option>
              ))}
            </select>
          </label>
        </div>

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
          <p>Informe um GT para começar a editar as respostas desta trilha.</p>
        </div>
      )}

      {selectedGtId && respostasFetching && (
        <div className="task-detail__loading">Atualizando respostas...</div>
      )}

      {selectedGtId && filteredPerguntas.length === 0 && !respostasFetching && (
        <div className="task-detail__empty">
          <h3>Nenhuma missão disponível</h3>
          <p>Não há missões associadas a este GT para esta trilha.</p>
        </div>
      )}

      {selectedGtId && filteredPerguntas.map((pergunta) => renderPergunta(pergunta))}
    </div>
  );
}
