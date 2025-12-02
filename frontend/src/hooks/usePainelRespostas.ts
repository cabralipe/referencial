import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, Resposta } from '@/api/types';

export function usePainelRespostas() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['respostas', 'painel'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
        query: { page_size: 200 },
      });
      return response.data.results ?? [];
    },
    staleTime: 30 * 1000,
  });
}
