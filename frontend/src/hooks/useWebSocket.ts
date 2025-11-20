import { useEffect, useRef, useState } from 'react';

type MessageHandler = (event: MessageEvent) => void;
type EventHandler = (event: Event) => void;
type CloseHandler = (event: CloseEvent) => void;

type UseWebSocketOptions = {
  path?: string | null;
  enabled?: boolean;
  onMessage?: MessageHandler;
  onOpen?: EventHandler;
  onClose?: CloseHandler;
  onError?: EventHandler;
  autoReconnect?: boolean;
  reconnectIntervalMs?: number;
};

type WebSocketStatus = 'idle' | 'connecting' | 'open' | 'closed';

type UseWebSocketReturn = {
  status: WebSocketStatus;
  lastError: Event | null;
  lastCloseEvent: CloseEvent | null;
  url: string | null;
};

function resolveWebSocketBaseUrl(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const envBase = import.meta.env.VITE_WS_BASE_URL as string | undefined;
  if (envBase) {
    return envBase.replace(/\/$/, '');
  }
  const apiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (apiBase && apiBase.startsWith('http')) {
    try {
      const parsed = new URL(apiBase);
      const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${parsed.host}`;
    } catch (_err) {
      // fallback para heurística do host atual
    }
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

function buildUrl(path: string): string | null {
  const base = resolveWebSocketBaseUrl();
  if (!base) {
    return null;
  }
  if (path.startsWith('ws://') || path.startsWith('wss://')) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

export function useWebSocket({
  path,
  enabled = true,
  onMessage,
  onOpen,
  onClose,
  onError,
  autoReconnect = true,
  reconnectIntervalMs = 4000,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<WebSocketStatus>('idle');
  const [lastError, setLastError] = useState<Event | null>(null);
  const [lastCloseEvent, setLastCloseEvent] = useState<CloseEvent | null>(null);
  const [url, setUrl] = useState<string | null>(null);

  const messageHandlerRef = useRef<MessageHandler | undefined>(onMessage);
  const openHandlerRef = useRef<EventHandler | undefined>(onOpen);
  const closeHandlerRef = useRef<CloseHandler | undefined>(onClose);
  const errorHandlerRef = useRef<EventHandler | undefined>(onError);

  messageHandlerRef.current = onMessage;
  openHandlerRef.current = onOpen;
  closeHandlerRef.current = onClose;
  errorHandlerRef.current = onError;

  useEffect(() => {
    if (!enabled || !path) {
      setStatus('idle');
      return undefined;
    }

    const url = buildUrl(path);
    if (!url) {
      setStatus('closed');
      setUrl(null);
      return undefined;
    }

    setUrl(url);
    let socket: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let disposed = false;

    const connect = () => {
      if (disposed) {
        return;
      }
      socket = new WebSocket(url);
      setStatus('connecting');

      socket.onopen = (event) => {
        setStatus('open');
        setLastError(null);
        openHandlerRef.current?.(event);
      };

      socket.onmessage = (event) => {
        messageHandlerRef.current?.(event);
      };

      socket.onerror = (event) => {
        setLastError(event);
        errorHandlerRef.current?.(event);
        if (process.env.NODE_ENV !== 'production') {
          console.warn('[ws] erro na conexão', url, event);
        }
      };

      socket.onclose = (event) => {
        setStatus('closed');
        setLastCloseEvent(event);
        closeHandlerRef.current?.(event);
        if (!disposed && autoReconnect && event.code !== 1000) {
          reconnectTimeout = setTimeout(connect, reconnectIntervalMs);
          if (process.env.NODE_ENV !== 'production') {
            console.warn('[ws] reconectando em breve', url, event.code, event.reason);
          }
        }
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      socket?.close(1000, 'component-unmount');
    };
  }, [path, enabled, autoReconnect, reconnectIntervalMs]);

  return { status, lastError, lastCloseEvent, url };
}
