import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse, Resposta } from '@/api/types';

export function useAvailableGtIds() {
  const client = useApiClient();

  const query = useQuery({
    queryKey: ['respostas', 'all-gt'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<Resposta>>('/respostas', {
        query: { page_size: 200 },
      });
      return response.data.results ?? [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const gtOptions = useMemo(() => {
    if (!query.data) {
      return [] as number[];
    }
    const unique = new Set<number>();
    for (const resposta of query.data) {
      if (resposta.gt) {
        unique.add(resposta.gt);
      }
    }
    return Array.from(unique).sort((a, b) => a - b);
  }, [query.data]);

  return {
    ...query,
    gtOptions,
  };
}
