export interface Tarefa {
  id: number;
  nome: string;
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
  gts: number[];
}

export interface GT {
  id: number;
  nome: string;
  etapa: string;
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

export interface TextoColaborativo {
  id: number;
  gt: number;
  titulo: string;
  conteudo_html: string;
  autor: number | null;
  version: number;
  created_at: string;
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

export interface CelulaQuadro {
  id: number;
  quadro: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

export interface Quadro {
  id: number;
  gt: number;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
}

export interface FormularioDinamico {
  id: number;
  nome: string;
  descricao: string;
  ativo: boolean;
}

export interface CampoDinamico {
  id: number;
  formulario: number;
  chave: string;
  tipo: string;
  config_json: Record<string, unknown>;
  obrigatorio: boolean;
  ordem: number;
}

export interface RespostaCampoDinamico {
  id: number;
  formulario: number;
  campo: number;
  valor_texto: string | null;
  valor_num: number | null;
  valor_bool: boolean | null;
  url_arquivo: string | null;
  owner_type: string | null;
  owner_id: number | null;
}

export interface ExportJob {
  id: number;
  alvo_tipo: string;
  alvo_id: number;
  formato: string;
  status: string;
  url_resultado: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface AuditLog {
  id: number;
  cliente: number;
  usuario_id: number | null;
  entidade: string;
  entidade_id: number;
  acao: string;
  diff_json: Record<string, unknown> | null;
  timestamp: string;
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

export interface Midia {
  id: number;
  url: string;
  legenda: string | null;
  tags: string[] | null;
  uploaded_by: number | null;
  created_at: string;
}

export interface BlocoTexto {
  id: number;
  titulo: string;
  conteudo_html: string;
  tags: string[] | null;
  created_by: number | null;
  updated_at: string;
  etag: string;
}

export interface DiffResponse {
  html: string;
}
