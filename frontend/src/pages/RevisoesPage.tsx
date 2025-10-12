import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateRevisao, useRevisoes, useUpdateRevisao } from '@/hooks/useRevisoes';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';

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
  const [alvoIdFiltro, setAlvoIdFiltro] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');

  const alvoIdFiltroNumber = alvoIdFiltro ? Number(alvoIdFiltro) : undefined;

  const { data: revisoes, isLoading, refetch } = useRevisoes({
    alvoTipo: alvoTipoFiltro || undefined,
    alvoId: alvoIdFiltroNumber,
    status: statusFiltro || undefined,
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

  const revisoesOrdenadas = useMemo(() => {
    if (!revisoes) return [];
    return revisoes.slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [revisoes]);

  const handleSubmitNovaRevisao = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const alvoTipo = String(form.get('alvoTipo') ?? '').trim();
    const alvoId = Number(form.get('alvoId'));
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
            description: 'Busque revisões vinculadas a uma tarefa, texto único ou outro identificador.',
          },
          {
            title: 'Atualize pareceres',
            description: 'Comunique o status da análise e registre comentários em HTML para orientar o time.',
          },
          {
            title: 'Evite conflitos de ETag',
            description: 'Após atualizar, recarregue a lista para garantir que está trabalhando na versão mais recente.',
          },
        ]}
      />

      <div className="revisoes__filters">
        <label>
          <span>Alvo tipo</span>
          <select value={alvoTipoFiltro} onChange={(event) => setAlvoTipoFiltro(event.target.value)}>
            <option value="">Todos</option>
            {ALVO_TIPOS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
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
          <select value={statusFiltro} onChange={(event) => setStatusFiltro(event.target.value)}>
            <option value="">Todos</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="ghost" onClick={() => refetch()}>
          Recarregar
        </button>
      </div>

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
            <span>Alvo ID</span>
            <input name="alvoId" type="number" min={1} placeholder="Ex.: 42" required />
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
                  <span>Status atual: {revisao.status}</span>
                </div>
                <div className="revisoes__metas">
                  <span>Solicitante #{revisao.solicitante ?? '—'}</span>
                  <span>Revisor #{revisao.revisor ?? '—'}</span>
                  <span>Atualizado {new Date(revisao.updated_at).toLocaleString('pt-BR')}</span>
                  <span>ETag: {revisao.etag}</span>
                </div>
              </header>

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
