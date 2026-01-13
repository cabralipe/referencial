import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useRespostas } from '@/hooks/useRespostas';
import { useDeleteRevisao, useRevisoes, useUpdateRevisao } from '@/hooks/useRevisoes';
import { useAuth } from '@/context/AuthContext';
import type { Resposta, Revisao } from '@/api/types';

import './PareceresPage.css';

const STATUS_LABELS: Record<string, string> = {
  rascunho: 'Rascunho',
  em_revisao: 'Em revisão',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
};

const stripHtml = (html?: string | null) => {
  if (!html) return '';
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
};

const htmlToPlainText = (html?: string | null) => {
  if (!html) return '';
  const normalized = html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n');
  return normalized
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n\s+/g, '\n')
    .trim();
};

const toNumberId = (value: number | string | null | undefined) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

export function PareceresPage() {
  const { user } = useAuth();
  const isRedator = user?.role === 'articulador';
  const isMembroGt = user?.role === 'membro_gt';
  const [gtFiltro, setGtFiltro] = useState<number | ''>('');
  const [buscaConteudo, setBuscaConteudo] = useState('');
  const [draftParecer, setDraftParecer] = useState<Record<number, string>>({});
  const [feedbackParecer, setFeedbackParecer] = useState<Record<number, string>>({});
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const { gtOptions, isLoading: gtsLoading } = useAvailableGts();
  const { data: respostas, isLoading: respostasLoading, refetch: refetchRespostas } = useRespostas({ includeAll: true });
  const { data: revisoes, isLoading: revisoesLoading, refetch: refetchRevisoes } = useRevisoes({
    alvoTipo: 'resposta',
    pageSize: 500,
  });
  const updateRevisao = useUpdateRevisao();
  const deleteRevisao = useDeleteRevisao();

  const gtsPermitidos = useMemo(() => new Set(gtOptions.map((gt) => gt.id)), [gtOptions]);

  const respostasBase = useMemo(() => {
    if (!respostas || !user) return [];
    if (isRedator) {
      return respostas.filter((resp) => gtsPermitidos.has(resp.gt));
    }
    if (isMembroGt) return respostas.filter((resp) => resp.autor === user.id);
    return [];
  }, [gtsPermitidos, isRedator, isMembroGt, respostas, user]);

  const respostasFiltradas = useMemo(() => {
    const term = buscaConteudo.trim().toLowerCase();
    return respostasBase.filter((resp) => {
      if (gtFiltro && resp.gt !== gtFiltro) return false;
      if (!term) return true;
      const textoPergunta = (resp.pergunta_texto || '').toLowerCase();
      const textoConteudo = stripHtml(resp.conteudo_html).toLowerCase();
      return textoPergunta.includes(term) || textoConteudo.includes(term);
    });
  }, [buscaConteudo, gtFiltro, respostasBase]);

  const respostasById = useMemo(() => {
    return new Map(respostasBase.map((resp) => [resp.id, resp]));
  }, [respostasBase]);

  const respostaIdsFiltradas = useMemo(
    () => new Set(respostasFiltradas.map((resp) => resp.id)),
    [respostasFiltradas],
  );

  const pareceresFiltrados = useMemo(() => {
    if (!revisoes) return [];
    let filtradas = revisoes.filter((rev) => {
      if (rev.alvo_tipo !== 'resposta') return false;
      const alvoId = toNumberId(rev.alvo_id);
      if (alvoId === null) return false;
      return respostaIdsFiltradas.has(alvoId);
    });
    if (isRedator && user) {
      filtradas = filtradas.filter((rev) => rev.revisor === user.id || rev.solicitante === user.id);
    }
    return filtradas
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [isRedator, revisoes, respostaIdsFiltradas, user]);

  const handleAtualizarParecer = async (revisao: Revisao) => {
    const valor = draftParecer[revisao.id];
    if (valor === undefined) return;
    setFeedbackParecer((prev) => ({ ...prev, [revisao.id]: '' }));
    try {
      await updateRevisao.mutateAsync({
        revisaoId: revisao.id,
        payload: { parecer_html: valor },
        etag: revisao.etag,
      });
      setFeedbackParecer((prev) => ({ ...prev, [revisao.id]: 'Parecer atualizado com sucesso.' }));
      setDraftParecer((prev) => {
        const next = { ...prev };
        delete next[revisao.id];
        return next;
      });
      refetchRevisoes();
    } catch (err: any) {
      setFeedbackParecer((prev) => ({ ...prev, [revisao.id]: err?.message ?? 'Falha ao atualizar parecer.' }));
    }
  };

  const handleExcluirParecer = async (revisaoId: number) => {
    const confirmacao = window.confirm('Excluir este parecer? Esta ação não pode ser desfeita.');
    if (!confirmacao) return;
    setDeletingId(revisaoId);
    setFeedbackParecer((prev) => ({ ...prev, [revisaoId]: '' }));
    try {
      await deleteRevisao.mutateAsync({ revisaoId });
      setFeedbackParecer((prev) => ({ ...prev, [revisaoId]: 'Parecer excluído com sucesso.' }));
      refetchRevisoes();
    } catch (err: any) {
      setFeedbackParecer((prev) => ({ ...prev, [revisaoId]: err?.message ?? 'Falha ao excluir parecer.' }));
    } finally {
      setDeletingId(null);
    }
  };

  if (!user) {
    return <FullPageLoader message="Carregando pareceres..." />;
  }

  if (gtsLoading || respostasLoading || revisoesLoading) {
    return <FullPageLoader message="Carregando pareceres..." />;
  }

  if (!isMembroGt && !isRedator) {
    return (
      <div className="pareceres">
        <header className="pareceres__header">
          <div>
            <h1>Pareceres</h1>
            <p>Esta tela está disponível apenas para membros de GT e redatores.</p>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className="pareceres">
      <header className="pareceres__header">
        <div>
          <h1>Pareceres</h1>
          <p>
            {isRedator
              ? 'Acompanhe os pareceres que você publicou e os ajustes solicitados.'
              : 'Veja os pareceres enviados para as suas respostas e acompanhe os ajustes solicitados.'}
          </p>
        </div>
        <button
          type="button"
          className="pareceres__button"
          onClick={() => {
            refetchRespostas();
            refetchRevisoes();
          }}
        >
          Atualizar pareceres
        </button>
      </header>

      <PageInstructions
        title="Como usar"
        description={
          isRedator
            ? 'Organize seus pareceres por GT e encontre rapidamente as missões revisadas.'
            : 'Organize seus pareceres por GT e encontre rapidamente as missões que precisam de ajuste.'
        }
        items={[
          {
            title: 'Use os filtros',
            description: 'Filtre por GT e palavra-chave para localizar a missão correta.',
          },
          {
            title: isRedator ? 'Revise seu parecer' : 'Leia o parecer',
            description: isRedator
              ? 'O texto destacado abaixo mostra o parecer que você publicou.'
              : 'O texto destacado abaixo mostra o feedback do redator para sua resposta.',
          },
          {
            title: 'Volte para a trilha',
            description: isRedator
              ? 'Abra a trilha para revisar a missão quando precisar atualizar o parecer.'
              : 'Abra a trilha para revisar a missão e aplicar os ajustes solicitados.',
          },
        ]}
      />

      <section className="pareceres__filters">
        <label>
          <span>Filtrar por GT</span>
          <select
            value={gtFiltro === '' ? '' : String(gtFiltro)}
            onChange={(e) => setGtFiltro(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">Todos</option>
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>
        <label className="pareceres__filters-search">
          <span>Busca em missão ou resposta</span>
          <input
            type="search"
            value={buscaConteudo}
            onChange={(e) => setBuscaConteudo(e.target.value)}
            placeholder="Palavra-chave da missão ou do texto"
          />
        </label>
      </section>

      {pareceresFiltrados.length > 0 ? (
        <div className="pareceres__list">
          {pareceresFiltrados.map((rev) => {
            const alvoId = toNumberId(rev.alvo_id);
            const resposta = alvoId === null ? undefined : respostasById.get(alvoId);
            const preview = rev.alvo_preview as Revisao['alvo_preview'];
            const gtNome = resposta?.gt_nome ?? (preview && 'gt_nome' in preview ? preview.gt_nome : null);
            const tarefaId = resposta?.tarefa_id ?? (preview && 'tarefa' in preview ? preview.tarefa : null);
            const gtId = resposta?.gt ?? (preview && 'gt' in preview ? preview.gt : null);
            const linkTo = tarefaId && gtId ? `/tarefas/${tarefaId}?gt=${gtId}` : null;
            const statusLabel = STATUS_LABELS[rev.status] ?? rev.status;
            const canEdit = isRedator && user && (rev.revisor === user.id || rev.solicitante === user.id);

            return (
              <article key={rev.id} className="pareceres__card">
                <header className="pareceres__card-header">
                  <div>
                    <h2>Parecer #{rev.id}</h2>
                    <p>
                      {gtNome ? `${gtNome} · ` : ''}
                      Missão {resposta?.pergunta_ordem ?? resposta?.pergunta ?? '—'} · Trilha {tarefaId ?? '—'}
                    </p>
                  </div>
                  <div className="pareceres__card-meta">
                    <span className="pareceres__badge">Status: {statusLabel}</span>
                    <span className="pareceres__badge">Atualizado {new Date(rev.updated_at).toLocaleString('pt-BR')}</span>
                    {linkTo && (
                      <Link to={linkTo} className="pareceres__button pareceres__button--ghost">
                        Abrir trilha
                      </Link>
                    )}
                  </div>
                </header>

                {resposta?.pergunta_texto && (
                  <div className="pareceres__preview">
                    <div className="pareceres__preview-label">Missão</div>
                    <div
                      className="pareceres__preview-body"
                      dangerouslySetInnerHTML={{ __html: resposta.pergunta_texto }}
                    />
                  </div>
                )}

                <div className="pareceres__preview">
                  <div className="pareceres__preview-label">{isRedator ? 'Resposta revisada' : 'Sua resposta'}</div>
                  <p className="pareceres__preview-body pareceres__preview-body--plain">
                    {htmlToPlainText(resposta?.conteudo_html) || 'Sem conteúdo.'}
                  </p>
                </div>

                <div className="pareceres__parecer">
                  <div className="pareceres__preview-label">{isRedator ? 'Seu parecer' : 'Parecer do redator'}</div>
                  <div
                    className="pareceres__parecer-body"
                    dangerouslySetInnerHTML={{ __html: rev.parecer_html || '<p>Sem parecer registrado.</p>' }}
                  />
                </div>
                {canEdit && (
                  <div className="pareceres__edit">
                    <span className="pareceres__preview-label">Editar parecer (HTML)</span>
                    <textarea
                      className="pareceres__parecer-field"
                      value={draftParecer[rev.id] ?? rev.parecer_html ?? ''}
                      onChange={(event) =>
                        setDraftParecer((prev) => ({ ...prev, [rev.id]: event.target.value }))
                      }
                      rows={6}
                    />
                    <div className="pareceres__actions">
                      <button type="button" className="pareceres__button" onClick={() => handleAtualizarParecer(rev)}>
                        {updateRevisao.isPending ? 'Salvando...' : 'Salvar parecer'}
                      </button>
                      <button
                        type="button"
                        className="pareceres__button pareceres__button--ghost"
                        onClick={() => handleExcluirParecer(rev.id)}
                        disabled={deletingId === rev.id}
                      >
                        {deletingId === rev.id ? 'Excluindo...' : 'Excluir parecer'}
                      </button>
                      {feedbackParecer[rev.id] && (
                        <span className="pareceres__feedback">{feedbackParecer[rev.id]}</span>
                      )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <div className="pareceres__empty">
          <h2>Nenhum parecer encontrado</h2>
          <p>
            {isRedator
              ? 'Assim que você publicar um parecer, ele aparecerá aqui.'
              : 'Assim que o redator publicar um parecer, ele aparecerá aqui para você.'}
          </p>
        </div>
      )}
    </div>
  );
}
