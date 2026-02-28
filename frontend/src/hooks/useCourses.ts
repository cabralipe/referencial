import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type {
  Curso,
  CursoCertificacaoStatus,
  CursoDetail,
  PaginatedResponse,
  PlanoAulaPublicacao,
  PlanoAulaResposta,
} from '@/api/types';

function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

export function useCursos() {
  const client = useApiClient();
  return useQuery({
    queryKey: ['cursos'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Curso> | Curso[]>('/cursos', { query: { page_size: 200 } });
      return unwrapList(response.data);
    },
  });
}

export function useCurso(cursoId?: string | number) {
  const client = useApiClient();
  return useQuery({
    enabled: Boolean(cursoId),
    queryKey: ['cursos', cursoId],
    queryFn: async () => {
      const response = await client.get<CursoDetail>(`/cursos/${cursoId}`);
      return response.data;
    },
  });
}

export function useUpdateCurso() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ cursoId, payload }: { cursoId: number; payload: Record<string, unknown> }) => {
      const response = await client.patch<CursoDetail>(`/cursos/${cursoId}`, { body: payload });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['cursos'] });
      queryClient.invalidateQueries({ queryKey: ['cursos', data.id] });
    },
  });
}

export function useCreateCurso() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const response = await client.post<Curso>(`/cursos`, { body: payload });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cursos'] });
    },
  });
}

export function useMarcarProgresso(cursoId?: number) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      if (!cursoId) throw new Error('cursoId ausente');
      const response = await client.post<{ ok: boolean; progresso: { id: number; percentual: number } }>(
        `/cursos/${cursoId}/progresso`,
        { body: { item_id: itemId } },
      );
      return response.data;
    },
    onSuccess: () => {
      if (!cursoId) return;
      queryClient.invalidateQueries({ queryKey: ['cursos', cursoId] });
      queryClient.invalidateQueries({ queryKey: ['cursos', String(cursoId)] });
      queryClient.invalidateQueries({ queryKey: ['cursos'] });
    },
  });
}

export function useCertificacaoStatus(cursoId?: number) {
  const client = useApiClient();
  return useQuery({
    enabled: Boolean(cursoId),
    queryKey: ['cursos', cursoId, 'certificacao', 'status'],
    queryFn: async () => {
      const response = await client.get<CursoCertificacaoStatus>(`/cursos/${cursoId}/certificacao/status`);
      return response.data;
    },
  });
}

export function useEmitirCertificado(cursoId?: number) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!cursoId) throw new Error('cursoId ausente');
      const response = await client.post<{ codigo: string; emitido_em: string; stub: boolean }>(
        `/cursos/${cursoId}/certificacao/emitir`,
        { body: {} },
      );
      return response.data;
    },
    onSuccess: () => {
      if (!cursoId) return;
      queryClient.invalidateQueries({ queryKey: ['cursos', cursoId, 'certificacao', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['cursos', cursoId] });
    },
  });
}

export function usePlanosAula(cursoId?: number) {
  const client = useApiClient();
  return useQuery({
    enabled: Boolean(cursoId),
    queryKey: ['planos-aula', { cursoId }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<PlanoAulaResposta> | PlanoAulaResposta[]>('/planos-aula', {
        query: { curso: cursoId, page_size: 200 },
      });
      return unwrapList(response.data);
    },
  });
}

export function useCreatePlanoAula(cursoId?: number) {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { titulo?: string; campos: Record<string, string> }) => {
      if (!cursoId) throw new Error('cursoId ausente');
      const response = await client.post<PlanoAulaResposta>('/planos-aula', {
        body: { curso: cursoId, ...payload },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['planos-aula', { cursoId }] });
      queryClient.invalidateQueries({ queryKey: ['cursos', cursoId] });
    },
  });
}

export function useUpdatePlanoAula() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, cursoId, payload }: { id: number; cursoId: number; payload: { titulo?: string; campos?: Record<string, string> } }) => {
      const response = await client.patch<PlanoAulaResposta>(`/planos-aula/${id}`, { body: { curso: cursoId, ...payload } });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['planos-aula', { cursoId: variables.cursoId }] });
      queryClient.invalidateQueries({ queryKey: ['cursos', variables.cursoId] });
    },
  });
}

export function useEnviarPlanoAula() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      cursoId,
      compartilharNoBanco,
    }: {
      id: number;
      cursoId: number;
      compartilharNoBanco: boolean;
    }) => {
      const response = await client.post<{ plano: PlanoAulaResposta; publicacao: PlanoAulaPublicacao }>(`/planos-aula/${id}/enviar`, {
        body: { compartilhar_no_banco: compartilharNoBanco },
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['planos-aula', { cursoId: variables.cursoId }] });
      queryClient.invalidateQueries({ queryKey: ['cursos', variables.cursoId] });
      queryClient.invalidateQueries({ queryKey: ['banco-planos'] });
    },
  });
}

export function useBancoPlanos(params: { componente?: string; etapaModalidade?: string; status?: string } = {}) {
  const client = useApiClient();
  return useQuery({
    queryKey: ['banco-planos', params],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<PlanoAulaPublicacao> | PlanoAulaPublicacao[]>('/banco-planos', {
        query: {
          componente: params.componente,
          etapa_modalidade: params.etapaModalidade,
          status: params.status,
          page_size: 200,
        },
      });
      return unwrapList(response.data);
    },
  });
}

export function useUpdateBancoPlano() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, allowComments }: { id: number; status: string; allowComments?: boolean }) => {
      const response = await client.patch<PlanoAulaPublicacao>(`/banco-planos/${id}`, {
        body: { status, allow_comments: allowComments },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['banco-planos'] });
      queryClient.invalidateQueries({ queryKey: ['planos-aula'] });
    },
  });
}
