import { FormEvent, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useAuth } from '@/context/AuthContext';
import {
  useBancoPlanos,
  useCertificacaoStatus,
  useCreatePlanoAula,
  useCurso,
  useEmitirCertificado,
  useEnviarPlanoAula,
  useMarcarProgresso,
  usePlanosAula,
  useUpdateBancoPlano,
  useUpdatePlanoAula,
} from '@/hooks/useCourses';

import './CursoDetailPage.css';

const PLANO_FIELDS = [
  ['escola', 'Escola'],
  ['professor', 'Professor'],
  ['etapa_modalidade', 'Etapa/Modalidade'],
  ['componente_curricular', 'Componente Curricular'],
  ['unidade_tematica', 'Unidade Temática'],
  ['habilidades_referencial', 'Habilidades (código do Referencial)'],
  ['objetivos_aprendizagem', 'Objetivos de Aprendizagem'],
  ['conteudos', 'Conteúdos'],
  ['metodologia', 'Metodologia'],
  ['recursos', 'Recursos'],
  ['avaliacao', 'Avaliação'],
  ['estrategias_recomposicao', 'Estratégias de Recomposição'],
  ['estrategias_inclusivas_aee', 'Estratégias Inclusivas (AEE)'],
  ['referencias', 'Referências'],
] as const;

