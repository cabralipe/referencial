import { useEffect, useMemo, useState } from 'react';

import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import { useAreas } from '@/hooks/useAreas';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useQuadros, useUpdateCelulaQuadro } from '@/hooks/useQuadros';

import './QuadrosPage.css';

type CellKey = `${number}-${number}-${number}`;

function buildKey(quadroId: number, linha: number, coluna: number): CellKey {
  return `${quadroId}-${linha}-${coluna}` as const;
}

export function QuadrosPage() {
  const { data: areas, isLoading: isLoadingAreas } = useAreas();
  const { gtOptions } = useAvailableGts();
  const [selectedArea, setSelectedArea] = useState<number | ''>('');
  const [selectedGt, setSelectedGt] = useState<number | ''>('');
  const [templateFilter, setTemplateFilter] = useState('');
  const [drafts, setDrafts] = useState<Record<CellKey, string>>({});
  const [viewMode, setViewMode] = useState<'compact' | 'expanded'>('expanded');

  const { data: quadros, isLoading } = useQuadros({
    areaId: typeof selectedArea === 'number' ? selectedArea : undefined,
    gtId: typeof selectedGt === 'number' ? selectedGt : undefined,
    template: templateFilter || undefined,
  });
  const updateCelula = useUpdateCelulaQuadro();

  const sortedAreas = useMemo(() => {
    if (!areas) return [];
    return [...areas].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'));
  }, [areas]);

  const selectedAreaInfo = useMemo(() => {
    if (typeof selectedArea !== 'number') return null;
    return sortedAreas.find((area) => area.id === selectedArea) ?? null;
  }, [selectedArea, sortedAreas]);

  const filteredGtOptions = useMemo(() => {
    if (!selectedAreaInfo) return gtOptions;
    const allowed = new Set(selectedAreaInfo.gts);
    return gtOptions.filter((gt) => allowed.has(gt.id));
  }, [gtOptions, selectedAreaInfo]);

  const templates = useMemo(() => {
    if (!quadros) return [] as string[];
    return Array.from(new Set(quadros.map((item) => item.template))).sort();
  }, [quadros]);

  useEffect(() => {
    if (!selectedAreaInfo || typeof selectedGt !== 'number') {
      return;
    }
    if (!selectedAreaInfo.gts.includes(selectedGt)) {
      setSelectedGt('');
    }
  }, [selectedAreaInfo, selectedGt]);

  if (isLoadingAreas && !areas) {
    return <FullPageLoader message="Carregando áreas..." />;
  }

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

      {sortedAreas.length > 0 && !selectedAreaInfo ? (
        <section className="quadros__areas">
          <div className="quadros__areas-header">
            <h2>Selecione uma área</h2>
            <p>As áreas definem quais GTs compõem cada conjunto de quadros.</p>
          </div>
          <div className="quadros__areas-grid">
            {sortedAreas.map((area) => (
              <button type="button" key={area.id} className="quadros__area-card" onClick={() => setSelectedArea(area.id)}>
                <strong>{area.nome}</strong>
                {area.descricao_html ? (
                  <div
                    className="quadros__area-description"
                    dangerouslySetInnerHTML={{ __html: area.descricao_html }}
                  />
                ) : null}
                <span>{area.gts.length} GT{area.gts.length === 1 ? '' : 's'}</span>
              </button>
            ))}
          </div>
        </section>
      ) : (
        <>
          {selectedAreaInfo ? (
            <div className="quadros__area-active">
              <div>
                <span>Área selecionada</span>
                <strong>{selectedAreaInfo.nome}</strong>
                {selectedAreaInfo.descricao_html ? (
                  <div
                    className="quadros__area-description"
                    dangerouslySetInnerHTML={{ __html: selectedAreaInfo.descricao_html }}
                  />
                ) : null}
              </div>
              <button type="button" onClick={() => setSelectedArea('')}>
                Trocar área
              </button>
            </div>
          ) : null}

          <div className="quadros__filters">
            <label>
              <span>GT</span>
              <select value={selectedGt} onChange={(event) => setSelectedGt(event.target.value ? Number(event.target.value) : '')}>
                <option value="">Todos</option>
                {filteredGtOptions.map((gt) => (
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

            <div className="quadros__view-toggle">
              <span>Visao</span>
              <button
                type="button"
                className={viewMode === 'compact' ? 'is-active' : ''}
                onClick={() => setViewMode('compact')}
              >
                Compacta
              </button>
              <button
                type="button"
                className={viewMode === 'expanded' ? 'is-active' : ''}
                onClick={() => setViewMode('expanded')}
              >
                Expandida
              </button>
            </div>
          </div>
        </>
      )}

      {sortedAreas.length > 0 && !selectedAreaInfo ? null : quadros && quadros.length > 0 ? (
        <div className="quadros__list">
          {quadros.map((quadro) => {
            const linhasIndex = new Set<number>();
            const colunasIndex = new Set<number>();

            quadro.celulas.forEach((celula) => {
              linhasIndex.add(celula.linha);
              colunasIndex.add(celula.coluna);
            });

            quadro.linhas.forEach((linha) => linhasIndex.add(linha.linha));
            quadro.colunas.forEach((coluna) => colunasIndex.add(coluna.coluna));

            const linhasList = Array.from(linhasIndex);
            const colunasList = Array.from(colunasIndex);
            const minLinha = linhasList.length > 0 ? Math.min(...linhasList) : 0;
            const maxLinha = linhasList.length > 0 ? Math.max(...linhasList) : 0;
            const minColuna = colunasList.length > 0 ? Math.min(...colunasList) : 0;
            const maxColuna = colunasList.length > 0 ? Math.max(...colunasList) : 0;
            const totalLinhas = maxLinha - minLinha;
            const totalColunas = maxColuna - minColuna;
            const rowNames = new Map(quadro.linhas.map((linha) => [linha.linha, linha.nome]));
            const colNames = new Map(quadro.colunas.map((coluna) => [coluna.coluna, coluna.nome]));

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

                <div className={`quadros__grid ${viewMode === 'compact' ? 'quadros__grid--compact' : ''}`}>
                  <div className="quadros__table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th className="quadros__sticky-corner">Linhas \\ Colunas</th>
                          {Array.from({ length: totalColunas + 1 }).map((_, idx) => {
                            const coluna = minColuna + idx;
                            const colLabel = colNames.get(coluna) ?? `Coluna ${coluna}`;
                            return (
                              <th key={coluna} className="quadros__sticky-col">
                                {colLabel}
                              </th>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {Array.from({ length: totalLinhas + 1 }).map((_, idx) => {
                          const linha = minLinha + idx;
                          const rowLabel = rowNames.get(linha) ?? `Linha ${linha}`;
                          return (
                            <tr key={linha}>
                              <th className="quadros__sticky-row">{rowLabel}</th>
                              {Array.from({ length: totalColunas + 1 }).map((__, colIdx) => {
                                const coluna = minColuna + colIdx;
                                const value = getConteudo(linha, coluna);
                                const isSaving = updateCelula.isPending;
                                const colLabel = colNames.get(coluna) ?? `Coluna ${coluna}`;
                                return (
                                  <td key={coluna}>
                                    <label>
                                      <span>
                                        {rowLabel} · {colLabel}
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
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="quadros__empty">
          <h3>Nenhum quadro disponível</h3>
          <p>
            {sortedAreas.length === 0
              ? 'Nenhuma área cadastrada. Cadastre áreas no admin para agrupar os quadros.'
              : 'Ajuste os filtros para visualizar quadros cadastrados.'}
          </p>
        </div>
      )}
    </div>
  );
}
