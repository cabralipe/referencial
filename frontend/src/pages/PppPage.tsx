import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { ApiError, useApiClient } from '@/api/client';
import type { Comentario, Escola, PaginatedResponse } from '@/api/types';
import { Button } from '@/components/common/Button';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAuth } from '@/context/AuthContext';
import { useComentarios, useCreateComentario, useUpdateComentario } from '@/hooks/useComentarios';
import { useConcludePpp, usePppDocumento, usePppOverview, useUpdatePppConteudo } from '@/hooks/usePpp';
import { useStreamSubscription } from '@/hooks/useStreamSubscription';
import './PppPage.css';

type PppPageProps = {
  adminMode?: boolean;
};

const STATUS_LABELS: Record<string, string> = {
  em_elaboracao: 'Em elaboração',
  concluido: 'Concluído',
};

const STATUS_CLASSES: Record<string, string> = {
  em_elaboracao: 'bg-[rgba(245,158,11,0.12)] text-[var(--color-warning)]',
  concluido: 'bg-[rgba(22,163,74,0.12)] text-[var(--color-success)]',
};

const COMMENT_ACTION_BUTTON_STYLE = {
  backgroundColor: '#dbeafe',
  color: '#1d4ed8',
  border: '1px solid #93c5fd',
};

function formatDateTime(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
}

function ensureHtml(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return '';
  if (/<\/?[a-z][\s\S]*>/i.test(trimmed)) {
    return trimmed;
  }
  return `<p>${trimmed.replace(/\n/g, '<br />')}</p>`;
}

function formatCommentReference(anchor: unknown) {
  if (!anchor) return '';

  let parsed = anchor;
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed);
    } catch {
      return parsed;
    }
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return String(parsed);
  }

  const labels: Record<string, string> = {
    local: 'Local',
    trecho: 'Trecho',
  };

  const parts = Object.entries(parsed)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
    .map(([key, value]) => `${labels[key] ?? key}: ${String(value)}`);

  return parts.join(' • ');
}

function extractCommentReference(anchor: unknown) {
  if (!anchor) return { local: '', trecho: '' };

  let parsed = anchor;
  if (typeof parsed === 'string') {
    try {
      parsed = JSON.parse(parsed);
    } catch {
      return { local: '', trecho: parsed };
    }
  }

  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    return { local: '', trecho: String(parsed) };
  }

  const record = parsed as Record<string, unknown>;
  return {
    local: typeof record.local === 'string' ? record.local : '',
    trecho: typeof record.trecho === 'string' ? record.trecho : '',
  };
}

