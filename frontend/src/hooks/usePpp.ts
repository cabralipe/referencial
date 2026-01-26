import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PppConfig, PppTrilhasResponse } from '@/api/types';

interface UsePppTrilhasParams {
  gtId?: number | null;
  enabled?: boolean;
}

export function usePppTrilhas({ gtId, enabled = true }: UsePppTrilhasParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['ppp', 'trilhas', { gtId }],
    enabled,
    queryFn: async () => {
      const response = await client.get<PppTrilhasResponse>('/ppp', {
        query: {
          gt_id: gtId ?? undefined,
        },
      });
      return response.data;
    },
  });
}

export function usePppConfig() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['ppp', 'config'],
    queryFn: async () => {
      const response = await client.get<PppConfig>('/ppp/config');
      return response.data;
    },
  });
}

interface UpdatePppConfigInput {
  tarefa_ids: number[];
  descricao?: string;
}

export function useUpdatePppConfig() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: UpdatePppConfigInput) => {
      const response = await client.patch<PppConfig>('/ppp/config', { body: payload });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ppp'] });
      queryClient.invalidateQueries({ queryKey: ['ppp', 'config'] });
    },
  });
}
