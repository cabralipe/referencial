# Guia de Implementação - Frontend Referencial Curricular

## 1. Estrutura de Arquivos Sugerida

```
frontend/src/
├── api/
│   ├── client.ts (existente)
│   ├── types.ts (expandir)
│   └── hooks/
│       ├── useTextoUnico.ts
│       ├── useQuadros.ts
│       ├── useRevisoes.ts
│       ├── useComentarios.ts
│       ├── useNotificacoes.ts
│       ├── useMidias.ts
│       ├── useBlocos.ts
│       └── useExports.ts
├── components/
│   ├── common/ (existente)
│   ├── layout/ (existente)
│   ├── forms/
│   │   ├── RichTextEditor.tsx
│   │   ├── FileUpload.tsx
│   │   └── FormField.tsx
│   ├── editors/
│   │   ├── TextoUnicoEditor.tsx
│   │   ├── QuadroEditor.tsx
│   │   └── ComentarioEditor.tsx
│   ├── modals/
│   │   ├── RevisaoModal.tsx
│   │   ├── ExportModal.tsx
│   │   └── SeletorBlocosModal.tsx
│   ├── notifications/
│   │   ├── NotificationBell.tsx
│   │   └── NotificationList.tsx
│   └── biblioteca/
│       ├── MidiaGrid.tsx
│       ├── MidiaUpload.tsx
│       └── BlocosList.tsx
├── pages/
│   ├── DashboardPage.tsx (existente)
│   ├── TaskDetailPage.tsx (existente)
│   ├── TextoUnicoPage.tsx
│   ├── QuadroPage.tsx
│   ├── BibliotecaPage.tsx
│   ├── RevisoesPage.tsx
│   └── AuditoriaPage.tsx
└── utils/
    ├── editor.ts
    ├── export.ts
    └── notifications.ts
```

## 2. Tipos TypeScript Expandidos

### 2.1 Entidades Principais

```typescript
// Expandir api/types.ts

export interface GT {
  id: number;
  nome: string;
  etapa: string;
  membros: number[];
  cliente: number;
  created_at: string;
  updated_at: string;
}

export interface Quadro {
  id: number;
  gt: number;
  template: string;
  version: number;
  celulas: CelulaQuadro[];
  created_at: string;
  updated_at: string;
}

export interface CelulaQuadro {
  id: number;
  quadro: number;
  linha: number;
  coluna: number;
  valor_html: string;
}

export interface Midia {
  id: number;
  url: string;
  legenda: string;
  tags: string[];
  uploaded_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface BlocoTexto {
  id: number;
  titulo: string;
  conteudo_html: string;
  tags: string[];
  created_by: number | null;
  created_at: string;
  updated_at: string;
  etag: string;
}

export interface ExportJob {
  id: number;
  alvo_tipo: 'texto_unico' | 'quadro';
  alvo_id: string;
  formato: 'pdf' | 'docx';
  status: 'queued' | 'running' | 'done' | 'error';
  url_resultado: string;
  finished_at: string | null;
  created_at: string;
}

export interface FormularioDinamico {
  id: number;
  nome: string;
  descricao: string;
  ativo: boolean;
  campos: CampoDinamico[];
}

export interface CampoDinamico {
  id: number;
  chave: string;
  tipo: 'texto' | 'select' | 'upload' | 'inteiro' | 'decimal' | 'bool';
  config_json: Record<string, any>;
  obrigatorio: boolean;
  ordem: number;
}
```

### 2.2 Tipos de Payload

```typescript
export interface CreateTextoUnicoPayload {
  gt: number;
  tarefa: number;
  conteudo_html: string;
}

export interface CreateQuadroPayload {
  gt: number;
  template: string;
}

export interface UpdateCelulaPayload {
  linha: number;
  coluna: number;
  valor_html: string;
}

export interface CreateRevisaoPayload {
  alvo_tipo: string;
  alvo_id: string;
  parecer_html?: string;
}

export interface CreateComentarioPayload {
  alvo_tipo: string;
  alvo_id: string;
  anchor_json: Record<string, any>;
  conteudo_html: string;
  mentions_ids?: number[];
}
```

## 3. Hooks de API Detalhados

### 3.1 useTextoUnico.ts

