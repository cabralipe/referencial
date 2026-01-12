import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useApiClient } from '@/api/client';
import type { ThrottleBlock } from '@/api/types';

interface UseThrottleBlocksParams {
  showAll?: boolean;
}

export function useThrottleBlocks({ showAll = false }: UseThrottleBlocksParams = {}) {
  const client = useApiClient();

  return useQuery({
    queryKey: ['throttle-blocks', { showAll }],
    queryFn: async () => {
      const response = await client.get<ThrottleBlock[]>('/throttle_blocks', {
        query: { show_all: showAll ? '1' : undefined },
      });
      return response.data ?? [];
    },
    refetchInterval: 30_000,
    staleTime: 20_000,
  });
}

export function useClearThrottleBlock() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (blockId: number) => {
      await client.del(`/throttle_blocks/${blockId}`);
      return blockId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['throttle-blocks'] });
    },
  });
}
