import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { useCreateCurso, useCurso, useCursos, useUpdateCurso } from '@/hooks/useCourses';

import './AdminCursosPage.css';

const DEFAULT_STRUCTURE = {
  avisos: [],
  cronograma: [],
  modulos: [
    { titulo: 'Apresentação', ordem: 1, tipo: 'APRESENTACAO', itens: [] },
    { titulo: 'Módulo 1', ordem: 2, tipo: 'MODULO', itens: [] },
    { titulo: 'Módulo 2', ordem: 3, tipo: 'MODULO', itens: [] },
    { titulo: 'Módulo 3', ordem: 4, tipo: 'MODULO', itens: [] },
    { titulo: 'Módulo 4', ordem: 5, tipo: 'MODULO', itens: [] },
    { titulo: 'Módulo 5', ordem: 6, tipo: 'MODULO', itens: [] },
    { titulo: 'Módulo 6', ordem: 7, tipo: 'MODULO', itens: [] },
    { titulo: 'Banco de Planos', ordem: 8, tipo: 'BANCO_PLANOS', itens: [] },
    { titulo: 'Fórum Geral', ordem: 9, tipo: 'FORUM_GERAL', itens: [] },
    { titulo: 'Biblioteca', ordem: 10, tipo: 'BIBLIOTECA', itens: [] },
    { titulo: 'Entrega Final', ordem: 11, tipo: 'ENTREGA_FINAL', itens: [] },
  ],
};

type EditableCursoItem = {
  id?: number;
  ordem: number;
  tipo: string;
  titulo: string;
  payload_json: Record<string, unknown>;
};

type EditableCursoModulo = {
  id?: number;
  titulo: string;
  ordem: number;
  tipo: string;
  itens: EditableCursoItem[];
};

type EditableAviso = {
  id?: number;
  titulo: string;
  corpo: string;
  publicado_em?: string | null;
};

type EditableCronograma = {
  id?: number;
  semana: string;
  titulo: string;
  descricao: string;
  ordem: number;
};