```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useApiClient } from '@/api/client';
import type { TextoUnico, CreateTextoUnicoPayload } from '@/api/types';

export function useTextoUnico(gtId?: number, tarefaId?: number) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(gtId && tarefaId),
    queryKey: ['texto_unico', gtId, tarefaId],
    queryFn: async () => {
      const response = await client.get<TextoUnico[]>('/texto_unico', {
        query: { gt: gtId, tarefa: tarefaId },
      });
      return response.data[0] || null;
    },
  });
}

export function useCreateTextoUnico() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateTextoUnicoPayload) => {
      const response = await client.post<TextoUnico>('/texto_unico', {
        body: payload,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['texto_unico', data.gt, data.tarefa] 
      });
    },
  });
}

export function useUpdateTextoUnico() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ 
      id, 
      payload, 
      etag 
    }: { 
      id: number; 
      payload: Partial<CreateTextoUnicoPayload>; 
      etag?: string;
    }) => {
      const response = await client.put<TextoUnico>(`/texto_unico/${id}`, {
        body: payload,
        ifMatch: etag,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['texto_unico', data.gt, data.tarefa] 
      });
    },
  });
}
```

### 3.2 useQuadros.ts

```typescript
export function useQuadro(gtId?: number, template?: string) {
  const client = useApiClient();

  return useQuery({
    enabled: Boolean(gtId && template),
    queryKey: ['quadro', gtId, template],
    queryFn: async () => {
      const response = await client.get<Quadro[]>('/quadro', {
        query: { gt: gtId, template },
      });
      return response.data[0] || null;
    },
  });
}

export function useGerarQuadro() {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ gtId }: { gtId: number }) => {
      const response = await client.post<Quadro>('/quadro/gerar', {
        query: { gt_id: gtId },
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ 
        queryKey: ['quadro', data.gt] 
      });
    },
  });
}

export function useUpdateCelula(quadroId: number) {
  const client = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: UpdateCelulaPayload) => {
      const response = await client.put<CelulaQuadro>(
        `/quadro/${quadroId}/celulas`, 
        { body: payload }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ 
        queryKey: ['quadro', quadroId] 
      });
    },
  });
}
```

## 4. Componentes Principais

### 4.1 RichTextEditor.tsx

```typescript
import { useCallback, useEffect, useRef } from 'react';
import { Editor } from '@tinymce/tinymce-react';

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: number;
  readonly?: boolean;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder,
  height = 400,
  readonly = false,
}: RichTextEditorProps) {
  const editorRef = useRef<any>(null);

  const handleEditorChange = useCallback((content: string) => {
    onChange(content);
  }, [onChange]);

  return (
    <Editor
      apiKey="your-tinymce-api-key"
      onInit={(evt, editor) => editorRef.current = editor}
      value={value}
      onEditorChange={handleEditorChange}
      init={{
        height,
        menubar: false,
        plugins: [
          'advlist', 'autolink', 'lists', 'link', 'image', 'charmap',
          'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
          'insertdatetime', 'media', 'table', 'preview', 'help', 'wordcount'
        ],
        toolbar: readonly ? false : 
          'undo redo | blocks | ' +
          'bold italic forecolor | alignleft aligncenter ' +
          'alignright alignjustify | bullist numlist outdent indent | ' +
          'removeformat | help',
        readonly,
        placeholder,
      }}
    />
  );
}
```

### 4.2 QuadroEditor.tsx

```typescript
import { useState, useCallback } from 'react';
import { useQuadro, useUpdateCelula } from '@/hooks/useQuadros';
import { RichTextEditor } from '@/components/forms/RichTextEditor';

interface QuadroEditorProps {
  gtId: number;
  template: string;
}

export function QuadroEditor({ gtId, template }: QuadroEditorProps) {
  const { data: quadro, isLoading } = useQuadro(gtId, template);
  const updateCelula = useUpdateCelula(quadro?.id || 0);
  const [editingCell, setEditingCell] = useState<{linha: number, coluna: number} | null>(null);

  const handleCellClick = useCallback((linha: number, coluna: number) => {
    setEditingCell({ linha, coluna });
  }, []);

  const handleCellSave = useCallback((valor_html: string) => {
    if (editingCell) {
      updateCelula.mutate({
        linha: editingCell.linha,
        coluna: editingCell.coluna,
        valor_html,
      });
      setEditingCell(null);
    }
  }, [editingCell, updateCelula]);

  if (isLoading) return <div>Carregando quadro...</div>;
  if (!quadro) return <div>Quadro não encontrado</div>;

  return (
    <div className="quadro-editor">
      <div className="quadro-grid">
        {/* Renderizar grid baseado nas células */}
        {quadro.celulas.map((celula) => (
          <div
            key={`${celula.linha}-${celula.coluna}`}
            className="quadro-cell"
            onClick={() => handleCellClick(celula.linha, celula.coluna)}
            dangerouslySetInnerHTML={{ __html: celula.valor_html }}
          />
        ))}
      </div>

      {editingCell && (
        <div className="cell-editor-modal">
          <RichTextEditor
            value={getCellValue(quadro.celulas, editingCell.linha, editingCell.coluna)}
            onChange={handleCellSave}
          />
        </div>
      )}
    </div>
  );
}
```

