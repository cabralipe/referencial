import { useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';

interface WebSocketMessage {
  type: string;
  payload?: any;
}

interface MediaWebSocketHookOptions {
  onFileUploaded?: (payload: any) => void;
  onFileUpdated?: (payload: any) => void;
  onFileDeleted?: (payload: any) => void;
  onFileMoved?: (payload: any) => void;
  onFolderCreated?: (payload: any) => void;
  onFolderUpdated?: (payload: any) => void;
  onFolderDeleted?: (payload: any) => void;
  onFileShared?: (payload: any) => void;
  onFileUnshared?: (payload: any) => void;
  onUploadProgress?: (payload: any) => void;
  onProcessingStarted?: (payload: any) => void;
  onProcessingCompleted?: (payload: any) => void;
  onProcessingFailed?: (payload: any) => void;
  autoReconnect?: boolean;
  showToasts?: boolean;
}

export const useMediaWebSocket = (options: MediaWebSocketHookOptions = {}) => {
  console.log('🚀 useMediaWebSocket hook inicializado');
  
  const { isAuthenticated } = useAuth();
  
  const {
    onFileUploaded,
    onFileUpdated,
    onFileDeleted,
    onFileMoved,
    onFolderCreated,
    onFolderUpdated,
    onFolderDeleted,
    onFileShared,
    onFileUnshared,
    onUploadProgress,
    onProcessingStarted,
    onProcessingCompleted,
    onProcessingFailed,
    autoReconnect = true,
    showToasts = true
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  const connect = useCallback(() => {
    console.log('🔌 Tentando conectar WebSocket...');
    
    // Só conectar se o usuário estiver autenticado
    if (!isAuthenticated) {
      console.log('🔌 Usuário não autenticado, não conectando WebSocket');
      return;
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('🔌 WebSocket já está conectado');
      return;
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Use the backend server port (8001) for WebSocket connection
      const backendHost = window.location.hostname + ':8001';
      
      // Get session ID from cookies
      const sessionId = document.cookie
        .split('; ')
        .find(row => row.startsWith('sessionid='))
        ?.split('=')[1];
      
      // Include session ID in WebSocket URL if available
      const wsUrl = sessionId 
        ? `${protocol}//${backendHost}/ws/media-library/?sessionid=${sessionId}`
        : `${protocol}//${backendHost}/ws/media-library/`;
      
      console.log('🔌 Conectando ao WebSocket:', wsUrl);
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('✅ Conectado ao WebSocket da biblioteca de mídia');
        reconnectAttemptsRef.current = 0;
        
        if (showToasts) {
          toast.success('Conectado à biblioteca de mídia');
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📨 Mensagem WebSocket recebida:', message);
          handleMessage(message);
        } catch (error) {
          console.error('Erro ao processar mensagem WebSocket:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('❌ Conexão WebSocket fechada:', event.code, event.reason);
        
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`🔄 Tentativa de reconexão ${reconnectAttemptsRef.current}/${maxReconnectAttempts}`);
            connect();
          }, reconnectDelay);
        } else if (showToasts && reconnectAttemptsRef.current >= maxReconnectAttempts) {
          toast.error('Falha ao conectar com a biblioteca de mídia');
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('❌ Erro no WebSocket:', error);
      };

    } catch (error) {
      console.error('Erro ao conectar WebSocket:', error);
    }
  }, [isAuthenticated, autoReconnect, showToasts]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    const { type, payload } = message;

    switch (type) {
      case 'connection.established':
        console.log('Conexão WebSocket estabelecida');
        break;

      case 'file.uploaded':
        onFileUploaded?.(payload);
        if (showToasts) {
          toast.success(`Arquivo "${payload.name}" enviado com sucesso`);
        }
        break;

      case 'file.updated':
        onFileUpdated?.(payload);
        if (showToasts) {
          toast.info(`Arquivo "${payload.name}" atualizado`);
        }
        break;

      case 'file.deleted':
        onFileDeleted?.(payload);
        if (showToasts) {
          toast.info('Arquivo removido');
        }
        break;

      case 'file.moved':
        onFileMoved?.(payload);
        if (showToasts) {
          toast.info(`Arquivo "${payload.name}" movido`);
        }
        break;

      case 'folder.created':
        onFolderCreated?.(payload);
        if (showToasts) {
          toast.success(`Pasta "${payload.name}" criada`);
        }
        break;

      case 'folder.updated':
        onFolderUpdated?.(payload);
        if (showToasts) {
          toast.info(`Pasta "${payload.name}" atualizada`);
        }
        break;

      case 'folder.deleted':
        onFolderDeleted?.(payload);
        if (showToasts) {
          toast.info('Pasta removida');
        }
        break;

      case 'file.shared':
        onFileShared?.(payload);
        if (showToasts) {
          toast.success('Arquivo compartilhado');
        }
        break;

      case 'file.unshared':
        onFileUnshared?.(payload);
        if (showToasts) {
          toast.info('Compartilhamento removido');
        }
        break;

      case 'upload.progress':
        onUploadProgress?.(payload);
        break;

      case 'processing.started':
        onProcessingStarted?.(payload);
        if (showToasts) {
          toast.info(`Processando "${payload.file_name}"...`);
        }
        break;

      case 'processing.completed':
        onProcessingCompleted?.(payload);
        if (showToasts) {
          toast.success(`"${payload.file_name}" processado com sucesso`);
        }
        break;

      case 'processing.failed':
        onProcessingFailed?.(payload);
        if (showToasts) {
          toast.error(`Falha ao processar "${payload.file_name}": ${payload.error}`);
        }
        break;

      case 'pong':
        // Resposta ao ping - não fazer nada
        break;

      default:
        console.log('Mensagem WebSocket não reconhecida:', type, payload);
    }
  }, [
    onFileUploaded,
    onFileUpdated,
    onFileDeleted,
    onFileMoved,
    onFolderCreated,
    onFolderUpdated,
    onFolderDeleted,
    onFileShared,
    onFileUnshared,
    onUploadProgress,
    onProcessingStarted,
    onProcessingCompleted,
    onProcessingFailed,
    showToasts
  ]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket não está conectado');
    }
  }, []);

  const subscribeToFolder = useCallback((folderId: number) => {
    sendMessage({
      type: 'subscribe_folder',
      folder_id: folderId
    });
  }, [sendMessage]);

  const unsubscribeFromFolder = useCallback((folderId: number) => {
    sendMessage({
      type: 'unsubscribe_folder',
      folder_id: folderId
    });
  }, [sendMessage]);

  const ping = useCallback(() => {
    sendMessage({ type: 'ping' });
  }, [sendMessage]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const getConnectionState = useCallback(() => {
    if (!wsRef.current) return 'DISCONNECTED';
    
    switch (wsRef.current.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'CONNECTED';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'DISCONNECTED';
      default:
        return 'UNKNOWN';
    }
  }, []);

  useEffect(() => {
    console.log('🚀 Inicializando useMediaWebSocket hook');
    
    // Conectar automaticamente apenas se autenticado
    if (isAuthenticated) {
      connect();
    } else {
      // Desconectar se não estiver autenticado
      disconnect();
    }
    
    // Configurar ping periódico apenas se autenticado
    let pingInterval: NodeJS.Timeout | null = null;
    if (isAuthenticated) {
      pingInterval = setInterval(() => {
        ping();
      }, 30000); // Ping a cada 30 segundos
    }
    
    return () => {
      console.log('🛑 Limpando useMediaWebSocket hook');
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingInterval) {
        clearInterval(pingInterval);
      }
      disconnect();
    };
  }, [isAuthenticated, connect, disconnect, ping]);

  return {
    connect,
    disconnect,
    sendMessage,
    subscribeToFolder,
    unsubscribeFromFolder,
    ping,
    getConnectionState,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN
  };
};

export default useMediaWebSocket;