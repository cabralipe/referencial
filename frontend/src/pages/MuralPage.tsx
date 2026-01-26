import { useMemo } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useMural } from '@/hooks/useMural';

import './MuralPage.css';

export function MuralPage() {
  const { data: posts, isLoading } = useMural();

  const ordered = useMemo(() => {
    return (posts ?? []).slice().sort((a, b) => {
      const fixA = a.fixado ? 1 : 0;
      const fixB = b.fixado ? 1 : 0;
      if (fixA !== fixB) return fixB - fixA;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [posts]);

  if (isLoading) {
    return <FullPageLoader message="Carregando mural..." />;
  }

  return (
    <div className="mural">
      <PageHeader
        title="Mural"
        description="Acompanhe os avisos e documentos publicados pela administração."
      />

      <div className="mural__grid">
        {ordered.map((post) => (
          <Card key={post.id}>
            <div className="mural__card">
              <header>
                <div>
                  <h2>{post.titulo}</h2>
                  <span>{new Date(post.updated_at).toLocaleString('pt-BR')}</span>
                </div>
                {post.fixado && <span className="mural__badge">Fixado</span>}
              </header>
              <div dangerouslySetInnerHTML={{ __html: post.conteudo_html }} />
              {post.link_url && (
                <a className="mural__link" href={post.link_url} target="_blank" rel="noreferrer">
                  Abrir link
                </a>
              )}
              {post.anexos && post.anexos.length > 0 && (
                <div className="mural__anexos">
                  {post.anexos.map((anexo, index) => (
                    <a key={`${post.id}-${index}`} href={anexo.url} target="_blank" rel="noreferrer">
                      {anexo.titulo || 'Anexo'}
                    </a>
                  ))}
                </div>
              )}
              {post.criado_por?.nome && (
                <p className="mural__autor">Publicado por {post.criado_por.nome}</p>
              )}
            </div>
          </Card>
        ))}
        {ordered.length === 0 && <p className="mural__empty">Nenhum aviso publicado ainda.</p>}
      </div>
    </div>
  );
}