### 4.3 NotificationBell.tsx

```typescript
import { useState } from 'react';
import { useNotificacoes, useMarkAsRead } from '@/hooks/useNotificacoes';

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const { data: notificacoes = [] } = useNotificacoes();
  const markAsRead = useMarkAsRead();

  const unreadCount = notificacoes.filter(n => !n.lida).length;

  const handleMarkAsRead = (id: number) => {
    markAsRead.mutate(id);
  };

  return (
    <div className="notification-bell">
      <button 
        className="bell-button"
        onClick={() => setIsOpen(!isOpen)}
      >
        🔔
        {unreadCount > 0 && (
          <span className="badge">{unreadCount}</span>
        )}
      </button>

      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <h3>Notificações</h3>
          </div>
          <div className="notification-list">
            {notificacoes.map((notificacao) => (
              <div
                key={notificacao.id}
                className={`notification-item ${!notificacao.lida ? 'unread' : ''}`}
                onClick={() => handleMarkAsRead(notificacao.id)}
              >
                <div className="notification-content">
                  {renderNotificationContent(notificacao)}
                </div>
                <div className="notification-time">
                  {formatTime(notificacao.created_at)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

## 5. Páginas Principais

### 5.1 TextoUnicoPage.tsx

```typescript
import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTextoUnico, useCreateTextoUnico, useUpdateTextoUnico } from '@/hooks/useTextoUnico';
import { RichTextEditor } from '@/components/forms/RichTextEditor';

export function TextoUnicoPage() {
  const { tarefaId } = useParams<{ tarefaId: string }>();
  const [searchParams] = useSearchParams();
  const gtId = searchParams.get('gt');
  
  const { data: textoUnico, isLoading } = useTextoUnico(
    gtId ? parseInt(gtId) : undefined,
    tarefaId ? parseInt(tarefaId) : undefined
  );
  
  const createTextoUnico = useCreateTextoUnico();
  const updateTextoUnico = useUpdateTextoUnico();
  
  const [content, setContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (!gtId || !tarefaId) return;
    
    setIsSaving(true);
    try {
      if (textoUnico) {
        await updateTextoUnico.mutateAsync({
          id: textoUnico.id,
          payload: { conteudo_html: content },
          etag: textoUnico.etag,
        });
      } else {
        await createTextoUnico.mutateAsync({
          gt: parseInt(gtId),
          tarefa: parseInt(tarefaId),
          conteudo_html: content,
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="texto-unico-page">
      <div className="page-header">
        <h1>Texto Único</h1>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="save-button"
        >
          {isSaving ? 'Salvando...' : 'Salvar'}
        </button>
      </div>

      <div className="editor-container">
        <RichTextEditor
          value={content}
          onChange={setContent}
          placeholder="Digite o texto único para este GT e tarefa..."
        />
      </div>
    </div>
  );
}
```

## 6. Considerações de Performance

### 6.1 Lazy Loading
```typescript
// router.tsx
const TextoUnicoPage = lazy(() => import('./pages/TextoUnicoPage'));
const QuadroPage = lazy(() => import('./pages/QuadroPage'));
const BibliotecaPage = lazy(() => import('./pages/BibliotecaPage'));
```

### 6.2 Debounce para Auto-save
```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSave = useDebouncedCallback(
  (content: string) => {
    // Salvar automaticamente
    handleSave(content);
  },
  2000 // 2 segundos
);
```

### 6.3 Otimistic Updates
```typescript
const updateTextoUnico = useMutation({
  mutationFn: updateTextoUnicoFn,
  onMutate: async (newData) => {
    // Cancelar queries em andamento
    await queryClient.cancelQueries({ queryKey: ['texto_unico'] });
    
    // Snapshot do valor anterior
    const previousData = queryClient.getQueryData(['texto_unico']);
    
    // Atualizar otimisticamente
    queryClient.setQueryData(['texto_unico'], newData);
    
    return { previousData };
  },
  onError: (err, newData, context) => {
    // Reverter em caso de erro
    queryClient.setQueryData(['texto_unico'], context?.previousData);
  },
});
```

## 7. Próximos Passos

1. **Implementar tipos TypeScript expandidos**
2. **Criar hooks básicos para cada API**
3. **Desenvolver componentes reutilizáveis**
4. **Implementar páginas por ordem de prioridade**
5. **Adicionar testes unitários**
6. **Otimizar performance**
7. **Implementar funcionalidades avançadas**

Este guia fornece uma base sólida para implementar todas as funcionalidades faltantes no frontend, mantendo consistência com a arquitetura atual e seguindo as melhores práticas do React.