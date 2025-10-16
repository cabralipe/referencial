import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { RichTextEditor } from '@/components/forms/RichTextEditor';
import { useTarefa } from '@/hooks/useTarefas';
import { useAvailableGtIds } from '@/hooks/useAvailableGtIds';
import { useTextoUnico, useUpsertTextoUnico } from '@/hooks/useTextoUnico';
import { useCreateReview } from '@/hooks/useReviews';
import { useDebounce } from '@/utils/debounce';
import { CommentSidebar, CommentSidebarTrigger, CommentInline } from '@/components/comments';

import './TextoUnicoPage.css';

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

export function TextoUnicoPage() {
  const { tarefaId = '' } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const gtParam = searchParams.get('gt');
  const selectedGtId = gtParam ? Number(gtParam) : null;

  const [content, setContent] = useState('');
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [reviewFeedback, setReviewFeedback] = useState<string>('');
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false);

  const { data: tarefa, isLoading: tarefaLoading, isError: tarefaError, error: tarefaErrorObj } =
    useTarefa(tarefaId);
  
  const { data: textoUnico, isLoading: textoUnicoLoading } = useTextoUnico({
    gtId: selectedGtId,
    tarefaId: tarefaId ? Number(tarefaId) : null,
  });
  
  const { gtOptions } = useAvailableGtIds();
  const upsertTextoUnico = useUpsertTextoUnico();
  const createReview = useCreateReview();

  // Initialize content when textoUnico loads
  useEffect(() => {
    if (textoUnico && !hasUnsavedChanges) {
      setContent(textoUnico.conteudo_html);
    }
  }, [textoUnico, hasUnsavedChanges]);

  // Auto-select first GT if none selected
  useEffect(() => {
    if (!gtParam && gtOptions.length > 0) {
      setSearchParams({ gt: String(gtOptions[0]) }, { replace: true });
    }
  }, [gtOptions, gtParam, setSearchParams]);

  // Auto-save function
  const performAutoSave = async (contentToSave: string) => {
    if (!selectedGtId || !tarefaId) return;

    setSaveStatus('saving');
    setErrorMessage('');

    try {
      await upsertTextoUnico.mutateAsync({
        gtId: selectedGtId,
        tarefaId: Number(tarefaId),
        conteudoHtml: contentToSave,
        textoUnicoId: textoUnico?.id,
        etag: textoUnico?.etag,
      });
      
      setSaveStatus('saved');
      setHasUnsavedChanges(false);
      
      // Reset to idle after showing saved status
      setTimeout(() => {
        setSaveStatus('idle');
      }, 2000);
    } catch (error) {
      setSaveStatus('error');
      const message = error instanceof ApiError 
        ? error.message 
        : 'Erro ao salvar o texto único';
      setErrorMessage(message);
    }
  };

  // Debounced auto-save (2 seconds delay)
  const debouncedAutoSave = useDebounce(performAutoSave, 2000);

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setHasUnsavedChanges(true);
    
    // Trigger auto-save
    if (newContent.trim() !== (textoUnico?.conteudo_html || '').trim()) {
      debouncedAutoSave(newContent);
    }
  };

  const handleManualSave = async () => {
    await performAutoSave(content);
  };

  const handleSelectGt = (gtId: number) => {
    if (hasUnsavedChanges) {
      const confirmLeave = window.confirm(
        'Você tem alterações não salvas. Deseja realmente trocar de GT?'
      );
      if (!confirmLeave) return;
    }
    
    setSearchParams({ gt: String(gtId) }, { replace: true });
    setHasUnsavedChanges(false);
  };

  const handleSolicitarRevisao = async () => {
    if (!selectedGtId || !textoUnico) return;
    
    try {
      await createReview.mutateAsync({
        target_type: 'texto_unico',
        target_id: String(textoUnico.id),
        gt_id: selectedGtId,
        parecer_html: '',
      });
      setReviewFeedback('Solicitação de revisão enviada com sucesso.');
      setTimeout(() => setReviewFeedback(''), 3000);
    } catch (err) {
      const message = err instanceof ApiError 
        ? err.message 
        : 'Não foi possível solicitar a revisão.';
      setReviewFeedback(message);
      setTimeout(() => setReviewFeedback(''), 5000);
    }
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

  if (tarefaLoading || textoUnicoLoading) {
    return <FullPageLoader message="Carregando texto único..." />;
  }

  if (tarefaError) {
    const message = buildErrorMessage(tarefaErrorObj, 'Erro ao carregar tarefa.');
    return (
      <div className="texto-unico__error">
        <h2>Algo deu errado</h2>
        <p>{message}</p>
        <Link to="/">Voltar ao painel</Link>
      </div>
    );
  }

  if (!tarefa) {
    return null;
  }

  const etapaLabel = tarefa.etapa ? `Etapa ${tarefa.etapa}` : 'Etapa não informada';

  const renderSaveStatus = () => {
    switch (saveStatus) {
      case 'saving':
        return <span className="save-status save-status--saving">Salvando...</span>;
      case 'saved':
        return <span className="save-status save-status--saved">✓ Salvo</span>;
      case 'error':
        return <span className="save-status save-status--error">✗ Erro ao salvar</span>;
      default:
        return hasUnsavedChanges ? (
          <span className="save-status save-status--unsaved">• Não salvo</span>
        ) : null;
    }
  };

  return (
    <div className="texto-unico-page">
      <div className="texto-unico__header">
        <div className="texto-unico__breadcrumb">
          <Link to="/" className="breadcrumb-link">Painel</Link>
          <span className="breadcrumb-separator">›</span>
          <span className="breadcrumb-current">Texto Único</span>
        </div>
        
        <div className="texto-unico__title-section">
          <h1 className="texto-unico__title">
            Texto Único - Tarefa {tarefa.ordem}
          </h1>
          <p className="texto-unico__subtitle">
            {etapaLabel} • {tarefa.tipo}
          </p>
        </div>

        <div className="texto-unico__actions">
          {renderSaveStatus()}
          {selectedGtId && textoUnico && (
            <>
              <CommentSidebarTrigger
                targetType="texto_unico"
                targetId={textoUnico.id}
                onToggle={setIsCommentSidebarOpen}
                className="btn btn--secondary"
              >
                Comentários
              </CommentSidebarTrigger>
              <button
                onClick={handleSolicitarRevisao}
                disabled={createReview.isPending}
                className="btn btn--review"
              >
                {createReview.isPending ? 'Solicitando...' : 'Solicitar Revisão'}
              </button>
            </>
          )}
          <button
            onClick={handleManualSave}
            disabled={saveStatus === 'saving' || !hasUnsavedChanges}
            className="btn btn--primary"
          >
            {saveStatus === 'saving' ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>

      <div className="texto-unico__gt-selector">
        <label htmlFor="gt-select" className="gt-selector__label">
          Grupo de Trabalho:
        </label>
        <select
          id="gt-select"
          value={selectedGtId || ''}
          onChange={(e) => handleSelectGt(Number(e.target.value))}
          className="gt-selector__select"
        >
          <option value="">Selecione um GT</option>
          {gtOptions.map((gtId) => (
            <option key={gtId} value={gtId}>
              GT {gtId}
            </option>
          ))}
        </select>
      </div>

      {errorMessage && (
        <div className="texto-unico__error-message">
          <p>{errorMessage}</p>
          <button 
            onClick={() => setErrorMessage('')}
            className="error-dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {reviewFeedback && (
        <div className="texto-unico__review-feedback">
          <p>{reviewFeedback}</p>
          <button 
            onClick={() => setReviewFeedback('')}
            className="feedback-dismiss"
          >
            ✕
          </button>
        </div>
      )}

      {selectedGtId ? (
        <div className="texto-unico__content-wrapper">
          <div className="texto-unico__editor-container">
            <CommentInline
              targetType="texto_unico"
              targetId={textoUnico?.id}
              enabled={Boolean(textoUnico)}
            >
              <RichTextEditor
                value={content}
                onChange={handleContentChange}
                placeholder="Digite o texto único para este GT e tarefa..."
                height={500}
              />
            </CommentInline>
            
            <div className="texto-unico__editor-footer">
              <p className="editor-info">
                {textoUnico ? 'Editando texto existente' : 'Criando novo texto único'}
                {textoUnico && (
                  <span className="editor-meta">
                    • Última atualização: {new Date(textoUnico.updated_at).toLocaleString('pt-BR')}
                    • Versão: {textoUnico.version}
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Comment Sidebar */}
          {textoUnico && (
            <CommentSidebar
              targetType="texto_unico"
              targetId={textoUnico.id}
              isOpen={isCommentSidebarOpen}
              onClose={() => setIsCommentSidebarOpen(false)}
              title={`Comentários - Texto Único (Tarefa ${tarefa.ordem})`}
            />
          )}
        </div>
      ) : (
        <div className="texto-unico__no-gt">
          <p>Selecione um Grupo de Trabalho para começar a editar o texto único.</p>
        </div>
      )}
    </div>
  );
}