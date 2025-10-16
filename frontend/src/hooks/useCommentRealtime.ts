import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { 
  Comment, 
  CommentWebSocketEvent, 
  CommentTargetType,
  UseCommentRealtimeProps,
  UseCommentRealtimeResult,
  CommentEventType,
  CommentRealtimeConfig
} from '@/types/comments';

// Hook para atualizações em tempo real de comentários
export function useCommentRealtime(
  targetType: CommentTargetType,
  targetId: string,
  config?: CommentRealtimeConfig
): UseCommentRealtimeResult {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = config?.maxReconnectAttempts || 5;
  const reconnectDelay = config?.reconnectDelay || 3000;

  const handleWebSocketMessage = useCallback((event: MessageEvent) => {
    try {
      const data: CommentWebSocketEvent = JSON.parse(event.data);
      
      // Verificar se o evento é relevante para o target atual
      if (data.target_type !== targetType || data.target_id !== targetId) {
        return;
      }

      const queryKey = ['comments', targetType, targetId];

      switch (data.event_type) {
        case CommentEventType.COMMENT_CREATED:
          // Invalidar queries para buscar novos comentários
          queryClient.invalidateQueries({ queryKey });
          
          // Mostrar notificação se não foi o usuário atual que criou
          if (data.comment && data.comment.autor.id !== user?.id) {
            if (config?.showNotifications !== false) {
              toast.info(
                `Novo comentário de ${data.comment.autor.nome}`,
                {
                  description: data.comment.conteudo_html.substring(0, 100) + '...',
                  action: {
                    label: 'Ver',
                    onClick: () => {
                      // Scroll para o comentário se possível
                      const element = document.getElementById(`comment-${data.comment?.id}`);
                      element?.scrollIntoView({ behavior: 'smooth' });
                    },
                  },
                }
              );
            }
          }
          break;

        case CommentEventType.COMMENT_UPDATED:
          if (data.comment) {
            // Atualizar cache do comentário específico
            queryClient.setQueryData(['comment', data.comment.id], data.comment);
            
            // Atualizar na lista de comentários
            queryClient.setQueryData(queryKey, (oldData: any) => {
              if (!oldData) return oldData;
              
              return {
                ...oldData,
                pages: oldData.pages.map((page: any) => ({
                  ...page,
                  results: page.results.map((comment: Comment) =>
                    comment.id === data.comment?.id ? data.comment : comment
                  ),
                })),
              };
            });

            // Notificação para resolução/reabertura
            if (data.comment.autor.id !== user?.id && config?.showNotifications !== false) {
              const action = data.comment.resolvido ? 'resolveu' : 'reabriu';
              toast.info(`${data.comment.autor.nome} ${action} um comentário`);
            }
          }
          break;

        case CommentEventType.COMMENT_DELETED:
          // Remover do cache
          if (data.comment_id) {
            queryClient.removeQueries({ queryKey: ['comment', data.comment_id] });
            
            // Remover da lista
            queryClient.setQueryData(queryKey, (oldData: any) => {
              if (!oldData) return oldData;
              
              return {
                ...oldData,
                pages: oldData.pages.map((page: any) => ({
                  ...page,
                  results: page.results.filter((comment: Comment) => 
                    comment.id !== data.comment_id
                  ),
                })),
              };
            });

            if (config?.showNotifications !== false) {
              toast.info('Um comentário foi removido');
            }
          }
          break;

        case CommentEventType.COMMENT_RESOLVED:
        case CommentEventType.COMMENT_REOPENED:
          // Invalidar queries para atualizar status
          queryClient.invalidateQueries({ queryKey });
          break;

        case CommentEventType.USER_TYPING:
          // Emitir evento personalizado para componentes que querem mostrar indicador de digitação
          if (data.user_id !== user?.id) {
            const typingEvent = new CustomEvent('comment-user-typing', {
              detail: {
                userId: data.user_id,
                userName: data.user_name,
                targetType,
                targetId,
              },
            });
            window.dispatchEvent(typingEvent);
          }
          break;

        case CommentEventType.USER_STOPPED_TYPING:
          // Emitir evento para parar indicador de digitação
          if (data.user_id !== user?.id) {
            const stoppedTypingEvent = new CustomEvent('comment-user-stopped-typing', {
              detail: {
                userId: data.user_id,
                targetType,
                targetId,
              },
            });
            window.dispatchEvent(stoppedTypingEvent);
          }
          break;
      }

      // Callback personalizado se fornecido
      if (config?.onMessage) {
        config.onMessage(data);
      }
    } catch (error) {
      console.error('Erro ao processar mensagem WebSocket:', error);
    }
  }, [targetType, targetId, user?.id, queryClient, config]);

  const connect = useCallback(() => {
    if (!user || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      // URL do WebSocket (ajustar conforme configuração do backend)
      const wsUrl = `${process.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/comments/${targetType}/${targetId}/`;
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket conectado para comentários');
        reconnectAttemptsRef.current = 0;
        
        if (config?.onConnect) {
          config.onConnect();
        }
      };

      wsRef.current.onmessage = handleWebSocketMessage;

      wsRef.current.onclose = (event) => {
        console.log('WebSocket desconectado:', event.code, event.reason);
        
        if (config?.onDisconnect) {
          config.onDisconnect();
        }

        // Tentar reconectar se não foi fechamento intencional
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Tentando reconectar... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
            connect();
          }, reconnectDelay);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('Erro no WebSocket:', error);
        
        if (config?.onError) {
          config.onError(error);
        }
      };
    } catch (error) {
      console.error('Erro ao conectar WebSocket:', error);
    }
  }, [user, targetType, targetId, handleWebSocketMessage, config, maxReconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Desconexão intencional');
      wsRef.current = null;
    }
  }, []);

  const sendTypingIndicator = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && user) {
      const message = {
        event_type: CommentEventType.USER_TYPING,
        user_id: user.id,
        user_name: user.nome,
        target_type: targetType,
        target_id: targetId,
      };
      wsRef.current.send(JSON.stringify(message));
    }
  }, [user, targetType, targetId]);

  const sendStoppedTypingIndicator = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && user) {
      const message = {
        event_type: CommentEventType.USER_STOPPED_TYPING,
        user_id: user.id,
        target_type: targetType,
        target_id: targetId,
      };
      wsRef.current.send(JSON.stringify(message));
    }
  }, [user, targetType, targetId]);

  // Conectar quando o hook é montado
  useEffect(() => {
    if (config?.autoConnect !== false) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, config?.autoConnect]);

  // Limpar timeout ao desmontar
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const isConnected = wsRef.current?.readyState === WebSocket.OPEN;
  const isConnecting = wsRef.current?.readyState === WebSocket.CONNECTING;

  return {
    isConnected,
    isConnecting,
    connect,
    disconnect,
    sendTypingIndicator,
    sendStoppedTypingIndicator,
  };
}

