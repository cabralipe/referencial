import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useApiClient } from '@/api/client';
import { useRevisoes } from '@/hooks/useRevisoes';
import { useReviewDecision } from '@/hooks/useReviewDecision';
import { useComentarios, useCreateComentario, useUpdateComentario } from '@/hooks/useComentarios';
import { useDiffApproved } from '@/hooks/useDiffApproved';
import type { Resposta, TextoUnico } from '@/api/types';

import './RedatorReviewDetailPage.css';

const CHECKLIST_OPTIONS = [
  'Faltam exemplos locais',
  'Texto precisa estar mais objetivo',
  'A linguagem está pouco pedagógica',
  'Referência à BNCC ausente',
  'Precisa detalhar responsáveis e prazos',
];

const stripHtml = (html?: string | null) =>
  (html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

const formatAnchorLabel = (anchor: unknown) => {
  if (!anchor) return null;
  if (typeof anchor === 'string') {
    try {
      return formatAnchorLabel(JSON.parse(anchor));
    } catch {
      return anchor;
    }
  }
  if (typeof anchor === 'object') {
    const record = anchor as Record<string, unknown>;
    if (typeof record.paragraph === 'number') {
      return `Parágrafo ${record.paragraph}`;
    }
    if (typeof record.txt === 'string') {
      return record.txt;
    }
    if (typeof record.trecho === 'string') {
      return record.trecho;
    }
    if (typeof record.local === 'string') {
      return record.local;
    }
    return JSON.stringify(record);
  }
  return null;
};

export function RedatorReviewDetailPage() {
  const { alvoTipo = 'resposta', alvoId = '' } = useParams();
  const alvoIdNumber = Number(alvoId);
  const client = useApiClient();

  const revisoesQuery = useRevisoes({ alvoTipo, alvoId: alvoIdNumber, pageSize: 200 });
  const revisaoAtual = useMemo(() => (revisoesQuery.data ?? [])[0] ?? null, [revisoesQuery.data]);

  const comentariosQuery = useComentarios({ alvoTipo, alvoId: alvoIdNumber, enabled: Boolean(alvoIdNumber) });
  const createComentario = useCreateComentario();
  const updateComentario = useUpdateComentario();

  const [resposta, setResposta] = useState<Resposta | null>(null);
  const [textoUnico, setTextoUnico] = useState<TextoUnico | null>(null);
  const [loadingTarget, setLoadingTarget] = useState(true);
  const [commentText, setCommentText] = useState('');
  const [selectedQuote, setSelectedQuote] = useState('');
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);

  const [checklist, setChecklist] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const [activeTab, setActiveTab] = useState<'texto' | 'comentarios' | 'parecer' | 'diff' | 'referencias'>('texto');

  const decision = useReviewDecision();
  const diffApproved = useDiffApproved();
  const [diffHtml, setDiffHtml] = useState('');

  useEffect(() => {
    let active = true;
    const loadTarget = async () => {
      setLoadingTarget(true);
      setResposta(null);
      setTextoUnico(null);
      if (!alvoIdNumber) {
        setLoadingTarget(false);
        return;
      }
      try {
        if (alvoTipo === 'resposta') {
          const response = await client.get<Resposta>(`/respostas/${alvoIdNumber}`);
          if (active) setResposta(response.data);
        } else if (alvoTipo === 'texto_unico') {
          const response = await client.get<TextoUnico>(`/texto_unico/${alvoIdNumber}`);
          if (active) setTextoUnico(response.data);
        }
      } finally {
        if (active) setLoadingTarget(false);
      }
    };
    loadTarget();
    return () => {
      active = false;
    };
  }, [alvoTipo, alvoIdNumber, client]);

  if (loadingTarget || revisoesQuery.isLoading) {
    return <FullPageLoader message="Carregando revisão..." />;
  }

  if (!resposta && !textoUnico) {
    return (
      <div className="redator-review-detail">
        <PageHeader title="Revisão" description="Nenhum conteúdo encontrado." />
        <Card>
          <Link to="/redator/revisoes">Voltar</Link>
        </Card>
      </div>
    );
  }

  const preview = revisaoAtual?.alvo_preview ?? null;
  const tarefaNome = preview && 'tarefa_nome' in preview ? preview.tarefa_nome : null;
  const tarefaEtapa = preview && 'tarefa_etapa' in preview ? preview.tarefa_etapa : null;
  const autorNome = preview && 'autor_nome' in preview ? preview.autor_nome : null;
  const gtNome = preview && 'gt_nome' in preview ? preview.gt_nome : null;

  const targetHtml = resposta?.conteudo_html ?? textoUnico?.conteudo_html ?? '';
  const plainText = stripHtml(targetHtml);
  const targetLabel = alvoTipo === 'texto_unico' ? 'Texto único' : 'Bloco';
  const reviewerRecommendation = revisaoAtual?.reviewer_recommendation;

  return (
    <div className="redator-review-detail">
      <PageHeader
        title={`Revisão do ${targetLabel} #${resposta?.id ?? textoUnico?.id ?? ''}`}
        description={`GT ${gtNome ?? resposta?.gt_nome ?? resposta?.gt ?? textoUnico?.gt ?? '—'} · ${tarefaNome ? tarefaNome : 'Sem trilha'}${tarefaEtapa ? ` · ${tarefaEtapa}` : ''}${autorNome ? ` · ${autorNome}` : ''} · Status ${revisaoAtual?.status ?? 'rascunho'}`}
        actions={(
          <div className="redator-review-detail__actions">
            <Button
              variant="secondary"
              onClick={async () => {
                if (!revisaoAtual) return;
                await decision.mutateAsync({
                  revisaoId: revisaoAtual.id,
                  decision: 'approve',
                  note,
                  checklist,
                  etag: revisaoAtual.etag,
                });
              }}
              disabled={!revisaoAtual || decision.isPending}
            >
              Validar
            </Button>
            <Button
              variant="ghost"
              onClick={async () => {
                if (!revisaoAtual) return;
                await decision.mutateAsync({
                  revisaoId: revisaoAtual.id,
                  decision: 'return',
                  note,
                  checklist,
                  etag: revisaoAtual.etag,
                });
              }}
              disabled={!revisaoAtual || decision.isPending}
            >
              Devolver
            </Button>
            <Link to="/redator/revisoes">Voltar</Link>
          </div>
        )}
      />

      <div className="redator-review-detail__tabs">
        {[
          { key: 'texto', label: 'Texto' },
          { key: 'comentarios', label: 'Comentários' },
          { key: 'parecer', label: 'Parecer' },
          { key: 'diff', label: 'Diff' },
          { key: 'referencias', label: 'Referências' },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            className={activeTab === item.key ? 'active' : ''}
            onClick={() => setActiveTab(item.key as typeof activeTab)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {activeTab === 'texto' && (
        <Card>
          <div className="redator-review-detail__content">
            <h2>Conteúdo atual</h2>
            <div dangerouslySetInnerHTML={{ __html: targetHtml || '<p>Sem conteúdo.</p>' }} />
          </div>
        </Card>
      )}

      {activeTab === 'parecer' && (
        <>
          <Card>
            <div className="redator-review-detail__recommendation">
              <h2>Recomendação do revisor</h2>
              {reviewerRecommendation ? (
                <>
                  <p>
                    Tipo: <strong>{reviewerRecommendation.decision_type.replace('recommend_', '')}</strong>
                  </p>
                  {reviewerRecommendation.checklist?.length ? (
                    <ul>
                      {reviewerRecommendation.checklist.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                  {reviewerRecommendation.note && <p>{reviewerRecommendation.note}</p>}
                </>
              ) : (
                <p>Sem recomendação registrada pelo revisor.</p>
              )}
            </div>
          </Card>
          <Card>
            <div className="redator-review-detail__checklist">
              <h2>Checklist de devolução</h2>
              <div className="redator-review-detail__checklist-items">
                {CHECKLIST_OPTIONS.map((item) => (
                  <label key={item}>
                    <input
                      type="checkbox"
                      checked={checklist.includes(item)}
                      onChange={(event) => {
                        if (event.target.checked) {
                          setChecklist((prev) => [...prev, item]);
                        } else {
                          setChecklist((prev) => prev.filter((value) => value !== item));
                        }
                      }}
                    />
                    {item}
                  </label>
                ))}
              </div>
              <label>
                <span>Observação</span>
                <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={3} />
              </label>
            </div>
          </Card>
        </>
      )}

      {activeTab === 'diff' && (
        <Card>
          <div className="redator-review-detail__diff">
            <h2>Diff</h2>
            <p>Compare o conteúdo atual com a última versão aprovada.</p>
            <Button
              variant="secondary"
              onClick={async () => {
                const response = await diffApproved.mutateAsync({ alvoTipo, alvoId: alvoIdNumber });
                setDiffHtml(response.html);
              }}
              disabled={diffApproved.isPending}
            >
              {diffApproved.isPending ? 'Carregando...' : 'Carregar diff'}
            </Button>
            {diffHtml && <div dangerouslySetInnerHTML={{ __html: diffHtml }} />}
          </div>
        </Card>
      )}

      {activeTab === 'comentarios' && (
        <Card>
          <div className="redator-review-detail__comentarios">
            <h2>Comentários</h2>
            <p>Selecione um trecho no texto abaixo para ancorar o comentário.</p>
            <textarea
              className="redator-review-detail__anchor"
              value={plainText}
              readOnly
              onMouseUp={(event) => {
                const target = event.currentTarget;
                const start = target.selectionStart ?? 0;
                const end = target.selectionEnd ?? 0;
                if (start === end) {
                  setSelectedQuote('');
                  setSelectionRange(null);
                  return;
                }
                setSelectionRange({ start, end });
                setSelectedQuote(plainText.slice(start, end));
              }}
            />

            <div className="redator-review-detail__comentario-form">
              <label>
                <span>Trecho selecionado</span>
                <input value={selectedQuote} readOnly placeholder="Selecione um trecho" />
              </label>
              <label className="full">
                <span>Comentário</span>
                <textarea value={commentText} onChange={(event) => setCommentText(event.target.value)} rows={3} />
              </label>
              <Button
                variant="secondary"
                onClick={async () => {
                  if (!commentText.trim()) return;
                  const anchor = selectionRange
                    ? JSON.stringify({ ...selectionRange, quote: selectedQuote })
                    : null;
                  await createComentario.mutateAsync({
                    alvoTipo: alvoTipo,
                    alvoId: alvoIdNumber,
                    conteudoHtml: commentText,
                    anchorJson: anchor,
                  });
                  setCommentText('');
                }}
                disabled={createComentario.isPending}
              >
                {createComentario.isPending ? 'Enviando...' : 'Adicionar comentário'}
              </Button>
            </div>

            <div className="redator-review-detail__comentario-list">
              {(comentariosQuery.data ?? []).map((comentario) => (
                <div key={comentario.id} className="redator-review-detail__comentario-item">
                  <div>
                    <strong>#{comentario.id}</strong>
                    <span>{comentario.resolvido ? 'Resolvido' : 'Aberto'}</span>
                  </div>
                  <div dangerouslySetInnerHTML={{ __html: comentario.conteudo_html }} />
                  {comentario.anchor_json && <small>Âncora: {formatAnchorLabel(comentario.anchor_json)}</small>}
                  {!comentario.resolvido && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        updateComentario.mutate({
                          comentarioId: comentario.id,
                          payload: { resolvido: true },
                          etag: comentario.etag,
                        })
                      }
                    >
                      Resolver
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'referencias' && (
        <Card>
          <div className="redator-review-detail__references">
            <h2>Referências</h2>
            <p>Consulte materiais de apoio e referências do cliente antes de validar.</p>
            <Link to="/biblioteca">Abrir biblioteca de referências</Link>
          </div>
        </Card>
      )}
    </div>
  );
}