function stripHtml(value?: string | null) {
  return (value || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

export function PppPage({ adminMode = false }: PppPageProps) {
  const client = useApiClient();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin_cliente' || user?.role === 'super_admin';
  const isProfessor = user?.role === 'professor';
  const shouldLoadOverview = adminMode && isAdmin;
  const escolaAssociadaId = !shouldLoadOverview ? (user?.escolaId ?? null) : null;

  const overviewQuery = usePppOverview(shouldLoadOverview);
  const escolasQuery = useQuery({
    queryKey: ['escolas'],
    enabled: shouldLoadOverview,
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Escola>>('/escolas', {
        query: { page_size: 200 },
      });
      return response.data.results ?? [];
    },
  });

  const [selectedEscolaId, setSelectedEscolaId] = useState<number | null>(null);

  useEffect(() => {
    if (!shouldLoadOverview || selectedEscolaId) return;
    const firstOverview = overviewQuery.data?.[0]?.escola_id;
    const firstSchool = escolasQuery.data?.[0]?.id;
    if (firstOverview) {
      setSelectedEscolaId(firstOverview);
      return;
    }
    if (firstSchool) {
      setSelectedEscolaId(firstSchool);
    }
  }, [escolasQuery.data, overviewQuery.data, selectedEscolaId, shouldLoadOverview]);

  useEffect(() => {
    if (shouldLoadOverview || selectedEscolaId) return;
    if (escolaAssociadaId) {
      setSelectedEscolaId(escolaAssociadaId);
    }
  }, [escolaAssociadaId, selectedEscolaId, shouldLoadOverview]);

  const escolaIdAtiva = shouldLoadOverview ? selectedEscolaId : escolaAssociadaId;
  const documentoQuery = usePppDocumento({
    escolaId: escolaIdAtiva ?? undefined,
    enabled: !shouldLoadOverview || Boolean(selectedEscolaId),
  });
  const updatePpp = useUpdatePppConteudo();
  const concludePpp = useConcludePpp();
  const createComentario = useCreateComentario();
  const updateComentario = useUpdateComentario();

  const ppp = documentoQuery.data;
  const isPppAvailable = ppp?.is_available !== false;
  const comentariosEnabled = Boolean(ppp?.id) && !isProfessor && isPppAvailable;
  const { data: comentarios, refetch: refetchComentarios } = useComentarios({
    alvoTipo: 'ppp',
    alvoId: ppp?.id,
    enabled: comentariosEnabled,
    resolvido: undefined,
  });

  useStreamSubscription({
    alvoTipo: 'ppp',
    alvoId: ppp?.id,
    enabled: comentariosEnabled,
    onMessage: () => {
      documentoQuery.refetch();
      refetchComentarios();
    },
  });

  const [titulo, setTitulo] = useState('');
  const [conteudo, setConteudo] = useState('');
  const [comentarioTexto, setComentarioTexto] = useState('');
  const [comentarioLocal, setComentarioLocal] = useState('');
  const [comentarioTrecho, setComentarioTrecho] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [comentarioDrafts, setComentarioDrafts] = useState<Record<number, string>>({});
  const [comentarioRespostaDrafts, setComentarioRespostaDrafts] = useState<Record<number, string>>({});
  const [comentarioRespostaAbertaId, setComentarioRespostaAbertaId] = useState<number | null>(null);
  const comentarioTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!ppp) return;
    setTitulo(ppp.titulo);
    setConteudo(ppp.conteudo_html);
  }, [ppp?.id, ppp?.version]);

  const comentariosOrdenados = useMemo(
    () => (comentarios ?? []).slice().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [comentarios],
  );

  const anchorPreview = useMemo(() => {
    if (!comentarioLocal.trim() && !comentarioTrecho.trim()) return '';
    return JSON.stringify(
      {
        ...(comentarioLocal.trim() ? { local: comentarioLocal.trim() } : {}),
        ...(comentarioTrecho.trim() ? { trecho: comentarioTrecho.trim() } : {}),
      },
      null,
      2,
    );
  }, [comentarioLocal, comentarioTrecho]);

  const selectedOverview = useMemo(
    () => overviewQuery.data?.find((item) => item.escola_id === selectedEscolaId) ?? null,
    [overviewQuery.data, selectedEscolaId],
  );

  const pageDescription = adminMode
    ? 'Acompanhe o andamento por escola, abra o documento e finalize a versão institucional em PDF.'
    : isProfessor
      ? 'Visualize a versão concluída do Projeto Político-Pedagógico da sua escola quando ela estiver disponível.'
      : 'Construa colaborativamente o Projeto Político-Pedagógico da sua escola com edição compartilhada e comentários contextualizados.';

  const handleSave = async () => {
    if (!ppp) return;
    setFeedback(null);
    try {
      await updatePpp.mutateAsync({
        escolaId: escolaIdAtiva ?? undefined,
        etag: ppp.etag,
        titulo,
        conteudoHtml: conteudo,
      });
      setFeedback('PPP salvo com sucesso.');
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Falha ao salvar o PPP.';
      setFeedback(message);
    }
  };

  const handleConclude = async () => {
    if (!ppp) return;
    setFeedback(null);
    try {
      await concludePpp.mutateAsync({
        escolaId: escolaIdAtiva ?? undefined,
        etag: ppp.etag,
      });
      setFeedback('PPP concluído e registrado na plataforma.');
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Falha ao concluir o PPP.';
      setFeedback(message);
    }
  };

  const handleDownloadPdf = async () => {
    if (!ppp) return;
    setFeedback(null);
    try {
      const response = await client.get<Blob>('/ppp/pdf', {
        query: { escola_id: escolaIdAtiva ?? undefined },
        responseType: 'blob',
      });
      const blobUrl = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = `ppp-${ppp.escola_nome.toLowerCase().replace(/\s+/g, '-')}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Falha ao gerar o PDF do PPP.';
      setFeedback(message);
    }
  };

  const handleCreateComentario = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!ppp || !comentarioTexto.trim()) return;
    const anchorJson =
      comentarioLocal.trim() || comentarioTrecho.trim()
        ? JSON.stringify({
            ...(comentarioLocal.trim() ? { local: comentarioLocal.trim() } : {}),
            ...(comentarioTrecho.trim() ? { trecho: comentarioTrecho.trim() } : {}),
          })
        : undefined;
    await createComentario.mutateAsync({
      alvoTipo: 'ppp',
      alvoId: ppp.id,
      conteudoHtml: ensureHtml(comentarioTexto),
      anchorJson,
    });
    setComentarioTexto('');
    setComentarioLocal('');
    setComentarioTrecho('');
    refetchComentarios();
  };

  const handleResolveComentario = async (comentario: Comentario) => {
    await updateComentario.mutateAsync({
      comentarioId: comentario.id,
      payload: { resolvido: true },
      etag: comentario.etag,
    });
    refetchComentarios();
  };

  const handleUpdateComentario = async (comentario: Comentario) => {
    const draft = comentarioDrafts[comentario.id];
    if (!draft?.trim()) return;
    await updateComentario.mutateAsync({
      comentarioId: comentario.id,
      payload: { conteudo_html: ensureHtml(draft) },
      etag: comentario.etag,
    });
    refetchComentarios();
  };

  const handleReplyComentario = (comentario: Comentario) => {
    setComentarioRespostaAbertaId(comentario.id);
    setComentarioRespostaDrafts((prev) => ({
      ...prev,
      [comentario.id]: prev[comentario.id] ?? stripHtml(comentario.resposta_html),
    }));
  };

  const handleSubmitRespostaComentario = async (comentario: Comentario) => {
    const draft = comentarioRespostaDrafts[comentario.id];
    if (!draft?.trim()) return;
    await updateComentario.mutateAsync({
      comentarioId: comentario.id,
      payload: { resposta_html: ensureHtml(draft) },
      etag: comentario.etag,
    });
    setComentarioRespostaAbertaId(null);
    refetchComentarios();
  };

  if ((documentoQuery.isLoading && !ppp) || (shouldLoadOverview && overviewQuery.isLoading && !overviewQuery.data)) {
    return <FullPageLoader message="Carregando PPP da escola..." />;
  }

  if (documentoQuery.isError) {
    const error = documentoQuery.error;
    const message = error instanceof ApiError ? error.message : 'Não foi possível carregar o PPP da escola.';
    return (
      <div className="ppp-page space-y-6">
        <PageHeader title="PPP" description="Houve um problema ao abrir o documento da escola." />
        <Card>
          <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-white px-6 py-12 text-center">
            <h2 className="mb-2 text-xl font-extrabold text-[var(--color-text)]">Falha ao carregar o PPP</h2>
            <p className="mx-auto max-w-2xl text-sm text-[var(--color-text-secondary)]">{message}</p>
          </div>
        </Card>
      </div>
    );
  }

  if (!ppp) {
    return (
      <div className="ppp-page space-y-6">
        <PageHeader
          title="PPP"
          description={
            shouldLoadOverview
              ? 'Selecione uma escola para abrir o Projeto Político-Pedagógico.'
              : 'Nenhuma escola foi identificada para o seu usuário.'
          }
        />
        <Card>
          <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-white px-6 py-12 text-center">
            <h2 className="mb-2 text-xl font-extrabold text-[var(--color-text)]">
              {shouldLoadOverview ? 'Nenhum PPP disponível' : 'Usuário sem escola vinculada'}
            </h2>
            <p className="mx-auto max-w-2xl text-sm text-[var(--color-text-secondary)]">
              {shouldLoadOverview
                ? 'Escolha uma escola para iniciar a elaboração ou ver o documento existente.'
                : 'Associe uma escola ao usuário para abrir automaticamente o PPP correspondente.'}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  const statusLabel = STATUS_LABELS[ppp.status] ?? ppp.status;
  const statusClass = STATUS_CLASSES[ppp.status] ?? 'bg-[var(--color-primary-light)] text-[var(--color-primary)]';
  const comentariosAbertos = ppp.comentarios_abertos ?? comentariosOrdenados.filter((item) => !item.resolvido).length;
  const overviewPanel = shouldLoadOverview ? (
    <Card>
      <div className="space-y-3">
        <div>
          <h3 className="text-lg font-extrabold text-[var(--color-text)]">Panorama por escola</h3>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Visão rápida do avanço do PPP em cada unidade.
          </p>
        </div>
        <div className="space-y-2">
          {(overviewQuery.data ?? []).map((item) => (
            <button
              key={item.escola_id}
              type="button"
              onClick={() => setSelectedEscolaId(item.escola_id)}
              className={`w-full rounded-[14px] border px-4 py-3 text-left transition ${
                selectedEscolaId === item.escola_id
                  ? 'border-[var(--color-primary)] bg-[var(--color-primary-light)]'
                  : 'border-[var(--color-border)] bg-white'
              }`}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <strong className="text-sm text-[var(--color-text)]">{item.escola_nome}</strong>
                <span className={`rounded-full px-2 py-1 text-[11px] font-bold ${STATUS_CLASSES[item.status] ?? statusClass}`}>
                  {STATUS_LABELS[item.status] ?? item.status}
                </span>
              </div>
              <div className="mt-2 flex flex-col gap-1 text-xs text-[var(--color-text-secondary)] sm:flex-row sm:items-center sm:justify-between">
                <span>{item.comentarios_abertos} comentário(s) aberto(s)</span>
                <span>{formatDateTime(item.updated_at)}</span>
              </div>
            </button>
          ))}
        </div>
        {selectedOverview && (
          <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-xs text-[var(--color-text-secondary)]">
            Escola ativa: <strong className="text-[var(--color-text)]">{selectedOverview.escola_nome}</strong>
          </div>
        )}
      </div>
    </Card>
  ) : null;
  const comentariosPanel = (
    <Card>
      <div className="space-y-3">
        <div>
          <h3 className="text-lg font-extrabold text-[var(--color-text)]">
            {isProfessor ? 'Acesso do professor' : 'Fila de comentários'}
          </h3>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {isProfessor
              ? 'Professores visualizam apenas a versão concluída do PPP da escola.'
              : 'O redator pode comentar o texto; Diretor e Coordenação acompanham e fecham as pendências.'}
          </p>
        </div>

        {isProfessor ? (
          <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-6 sm:py-8">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Esta área fica disponível apenas para consulta do documento final. Comentários, edição, conclusão e exportação em PDF permanecem restritos aos perfis responsáveis pela elaboração.
            </p>
          </div>
        ) : (
          <>
            <form className="space-y-3" onSubmit={handleCreateComentario}>
              <label className="block space-y-2">
                <span className="text-sm font-semibold text-[var(--color-text)]">Novo comentário</span>
                <textarea
                  ref={comentarioTextareaRef}
                  rows={4}
                  value={comentarioTexto}
                  onChange={(event) => setComentarioTexto(event.target.value)}
                  disabled={!ppp.can_comment || createComentario.isPending}
                  placeholder="Descreva o ajuste, a dúvida ou o encaminhamento desejado."
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">Local</span>
                  <input
                    value={comentarioLocal}
                    onChange={(event) => setComentarioLocal(event.target.value)}
                    disabled={!ppp.can_comment || createComentario.isPending}
                    placeholder="Ex.: capítulo 2"
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">Trecho</span>
                  <input
                    value={comentarioTrecho}
                    onChange={(event) => setComentarioTrecho(event.target.value)}
                    disabled={!ppp.can_comment || createComentario.isPending}
                    placeholder="Palavras-chave ou trecho"
                  />
                </label>
              </div>
              <div className="rounded-[14px] bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-secondary)]">
                <strong className="block text-[var(--color-text)]">Âncora JSON</strong>
                <code className="mt-2 block whitespace-pre-wrap break-all">{anchorPreview || 'Nenhuma referência informada.'}</code>
              </div>
              <Button className="w-full sm:w-auto" type="submit" variant="primary" disabled={!ppp.can_comment || createComentario.isPending}>
                {createComentario.isPending ? 'Enviando...' : 'Registrar comentário'}
              </Button>
            </form>

            <div className="space-y-3">
              {comentariosOrdenados.map((comentario) => (
                <div key={comentario.id} className="rounded-[14px] border border-[var(--color-border)] bg-white p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <strong className="text-sm text-[var(--color-text)]">Comentário</strong>
                        <span
                          className={`rounded-full px-2 py-1 text-[11px] font-bold ${
                            comentario.resolvido
                              ? 'bg-[rgba(22,163,74,0.12)] text-[var(--color-success)]'
                              : 'bg-[rgba(245,158,11,0.12)] text-[var(--color-warning)]'
                          }`}
                        >
                          {comentario.resolvido ? 'Resolvido' : 'Aberto'}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                        Criado em {formatDateTime(comentario.created_at)}
                      </p>
                    </div>
                    {!comentario.resolvido && ppp.can_conclude && (
                      <Button className="w-full sm:w-auto" size="sm" variant="outline" onClick={() => handleResolveComentario(comentario)}>
                        Resolver
                      </Button>
                    )}
                  </div>

                  {comentario.anchor_json && (
                    <div className="mt-3 rounded-[12px] bg-[var(--color-surface-muted)] px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                      <strong className="mr-2 text-[var(--color-text)]">Referência:</strong>
                      {formatCommentReference(comentario.anchor_json)}
                    </div>
                  )}

                  <div
                    className="prose prose-sm mt-3 max-w-none text-[var(--color-text)]"
                    dangerouslySetInnerHTML={{ __html: comentario.conteudo_html }}
                  />

                  {comentario.resposta_html && (
                    <div className="mt-3 rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-3">
                      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                        <strong className="text-[var(--color-text)]">Resposta</strong>
                        {comentario.respondido_em && <span>Respondido em {formatDateTime(comentario.respondido_em)}</span>}
                      </div>
                      <div
                        className="prose prose-sm max-w-none text-[var(--color-text)]"
                        dangerouslySetInnerHTML={{ __html: comentario.resposta_html }}
                      />
                    </div>
                  )}

                  {!comentario.resolvido && ppp.can_comment && comentario.autor === user?.id && (
                    <div className="mt-3 space-y-2">
                      <textarea
                        rows={3}
                        value={comentarioDrafts[comentario.id] ?? ''}
                        onChange={(event) => setComentarioDrafts((prev) => ({ ...prev, [comentario.id]: event.target.value }))}
                        placeholder="Atualize o texto do comentário, se necessário."
                      />
                      <Button
                        className="w-full sm:w-auto"
                        size="sm"
                        variant="ghost"
                        style={COMMENT_ACTION_BUTTON_STYLE}
                        onClick={() => handleUpdateComentario(comentario)}
                      >
                        Atualizar comentário
                      </Button>
                    </div>
                  )}

                  {!comentario.resolvido &&
                    ppp.can_comment &&
                    comentario.autor !== user?.id &&
                    (!comentario.respondido_por || comentario.respondido_por === user?.id) && (
                    <div className="mt-3">
                      {comentarioRespostaAbertaId === comentario.id ? (
                        <div className="space-y-2">
                          <textarea
                            rows={3}
                            value={comentarioRespostaDrafts[comentario.id] ?? ''}
                            onChange={(event) => setComentarioRespostaDrafts((prev) => ({ ...prev, [comentario.id]: event.target.value }))}
                            placeholder="Escreva a resposta para este comentário."
                          />
                          <div className="flex flex-col gap-2 sm:flex-row">
                            <Button className="w-full sm:w-auto" size="sm" variant="primary" onClick={() => handleSubmitRespostaComentario(comentario)}>
                              {comentario.resposta_html ? 'Atualizar resposta' : 'Enviar resposta'}
                            </Button>
                            <Button className="w-full sm:w-auto" size="sm" variant="ghost" onClick={() => setComentarioRespostaAbertaId(null)}>
                              Cancelar
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <Button
                          className="w-full sm:w-auto"
                          size="sm"
                          variant="ghost"
                          style={COMMENT_ACTION_BUTTON_STYLE}
                          onClick={() => handleReplyComentario(comentario)}
                        >
                          {comentario.resposta_html ? 'Editar resposta' : 'Responder comentário'}
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {comentariosOrdenados.length === 0 && (
                <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-8 text-center">
                  <h4 className="text-base font-extrabold text-[var(--color-text)]">Nenhum comentário registrado</h4>
                  <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                    Use este painel para orientar a construção do texto e registrar pendências.
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Card>
  );

  return (
    <div className="ppp-page space-y-6">
      <PageHeader
        title={adminMode ? 'Admin · PPP por escola' : 'PPP da Escola'}
        description={pageDescription}
        actions={(
          <div className="ppp-page__header-actions flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:justify-end">
            {shouldLoadOverview && (
              <select
                value={selectedEscolaId ?? ''}
                onChange={(event) => setSelectedEscolaId(event.target.value ? Number(event.target.value) : null)}
                className="w-full sm:min-w-[240px] sm:w-auto"
              >
                <option value="">Selecione a escola</option>
                {(escolasQuery.data ?? []).map((escola) => (
                  <option key={escola.id} value={escola.id}>
                    {escola.nome}
                  </option>
                ))}
              </select>
            )}
            <span className={`w-fit rounded-full px-3 py-1 text-xs font-bold ${statusClass}`}>{statusLabel}</span>
            {!isProfessor && (
              <>
                <Button className="w-full sm:w-auto" variant="outline" onClick={handleDownloadPdf} disabled={ppp.status !== 'concluido'}>
                  Baixar PDF
                </Button>
                <Button className="w-full sm:w-auto" variant="secondary" onClick={handleSave} disabled={!ppp.can_edit || updatePpp.isPending}>
                  {updatePpp.isPending ? 'Salvando...' : 'Salvar texto'}
                </Button>
                <Button className="w-full sm:w-auto" variant="primary" onClick={handleConclude} disabled={!ppp.can_conclude || concludePpp.isPending}>
                  {concludePpp.isPending ? 'Concluindo...' : 'Concluir PPP'}
                </Button>
              </>
            )}
          </div>
        )}
      />

      <div className="relative overflow-hidden rounded-[18px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[var(--shadow-md)]">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage:
              'linear-gradient(to right, var(--color-primary) 1px, transparent 1px), linear-gradient(to bottom, var(--color-text) 1px, transparent 1px)',
            backgroundSize: '32px 32px, 32px 32px',
          }}
        />
        <div
          className={`relative grid gap-4 px-3 py-3 sm:px-5 sm:py-5 ${
            shouldLoadOverview ? 'lg:grid-cols-[1.4fr_0.6fr]' : 'lg:grid-cols-1'
          }`}
        >
          <div className={shouldLoadOverview ? 'space-y-4 lg:col-span-2' : 'space-y-4'}>
            <div className="flex flex-col gap-3 rounded-[14px] bg-[var(--color-surface-muted)] p-4 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
              <div className="space-y-2">
                <span className="inline-flex rounded-full bg-[var(--color-primary-light)] px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--color-primary)]">
                  Documento escolar
                </span>
                <div>
                  <h2 className="text-xl font-extrabold text-[var(--color-text)] sm:text-2xl">{ppp.escola_nome}</h2>
                  <p className="break-words text-sm text-[var(--color-text-secondary)]">
                    Última edição: {formatDateTime(ppp.updated_at)} · Por {ppp.ultima_edicao_por_nome ?? 'colaborador não identificado'}
                  </p>
                </div>
              </div>
              <div className="flex w-full min-w-0 flex-col gap-2 rounded-[14px] border border-[var(--color-border)] bg-white p-3 text-sm text-[var(--color-text-secondary)] sm:min-w-[220px] sm:max-w-[320px]">
                <span>
                  <strong className="text-[var(--color-text)]">Comentários abertos:</strong> {isPppAvailable ? comentariosAbertos : 'Disponível após conclusão'}
                </span>
                <span>
                  <strong className="text-[var(--color-text)]">Versão:</strong> {ppp.version}
                </span>
                <span>
                  <strong className="text-[var(--color-text)]">Conclusão:</strong> {ppp.concluido_em ? formatDateTime(ppp.concluido_em) : 'Ainda não concluído'}
                </span>
                {ppp.concluido_por_nome && (
                  <span>
                    <strong className="text-[var(--color-text)]">Responsável:</strong> {ppp.concluido_por_nome}
                  </span>
                )}
              </div>
            </div>

            <Card className="border-none bg-transparent p-0 shadow-none" noPadding>
              {isPppAvailable ? (
                <div className="space-y-4 rounded-[14px] bg-white p-3 sm:p-4">
                  <label className="block space-y-2">
                    <span className="text-sm font-semibold text-[var(--color-text)]">Título do documento</span>
                    <input
                      value={titulo}
                      onChange={(event) => setTitulo(event.target.value)}
                      disabled={isProfessor || !ppp.can_edit}
                      placeholder="Informe o título institucional do PPP"
                    />
                  </label>
                  <div className="space-y-2">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <span className="text-sm font-semibold text-[var(--color-text)]">Texto colaborativo</span>
                      {(isProfessor || !ppp.can_edit) && (
                        <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-text-secondary)]">
                          Somente leitura
                        </span>
                      )}
                    </div>
                    <RichTextEditor
                      value={conteudo}
                      onChange={setConteudo}
                      placeholder="Escreva o PPP da escola com objetivos, princípios, organização pedagógica e compromissos institucionais."
                      disabled={isProfessor || !ppp.can_edit}
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3 rounded-[14px] bg-white p-4 sm:p-6">
                  <span className="inline-flex w-fit rounded-full bg-[rgba(245,158,11,0.12)] px-3 py-1 text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--color-warning)]">
                    Visualização indisponível
                  </span>
                  <h3 className="text-xl font-extrabold text-[var(--color-text)]">PPP ainda não concluído</h3>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    {ppp.availability_message ?? 'O PPP da sua escola ainda está em elaboração e será liberado para consulta após a conclusão.'}
                  </p>
                </div>
              )}
            </Card>
          </div>

          <div className={shouldLoadOverview ? 'space-y-4 lg:col-span-2' : 'space-y-4'}>
            {shouldLoadOverview && (
              <Card>
                <div className="space-y-3">
                  <div>
                    <h3 className="text-lg font-extrabold text-[var(--color-text)]">Panorama por escola</h3>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      Visão rápida do avanço do PPP em cada unidade.
                    </p>
                  </div>
                  <div className="space-y-2">
                    {(overviewQuery.data ?? []).map((item) => (
                      <button
                        key={item.escola_id}
                        type="button"
                        onClick={() => setSelectedEscolaId(item.escola_id)}
                        className={`w-full rounded-[14px] border px-4 py-3 text-left transition ${
                          selectedEscolaId === item.escola_id
                            ? 'border-[var(--color-primary)] bg-[var(--color-primary-light)]'
                            : 'border-[var(--color-border)] bg-white'
                        }`}
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <strong className="text-sm text-[var(--color-text)]">{item.escola_nome}</strong>
                          <span className={`rounded-full px-2 py-1 text-[11px] font-bold ${STATUS_CLASSES[item.status] ?? statusClass}`}>
                            {STATUS_LABELS[item.status] ?? item.status}
                          </span>
                        </div>
                        <div className="mt-2 flex flex-col gap-1 text-xs text-[var(--color-text-secondary)] sm:flex-row sm:items-center sm:justify-between">
                          <span>{item.comentarios_abertos} comentário(s) aberto(s)</span>
                          <span>{formatDateTime(item.updated_at)}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedOverview && (
                    <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-3 text-xs text-[var(--color-text-secondary)]">
                      Escola ativa: <strong className="text-[var(--color-text)]">{selectedOverview.escola_nome}</strong>
                    </div>
                  )}
                </div>
              </Card>
            )}

            <Card>
              <div className="space-y-3">
                <div>
                  <h3 className="text-lg font-extrabold text-[var(--color-text)]">
                    {isProfessor ? 'Acesso do professor' : 'Fila de comentários'}
                  </h3>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    {isProfessor
                      ? 'Professores visualizam apenas a versão concluída do PPP da escola.'
                      : 'O redator pode comentar o texto; Diretor e Coordenação acompanham e fecham as pendências.'}
                  </p>
                </div>

                {isProfessor ? (
                  <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-6 sm:py-8">
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      Esta área fica disponível apenas para consulta do documento final. Comentários, edição, conclusão e exportação em PDF permanecem restritos aos perfis responsáveis pela elaboração.
                    </p>
                  </div>
                ) : (
                  <>
                    <form className="space-y-3" onSubmit={handleCreateComentario}>
                      <label className="block space-y-2">
                        <span className="text-sm font-semibold text-[var(--color-text)]">Novo comentário</span>
                        <textarea
                          rows={4}
                          value={comentarioTexto}
                          onChange={(event) => setComentarioTexto(event.target.value)}
                          disabled={!ppp.can_comment || createComentario.isPending}
                          placeholder="Descreva o ajuste, a dúvida ou o encaminhamento desejado."
                        />
                      </label>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="block space-y-2">
                          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">Local</span>
                          <input
                            value={comentarioLocal}
                            onChange={(event) => setComentarioLocal(event.target.value)}
                            disabled={!ppp.can_comment || createComentario.isPending}
                            placeholder="Ex.: capítulo 2"
                          />
                        </label>
                        <label className="block space-y-2">
                          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">Trecho</span>
                          <input
                            value={comentarioTrecho}
                            onChange={(event) => setComentarioTrecho(event.target.value)}
                            disabled={!ppp.can_comment || createComentario.isPending}
                            placeholder="Palavras-chave ou trecho"
                          />
                        </label>
                      </div>
                      <div className="rounded-[14px] bg-[var(--color-surface-muted)] p-3 text-xs text-[var(--color-text-secondary)]">
                        <strong className="block text-[var(--color-text)]">Âncora JSON</strong>
                        <code className="mt-2 block whitespace-pre-wrap break-all">{anchorPreview || 'Nenhuma referência informada.'}</code>
                      </div>
                      <Button className="w-full sm:w-auto" type="submit" variant="primary" disabled={!ppp.can_comment || createComentario.isPending}>
                        {createComentario.isPending ? 'Enviando...' : 'Registrar comentário'}
                      </Button>
                    </form>

                    <div className="space-y-3">
                      {comentariosOrdenados.map((comentario) => (
                        <div key={comentario.id} className="rounded-[14px] border border-[var(--color-border)] bg-white p-4">
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <strong className="text-sm text-[var(--color-text)]">Comentário</strong>
                                <span
                                  className={`rounded-full px-2 py-1 text-[11px] font-bold ${
                                    comentario.resolvido
                                      ? 'bg-[rgba(22,163,74,0.12)] text-[var(--color-success)]'
                                      : 'bg-[rgba(245,158,11,0.12)] text-[var(--color-warning)]'
                                  }`}
                                >
                                  {comentario.resolvido ? 'Resolvido' : 'Aberto'}
                                </span>
                              </div>
                              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                                Criado em {formatDateTime(comentario.created_at)}
                              </p>
                            </div>
                            {!comentario.resolvido && ppp.can_conclude && (
                              <Button className="w-full sm:w-auto" size="sm" variant="outline" onClick={() => handleResolveComentario(comentario)}>
                                Resolver
                              </Button>
                            )}
                          </div>

                          {comentario.anchor_json && (
                            <div className="mt-3 rounded-[12px] bg-[var(--color-surface-muted)] px-3 py-2 text-xs text-[var(--color-text-secondary)]">
                              <strong className="mr-2 text-[var(--color-text)]">Referência:</strong>
                              {formatCommentReference(comentario.anchor_json)}
                            </div>
                          )}

                          <div
                            className="prose prose-sm mt-3 max-w-none text-[var(--color-text)]"
                            dangerouslySetInnerHTML={{ __html: comentario.conteudo_html }}
                          />

                          {comentario.resposta_html && (
                            <div className="mt-3 rounded-[12px] border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-3">
                              <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                                <strong className="text-[var(--color-text)]">Resposta</strong>
                                {comentario.respondido_em && <span>Respondido em {formatDateTime(comentario.respondido_em)}</span>}
                              </div>
                              <div
                                className="prose prose-sm max-w-none text-[var(--color-text)]"
                                dangerouslySetInnerHTML={{ __html: comentario.resposta_html }}
                              />
                            </div>
                          )}

                          {!comentario.resolvido && ppp.can_comment && comentario.autor === user?.id && (
                            <div className="mt-3 space-y-2">
                              <textarea
                                rows={3}
                                value={comentarioDrafts[comentario.id] ?? ''}
                                onChange={(event) => setComentarioDrafts((prev) => ({ ...prev, [comentario.id]: event.target.value }))}
                                placeholder="Atualize o texto do comentário, se necessário."
                              />
                              <Button
                                className="w-full sm:w-auto"
                                size="sm"
                                variant="ghost"
                                style={COMMENT_ACTION_BUTTON_STYLE}
                                onClick={() => handleUpdateComentario(comentario)}
                              >
                                Atualizar comentário
                              </Button>
                            </div>
                          )}

                          {!comentario.resolvido &&
                            ppp.can_comment &&
                            comentario.autor !== user?.id &&
                            (!comentario.respondido_por || comentario.respondido_por === user?.id) && (
                            <div className="mt-3">
                              {comentarioRespostaAbertaId === comentario.id ? (
                                <div className="space-y-2">
                                  <textarea
                                    rows={3}
                                    value={comentarioRespostaDrafts[comentario.id] ?? ''}
                                    onChange={(event) => setComentarioRespostaDrafts((prev) => ({ ...prev, [comentario.id]: event.target.value }))}
                                    placeholder="Escreva a resposta para este comentário."
                                  />
                                  <div className="flex flex-col gap-2 sm:flex-row">
                                    <Button className="w-full sm:w-auto" size="sm" variant="primary" onClick={() => handleSubmitRespostaComentario(comentario)}>
                                      {comentario.resposta_html ? 'Atualizar resposta' : 'Enviar resposta'}
                                    </Button>
                                    <Button className="w-full sm:w-auto" size="sm" variant="ghost" onClick={() => setComentarioRespostaAbertaId(null)}>
                                      Cancelar
                                    </Button>
                                  </div>
                                </div>
                              ) : (
                                <Button
                                  className="w-full sm:w-auto"
                                  size="sm"
                                  variant="ghost"
                                  style={COMMENT_ACTION_BUTTON_STYLE}
                                  onClick={() => handleReplyComentario(comentario)}
                                >
                                  {comentario.resposta_html ? 'Editar resposta' : 'Responder comentário'}
                                </Button>
                              )}
                            </div>
                          )}
                        </div>
                      ))}

                      {comentariosOrdenados.length === 0 && (
                        <div className="rounded-[14px] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 py-8 text-center">
                          <h4 className="text-base font-extrabold text-[var(--color-text)]">Nenhum comentário registrado</h4>
                          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                            Use este painel para orientar a construção do texto e registrar pendências.
                          </p>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>

      {feedback && (
        <Card>
          <p className="text-sm text-[var(--color-text-secondary)]">{feedback}</p>
        </Card>
      )}
    </div>
  );
}
