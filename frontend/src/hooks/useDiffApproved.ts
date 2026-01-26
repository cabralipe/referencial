import { useMutation } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { DiffResponse } from '@/api/types';

interface DiffApprovedInput {
  alvoTipo: string;
  alvoId: number;
}

export function useDiffApproved() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async ({ alvoTipo, alvoId }: DiffApprovedInput) => {
      const response = await client.get<DiffResponse>('/diff/aprovado', {
        query: {
          alvo_tipo: alvoTipo,
          alvo_id: alvoId,
        },
      });
      return response.data;
    },
  });
}
