import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { PaginatedResponse } from '@/api/types';

export interface UsuarioSuggestion {
  id: number;
  nome: string;
  email: string;
}

export function useUsuariosLookup(q: string) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['usuarios-lookup', { q }],
    enabled: q.trim().length >= 2,
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<UsuarioSuggestion>>('/usuarios/lookup', {
        query: { search: q, page_size: 10 },
      });
      return response.data.results ?? [];
    },
    staleTime: 5 * 60 * 1000,
  });
}
