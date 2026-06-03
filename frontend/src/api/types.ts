export interface Tarefa {
  id: number;
  nome: string;
  ordem: number;
  etapa: string;
  tipo: 'PERGUNTAS' | 'OFICINA' | string;
  status: 'rascunho' | 'em_desenvolvimento' | 'em_revisao' | 'concluida' | string;
  created_at?: string;
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

export interface Escola {
  id: number;
  nome: string;
}

export interface Area {
  id: number;
  nome: string;
  descricao_html?: string;
  gts: number[];
}

export interface Resposta {
  id: number;
  gt: number;
  gt_nome?: string | null;
  pergunta: number;
  pergunta_ordem?: number | null;
  pergunta_texto?: string | null;
  tarefa_id?: number | null;
  conteudo_html: string;
  autor: number | null;
  autor_nome?: string | null;
  version: number;
  updated_at: string;
  etag: string;
  tarefa_status?: string | null;
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

export interface ThrottleBlock {
  id: number;
  cliente: number | null;
  usuario: number | null;
  usuario_nome?: string | null;
  usuario_email?: string | null;
  scope: string;
  ident: string;
  wait_seconds: number;
  blocked_until: string | null;
  created_at: string;
}

export interface TextoColaborativo {
  id: number;
  gt: number;
  pergunta: number | null;
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
  alvo_preview?: RevisaoAlvoPreview | null;
  status: string;
  parecer_html: string;
  revisor: number | null;
  solicitante: number | null;
  reviewer_recommendation?: {
    id: number;
    decision_type: string;
    checklist: string[];
    note: string;
    created_at: string;
    actor_id: number | null;
  } | null;
  created_at: string;
  updated_at: string;
  etag: string;
}

export type RevisaoAlvoPreview =
  | {
    type: 'resposta';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    pergunta?: number | null;
    pergunta_ordem?: number | null;
    tarefa?: number | null;
    tarefa_nome?: string | null;
    tarefa_etapa?: string | null;
    autor_nome?: string | null;
    conteudo_html?: string;
  }
  | {
    type: 'texto_unico';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    tarefa?: number | null;
    tarefa_nome?: string | null;
    tarefa_etapa?: string | null;
    conteudo_html?: string;
  }
  | {
    type: 'quadro';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    template?: string | null;
  };

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
  area: number | null;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
  linhas: {
    id: number;
    linha: number;
    nome: string;
    ordem: number;
  }[];
  colunas: {
    id: number;
    coluna: number;
    nome: string;
    ordem: number;
  }[];
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
  alvo_id: string;
  payload_json?: Record<string, unknown> | null;
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
  usuario_nome: string | null;
  usuario_email: string | null;
  usuario_last_login: string | null;
  entidade: string;
  entidade_id: number;
  acao: string;
  diff_json: Record<string, unknown> | null;
  timestamp: string;
}

export interface OnlineUser {
  id: number;
  usuario_id: number | null;
  usuario_nome: string | null;
  usuario_email: string | null;
  usuario_role: string | null;
  cliente: number | null;
  first_seen_at: string;
  last_seen_at: string;
  session_duration_seconds?: number;
  device_label?: string | null;
}

export interface Comentario {
  id: number;
  alvo_tipo: string;
  alvo_id: number;
  alvo_preview?: ComentarioAlvoPreview | null;
  anchor_json: string | Record<string, unknown> | null;
  conteudo_html: string;
  resposta_html: string;
  autor: number | null;
  resolvido: boolean;
  resolvido_por: number | null;
  resolved_at: string | null;
  respondido_por: number | null;
  respondido_em: string | null;
  mentions_ids: number[];
  created_at: string;
  updated_at: string;
  etag: string;
}

export type ComentarioAlvoPreview =
  | {
    type: 'resposta';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    tarefa?: number | null;
    tarefa_nome?: string | null;
    pergunta?: number | null;
    pergunta_ordem?: number | null;
    pergunta_texto?: string | null;
  }
  | {
    type: 'texto_unico';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    tarefa?: number | null;
    tarefa_nome?: string | null;
  }
  | {
    type: 'quadro';
    id: number;
    gt?: number | null;
    gt_nome?: string | null;
    template?: string | null;
  }
  | {
    type: 'ppp';
    id: number;
    escola?: number | null;
    escola_nome?: string | null;
    titulo?: string | null;
    status?: string | null;
  };

export interface Notificacao {
  id: number;
  tipo: string;
  payload_json: Record<string, unknown>;
  lida: boolean;
  created_at: string;
}

export interface MuralPost {
  id: string;
  titulo: string;
  conteudo_html: string;
  link_url?: string | null;
  anexos?: Array<{ titulo?: string; url?: string }>;
  modalidade?: 'aviso' | 'recebimento_arquivo' | string;
  fixado?: boolean;
  position?: number;
  ordem?: number;
  gt_ids?: number[];
  criado_por?: {
    id?: number | null;
    nome?: string | null;
    email?: string | null;
  };
  envios_arquivo?: Array<{
    id: number;
    gt_id?: number | null;
    gt_nome?: string | null;
    usuario_id?: number | null;
    usuario_nome?: string | null;
    arquivo_url: string;
    nome_arquivo: string;
    created_at: string;
    updated_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface MuralDownloadRegistro {
  id: number;
  usuario_id?: number | null;
  usuario_nome?: string | null;
  usuario_email?: string | null;
  anexo_index: number;
  anexo_titulo: string;
  anexo_url: string;
  created_at: string;
}

export interface MuralRelatorioItem {
  id: string;
  titulo: string;
  modalidade?: 'aviso' | 'recebimento_arquivo' | string;
  gt_ids?: number[];
  anexos?: Array<{ titulo?: string; url?: string }>;
  total_envios: number;
  envios_arquivo: NonNullable<MuralPost['envios_arquivo']>;
  total_downloads: number;
  downloads: MuralDownloadRegistro[];
  created_at: string;
  updated_at: string;
}

export interface PppDocumento {
  id: number | null;
  escola: number;
  escola_nome: string;
  titulo: string;
  conteudo_html: string;
  status: 'em_elaboracao' | 'concluido' | string;
  ultima_edicao_por: number | null;
  ultima_edicao_por_nome?: string | null;
  concluido_por: number | null;
  concluido_por_nome?: string | null;
  concluido_em: string | null;
  version: number;
  updated_at: string;
  etag: string;
  can_edit: boolean;
  can_comment: boolean;
  can_conclude: boolean;
  comentarios_abertos?: number;
  is_available?: boolean;
  availability_message?: string | null;
}

export interface PppOverviewItem {
  escola_id: number;
  escola_nome: string;
  ppp_id: number | null;
  status: 'em_elaboracao' | 'concluido' | string;
  updated_at: string | null;
  comentarios_abertos: number;
}

export interface CursoAviso {
  id: number;
  titulo: string;
  corpo: string;
  publicado_em: string | null;
}

export interface CursoCronogramaItem {
  id: number;
  semana: string;
  titulo: string;
  descricao: string;
  ordem: number;
}

export interface CursoItem {
  id: number;
  ordem: number;
  tipo: 'VIDEO' | 'TEXTO' | 'CADERNO' | 'TAREFA' | 'FORUM' | 'FORMULARIO' | 'CHECKLIST' | string;
  titulo: string;
  payload_json: Record<string, unknown>;
}

export interface CursoModulo {
  id: number;
  titulo: string;
  ordem: number;
  tipo:
  | 'APRESENTACAO'
  | 'MODULO'
  | 'BANCO_PLANOS'
  | 'FORUM_GERAL'
  | 'BIBLIOTECA'
  | 'ENTREGA_FINAL'
  | string;
  itens: CursoItem[];
}

export interface CursoProgressoItem {
  id: number;
  item_id: number | null;
  referencia_tipo: string;
  referencia_id: string;
  concluido_em: string;
}

export interface CursoProgresso {
  id?: number;
  percentual: number | string;
  itens: CursoProgressoItem[];
}

export interface CursoRegrasCertificacao {
  presenca_presencial_obrigatoria: boolean;
  min_sincronos: number;
  min_planos: number;
  entrega_final_obrigatoria: boolean;
  compartilhar_banco_obrigatorio: boolean;
}

export interface Curso {
  id: number;
  nome: string;
  categoria: string;
  descricao: string;
  objetivos?: string;
  carga_horaria_total?: number;
  carga_presencial?: number;
  carga_sincrona?: number;
  carga_producao?: number;
  publicado: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CursoDetail extends Curso {
  avisos: CursoAviso[];
  cronograma: CursoCronogramaItem[];
  menu: Array<{ id: number; titulo: string; ordem: number; tipo: string }>;
  modulos: CursoModulo[];
  progresso: CursoProgresso;
  regras_certificacao: CursoRegrasCertificacao;
}

export interface CursoCertificacaoStatus {
  regras: CursoRegrasCertificacao;
  checks: Record<string, { required: boolean | number; ok: boolean; value: unknown }>;
  pode_emitir_certificado: boolean;
  certificado_emitido: boolean;
  certificado?: { id: number; codigo: string; emitido_em: string } | null;
}

export interface PlanoAulaPublicacaoResumo {
  id: number;
  status: 'RASCUNHO' | 'ENVIADO' | 'APROVADO' | 'PUBLICADO' | string;
  allow_comments: boolean;
  updated_at: string;
}

export interface PlanoAulaResposta {
  id: number;
  curso: number;
  usuario: number;
  formulario: number;
  titulo: string;
  status: 'RASCUNHO' | 'ENVIADO' | string;
  compartilhado_banco: boolean;
  dados_cache_json: Record<string, string>;
  campos: Record<string, string>;
  publicacao?: PlanoAulaPublicacaoResumo | null;
  enviado_em?: string | null;
  bloqueado_em?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanoAulaPublicacao {
  id: number;
  resposta_formulario_id: number;
  autor: number;
  autor_nome?: string | null;
  status: 'RASCUNHO' | 'ENVIADO' | 'APROVADO' | 'PUBLICADO' | string;
  allow_comments: boolean;
  payload_json: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface Midia {
  id: number;
  titulo: string | null;
  url: string;
  descricao: string | null;
  tags: string[] | null;
  gt?: number | null;
  pergunta?: number | null;
  uploaded_by: number | null;
  created_at: string;
}

export interface BlocoTexto {
  id: number;
  titulo: string;
  conteudo_html: string;
  tags: string[] | null;
  gt?: number | null;
  pergunta?: number | null;
  created_by: number | null;
  updated_at: string;
  etag: string;
}

export interface ConsultaPublica {
  id: number;
  titulo: string;
  slug: string;
  token_acesso: string;
  descricao: string;
  pdf: string;
  pdf_url: string | null;
  imagem_hero?: string | null;
  imagem_hero_url?: string | null;
  data_publicacao: string;
  data_validade: string | null;
  data_fechamento: string | null;
  perguntas_votacao: { pergunta: string; opcoes: string[] }[];
  ativa: boolean;
  public_url: string;
  total_manifestacoes: number;
  created_at: string;
  updated_at: string;
}

export interface ConsultaPublicaPublic {
  titulo: string;
  descricao: string;
  pdf_url: string | null;
  imagem_hero_url?: string | null;
  data_publicacao: string;
  data_validade: string | null;
  data_fechamento: string | null;
  perguntas_votacao: { pergunta: string; opcoes: string[] }[];
  esta_disponivel: boolean;
  total_manifestacoes: number;
}

export interface ManifestacaoPublica {
  id: number;
  consulta: number;
  pagina: number | null;
  comentario: string;
  votos: string[];
  nome_completo: string;
  cpf?: string;
  cidade: string;
  estado: string;
  contato_email: string | null;
  area_atuacao_profissional: string;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

export interface ManifestacaoPublicaPublic {
  id: number;
  pagina: number | null;
  comentario: string;
  votos: string[];
  nome_completo: string;
  cidade: string;
  estado: string;
  area_atuacao_profissional: string;
  created_at: string;
}

export type CampoFormularioTipo = 'text' | 'email' | 'tel' | 'textarea' | 'select' | 'checkbox_group' | 'number';

export interface CampoFormulario {
  chave: string;
  label: string;
  tipo: CampoFormularioTipo;
  obrigatorio: boolean;
  ordem: number;
  ativo: boolean;
  padrao?: boolean;
  opcoes?: string[];
}

export interface FormularioInscricao {
  id: number;
  titulo: string;
  subtitulo: string;
  descricao: string;
  token_acesso: string;
  imagem_hero?: string | null;
  imagem_hero_url?: string | null;
  ativo: boolean;
  opcoes_area_atuacao: string[];
  opcoes_representacao: string[];
  campos_config: CampoFormulario[];
  public_url: string;
  total_inscricoes: number;
  created_at: string;
  updated_at: string;
}

export interface FormularioInscricaoPublic {
  titulo: string;
  subtitulo: string;
  descricao: string;
  imagem_hero_url?: string | null;
  ativo: boolean;
  opcoes_area_atuacao: string[];
  opcoes_representacao: string[];
  campos_config: CampoFormulario[];
  campos_efetivos: CampoFormulario[];
}

export interface InscricaoPublica {
  id: number;
  formulario: number;
  nome_completo: string;
  instituicao_comunidade: string;
  telefone: string;
  email: string;
  areas_atuacao: string[];
  area_atuacao_outro: string;
  representacoes: string[];
  representacao_outro: string;
  dados_extras: Record<string, unknown>;
  ip_address?: string | null;
  created_at: string;
}

export interface DiffResponse {
  html: string;
}

export interface MebThread {
  id: number;
  usuario: number;
  usuario_nome: string | null;
  usuario_email: string | null;
  created_at: string;
  updated_at: string;
  last_message_preview: string | null;
  last_message_origin: 'cliente' | 'admin' | 'meb' | 'sistema' | null;
  last_message_at: string | null;
  total_messages: number;
}

export interface MebMessage {
  id: number;
  thread: number;
  conteudo: string;
  origem: 'cliente' | 'admin' | 'meb' | 'sistema';
  autor: number | null;
  autor_nome: string | null;
  created_at: string;
  is_mine: boolean;
}
