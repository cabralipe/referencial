import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/context/AuthContext';
import { useMebMessages, useMebThreadMe, useMebThreads, useSendMebMessage, useUploadMebAvatar } from '@/hooks/useMebChat';
import type { MebThread } from '@/api/types';

import './MebAssistant.css';

const QUICK_QUESTIONS = [
  'Como envio minhas tarefas?',
  'Esqueci minha senha de login',
  'Onde vejo os prazos?',
];

const ADMIN_ROLES = new Set(['admin_cliente', 'super_admin']);

function formatHour(isoDate: string) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  return date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function threadLabel(thread: MebThread) {
  return thread.usuario_nome || thread.usuario_email || `Usuário #${thread.usuario}`;
}

export function MebAssistant() {
  const { user, cliente, refreshCliente } = useAuth();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [selectedUsuario, setSelectedUsuario] = useState<number | null>(null);

  const messagesContainerRef = useRef<HTMLDivElement | null>(null);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const isPrivileged = !!user && ADMIN_ROLES.has(user.role);
  const isAuthenticated = !!user;
  const mascotImage = cliente?.tema?.meb_avatar_url || cliente?.tema?.logo_url || null;

  useEffect(() => {
    if (!user) {
      setOpen(false);
      setSelectedUsuario(null);
      setMessage('');
    }
  }, [user]);

  const threadMeQuery = useMebThreadMe({
    enabled: isAuthenticated && open && !isPrivileged,
  });
  const threadsQuery = useMebThreads({
    enabled: isAuthenticated && open && isPrivileged,
  });

  useEffect(() => {
    if (!isPrivileged) {
      setSelectedUsuario(null);
      return;
    }
    if (threadsQuery.data && threadsQuery.data.length > 0) {
      const alreadySelected = threadsQuery.data.some((thread) => thread.usuario === selectedUsuario);
      if (!alreadySelected) {
        setSelectedUsuario(threadsQuery.data[0].usuario);
      }
    } else {
      setSelectedUsuario(null);
    }
  }, [isPrivileged, threadsQuery.data, selectedUsuario]);

  const messagesQuery = useMebMessages({
    usuarioId: isPrivileged ? selectedUsuario ?? undefined : undefined,
    enabled: isAuthenticated && open && (!isPrivileged || Boolean(selectedUsuario)),
  });

  const sendMessage = useSendMebMessage();
  const uploadAvatar = useUploadMebAvatar();

  useEffect(() => {
    if (!open) return;
    if (!messagesContainerRef.current) return;
    messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
  }, [messagesQuery.data, open]);

  if (!user) {
    return null;
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    if (isPrivileged && !selectedUsuario) return;
    sendMessage.mutate(
      {
        conteudo: trimmed,
        usuarioId: isPrivileged ? selectedUsuario : undefined,
      },
      {
        onSuccess: () => setMessage(''),
      },
    );
  };

  const disabledComposer = sendMessage.isPending || (isPrivileged && !selectedUsuario);
  const currentThreads = threadsQuery.data ?? [];
  const currentMessages = messagesQuery.data ?? [];

  const statusLabel = messagesQuery.isFetching ? 'Atualizando…' : 'Online';

  const headerSubtitle = isPrivileged
    ? 'Acompanhe as conversas dos clientes'
    : 'Envie dúvidas rápidas e receba ajuda do MEB';

  const showSuggestionButtons = !isPrivileged;

  const showEmptyState = !messagesQuery.isPending && currentMessages.length === 0;

  const handleSelectChange = (value: string) => {
    if (!value) {
      setSelectedUsuario(null);
      return;
    }
    setSelectedUsuario(Number(value));
  };

  const resolvedThread = isPrivileged ? currentThreads.find((thread) => thread.usuario === selectedUsuario) : threadMeQuery.data;

  const resolvedClientName = resolvedThread ? threadLabel(resolvedThread) : null;

  const resolvedPlaceholder = isPrivileged
    ? resolvedClientName
      ? `Responder ${resolvedClientName}…`
      : 'Selecione um cliente para responder'
    : 'Digite sua mensagem';

  const handleQuickQuestion = (text: string) => {
    setMessage(text);
  };

  const authorLabel = (origem: string, nome: string | null) => {
    if (nome) return nome;
    switch (origem) {
      case 'meb':
        return 'MEB';
      case 'admin':
        return 'Administrador';
      case 'cliente':
        return resolvedClientName ?? 'Cliente';
      default:
        return 'Sistema';
    }
  };

  const handleAvatarClick = () => {
    avatarInputRef.current?.click();
  };

  const handleAvatarChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    uploadAvatar.mutate(file, {
      onSuccess: async () => {
        await refreshCliente();
        event.target.value = '';
      },
    });
  };

  return (
    <>
      <button
        type="button"
        className={`meb-toggle ${open ? 'meb-toggle--open' : ''}`}
        onClick={() => setOpen((prev) => !prev)}
        aria-pressed={open}
        aria-label={open ? 'Fechar chat do MEB' : 'Abrir chat do MEB'}
      >
        <span>MEB</span>
      </button>
      {open && (
        <section className="meb-panel" aria-live="polite">
          <header className="meb-panel__header">
            <div className="meb-panel__header-content">
              <div className="meb-panel__avatar" aria-label="Avatar do MEB">
                {mascotImage ? (
                  <img src={mascotImage} alt="Avatar do mascote MEB" />
                ) : (
                  <span className="meb-panel__avatar-placeholder">MEB</span>
                )}
              </div>
              <div>
                <strong>MEB</strong>
                <p>{headerSubtitle}</p>
              </div>
            </div>
            <div className="meb-panel__status">
              <span className="meb-panel__dot" aria-hidden="true" />
              {statusLabel}
            </div>
            <button type="button" className="meb-panel__close" onClick={() => setOpen(false)} aria-label="Fechar chat">
              ×
            </button>
          </header>

          {isPrivileged && (
            <div className="meb-panel__upload">
              <p>Atualize a imagem do mascote para personalizar o chat.</p>
              <div className="meb-panel__upload-actions">
                <input
                  ref={avatarInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarChange}
                  hidden
                />
                <button type="button" onClick={handleAvatarClick} disabled={uploadAvatar.isPending}>
                  {uploadAvatar.isPending ? 'Enviando...' : 'Enviar nova imagem'}
                </button>
                {uploadAvatar.isError && <span className="meb-panel__error">Falha ao enviar. Tente novamente.</span>}
                {uploadAvatar.isSuccess && <span className="meb-panel__success">Avatar atualizado!</span>}
              </div>
            </div>
          )}

          {isPrivileged && (
            <div className="meb-panel__thread-picker">
              <label htmlFor="meb-thread-select">Cliente</label>
              <select
                id="meb-thread-select"
                value={selectedUsuario ?? ''}
                onChange={(event) => handleSelectChange(event.target.value)}
              >
                {currentThreads.length === 0 && <option value="">Sem conversas ainda</option>}
                {currentThreads.length > 0 && <option value="">Selecione um cliente</option>}
                {currentThreads.map((thread) => (
                  <option key={thread.id} value={thread.usuario}>
                    {threadLabel(thread)}
                    {thread.last_message_preview ? ` • ${thread.last_message_preview.slice(0, 30)}` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {showSuggestionButtons && (
            <div className="meb-panel__suggestions">
              {QUICK_QUESTIONS.map((item) => (
                <button type="button" key={item} onClick={() => handleQuickQuestion(item)}>
                  {item}
                </button>
              ))}
            </div>
          )}

          <div className="meb-panel__messages" ref={messagesContainerRef}>
            {messagesQuery.isPending ? (
              <p className="meb-panel__helper">Carregando conversa…</p>
            ) : showEmptyState ? (
              <p className="meb-panel__helper">
                {isPrivileged ? 'Escolha um cliente para visualizar a conversa.' : 'Envie uma mensagem para começar.'}
              </p>
            ) : (
              currentMessages.map((msg) => {
                const classes = ['meb-message'];
                if (msg.is_mine) {
                  classes.push('meb-message--me');
                } else {
                  classes.push(`meb-message--${msg.origem}`);
                }
                return (
                  <article key={msg.id} className={classes.join(' ')}>
                    <div className="meb-message__meta">
                      <span>{authorLabel(msg.origem, msg.autor_nome)}</span>
                      <time dateTime={msg.created_at}>{formatHour(msg.created_at)}</time>
                    </div>
                    <p>{msg.conteudo}</p>
                  </article>
                );
              })
            )}
          </div>

          <form className="meb-panel__composer" onSubmit={handleSubmit}>
            <textarea
              rows={2}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={resolvedPlaceholder}
              disabled={disabledComposer}
            />
            <div className="meb-panel__composer-actions">
              {sendMessage.isError && <span className="meb-panel__error">Não foi possível enviar. Tente novamente.</span>}
              <button type="submit" disabled={disabledComposer || !message.trim()}>
                Enviar
              </button>
            </div>
          </form>
        </section>
      )}
    </>
  );
}
