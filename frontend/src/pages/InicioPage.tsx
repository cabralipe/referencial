import { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { buildBackendUrl } from '@/config/env';
import { useAuth } from '@/context/AuthContext';
import { useAvailableGts } from '@/hooks/useAvailableGts';
import { useContinuar } from '@/hooks/useContinuar';
import { usePppDocumento } from '@/hooks/usePpp';
import { useRespostas } from '@/hooks/useRespostas';
import { useRevisoes } from '@/hooks/useRevisoes';
import type { Revisao } from '@/api/types';

import './InicioPage.css';

const PPP_STATUS_LABELS: Record<string, string> = {
  em_elaboracao: 'Em elaboracao',
  concluido: 'Concluido',
};

const formatDateTime = (value?: string | null) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

const stripHtml = (html?: string | null) => {
  if (!html) return '';
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
};

export function InicioPage() {
  const { user } = useAuth();
  const isSchoolLeader = user?.role === 'diretor' || user?.role === 'coordenador_pedagogico';
  const isProfessor = user?.role === 'professor';

  if (isSchoolLeader || isProfessor) {
    return <SchoolInicioContent isProfessor={isProfessor} />;
  }

  return <MemberInicioContent />;
}

function SchoolInicioContent({ isProfessor }: { isProfessor: boolean }) {
  const { user } = useAuth();
  const avaHref = buildBackendUrl('/ava/catalogo/');
  const pppQuery = usePppDocumento({
    escolaId: user?.escolaId,
    enabled: Boolean(user?.escolaId),
  });

  if (pppQuery.isLoading) {
    return <FullPageLoader message="Carregando inicio..." />;
  }

  const ppp = pppQuery.data;
  const statusLabel = PPP_STATUS_LABELS[ppp?.status ?? ''] ?? (ppp?.status || 'Não iniciado');
  const comentariosAbertos = ppp?.comentarios_abertos ?? 0;
  const isAvailable = ppp?.is_available !== false;
  const title = isProfessor ? 'Acompanhamento da escola' : 'Painel da escola';
  const description = isProfessor
    ? 'Consulte o PPP liberado, acompanhe os avisos e acesse rapidamente o AVA.'
    : 'Acompanhe o andamento do PPP da escola, comentarios abertos e atalhos principais.';

  return (
    <div className="inicio">
      <PageHeader
        title={title}
        description={description}
        actions={(
          <div className="inicio__actions">
            <Link to="/ppp">
              <Button variant="primary" disabled={!user?.escolaId}>Abrir PPP</Button>
            </Link>
            <a href={avaHref} target="_blank" rel="noopener noreferrer">
              <Button variant="secondary">Acessar AVA</Button>
            </a>
          </div>
        )}
      />

      <section className="inicio__stats">
        <Card>
          <div className="inicio__stat">
            <span>Escola vinculada</span>
            <strong>{ppp?.escola_nome || 'Não informada'}</strong>
            <p>
              {user?.escolaId
                ? 'Os dados desta pagina consideram a escola associada ao seu usuario.'
                : 'Associe uma escola ao usuario para liberar os dados institucionais.'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="inicio__stat">
            <span>Status do PPP</span>
            <strong>{statusLabel}</strong>
            <p>
              {isProfessor
                ? 'Professores consultam a versao disponibilizada pela gestao.'
                : 'Direcao e coordenacao acompanham a elaboracao e publicacao do documento.'}
            </p>
          </div>
        </Card>
        <Card>
          <div className="inicio__stat">
            <span>{isProfessor ? 'Disponibilidade' : 'Comentarios abertos'}</span>
            <strong>{isProfessor ? (isAvailable ? 'Liberado' : 'Aguardando') : comentariosAbertos}</strong>
            <p>
              {isProfessor
                ? (ppp?.availability_message ?? 'O documento será exibido assim que a versão concluída estiver disponível.')
                : 'Pendencias e observacoes registradas no fluxo do PPP da escola.'}
            </p>
          </div>
        </Card>
      </section>

      <section className="inicio__school-grid">
        <Card>
          <div className="inicio__panel">
            <div className="inicio__panel-header">
              <div>
                <h2>Resumo do PPP</h2>
                <p>Situacao atual do documento institucional da escola.</p>
              </div>
            </div>
            {ppp ? (
              <div className="inicio__meta-list">
                <div className="inicio__meta-item">
                  <span>Titulo</span>
                  <strong>{ppp.titulo || 'Título ainda não definido'}</strong>
                </div>
                <div className="inicio__meta-item">
                  <span>Última edição</span>
                  <strong>{formatDateTime(ppp.updated_at)}</strong>
                </div>
                <div className="inicio__meta-item">
                  <span>Responsavel pela ultima edicao</span>
                  <strong>{ppp.ultima_edicao_por_nome ?? 'Não identificado'}</strong>
                </div>
                <div className="inicio__meta-item">
                  <span>Versao</span>
                  <strong>{ppp.version}</strong>
                </div>
                <div className="inicio__meta-item">
                  <span>Conclusao</span>
                  <strong>{ppp.concluido_em ? formatDateTime(ppp.concluido_em) : 'Ainda não concluído'}</strong>
                </div>
              </div>
            ) : (
              <div className="inicio__empty">Nenhum PPP foi localizado para a escola vinculada.</div>
            )}
          </div>
        </Card>

        <Card>
          <div className="inicio__panel">
            <div className="inicio__panel-header">
              <div>
                <h2>Proximos acessos</h2>
                <p>Atalhos uteis para a rotina escolar.</p>
              </div>
            </div>
            <div className="inicio__quick-links">
              <Link className="inicio__quick-link" to="/ppp">
                <strong>{isProfessor ? 'Consultar PPP' : 'Gerenciar PPP'}</strong>
                <span>
                  {isProfessor
                    ? 'Abra a versão disponível do documento da escola.'
                    : 'Edite, acompanhe comentarios e finalize o documento.'}
                </span>
              </Link>
              <a className="inicio__quick-link" href={avaHref} target="_blank" rel="noopener noreferrer">
                <strong>Acessar AVA</strong>
                <span>Entre no ambiente virtual para acompanhar conteúdos e percursos formativos.</span>
              </a>
              <Link className="inicio__quick-link" to="/mural">
                <strong>Acompanhar mural</strong>
                <span>Consulte comunicados e atualizacoes recentes publicados para sua escola.</span>
              </Link>
            </div>
          </div>
        </Card>
      </section>
    </div>
  );
}

function MemberInicioContent() {
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
    return <FullPageLoader message="Carregando inicio..." />;
  }

  return (
    <div className="inicio">
      <PageHeader
        title="Bem-vindo(a) ao PROLUC"
        description="Aqui voce acompanha suas trilhas e os pareceres do redator."
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
            <p>Esses sao os grupos em que voce atua.</p>
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
                    <strong>Revisao #{rev.id}</strong>
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
