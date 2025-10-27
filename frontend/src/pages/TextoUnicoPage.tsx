import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/api/client';
import type { TextoColaborativo } from '@/api/types';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAvailableGtIds } from '@/hooks/useAvailableGtIds';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';
import {
  useCreateTextoColaborativo,
  useTextosColaborativos,
  useUpdateTextoColaborativo,
} from '@/hooks/useTextosColaborativos';
import { useGenerateTextoUnico, useTextoUnicos } from '@/hooks/useTextoUnico';
import { useTarefas } from '@/hooks/useTarefas';

import './TextoUnicoPage.css';

type FeedbackEntry = {
  type: 'success' | 'error' | 'info';
  message: string;
};

function normalizePayload(payload: Record<string, unknown>): TextoColaborativo | null {
  if (!payload) {
    return null;
  }
  const id = Number(payload.id);
  const gt = Number(payload.gt);
  if (!Number.isFinite(id) || !Number.isFinite(gt)) {
    return null;
  }
  const version = Number(payload.version ?? 1);
  const autorValue = payload.autor == null ? null : Number(payload.autor);
  return {
    id,
    gt,
    titulo: typeof payload.titulo === 'string' ? payload.titulo : '',
    conteudo_html: typeof payload.conteudo_html === 'string' ? payload.conteudo_html : '',
    autor: autorValue != null && Number.isFinite(autorValue) ? autorValue : null,
    version: Number.isFinite(version) ? version : 1,
    created_at:
      typeof payload.created_at === 'string' ? payload.created_at : new Date().toISOString(),
    updated_at:
      typeof payload.updated_at === 'string' ? payload.updated_at : new Date().toISOString(),
    etag: typeof payload.etag === 'string' ? payload.etag : '',
  };
}

