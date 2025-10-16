import React, { useEffect, useState } from 'react';
import { useMediaWebSocket } from '../hooks/useMediaWebSocket';

export function WebSocketTestPage() {
  const [messages, setMessages] = useState<string[]>([]);
  
  const addMessage = (message: string) => {
    setMessages(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  // Usar o hook do WebSocket
  const { isConnected, connect, disconnect } = useMediaWebSocket({
    onFileUploaded: (payload) => addMessage(`Arquivo enviado: ${JSON.stringify(payload)}`),
    onFileUpdated: (payload) => addMessage(`Arquivo atualizado: ${JSON.stringify(payload)}`),
    onFileDeleted: (payload) => addMessage(`Arquivo deletado: ${JSON.stringify(payload)}`),
    onFolderCreated: (payload) => addMessage(`Pasta criada: ${JSON.stringify(payload)}`),
    showToasts: false
  });

  useEffect(() => {
    addMessage('Componente WebSocketTestPage montado');
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Teste de WebSocket</h1>
      <div style={{ marginBottom: '20px' }}>
        <strong>Status: </strong>
        <span style={{ color: isConnected ? 'green' : 'red' }}>
          {isConnected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>
      
      <div style={{ marginBottom: '20px' }}>
        <button onClick={connect} disabled={isConnected}>
          Conectar
        </button>
        <button onClick={disconnect} disabled={!isConnected} style={{ marginLeft: '10px' }}>
          Desconectar
        </button>
      </div>

      <div>
        <h3>Mensagens:</h3>
        <div style={{ 
          border: '1px solid #ccc', 
          padding: '10px', 
          height: '300px', 
          overflowY: 'scroll',
          backgroundColor: '#f5f5f5'
        }}>
          {messages.map((message, index) => (
            <div key={index}>{message}</div>
          ))}
        </div>
      </div>
    </div>
  );
}