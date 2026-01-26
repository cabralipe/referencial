import { useMemo } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useBlocos, useMidias } from '@/hooks/useBiblioteca';
import { useMural } from '@/hooks/useMural';

import './MuralPage.css';

type MuralItem =
  | {
      kind: 'mural';
      id: string;
      titulo: string;
      conteudo_html: string;
      link_url?: string | null;
      anexos?: Array<{ titulo?: string; url?: string }>;
      fixado?: boolean;
      criado_por?: { nome?: string | null };
      updated_at: string;
    }
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

export function MuralPage() {
  const { data: posts, isLoading } = useMural();
  const { data: midias, isLoading: midiasLoading } = useMidias();
  const { data: blocos, isLoading: blocosLoading } = useBlocos();

  const ordered = useMemo<MuralItem[]>(() => {
    const muralItems: MuralItem[] = (posts ?? []).map((post) => ({
      kind: 'mural',
      id: post.id,
      titulo: post.titulo,
      conteudo_html: post.conteudo_html,
      link_url: post.link_url,
      anexos: post.anexos,
      fixado: post.fixado,
      criado_por: post.criado_por,
      updated_at: post.updated_at,
    }));
    const blocoItems: MuralItem[] = (blocos ?? []).map((bloco) => ({
      kind: 'bloco',
      id: `bloco-${bloco.id}`,
      titulo: bloco.titulo,
      conteudo_html: bloco.conteudo_html,
      updated_at: bloco.updated_at,
    }));
    const midiaItems: MuralItem[] = (midias ?? []).map((midia) => ({
      kind: 'midia',
      id: `midia-${midia.id}`,
      titulo: midia.titulo || 'Link da biblioteca',
      descricao: midia.descricao,
      link_url: midia.url,
      updated_at: midia.created_at,
    }));
    return [...muralItems, ...blocoItems, ...midiaItems].sort((a, b) => {
      const fixA = a.kind === 'mural' && a.fixado ? 1 : 0;
      const fixB = b.kind === 'mural' && b.fixado ? 1 : 0;
      if (fixA !== fixB) return fixB - fixA;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [posts, blocos, midias]);

  if (isLoading || midiasLoading || blocosLoading) {
    return <FullPageLoader message="Carregando mural..." />;
  }

  return (
    <div className="mural">
      <PageHeader
        title="Mural"
        description="Acompanhe os avisos e documentos publicados pela administração."
      />

      <div className="mural__grid">
        {ordered.map((item) => {
          if (item.kind === 'midia') {
            const descricao = item.descricao?.trim() || item.link_url;
            return (
              <Card key={item.id}>
                <div className="mural__card">
                  <header>
                    <div>
                      <h2>{item.titulo}</h2>
                      <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                    </div>
                  </header>
                  <p>{descricao}</p>
                  <a className="mural__link" href={item.link_url} target="_blank" rel="noreferrer">
                    Abrir link
                  </a>
                </div>
              </Card>
            );
          }
          if (item.kind === 'bloco') {
            return (
              <Card key={item.id}>
                <div className="mural__card">
                  <header>
                    <div>
                      <h2>{item.titulo}</h2>
                      <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                    </div>
                  </header>
                  <div dangerouslySetInnerHTML={{ __html: item.conteudo_html }} />
                </div>
              </Card>
            );
          }
          return (
            <Card key={item.id}>
              <div className="mural__card">
                <header>
                  <div>
                    <h2>{item.titulo}</h2>
                    <span>{new Date(item.updated_at).toLocaleString('pt-BR')}</span>
                  </div>
                  {item.fixado && <span className="mural__badge">Fixado</span>}
                </header>
                <div dangerouslySetInnerHTML={{ __html: item.conteudo_html }} />
                {item.link_url && (
                  <a className="mural__link" href={item.link_url} target="_blank" rel="noreferrer">
                    Abrir link
                  </a>
                )}
                {item.anexos && item.anexos.length > 0 && (
                  <div className="mural__anexos">
                    {item.anexos.map((anexo, index) => (
                      <a key={`${item.id}-${index}`} href={anexo.url} target="_blank" rel="noreferrer">
                        {anexo.titulo || 'Anexo'}
                      </a>
                    ))}
                  </div>
                )}
                {item.criado_por?.nome && (
                  <p className="mural__autor">Publicado por {item.criado_por.nome}</p>
                )}
              </div>
            </Card>
          );
        })}
        {ordered.length === 0 && <p className="mural__empty">Nenhum aviso publicado ainda.</p>}
      </div>
    </div>
  );
}