export function CursoDetailPage() {
  const { id } = useParams();
  const cursoId = id ? Number(id) : undefined;
  const { user } = useAuth();
  const isTutorOrAdmin = ['articulador', 'admin_cliente', 'super_admin'].includes(user?.role ?? '');
  const isAdmin = ['admin_cliente', 'super_admin'].includes(user?.role ?? '');
  const [filtroComponente, setFiltroComponente] = useState('');
  const [filtroEtapa, setFiltroEtapa] = useState('');
  const [filtroStatusBanco, setFiltroStatusBanco] = useState(isTutorOrAdmin ? 'ENVIADO' : 'PUBLICADO');

  const { data: curso, isLoading } = useCurso(id);
  const { data: certStatus } = useCertificacaoStatus(cursoId);
  const { data: planos } = usePlanosAula(cursoId);
  const { data: bancoPlanos } = useBancoPlanos({
    componente: filtroComponente || undefined,
    etapaModalidade: filtroEtapa || undefined,
    status: filtroStatusBanco || undefined,
  });

  const marcarProgresso = useMarcarProgresso(cursoId);
  const criarPlano = useCreatePlanoAula(cursoId);
  const atualizarPlano = useUpdatePlanoAula();
  const enviarPlano = useEnviarPlanoAula();
  const emitirCertificado = useEmitirCertificado(cursoId);
  const updateBancoPlano = useUpdateBancoPlano();

  const [editingPlanoId, setEditingPlanoId] = useState<number | null>(null);
  const [planoTitulo, setPlanoTitulo] = useState('');
  const [compartilharBanco, setCompartilharBanco] = useState(true);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(
    Object.fromEntries(PLANO_FIELDS.map(([k]) => [k, ''])),
  );
  const [feedback, setFeedback] = useState('');

  const progressoItemIds = useMemo(
    () => new Set((curso?.progresso?.itens ?? []).map((item) => item.item_id).filter(Boolean)),
    [curso?.progresso?.itens],
  );

  const publicacoesDoCurso = useMemo(() => {
    const allowed = new Set((planos ?? []).map((p) => p.id));
    return (bancoPlanos ?? []).filter((pub) => allowed.has(pub.resposta_formulario_id));
  }, [bancoPlanos, planos]);

  const minhasPublicacoes = useMemo(() => {
    if (!user) return [];
    return publicacoesDoCurso.filter((pub) => pub.autor === user.id);
  }, [publicacoesDoCurso, user]);

  const beginEditPlano = (planoId?: number) => {
    if (!planoId) {
      setEditingPlanoId(null);
      setPlanoTitulo('');
      setFieldValues(Object.fromEntries(PLANO_FIELDS.map(([k]) => [k, ''])));
      return;
    }
    const plano = (planos ?? []).find((p) => p.id === planoId);
    if (!plano) return;
    setEditingPlanoId(plano.id);
    setPlanoTitulo(plano.titulo ?? '');
    setFieldValues({
      ...Object.fromEntries(PLANO_FIELDS.map(([k]) => [k, ''])),
      ...(plano.campos ?? plano.dados_cache_json ?? {}),
    });
    setCompartilharBanco(Boolean(plano.compartilhado_banco));
  };

  const handleSubmitPlano = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    if (!cursoId) return;
    try {
      if (editingPlanoId) {
        await atualizarPlano.mutateAsync({
          id: editingPlanoId,
          cursoId,
          payload: { titulo: planoTitulo, campos: fieldValues },
        });
        setFeedback('Plano atualizado.');
      } else {
        const created = await criarPlano.mutateAsync({ titulo: planoTitulo, campos: fieldValues });
        setEditingPlanoId(created.id);
        setFeedback('Plano criado como rascunho.');
      }
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Falha ao salvar plano.');
    }
  };

  const handleEnviarPlano = async () => {
    if (!editingPlanoId || !cursoId) return;
    setFeedback('');
    try {
      await enviarPlano.mutateAsync({
        id: editingPlanoId,
        cursoId,
        compartilharNoBanco: compartilharBanco,
      });
      setFeedback('Plano enviado com sucesso.');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Falha ao enviar plano.');
    }
  };

  if (isLoading || !curso) {
    return <FullPageLoader message="Carregando curso..." />;
  }

  return (
    <div className="curso-detail">
      <PageHeader
        title={curso.nome}
        description={curso.descricao || 'Curso AVAMEC integrado à plataforma.'}
        actions={
          <div className="curso-detail__header-actions">
            <span className="curso-detail__progress-pill">
              Progresso: {Number(curso.progresso?.percentual ?? 0)}%
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => emitirCertificado.mutate()}
              disabled={!certStatus?.pode_emitir_certificado || emitirCertificado.isPending}
            >
              {emitirCertificado.isPending ? 'Emitindo...' : 'Emitir certificado'}
            </Button>
            {isAdmin && cursoId && (
              <Link className="curso-detail__header-link" to={`/admin/cursos/${cursoId}/banco-planos`}>
                Moderar banco
              </Link>
            )}
          </div>
        }
      />

      <section className="curso-detail__top-grid">
        <Card className="curso-detail__panel">
          <h3>Visão do curso</h3>
          <p>{curso.objetivos || 'Objetivos não informados.'}</p>
          <div className="curso-detail__stats">
            <span>Total: {curso.carga_horaria_total ?? 0}h</span>
            <span>Presencial: {curso.carga_presencial ?? 0}h</span>
            <span>Síncrona: {curso.carga_sincrona ?? 0}h</span>
            <span>Produção: {curso.carga_producao ?? 0}h</span>
          </div>
        </Card>

        <Card className="curso-detail__panel">
          <h3>Certificação</h3>
          {certStatus ? (
            <ul className="curso-detail__checks">
              {Object.entries(certStatus.checks).map(([key, check]) => (
                <li key={key} className={check.ok ? 'is-ok' : 'is-pending'}>
                  <strong>{key}</strong>
                  <span>
                    {String(check.value)} / {String(check.required)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>Carregando status de certificação...</p>
          )}
          {certStatus?.certificado_emitido && certStatus.certificado && (
            <p className="curso-detail__cert-code">Código: {certStatus.certificado.codigo}</p>
          )}
        </Card>
      </section>

      <section className="curso-detail__content-grid">
        <div className="curso-detail__main">
          <Card className="curso-detail__panel">
            <h3>Avisos</h3>
            <div className="curso-detail__list">
              {(curso.avisos ?? []).length === 0 && <p>Nenhum aviso publicado.</p>}
              {(curso.avisos ?? []).map((aviso) => (
                <article key={aviso.id} className="curso-detail__list-item">
                  <h4>{aviso.titulo}</h4>
                  <small>{aviso.publicado_em ? new Date(aviso.publicado_em).toLocaleString('pt-BR') : 'Sem data'}</small>
                  <p>{aviso.corpo}</p>
                </article>
              ))}
            </div>
          </Card>

          <Card className="curso-detail__panel">
            <h3>Módulos e Itens</h3>
            <div className="curso-detail__modules">
              {curso.modulos.map((modulo) => (
                <section key={modulo.id} className="curso-detail__module">
                  <header>
                    <div>
                      <strong>{modulo.ordem}. {modulo.titulo}</strong>
                      <small>{modulo.tipo}</small>
                    </div>
                  </header>
                  <ul>
                    {modulo.itens.map((item) => (
                      <li key={item.id}>
                        <div>
                          <span>{item.ordem}. {item.titulo}</span>
                          <small>{item.tipo}</small>
                        </div>
                        <Button
                          size="sm"
                          variant={progressoItemIds.has(item.id) ? 'secondary' : 'outline'}
                          disabled={progressoItemIds.has(item.id) || marcarProgresso.isPending}
                          onClick={() => marcarProgresso.mutate(item.id)}
                        >
                          {progressoItemIds.has(item.id) ? 'Concluído' : 'Marcar conclusão'}
                        </Button>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </Card>

          <Card className="curso-detail__panel">
            <h3>Banco Colaborativo de Planos</h3>
            <div className="curso-detail__bank-filters">
              <label>
                <span>Componente</span>
                <input value={filtroComponente} onChange={(e) => setFiltroComponente(e.target.value)} placeholder="Matemática" />
              </label>
              <label>
                <span>Etapa/Modalidade</span>
                <input value={filtroEtapa} onChange={(e) => setFiltroEtapa(e.target.value)} placeholder="Anos Finais" />
              </label>
              <label>
                <span>Status</span>
                <select value={filtroStatusBanco} onChange={(e) => setFiltroStatusBanco(e.target.value)}>
                  {!isTutorOrAdmin && <option value="PUBLICADO">PUBLICADO</option>}
                  {isTutorOrAdmin && (
                    <>
                      <option value="">Todos</option>
                      <option value="ENVIADO">ENVIADO</option>
                      <option value="APROVADO">APROVADO</option>
                      <option value="PUBLICADO">PUBLICADO</option>
                      <option value="RASCUNHO">RASCUNHO</option>
                    </>
                  )}
                </select>
              </label>
            </div>

            {(publicacoesDoCurso ?? []).length === 0 ? (
              <p>Nenhuma publicação encontrada para os filtros. {minhasPublicacoes.length === 0 ? 'Você ainda não possui plano publicado/enviado aqui.' : ''}</p>
            ) : (
              <div className="curso-detail__list">
                {publicacoesDoCurso.map((pub) => (
                  <div key={pub.id} className="curso-detail__list-item curso-detail__bank-row">
                    <div>
                      <strong>Publicação #{pub.id}</strong>
                      <small>Autor: {pub.autor_nome || `#${pub.autor}`}</small>
                      <small>Status: {pub.status}</small>
                    </div>
                    {isTutorOrAdmin && (
                      <div className="curso-detail__bank-actions">
                        <Button size="sm" variant="outline" onClick={() => updateBancoPlano.mutate({ id: pub.id, status: 'APROVADO' })}>
                          Aprovar
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => updateBancoPlano.mutate({ id: pub.id, status: 'PUBLICADO' })}>
                          Publicar
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <aside className="curso-detail__side">
          <Card className="curso-detail__panel">
            <h3>Cronograma</h3>
            <ol className="curso-detail__timeline">
              {curso.cronograma.map((item) => (
                <li key={item.id}>
                  <strong>{item.semana || `Etapa ${item.ordem}`}</strong>
                  <span>{item.titulo}</span>
                  {item.descricao && <p>{item.descricao}</p>}
                </li>
              ))}
            </ol>
          </Card>

          <Card className="curso-detail__panel">
            <div className="curso-detail__plan-header">
              <h3>Plano de Aula</h3>
              <Button size="sm" variant="ghost" onClick={() => beginEditPlano()}>
                Novo rascunho
              </Button>
            </div>
            <div className="curso-detail__my-plans">
              {(planos ?? []).map((plano) => (
                <button key={plano.id} type="button" onClick={() => beginEditPlano(plano.id)} className={editingPlanoId === plano.id ? 'is-active' : ''}>
                  <span>{plano.titulo || `Plano #${plano.id}`}</span>
                  <small>{plano.status}</small>
                </button>
              ))}
            </div>

            <form className="curso-detail__plan-form" onSubmit={handleSubmitPlano}>
              <label>
                <span>Título do plano</span>
                <input value={planoTitulo} onChange={(e) => setPlanoTitulo(e.target.value)} placeholder="Plano de aula - frações" />
              </label>
              {PLANO_FIELDS.map(([key, label]) => (
                <label key={key}>
                  <span>{label}</span>
                  <textarea
                    rows={key === 'metodologia' || key === 'avaliacao' ? 4 : 2}
                    value={fieldValues[key] ?? ''}
                    onChange={(e) => setFieldValues((prev) => ({ ...prev, [key]: e.target.value }))}
                  />
                </label>
              ))}
              <label className="curso-detail__checkbox">
                <input
                  type="checkbox"
                  checked={compartilharBanco}
                  onChange={(e) => setCompartilharBanco(e.target.checked)}
                />
                Compartilhar no banco colaborativo ao enviar
              </label>
              <div className="curso-detail__form-actions">
                <Button type="submit" variant="outline" disabled={criarPlano.isPending || atualizarPlano.isPending}>
                  {editingPlanoId ? 'Salvar rascunho' : 'Criar rascunho'}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!editingPlanoId || enviarPlano.isPending}
                  onClick={handleEnviarPlano}
                >
                  {enviarPlano.isPending ? 'Enviando...' : 'Enviar produção'}
                </Button>
              </div>
              {feedback && <p className="curso-detail__feedback">{feedback}</p>}
            </form>
          </Card>
        </aside>
      </section>
    </div>
  );
}
