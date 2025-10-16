import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { QuadroGrid } from '@/components/quadros/QuadroGrid';
import { QuadroToolbar } from '@/components/quadros/QuadroToolbar';
import { QuadroStatusBar } from '@/components/quadros/QuadroStatusBar';
import { CommentSidebar } from '@/components/comments';
import { useGetOrCreateQuadro, useUpdateCelula } from '@/hooks/useQuadros';
import { useAvailableGtIds } from '@/hooks/useAvailableGtIds';
import { useCreateReview } from '@/hooks/useReviews';
import { getTemplate } from '@/utils/quadroTemplates';
import type { QuadroState } from '@/api/types';
import './QuadroPage.css';

export function QuadroPage() {
  const { tarefaId } = useParams<{ tarefaId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { data: gtIds } = useAvailableGtIds();
  
  // State management
  const [selectedTemplate, setSelectedTemplate] = useState<string>('swot');
  const [quadroState, setQuadroState] = useState<QuadroState>({
    hasUnsavedChanges: false,
    editingCells: new Set(),
    lastSaved: null,
    error: null,
  });
  const [pendingUpdates, setPendingUpdates] = useState<Map<string, string>>(new Map());
  const [isCommentSidebarOpen, setIsCommentSidebarOpen] = useState(false);
  const [selectedCellForComments, setSelectedCellForComments] = useState<{linha: number, coluna: number} | null>(null);

  // Get current GT ID from URL params or fallback to first available
  const gtParam = searchParams.get('gt');
  const currentGtId = gtParam ? Number(gtParam) : (gtIds?.[0] || 1);

  // React Query hooks
  const {
    data: quadro,
    isLoading,
    error: quadroError,
    refetch,
  } = useGetOrCreateQuadro(currentGtId, selectedTemplate);

  const updateCelulaMutation = useUpdateCelula();
  const createReview = useCreateReview();

  // Get template data
  const template = useMemo(() => getTemplate(selectedTemplate), [selectedTemplate]);

  // Debounced auto-save function
  const debouncedSave = useCallback((linha: number, coluna: number, valor: string) => {
    const cellKey = `${linha}-${coluna}`;
    
    // Update pending updates
    setPendingUpdates(prev => {
      const newMap = new Map(prev);
      if (valor.trim() === '') {
        newMap.delete(cellKey);
      } else {
        newMap.set(cellKey, valor);
      }
      return newMap;
    });

    // Set unsaved changes flag
    setQuadroState(prev => ({
      ...prev,
      hasUnsavedChanges: true,
      error: null,
    }));

    // Debounce the actual save operation
    const timeoutId = setTimeout(() => {
      if (!quadro) return;

      updateCelulaMutation.mutate(
        {
          quadroId: quadro.id,
          linha,
          coluna,
          valor_html: valor,
        },
        {
          onSuccess: () => {
            setPendingUpdates(prev => {
              const newMap = new Map(prev);
              newMap.delete(cellKey);
              return newMap;
            });
            
            setQuadroState(prev => ({
              ...prev,
              hasUnsavedChanges: prev.hasUnsavedChanges && pendingUpdates.size > 1,
              lastSaved: new Date(),
              error: null,
            }));
          },
          onError: (error) => {
            console.error('Error saving cell:', error);
            setQuadroState(prev => ({
              ...prev,
              error: 'Erro ao salvar célula. Tente novamente.',
            }));
            toast.error('Erro ao salvar célula');
          },
        }
      );
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [quadro, updateCelulaMutation, pendingUpdates.size]);

  // Handle cell value changes
  const handleCellChange = useCallback(
    (linha: number, coluna: number, valor: string) => {
      debouncedSave(linha, coluna, valor);
    },
    [debouncedSave]
  );

  // Handle opening comments for a specific cell
  const handleOpenCellComments = useCallback((linha: number, coluna: number) => {
    setSelectedCellForComments({ linha, coluna });
    setIsCommentSidebarOpen(true);
  }, []);



  // Handle template change
  const handleTemplateChange = useCallback(
    (templateId: string) => {
      if (quadroState.hasUnsavedChanges) {
        const confirmed = window.confirm(
          'Você tem alterações não salvas. Deseja continuar e perder essas alterações?'
        );
        if (!confirmed) return;
      }

      setSelectedTemplate(templateId);
      setQuadroState({
        hasUnsavedChanges: false,
        editingCells: new Set(),
        lastSaved: null,
        error: null,
      });
      setPendingUpdates(new Map());
    },
    [quadroState.hasUnsavedChanges]
  );

  // Handle export
  const handleExport = useCallback(() => {
    if (!quadro || !template) return;

    const data = {
      quadro,
      template,
      exportedAt: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quadro-${template.nome.toLowerCase()}-${quadro.version}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('Quadro exportado com sucesso');
  }, [quadro, template]);

  // Handle review request
  const handleSolicitarRevisao = useCallback(async () => {
    if (!quadro || !currentGtId) return;
    
    try {
      await createReview.mutateAsync({
        target_type: 'quadro',
        target_id: String(quadro.id),
        gt_id: currentGtId,
        parecer_html: '',
      });
      toast.success('Solicitação de revisão enviada com sucesso.');
    } catch (error) {
      console.error('Error requesting review:', error);
      toast.error('Não foi possível solicitar a revisão.');
    }
  }, [quadro, currentGtId, createReview]);

  // Handle navigation back
  const handleBack = useCallback(() => {
    if (quadroState.hasUnsavedChanges) {
      const confirmed = window.confirm(
        'Você tem alterações não salvas. Deseja sair mesmo assim?'
      );
      if (!confirmed) return;
    }
    
    const backUrl = gtParam 
      ? `/tarefas/${tarefaId}?gt=${gtParam}`
      : `/tarefas/${tarefaId}`;
    navigate(backUrl);
  }, [navigate, tarefaId, gtParam, quadroState.hasUnsavedChanges]);

  // Handle errors
  useEffect(() => {
    if (quadroError) {
      setQuadroState(prev => ({
        ...prev,
        error: 'Erro ao carregar quadro. Tente recarregar a página.',
      }));
      toast.error('Erro ao carregar quadro');
    }
  }, [quadroError]);

  // Handle beforeunload event
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (quadroState.hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [quadroState.hasUnsavedChanges]);

  // Validate required params
  if (!tarefaId) {
    return (
      <div className="quadro-page-error">
        <h2>Erro: ID da tarefa não encontrado</h2>
        <button onClick={() => navigate('/tasks')} className="back-button">
          Voltar para Tarefas
        </button>
      </div>
    );
  }

  return (
    <div className="quadro-page">
      <div className="quadro-page-header">
        <button
          onClick={handleBack}
          className="back-button"
          type="button"
        >
          ← Voltar
        </button>
        
        <QuadroToolbar
          quadro={quadro}
          template={template}
          onTemplateChange={handleTemplateChange}
          onExport={handleExport}
          onSolicitarRevisao={handleSolicitarRevisao}
          onOpenComments={() => setIsCommentSidebarOpen(true)}
          isLoading={isLoading}
          isSaving={updateCelulaMutation.isPending}
          isRequestingReview={createReview.isPending}
          hasUnsavedChanges={quadroState.hasUnsavedChanges}
        />
      </div>

      <div className="quadro-page-content">
        {isLoading ? (
          <div className="quadro-loading">
            <div className="loading-spinner"></div>
            <p>Carregando quadro...</p>
          </div>
        ) : quadro && template ? (
          <QuadroGrid
            quadro={quadro}
            template={template}
            onCellUpdate={handleCellChange}
            onOpenCellComments={handleOpenCellComments}
          />
        ) : (
          <div className="quadro-error">
            <h3>Erro ao carregar quadro</h3>
            <p>Não foi possível carregar o quadro. Tente novamente.</p>
            <button onClick={() => refetch()} className="retry-button">
              Tentar novamente
            </button>
          </div>
        )}
      </div>

      <QuadroStatusBar
        quadro={quadro}
        template={template}
        isLoading={isLoading}
        isSaving={updateCelulaMutation.isPending}
        lastSaved={quadroState.lastSaved}
        error={quadroState.error}
      />

      {quadro && (
        <CommentSidebar
          isOpen={isCommentSidebarOpen}
          onClose={() => {
            setIsCommentSidebarOpen(false);
            setSelectedCellForComments(null);
          }}
          targetType="quadro"
          targetId={String(quadro.id)}
          anchor={selectedCellForComments ? {
            type: 'cell',
            data: {
              linha: selectedCellForComments.linha,
              coluna: selectedCellForComments.coluna,
              template: selectedTemplate,
            }
          } : undefined}
        />
      )}
    </div>
  );
}