export function TextoUnicoPage() {
  const { data: tarefas } = useTarefas();
  const { gtOptions } = useAvailableGtIds();

  const [selectedGt, setSelectedGt] = useState<number | ''>('');
  const [selectedTarefa, setSelectedTarefa] = useState<number | ''>('');
  const selectedGtNumber = typeof selectedGt === 'number' ? selectedGt : null;

  const tarefasOptions = useMemo(() => {
    return (tarefas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
  }, [tarefas]);

  const { data: textos, isLoading, refetch, isFetching } = useTextoUnicos({
    gtId: selectedGtNumber ?? undefined,
    tarefaId: typeof selectedTarefa === 'number' ? selectedTarefa : undefined,
  });
  const generateTexto = useGenerateTextoUnico();

  const {
    data: textosColaborativos,
    isLoading: collabLoading,
  } = useTextosColaborativos({ gtId: selectedGtNumber ?? undefined });
  const createTexto = useCreateTextoColaborativo();
  const updateTexto = useUpdateTextoColaborativo();
  const queryClient = useQueryClient();

  const [collabDrafts, setCollabDrafts] = useState<
    Record<number, { titulo: string; conteudo: string }>
  >({});
  const [collabEtags, setCollabEtags] = useState<Record<number, string>>({});
  const [collabFeedback, setCollabFeedback] = useState<Record<number, FeedbackEntry>>({});
  const [collabSaving, setCollabSaving] = useState<Record<number, boolean>>({});
  const [novoTitulo, setNovoTitulo] = useState('');
  const [novoConteudo, setNovoConteudo] = useState('');
  const [createFeedback, setCreateFeedback] = useState<FeedbackEntry | null>(null);

  useEffect(() => {
    if (!textosColaborativos) {
      setCollabDrafts({});
      setCollabEtags({});
      setCollabFeedback({});
      return;
    }
    const ids = new Set<number>();
    setCollabDrafts((prev) => {
      const next: Record<number, { titulo: string; conteudo: string }> = {};
      textosColaborativos.forEach((texto) => {
        ids.add(texto.id);
        const existing = prev[texto.id];
        if (!existing || existing.conteudo === texto.conteudo_html) {
          next[texto.id] = { titulo: texto.titulo, conteudo: texto.conteudo_html };
        } else {
          next[texto.id] = existing;
        }
      });
      return next;
    });
    setCollabEtags(() => {
      const next: Record<number, string> = {};
      textosColaborativos.forEach((texto) => {
        next[texto.id] = texto.etag;
      });
      return next;
    });
    setCollabFeedback((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((key) => {
        if (!ids.has(Number(key))) {
          delete next[Number(key)];
        }
      });
      return next;
    });
    setCollabSaving((prev) => {
      const next = { ...prev };
      Object.keys(next).forEach((key) => {
        if (!ids.has(Number(key))) {
          delete next[Number(key)];
        }
      });
      return next;
    });
  }, [textosColaborativos]);

  useEffect(() => {
    setNovoTitulo('');
    setNovoConteudo('');
    setCreateFeedback(null);
  }, [selectedGtNumber]);

  useStreamSubscription({
    alvoTipo: 'texto_colaborativo_list',
    alvoId: selectedGtNumber ?? undefined,
    enabled: Boolean(selectedGtNumber),
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown> & { event?: string };
        if (!data.event || !data.event.startsWith('collab_text:')) {
          return;
        }
        const normalized = normalizePayload(data);
        if (!normalized || normalized.gt !== selectedGtNumber) {
          return;
        }
        queryClient.setQueryData<TextoColaborativo[] | undefined>(
          ['textos-colaborativos', { gtId: normalized.gt }],
          (previous = []) => {
            const filtered = previous.filter((item) => item.id !== normalized.id);
            const next = [normalized, ...filtered];
            return next.sort(
              (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
            );
          },
        );
        setCollabEtags((prev) => ({ ...prev, [normalized.id]: normalized.etag }));
        setCollabDrafts((prev) => {
          const current = prev[normalized.id];
          if (!current || current.conteudo === normalized.conteudo_html) {
            return {
              ...prev,
              [normalized.id]: {
                titulo: normalized.titulo,
                conteudo: normalized.conteudo_html,
              },
            };
          }
          return prev;
        });
      } catch (error) {
        // Ignora payloads malformados
      }
    },
  });

  const buildErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return fallback;
  };

  const handleGenerate = async () => {
    if (selectedGtNumber == null || typeof selectedTarefa !== 'number') {
      return;
    }
    await generateTexto.mutateAsync({ gtId: selectedGtNumber, tarefaId: selectedTarefa });
    refetch();
  };

  const handleCreateTexto = async () => {
    if (selectedGtNumber == null) {
      return;
    }
    if (novoTitulo.trim().length === 0) {
      setCreateFeedback({ type: 'error', message: 'Informe um título para criar o texto.' });
      return;
    }
    setCreateFeedback(null);
    try {
      const created = await createTexto.mutateAsync({
        gtId: selectedGtNumber,
        titulo: novoTitulo.trim(),
        conteudoHtml: novoConteudo,
      });
      setNovoTitulo('');
      setNovoConteudo('');
      setCreateFeedback({ type: 'success', message: 'Texto colaborativo criado com sucesso.' });
      setCollabDrafts((prev) => ({
        ...prev,
        [created.id]: { titulo: created.titulo, conteudo: created.conteudo_html },
      }));
      setCollabEtags((prev) => ({ ...prev, [created.id]: created.etag }));
    } catch (err) {
      const message = buildErrorMessage(err, 'Não foi possível criar o texto colaborativo.');
      setCreateFeedback({ type: 'error', message });
    }
  };

  const handleSalvarTexto = async (textoId: number) => {
    if (selectedGtNumber == null) {
      return;
    }
    const draft = collabDrafts[textoId];
    const etag = collabEtags[textoId];
    if (!draft || !etag) {
      return;
    }
    if (draft.titulo.trim().length === 0) {
      setCollabFeedback((prev) => ({
        ...prev,
        [textoId]: { type: 'error', message: 'Defina um título antes de salvar.' },
      }));
      return;
    }
    setCollabSaving((prev) => ({ ...prev, [textoId]: true }));
    setCollabFeedback((prev) => {
      const next = { ...prev };
      delete next[textoId];
      return next;
    });
    try {
      const updated = await updateTexto.mutateAsync({
        textoId,
        gtId: selectedGtNumber,
        titulo: draft.titulo.trim(),
        conteudoHtml: draft.conteudo,
        etag,
      });
      setCollabEtags((prev) => ({ ...prev, [textoId]: updated.etag }));
      setCollabDrafts((prev) => ({
        ...prev,
        [textoId]: { titulo: updated.titulo, conteudo: updated.conteudo_html },
      }));
      setCollabFeedback((prev) => ({
        ...prev,
        [textoId]: { type: 'success', message: 'Texto atualizado.' },
      }));
    } catch (err) {
      const message = buildErrorMessage(err, 'Não foi possível salvar o texto.');
      setCollabFeedback((prev) => ({
        ...prev,
        [textoId]: { type: 'error', message },
      }));
    } finally {
      setCollabSaving((prev) => ({ ...prev, [textoId]: false }));
    }
  };

  if (isLoading && !textos) {
    return <FullPageLoader message="Carregando textos únicos..." />;
  }

  return (
    <div className="texto-unico">
      <header className="texto-unico__header">
        <div>
          <h1>Textos do GT</h1>
          <p>Crie rascunhos colaborativos em tempo real e gere versões consolidadas quando estiver pronto.</p>
        </div>
      </header>

      <PageInstructions
        title="Como trabalhar com textos do GT"
        description="Integre o fluxo colaborativo antes de gerar o Texto Único para revisão."
        items={[
          {
            title: 'Crie textos colaborativos',
            description: 'Qualquer membro do GT pode editar simultaneamente, com atualização em tempo real.',
          },
          {
            title: 'Selecione GT e tarefa',
            description: 'As gerações de texto único continuam vinculadas a uma tarefa específica.',
          },
          {
            title: 'Monitore versões e ETags',
            description: 'Eles ajudam a evitar conflitos e sinalizam quando há uma atualização recente.',
          },
        ]}
        footer="Ao finalizar um texto colaborativo, gere um Texto Único para consolidar a versão do GT."
      />

      <div className="texto-unico__filters">
        <label>
          <span>GT</span>
          <select
            value={selectedGt}
            onChange={(event) =>
              setSelectedGt(event.target.value ? Number(event.target.value) : '')
            }
          >
            <option value="">Selecione</option>
            {gtOptions.map((gt) => (
              <option key={gt} value={gt}>
                {gt}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Tarefa</span>
          <select
            value={selectedTarefa}
            onChange={(event) =>
              setSelectedTarefa(event.target.value ? Number(event.target.value) : '')
            }
          >
            <option value="">Selecione</option>
            {tarefasOptions.map((tarefa) => (
              <option key={tarefa.id} value={tarefa.id}>
                {tarefa.ordem} — {tarefa.tipo === 'OFICINA' ? 'Oficina' : 'Questionário'}
              </option>
            ))}
          </select>
        </label>

        <div className="texto-unico__actions">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={
              selectedGtNumber == null ||
              typeof selectedTarefa !== 'number' ||
              generateTexto.isPending
            }
          >
            {generateTexto.isPending ? 'Gerando...' : 'Gerar texto único'}
          </button>
          <button type="button" className="ghost" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? 'Atualizando...' : 'Recarregar'}
          </button>
        </div>
      </div>

      <section className="texto-colaborativo">
        <header className="texto-colaborativo__header">
          <div>
            <h2>Textos colaborativos</h2>
            <p>Organize ideias em rascunhos que todo o GT pode editar simultaneamente.</p>
          </div>
        </header>

        {selectedGtNumber == null ? (
          <div className="texto-unico__empty">
            <h3>Nenhum GT selecionado</h3>
            <p>Escolha um GT para visualizar e editar textos colaborativos.</p>
          </div>
        ) : (
          <>
            <div className="texto-colaborativo__create">
              <input
                type="text"
                placeholder="Titulo do novo texto"
                value={novoTitulo}
                onChange={(event) => setNovoTitulo(event.target.value)}
              />
              <textarea
                placeholder="Descreva o conteúdo inicial..."
                rows={4}
                value={novoConteudo}
                onChange={(event) => setNovoConteudo(event.target.value)}
              />
              <div className="texto-colaborativo__create-actions">
                <button
                  type="button"
                  onClick={handleCreateTexto}
                  disabled={createTexto.isPending || novoTitulo.trim().length === 0}
                >
                  {createTexto.isPending ? 'Criando...' : 'Criar texto'}
                </button>
              </div>
              {createFeedback && (
                <p className={`texto-colaborativo__feedback texto-colaborativo__feedback--${createFeedback.type}`}>
                  {createFeedback.message}
                </p>
              )}
            </div>

            {collabLoading && !textosColaborativos ? (
              <div className="texto-unico__empty">
                <h3>Carregando textos colaborativos...</h3>
                <p>Aguarde, estamos sincronizando os rascunhos deste GT.</p>
              </div>
            ) : textosColaborativos && textosColaborativos.length > 0 ? (
              <div className="texto-colaborativo__grid">
                {textosColaborativos.map((texto) => {
                  const draft = collabDrafts[texto.id] ?? {
                    titulo: texto.titulo,
                    conteudo: texto.conteudo_html,
                  };
                  const feedback = collabFeedback[texto.id];
                  const saving = collabSaving[texto.id] ?? false;
                  const updatedAtLabel = new Date(texto.updated_at).toLocaleString('pt-BR');
                  return (
                    <article key={texto.id} className="texto-colaborativo__card">
                      <header>
                        <input
                          type="text"
                          value={draft.titulo}
                          onChange={(event) =>
                            setCollabDrafts((prev) => ({
                              ...prev,
                              [texto.id]: {
                                titulo: event.target.value,
                                conteudo: prev[texto.id]?.conteudo ?? '',
                              },
                            }))
                          }
                        />
                        <span>Versão {texto.version}</span>
                      </header>
                      <textarea
                        rows={6}
                        value={draft.conteudo}
                        onChange={(event) =>
                          setCollabDrafts((prev) => ({
                            ...prev,
                            [texto.id]: {
                              titulo: prev[texto.id]?.titulo ?? '',
                              conteudo: event.target.value,
                            },
                          }))
                        }
                      />
                      <div className="texto-colaborativo__meta">
                        <span>Última atualização: {updatedAtLabel}</span>
                        {collabEtags[texto.id] && <span>ETag: {collabEtags[texto.id]}</span>}
                      </div>
                      <div className="texto-colaborativo__actions">
                        <button
                          type="button"
                          onClick={() => handleSalvarTexto(texto.id)}
                          disabled={saving || updateTexto.isPending}
                        >
                          {saving ? 'Salvando...' : 'Salvar texto'}
                        </button>
                      </div>
                      {feedback && (
                        <p
                          className={`texto-colaborativo__feedback texto-colaborativo__feedback--${feedback.type}`}
                        >
                          {feedback.message}
                        </p>
                      )}
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="texto-unico__empty">
                <h3>Nenhum texto colaborativo</h3>
                <p>Crie um novo texto para iniciar a escrita conjunta do GT.</p>
              </div>
            )}
          </>
        )}
      </section>

      {textos && textos.length > 0 ? (
        <div className="texto-unico__grid">
          {textos.map((texto) => (
            <article key={texto.id} className="texto-unico__card">
              <header>
                <h2>
                  GT {texto.gt} · Tarefa {texto.tarefa}
                </h2>
                <span>Versão {texto.version}</span>
              </header>
              <div className="texto-unico__meta">
                <span>Atualizado em {new Date(texto.updated_at).toLocaleString('pt-BR')}</span>
                {texto.responsavel && <span>Responsável #{texto.responsavel}</span>}
                <span>ETag: {texto.etag}</span>
              </div>
              <details>
                <summary>Visualizar HTML</summary>
                <div className="texto-unico__preview" dangerouslySetInnerHTML={{ __html: texto.conteudo_html }} />
              </details>
            </article>
          ))}
        </div>
      ) : (
        <div className="texto-unico__empty">
          <h3>Nenhum texto único encontrado</h3>
          <p>Selecione um GT e tarefa ou gere um novo conteúdo para iniciar.</p>
        </div>
      )}
    </div>
  );
}