// Hook para indicadores de digitação
export function useTypingIndicators(targetType: CommentTargetType, targetId: string) {
  const [typingUsers, setTypingUsers] = useState<Array<{ userId: number; userName: string }>>([]);

  useEffect(() => {
    const handleUserTyping = (event: CustomEvent) => {
      const { userId, userName, targetType: eventTargetType, targetId: eventTargetId } = event.detail;
      
      if (eventTargetType === targetType && eventTargetId === targetId) {
        setTypingUsers(prev => {
          const existing = prev.find(u => u.userId === userId);
          if (!existing) {
            return [...prev, { userId, userName }];
          }
          return prev;
        });

        // Remover automaticamente após 3 segundos
        setTimeout(() => {
          setTypingUsers(prev => prev.filter(u => u.userId !== userId));
        }, 3000);
      }
    };

    const handleUserStoppedTyping = (event: CustomEvent) => {
      const { userId, targetType: eventTargetType, targetId: eventTargetId } = event.detail;
      
      if (eventTargetType === targetType && eventTargetId === targetId) {
        setTypingUsers(prev => prev.filter(u => u.userId !== userId));
      }
    };

    window.addEventListener('comment-user-typing', handleUserTyping as EventListener);
    window.addEventListener('comment-user-stopped-typing', handleUserStoppedTyping as EventListener);

    return () => {
      window.removeEventListener('comment-user-typing', handleUserTyping as EventListener);
      window.removeEventListener('comment-user-stopped-typing', handleUserStoppedTyping as EventListener);
    };
  }, [targetType, targetId]);

  return typingUsers;
}