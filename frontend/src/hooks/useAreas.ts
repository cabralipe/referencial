import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { Area, PaginatedResponse } from '@/api/types';

export function useAreas() {
  const client = useApiClient();

  return useQuery({
    queryKey: ['areas'],
    queryFn: async () => {
      const collected: Area[] = [];
      let nextUrl: string | null = null;
      let currentUrl: string = '/areas';
      let firstFetch = true;

      do {
        const response = await client.get<PaginatedResponse<Area>>(currentUrl, {
          query: firstFetch ? { page_size: 200 } : undefined,
        });
        const { results = [], next } = response.data;
        collected.push(...results);
        nextUrl = next ?? null;
        if (nextUrl) {
          currentUrl = nextUrl;
        }
        firstFetch = false;
      } while (nextUrl);

      return collected;
    },
    staleTime: 5 * 60 * 1000,
  });
}
