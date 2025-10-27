import { useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useQuadros, useUpdateCelulaQuadro } from '@/hooks/useQuadros';

import './QuadrosPage.css';

type CellKey = `${number}-${number}-${number}`;

function buildKey(quadroId: number, linha: number, coluna: number): CellKey {
  return `${quadroId}-${linha}-${coluna}` as const;
}

export function QuadrosPage() {
  const { gtOptions } = useAvailableGts();
  const [selectedGt, setSelectedGt] = useState<number | ''>('');
  const [templateFilter, setTemplateFilter] = useState('');
  const [drafts, setDrafts] = useState<Record<CellKey, string>>({});

  const { data: quadros, isLoading } = useQuadros({
    gtId: typeof selectedGt === 'number' ? selectedGt : undefined,
    template: templateFilter || undefined,
  });
  const updateCelula = useUpdateCelulaQuadro();

  const templates = useMemo(() => {
    if (!quadros) return [] as string[];
    return Array.from(new Set(quadros.map((item) => item.template))).sort();
  }, [quadros]);

  if (isLoading && !quadros) {
    return <FullPageLoader message="Carregando quadros..." />;
  }

  const handleChange = (quadroId: number, linha: number, coluna: number, value: string) => {
    setDrafts((prev) => ({
      ...prev,
      [buildKey(quadroId, linha, coluna)]: value,
    }));
  };

  const handleSalvar = async (quadroId: number, linha: number, coluna: number) => {
    const valor_html = drafts[buildKey(quadroId, linha, coluna)] ?? '';
    await updateCelula.mutateAsync({ quadroId, linha, coluna, valor_html });
  };

  return (
    <div className="quadros">
      <header className="quadros__header">
        <div>
          <h1>Quadros de Oficina</h1>
          <p>Atualize células compartilhadas dos quadros de referência por GT ou template.</p>
        </div>
      </header>

      <PageInstructions
        title="Dicas para manter quadros organizados"
        description="Edite os blocos colaborativos com cuidado para evitar sobrescritas indevidas."
        items={[
          {
            title: 'Filtre antes de editar',
            description: 'Escolha o GT ou template para reduzir a visualização às células relevantes.',
          },
          {
            title: 'Salve célula a célula',
            description: 'Cada botão salva apenas a célula correspondente e devolve um novo versionamento.',
          },
          {
            title: 'Conferir versionamento',
            description: 'Use o campo “Version” do quadro para validar se outra pessoa atualizou após sua edição.',
          },
        ]}
      />

      <div className="quadros__filters">
        <label>
          <span>GT</span>
          <select value={selectedGt} onChange={(event) => setSelectedGt(event.target.value ? Number(event.target.value) : '')}>
            <option value="">Todos</option>
            {gtOptions.map((gt) => (
              <option key={gt.id} value={gt.id}>
                {gt.displayName}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Template</span>
          <select value={templateFilter} onChange={(event) => setTemplateFilter(event.target.value)}>
            <option value="">Todos</option>
            {templates.map((tpl) => (
              <option key={tpl} value={tpl}>
                {tpl}
              </option>
            ))}
          </select>
        </label>
      </div>

      {quadros && quadros.length > 0 ? (
        <div className="quadros__list">
          {quadros.map((quadro) => {
            const maxLinha = Math.max(0, ...quadro.celulas.map((celula) => celula.linha));
            const maxColuna = Math.max(0, ...quadro.celulas.map((celula) => celula.coluna));

            const getConteudo = (linha: number, coluna: number) => {
              const key = buildKey(quadro.id, linha, coluna);
              const draft = drafts[key];
              if (draft !== undefined) {
                return draft;
              }
              const celula = quadro.celulas.find((item) => item.linha === linha && item.coluna === coluna);
              return celula?.valor_html ?? '';
            };

            return (
              <article key={quadro.id} className="quadros__card">
                <header>
                  <div>
                    <h2>Quadro #{quadro.id}</h2>
                    <span>Template: {quadro.template}</span>
                  </div>
                  <span>Version {quadro.version}</span>
                </header>

                <div className="quadros__grid">
                  <table>
                    <tbody>
                      {Array.from({ length: maxLinha + 1 }).map((_, linha) => (
                        <tr key={linha}>
                          {Array.from({ length: maxColuna + 1 }).map((__, coluna) => {
                            const value = getConteudo(linha, coluna);
                            const isSaving = updateCelula.isPending;
                            return (
                              <td key={coluna}>
                                <label>
                                  <span>
                                    L{linha} · C{coluna}
                                  </span>
                                  <textarea
                                    value={value}
                                    onChange={(event) => handleChange(quadro.id, linha, coluna, event.target.value)}
                                    rows={4}
                                  />
                                </label>
                                <button type="button" onClick={() => handleSalvar(quadro.id, linha, coluna)} disabled={isSaving}>
                                  {isSaving ? 'Salvando...' : 'Salvar célula'}
                                </button>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="quadros__empty">
          <h3>Nenhum quadro disponível</h3>
          <p>Ajuste os filtros para visualizar quadros cadastrados.</p>
        </div>
      )}
    </div>
  );
}
