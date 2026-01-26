import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { ApiError } from '@/api/client';
import type { TextoColaborativo } from '@/api/types';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';
import {
  useCreateTextoColaborativo,
  useTextosColaborativos,
  useUpdateTextoColaborativo,
  useBulkUpdateTextosColaborativos,
} from '@/hooks/useTextosColaborativos';
import { useGenerateTextoUnico, useTextoUnicos } from '@/hooks/useTextoUnico';
import { useTarefas } from '@/hooks/useTarefas';

import './TextoUnicoPage.css';

type FeedbackEntry = {
  type: 'success' | 'error' | 'info';
  message: string;
};

type Template = {
  key: string;
  label: string;
  template: string;
};

type TextoUnicoSection = {
  id: string;
  pergunta: string;
  html: string;
  preview: string;
};

const TEXTO_TEMPLATES: Template[] = [
  {
    key: 'topicos',
    label: 'Resumo em tópicos',
    template:
      '<p><strong>Resumo rápido</strong></p><ul><li>Contexto principal...</li><li>Ponto de atenção...</li><li>Decisão tomada...</li></ul><p><strong>Próximo passo:</strong> ...</p>',
  },
  {
    key: 'historia',
    label: 'Narrativa clara',
    template:
      '<p><strong>Situação</strong>: ...</p><p><strong>Ação</strong>: ...</p><p><strong>Resultado</strong>: ...</p><p><em>Inclua números e evidências sempre que possível.</em></p>',
  },
  {
    key: 'plano',
    label: 'Plano de ação',
    template:
      '<p><strong>Objetivo</strong>: ...</p><ol><li>Passo 1 — descrição e responsável.</li><li>Passo 2 — data alvo.</li><li>Riscos e mitigação.</li></ol><p><strong>Métrica de sucesso</strong>: ...</p>',
  },
];

const stripHtml = (value: string) => {
  if (!value.trim()) return '';
  const doc = new DOMParser().parseFromString(value, 'text/html');
  return (doc.body.textContent ?? '').replace(/\s+/g, ' ').trim();
};

const getWordStats = (value: string) => {
  const trimmed = stripHtml(value);
  return {
    words: trimmed ? trimmed.split(/\s+/).length : 0,
    chars: trimmed.length,
  };
};

const ensureHtml = (value: string) => {
  const text = value.trim();
  if (!text) return '';
  const hasHtmlTag = /<\/?[a-z][\s\S]*>/i.test(text);
  if (hasHtmlTag) {
    return value;
  }
  const paragraphs = text
    .split(/\n{2,}/)
    .map((block) => `<p>${block.replace(/\n/g, '<br />')}</p>`)
    .join('');
  return paragraphs || `<p>${text}</p>`;
};

