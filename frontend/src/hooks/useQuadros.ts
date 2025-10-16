import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { 
  PaginatedResponse, 
  Quadro, 
  CreateQuadroPayload 
} from '@/api/types';

interface UseQuadrosParams {
  gtId?: number | null;
  template?: string | null;
}

export function useQuadros({ gtId, template }: UseQuadrosParams) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(gtId),
    queryKey: ['quadros', gtId, template],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Quadro>>('/quadros', {
        query: {
          gt_id: gtId ?? undefined,
          template: template ?? undefined,
        },
      });
      return response.data.results;
    },
  });
}

export function useQuadro(quadroId?: number | null) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(quadroId),
    queryKey: ['quadro', quadroId],
    queryFn: async () => {
      const response = await client.get<Quadro>(`/quadros/${quadroId}`);
      return response.data;
    },
  });
}

export function useCreateQuadro() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateQuadroPayload) => {
      const response = await client.post<Quadro>('/quadros', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['quadros', data.gt] 
      });
    },
  });
}

interface UpdateCelulaInput {
  quadroId: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

export function useUpdateCelula() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ quadroId, linha, coluna, valor_html }: UpdateCelulaInput) => {
      const response = await client.put(`/quadros/${quadroId}/celula/`, {
        body: {
          linha,
          coluna,
          valor_html,
        },
      });
      return response.data;
    },
    onSuccess: (data, variables) => {
      // Update the specific quadro in cache
      queryClient.setQueryData(
        ['quadro', variables.quadroId],
        (old: Quadro | undefined) => {
          if (!old) return old;
          
          const celulas = old.celulas.map(celula => 
            celula.linha === variables.linha && 
            celula.coluna === variables.coluna
              ? { ...celula, valor_html: variables.valor_html }
              : celula
          );
          
          // If cell doesn't exist, add it
          const cellExists = old.celulas.some(
            celula => celula.linha === variables.linha && celula.coluna === variables.coluna
          );
          
          if (!cellExists) {
            celulas.push({
              id: Date.now(), // Temporary ID until we get the real one from server
              quadro: variables.quadroId,
              linha: variables.linha,
              coluna: variables.coluna,
              valor_html: variables.valor_html,
            });
          }
          
          return { ...old, celulas };
        }
      );
      
      // Also invalidate the quadros list to ensure consistency
      queryClient.invalidateQueries({ 
        queryKey: ['quadros'] 
      });
    },
  });
}

interface GetOrCreateQuadroInput {
  gtId: number;
  template: string;
}

export function useGetOrCreateQuadro() {
  const createQuadro = useCreateQuadro();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ gtId, template }: GetOrCreateQuadroInput) => {
      // First, try to get existing quadro
      const existingQuadros = queryClient.getQueryData<Quadro[]>(['quadros', gtId, template]);
      
      if (existingQuadros && existingQuadros.length > 0) {
        return existingQuadros[0];
      }
      
      // If no existing quadro, create a new one
      return createQuadro.mutateAsync({
        gt: gtId,
        template,
      });
    },
  });
}