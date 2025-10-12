import { useMutation } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { DiffResponse } from '@/api/types';

interface BuildDiffInput {
  alvoTipo: string;
  alvoId: number;
  fromVersion: number;
  toVersion: number;
}

export function useBuildDiff() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async ({ alvoId, alvoTipo, fromVersion, toVersion }: BuildDiffInput) => {
      const response = await client.get<DiffResponse>('/diff', {
        query: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
          from: fromVersion,
          to: toVersion,
        },
      });
      return response.data;
    },
  });
}
