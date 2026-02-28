import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { useApiClient } from '@/api/client';

import './PlanoEditorPage.css';

type PlanoPayload = {
  id: number;
  escola: string;
  etapa_modalidade: string;
  componente_curricular: string;
  unidade_tematica: string;
  habilidades: string[];
  objetivos: string;
  conteudos: string;
  metodologia: string;
  recursos: string;
  avaliacao: string;
  estrategias_recomposicao: string;
  estrategias_inclusivas: string;
  referencias: string;
  status: string;
};

const STEPS = ['Identificação', 'Alinhamento curricular', 'Metodologia', 'Avaliação', 'Inclusão', 'Revisão final'];

function emptyPlano(): PlanoPayload {
  return {
    id: 0,
    escola: '',
    etapa_modalidade: '',
    componente_curricular: '',
    unidade_tematica: '',
    habilidades: [],
    objetivos: '',
    conteudos: '',
    metodologia: '',
    recursos: '',
    avaliacao: '',
    estrategias_recomposicao: '',
    estrategias_inclusivas: '',
    referencias: '',
    status: 'rascunho',
  };
}

export function PlanoEditorPage() {
  const { id } = useParams();
  const client = useApiClient();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [loading, setLoading] = useState(true);
  const [plano, setPlano] = useState<PlanoPayload>(emptyPlano());
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const response = await client.get<PlanoPayload>(`/planos-estruturados/${id}`);
        setPlano(response.data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [client, id]);

  const saveDraft = useMemo(
    () => async (payload: Partial<PlanoPayload>) => {
      if (!id) return;
      setSaving(true);
      try {
        await client.patch(`/planos-estruturados/${id}/autosave`, { body: payload });
        setStatusText(`Salvo automaticamente às ${new Date().toLocaleTimeString('pt-BR')}`);
      } finally {
        setSaving(false);
      }
    },
    [client, id],
  );

  const updateField = (field: keyof PlanoPayload, value: string | string[]) => {
    const updated = { ...plano, [field]: value };
    setPlano(updated);
    if (timer.current) {
      window.clearTimeout(timer.current);
    }
    timer.current = window.setTimeout(() => {
      void saveDraft({ [field]: value } as Partial<PlanoPayload>);
    }, 800);
  };

  if (loading) {
    return <FullPageLoader message="Carregando plano..." />;
  }

  return (
    <div className="plano-editor">
      <PageHeader
        title={`Editor de Plano #${plano.id}`}
        description="Fluxo multi-step com salvamento automático."
        actions={<span className="plano-editor__status">{saving ? 'Salvando...' : statusText}</span>}
      />

      <Card className="plano-editor__steps">
        {STEPS.map((label, idx) => (
          <button
            key={label}
            type="button"
            className={idx === step ? 'is-active' : ''}
            onClick={() => setStep(idx)}
          >
            {idx + 1}. {label}
          </button>
        ))}
      </Card>

      <Card className="plano-editor__form">
        {step === 0 && (
          <>
            <label>Escola</label>
            <input value={plano.escola} onChange={(e) => updateField('escola', e.target.value)} />
            <label>Etapa/Modalidade</label>
            <input value={plano.etapa_modalidade} onChange={(e) => updateField('etapa_modalidade', e.target.value)} />
            <label>Componente Curricular</label>
            <input value={plano.componente_curricular} onChange={(e) => updateField('componente_curricular', e.target.value)} />
          </>
        )}
        {step === 1 && (
          <>
            <label>Unidade Temática</label>
            <input value={plano.unidade_tematica} onChange={(e) => updateField('unidade_tematica', e.target.value)} />
            <label>Habilidades (uma por linha)</label>
            <textarea
              value={plano.habilidades.join('\n')}
              onChange={(e) => updateField('habilidades', e.target.value.split('\n').map((s) => s.trim()).filter(Boolean))}
            />
            <label>Objetivos</label>
            <textarea value={plano.objetivos} onChange={(e) => updateField('objetivos', e.target.value)} />
          </>
        )}
        {step === 2 && (
          <>
            <label>Conteúdos</label>
            <textarea value={plano.conteudos} onChange={(e) => updateField('conteudos', e.target.value)} />
            <label>Metodologia</label>
            <textarea value={plano.metodologia} onChange={(e) => updateField('metodologia', e.target.value)} />
            <label>Recursos</label>
            <textarea value={plano.recursos} onChange={(e) => updateField('recursos', e.target.value)} />
          </>
        )}
        {step === 3 && (
          <>
            <label>Avaliação</label>
            <textarea value={plano.avaliacao} onChange={(e) => updateField('avaliacao', e.target.value)} />
            <label>Estratégias de Recomposição</label>
            <textarea
              value={plano.estrategias_recomposicao}
              onChange={(e) => updateField('estrategias_recomposicao', e.target.value)}
            />
          </>
        )}
        {step === 4 && (
          <>
            <label>Estratégias Inclusivas</label>
            <textarea
              value={plano.estrategias_inclusivas}
              onChange={(e) => updateField('estrategias_inclusivas', e.target.value)}
            />
          </>
        )}
        {step === 5 && (
          <>
            <label>Referências</label>
            <textarea value={plano.referencias} onChange={(e) => updateField('referencias', e.target.value)} />
            <p className="plano-editor__hint">Revise os campos anteriores antes de enviar para avaliação.</p>
          </>
        )}
      </Card>
    </div>
  );
}

