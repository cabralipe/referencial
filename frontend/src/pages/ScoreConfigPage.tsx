import { useEffect, useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useScoreConfig } from '@/hooks/useScore';
import { useTarefas } from '@/hooks/useTarefas';
import { useAuth } from '@/context/AuthContext';

import './ScoreConfigPage.css';

export function ScoreConfigPage() {
  const { user } = useAuth();
  const { data: tarefas, isLoading: tarefasLoading } = useTarefas();
  const { data: config, isLoading, update } = useScoreConfig();

  const [monthlyLimit, setMonthlyLimit] = useState(0);
  const [defaultPoints, setDefaultPoints] = useState(0);
  const [tarefaPoints, setTarefaPoints] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!config) return;
    setMonthlyLimit(config.monthly_limit ?? 0);
    setDefaultPoints(config.default_points ?? 0);
    setTarefaPoints(config.tarefa_points ?? {});
  }, [config]);

  const tarefasOrdenadas = useMemo(() => {
    return (tarefas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
  }, [tarefas]);

  if (!user) {
    return <FullPageLoader message="Carregando configurações de score..." />;
  }

  if (user.role !== 'admin_cliente' && user.role !== 'super_admin') {
    return (
      <div className="score-config__empty">
        <h2>Acesso restrito</h2>
        <p>Somente admins podem ajustar as configurações de gamificação.</p>
      </div>
    );
  }

  if (isLoading || tarefasLoading) {
    return <FullPageLoader message="Carregando configurações de score..." />;
  }

  return (
    <div className="score-config">
      <header className="score-config__header">
        <div>
          <h1>Gamificação</h1>
          <p>Defina metas mensais e o score que cada trilha pedagógica vale para o redator.</p>
        </div>
        <button
          type="button"
          className="score-config__save"
          onClick={() =>
            update.mutate({
              monthly_limit: monthlyLimit,
              default_points: defaultPoints,
              tarefa_points: tarefaPoints,
            })
          }
          disabled={update.isPending}
        >
          {update.isPending ? 'Salvando...' : 'Salvar configurações'}
        </button>
      </header>

      <PageInstructions
        title="Como funciona o score"
        description="Cada parecer ou revisão registrada rende pontos ao redator. Ajuste a meta mensal e a pontuação por trilha."
        items={[
          {
            title: 'Meta mensal',
            description: 'Define o limite de pontos desejado para o período atual.',
          },
          {
            title: 'Pontuação padrão',
            description: 'Usada quando a trilha não tem um valor específico configurado.',
          },
          {
            title: 'Pontuação por trilha',
            description: 'Personalize valores de acordo com a complexidade de cada trilha pedagógica.',
          },
        ]}
      />

      <section className="score-config__section">
        <div className="score-config__card">
          <label>
            <span>Limite mensal de score</span>
            <input
              type="number"
              min={0}
              value={monthlyLimit}
              onChange={(event) => setMonthlyLimit(Number(event.target.value))}
            />
          </label>
          <label>
            <span>Pontuação padrão por revisão</span>
            <input
              type="number"
              min={0}
              value={defaultPoints}
              onChange={(event) => setDefaultPoints(Number(event.target.value))}
            />
          </label>
        </div>

        <div className="score-config__list">
          <h2>Pontuação por trilha</h2>
          {tarefasOrdenadas.length === 0 ? (
            <div className="score-config__empty">Nenhuma trilha encontrada para configurar.</div>
          ) : (
            tarefasOrdenadas.map((tarefa) => {
              const value = tarefaPoints[String(tarefa.id)] ?? '';
              return (
                <div key={tarefa.id} className="score-config__row">
                  <div>
                    <strong>Trilha {tarefa.ordem}</strong>
                    <span>{tarefa.nome}</span>
                  </div>
                  <input
                    type="number"
                    min={0}
                    placeholder={String(defaultPoints || 0)}
                    value={value}
                    onChange={(event) => {
                      const next = { ...tarefaPoints };
                      const raw = event.target.value;
                      if (raw === '') {
                        delete next[String(tarefa.id)];
                      } else {
                        next[String(tarefa.id)] = Number(raw);
                      }
                      setTarefaPoints(next);
                    }}
                  />
                </div>
              );
            })
          )}
        </div>
      </section>

      {update.isSuccess && (
        <div className="score-config__success">Configurações salvas com sucesso.</div>
      )}
      {update.isError && (
        <div className="score-config__error">Não foi possível salvar. Tente novamente.</div>
      )}
    </div>
  );
}
