import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { RichTextEditor } from '@/components/common/RichTextEditor';
import type { MuralPost } from '@/api/types';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useBlocos, useMidias } from '@/hooks/useBiblioteca';
import { useCreateMuralPost, useDeleteMuralPost, useMural, useUpdateMuralPost, useReorderMuralPosts } from '@/hooks/useMural';

import './AdminMuralPage.css';

type MuralEditorPageProps = {
  title?: string;
  description?: string;
};

type ReferenciaItem =
  | {
    kind: 'bloco';
    id: string;
    titulo: string;
    conteudo_html: string;
    updated_at: string;
  }
  | {
    kind: 'midia';
    id: string;
    titulo: string;
    descricao?: string | null;
    link_url: string;
    updated_at: string;
  };

type MuralModalidade = 'aviso' | 'recebimento_arquivo';

const DRAG_SCROLL_EDGE_PX = 120;
const DRAG_SCROLL_STEP_PX = 18;

function getPostPosition(post: MuralPost) {
  return post.position ?? post.ordem ?? 0;
}

function sortMuralPosts(posts: MuralPost[]) {
  return posts.slice().sort((a, b) => {
    const fixA = a.fixado ? 1 : 0;
    const fixB = b.fixado ? 1 : 0;
    if (fixA !== fixB) return fixB - fixA;
    const positionA = getPostPosition(a);
    const positionB = getPostPosition(b);
    if (positionA !== positionB) return positionA - positionB;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export function AdminMuralPage({
  title = 'Admin · Mural',
  description = 'Publique avisos para os membros do GT e acompanhe os comunicados.',
}: MuralEditorPageProps) {
  const { data: posts, isLoading } = useMural();
  const { data: midias, isLoading: midiasLoading } = useMidias();
  const { data: blocos, isLoading: blocosLoading } = useBlocos();
  const { gtOptions } = useAvailableGts({ scope: 'all' });
  const createPost = useCreateMuralPost();
  const updatePost = useUpdateMuralPost();
  const deletePost = useDeleteMuralPost();
  const reorderPosts = useReorderMuralPosts();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [titulo, setTitulo] = useState('');
  const [conteudo, setConteudo] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [modalidade, setModalidade] = useState<MuralModalidade>('aviso');
  const [fixado, setFixado] = useState(false);
  const [gtIds, setGtIds] = useState<number[]>([]);
  const [includeAll, setIncludeAll] = useState(true);
  const [feedback, setFeedback] = useState('');
  const [novosAnexos, setNovosAnexos] = useState<File[]>([]);
  const [anexosExistentes, setAnexosExistentes] = useState<Array<{ titulo?: string; url?: string }>>([]);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [orderedPosts, setOrderedPosts] = useState<MuralPost[]>([]);
  const [draggedPostId, setDraggedPostId] = useState<string | null>(null);
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const [selectedGtFilter, setSelectedGtFilter] = useState<'all' | string>('all');
  const dragClientYRef = useRef<number | null>(null);
  const dragScrollFrameRef = useRef<number | null>(null);

  useEffect(() => {
    setOrderedPosts(sortMuralPosts(posts ?? []));
  }, [posts]);

  useEffect(() => {
    if (!draggedPostId) {
      dragClientYRef.current = null;
      if (dragScrollFrameRef.current !== null) {
        window.cancelAnimationFrame(dragScrollFrameRef.current);
        dragScrollFrameRef.current = null;
      }
      return;
    }

    const updatePointerPosition = (event: globalThis.DragEvent) => {
      dragClientYRef.current = event.clientY;
    };

    const tick = () => {
      const clientY = dragClientYRef.current;
      if (clientY !== null) {
        const viewportHeight = window.innerHeight;
        if (clientY < DRAG_SCROLL_EDGE_PX) {
          const intensity = (DRAG_SCROLL_EDGE_PX - clientY) / DRAG_SCROLL_EDGE_PX;
          window.scrollBy({ top: -Math.max(8, Math.round(DRAG_SCROLL_STEP_PX * intensity)) });
        } else if (viewportHeight - clientY < DRAG_SCROLL_EDGE_PX) {
          const intensity = (DRAG_SCROLL_EDGE_PX - (viewportHeight - clientY)) / DRAG_SCROLL_EDGE_PX;
          window.scrollBy({ top: Math.max(8, Math.round(DRAG_SCROLL_STEP_PX * intensity)) });
        }
      }
      dragScrollFrameRef.current = window.requestAnimationFrame(tick);
    };

    document.addEventListener('dragover', updatePointerPosition);
    dragScrollFrameRef.current = window.requestAnimationFrame(tick);

    return () => {
      document.removeEventListener('dragover', updatePointerPosition);
      if (dragScrollFrameRef.current !== null) {
        window.cancelAnimationFrame(dragScrollFrameRef.current);
        dragScrollFrameRef.current = null;
      }
    };
  }, [draggedPostId]);

  const referencias = useMemo<ReferenciaItem[]>(() => {
    const blocosItems: ReferenciaItem[] = (blocos ?? []).map((bloco) => ({
      kind: 'bloco',
      id: `bloco-${bloco.id}`,
      titulo: bloco.titulo,
      conteudo_html: bloco.conteudo_html,
      updated_at: bloco.updated_at,
    }));
    const midiaItems: ReferenciaItem[] = (midias ?? []).map((midia) => ({
      kind: 'midia',
      id: `midia-${midia.id}`,
      titulo: midia.titulo || 'Link da biblioteca',
      descricao: midia.descricao,
      link_url: midia.url,
      updated_at: midia.created_at,
    }));
    return [...blocosItems, ...midiaItems].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
  }, [blocos, midias]);

  const isFilteringByGt = selectedGtFilter !== 'all';

  const visiblePosts = useMemo(() => {
    if (!isFilteringByGt) {
      return orderedPosts;
    }

    const selectedGtId = Number(selectedGtFilter);
    return orderedPosts.filter((post) => {
      const postGtIds = post.gt_ids ?? [];
      return postGtIds.length === 0 || postGtIds.includes(selectedGtId);
    });
  }, [isFilteringByGt, orderedPosts, selectedGtFilter]);

  const resetForm = () => {
    setEditingId(null);
    setTitulo('');
    setConteudo('');
    setLinkUrl('');
    setModalidade('aviso');
    setFixado(false);
    setGtIds([]);
    setIncludeAll(true);
    setNovosAnexos([]);
    setAnexosExistentes([]);
    setFileInputKey((prev) => prev + 1);
  };

  const handleFilesChange = (event: ChangeEvent<HTMLInputElement>) => {
    setNovosAnexos(Array.from(event.target.files ?? []));
  };

  const buildPayload = () => {
    const formData = new FormData();
    formData.append('titulo', titulo);
    formData.append('conteudo_html', conteudo);
    if (linkUrl.trim()) {
      formData.append('link_url', linkUrl.trim());
    }
    formData.append('modalidade', modalidade);
    formData.append('fixado', String(fixado));
    formData.append('include_all', String(includeAll));
    gtIds.forEach((gtId) => {
      formData.append('gt_ids', String(gtId));
    });
    formData.append('existing_anexos', JSON.stringify(anexosExistentes));
    novosAnexos.forEach((arquivo) => {
      formData.append('anexos_uploads', arquivo);
    });
    return formData;
  };

  const persistOrder = async (nextPosts: MuralPost[], previousPosts: MuralPost[]) => {
    setOrderedPosts(nextPosts);
    setFeedback('');
    try {
      await reorderPosts.mutateAsync(nextPosts.map((post, index) => ({ id: post.id, position: index })));
    } catch (error) {
      setOrderedPosts(previousPosts);
      setFeedback(error instanceof Error ? error.message : 'Nao foi possivel salvar a nova ordem do mural.');
    }
  };

  const matchesSelectedGtFilter = (post: MuralPost) => {
    if (!isFilteringByGt) {
      return true;
    }

    const selectedGtId = Number(selectedGtFilter);
    const postGtIds = post.gt_ids ?? [];
    return postGtIds.length === 0 || postGtIds.includes(selectedGtId);
  };

  const handleDragStart = (event: DragEvent<HTMLElement>, post: MuralPost) => {
    if (reorderPosts.isPending) {
      event.preventDefault();
      return;
    }
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', post.id);
    dragClientYRef.current = event.clientY;
    setDraggedPostId(post.id);
    setDropTargetId(post.id);
  };

  const handleDragOver = (event: DragEvent<HTMLElement>, post: MuralPost) => {
    if (!draggedPostId || draggedPostId === post.id) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setDropTargetId(post.id);
  };

  const handleDrop = async (event: DragEvent<HTMLElement>, targetPost: MuralPost) => {
    event.preventDefault();
    if (!draggedPostId || draggedPostId === targetPost.id) {
      setDraggedPostId(null);
      setDropTargetId(null);
      return;
    }

    const previousPosts = [...orderedPosts];
    const sourceIndex = previousPosts.findIndex((post) => post.id === draggedPostId);
    const targetIndex = previousPosts.findIndex((post) => post.id === targetPost.id);
    if (sourceIndex < 0 || targetIndex < 0) {
      setDraggedPostId(null);
      setDropTargetId(null);
      return;
    }

    const sourcePost = previousPosts[sourceIndex];
    if (Boolean(sourcePost.fixado) !== Boolean(targetPost.fixado)) {
      setFeedback('Avisos fixados so podem ser reordenados entre fixados. Os demais ficam abaixo.');
      setDraggedPostId(null);
      setDropTargetId(null);
      return;
    }

    let nextPosts: MuralPost[];

    if (isFilteringByGt) {
      const visiblePreviousPosts = previousPosts.filter(matchesSelectedGtFilter);
      const sourceVisibleIndex = visiblePreviousPosts.findIndex((post) => post.id === draggedPostId);
      const targetVisibleIndex = visiblePreviousPosts.findIndex((post) => post.id === targetPost.id);

      if (sourceVisibleIndex < 0 || targetVisibleIndex < 0) {
        setDraggedPostId(null);
        setDropTargetId(null);
        return;
      }

      const visibleNextPosts = [...visiblePreviousPosts];
      const [movedVisiblePost] = visibleNextPosts.splice(sourceVisibleIndex, 1);
      visibleNextPosts.splice(targetVisibleIndex, 0, movedVisiblePost);

      let visibleCursor = 0;
      nextPosts = previousPosts.map((post) => {
        if (!matchesSelectedGtFilter(post)) {
          return post;
        }
        const replacement = visibleNextPosts[visibleCursor];
        visibleCursor += 1;
        return replacement;
      });
    } else {
      nextPosts = [...previousPosts];
      const [movedPost] = nextPosts.splice(sourceIndex, 1);
      nextPosts.splice(targetIndex, 0, movedPost);
    }

    setDraggedPostId(null);
    setDropTargetId(null);
    await persistOrder(nextPosts, previousPosts);
  };

  const handleDragEnd = () => {
    dragClientYRef.current = null;
    setDraggedPostId(null);
    setDropTargetId(null);
  };

  const handleEdit = (post: MuralPost) => {
    setEditingId(post.id);
    setTitulo(post.titulo);
    setConteudo(post.conteudo_html);
    setLinkUrl(post.link_url ?? '');
    setModalidade((post.modalidade as MuralModalidade) || 'aviso');
    setFixado(Boolean(post.fixado));
    setGtIds(post.gt_ids ?? []);
    setIncludeAll(!(post.gt_ids && post.gt_ids.length > 0));
    setAnexosExistentes(post.anexos ?? []);
    setNovosAnexos([]);
    setFileInputKey((prev) => prev + 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    if (!conteudo.trim()) {
      setFeedback('Informe o conteudo do aviso.');
      return;
    }
    try {
      const payload = buildPayload();
      if (editingId) {
        await updatePost.mutateAsync({ id: editingId, payload });
      } else {
        await createPost.mutateAsync(payload);
      }
      resetForm();
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Nao foi possivel salvar o aviso.');
    }
  };

  if (isLoading || midiasLoading || blocosLoading) {
    return <FullPageLoader message="Carregando mural..." />;
  }

  return (
    <div className="admin-mural">
      <PageHeader title={title} description={description} />

      <Card>
        <form className="admin-mural__form" onSubmit={handleSubmit}>
          <h2>{editingId ? 'Editar aviso' : 'Novo aviso'}</h2>
          <label>
            <span>Titulo</span>
            <input value={titulo} onChange={(event) => setTitulo(event.target.value)} required />
          </label>
          <label>
            <span>Modalidade</span>
            <select value={modalidade} onChange={(event) => setModalidade(event.target.value as MuralModalidade)}>
              <option value="aviso">Aviso</option>
              <option value="recebimento_arquivo">Recebimento de arquivo</option>
            </select>
          </label>
          <label className="full">
            <span>Conteudo</span>
            <RichTextEditor value={conteudo} onChange={setConteudo} placeholder="Escreva o aviso." />
          </label>
          <label>
            <span>Link</span>
            <input value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} />
          </label>
          <label className="full">
            <span>Anexos do post</span>
            <input key={fileInputKey} type="file" multiple onChange={handleFilesChange} />
          </label>
          {(anexosExistentes.length > 0 || novosAnexos.length > 0) && (
            <div className="admin-mural__attachment-list">
              {anexosExistentes.map((anexo, index) => (
                <a key={`anexo-existente-${index}`} href={anexo.url} target="_blank" rel="noreferrer">
                  {anexo.titulo || `Anexo ${index + 1}`}
                </a>
              ))}
              {novosAnexos.map((arquivo) => (
                <span key={arquivo.name}>{arquivo.name}</span>
              ))}
            </div>
          )}
          <label className="checkbox">
            <input type="checkbox" checked={fixado} onChange={(event) => setFixado(event.target.checked)} />
            Fixar no topo
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={includeAll}
              onChange={(event) => {
                const checked = event.target.checked;
                setIncludeAll(checked);
                if (checked) {
                  setGtIds([]);
                }
              }}
            />
            Enviar para todos os GTs
          </label>
          {!includeAll && (
            <div className="admin-mural__gts">
              {gtOptions.map((gt) => (
                <label key={gt.id}>
                  <input
                    type="checkbox"
                    checked={gtIds.includes(gt.id)}
                    onChange={(event) => {
                      if (event.target.checked) {
                        setGtIds((prev) => [...prev, gt.id]);
                      } else {
                        setGtIds((prev) => prev.filter((id) => id !== gt.id));
                      }
                    }}
                  />
                  {gt.displayName}
                </label>
              ))}
            </div>
          )}
          <div className="admin-mural__actions">
            <Button type="submit" variant="secondary" disabled={createPost.isPending || updatePost.isPending}>
              {editingId ? 'Atualizar' : 'Publicar'}
            </Button>
            {editingId && (
              <Button type="button" variant="ghost" onClick={resetForm}>
                Cancelar
              </Button>
            )}
          </div>
          {feedback && <p className="admin-mural__feedback">{feedback}</p>}
        </form>
      </Card>

      <div className="admin-mural__list-header">
        <div>
          <h2>Ordem do mural</h2>
          <p>
            {isFilteringByGt
              ? 'Lista filtrada por GT. O drag and drop reordena apenas os avisos visiveis neste filtro.'
              : 'Arraste os avisos para reordenar. Fixados permanecem acima dos demais.'}
          </p>
        </div>
        <div className="admin-mural__list-tools">
          <label className="admin-mural__filter">
            <span>Filtrar por GT</span>
            <select value={selectedGtFilter} onChange={(event) => setSelectedGtFilter(event.target.value)}>
              <option value="all">Todos os GTs</option>
              {gtOptions.map((gt) => (
                <option key={gt.id} value={String(gt.id)}>
                  {gt.displayName}
                </option>
              ))}
            </select>
          </label>
          {reorderPosts.isPending && <span className="admin-mural__saving">Salvando ordem...</span>}
        </div>
      </div>

      <div className="admin-mural__lista">
        {visiblePosts.map((post) => (
          <Card key={post.id}>
            <article
              className={[
                'admin-mural__item',
                draggedPostId === post.id ? 'admin-mural__item--dragging' : '',
                dropTargetId === post.id && draggedPostId !== post.id ? 'admin-mural__item--drop-target' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              draggable={!reorderPosts.isPending}
              onDragStart={(event) => handleDragStart(event, post)}
              onDragOver={(event) => handleDragOver(event, post)}
              onDrop={(event) => void handleDrop(event, post)}
              onDragEnd={handleDragEnd}
            >
              <header>
                <div>
                  <h3>{post.titulo}</h3>
                  <span>{new Date(post.updated_at).toLocaleString('pt-BR')}</span>
                </div>
                <div className="admin-mural__meta">
                  <span
                    className="admin-mural__drag-handle"
                    title={isFilteringByGt ? 'Arraste para reordenar dentro do GT filtrado' : 'Arraste para reordenar'}
                  >
                    Arrastar
                  </span>
                  {post.modalidade === 'recebimento_arquivo' && (
                    <span className="admin-mural__badge admin-mural__badge--info">Recebe arquivo</span>
                  )}
                  {post.fixado && <span className="admin-mural__badge">Fixado</span>}
                </div>
              </header>
              <div className="admin-mural__item-content" dangerouslySetInnerHTML={{ __html: post.conteudo_html }} />
              {post.link_url && (
                <a className="admin-mural__reference-link" href={post.link_url} target="_blank" rel="noreferrer">
                  Abrir link
                </a>
              )}
              {post.anexos && post.anexos.length > 0 && (
                <div className="admin-mural__attachment-list">
                  {post.anexos.map((anexo, idx) => (
                    <a key={`${post.id}-anexo-${idx}`} href={anexo.url} target="_blank" rel="noreferrer">
                      {anexo.titulo || `Anexo ${idx + 1}`}
                    </a>
                  ))}
                </div>
              )}
              {post.modalidade === 'recebimento_arquivo' && (
                <div className="admin-mural__submissions">
                  <h4>Arquivos recebidos</h4>
                  {post.envios_arquivo && post.envios_arquivo.length > 0 ? (
                    post.envios_arquivo.map((envio) => (
                      <div key={envio.id} className="admin-mural__submission-item">
                        <div>
                          <strong>{envio.nome_arquivo}</strong>
                          <span>
                            {envio.gt_nome ? `${envio.gt_nome} · ` : ''}
                            {envio.usuario_nome || 'Usuario'}
                          </span>
                        </div>
                        <a href={envio.arquivo_url} target="_blank" rel="noreferrer">
                          Baixar
                        </a>
                      </div>
                    ))
                  ) : (
                    <p className="admin-mural__submissions-empty">Nenhum arquivo enviado ainda.</p>
                  )}
                </div>
              )}
              <div className="admin-mural__item-actions">
                <Button size="sm" variant="ghost" onClick={() => handleEdit(post)} title="Editar aviso">
                  Editar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deletePost.mutate(post.id)}
                  disabled={deletePost.isPending}
                  title="Remover aviso"
                >
                  Remover
                </Button>
              </div>
            </article>
          </Card>
        ))}
        {visiblePosts.length === 0 && (
          <Card>
            <div className="admin-mural__empty-state">
              Nenhum aviso encontrado para o GT selecionado.
            </div>
          </Card>
        )}
      </div>

      <section className="admin-mural__references">
        <h2>Materiais da biblioteca</h2>
        <div className="admin-mural__references-grid">
          {referencias.map((item) => {
            if (item.kind === 'midia') {
              const descricao = item.descricao?.trim() || item.link_url;
              return (
                <Card key={item.id}>
                  <div className="admin-mural__reference-card">
                    <header>
                      <div>
                        <h3>{item.titulo}</h3>
                        <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                      </div>
                    </header>
                    <p>{descricao}</p>
                    <a className="admin-mural__reference-link" href={item.link_url} target="_blank" rel="noreferrer">
                      Abrir link
                    </a>
                  </div>
                </Card>
              );
            }
            return (
              <Card key={item.id}>
                <div className="admin-mural__reference-card">
                  <header>
                    <div>
                      <h3>{item.titulo}</h3>
                      <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                    </div>
                  </header>
                  <div dangerouslySetInnerHTML={{ __html: item.conteudo_html }} />
                </div>
              </Card>
            );
          })}
          {referencias.length === 0 && <p className="admin-mural__references-empty">Nenhuma referencia encontrada.</p>}
        </div>
      </section>
    </div>
  );
}
