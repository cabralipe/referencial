export type RoleOption = 'membro_gt' | 'revisor' | 'articulador';

export type RoleInfo = {
  label: string;
  title: string;
  does: string[];
  doesNot: string[];
};

export const ROLE_OPTIONS: Record<RoleOption, RoleInfo> = {
  membro_gt: {
    label: 'Articulador',
    title: 'Articulador (membro GT)',
    does: ['Responde tarefas e constrói textos do GT', 'Envia para revisão'],
    doesNot: ['Não publica avisos no mural (isso é do admin)'],
  },
  revisor: {
    label: 'Revisor',
    title: 'Revisor',
    does: ['Comenta por trecho e recomenda ajustes', 'Conclui revisão com checklist'],
    doesNot: ['Não valida oficialmente etapas'],
  },
  articulador: {
    label: 'Redator',
    title: 'Redator',
    does: ['Valida conteúdos e libera etapas', 'Consolida textos e exporta'],
    doesNot: ['Não edita dados administrativos do sistema'],
  },
};
