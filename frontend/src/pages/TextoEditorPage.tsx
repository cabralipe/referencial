import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useRespostas } from '@/hooks/useRespostas';
import { useResposta, useUpdateResposta } from '@/hooks/useResposta';
import { useComentarios, useCreateComentario } from '@/hooks/useComentarios';
import { useCreateRevisao } from '@/hooks/useRevisoes';
import { useAuditLogs } from '@/hooks/useAuditLogs';
import { useBuildDiff } from '@/hooks/useDiff';
import type { Resposta } from '@/api/types';

import './TextoEditorPage.css';

const BNCC_REGEX = /^[A-Z]{2}\d{2}[A-Z]{2}\d{2}$/;

const ensureHtml = (value: string) => {
  const text = value.trim();
  if (!text) return '';
  const hasHtmlTag = /<\/?[a-z][\s\S]*>/i.test(text);
  if (hasHtmlTag) return value;
  return `<p>${text.replace(/\n/g, '<br />')}</p>`;
};

const splitParagraphs = (html?: string | null) => {
  if (!html) return [];
  return html
    .split(/<\/p>/i)
    .map((chunk) => chunk.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim())
    .filter(Boolean);
};

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

export function TextoEditorPage() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const { gtOptions } = useAvailableGts();
  const selectedGtId = searchParams.get('gt') ? Number(searchParams.get('gt')) : gtOptions[0]?.id ?? null;

  const { data: respostas, isLoading: respostasLoading } = useRespostas({ gtId: selectedGtId ?? undefined });
  const respostaId = id && /^\d+$/.test(id) ? Number(id) : null;
  const { data: resposta, isLoading: respostaLoading } = useResposta(respostaId);
  const updateResposta = useUpdateResposta();
  const createRevisao = useCreateRevisao();

  const [draft, setDraft] = useState('');
  const [bnccCode, setBnccCode] = useState('');
  const [feedback, setFeedback] = useState('');
  const [submitFeedback, setSubmitFeedback] = useState('');
  const autoSaveTimer = useRef<number | null>(null);
  const lastSaved = useRef<string>('');

  useEffect(() => {
    if (resposta) {
      setDraft(resposta.conteudo_html ?? '');
      lastSaved.current = resposta.conteudo_html ?? '';
    }
  }, [resposta]);

  const isFocus = searchParams.get('focus') === '1';

  useEffect(() => {
    if (!isFocus || !resposta) return;
    if (autoSaveTimer.current) {
      window.clearTimeout(autoSaveTimer.current);
    }
    if (draft === lastSaved.current) return;
    autoSaveTimer.current = window.setTimeout(async () => {
      try {
        await updateResposta.mutateAsync({
          respostaId: resposta.id,
          gt: resposta.gt,
          pergunta: resposta.pergunta,
          conteudo_html: ensureHtml(draft),
          etag: resposta.etag,
        });
        lastSaved.current = draft;
        setFeedback('Salvo automaticamente.');
      } catch (error) {
        setFeedback('Falha no auto-save.');
      }
    }, 1500);
  }, [draft, isFocus, resposta, updateResposta]);

  const comentariosQuery = useComentarios({ alvoTipo: 'resposta', alvoId: resposta?.id, enabled: Boolean(resposta?.id) });
  const createComentario = useCreateComentario();

  const auditLogs = useAuditLogs({
    entidade: 'curriculum.Resposta',
    entidadeId: resposta?.id,
    pageSize: 100,
    enabled: Boolean(resposta?.id),
  });
  const buildDiff = useBuildDiff();

  const versions = useMemo(() => {
    const versionSet = new Set<number>();
    (auditLogs.data ?? []).forEach((log) => {
      const current = log.diff_json?.current as { version?: number } | undefined;
      if (current?.version) {
        versionSet.add(Number(current.version));
      }
    });
    return Array.from(versionSet).sort((a, b) => a - b);
  }, [auditLogs.data]);

  const [diffFrom, setDiffFrom] = useState<number | null>(null);
  const [diffTo, setDiffTo] = useState<number | null>(null);
  const [diffHtml, setDiffHtml] = useState<string>('');

  const paragraphOptions = useMemo(() => splitParagraphs(draft), [draft]);
  const [selectedParagraph, setSelectedParagraph] = useState<number | null>(null);
  const [comentarioDraft, setComentarioDraft] = useState('');

  const handleInsert = (snippet: string) => {
    setDraft((prev) => `${prev}\n${snippet}`.trim());
  };

  const handleSave = async () => {
    if (!resposta) return;
    setFeedback('');
    try {
      await updateResposta.mutateAsync({
        respostaId: resposta.id,
        gt: resposta.gt,
        pergunta: resposta.pergunta,
        conteudo_html: ensureHtml(draft),
        etag: resposta.etag,
      });
      setFeedback('Texto salvo com sucesso.');
      lastSaved.current = draft;
    } catch (error) {
      setFeedback('Não foi possível salvar o texto.');
    }
  };

  const handleSubmitReview = async () => {
    if (!resposta) return;
    setSubmitFeedback('');
    try {
      await createRevisao.mutateAsync({
        alvoTipo: 'resposta',
        alvoId: resposta.id,
        parecerHtml: '',
      });
      setSubmitFeedback('Enviado para revisão.');
    } catch (error) {
      setSubmitFeedback('Não foi possível enviar para revisão.');
    }
  };

  const handleAddComentario = async () => {
    if (!resposta) return;
    const payload = comentarioDraft.trim();
    if (!payload) return;
    const anchor = selectedParagraph !== null ? JSON.stringify({ paragraph: selectedParagraph }) : null;
    await createComentario.mutateAsync({
      alvoTipo: 'resposta',
      alvoId: resposta.id,
      conteudoHtml: ensureHtml(payload),
      anchorJson: anchor,
    });
    setComentarioDraft('');
  };

  if (!id) {
    if (respostasLoading) {
      return <FullPageLoader message="Carregando textos..." />;
    }
    return (
      <div className="texto-editor">
        <PageHeader
          title="Construção de Texto"
          description="Escolha um texto para continuar a escrita colaborativa."
        />
        <Card>
          <label className="texto-editor__gt">
            <span>GT</span>
            <select
              value={selectedGtId ?? ''}
              onChange={(event) => {
                const value = event.target.value ? Number(event.target.value) : null;
                if (value) {
                  setSearchParams({ gt: String(value) });
                } else {
                  setSearchParams({});
                }
              }}
            >
              {gtOptions.map((gt) => (
                <option key={gt.id} value={gt.id}>
                  {gt.displayName}
                </option>
              ))}
            </select>
          </label>
          <div className="texto-editor__lista">
            {(respostas ?? []).map((resp) => (
              <div key={resp.id} className="texto-editor__item">
                <div>
                  <strong>Resposta #{resp.id}</strong>
                  <span>Atualizado {new Date(resp.updated_at).toLocaleString('pt-BR')}</span>
                </div>
                <Link to={`/texto/${resp.id}?gt=${resp.gt}`}>
                  <Button size="sm" variant="secondary">Abrir</Button>
                </Link>
              </div>
            ))}
            {(!respostas || respostas.length === 0) && (
              <p className="texto-editor__empty">Nenhum texto encontrado para este GT.</p>
            )}
          </div>
        </Card>
      </div>
    );
  }

  if (respostaLoading) {
    return <FullPageLoader message="Carregando editor..." />;
  }
  if (!resposta) {
    return (
      <div className="texto-editor">
        <PageHeader title="Texto não encontrado" description="Volte para a lista de textos." />
        <Card>
          <Link to="/texto">Voltar</Link>
        </Card>
      </div>
    );
  }

  const trilhaLink = resposta.tarefa_id ? `/minha-trilha/${resposta.tarefa_id}?gt=${resposta.gt}` : `/minha-trilha?gt=${resposta.gt}`;

  return (
    <div className="texto-editor">
      <PageHeader
        title={`Texto #${resposta.id}`}
        description="Edite o texto, registre comentários e acompanhe o histórico."
        actions={(
          <div className="texto-editor__actions">
            <Button variant="primary" onClick={handleSave} disabled={updateResposta.isPending}>
              {updateResposta.isPending ? 'Salvando...' : 'Salvar texto'}
            </Button>
            <Button variant="secondary" onClick={handleSubmitReview} disabled={createRevisao.isPending}>
              {createRevisao.isPending ? 'Enviando...' : 'Enviar para revisão'}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                const params = new URLSearchParams(searchParams);
                const next = isFocus ? '0' : '1';
                params.set('focus', next);
                setSearchParams(params, { replace: true });
              }}
            >
              {isFocus ? 'Sair do modo foco' : 'Entrar no modo foco'}
            </Button>
            <Link to={trilhaLink}>
              <Button variant="secondary">Voltar à trilha</Button>
            </Link>
          </div>
        )}
      />

      <Card>
        <div className="texto-editor__editor-shell">
          <div className="texto-editor__toolbar">
            <div className="texto-editor__toolbar-group">
              <button type="button" onClick={() => handleInsert('<h2>Título</h2>')}>Título</button>
              <button type="button" onClick={() => handleInsert('<p>Parágrafo</p>')}>Parágrafo</button>
              <button type="button" onClick={() => handleInsert('<ul><li>Item</li></ul>')}>Lista</button>
              <button
                type="button"
                onClick={() =>
                  handleInsert('<table><tr><th>Título</th></tr><tr><td>Conteúdo</td></tr></table>')
                }
              >
                Tabela
              </button>
            </div>
            <div className="texto-editor__toolbar-divider" />
            <div className="texto-editor__toolbar-group">
              <span className="texto-editor__toolbar-label">Estilo</span>
              <button type="button" onClick={() => handleInsert('<strong>Negrito</strong>')}>Negrito</button>
              <button type="button" onClick={() => handleInsert('<em>Itálico</em>')}>Itálico</button>
              <button type="button" onClick={() => handleInsert('<u>Sublinhado</u>')}>Sublinhado</button>
            </div>
          </div>

          <div className="texto-editor__subtoolbar">
            <div className="texto-editor__bncc">
              <label>
                <span>Código BNCC</span>
                <input
                  type="text"
                  value={bnccCode}
                  onChange={(event) => setBnccCode(event.target.value.toUpperCase())}
                  placeholder="Ex.: EF01LP01"
                />
              </label>
              <button
                type="button"
                onClick={() => {
                  if (!BNCC_REGEX.test(bnccCode.trim())) {
                    setFeedback('Código BNCC inválido. Use o padrão EF01LP01.');
                    return;
                  }
                  handleInsert(`<span class=\"bncc-code\">${bnccCode.trim()}</span>`);
                  setBnccCode('');
                }}
              >
                Inserir código
              </button>
            </div>
            <div className="texto-editor__status">
              <span>Fonte: Documento</span>
              <span>{draft.length} caracteres</span>
            </div>
          </div>

          <div className="texto-editor__page">
            <div className="texto-editor__ruler" aria-hidden="true" />
            <div className="texto-editor__editor">
              <RichTextEditor
                value={draft}
                onChange={setDraft}
                placeholder="Escreva como em um documento."
              />
            </div>
          </div>

          {feedback && <p className="texto-editor__feedback">{feedback}</p>}
          {submitFeedback && <p className="texto-editor__feedback">{submitFeedback}</p>}
          <details className="texto-editor__preview">
            <summary>Pré-visualização</summary>
            <div dangerouslySetInnerHTML={{ __html: ensureHtml(draft) || '<p>Sem conteúdo.</p>' }} />
          </details>
        </div>
      </Card>

      <Card>
        <div className="texto-editor__comentarios">
          <div>
            <h2>Comentários por trecho</h2>
            <p>Associe seu comentário a um parágrafo específico para facilitar a revisão.</p>
          </div>
          <div className="texto-editor__comentario-form">
            <label>
              <span>Trecho</span>
              <select
                value={selectedParagraph ?? ''}
                onChange={(event) => setSelectedParagraph(event.target.value ? Number(event.target.value) : null)}
              >
                <option value="">Sem trecho específico</option>
                {paragraphOptions.map((text, index) => (
                  <option key={`${index}-${text}`} value={index + 1}>
                    Parágrafo {index + 1} - {text.slice(0, 40)}
                  </option>
                ))}
              </select>
            </label>
            <label className="full">
              <span>Comentário</span>
              <textarea
                rows={3}
                value={comentarioDraft}
                onChange={(event) => setComentarioDraft(event.target.value)}
                placeholder="Escreva o comentário (HTML permitido)."
              />
            </label>
            <Button
              variant="secondary"
              onClick={handleAddComentario}
              disabled={createComentario.isPending}
            >
              {createComentario.isPending ? 'Enviando...' : 'Registrar comentário'}
            </Button>
          </div>

          <div className="texto-editor__comentario-list">
            {(comentariosQuery.data ?? []).map((comentario) => (
              <div key={comentario.id} className="texto-editor__comentario-item">
                <div>
                  <strong>Comentário #{comentario.id}</strong>
                  {comentario.anchor_json && (
                    <span>
                      Trecho:{' '}
                      {formatAnchorLabel(comentario.anchor_json)}
                    </span>
                  )}
                </div>
                <div dangerouslySetInnerHTML={{ __html: comentario.conteudo_html }} />
              </div>
            ))}
            {(!comentariosQuery.data || comentariosQuery.data.length === 0) && (
              <p className="texto-editor__empty">Nenhum comentário registrado.</p>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <div className="texto-editor__historico">
          <div>
            <h2>Histórico de versões</h2>
            <p>Compare versões para revisar alterações.</p>
          </div>
          <div className="texto-editor__diff-controls">
            <label>
              <span>De</span>
              <select value={diffFrom ?? ''} onChange={(event) => setDiffFrom(event.target.value ? Number(event.target.value) : null)}>
                <option value="">Selecione</option>
                {versions.map((version) => (
                  <option key={version} value={version}>{version}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Para</span>
              <select value={diffTo ?? ''} onChange={(event) => setDiffTo(event.target.value ? Number(event.target.value) : null)}>
                <option value="">Selecione</option>
                {versions.map((version) => (
                  <option key={version} value={version}>{version}</option>
                ))}
              </select>
            </label>
            <Button
              variant="ghost"
              onClick={async () => {
                if (!diffFrom || !diffTo) return;
                const response = await buildDiff.mutateAsync({
                  alvoTipo: 'resposta',
                  alvoId: resposta.id,
                  fromVersion: diffFrom,
                  toVersion: diffTo,
                });
                setDiffHtml(response.html);
              }}
              disabled={buildDiff.isPending}
            >
              {buildDiff.isPending ? 'Comparando...' : 'Comparar'}
            </Button>
          </div>
          {diffHtml && (
            <div className="texto-editor__diff" dangerouslySetInnerHTML={{ __html: diffHtml }} />
          )}
        </div>
      </Card>
    </div>
  );
}
