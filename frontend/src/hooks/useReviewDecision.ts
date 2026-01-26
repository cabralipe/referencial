import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { Revisao } from '@/api/types';

interface ReviewDecisionInput {
  revisaoId: number;
  decision: 'approve' | 'return';
  checklist?: string[];
  note?: string;
  etag?: string;
}

export function useReviewDecision() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ revisaoId, decision, checklist, note, etag }: ReviewDecisionInput) => {
      const response = await client.post<Revisao>(`/revisoes/${revisaoId}/decisao`, {
        body: { decision, checklist, note },
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['revisoes'] });
    },
  });
}
