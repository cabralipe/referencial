import { FormEvent, useMemo, useState } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useCreateMuralPost, useDeleteMuralPost, useMural, useUpdateMuralPost } from '@/hooks/useMural';

import './AdminMuralPage.css';

export function AdminMuralPage() {
  const { data: posts, isLoading } = useMural();
  const { gtOptions } = useAvailableGts({ scope: 'all' });
  const createPost = useCreateMuralPost();
  const updatePost = useUpdateMuralPost();
  const deletePost = useDeleteMuralPost();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [titulo, setTitulo] = useState('');
  const [conteudo, setConteudo] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [fixado, setFixado] = useState(false);
  const [gtIds, setGtIds] = useState<number[]>([]);
  const [includeAll, setIncludeAll] = useState(true);
  const [feedback, setFeedback] = useState('');

  const ordered = useMemo(() => {
    return (posts ?? []).slice().sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
  }, [posts]);

  const resetForm = () => {
    setEditingId(null);
    setTitulo('');
    setConteudo('');
    setLinkUrl('');
    setFixado(false);
    setGtIds([]);
    setIncludeAll(true);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    const payload = {
      titulo,
      conteudo_html: conteudo,
      link_url: linkUrl || undefined,
      fixado,
      include_all: includeAll,
      gt_ids: includeAll ? [] : gtIds,
    };
    try {
      if (editingId) {
        await updatePost.mutateAsync({ id: editingId, ...payload });
      } else {
        await createPost.mutateAsync(payload);
      }
      resetForm();
    } catch (error) {
      setFeedback('Não foi possível salvar o aviso.');
    }
  };

  if (isLoading) {
    return <FullPageLoader message="Carregando mural..." />;
  }

  return (
    <div className="admin-mural">
      <PageHeader
        title="Admin · Mural"
        description="Publique avisos para os membros do GT e acompanhe os comunicados." 
      />

      <Card>
        <form className="admin-mural__form" onSubmit={handleSubmit}>
          <h2>{editingId ? 'Editar aviso' : 'Novo aviso'}</h2>
          <label>
            <span>Título</span>
            <input value={titulo} onChange={(event) => setTitulo(event.target.value)} required />
          </label>
          <label className="full">
            <span>Conteúdo (HTML)</span>
            <textarea value={conteudo} onChange={(event) => setConteudo(event.target.value)} rows={4} required />
          </label>
          <label>
            <span>Link</span>
            <input value={linkUrl} onChange={(event) => setLinkUrl(event.target.value)} />
          </label>
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
        {ordered.map((post) => (
          <Card key={post.id}>
            <div className="admin-mural__item">
              <header>
                <div>
                  <h3>{post.titulo}</h3>
                  <span>{new Date(post.updated_at).toLocaleString('pt-BR')}</span>
                </div>
                {post.fixado && <span className="admin-mural__badge">Fixado</span>}
              </header>
              <div dangerouslySetInnerHTML={{ __html: post.conteudo_html }} />
              <div className="admin-mural__item-actions">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditingId(post.id);
                    setTitulo(post.titulo);
                    setConteudo(post.conteudo_html);
                    setLinkUrl(post.link_url ?? '');
                    setFixado(Boolean(post.fixado));
                    setGtIds(post.gt_ids ?? []);
                    setIncludeAll(!(post.gt_ids && post.gt_ids.length > 0));
                  }}
                >
                  Editar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => deletePost.mutate(post.id)}
                  disabled={deletePost.isPending}
                >
                  Remover
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
