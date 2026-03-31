import { FormEvent, useEffect, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useComentarios, useCreateComentario, useUpdateComentario } from '@/hooks/useComentarios';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useTarefas } from '@/hooks/useTarefas';
import { usePerguntas } from '@/hooks/usePerguntas';
import { useApiClient } from '@/api/client';
import type { Comentario, PaginatedResponse, Resposta } from '@/api/types';

import './ComentariosPage.css';

const COMMENT_TARGETS = [
  { value: 'resposta', label: 'Resposta' },
  { value: 'texto_unico', label: 'Texto único' },
  { value: 'quadro', label: 'Quadro' },
  { value: 'ppp', label: 'PPP' },
];

export function ComentariosPage() {
  const [alvoTipoFiltro, setAlvoTipoFiltro] = useState('');
  const [alvoIdFiltro, setAlvoIdFiltro] = useState('');
  const [mostrarResolvidos, setMostrarResolvidos] = useState<'todos' | 'abertos' | 'fechados'>('todos');
  const [anchorLocal, setAnchorLocal] = useState('');
  const [anchorTrecho, setAnchorTrecho] = useState('');
  const [alvoTipoNovo, setAlvoTipoNovo] = useState('resposta');
  const [alvoIdNovo, setAlvoIdNovo] = useState('');
  const [gtSelecionado, setGtSelecionado] = useState<number | ''>('');
  const [tarefaSelecionada, setTarefaSelecionada] = useState<number | ''>('');
  const [perguntaSelecionada, setPerguntaSelecionada] = useState<number | ''>('');
  const [respostaSelecionada, setRespostaSelecionada] = useState<Resposta | null>(null);
  const [respostaFeedback, setRespostaFeedback] = useState<string | null>(null);

  const alvoIdNumero = useMemo(() => {
    if (!alvoIdFiltro) {
      return undefined;
    }
    const parsed = Number(alvoIdFiltro);
    return Number.isFinite(parsed) ? parsed : undefined;
  }, [alvoIdFiltro]);

  const { data: comentarios, isLoading, refetch } = useComentarios({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdNumero,
    resolvido:
      mostrarResolvidos === 'todos'
        ? undefined
        : mostrarResolvidos === 'fechados'
        ? true
        : false,
  });
  const criarComentario = useCreateComentario();
  const atualizarComentario = useUpdateComentario();
  const { gtOptions } = useAvailableGts({ scope: 'member' });
  const gtSelecionadoNumero = typeof gtSelecionado === 'number' ? gtSelecionado : null;
  const tarefaSelecionadaNumero = typeof tarefaSelecionada === 'number' ? tarefaSelecionada : null;
  const perguntaSelecionadaNumero = typeof perguntaSelecionada === 'number' ? perguntaSelecionada : null;
  const tarefasQuery = useTarefas({ gtId: gtSelecionadoNumero ?? undefined });
  const perguntasQuery = usePerguntas(tarefaSelecionadaNumero ?? undefined, gtSelecionadoNumero ?? undefined);
  const client = useApiClient();

  useStreamSubscription({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdNumero,
    enabled: Boolean(alvoTipoFiltro && alvoIdNumero),
    onMessage: () => {
      refetch();
    },
  });

  const [draftConteudo, setDraftConteudo] = useState<Record<number, string>>({});
  const [draftResolvido, setDraftResolvido] = useState<Record<number, boolean>>({});

  const comentariosOrdenados = useMemo(() => {
    if (!comentarios) return [];
    return comentarios.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [comentarios]);

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

  const normalizeAnchor = (anchor: unknown) => {
    if (!anchor) return null;
    if (typeof anchor === 'string') {
      try {
        return JSON.parse(anchor) as { local?: string; trecho?: string };
      } catch (err) {
        return null;
      }
    }
    if (typeof anchor === 'object') {
      return anchor as { local?: string; trecho?: string };
    }
    return null;
  };

  const anchorJsonPreview = useMemo(() => {
    if (!anchorLocal.trim() && !anchorTrecho.trim()) {
      return '';
    }
    return JSON.stringify(
      {
        ...(anchorLocal.trim() ? { local: anchorLocal.trim() } : {}),
        ...(anchorTrecho.trim() ? { trecho: anchorTrecho.trim() } : {}),
      },
      null,
      2,
    );
  }, [anchorLocal, anchorTrecho]);

  const perguntasFiltradas = useMemo(() => {
    const perguntas = perguntasQuery.data ?? [];
    if (!gtSelecionadoNumero) {
      return perguntas;
    }
    return perguntas
      .filter((pergunta) => pergunta.gts.length === 0 || pergunta.gts.includes(gtSelecionadoNumero))
      .sort((a, b) => a.ordem - b.ordem);
  }, [gtSelecionadoNumero, perguntasQuery.data]);

  useEffect(() => {
    setTarefaSelecionada('');
    setPerguntaSelecionada('');
    setRespostaSelecionada(null);
    setRespostaFeedback(null);
  }, [gtSelecionado]);

  useEffect(() => {
    setPerguntaSelecionada('');
    setRespostaSelecionada(null);
    setRespostaFeedback(null);
  }, [tarefaSelecionada]);

  useEffect(() => {
    let active = true;

    const fetchResposta = async () => {
      if (alvoTipoNovo !== 'resposta') {
        setRespostaSelecionada(null);
        setRespostaFeedback(null);
        return;
      }
      if (!gtSelecionadoNumero || !perguntaSelecionadaNumero) {
        setRespostaSelecionada(null);
        setRespostaFeedback(null);
        return;
      }
      setRespostaFeedback('Buscando resposta vinculada...');
      try {
        const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
          query: {
            gt_id: gtSelecionadoNumero,
            pergunta_id: perguntaSelecionadaNumero,
            page_size: 1,
          },
        });
        if (!active) return;
        const resposta = response.data?.results?.[0] ?? null;
        setRespostaSelecionada(resposta);
        if (resposta) {
          setAlvoTipoNovo('resposta');
          setAlvoIdNovo(String(resposta.id));
          setRespostaFeedback('Resposta encontrada e selecionada.');
        } else {
          setAlvoIdNovo('');
          setRespostaFeedback('Nenhuma resposta encontrada para esse GT e missão.');
        }
      } catch (err: any) {
        if (!active) return;
        setRespostaSelecionada(null);
        setRespostaFeedback('Falha ao buscar a resposta selecionada.');
      }
    };

    fetchResposta();
    return () => {
      active = false;
    };
  }, [alvoTipoNovo, client, gtSelecionadoNumero, perguntaSelecionadaNumero]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const alvoTipo = alvoTipoNovo.trim();
    const alvoId = Number(alvoIdNovo);
    const conteudo = String(form.get('conteudo') ?? '').trim();
    const mentions = String(form.get('mentions') ?? '')
      .split(',')
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value) && value > 0);

    const anchorJson =
      anchorLocal.trim() || anchorTrecho.trim()
        ? JSON.stringify({
            ...(anchorLocal.trim() ? { local: anchorLocal.trim() } : {}),
            ...(anchorTrecho.trim() ? { trecho: anchorTrecho.trim() } : {}),
          })
        : undefined;
    if (!alvoTipo || !alvoId || !conteudo) {
      return;
    }
    await criarComentario.mutateAsync({
      alvoTipo,
      alvoId,
      conteudoHtml: ensureHtml(conteudo),
      anchorJson,
      mentions: mentions.length > 0 ? mentions : undefined,
    });
    refetch();
    event.currentTarget.reset();
    setAnchorLocal('');
    setAnchorTrecho('');
    setAlvoIdNovo('');
    setRespostaSelecionada(null);
    setRespostaFeedback(null);
  };

  const renderContextoComentario = (comentario: Comentario) => {
    const preview = comentario.alvo_preview;
    if (!preview) return null;
    const anchor = normalizeAnchor(comentario.anchor_json);
    if (preview.type === 'resposta') {
      return (
        <div className="comentarios__contexto">
          <div className="comentarios__contexto-line">
            <span>GT: {preview.gt_nome ?? `#${preview.gt ?? '—'}`}</span>
            <span>Trilha: {preview.tarefa_nome ?? `#${preview.tarefa ?? '—'}`}</span>
            <span>Missão: {preview.pergunta_ordem ?? preview.pergunta ?? '—'}</span>
          </div>
          {preview.pergunta_texto && <p className="comentarios__contexto-texto">{preview.pergunta_texto}</p>}
          {anchor && (anchor.local || anchor.trecho) && (
            <div className="comentarios__contexto-anchor">
              {anchor.local && <span>Local: {anchor.local}</span>}
              {anchor.trecho && <span>Trecho: {anchor.trecho}</span>}
            </div>
          )}
        </div>
      );
    }
    if (preview.type === 'texto_unico') {
      return (
        <div className="comentarios__contexto">
          <div className="comentarios__contexto-line">
            <span>GT: {preview.gt_nome ?? `#${preview.gt ?? '—'}`}</span>
            <span>Trilha: {preview.tarefa_nome ?? `#${preview.tarefa ?? '—'}`}</span>
            <span>Texto único #{preview.id}</span>
          </div>
          {anchor && (anchor.local || anchor.trecho) && (
            <div className="comentarios__contexto-anchor">
              {anchor.local && <span>Local: {anchor.local}</span>}
              {anchor.trecho && <span>Trecho: {anchor.trecho}</span>}
            </div>
          )}
        </div>
      );
    }
    if (preview.type === 'ppp') {
      return (
        <div className="comentarios__contexto">
          <div className="comentarios__contexto-line">
            <span>Escola: {preview.escola_nome ?? `#${preview.escola ?? '—'}`}</span>
            <span>{preview.titulo ?? 'PPP'}</span>
            <span>Status: {preview.status ?? '—'}</span>
          </div>
          {anchor && (anchor.local || anchor.trecho) && (
            <div className="comentarios__contexto-anchor">
              {anchor.local && <span>Local: {anchor.local}</span>}
              {anchor.trecho && <span>Trecho: {anchor.trecho}</span>}
            </div>
          )}
        </div>
      );
    }
    return (
      <div className="comentarios__contexto">
        <div className="comentarios__contexto-line">
          <span>GT: {preview.gt_nome ?? `#${preview.gt ?? '—'}`}</span>
          <span>Template: {preview.template ?? '—'}</span>
          <span>Quadro #{preview.id}</span>
        </div>
        {anchor && (anchor.local || anchor.trecho) && (
          <div className="comentarios__contexto-anchor">
            {anchor.local && <span>Local: {anchor.local}</span>}
            {anchor.trecho && <span>Trecho: {anchor.trecho}</span>}
          </div>
        )}
      </div>
    );
  };

  const handleAtualizar = async (comentarioId: number, etag: string) => {
    const conteudo = draftConteudo[comentarioId];
    const resolvido = draftResolvido[comentarioId];
    await atualizarComentario.mutateAsync({
      comentarioId,
      payload: {
        conteudo_html: ensureHtml(conteudo ?? ''),
        resolvido,
      },
      etag,
    });
    refetch();
  };

  if (isLoading && !comentarios) {
    return <FullPageLoader message="Carregando comentários..." />;
  }

  return (
    <div className="comentarios">
      <header className="comentarios__header">
        <div>
          <h1>Comentários</h1>
          <p>Gerencie discussões ancoradas em conteúdos e sinalize resoluções rapidamente.</p>
        </div>
      </header>

      <PageInstructions
        title="Boas práticas em discussões"
        description="Comentários ajudam a registrar decisões e pendências diretamente no conteúdo."
        items={[
          {
            title: 'Contextualize pelo alvo',
            description: 'Informe tipo e ID do registro (tarefa, resposta, quadro) para centralizar a conversa.',
          },
          {
            title: 'Mencione colaboradores',
            description: 'Use a lista de IDs para notificar pessoas responsáveis pela atualização solicitada.',
          },
          {
            title: 'Resolva quando concluído',
            description: 'Marcar como resolvido remove o comentário da fila de pendências e notifica interessados.',
          },
        ]}
      />

      <div className="comentarios__filters">
        <label>
          <span>Alvo tipo</span>
          <select value={alvoTipoFiltro} onChange={(event) => setAlvoTipoFiltro(event.target.value)}>
            <option value="">Todos</option>
            {COMMENT_TARGETS.map((target) => (
              <option key={target.value} value={target.value}>
                {target.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Alvo ID</span>
          <input type="number" value={alvoIdFiltro} onChange={(event) => setAlvoIdFiltro(event.target.value)} />
        </label>
        <label>
          <span>Status</span>
          <select value={mostrarResolvidos} onChange={(event) => setMostrarResolvidos(event.target.value as any)}>
            <option value="todos">Todos</option>
            <option value="abertos">Abertos</option>
            <option value="fechados">Resolvidos</option>
          </select>
        </label>
        <button type="button" className="ghost" onClick={() => refetch()}>
          Recarregar
        </button>
      </div>

      <section className="comentarios__novo">
        <h2>Novo comentário</h2>
        <form onSubmit={handleSubmit}>
          <label>
            <span>GT</span>
            <select
              value={gtSelecionado === '' ? '' : String(gtSelecionado)}
              onChange={(event) => setGtSelecionado(event.target.value ? Number(event.target.value) : '')}
              disabled={alvoTipoNovo !== 'resposta'}
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
            <span>Tarefa</span>
            <select
              value={tarefaSelecionada === '' ? '' : String(tarefaSelecionada)}
              onChange={(event) => setTarefaSelecionada(event.target.value ? Number(event.target.value) : '')}
              disabled={alvoTipoNovo !== 'resposta' || !gtSelecionadoNumero || tarefasQuery.isLoading}
            >
              <option value="">{gtSelecionadoNumero ? 'Selecione' : 'Escolha um GT'}</option>
              {(tarefasQuery.data ?? []).map((tarefa) => (
                <option key={tarefa.id} value={tarefa.id}>
                  {tarefa.ordem}. {tarefa.nome}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Pergunta</span>
            <select
              value={perguntaSelecionada === '' ? '' : String(perguntaSelecionada)}
              onChange={(event) => setPerguntaSelecionada(event.target.value ? Number(event.target.value) : '')}
              disabled={alvoTipoNovo !== 'resposta' || !tarefaSelecionadaNumero || perguntasQuery.isLoading}
            >
              <option value="">{tarefaSelecionadaNumero ? 'Selecione' : 'Escolha uma tarefa'}</option>
              {perguntasFiltradas.map((pergunta) => (
                <option key={pergunta.id} value={pergunta.id}>
                  Missão {pergunta.ordem}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Alvo tipo</span>
            <select name="alvoTipo" required value={alvoTipoNovo} onChange={(event) => setAlvoTipoNovo(event.target.value)}>
              {COMMENT_TARGETS.map((target) => (
                <option key={target.value} value={target.value}>
                  {target.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Alvo ID</span>
            <input
              name="alvoId"
              type="number"
              min={1}
              placeholder="Ex.: 120"
              required
              value={alvoIdNovo}
              onChange={(event) => setAlvoIdNovo(event.target.value)}
            />
          </label>
          <div className="comentarios__hint">
            {alvoTipoNovo === 'resposta'
              ? respostaFeedback || 'Selecione GT, tarefa e missão para preencher automaticamente o alvo.'
              : 'Selecione um alvo diferente de resposta usando o ID manualmente.'}
          </div>
          {respostaSelecionada && (
            <div className="comentarios__contexto comentarios__contexto--form">
              <div className="comentarios__contexto-line">
                <span>Resposta #{respostaSelecionada.id}</span>
                <span>GT: {respostaSelecionada.gt_nome ?? `#${respostaSelecionada.gt}`}</span>
                <span>Missão: {respostaSelecionada.pergunta_ordem ?? respostaSelecionada.pergunta}</span>
              </div>
              {respostaSelecionada.pergunta_texto && (
                <p className="comentarios__contexto-texto">{respostaSelecionada.pergunta_texto}</p>
              )}
            </div>
          )}
          <label>
            <span>Mentions (IDs separados por vírgula)</span>
            <input name="mentions" type="text" placeholder="Ex.: 3, 18" />
          </label>
          <div className="comentarios__anchor full">
            <div className="comentarios__anchor-header">
              <span>Referência no conteúdo (opcional)</span>
              <p>Descreva onde o comentário se aplica e nós geramos o JSON automaticamente.</p>
            </div>
            <div className="comentarios__anchor-fields">
              <label>
                <span>Local ou bloco</span>
                <input
                  type="text"
                  name="anchorLocal"
                  value={anchorLocal}
                  onChange={(event) => setAnchorLocal(event.target.value)}
                  placeholder="Ex.: Introdução · Missão 3"
                />
              </label>
              <label>
                <span>Trecho destacado</span>
                <textarea
                  name="anchorTrecho"
                  rows={3}
                  value={anchorTrecho}
                  onChange={(event) => setAnchorTrecho(event.target.value)}
                  placeholder="Cole o trecho ou palavras-chave que quer ancorar"
                />
              </label>
            </div>
            <div className="comentarios__anchor-preview">
              <span>Prévia do JSON</span>
              <code>{anchorJsonPreview || 'Nenhuma referência adicionada.'}</code>
            </div>
          </div>
          <label className="full">
            <span>Conteúdo</span>
            <textarea
              name="conteudo"
              rows={4}
              placeholder="Descreva o ajuste sugerido (texto simples; convertemos para HTML)"
              required
            />
          </label>
          <button type="submit" disabled={criarComentario.isPending}>
            {criarComentario.isPending ? 'Enviando...' : 'Registrar comentário'}
          </button>
        </form>
      </section>

      {comentariosOrdenados.length > 0 ? (
        <div className="comentarios__lista">
          {comentariosOrdenados.map((comentario) => (
            <article key={comentario.id} className="comentarios__card">
              <header>
                <div>
                  <h3>
                    Comentário #{comentario.id} — {comentario.alvo_tipo} #{comentario.alvo_id}
                  </h3>
                  <span>Criado em {new Date(comentario.created_at).toLocaleString('pt-BR')}</span>
                </div>
                <div className="comentarios__meta">
                  <span>Autor #{comentario.autor ?? '—'}</span>
                  <span>Resolução: {comentario.resolvido ? 'Resolvido' : 'Em aberto'}</span>
                  {comentario.resolvido_por && <span>Resolvido por #{comentario.resolvido_por}</span>}
                  {comentario.resolved_at && <span>Em {new Date(comentario.resolved_at).toLocaleString('pt-BR')}</span>}
                  <span>ETag: {comentario.etag}</span>
                </div>
              </header>

              {renderContextoComentario(comentario)}

              <details>
                <summary>Conteúdo atual</summary>
                <div dangerouslySetInnerHTML={{ __html: comentario.conteudo_html }} />
              </details>

              <div className="comentarios__editar">
                <label className="full">
                  <span>Atualizar conteúdo</span>
                  <textarea
                    rows={3}
                    value={draftConteudo[comentario.id] ?? comentario.conteudo_html}
                    onChange={(event) => setDraftConteudo((prev) => ({ ...prev, [comentario.id]: event.target.value }))}
                  />
                </label>
                <label>
                  <span>Marcar como resolvido?</span>
                  <select
                    value={draftResolvido[comentario.id] ?? comentario.resolvido}
                    onChange={(event) => setDraftResolvido((prev) => ({ ...prev, [comentario.id]: event.target.value === 'true' }))}
                  >
                    <option value="false">Não</option>
                    <option value="true">Sim</option>
                  </select>
                </label>
                <button
                  type="button"
                  onClick={() => handleAtualizar(comentario.id, comentario.etag)}
                  disabled={atualizarComentario.isPending}
                >
                  {atualizarComentario.isPending ? 'Salvando...' : 'Aplicar atualização'}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="comentarios__empty">
          <h3>Sem comentários</h3>
          <p>Ajuste filtros ou crie um novo comentário para iniciar uma discussão.</p>
        </div>
      )}
    </div>
  );
}
