export interface Tarefa {
  id: number;
  ordem: number;
  etapa: string;
  tipo: 'PERGUNTAS' | 'OFICINA' | string;
  status: 'rascunho' | 'em_revisao' | 'concluida' | string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Pergunta {
  id: number;
  tarefa: number;
  ordem: number;
  texto: string;
  permite_upload: boolean;
  obrigatoria: boolean;
}

export interface Resposta {
  id: number;
  gt: number;
  pergunta: number;
  conteudo_html: string;
  autor: number | null;
  version: number;
  updated_at: string;
  etag: string;
}

// GT (Grupo de Trabalho) interface
export interface GT {
  id: number;
  nome: string;
  etapa: string;
  membros: number[];
  cliente: number;
  created_at: string;
  updated_at: string;
}

export interface TextoUnico {
  id: number;
  gt: number;
  tarefa: number;
  conteudo_html: string;
  responsavel: number | null;
  version: number;
  updated_at: string;
  etag: string;
}

// Payload types for TextoUnico operations
export interface CreateTextoUnicoPayload {
  gt: number;
  tarefa: number;
  conteudo_html: string;
}

export interface UpdateTextoUnicoPayload {
  conteudo_html: string;
}

// User interface
export interface User {
  id: number;
  name: string;
  email: string;
  perfil?: string;
}

// Reviews System Types
export type ReviewTargetType = 'resposta' | 'texto_unico' | 'quadro';
export type ReviewStatus = 'rascunho' | 'em_revisao' | 'aprovado' | 'reprovado';

export interface Review {
  id: number;
  alvo_tipo: ReviewTargetType;
  alvo_id: string;
  status: ReviewStatus;
  parecer_html: string;
  revisor: User | null;
  solicitante: User | null;
  created_at: string;
  updated_at: string;
  etag: string;
}

// Legacy interface for backward compatibility
export interface Revisao {
  id: number;
  alvo_tipo: string;
  alvo_id: number;
  status: string;
  parecer_html: string;
  revisor: number | null;
  solicitante: number | null;
  created_at: string;
  updated_at: string;
  etag: string;
}

export interface Comentario {
  id: number;
  alvo_tipo: string;
  alvo_id: number;
  anchor_json: string;
  conteudo_html: string;
  autor: number | null;
  resolvido: boolean;
  resolvido_por: number | null;
  resolved_at: string | null;
  mentions_ids: number[];
  created_at: string;
  updated_at: string;
  etag: string;
}

export interface Notificacao {
  id: number;
  tipo: string;
  payload_json: Record<string, unknown>;
  lida: boolean;
  created_at: string;
}

// Quadros (Oficinas) interfaces
export interface Quadro {
  id: number;
  gt: number;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
  created_at: string;
  updated_at: string;
}

export interface CelulaQuadro {
  id: number;
  quadro: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

// Template configuration interfaces
export interface QuadroTemplate {
  id: string;
  nome: string;
  descricao: string;
  linhas: number;
  colunas: number;
  cabecalhos?: {
    linhas?: string[];
    colunas?: string[];
  };
  configuracao?: {
    celulasFixas?: Array<{
      linha: number;
      coluna: number;
      valor: string;
      editavel: boolean;
    }>;
    estilos?: {
      [key: string]: React.CSSProperties;
    };
  };
}

// Payload types for Quadro operations
export interface UpdateCelulaPayload {
  linha: number;
  coluna: number;
  valor_html: string;
}

export interface CreateQuadroPayload {
  gt: number;
  template: string;
}

// Component state interfaces
export interface QuadroState {
  quadro: Quadro | null;
  loading: boolean;
  error: string | null;
  editingCell: { linha: number; coluna: number } | null;
  unsavedChanges: boolean;
}
