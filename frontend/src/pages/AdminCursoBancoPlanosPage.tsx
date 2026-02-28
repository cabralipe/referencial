import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useBancoPlanos, useCurso, usePlanosAula, useUpdateBancoPlano } from '@/hooks/useCourses';

import './AdminCursoBancoPlanosPage.css';

export function AdminCursoBancoPlanosPage() {
  const { id } = useParams();
  const cursoId = id ? Number(id) : undefined;
  const [componente, setComponente] = useState('');
  const [etapa, setEtapa] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('ENVIADO');

  const { data: curso, isLoading: cursoLoading } = useCurso(id);
  const { data: planos, isLoading: planosLoading } = usePlanosAula(cursoId);
  const { data: publicacoes, isLoading: pubsLoading } = useBancoPlanos({
    componente: componente || undefined,
    etapaModalidade: etapa || undefined,
    status: statusFiltro || undefined,
  });
  const updateBancoPlano = useUpdateBancoPlano();

  const planoIdsDoCurso = useMemo(() => new Set((planos ?? []).map((p) => p.id)), [planos]);
  const rows = useMemo(
    () => (publicacoes ?? []).filter((pub) => planoIdsDoCurso.has(pub.resposta_formulario_id)),
    [publicacoes, planoIdsDoCurso],
  );

  if (cursoLoading || planosLoading || pubsLoading) {
    return <FullPageLoader message="Carregando moderação do banco de planos..." />;
  }

  return (
    <div className="admin-curso-banco">
      <PageHeader
        title={`Banco de Planos · ${curso?.nome ?? 'Curso'}`}
        description="Moderação em lote das publicações de plano de aula do curso."
        actions={<Link className="admin-curso-banco__back" to={`/admin/cursos?curso=${id}`}>Voltar ao admin do curso</Link>}
      />

      <Card>
        <div className="admin-curso-banco__filters">
          <label>
            <span>Componente</span>
            <input value={componente} onChange={(e) => setComponente(e.target.value)} placeholder="Matemática" />
          </label>
          <label>
            <span>Etapa/Modalidade</span>
            <input value={etapa} onChange={(e) => setEtapa(e.target.value)} placeholder="Anos Finais" />
          </label>
          <label>
            <span>Status</span>
            <select value={statusFiltro} onChange={(e) => setStatusFiltro(e.target.value)}>
              <option value="">Todos</option>
              <option value="ENVIADO">Enviado</option>
              <option value="APROVADO">Aprovado</option>
              <option value="PUBLICADO">Publicado</option>
              <option value="RASCUNHO">Rascunho</option>
            </select>
          </label>
        </div>
      </Card>

      <div className="admin-curso-banco__list">
        {rows.length === 0 && (
          <Card>
            <p>Nenhuma publicação encontrada para os filtros aplicados.</p>
          </Card>
        )}

        {rows.map((pub) => (
          <Card key={pub.id}>
            <div className="admin-curso-banco__row">
              <div className="admin-curso-banco__meta">
                <h3>Publicação #{pub.id}</h3>
                <p>
                  Autor: {pub.autor_nome || `#${pub.autor}`} · Status: <strong>{pub.status}</strong>
                </p>
                <small>Atualizado em {new Date(pub.updated_at).toLocaleString('pt-BR')}</small>
              </div>

              <div className="admin-curso-banco__actions">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={updateBancoPlano.isPending}
                  onClick={() => updateBancoPlano.mutate({ id: pub.id, status: 'APROVADO' })}
                >
                  Aprovar
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={updateBancoPlano.isPending}
                  onClick={() => updateBancoPlano.mutate({ id: pub.id, status: 'PUBLICADO' })}
                >
                  Publicar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={updateBancoPlano.isPending}
                  onClick={() => updateBancoPlano.mutate({ id: pub.id, status: 'ENVIADO' })}
                >
                  Retornar p/ Enviado
                </Button>
              </div>
            </div>

            <div className="admin-curso-banco__payload">
              {Object.entries(pub.payload_json ?? {}).slice(0, 6).map(([key, value]) => (
                <div key={key} className="admin-curso-banco__payload-item">
                  <strong>{key}</strong>
                  <span>{String(value || '').slice(0, 180) || '—'}</span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

