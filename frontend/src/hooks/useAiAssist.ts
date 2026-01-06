import { useMutation } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';

export type AiMode = 'draft' | 'grammar' | 'review';

interface AiAssistInput {
  mode: AiMode;
  text: string;
  context?: string;
}

interface AiAssistResponse {
  output: string;
}

export function useAiAssist() {
  const client = useApiClient();

  return useMutation({
    mutationFn: async (payload: AiAssistInput) => {
      const response = await client.post<AiAssistResponse>('/ai/assist', {
        body: payload,
      });
      return response.data;
    },
  });
}
