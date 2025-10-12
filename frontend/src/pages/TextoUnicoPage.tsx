import { useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAvailableGtIds } from '@/hooks/useAvailableGtIds';
import { useGenerateTextoUnico, useTextoUnicos } from '@/hooks/useTextoUnico';
import { useTarefas } from '@/hooks/useTarefas';

import './TextoUnicoPage.css';

export function TextoUnicoPage() {
  const { data: tarefas } = useTarefas();
  const { gtOptions } = useAvailableGtIds();

  const [selectedGt, setSelectedGt] = useState<number | ''>('');
  const [selectedTarefa, setSelectedTarefa] = useState<number | ''>('');

  const tarefasOptions = useMemo(() => {
    return (tarefas ?? []).slice().sort((a, b) => a.ordem - b.ordem);
  }, [tarefas]);

  const { data: textos, isLoading, refetch, isFetching } = useTextoUnicos({
    gtId: typeof selectedGt === 'number' ? selectedGt : undefined,
    tarefaId: typeof selectedTarefa === 'number' ? selectedTarefa : undefined,
  });
  const generateTexto = useGenerateTextoUnico();

  const handleGenerate = async () => {
    if (typeof selectedGt !== 'number' || typeof selectedTarefa !== 'number') {
      return;
    }
    await generateTexto.mutateAsync({ gtId: selectedGt, tarefaId: selectedTarefa });
    refetch();
  };

  if (isLoading && !textos) {
    return <FullPageLoader message="Carregando textos únicos..." />;
  }

  return (
    <div className="texto-unico">
      <header className="texto-unico__header">
        <div>
          <h1>Texto Único</h1>
          <p>Centralize as versões consolidadas por GT e acompanhe o histórico de geração.</p>
        </div>
      </header>

      <PageInstructions
        title="Quando gerar um texto único"
        description="Use esta área para consolidar contribuições do GT antes de enviar para revisão."
        items={[
          {
            title: 'Selecione GT e tarefa',
            description: 'O texto único é sempre associado a uma tarefa específica do grupo de trabalho.',
          },
          {
            title: 'Acione a geração',
            description: 'O backend processa e atualiza a versão; aguarde a confirmação antes de editar manualmente.',
          },
          {
            title: 'Monitore versões',
            description: 'Confira o número da versão e a data de atualização para saber se é seguro publicar.',
          },
        ]}
        footer="Gerações sucessivas sobrescrevem o conteúdo preservando o histórico via versionamento."
      />

      <div className="texto-unico__filters">
        <label>
          <span>GT</span>
          <select value={selectedGt} onChange={(event) => setSelectedGt(event.target.value ? Number(event.target.value) : '')}>
            <option value="">Selecione</option>
            {gtOptions.map((gt) => (
              <option key={gt} value={gt}>
                {gt}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Tarefa</span>
          <select
            value={selectedTarefa}
            onChange={(event) => setSelectedTarefa(event.target.value ? Number(event.target.value) : '')}
          >
            <option value="">Selecione</option>
            {tarefasOptions.map((tarefa) => (
              <option key={tarefa.id} value={tarefa.id}>
                {tarefa.ordem} — {tarefa.tipo === 'OFICINA' ? 'Oficina' : 'Questionário'}
              </option>
            ))}
          </select>
        </label>

        <div className="texto-unico__actions">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={
              typeof selectedGt !== 'number' ||
              typeof selectedTarefa !== 'number' ||
              generateTexto.isPending
            }
          >
            {generateTexto.isPending ? 'Gerando...' : 'Gerar texto único'}
          </button>
          <button type="button" className="ghost" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? 'Atualizando...' : 'Recarregar'}
          </button>
        </div>
      </div>

      {textos && textos.length > 0 ? (
        <div className="texto-unico__grid">
          {textos.map((texto) => (
            <article key={texto.id} className="texto-unico__card">
              <header>
                <h2>
                  GT {texto.gt} · Tarefa {texto.tarefa}
                </h2>
                <span>Versão {texto.version}</span>
              </header>
              <div className="texto-unico__meta">
                <span>Atualizado em {new Date(texto.updated_at).toLocaleString('pt-BR')}</span>
                {texto.responsavel && <span>Responsável #{texto.responsavel}</span>}
                <span>ETag: {texto.etag}</span>
              </div>
              <details>
                <summary>Visualizar HTML</summary>
                <div className="texto-unico__preview" dangerouslySetInnerHTML={{ __html: texto.conteudo_html }} />
              </details>
            </article>
          ))}
        </div>
      ) : (
        <div className="texto-unico__empty">
          <h3>Nenhum texto encontrado</h3>
          <p>Selecione um GT e tarefa ou gere um novo conteúdo para iniciar.</p>
        </div>
      )}
    </div>
  );
}
