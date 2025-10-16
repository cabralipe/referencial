import { QuadroTemplate } from '../api/types';

export const QUADRO_TEMPLATES: Record<string, QuadroTemplate> = {
  swot: {
    id: 'swot',
    nome: 'Análise SWOT',
    descricao: 'Matriz de Forças, Fraquezas, Oportunidades e Ameaças',
    linhas: 2,
    colunas: 2,
    cabecalhos: {
      linhas: ['Fatores Internos', 'Fatores Externos'],
      colunas: ['Positivos', 'Negativos'],
    },
    configuracao: {
      celulasFixas: [
        { linha: 0, coluna: 0, valor: '<strong>FORÇAS</strong><br><small>Características internas positivas</small>', editavel: false },
        { linha: 0, coluna: 1, valor: '<strong>FRAQUEZAS</strong><br><small>Características internas negativas</small>', editavel: false },
        { linha: 1, coluna: 0, valor: '<strong>OPORTUNIDADES</strong><br><small>Fatores externos positivos</small>', editavel: false },
        { linha: 1, coluna: 1, valor: '<strong>AMEAÇAS</strong><br><small>Fatores externos negativos</small>', editavel: false },
      ],
      estilos: {
        'cell-0-0': { backgroundColor: '#d4edda', borderColor: '#28a745' },
        'cell-0-1': { backgroundColor: '#f8d7da', borderColor: '#dc3545' },
        'cell-1-0': { backgroundColor: '#d1ecf1', borderColor: '#17a2b8' },
        'cell-1-1': { backgroundColor: '#fff3cd', borderColor: '#ffc107' },
      },
    },
  },

  canvas: {
    id: 'canvas',
    nome: 'Business Model Canvas',
    descricao: 'Modelo de 9 blocos para planejamento de negócios',
    linhas: 3,
    colunas: 5,
    cabecalhos: {
      colunas: [
        'Parcerias Chave',
        'Atividades Chave',
        'Proposta de Valor',
        'Relacionamento',
        'Segmentos de Cliente'
      ],
    },
    configuracao: {
      celulasFixas: [
        { linha: 0, coluna: 0, valor: '<strong>Parcerias Chave</strong><br><small>Quem são nossos parceiros e fornecedores?</small>', editavel: false },
        { linha: 0, coluna: 1, valor: '<strong>Atividades Chave</strong><br><small>Que atividades nossa proposta de valor requer?</small>', editavel: false },
        { linha: 0, coluna: 2, valor: '<strong>Proposta de Valor</strong><br><small>Que valor entregamos ao cliente?</small>', editavel: false },
        { linha: 0, coluna: 3, valor: '<strong>Relacionamento</strong><br><small>Que tipo de relacionamento cada segmento espera?</small>', editavel: false },
        { linha: 0, coluna: 4, valor: '<strong>Segmentos de Cliente</strong><br><small>Para quem criamos valor?</small>', editavel: false },
        { linha: 1, coluna: 1, valor: '<strong>Recursos Chave</strong><br><small>Que recursos nossa proposta de valor requer?</small>', editavel: false },
        { linha: 1, coluna: 3, valor: '<strong>Canais</strong><br><small>Como chegamos aos nossos clientes?</small>', editavel: false },
        { linha: 2, coluna: 0, valor: '<strong>Estrutura de Custos</strong><br><small>Quais são os custos mais importantes?</small>', editavel: false },
        { linha: 2, coluna: 4, valor: '<strong>Fontes de Receita</strong><br><small>Por que valor nossos clientes pagam?</small>', editavel: false },
      ],
    },
  },

  brainstorm: {
    id: 'brainstorm',
    nome: 'Quadro de Brainstorming',
    descricao: 'Grade livre para organização de ideias',
    linhas: 4,
    colunas: 4,
    cabecalhos: {
      colunas: ['Ideias A', 'Ideias B', 'Ideias C', 'Ideias D'],
    },
  },

  decisao: {
    id: 'decisao',
    nome: 'Matriz de Decisão',
    descricao: 'Critérios vs. Alternativas para tomada de decisão',
    linhas: 5,
    colunas: 4,
    cabecalhos: {
      linhas: ['Critério 1', 'Critério 2', 'Critério 3', 'Critério 4', 'TOTAL'],
      colunas: ['Alternativa A', 'Alternativa B', 'Alternativa C', 'Melhor Opção'],
    },
    configuracao: {
      celulasFixas: [
        { linha: 4, coluna: 0, valor: '<strong>TOTAL</strong>', editavel: false },
        { linha: 4, coluna: 1, valor: '<strong>TOTAL</strong>', editavel: false },
        { linha: 4, coluna: 2, valor: '<strong>TOTAL</strong>', editavel: false },
        { linha: 4, coluna: 3, valor: '<strong>MELHOR OPÇÃO</strong>', editavel: false },
      ],
      estilos: {
        'row-4': { backgroundColor: '#f8f9fa', fontWeight: 'bold' },
      },
    },
  },

  retrospectiva: {
    id: 'retrospectiva',
    nome: 'Retrospectiva',
    descricao: 'O que funcionou, o que melhorar, próximas ações',
    linhas: 1,
    colunas: 3,
    cabecalhos: {
      colunas: ['O que funcionou bem?', 'O que pode melhorar?', 'Próximas ações'],
    },
    configuracao: {
      estilos: {
        'cell-0-0': { backgroundColor: '#d4edda', borderColor: '#28a745' },
        'cell-0-1': { backgroundColor: '#fff3cd', borderColor: '#ffc107' },
        'cell-0-2': { backgroundColor: '#d1ecf1', borderColor: '#17a2b8' },
      },
    },
  },
};

// Helper function to get template by ID
export const getTemplate = (templateId: string): QuadroTemplate | null => {
  return QUADRO_TEMPLATES[templateId] || null;
};

// Helper function to get all available templates
export const getAllTemplates = (): QuadroTemplate[] => {
  return Object.values(QUADRO_TEMPLATES);
};

// Helper function to check if a cell is fixed (non-editable)
export const isCellFixed = (template: QuadroTemplate, linha: number, coluna: number): boolean => {
  if (!template.configuracao?.celulasFixas) return false;
  
  return template.configuracao.celulasFixas.some(
    celula => celula.linha === linha && celula.coluna === coluna && !celula.editavel
  );
};

// Helper function to get fixed cell value
export const getFixedCellValue = (template: QuadroTemplate, linha: number, coluna: number): string | null => {
  if (!template.configuracao?.celulasFixas) return null;
  
  const celulaFixa = template.configuracao.celulasFixas.find(
    celula => celula.linha === linha && celula.coluna === coluna
  );
  
  return celulaFixa?.valor || null;
};

// Helper function to get cell styles
export const getCellStyles = (template: QuadroTemplate, linha: number, coluna: number): React.CSSProperties => {
  if (!template.configuracao?.estilos) return {};
  
  const cellKey = `cell-${linha}-${coluna}`;
  const rowKey = `row-${linha}`;
  const colKey = `col-${coluna}`;
  
  return {
    ...template.configuracao.estilos[cellKey],
    ...template.configuracao.estilos[rowKey],
    ...template.configuracao.estilos[colKey],
  };
};