import { FormEvent, useMemo, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useComentarios, useCreateComentario, useUpdateComentario } from '@/hooks/useComentarios';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';

import './ComentariosPage.css';

const COMMENT_TARGETS = [
  { value: 'resposta', label: 'Resposta' },
  { value: 'texto_unico', label: 'Texto único' },
  { value: 'quadro', label: 'Quadro' },
];

export function ComentariosPage() {
  const [alvoTipoFiltro, setAlvoTipoFiltro] = useState('');
  const [alvoIdFiltro, setAlvoIdFiltro] = useState('');
  const [mostrarResolvidos, setMostrarResolvidos] = useState<'todos' | 'abertos' | 'fechados'>('todos');

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

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const alvoTipo = String(form.get('alvoTipo') ?? '').trim();
    const alvoId = Number(form.get('alvoId'));
    const conteudo = String(form.get('conteudo') ?? '').trim();
    const anchor = String(form.get('anchor') ?? '').trim();
    const mentions = String(form.get('mentions') ?? '')
      .split(',')
      .map((value) => Number(value.trim()))
      .filter((value) => Number.isFinite(value));
    if (!alvoTipo || !alvoId || !conteudo) {
      return;
    }
    await criarComentario.mutateAsync({
      alvoTipo,
      alvoId,
      conteudoHtml: conteudo,
      anchorJson: anchor || undefined,
      mentions: mentions.length > 0 ? mentions : undefined,
    });
    refetch();
    event.currentTarget.reset();
  };

  const handleAtualizar = async (comentarioId: number, etag: string) => {
    const conteudo = draftConteudo[comentarioId];
    const resolvido = draftResolvido[comentarioId];
    await atualizarComentario.mutateAsync({
      comentarioId,
      payload: {
        conteudo_html: conteudo,
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
            <span>Alvo tipo</span>
            <select name="alvoTipo" required defaultValue="resposta">
              {COMMENT_TARGETS.map((target) => (
                <option key={target.value} value={target.value}>
                  {target.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Alvo ID</span>
            <input name="alvoId" type="number" min={1} placeholder="Ex.: 120" required />
          </label>
          <label>
            <span>Mentions (IDs separados por vírgula)</span>
            <input name="mentions" type="text" placeholder="Ex.: 3, 18" />
          </label>
          <label className="full">
            <span>Anchor JSON (opcional)</span>
            <textarea name="anchor" rows={3} placeholder='{"paragraph":2}' />
          </label>
          <label className="full">
            <span>Conteúdo em HTML</span>
            <textarea name="conteudo" rows={4} placeholder="Descreva o ajuste sugerido" required />
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
