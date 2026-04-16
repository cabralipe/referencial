import { ChangeEvent, FormEvent, useMemo, useState } from 'react';

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

  const ordered = useMemo(() => {
    return (posts ?? []).slice().sort((a, b) => {
      const ordemA = a.ordem ?? 0;
      const ordemB = b.ordem ?? 0;
      if (ordemA !== ordemB) return ordemA - ordemB;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [posts]);

  const handleMove = (index: number, direction: 'up' | 'down') => {
    const list = [...ordered];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= list.length) return;
    [list[index], list[targetIndex]] = [list[targetIndex], list[index]];
    const items = list.map((post, i) => ({ id: post.id, ordem: i }));
    reorderPosts.mutate(items);
  };

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
      setFeedback('Informe o conteúdo do aviso.');
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
      setFeedback(error instanceof Error ? error.message : 'Não foi possível salvar o aviso.');
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
            <span>Título</span>
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
            <span>Conteúdo</span>
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

      <div className="admin-mural__lista">
        {ordered.map((post, index) => (
          <Card key={post.id}>
            <div className="admin-mural__item">
              <header>
                <div>
                  <h3>{post.titulo}</h3>
                  <span>{new Date(post.updated_at).toLocaleString('pt-BR')}</span>
                </div>
                <div className="admin-mural__meta">
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
                            {envio.usuario_nome || 'Usuário'}
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
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleMove(index, 'up')}
                  disabled={index === 0 || reorderPosts.isPending}
                  title="Mover para cima"
                >
                  ▲
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleMove(index, 'down')}
                  disabled={index === ordered.length - 1 || reorderPosts.isPending}
                  title="Mover para baixo"
                >
                  ▼
                </Button>
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
            </div>
          </Card>
        ))}
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
          {referencias.length === 0 && <p className="admin-mural__references-empty">Nenhuma referência encontrada.</p>}
        </div>
      </section>
    </div>
  );
}