export function AdminCursosPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedId = searchParams.get('curso');
  const { data: cursos, isLoading } = useCursos();
  const { data: cursoDetail, isLoading: loadingDetail } = useCurso(selectedId ?? undefined);
  const createCurso = useCreateCurso();
  const updateCurso = useUpdateCurso();

  const [nome, setNome] = useState('Curso: Referencial Curricular e Implementação do PPP na Prática Pedagógica');
  const [descricao, setDescricao] = useState('Página inicial do curso com avisos, cronograma, progresso e produção orientada.');
  const [objetivos, setObjetivos] = useState('Fortalecer a implementação do referencial e do PPP na prática pedagógica.');
  const [publicado, setPublicado] = useState(false);
  const [cargaTotal, setCargaTotal] = useState(60);
  const [cargaPresencial, setCargaPresencial] = useState(8);
  const [cargaSincrona, setCargaSincrona] = useState(14);
  const [cargaProducao, setCargaProducao] = useState(38);
  const [regrasJson, setRegrasJson] = useState(
    JSON.stringify(
      {
        presenca_presencial_obrigatoria: true,
        min_sincronos: 4,
        min_planos: 1,
        entrega_final_obrigatoria: true,
        compartilhar_banco_obrigatorio: true,
      },
      null,
      2,
    ),
  );
  const [estruturaJson, setEstruturaJson] = useState(JSON.stringify(DEFAULT_STRUCTURE, null, 2));
  const [modulosEditor, setModulosEditor] = useState<EditableCursoModulo[]>(DEFAULT_STRUCTURE.modulos as EditableCursoModulo[]);
  const [avisosEditor, setAvisosEditor] = useState<EditableAviso[]>([]);
  const [cronogramaEditor, setCronogramaEditor] = useState<EditableCronograma[]>([]);
  const [advancedJsonMode, setAdvancedJsonMode] = useState(false);
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    if (!cursoDetail) return;
    setNome(cursoDetail.nome);
    setDescricao(cursoDetail.descricao ?? '');
    setObjetivos(cursoDetail.objetivos ?? '');
    setPublicado(Boolean(cursoDetail.publicado));
    setCargaTotal(cursoDetail.carga_horaria_total ?? 60);
    setCargaPresencial(cursoDetail.carga_presencial ?? 8);
    setCargaSincrona(cursoDetail.carga_sincrona ?? 14);
    setCargaProducao(cursoDetail.carga_producao ?? 38);
    setRegrasJson(JSON.stringify(cursoDetail.regras_certificacao ?? {}, null, 2));
    const avisos = (cursoDetail.avisos ?? []).map((a) => ({
      id: a.id,
      titulo: a.titulo,
      corpo: a.corpo,
      publicado_em: a.publicado_em,
    }));
    const cronograma = (cursoDetail.cronograma ?? []).map((c) => ({
      id: c.id,
      semana: c.semana ?? '',
      titulo: c.titulo,
      descricao: c.descricao ?? '',
      ordem: c.ordem,
    }));
    const modulos = (cursoDetail.modulos ?? []).map((m) => ({
      id: m.id,
      titulo: m.titulo,
      ordem: m.ordem,
      tipo: m.tipo,
      itens: (m.itens ?? []).map((i) => ({
        id: i.id,
        ordem: i.ordem,
        tipo: i.tipo,
        titulo: i.titulo,
        payload_json: i.payload_json ?? {},
      })),
    }));
    setAvisosEditor(avisos);
    setCronogramaEditor(cronograma);
    setModulosEditor(modulos);
    setEstruturaJson(
      JSON.stringify(
        {
          avisos,
          cronograma,
          modulos,
        },
        null,
        2,
      ),
    );
  }, [cursoDetail]);

  useEffect(() => {
    if (advancedJsonMode) return;
    setEstruturaJson(
      JSON.stringify(
        {
          avisos: avisosEditor,
          cronograma: cronogramaEditor,
          modulos: modulosEditor,
        },
        null,
        2,
      ),
    );
  }, [advancedJsonMode, avisosEditor, cronogramaEditor, modulosEditor]);

  const cursoOptions = useMemo(() => cursos ?? [], [cursos]);

  const handleSave = async (event: FormEvent) => {
    event.preventDefault();
    setFeedback('');
    try {
      const regras = JSON.parse(regrasJson || '{}');
      const estrutura = advancedJsonMode
        ? JSON.parse(estruturaJson || '{}')
        : { avisos: avisosEditor, cronograma: cronogramaEditor, modulos: modulosEditor };
      const payload = {
        nome,
        categoria: 'avamec',
        descricao,
        objetivos,
        publicado,
        carga_horaria_total: Number(cargaTotal),
        carga_presencial: Number(cargaPresencial),
        carga_sincrona: Number(cargaSincrona),
        carga_producao: Number(cargaProducao),
        regras_certificacao_json: regras,
        avisos: Array.isArray(estrutura.avisos) ? estrutura.avisos : [],
        cronograma: Array.isArray(estrutura.cronograma) ? estrutura.cronograma : [],
        modulos: Array.isArray(estrutura.modulos) ? estrutura.modulos : [],
      };
      if (selectedId) {
        await updateCurso.mutateAsync({ cursoId: Number(selectedId), payload });
        setFeedback('Curso atualizado.');
      } else {
        const created = await createCurso.mutateAsync(payload);
        setFeedback('Curso criado.');
        setSearchParams({ curso: String(created.id) });
      }
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Falha ao salvar curso.');
    }
  };

  const addModulo = () => {
    setModulosEditor((prev) => [
      ...prev,
      {
        titulo: `Novo módulo ${prev.length + 1}`,
        ordem: prev.length + 1,
        tipo: 'MODULO',
        itens: [],
      },
    ]);
  };

  const normalizeOrders = (mods: EditableCursoModulo[]) =>
    mods.map((m, idx) => ({
      ...m,
      ordem: idx + 1,
      itens: (m.itens ?? []).map((item, jdx) => ({ ...item, ordem: jdx + 1 })),
    }));

  const handleToggleAdvancedMode = () => {
    if (advancedJsonMode) {
      try {
        const parsed = JSON.parse(estruturaJson || '{}');
        setAvisosEditor(Array.isArray(parsed.avisos) ? parsed.avisos : []);
        setCronogramaEditor(Array.isArray(parsed.cronograma) ? parsed.cronograma : []);
        setModulosEditor(Array.isArray(parsed.modulos) ? normalizeOrders(parsed.modulos as EditableCursoModulo[]) : []);
        setFeedback('Estrutura JSON aplicada ao editor visual.');
      } catch (error) {
        setFeedback('JSON inválido: corrija antes de voltar ao editor visual.');
        return;
      }
    }
    setAdvancedJsonMode((v) => !v);
  };

  if (isLoading || (selectedId && loadingDetail)) {
    return <FullPageLoader message="Carregando admin de cursos..." />;
  }

  return (
    <div className="admin-cursos">
      <PageHeader
        title="Admin · Cursos (AVAMEC)"
        description="Configure a camada wrapper do curso sem alterar o PPP. Editor visual para módulos/itens + modo JSON avançado."
        actions={
          selectedId ? (
            <Link className="admin-cursos__moderation-link" to={`/admin/cursos/${selectedId}/banco-planos`}>
              Moderar Banco de Planos
            </Link>
          ) : undefined
        }
      />

      <div className="admin-cursos__grid">
        <Card className="admin-cursos__sidebar">
          <div className="admin-cursos__sidebar-head">
            <h3>Cursos</h3>
            <Button size="sm" variant="ghost" onClick={() => setSearchParams({})}>Novo</Button>
          </div>
          <div className="admin-cursos__list">
            {cursoOptions.map((curso) => (
              <button
                key={curso.id}
                type="button"
                className={selectedId === String(curso.id) ? 'is-active' : ''}
                onClick={() => setSearchParams({ curso: String(curso.id) })}
              >
                <span>{curso.nome}</span>
                <small>{curso.publicado ? 'Publicado' : 'Rascunho'}</small>
              </button>
            ))}
          </div>
        </Card>

        <Card>
          <form className="admin-cursos__form" onSubmit={handleSave}>
            <div className="admin-cursos__two-col">
              <label>
                <span>Nome</span>
                <input value={nome} onChange={(e) => setNome(e.target.value)} required />
              </label>
              <label className="checkbox">
                <input type="checkbox" checked={publicado} onChange={(e) => setPublicado(e.target.checked)} />
                Publicado
              </label>
            </div>

            <label>
              <span>Descrição</span>
              <textarea rows={3} value={descricao} onChange={(e) => setDescricao(e.target.value)} />
            </label>

            <label>
              <span>Objetivos</span>
              <textarea rows={4} value={objetivos} onChange={(e) => setObjetivos(e.target.value)} />
            </label>

            <div className="admin-cursos__hours">
              <label><span>CH Total</span><input type="number" value={cargaTotal} onChange={(e) => setCargaTotal(Number(e.target.value))} /></label>
              <label><span>Presencial</span><input type="number" value={cargaPresencial} onChange={(e) => setCargaPresencial(Number(e.target.value))} /></label>
              <label><span>Síncrona</span><input type="number" value={cargaSincrona} onChange={(e) => setCargaSincrona(Number(e.target.value))} /></label>
              <label><span>Produção</span><input type="number" value={cargaProducao} onChange={(e) => setCargaProducao(Number(e.target.value))} /></label>
            </div>

            <label>
              <span>Regras de certificação (JSON)</span>
              <textarea rows={8} value={regrasJson} onChange={(e) => setRegrasJson(e.target.value)} spellCheck={false} />
            </label>

            <div className="admin-cursos__builder">
              <div className="admin-cursos__builder-head">
                <h3>Editor visual de estrutura</h3>
                <div className="admin-cursos__builder-actions">
                  <Button type="button" size="sm" variant="ghost" onClick={handleToggleAdvancedMode}>
                    {advancedJsonMode ? 'Voltar ao visual' : 'Modo JSON avançado'}
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={addModulo}>
                    Adicionar módulo
                  </Button>
                </div>
              </div>

              <div className="admin-cursos__subsection">
                <h4>Avisos</h4>
                <div className="admin-cursos__stack">
                  {avisosEditor.map((aviso, index) => (
                    <div key={`aviso-${index}`} className="admin-cursos__nested-card">
                      <div className="admin-cursos__inline-grid">
                        <label>
                          <span>Título</span>
                          <input
                            value={aviso.titulo}
                            onChange={(e) =>
                              setAvisosEditor((prev) =>
                                prev.map((item, i) => (i === index ? { ...item, titulo: e.target.value } : item)),
                              )
                            }
                          />
                        </label>
                        <label>
                          <span>Publicado em (ISO, opcional)</span>
                          <input
                            value={aviso.publicado_em ?? ''}
                            onChange={(e) =>
                              setAvisosEditor((prev) =>
                                prev.map((item, i) => (i === index ? { ...item, publicado_em: e.target.value || null } : item)),
                              )
                            }
                          />
                        </label>
                      </div>
                      <label>
                        <span>Corpo</span>
                        <textarea
                          rows={3}
                          value={aviso.corpo}
                          onChange={(e) =>
                            setAvisosEditor((prev) =>
                              prev.map((item, i) => (i === index ? { ...item, corpo: e.target.value } : item)),
                            )
                          }
                        />
                      </label>
                      <div className="admin-cursos__nested-actions">
                        <Button type="button" size="sm" variant="ghost" onClick={() => setAvisosEditor((prev) => prev.filter((_, i) => i !== index))}>
                          Remover aviso
                        </Button>
                      </div>
                    </div>
                  ))}
                  <Button type="button" size="sm" variant="outline" onClick={() => setAvisosEditor((prev) => [...prev, { titulo: 'Novo aviso', corpo: '', publicado_em: null }])}>
                    Adicionar aviso
                  </Button>
                </div>
              </div>

              <div className="admin-cursos__subsection">
                <h4>Cronograma</h4>
                <div className="admin-cursos__stack">
                  {cronogramaEditor.map((item, index) => (
                    <div key={`cron-${index}`} className="admin-cursos__nested-card">
                      <div className="admin-cursos__inline-grid admin-cursos__inline-grid--3">
                        <label>
                          <span>Semana</span>
                          <input value={item.semana} onChange={(e) => setCronogramaEditor((prev) => prev.map((x, i) => (i === index ? { ...x, semana: e.target.value } : x)))} />
                        </label>
                        <label>
                          <span>Título</span>
                          <input value={item.titulo} onChange={(e) => setCronogramaEditor((prev) => prev.map((x, i) => (i === index ? { ...x, titulo: e.target.value } : x)))} />
                        </label>
                        <label>
                          <span>Ordem</span>
                          <input type="number" value={item.ordem} onChange={(e) => setCronogramaEditor((prev) => prev.map((x, i) => (i === index ? { ...x, ordem: Number(e.target.value) || 0 } : x)))} />
                        </label>
                      </div>
                      <label>
                        <span>Descrição</span>
                        <textarea rows={2} value={item.descricao} onChange={(e) => setCronogramaEditor((prev) => prev.map((x, i) => (i === index ? { ...x, descricao: e.target.value } : x)))} />
                      </label>
                      <div className="admin-cursos__nested-actions">
                        <Button type="button" size="sm" variant="ghost" onClick={() => setCronogramaEditor((prev) => prev.filter((_, i) => i !== index))}>
                          Remover item
                        </Button>
                      </div>
                    </div>
                  ))}
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setCronogramaEditor((prev) => [...prev, { semana: '', titulo: 'Novo item', descricao: '', ordem: prev.length + 1 }])}
                  >
                    Adicionar item do cronograma
                  </Button>
                </div>
              </div>

              <div className="admin-cursos__subsection">
                <h4>Módulos e itens</h4>
                <div className="admin-cursos__stack">
                  {modulosEditor.map((modulo, moduloIndex) => (
                    <div key={`mod-${moduloIndex}`} className="admin-cursos__module-card">
                      <div className="admin-cursos__inline-grid admin-cursos__inline-grid--3">
                        <label>
                          <span>Título do módulo</span>
                          <input
                            value={modulo.titulo}
                            onChange={(e) =>
                              setModulosEditor((prev) =>
                                prev.map((m, i) => (i === moduloIndex ? { ...m, titulo: e.target.value } : m)),
                              )
                            }
                          />
                        </label>
                        <label>
                          <span>Ordem</span>
                          <input
                            type="number"
                            value={modulo.ordem}
                            onChange={(e) =>
                              setModulosEditor((prev) =>
                                prev.map((m, i) => (i === moduloIndex ? { ...m, ordem: Number(e.target.value) || 0 } : m)),
                              )
                            }
                          />
                        </label>
                        <label>
                          <span>Tipo</span>
                          <select
                            value={modulo.tipo}
                            onChange={(e) =>
                              setModulosEditor((prev) =>
                                prev.map((m, i) => (i === moduloIndex ? { ...m, tipo: e.target.value } : m)),
                              )
                            }
                          >
                            {['APRESENTACAO', 'MODULO', 'BANCO_PLANOS', 'FORUM_GERAL', 'BIBLIOTECA', 'ENTREGA_FINAL'].map((tipo) => (
                              <option key={tipo} value={tipo}>{tipo}</option>
                            ))}
                          </select>
                        </label>
                      </div>

                      <div className="admin-cursos__nested-actions">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            setModulosEditor((prev) => normalizeOrders(prev.filter((_, i) => i !== moduloIndex)))
                          }
                        >
                          Remover módulo
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setModulosEditor((prev) =>
                              prev.map((m, i) =>
                                i === moduloIndex
                                  ? {
                                      ...m,
                                      itens: [
                                        ...m.itens,
                                        {
                                          ordem: (m.itens?.length ?? 0) + 1,
                                          tipo: 'TEXTO',
                                          titulo: `Novo item ${(m.itens?.length ?? 0) + 1}`,
                                          payload_json: {},
                                        },
                                      ],
                                    }
                                  : m,
                              ),
                            )
                          }
                        >
                          Adicionar item
                        </Button>
                      </div>

                      <div className="admin-cursos__items">
                        {(modulo.itens ?? []).map((item, itemIndex) => (
                          <div key={`item-${moduloIndex}-${itemIndex}`} className="admin-cursos__nested-card">
                            <div className="admin-cursos__inline-grid admin-cursos__inline-grid--4">
                              <label>
                                <span>Título</span>
                                <input
                                  value={item.titulo}
                                  onChange={(e) =>
                                    setModulosEditor((prev) =>
                                      prev.map((m, mi) =>
                                        mi === moduloIndex
                                          ? {
                                              ...m,
                                              itens: m.itens.map((it, ii) => (ii === itemIndex ? { ...it, titulo: e.target.value } : it)),
                                            }
                                          : m,
                                      ),
                                    )
                                  }
                                />
                              </label>
                              <label>
                                <span>Tipo</span>
                                <select
                                  value={item.tipo}
                                  onChange={(e) =>
                                    setModulosEditor((prev) =>
                                      prev.map((m, mi) =>
                                        mi === moduloIndex
                                          ? {
                                              ...m,
                                              itens: m.itens.map((it, ii) => (ii === itemIndex ? { ...it, tipo: e.target.value } : it)),
                                            }
                                          : m,
                                      ),
                                    )
                                  }
                                >
                                  {['VIDEO', 'TEXTO', 'CADERNO', 'TAREFA', 'FORUM', 'FORMULARIO', 'CHECKLIST'].map((tipo) => (
                                    <option key={tipo} value={tipo}>{tipo}</option>
                                  ))}
                                </select>
                              </label>
                              <label>
                                <span>Ordem</span>
                                <input
                                  type="number"
                                  value={item.ordem}
                                  onChange={(e) =>
                                    setModulosEditor((prev) =>
                                      prev.map((m, mi) =>
                                        mi === moduloIndex
                                          ? {
                                              ...m,
                                              itens: m.itens.map((it, ii) => (ii === itemIndex ? { ...it, ordem: Number(e.target.value) || 0 } : it)),
                                            }
                                          : m,
                                      ),
                                    )
                                  }
                                />
                              </label>
                              <label>
                                <span>Payload (JSON)</span>
                                <input
                                  value={JSON.stringify(item.payload_json ?? {})}
                                  onChange={(e) => {
                                    const next = e.target.value;
                                    setModulosEditor((prev) =>
                                      prev.map((m, mi) =>
                                        mi === moduloIndex
                                          ? {
                                              ...m,
                                              itens: m.itens.map((it, ii) => {
                                                if (ii !== itemIndex) return it;
                                                try {
                                                  return { ...it, payload_json: JSON.parse(next || '{}') };
                                                } catch {
                                                  return { ...it };
                                                }
                                              }),
                                            }
                                          : m,
                                      ),
                                    );
                                  }}
                                />
                              </label>
                            </div>
                            <div className="admin-cursos__nested-actions">
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                onClick={() =>
                                  setModulosEditor((prev) =>
                                    prev.map((m, mi) =>
                                      mi === moduloIndex ? { ...m, itens: m.itens.filter((_, ii) => ii !== itemIndex).map((it, idx) => ({ ...it, ordem: idx + 1 })) } : m,
                                    ),
                                  )
                                }
                              >
                                Remover item
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {advancedJsonMode && (
              <label>
                <span>Estrutura do curso (JSON: avisos, cronograma, modulos/itens)</span>
                <textarea rows={20} value={estruturaJson} onChange={(e) => setEstruturaJson(e.target.value)} spellCheck={false} />
              </label>
            )}

            <div className="admin-cursos__actions">
              <Button type="submit" variant="secondary" disabled={createCurso.isPending || updateCurso.isPending}>
                {selectedId ? (updateCurso.isPending ? 'Salvando...' : 'Salvar curso') : (createCurso.isPending ? 'Criando...' : 'Criar curso')}
              </Button>
            </div>

            {feedback && <p className="admin-cursos__feedback">{feedback}</p>}
          </form>
        </Card>
      </div>
    </div>
  );
}
