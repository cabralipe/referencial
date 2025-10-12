import { useMemo, useState } from 'react';

import { useWebSocket } from './useWebSocket';

type PresenceEntry = {
  userId: number | null;
  event: 'join' | 'leave' | 'event';
};

type PresenceState = {
  participants: number[];
  lastEvent?: PresenceEntry;
};

type UsePresenceOptions = {
  docType?: string | null;
  objectId?: string | number | null;
  enabled?: boolean;
};

export function usePresence({ docType, objectId, enabled = true }: UsePresenceOptions) {
  const [state, setState] = useState<PresenceState>({ participants: [] });

  const path = useMemo(() => {
    if (!docType || docType.trim().length === 0) {
      return null;
    }
    if (objectId === undefined || objectId === null || `${objectId}`.trim().length === 0) {
      return null;
    }
    return `/ws/presence/${encodeURIComponent(docType)}/${encodeURIComponent(String(objectId))}`;
  }, [docType, objectId]);

  useWebSocket({
    path,
    enabled: enabled && Boolean(path),
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data) as { event?: string; user_id?: number | null };
        if (!data.event) {
          return;
        }
        setState((prev) => {
          const next = new Set(prev.participants);
          if (data.user_id != null) {
            if (data.event === 'join') {
              next.add(data.user_id);
            }
            if (data.event === 'leave') {
              next.delete(data.user_id);
            }
          }
          return {
            participants: Array.from(next),
            lastEvent: {
              userId: data.user_id ?? null,
              event: data.event as PresenceEntry['event'],
            },
          };
        });
      } catch (error) {
        // Ignora payloads inesperados
      }
    },
  });

  return state;
}