const buildPreview = (value: string, maxLength = 200) => {
  const text = stripHtml(value);
  if (!text) return 'Sem conteúdo.';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}…`;
};

const parseTextoUnicoSections = (conteudoHtml: string): TextoUnicoSection[] => {
  if (!conteudoHtml.trim()) return [];
  const doc = new DOMParser().parseFromString(conteudoHtml, 'text/html');
  const sections: TextoUnicoSection[] = [];
  let current: { pergunta: string; nodes: Node[] } | null = null;

  const pushCurrent = () => {
    if (!current) return;
    const container = doc.createElement('div');
    current.nodes.forEach((node) => container.appendChild(node.cloneNode(true)));
    const html = container.innerHTML.trim();
    const preview = buildPreview(html);
    sections.push({
      id: `q-${sections.length + 1}`,
      pergunta: current.pergunta || `Pergunta ${sections.length + 1}`,
      html,
      preview,
    });
  };

  Array.from(doc.body.childNodes).forEach((node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element;
      if (element.tagName.toLowerCase() === 'h3') {
        pushCurrent();
        current = {
          pergunta: (element.textContent ?? '').trim(),
          nodes: [],
        };
        return;
      }
    }
    if (current) {
      current.nodes.push(node);
    }
  });

  pushCurrent();

  if (sections.length === 0) {
    const preview = buildPreview(conteudoHtml);
    if (preview) {
      sections.push({
        id: 'q-1',
        pergunta: 'Texto completo',
        html: conteudoHtml,
        preview,
      });
    }
  }

  return sections;
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
    pergunta: payload.pergunta == null ? null : Number(payload.pergunta),
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
  const { gtOptions } = useAvailableGts();

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
  const bulkUpdateTextos = useBulkUpdateTextosColaborativos(selectedGtNumber);
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
  const [bulkFeedback, setBulkFeedback] = useState<FeedbackEntry | null>(null);
  const [modalSection, setModalSection] = useState<
    | null
    | {
        textoId: number;
        gt: number;
        tarefa: number;
        version: number;
        pergunta: string;
        html: string;
      }
  >(null);
  const novoStats = getWordStats(novoConteudo);

  const textoSections = useMemo(() => {
    const map = new Map<number, TextoUnicoSection[]>();
    (textos ?? []).forEach((texto) => {
      map.set(texto.id, parseTextoUnicoSections(texto.conteudo_html));
    });
    return map;
  }, [textos]);

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
    if (!modalSection) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setModalSection(null);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [modalSection]);

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

  const collectDirtyTextos = () => {
    if (!textosColaborativos) return [] as Array<{ id: number; titulo: string; conteudoHtml: string; etag: string }>;
    return textosColaborativos
      .map((texto) => {
        const draft = collabDrafts[texto.id] ?? { titulo: texto.titulo, conteudo: texto.conteudo_html };
        const hasChanges = draft.titulo.trim() !== texto.titulo || draft.conteudo !== texto.conteudo_html;
        if (!hasChanges) return null;
        const etag = collabEtags[texto.id];
        if (!etag) return null;
        return {
          id: texto.id,
          titulo: draft.titulo.trim(),
          conteudoHtml: ensureHtml(draft.conteudo),
          etag,
        };
      })
      .filter(Boolean) as Array<{ id: number; titulo: string; conteudoHtml: string; etag: string }>;
  };

  const buildErrorMessage = (err: unknown, fallback: string) => {
    if (err instanceof ApiError) {
      return err.message;
    }
    if (err instanceof Error) {
      return err.message;
    }
    return fallback;
  };

  const handleSalvarTodos = async () => {
    const itens = collectDirtyTextos();
    if (itens.length === 0) {
      setBulkFeedback({ type: 'info', message: 'Nenhum texto colaborativo alterado.' });
      return;
    }
    setBulkFeedback(null);
    try {
      const result = await bulkUpdateTextos.mutateAsync(itens);
      setCollabEtags((prev) => {
        const next = { ...prev };
        result.updated.forEach((item) => {
          next[item.id] = item.etag;
        });
        return next;
      });
      setCollabDrafts((prev) => {
        const next = { ...prev };
        result.updated.forEach((item) => {
          next[item.id] = { titulo: item.titulo, conteudo: item.conteudo_html };
        });
        return next;
      });
      if (result.errors.length > 0) {
        setBulkFeedback({
          type: 'info',
          message: `Alguns textos não foram salvos (${result.errors.length}). Confira ETags desatualizados.`,
        });
      } else {
        setBulkFeedback({ type: 'success', message: 'Todos os textos alterados foram salvos.' });
      }
    } catch (err) {
      const message = buildErrorMessage(err, 'Falha ao salvar textos em lote.');
      setBulkFeedback({ type: 'error', message });
    }
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
        conteudoHtml: ensureHtml(novoConteudo),
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

  const handleAppendTemplateNew = (template: string) => {
    setNovoConteudo((prev) => {
      const separator = prev.trim() ? '\n\n' : '';
      return `${prev}${separator}${template}`;
    });
    setCreateFeedback({ type: 'info', message: 'Modelo adicionado. Personalize antes de salvar.' });
  };

  const handleAppendTemplateCollab = (textoId: number, template: string) => {
    setCollabDrafts((prev) => {
      const source = textosColaborativos?.find((item) => item.id === textoId);
      const current = prev[textoId] ?? { titulo: source?.titulo ?? '', conteudo: source?.conteudo_html ?? '' };
      const separator = current.conteudo.trim() ? '\n\n' : '';
      return {
        ...prev,
        [textoId]: { ...current, conteudo: `${current.conteudo}${separator}${template}` },
      };
    });
    setCollabFeedback((prev) => ({
      ...prev,
      [textoId]: { type: 'info', message: 'Modelo adicionado; ajuste o texto e salve.' },
    }));
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
        conteudoHtml: ensureHtml(draft.conteudo),
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
            title: 'Selecione GT e trilha',
            description: 'As gerações de texto único continuam vinculadas a uma trilha específica.',
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
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Trilha</span>
          <select
            value={selectedTarefa}
            onChange={(event) =>
              setSelectedTarefa(event.target.value ? Number(event.target.value) : '')
            }
          >
            <option value="">Selecione</option>
            {tarefasOptions.map((tarefa) => (
              <option key={tarefa.id} value={tarefa.id}>
                Trilha {tarefa.ordem} — {tarefa.tipo === 'OFICINA' ? 'Oficina' : 'Questionário'}
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
          {selectedGtNumber != null && (
            <div className="texto-colaborativo__header-actions">
              <button
                type="button"
                onClick={handleSalvarTodos}
                disabled={bulkUpdateTextos.isPending}
              >
                {bulkUpdateTextos.isPending ? 'Salvando em lote...' : 'Salvar textos alterados'}
              </button>
              {bulkFeedback && (
                <span className={`texto-colaborativo__feedback texto-colaborativo__feedback--${bulkFeedback.type}`}>
                  {bulkFeedback.message}
                </span>
              )}
            </div>
          )}
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
                placeholder="Título do novo texto"
                value={novoTitulo}
                onChange={(event) => setNovoTitulo(event.target.value)}
              />
              <RichTextEditor
                value={novoConteudo}
                onChange={setNovoConteudo}
                placeholder="Descreva o conteúdo inicial."
              />
              <div className="texto-colaborativo__toolbar">
                <div className="texto-colaborativo__chips">
                  {TEXTO_TEMPLATES.map((template) => (
                    <button
                      key={template.key}
                      type="button"
                      onClick={() => handleAppendTemplateNew(template.template)}
                      disabled={createTexto.isPending}
                    >
                      {template.label}
                    </button>
                  ))}
                </div>
                <div className="texto-colaborativo__stats">
                  <span>{novoStats.words} palavra(s)</span>
                  <span>·</span>
                  <span>{novoStats.chars} caractere(s)</span>
                </div>
              </div>
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
                  const stats = getWordStats(draft.conteudo);
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
                      {texto.pergunta ? (
                        <div className="texto-colaborativo__tag">
                          Origem: Missão #{texto.pergunta}
                        </div>
                      ) : null}
                      <RichTextEditor
                        value={draft.conteudo}
                        onChange={(value) =>
                          setCollabDrafts((prev) => ({
                            ...prev,
                            [texto.id]: {
                              titulo: prev[texto.id]?.titulo ?? '',
                              conteudo: value,
                            },
                          }))
                        }
                        placeholder="Escreva o texto colaborativo."
                      />
                      <div className="texto-colaborativo__toolbar texto-colaborativo__toolbar--compact">
                        <div className="texto-colaborativo__chips">
                          {TEXTO_TEMPLATES.map((template) => (
                            <button
                              key={template.key}
                              type="button"
                              onClick={() => handleAppendTemplateCollab(texto.id, template.template)}
                              disabled={saving || updateTexto.isPending || bulkUpdateTextos.isPending}
                            >
                              {template.label}
                            </button>
                          ))}
                        </div>
                        <div className="texto-colaborativo__stats">
                          <span>{stats.words} palavra(s)</span>
                          <span>·</span>
                          <span>{stats.chars} caractere(s)</span>
                        </div>
                      </div>
                      <div className="texto-colaborativo__meta">
                        <span>Última atualização: {updatedAtLabel}</span>
                        {collabEtags[texto.id] && <span>ETag: {collabEtags[texto.id]}</span>}
                      </div>
                      <div className="texto-colaborativo__actions">
                        <button
                          type="button"
                          onClick={() => handleSalvarTexto(texto.id)}
                          disabled={saving || updateTexto.isPending || bulkUpdateTextos.isPending}
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
                  GT {texto.gt} · Trilha {texto.tarefa}
                </h2>
                <span>Versão {texto.version}</span>
              </header>
              <div className="texto-unico__meta">
                <span>Atualizado em {new Date(texto.updated_at).toLocaleString('pt-BR')}</span>
                {texto.responsavel && <span>Responsável #{texto.responsavel}</span>}
                <span>ETag: {texto.etag}</span>
              </div>
              {(textoSections.get(texto.id) ?? []).length > 0 ? (
                <div className="texto-unico__questions">
                  {(textoSections.get(texto.id) ?? []).map((section, index) => (
                    <button
                      key={section.id}
                      type="button"
                      className="texto-unico__question"
                      onClick={() =>
                        setModalSection({
                          textoId: texto.id,
                          gt: texto.gt,
                          tarefa: texto.tarefa,
                          version: texto.version,
                          pergunta: section.pergunta,
                          html: section.html,
                        })
                      }
                      aria-label={`Abrir pergunta ${index + 1}`}
                    >
                      <span className="texto-unico__question-index">Pergunta {index + 1}</span>
                      <span className="texto-unico__question-title">{section.pergunta}</span>
                      <span className="texto-unico__question-preview">{section.preview}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="texto-unico__empty">
                  <h3>Sem perguntas disponíveis</h3>
                  <p>O conteúdo ainda não foi estruturado para exibir as perguntas.</p>
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="texto-unico__empty">
          <h3>Nenhum texto único encontrado</h3>
          <p>Selecione um GT e trilha ou gere um novo conteúdo para iniciar.</p>
        </div>
      )}

      {modalSection ? (
        <div
          className="texto-unico__modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="texto-unico-modal-title"
          onClick={() => setModalSection(null)}
        >
          <div className="texto-unico__modal" onClick={(event) => event.stopPropagation()}>
            <header className="texto-unico__modal-header">
              <div>
                <p className="texto-unico__modal-eyebrow">
                  GT {modalSection.gt} · Trilha {modalSection.tarefa}
                </p>
                <h3 id="texto-unico-modal-title">{modalSection.pergunta}</h3>
                <p className="texto-unico__modal-meta">Versão {modalSection.version}</p>
              </div>
              <button
                type="button"
                className="texto-unico__modal-close"
                onClick={() => setModalSection(null)}
                aria-label="Fechar modal da pergunta"
              >
                Fechar
              </button>
            </header>
            <div className="texto-unico__modal-body">
              <div
                className="texto-unico__modal-content"
                dangerouslySetInnerHTML={{ __html: modalSection.html }}
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
