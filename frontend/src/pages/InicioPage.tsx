import { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import { useContinuar } from '@/hooks/useContinuar';
import type { Revisao } from '@/api/types';

import './InicioPage.css';

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

const stripHtml = (html?: string | null) => {
  if (!html) return '';
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
};

export function InicioPage() {
  const navigate = useNavigate();
  const { gtOptions, isLoading: gtsLoading } = useAvailableGts();
  const { data: respostas, isLoading: respostasLoading } = useRespostas({ includeAll: true });
  const { data: revisoes, isLoading: revisoesLoading } = useRevisoes({ alvoTipo: 'resposta', pageSize: 200 });
  const continuar = useContinuar();

  const respostaIds = useMemo(() => new Set((respostas ?? []).map((resp) => resp.id)), [respostas]);

  const pareceres = useMemo(() => {
    return (revisoes ?? [])
      .filter((rev) => rev.alvo_tipo === 'resposta' && respostaIds.has(rev.alvo_id))
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 5);
  }, [revisoes, respostaIds]);

  if (gtsLoading || respostasLoading || revisoesLoading) {
    return <FullPageLoader message="Carregando início..." />;
  }

  return (
    <div className="inicio">
      <PageHeader
        title="Bem-vindo(a) ao PROLUC"
        description="Aqui você acompanha suas trilhas e os pareceres do redator."
        actions={(
          <div className="inicio__actions">
            <Button
              variant="primary"
              onClick={async () => {
                const data = await continuar.mutateAsync();
                if (data?.url) {
                  navigate(data.url);
                }
              }}
              disabled={continuar.isPending}
            >
              {continuar.isPending ? 'Carregando...' : 'Continuar'}
            </Button>
            <Link to="/mural">
              <Button variant="secondary">Ver Mural</Button>
            </Link>
          </div>
        )}
      />

      <section className="inicio__stats">
        <Card>
          <div className="inicio__stat">
            <span>GTs vinculados</span>
            <strong>{gtOptions.length}</strong>
            <p>Esses são os grupos em que você atua.</p>
          </div>
        </Card>
        <Card>
          <div className="inicio__stat">
            <span>Respostas registradas</span>
            <strong>{respostas?.length ?? 0}</strong>
            <p>Use "Minha Trilha" para continuar as respostas pendentes.</p>
          </div>
        </Card>
        <Card>
          <div className="inicio__stat">
            <span>Pareceres recentes</span>
            <strong>{pareceres.length}</strong>
            <p>Feedbacks do redator para seu GT.</p>
          </div>
        </Card>
      </section>

      <Card>
        <div className="inicio__pareceres-header">
          <div>
            <h2>Pareceres do redator</h2>
            <p>Ajuste sua trilha a partir dos pareceres recebidos.</p>
          </div>
          <Link to="/minha-trilha">
            <Button size="sm" variant="ghost">Abrir trilhas</Button>
          </Link>
        </div>
        {pareceres.length > 0 ? (
          <div className="inicio__pareceres-list">
            {pareceres.map((rev) => {
              const preview = rev.alvo_preview as Revisao['alvo_preview'];
              const tarefaId = preview && 'tarefa' in preview ? preview.tarefa : null;
              const gtId = preview && 'gt' in preview ? preview.gt : null;
              const linkTo = tarefaId && gtId ? `/minha-trilha/${tarefaId}?gt=${gtId}` : '/minha-trilha';
              return (
                <div key={rev.id} className="inicio__parecer">
                  <div>
                    <strong>Revisão #{rev.id}</strong>
                    <span>{stripHtml(rev.parecer_html) || 'Sem parecer detalhado.'}</span>
                  </div>
                  <div className="inicio__parecer-meta">
                    <span>Status: {rev.status}</span>
                    <span>Atualizado {formatDateTime(rev.updated_at)}</span>
                    <Link to={linkTo}>
                      <Button size="sm" variant="primary">Abrir</Button>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="inicio__empty">Nenhum parecer disponível ainda.</div>
        )}
      </Card>
    </div>
  );
}
