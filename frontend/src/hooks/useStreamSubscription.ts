import { useMemo } from 'react';

import { useWebSocket } from './useWebSocket';

type UseStreamSubscriptionOptions = {
  alvoTipo?: string | null;
  alvoId?: string | number | null;
  enabled?: boolean;
  onMessage?: (event: MessageEvent) => void;
};

export function useStreamSubscription({ alvoTipo, alvoId, enabled = true, onMessage }: UseStreamSubscriptionOptions) {
  const path = useMemo(() => {
    if (!alvoTipo || alvoTipo.trim().length === 0) {
      return null;
    }
    if (alvoId === undefined || alvoId === null || `${alvoId}`.trim().length === 0) {
      return null;
    }
    return `/ws/stream/${encodeURIComponent(alvoTipo)}/${encodeURIComponent(String(alvoId))}`;
  }, [alvoTipo, alvoId]);

  useWebSocket({
    path,
    enabled: enabled && Boolean(path),
    onMessage,
  });
}
