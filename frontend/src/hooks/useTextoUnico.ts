import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, TextoUnico } from '@/api/types';

interface UseTextoUnicoParams {
  gtId?: number;
  tarefaId?: number;
  includeAll?: boolean;
}

export function useTextoUnicos({ gtId, tarefaId, includeAll = false }: UseTextoUnicoParams = {}) {
  const client = useApiClient();

  return useQuery({
    enabled: includeAll || Boolean(gtId || tarefaId),
    queryKey: ['texto-unico', { gtId, tarefaId, includeAll }],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<TextoUnico>>('/texto_unico', {
        query: {
          gt_id: gtId,
          gt: gtId,
          tarefa_id: tarefaId,
          tarefa: tarefaId,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

interface GenerateTextoUnicoInput {
  gtId: number;
  tarefaId: number;
}

export function useGenerateTextoUnico() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ gtId, tarefaId }: GenerateTextoUnicoInput) => {
      const response = await client.post<TextoUnico>('/texto_unico/gerar', {
        body: {
          gt_id: gtId,
          tarefa_id: tarefaId,
        },
      });
      return response.data;
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['texto-unico', { gtId: variables.gtId, tarefaId: variables.tarefaId }] });
    },
  });
}
