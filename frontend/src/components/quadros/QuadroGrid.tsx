import { useState } from 'react';
import type { Quadro, QuadroTemplate, CelulaQuadro } from '@/api/types';
import { QuadroCell } from './QuadroCell';
import './QuadroGrid.css';

interface QuadroGridProps {
  quadro: Quadro;
  template: QuadroTemplate;
  onCellUpdate: (linha: number, coluna: number, valor: string) => void;
  onOpenCellComments?: (linha: number, coluna: number) => void;
  readonly?: boolean;
}

export function QuadroGrid({
  quadro,
  template,
  onCellUpdate,
  onOpenCellComments,
  readonly = false,
}: QuadroGridProps) {
  const [editingCell, setEditingCell] = useState<{
    linha: number;
    coluna: number;
  } | null>(null);

  // Create matrix of cells
  const criarMatriz = (): (CelulaQuadro | null)[][] => {
    const matriz: (CelulaQuadro | null)[][] = [];
    
    for (let linha = 0; linha < template.linhas; linha++) {
      matriz[linha] = [];
      for (let coluna = 0; coluna < template.colunas; coluna++) {
        const celula = quadro.celulas.find(
          c => c.linha === linha && c.coluna === coluna
        );
        matriz[linha][coluna] = celula || null;
      }
    }
    
    return matriz;
  };

  const matriz = criarMatriz();

  const handleStartEdit = (linha: number, coluna: number) => {
    if (!readonly) {
      setEditingCell({ linha, coluna });
    }
  };

  const handleFinishEdit = (linha: number, coluna: number, valor: string) => {
    onCellUpdate(linha, coluna, valor);
    setEditingCell(null);
  };

  return (
    <div className="quadro-grid-container">
      <div className="quadro-grid">
        {/* Column headers */}
        {template.cabecalhos?.colunas && (
          <div className="grid-header-row">
            {/* Corner cell for row headers */}
            {template.cabecalhos?.linhas && (
              <div className="grid-corner"></div>
            )}
            {template.cabecalhos.colunas.map((cabecalho, index) => (
              <div key={index} className="grid-header-cell column-header">
                {cabecalho}
              </div>
            ))}
          </div>
        )}

        {/* Data rows */}
        {matriz.map((linha, linhaIndex) => (
          <div key={linhaIndex} className="grid-row">
            {/* Row header */}
            {template.cabecalhos?.linhas && (
              <div className="grid-header-cell row-header">
                {template.cabecalhos.linhas[linhaIndex]}
              </div>
            )}

            {/* Data cells */}
            {linha.map((celula, colunaIndex) => (
              <QuadroCell
                key={`${linhaIndex}-${colunaIndex}`}
                celula={celula}
                linha={linhaIndex}
                coluna={colunaIndex}
                template={template}
                isEditing={
                  editingCell?.linha === linhaIndex &&
                  editingCell?.coluna === colunaIndex
                }
                onStartEdit={() => handleStartEdit(linhaIndex, colunaIndex)}
                onFinishEdit={(valor) => handleFinishEdit(linhaIndex, colunaIndex, valor)}
                onOpenComments={onOpenCellComments}
                readonly={readonly}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}