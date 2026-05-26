import { FormEvent, useEffect, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useCreateRevisao, useDeleteRevisao, useRevisoes, useUpdateRevisao } from '@/hooks/useRevisoes';
import { useRespostas } from '@/hooks/useRespostas';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useAiAssist } from '@/hooks/useAiAssist';
import { useApiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';
import type { Resposta } from '@/api/types';

import './RevisoesPage.css';

const STATUS_OPTIONS = [
  { value: 'rascunho', label: 'Rascunho' },
  { value: 'em_revisao', label: 'Em revisão' },
  { value: 'aprovado', label: 'Aprovado' },
  { value: 'reprovado', label: 'Reprovado' },
];

const ALVO_TIPOS = [
  { value: 'resposta', label: 'Resposta' },
  { value: 'texto_unico', label: 'Texto único' },
  { value: 'quadro', label: 'Quadro' },
];

export function RevisoesPage() {
  const [gtFiltro, setGtFiltro] = useState<number | ''>('');
  const [buscaConteudo, setBuscaConteudo] = useState('');

  const parseNumericId = (value: string): number | undefined => {
    if (!value) return undefined;
    const match = value.match(/(\d+)(?!.*\d)/);
    if (!match) return undefined;
    const num = Number(match[1]);
    return Number.isFinite(num) ? num : undefined;
  };

  const { data: revisoes, isLoading, refetch } = useRevisoes();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts({ scope: 'member' });
  const { data: respostas, isLoading: respostasLoading, refetch: refetchRespostas } = useRespostas({
    includeAll: true,
  });

  const createRevisao = useCreateRevisao();
  const updateRevisao = useUpdateRevisao();
  const deleteRevisao = useDeleteRevisao();

  const [draftParecer, setDraftParecer] = useState<Record<number, string>>({});
  const [draftStatus, setDraftStatus] = useState<Record<number, string>>({});
  const [draftParecerResposta, setDraftParecerResposta] = useState<Record<number, string>>({});
  const [feedbackResposta, setFeedbackResposta] = useState<Record<number, string>>({});
  const [draftConteudoResposta, setDraftConteudoResposta] = useState<Record<number, string>>({});
  const [modalRespostaId, setModalRespostaId] = useState<number | null>(null);
  const [iaFeedback, setIaFeedback] = useState<string | null>(null);
  const [deleteFeedback, setDeleteFeedback] = useState<Record<number, string>>({});
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const client = useApiClient();
  const aiAssist = useAiAssist();
  const { user } = useAuth();

  const stripHtml = (value?: string | null) =>
    (value ?? '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

  const htmlToPlainText = (value?: string | null) => {
    if (!value) return '';
    const normalized = value
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n');
    return normalized
      .replace(/<[^>]+>/g, ' ')
      .replace(/[ \t]+/g, ' ')
      .replace(/\n\s+/g, '\n')
      .trim();
  };

  const revisoesOrdenadas = useMemo(() => {
    if (!revisoes) return [];
    return revisoes.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [revisoes]);

  const respostasById = useMemo(() => {
    if (!respostas) return new Map<number, Resposta>();
    return new Map(respostas.map((resp) => [resp.id, resp]));
  }, [respostas]);

  const gtsPermitidos = useMemo(() => {
    if (user?.role !== 'articulador') {
      return null;
    }
    return new Set(gtOptions.map((gt) => gt.id));
  }, [gtOptions, user?.role]);

  const respostasFiltradas = useMemo(() => {
    if (!respostas) return [];
    const term = buscaConteudo.trim().toLowerCase();
    return respostas
      .filter((resp) => {
        if (gtsPermitidos && !gtsPermitidos.has(resp.gt)) return false;
        if (gtFiltro && resp.gt !== gtFiltro) return false;
        if (!term) return true;
        const textoPergunta = (resp.pergunta_texto || '').toLowerCase();
        const textoConteudo = (resp.conteudo_html || '').replace(/<[^>]+>/g, ' ').toLowerCase();
        return textoPergunta.includes(term) || textoConteudo.includes(term);
      })
      .sort((a, b) => {
        const perguntaA = a.pergunta ?? Number.MAX_SAFE_INTEGER;
        const perguntaB = b.pergunta ?? Number.MAX_SAFE_INTEGER;
        if (perguntaA !== perguntaB) {
          return perguntaA - perguntaB;
        }
        return new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime();
      })
      .slice(0, 50);
  }, [buscaConteudo, gtFiltro, respostas, gtsPermitidos]);

  const respostaAtiva = useMemo(
    () => respostasFiltradas.find((resp) => resp.id === modalRespostaId) ?? null,
    [modalRespostaId, respostasFiltradas],
  );

  useEffect(() => {
    if (modalRespostaId && !respostaAtiva) {
      setModalRespostaId(null);
    }
  }, [modalRespostaId, respostaAtiva]);

  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setModalRespostaId(null);
      }
    };
    if (modalRespostaId) {
      window.addEventListener('keydown', handleEsc);
    }
    return () => window.removeEventListener('keydown', handleEsc);
  }, [modalRespostaId]);

  const handleSubmitNovaRevisao = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const alvoTipo = String(form.get('alvoTipo') ?? '').trim();
    const alvoIdValue = String(form.get('alvoId') ?? '');
    const alvoId = parseNumericId(alvoIdValue);
    const parecer = String(form.get('parecer') ?? '');
    const revisor = form.get('revisor') ? Number(form.get('revisor')) : undefined;
    if (!alvoTipo || !alvoId) {
      return;
    }
    await createRevisao.mutateAsync({ alvoTipo, alvoId, parecerHtml: parecer || undefined, revisor, status: 'em_revisao' });
    refetch();
    formElement.reset();
  };

  const handleAtualizar = async (revisaoId: number, etag: string) => {
    const payload: Record<string, unknown> = {};
    if (draftParecer[revisaoId] !== undefined) {
      payload.parecer_html = draftParecer[revisaoId];
    }
    if (draftStatus[revisaoId]) {
      payload.status = draftStatus[revisaoId];
    }
    if (Object.keys(payload).length === 0) {
      return;
    }
    await updateRevisao.mutateAsync({
      revisaoId,
      payload,
      etag,
    });
    refetch();
    setDraftParecer((prev) => {
      const next = { ...prev };
      delete next[revisaoId];
      return next;
    });
    setDraftStatus((prev) => {
      const next = { ...prev };
      delete next[revisaoId];
      return next;
    });
  };

  const handleExcluir = async (revisaoId: number) => {
    const confirmacao = window.confirm('Excluir este parecer? Esta ação não pode ser desfeita.');
    if (!confirmacao) return;
    setDeletingId(revisaoId);
    setDeleteFeedback((prev) => ({ ...prev, [revisaoId]: '' }));
    try {
      await deleteRevisao.mutateAsync({ revisaoId });
      setDeleteFeedback((prev) => ({ ...prev, [revisaoId]: 'Parecer excluído com sucesso.' }));
      refetch();
    } catch (err: any) {
      setDeleteFeedback((prev) => ({ ...prev, [revisaoId]: err?.message ?? 'Falha ao excluir parecer.' }));
    } finally {
      setDeletingId(null);
    }
  };

  const renderPreview = (preview: any) => {
    if (!preview) {
      return <div className="revisoes__preview revisoes__preview--empty">Conteúdo do alvo não encontrado.</div>;
    }
    if (preview.type === 'resposta') {
      const resposta = respostasById.get(preview.id);
      const perguntaTexto = resposta?.pergunta_texto;
      return (
        <div className="revisoes__preview">
          <div className="revisoes__preview-meta">
            <span>Resposta #{preview.id}</span>
            {preview.tarefa && <span>Trilha #{preview.tarefa}</span>}
            {preview.pergunta_ordem && <span>Missão {preview.pergunta_ordem}</span>}
            {preview.gt_nome && <span>GT: {preview.gt_nome}</span>}
          </div>
          {perguntaTexto && (
            <div
              className="revisoes__preview-body"
              dangerouslySetInnerHTML={{ __html: perguntaTexto }}
            />
          )}
          <div
            className="revisoes__preview-body"
            dangerouslySetInnerHTML={{ __html: preview.conteudo_html || '<p>Sem conteúdo.</p>' }}
          />
        </div>
      );
    }
    if (preview.type === 'texto_unico') {
      return (
        <div className="revisoes__preview">
          <div className="revisoes__preview-meta">
            <span>Texto único #{preview.id}</span>
            {preview.tarefa && <span>Trilha #{preview.tarefa}</span>}
            {preview.gt_nome && <span>GT: {preview.gt_nome}</span>}
          </div>
          <div
            className="revisoes__preview-body"
            dangerouslySetInnerHTML={{ __html: preview.conteudo_html || '<p>Sem conteúdo.</p>' }}
          />
        </div>
      );
    }
    return (
      <div className="revisoes__preview">
        <div className="revisoes__preview-meta">
          <span>Quadro #{preview.id}</span>
          {preview.template && <span>Template: {preview.template}</span>}
          {preview.gt_nome && <span>GT: {preview.gt_nome}</span>}
        </div>
      </div>
    );
  };

  if (isLoading && !revisoes) {
    return <FullPageLoader message="Carregando revisões..." />;
  }

  return (
    <div className="revisoes">
      <header className="revisoes__header">
        <div>
          <h1>Revisões</h1>
          <p>Acompanhe solicitações de revisão e atualize pareceres de forma centralizada.</p>
        </div>
      </header>

      <PageInstructions
        title="Fluxo recomendado"
        description="Aprove revisões com rastreabilidade, mantendo registros alinhados com o GT."
        items={[
          {
            title: 'Filtre por alvo',
            description: 'Busque revisões vinculadas a uma resposta ou texto único para acompanhar o contexto.',
          },
          {
            title: 'Atualize pareceres',
            description: 'Comunique o status da análise e registre comentários em HTML — o cliente visualiza e pode corrigir.',
          },
          {
            title: 'Evite conflitos de ETag',
            description: 'Após atualizar, recarregue a lista para garantir que está trabalhando na versão mais recente.',
          },
        ]}
      />

      <section className="revisoes__respostas revisoes__panel">
        <header className="revisoes__respostas-header">
          <div>
            <h2>Respostas para revisão</h2>
            <p>Edite a resposta e publique um parecer — o cliente verá as duas coisas na tela dele.</p>
          </div>
          <div className="revisoes__respostas-actions">
            <label>
              <span>Filtrar por GT</span>
              <select value={gtFiltro === '' ? '' : String(gtFiltro)} onChange={(e) => setGtFiltro(e.target.value ? Number(e.target.value) : '')}>
                <option value="">Todos</option>
                {gtOptions.map((gt) => (
                  <option key={gt.id} value={gt.id}>
                    {gt.displayName}
                  </option>
                ))}
              </select>
            </label>
            <label className="revisoes__filters-inline">
              <span>Busca em missão ou conteúdo</span>
              <input
                type="search"
                value={buscaConteudo}
                onChange={(e) => setBuscaConteudo(e.target.value)}
                placeholder="Palavra-chave da missão ou da resposta"
              />
            </label>
            <button
              type="button"
              className="revisoes__button revisoes__button--ghost"
              onClick={() => {
                refetchRespostas();
              }}
              disabled={respostasLoading}
            >
              {respostasLoading ? 'Atualizando...' : 'Atualizar lista'}
            </button>
          </div>
        </header>

        {((user?.role === 'articulador' && gtsLoading) || (respostasLoading && !respostas)) ? (
          <FullPageLoader message="Carregando respostas..." />
        ) : respostasFiltradas.length === 0 ? (
          <div className="revisoes__empty">
            <h3>Nenhuma resposta encontrada</h3>
            <p>Ajuste filtros ou aguarde novas respostas.</p>
          </div>
        ) : (
          <div className="revisoes__respostas-grid">
            {respostasFiltradas.map((resp) => (
              <article key={resp.id} className={`revisoes__resposta-card ${resp.id === modalRespostaId ? 'is-open' : ''}`}>
                <header>
                  <div>
                    <h3>{resp.gt_nome ?? `GT #${resp.gt}`}</h3>
                    <p className="revisoes__meta-line">
                      Missão {resp.pergunta_ordem ?? resp.pergunta} · Trilha {resp.tarefa_id ?? '—'}
                    </p>
                  </div>
                  <div className="revisoes__card-actions">
                    <span className="revisoes__badge">Atualizado {new Date(resp.updated_at).toLocaleString('pt-BR')}</span>
                    <button
                      type="button"
                      className="revisoes__button revisoes__button--ghost"
                      onClick={() => setModalRespostaId(resp.id)}
                    >
                      Expandir
                    </button>
                  </div>
                </header>
                <div className="revisoes__resposta-snippet">
                  <span>Prévia</span>
                  <p title="Clique em expandir para visualizar todo o conteúdo.">
                    {(resp.conteudo_html ?? '').replace(/<[^>]+>/g, ' ').trim().slice(0, 160) || 'Sem conteúdo.'}
                    {(resp.conteudo_html ?? '').replace(/<[^>]+>/g, ' ').trim().length > 160 ? '…' : ''}
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {revisoesOrdenadas.length > 0 ? (
        <div className="revisoes__lista">
          {revisoesOrdenadas.map((revisao) => (
            <article key={revisao.id} className="revisoes__card">
              <header>
                <div>
                  <h3>
                    Revisão #{revisao.id} — {revisao.alvo_tipo} #{revisao.alvo_id}
                  </h3>
                  <div className="revisoes__badge-row">
                    <span className="revisoes__badge">Status: {revisao.status}</span>
                    <span className="revisoes__badge revisoes__badge--cliente">Visível para o cliente</span>
                  </div>
                </div>
                <div className="revisoes__metas">
                  <span>Solicitante #{revisao.solicitante ?? '—'}</span>
                  <span>Revisor #{revisao.revisor ?? '—'}</span>
                  <span>Atualizado {new Date(revisao.updated_at).toLocaleString('pt-BR')}</span>
                  <span>ETag: {revisao.etag}</span>
                </div>
              </header>

              {renderPreview(revisao.alvo_preview)}

              <details>
                <summary>Parecer atual</summary>
                <div dangerouslySetInnerHTML={{ __html: revisao.parecer_html ?? '<p>Sem parecer registrado.</p>' }} />
              </details>

              <div className="revisoes__editar">
                <label>
                  <span>Novo status</span>
                  <select
                    value={draftStatus[revisao.id] ?? revisao.status}
                    onChange={(event) => setDraftStatus((prev) => ({ ...prev, [revisao.id]: event.target.value }))}
                  >
                    {STATUS_OPTIONS.map((status) => (
                      <option key={status.value} value={status.value}>
                        {status.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="full">
                  <span>Atualizar parecer (HTML)</span>
                  <RichTextEditor
                    value={draftParecer[revisao.id] ?? revisao.parecer_html ?? ''}
                    onChange={(value) => setDraftParecer((prev) => ({ ...prev, [revisao.id]: value }))}
                    placeholder="Atualize o parecer."
                    className="revisoes__parecer-field"
                  />
                </label>
                <div className="revisoes__editar-actions">
                  <button
                    type="button"
                    className="revisoes__button"
                    onClick={() => handleAtualizar(revisao.id, revisao.etag)}
                    disabled={updateRevisao.isPending}
                  >
                    {updateRevisao.isPending ? 'Salvando...' : 'Salvar alterações'}
                  </button>
                  <button
                    type="button"
                    className="revisoes__button revisoes__button--ghost revisoes__button--danger"
                    onClick={() => handleExcluir(revisao.id)}
                    disabled={deletingId === revisao.id}
                  >
                    {deletingId === revisao.id ? 'Excluindo...' : 'Excluir parecer'}
                  </button>
                </div>
                {deleteFeedback[revisao.id] && (
                  <p className="revisoes__feedback">{deleteFeedback[revisao.id]}</p>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {respostaAtiva && (
        <div
          className="revisoes__modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="revisoes-modal-title"
          onClick={() => setModalRespostaId(null)}
        >
          <div className="revisoes__modal" onClick={(event) => event.stopPropagation()}>
            <header className="revisoes__modal-header">
              <div>
                <p className="revisoes__modal-eyebrow">GT {respostaAtiva.gt_nome ?? `#${respostaAtiva.gt}`}</p>
                <h3 id="revisoes-modal-title">
                  Missão {respostaAtiva.pergunta_ordem ?? respostaAtiva.pergunta} · Trilha{' '}
                  {respostaAtiva.tarefa_id ?? '—'}
                </h3>
                <div className="revisoes__badge-row">
                  <span className="revisoes__badge">Atualizado {new Date(respostaAtiva.updated_at).toLocaleString('pt-BR')}</span>
                  <span className="revisoes__badge revisoes__badge--cliente">ID #{respostaAtiva.id}</span>
                </div>
              </div>
              <button
                type="button"
                className="revisoes__button revisoes__button--ghost"
                onClick={() => setModalRespostaId(null)}
                aria-label="Fechar modal de resposta"
              >
                Fechar
              </button>
            </header>

            <div className="revisoes__modal-body">
              <div className="revisoes__modal-preview">
                {respostaAtiva.pergunta_texto && (
                  <div className="revisoes__preview-block">
                    <div className="revisoes__preview-meta">Missão</div>
                    <div
                      className="revisoes__preview-body"
                      dangerouslySetInnerHTML={{ __html: respostaAtiva.pergunta_texto }}
                    />
                  </div>
                )}
                <div className="revisoes__preview-block">
                  <div className="revisoes__preview-meta">Resposta</div>
                  <p className="revisoes__preview-body revisoes__preview-body--plain">
                    {htmlToPlainText(respostaAtiva.conteudo_html) || 'Sem conteúdo.'}
                  </p>
                </div>
              </div>

              <div className="revisoes__resposta-actions revisoes__resposta-actions--modal">
                <div className="revisoes__ia-actions">
                  <button
                    type="button"
                    className="revisoes__button revisoes__button--ghost"
                    onClick={async () => {
                      if (!respostaAtiva) return;
                      setIaFeedback(null);
                      try {
                        const response = await aiAssist.mutateAsync({
                          mode: 'review',
                          text: stripHtml(respostaAtiva.conteudo_html),
                          context: stripHtml(respostaAtiva.pergunta_texto),
                        });
                        setDraftParecerResposta((prev) => ({
                          ...prev,
                          [respostaAtiva.id]: response.output,
                        }));
                        setIaFeedback('Sugestao gerada. Revise antes de enviar.');
                      } catch (err: any) {
                        setIaFeedback('Não foi possível gerar o parecer com IA.');
                      }
                    }}
                    disabled={aiAssist.isPending}
                  >
                    {aiAssist.isPending ? 'IA em andamento...' : 'IA: sugerir parecer'}
                  </button>
                  {iaFeedback && <span className="revisoes__feedback">{iaFeedback}</span>}
                </div>
                <label className="full">
                  <span>Editar resposta (HTML)</span>
                  <RichTextEditor
                    value={draftConteudoResposta[respostaAtiva.id] ?? respostaAtiva.conteudo_html ?? ''}
                    onChange={(value) => setDraftConteudoResposta((prev) => ({ ...prev, [respostaAtiva.id]: value }))}
                    placeholder="Ajuste a resposta antes de enviar revisão."
                  />
                </label>
                <div className="revisoes__modal-buttons">
                  <button
                    type="button"
                    className="revisoes__button revisoes__button--secondary"
                    onClick={async () => {
                      try {
                        await client.put(`/respostas/${respostaAtiva.id}`, {
                          body: {
                            gt: respostaAtiva.gt,
                            pergunta: respostaAtiva.pergunta,
                            conteudo_html: draftConteudoResposta[respostaAtiva.id] ?? respostaAtiva.conteudo_html ?? '',
                          },
                          ifMatch: respostaAtiva.etag,
                        });
                        setFeedbackResposta((prev) => ({ ...prev, [respostaAtiva.id]: 'Resposta atualizada para o cliente.' }));
                        refetchRespostas();
                      } catch (err: any) {
                        setFeedbackResposta((prev) => ({ ...prev, [respostaAtiva.id]: err?.message ?? 'Falha ao salvar resposta.' }));
                      }
                    }}
                  >
                    Salvar resposta
                  </button>
                  <button
                    type="button"
                    className="revisoes__button"
                    onClick={async () => {
                      try {
                        await createRevisao.mutateAsync({
                          alvoTipo: 'resposta',
                          alvoId: respostaAtiva.id,
                          parecerHtml: (draftParecerResposta[respostaAtiva.id] ?? '').trim() || undefined,
                          status: 'em_revisao',
                        });
                        setFeedbackResposta((prev) => ({ ...prev, [respostaAtiva.id]: 'Revisão criada e visível para o cliente.' }));
                        setDraftParecerResposta((prev) => {
                          const next = { ...prev };
                          delete next[respostaAtiva.id];
                          return next;
                        });
                        refetch();
                      } catch (err: any) {
                        setFeedbackResposta((prev) => ({ ...prev, [respostaAtiva.id]: err?.message ?? 'Falha ao criar revisão.' }));
                      }
                    }}
                    disabled={createRevisao.isPending}
                  >
                    {createRevisao.isPending ? 'Enviando...' : 'Criar revisão'}
                  </button>
                </div>
                <label className="full">
                  <span>Parecer para o cliente (HTML)</span>
                  <RichTextEditor
                    value={draftParecerResposta[respostaAtiva.id] ?? ''}
                    onChange={(value) => setDraftParecerResposta((prev) => ({ ...prev, [respostaAtiva.id]: value }))}
                    placeholder="Explique o ajuste esperado; o cliente verá este comentário."
                    className="revisoes__parecer-field"
                  />
                </label>
                {feedbackResposta[respostaAtiva.id] && (
                  <p className="revisoes__feedback">{feedbackResposta[respostaAtiva.id]}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
