import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { GT, PaginatedResponse } from '@/api/types';
import { useAuth } from '@/context/AuthContext';

export interface GtOption extends GT {
  displayName: string;
}

export type GtScope = 'member' | 'all';

interface UseAvailableGtsOptions {
  scope?: GtScope;
}

export function useAvailableGts({ scope = 'member' }: UseAvailableGtsOptions = {}) {
  const client = useApiClient();
  const { user } = useAuth();

  const effectiveScope: GtScope = useMemo(() => {
    if (scope !== 'member') {
      return scope;
    }
    if (user?.role === 'admin_cliente' || user?.role === 'articulador' || user?.role === 'super_admin') {
      return 'all';
    }
    return scope;
  }, [scope, user?.role]);

  const query = useQuery({
    queryKey: ['gts', 'available', effectiveScope],
    queryFn: async () => {
      const collected: GT[] = [];
      let nextUrl: string | null = null;
      let currentUrl: string = '/gts';
      let firstFetch = true;

      do {
        const response = await client.get<PaginatedResponse<GT>>(currentUrl, {
          query: firstFetch
            ? { page_size: 200, ...(effectiveScope === 'member' ? { only_member: 'true' } : {}) }
            : undefined,
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
