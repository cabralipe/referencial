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
