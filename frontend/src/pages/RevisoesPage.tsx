import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateRevisao, useRevisoes, useUpdateRevisao } from '@/hooks/useRevisoes';
import { useRespostas } from '@/hooks/useRespostas';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';
import { useApiClient } from '@/api/client';

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
  const [alvoTipoFiltro, setAlvoTipoFiltro] = useState('');
  const [alvoIdFiltroInput, setAlvoIdFiltroInput] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');
  const [gtFiltro, setGtFiltro] = useState<number | ''>('');
  const [buscaConteudo, setBuscaConteudo] = useState('');

  const parseNumericId = (value: string): number | undefined => {
    if (!value) return undefined;
    const match = value.match(/(\d+)(?!.*\d)/);
    if (!match) return undefined;
    const num = Number(match[1]);
    return Number.isFinite(num) ? num : undefined;
  };

  const alvoIdFiltroNumber = parseNumericId(alvoIdFiltroInput);
  const isResposta = alvoTipoFiltro === 'resposta';
  const isTextoUnico = alvoTipoFiltro === 'texto_unico';

  const { data: revisoes, isLoading, refetch } = useRevisoes({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltroNumber,
    status: statusFiltro || undefined,
  });
  const { gtOptions } = useAvailableGts({ scope: 'all' });
  const { data: respostas, isLoading: respostasLoading, refetch: refetchRespostas } = useRespostas({
    includeAll: true,
  });

  useStreamSubscription({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltroNumber,
    enabled: Boolean(alvoTipoFiltro && alvoIdFiltroNumber),
    onMessage: () => {
      refetch();
    },
  });
  const createRevisao = useCreateRevisao();
  const updateRevisao = useUpdateRevisao();

  const [draftParecer, setDraftParecer] = useState<Record<number, string>>({});
  const [draftStatus, setDraftStatus] = useState<Record<number, string>>({});
  const [draftParecerResposta, setDraftParecerResposta] = useState<Record<number, string>>({});
  const [feedbackResposta, setFeedbackResposta] = useState<Record<number, string>>({});
  const [draftConteudoResposta, setDraftConteudoResposta] = useState<Record<number, string>>({});
  const [expandedCards, setExpandedCards] = useState<Record<number, boolean>>({});
  const client = useApiClient();

  const revisoesOrdenadas = useMemo(() => {
    if (!revisoes) return [];
    return revisoes.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [revisoes]);

  const respostasFiltradas = useMemo(() => {
    if (!respostas) return [];
    const term = buscaConteudo.trim().toLowerCase();
    return respostas
      .filter((resp) => {
        if (gtFiltro && resp.gt !== gtFiltro) return false;
        if (!term) return true;
        const textoPergunta = (resp.pergunta_texto || '').toLowerCase();
        const textoConteudo = (resp.conteudo_html || '').replace(/<[^>]+>/g, ' ').toLowerCase();
        return textoPergunta.includes(term) || textoConteudo.includes(term);
      })
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 50);
  }, [buscaConteudo, gtFiltro, respostas]);

  const toggleCard = (id: number) => {
    setExpandedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSubmitNovaRevisao = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const alvoTipo = String(form.get('alvoTipo') ?? '').trim();
    const alvoIdValue = String(form.get('alvoId') ?? '');
    const alvoId = parseNumericId(alvoIdValue);
    const parecer = String(form.get('parecer') ?? '');
    const revisor = form.get('revisor') ? Number(form.get('revisor')) : undefined;
    if (!alvoTipo || !alvoId) {
      return;
    }
    await createRevisao.mutateAsync({ alvoTipo, alvoId, parecerHtml: parecer || undefined, revisor });
    refetch();
    event.currentTarget.reset();
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

  const renderPreview = (preview: any) => {
    if (!preview) {
      return <div className="revisoes__preview revisoes__preview--empty">Conteúdo do alvo não encontrado.</div>;
    }
    if (preview.type === 'resposta') {
      return (
        <div className="revisoes__preview">
          <div className="revisoes__preview-meta">
            <span>Resposta #{preview.id}</span>
            {preview.tarefa && <span>Tarefa #{preview.tarefa}</span>}
            {preview.pergunta_ordem && <span>Pergunta {preview.pergunta_ordem}</span>}
            {preview.gt_nome && <span>GT: {preview.gt_nome}</span>}
          </div>
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
            {preview.tarefa && <span>Tarefa #{preview.tarefa}</span>}
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

      <div className="revisoes__filters revisoes__panel">
        <div className="revisoes__filters-header">
          <div>
            <h2>Filtrar revisões</h2>
            <p>Refine por alvo, status ou cole uma URL/ID para ir direto ao ponto.</p>
          </div>
          <button type="button" className="ghost" onClick={() => refetch()}>
            Recarregar
          </button>
        </div>
        <div className="revisoes__filters-grid">
          <label>
            <span>Alvo</span>
            <select value={alvoTipoFiltro} onChange={(event) => setAlvoTipoFiltro(event.target.value)}>
              <option value="">Todos</option>
              {ALVO_TIPOS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="revisoes__filters-inline">
            <span>Selecione {isResposta ? 'a resposta' : isTextoUnico ? 'o texto único' : 'o registro'}</span>
            <div className="revisoes__filters-composite">
              <input
                type="text"
                value={alvoIdFiltroInput}
                onChange={(event) => setAlvoIdFiltroInput(event.target.value)}
                placeholder={
                  isResposta
                    ? 'Cole a URL ou ID da resposta'
                    : isTextoUnico
                      ? 'Cole a URL ou ID do texto único'
                      : 'Cole a URL ou ID'
                }
              />
              <button
                type="button"
                className="ghost"
                onClick={() => refetch()}
                disabled={isLoading}
                aria-label="Aplicar filtro de alvo"
              >
                Filtrar
              </button>
            </div>
            <small className="revisoes__hint">
              Dica: cole a URL ou ID copiado da página de tarefa/texto único — extraímos o número automaticamente.
            </small>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFiltro} onChange={(event) => setStatusFiltro(event.target.value)}>
              <option value="">Todos</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

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
              <span>Busca em pergunta ou conteúdo</span>
              <input
                type="search"
                value={buscaConteudo}
                onChange={(e) => setBuscaConteudo(e.target.value)}
                placeholder="Palavra-chave da pergunta ou da resposta"
              />
            </label>
            <button type="button" className="ghost" onClick={() => { refetchRespostas(); }} disabled={respostasLoading}>
              {respostasLoading ? 'Atualizando...' : 'Atualizar lista'}
            </button>
          </div>
        </header>

        {respostasLoading && !respostas ? (
          <FullPageLoader message="Carregando respostas..." />
        ) : respostasFiltradas.length === 0 ? (
          <div className="revisoes__empty">
            <h3>Nenhuma resposta encontrada</h3>
            <p>Ajuste filtros ou aguarde novas respostas.</p>
          </div>
        ) : (
          <div className="revisoes__respostas-grid">
            {respostasFiltradas.map((resp) => (
              <article key={resp.id} className={`revisoes__resposta-card ${expandedCards[resp.id] ? 'is-open' : ''}`}>
                <header>
                  <div>
                    <h3>{resp.gt_nome ?? `GT #${resp.gt}`}</h3>
                    <p className="revisoes__meta-line">
                      Pergunta {resp.pergunta_ordem ?? resp.pergunta} · Tarefa {resp.tarefa_id ?? '—'}
                    </p>
                  </div>
                  <div className="revisoes__card-actions">
                    <span className="revisoes__badge">Atualizado {new Date(resp.updated_at).toLocaleString('pt-BR')}</span>
                    <button type="button" className="ghost" onClick={() => toggleCard(resp.id)}>
                      {expandedCards[resp.id] ? 'Recolher' : 'Expandir'}
                    </button>
                  </div>
                </header>

                {expandedCards[resp.id] && (
                  <div className="revisoes__card-body">
                    <div className="revisoes__preview revisoes__preview--card">
                      {resp.pergunta_texto && (
                        <div className="revisoes__preview-block">
                          <div className="revisoes__preview-meta">Pergunta</div>
                          <div
                            className="revisoes__preview-body"
                            dangerouslySetInnerHTML={{ __html: resp.pergunta_texto }}
                          />
                        </div>
                      )}
                      <div className="revisoes__preview-block">
                        <div className="revisoes__preview-meta">Resposta</div>
                        <div
                          className="revisoes__preview-body"
                          dangerouslySetInnerHTML={{ __html: resp.conteudo_html || '<p>Sem conteúdo.</p>' }}
                        />
                      </div>
                    </div>

                    <div className="revisoes__resposta-actions">
                      <label className="full">
                        <span>Editar resposta (HTML)</span>
                        <textarea
                          rows={4}
                          value={draftConteudoResposta[resp.id] ?? resp.conteudo_html ?? ''}
                          onChange={(e) => setDraftConteudoResposta((prev) => ({ ...prev, [resp.id]: e.target.value }))}
                          placeholder="Ajuste a resposta antes de enviar revisão."
                        />
                      </label>
                      <button
                        type="button"
                        className="secondary"
                        onClick={async () => {
                          try {
                            await client.put(`/respostas/${resp.id}`, {
                              body: {
                                gt: resp.gt,
                                pergunta: resp.pergunta,
                                conteudo_html: draftConteudoResposta[resp.id] ?? resp.conteudo_html ?? '',
                              },
                              ifMatch: resp.etag,
                            });
                            setFeedbackResposta((prev) => ({ ...prev, [resp.id]: 'Resposta atualizada para o cliente.' }));
                            refetchRespostas();
                          } catch (err: any) {
                            setFeedbackResposta((prev) => ({ ...prev, [resp.id]: err?.message ?? 'Falha ao salvar resposta.' }));
                          }
                        }}
                      >
                        Salvar resposta
                      </button>
                      <label className="full">
                        <span>Parecer para o cliente (HTML)</span>
                        <textarea
                          rows={3}
                          value={draftParecerResposta[resp.id] ?? ''}
                          onChange={(e) => setDraftParecerResposta((prev) => ({ ...prev, [resp.id]: e.target.value }))}
                          placeholder="Explique o ajuste esperado; o cliente verá este comentário."
                        />
                      </label>
                      <button
                        type="button"
                        onClick={async () => {
                          try {
                            await createRevisao.mutateAsync({
                              alvoTipo: 'resposta',
                              alvoId: resp.id,
                              parecerHtml: (draftParecerResposta[resp.id] ?? '').trim() || undefined,
                            });
                            setFeedbackResposta((prev) => ({ ...prev, [resp.id]: 'Revisão criada e visível para o cliente.' }));
                            setDraftParecerResposta((prev) => {
                              const next = { ...prev };
                              delete next[resp.id];
                              return next;
                            });
                            refetch();
                          } catch (err: any) {
                            setFeedbackResposta((prev) => ({ ...prev, [resp.id]: err?.message ?? 'Falha ao criar revisão.' }));
                          }
                        }}
                        disabled={createRevisao.isPending}
                      >
                        {createRevisao.isPending ? 'Enviando...' : 'Criar revisão'}
                      </button>
                      {feedbackResposta[resp.id] && <p className="revisoes__feedback">{feedbackResposta[resp.id]}</p>}
                    </div>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="revisoes__nova">
        <h2>Solicitar nova revisão</h2>
        <form onSubmit={handleSubmitNovaRevisao}>
          <label>
            <span>Alvo tipo</span>
            <select name="alvoTipo" required defaultValue="resposta">
              {ALVO_TIPOS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>URL ou ID do alvo</span>
            <input name="alvoId" type="text" placeholder="Cole a URL ou o ID" required />
            </label>
          <label>
            <span>Revisor (opcional)</span>
            <input name="revisor" type="number" min={1} placeholder="ID do revisor" />
          </label>
          <label className="full">
            <span>Parecer inicial (HTML)</span>
            <textarea name="parecer" rows={4} placeholder="Contexto da revisão" />
          </label>
          <button type="submit" disabled={createRevisao.isPending}>
            {createRevisao.isPending ? 'Enviando...' : 'Solicitar revisão'}
          </button>
        </form>
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
                  <textarea
                    rows={4}
                    value={draftParecer[revisao.id] ?? revisao.parecer_html ?? ''}
                    onChange={(event) => setDraftParecer((prev) => ({ ...prev, [revisao.id]: event.target.value }))}
                  />
                </label>
                <button type="button" onClick={() => handleAtualizar(revisao.id, revisao.etag)} disabled={updateRevisao.isPending}>
                  {updateRevisao.isPending ? 'Salvando...' : 'Salvar alterações'}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="revisoes__empty">
          <h3>Nenhuma revisão encontrada</h3>
          <p>Ajuste os filtros ou solicite uma nova revisão para começar.</p>
        </div>
      )}
    </div>
  );
}
