import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, Tarefa } from '@/api/types';

interface UseTarefasParams {
  etapa?: string;
  tipo?: string;
  status?: string;
  gtId?: number | null;
}

export function useTarefas(params: UseTarefasParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['tarefas', params],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Tarefa>>('/tarefas', {
        query: {
          ...params,
          gt_id: params.gtId ?? undefined,
          page_size: 200,
        },
      });
      return response.data.results ?? [];
    },
  });
}

export function useTarefa(tarefaId?: string) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(tarefaId),
    queryKey: ['tarefa', tarefaId],
    queryFn: async () => {
      const response = await client.get<Tarefa>(`/tarefas/${tarefaId}`);
      return response.data;
    },
  });
}
