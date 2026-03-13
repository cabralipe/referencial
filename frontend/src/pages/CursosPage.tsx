import { Link } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCursos } from '@/hooks/useCourses';
import { useAuth } from '@/context/AuthContext';
import { buildBackendUrl } from '@/config/env';

import './CursosPage.css';

export function CursosPage() {
  const { data: cursos, isLoading } = useCursos();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin_cliente' || user?.role === 'super_admin';
  const avaHref = buildBackendUrl('/ava/');

  if (isLoading) {
    return <FullPageLoader message="Carregando cursos..." />;
  }

  return (
    <div className="cursos-page">
      <PageHeader
        title="Módulos PROLUC"
        description="Referencial Curricular e Implementação do PPP na Prática Pedagógica"
        actions={(
          <>
            <a
              className="cursos-page__header-link"
              href={avaHref}
              target="_blank"
              rel="noopener noreferrer"
            >
              Acessar AVA
            </a>
            {isAdmin ? (
              <Link className="cursos-page__header-link" to="/admin/cursos">
                Configuracao dos Cursos
              </Link>
            ) : null}
          </>
        )}
      />

      <div className="cursos-page__hero">
        <div>
          <h2>Produção orientada, trilhas e certificação em um só fluxo</h2>
          <p>
            Acompanhe avisos, cronograma, progresso, atividades por módulo e a produção do Plano de Aula com envio e banco colaborativo.
          </p>
        </div>
      </div>

      <div className="cursos-page__grid">
        {(cursos ?? []).map((curso) => (
          <Card key={curso.id} className="cursos-page__card">
            <div className="cursos-page__card-head">
              <span className={`cursos-page__badge ${curso.publicado ? 'is-published' : 'is-draft'}`}>
                {curso.publicado ? 'Publicado' : 'Rascunho'}
              </span>
              {typeof curso.carga_horaria_total === 'number' && <small>{curso.carga_horaria_total}h</small>}
            </div>
            <h3>{curso.nome}</h3>
            <p>{curso.descricao || 'Curso sem descrição.'}</p>
            <div className="cursos-page__actions">
              <Link to={`/cursos/${curso.id}`}>Abrir curso</Link>
              {isAdmin && <Link to={`/admin/cursos?curso=${curso.id}`}>Editar</Link>}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

