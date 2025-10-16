import { useState, useEffect } from 'react';
import { Save, Send, X, User } from 'lucide-react';
import type { ReviewFormProps, CreateReviewPayload, UpdateReviewPayload } from '@/api/types';
import { RichTextEditor } from '@/components/forms/RichTextEditor';
import './ReviewForm.css';

export function ReviewForm({
  review,
  targetType,
  targetId,
  onSubmit,
  onCancel,
  loading = false,
  availableReviewers = [],
  mode = 'create',
}: ReviewFormProps) {
  const [formData, setFormData] = useState({
    revisor_id: review?.revisor?.id || '',
    parecer_html: review?.parecer_html || '',
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (review) {
      setFormData({
        revisor_id: review.revisor?.id || '',
        parecer_html: review.parecer_html || '',
      });
    }
  }, [review]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.revisor_id) {
      newErrors.revisor_id = 'Selecione um revisor';
    }
    
    if (mode === 'edit' && !formData.parecer_html.trim()) {
      newErrors.parecer_html = 'O parecer é obrigatório';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (action: 'save' | 'submit') => {
    if (!validateForm()) return;

    try {
      if (mode === 'create') {
        const payload: CreateReviewPayload = {
          alvo_tipo: targetType!,
          alvo_id: targetId!,
          revisor_id: parseInt(formData.revisor_id),
          parecer_html: formData.parecer_html,
        };
        await onSubmit(payload, action);
      } else {
        const payload: UpdateReviewPayload = {
          revisor_id: parseInt(formData.revisor_id),
          parecer_html: formData.parecer_html,
        };
        await onSubmit(payload, action);
      }
    } catch (error) {
      console.error('Erro ao salvar revisão:', error);
    }
  };

  const getTargetTypeLabel = (type: string) => {
    const labels = {
      resposta: 'Resposta',
      texto_unico: 'Texto Único',
      quadro: 'Quadro/Oficina',
    };
    return labels[type as keyof typeof labels] || type;
  };

  return (
    <div className="review-form">
      <div className="review-form__header">
        <h2 className="review-form__title">
          {mode === 'create' ? 'Solicitar Revisão' : 'Editar Revisão'}
        </h2>
        {targetType && (
          <p className="review-form__subtitle">
            Tipo de conteúdo: {getTargetTypeLabel(targetType)}
          </p>
        )}
      </div>

      <form className="review-form__form" onSubmit={(e) => e.preventDefault()}>
        <div className="review-form__field">
          <label htmlFor="revisor" className="review-form__label">
            <User size={16} />
            Revisor *
          </label>
          <select
            id="revisor"
            value={formData.revisor_id}
            onChange={(e) => setFormData(prev => ({ ...prev, revisor_id: e.target.value }))}
            className={`review-form__select ${errors.revisor_id ? 'error' : ''}`}
            disabled={loading}
          >
            <option value="">Selecione um revisor</option>
            {availableReviewers.map((reviewer) => (
              <option key={reviewer.id} value={reviewer.id}>
                {reviewer.name}
              </option>
            ))}
          </select>
          {errors.revisor_id && (
            <span className="review-form__error">{errors.revisor_id}</span>
          )}
        </div>

        <div className="review-form__field">
          <label className="review-form__label">
            Parecer {mode === 'edit' ? '*' : '(opcional)'}
          </label>
          <div className="review-form__editor-wrapper">
            <RichTextEditor
              value={formData.parecer_html}
              onChange={(value) => setFormData(prev => ({ ...prev, parecer_html: value }))}
              placeholder="Digite o parecer da revisão..."
              disabled={loading}
            />
          </div>
          {errors.parecer_html && (
            <span className="review-form__error">{errors.parecer_html}</span>
          )}
        </div>

        <div className="review-form__actions">
          <button
            type="button"
            onClick={onCancel}
            className="btn btn--secondary"
            disabled={loading}
          >
            <X size={16} />
            Cancelar
          </button>
          
          <button
            type="button"
            onClick={() => handleSubmit('save')}
            className="btn btn--primary"
            disabled={loading}
          >
            <Save size={16} />
            {loading ? 'Salvando...' : 'Salvar Rascunho'}
          </button>
          
          <button
            type="button"
            onClick={() => handleSubmit('submit')}
            className="btn btn--success"
            disabled={loading}
          >
            <Send size={16} />
            {loading ? 'Enviando...' : 'Enviar para Revisão'}
          </button>
        </div>
      </form>
    </div>
  );
}