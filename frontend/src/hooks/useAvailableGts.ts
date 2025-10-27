import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { GT, PaginatedResponse } from '@/api/types';

export interface GtOption extends GT {
  displayName: string;
}

export function useAvailableGts() {
  const client = useApiClient();

  const query = useQuery({
    queryKey: ['gts', 'available'],
    queryFn: async () => {
      const response = await client.get<PaginatedResponse<GT>>('/gts', {
        query: { page_size: 200 },
      });
      return response.data.results ?? [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const gtOptions = useMemo(() => {
    if (!query.data) {
      return [] as GtOption[];
    }

    const nameCounts = new Map<string, number>();
    const nameStageCounts = new Map<string, number>();

    query.data.forEach((gt) => {
      const normalizedName = gt.nome.trim();
      nameCounts.set(normalizedName, (nameCounts.get(normalizedName) ?? 0) + 1);
      const etapaKey = `${normalizedName}||${(gt.etapa ?? '').trim()}`;
      nameStageCounts.set(etapaKey, (nameStageCounts.get(etapaKey) ?? 0) + 1);
    });

    return query.data
      .map((gt): GtOption => {
        const normalizedName = gt.nome.trim();
        let displayName = normalizedName;
        if ((nameCounts.get(normalizedName) ?? 0) > 1) {
          const etapa = (gt.etapa ?? '').trim();
          const etapaKey = `${normalizedName}||${etapa}`;
          if (etapa && (nameStageCounts.get(etapaKey) ?? 0) === 1) {
            displayName = `${normalizedName} - ${etapa}`;
          } else {
            displayName = `${normalizedName} - #${gt.id}`;
          }
        }
        return {
          ...gt,
          displayName,
        };
      })
      .sort((a, b) => a.displayName.localeCompare(b.displayName, 'pt-BR'));
  }, [query.data]);

  return {
    ...query,
    gtOptions,
  };
}
