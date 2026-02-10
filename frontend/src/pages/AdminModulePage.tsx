import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';

import { useApiClient } from '@/api/client';
import { Card } from '@/components/common/Card';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageHeader } from '@/components/common/PageHeader';
import { useAdminScope } from '@/hooks/useAdminScope';
import { useAuth } from '@/context/AuthContext';
import { ADMIN_MODULES } from './adminModules';

import './AdminModulePage.css';

type AnyRecord = Record<string, unknown>;

const READ_ONLY_FIELDS = new Set([
  'id',
  'created_at',
  'updated_at',
  'last_login',
  'date_joined',
  'etag',
]);

const TEXTAREA_FIELDS = [
  'descricao',
  'conteudo',
  'conteudo_html',
  'parecer_html',
  'diff_json',
  'anchor_json',
  'rodape_html',
  'cabecalho_html',
];

function inferInputType(value: unknown, field: string) {
  if (TEXTAREA_FIELDS.some((name) => field.includes(name))) return 'textarea';
  if (typeof value === 'boolean') return 'checkbox';
  if (typeof value === 'number') return 'number';
  if (field.toLowerCase().includes('email')) return 'email';
  if (field.toLowerCase().includes('url')) return 'url';
  return 'text';
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function parseValue(value: string, template: unknown, field: string) {
  if (template === null || template === undefined) return value;
  if (typeof template === 'number') return Number(value);
  if (typeof template === 'boolean') return value === 'true' || value === '1';
  if (Array.isArray(template)) return value.split(',').map((item) => item.trim()).filter(Boolean);
  if (typeof template === 'object') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  if (field.endsWith('_id') || field === 'id' || field === 'cliente' || field === 'usuario') {
    const numeric = Number(value);
    return Number.isNaN(numeric) ? value : numeric;
  }
  return value;
}

export function AdminModulePage() {
  const { moduleId = '' } = useParams();
  const module = ADMIN_MODULES.find((entry) => entry.id === moduleId);
  const client = useApiClient();
  const { user } = useAuth();
  const { headers, isSuperAdmin, clientes, selectedClienteId, setSelectedClienteId } = useAdminScope();
  const [searchParams] = useSearchParams();

  const [rows, setRows] = useState<AnyRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [activeQuickFilter, setActiveQuickFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'simple' | 'advanced'>(() => module?.defaultView ?? 'simple');
  const [autoOpened, setAutoOpened] = useState(false);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editing, setEditing] = useState<AnyRecord | null>(null);
  const [formData, setFormData] = useState<AnyRecord>({});
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonDraft, setJsonDraft] = useState('');
  const [formError, setFormError] = useState('');

  const load = useCallback(async () => {
    if (!module) return;
    setLoading(true);
    setError('');
    try {
      const response = await client.get<any>(module.endpoint, {
        query: { page, page_size: pageSize },
        headers,
      });
      const payload = response.data;
      const list = Array.isArray(payload) ? payload : payload?.results ?? [];
      setRows(list);
    } catch (err: any) {
      setError(err?.message ?? 'Não foi possível carregar dados.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [client, headers, module, page, pageSize]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!module) return;
    setViewMode(module.defaultView ?? 'simple');
    setAutoOpened(false);
    setActiveQuickFilter('all');
  }, [module]);

  useEffect(() => {
    if (viewMode === 'simple') {
      setJsonMode(false);
    }
  }, [viewMode]);

  useEffect(() => {
    const quickFilter = searchParams.get('filter');
    if (quickFilter) {
      setActiveQuickFilter(quickFilter);
    }
    const shouldOpen = searchParams.get('new');
    if (shouldOpen === '1' && module && !autoOpened) {
      openCreate();
      setAutoOpened(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, module, autoOpened]);

  if (!module) {
    return (
      <div className="admin-module">
        <PageHeader title="Módulo não encontrado" description="Escolha um módulo válido no Admin Console." />
        <Card>
          <Link to="/admin/console">Voltar ao Admin Console</Link>
        </Card>
      </div>
    );
  }

  const filteredRows = useMemo(() => {
    let nextRows = rows;
    if (module?.quickFilters && activeQuickFilter !== 'all') {
      const match = module.quickFilters.find((filter) => filter.id === activeQuickFilter);
      if (match) {
        nextRows = nextRows.filter((row) => {
          const value = row[match.field];
          if (match.operator === 'truthy') return Boolean(value);
          if (match.operator === 'falsy') return !value;
          if (match.operator === 'not_equals') return String(value) !== String(match.value ?? '');
          return String(value) === String(match.value ?? '');
        });
      }
    }
    const term = search.trim().toLowerCase();
    if (!term) return nextRows;
    return nextRows.filter((row) =>
      Object.values(row).some((value) => String(value ?? '').toLowerCase().includes(term)),
    );
  }, [activeQuickFilter, module?.quickFilters, rows, search]);

  const columns = useMemo(() => {
    const keys = new Set<string>();
    rows.forEach((row) => Object.keys(row).forEach((key) => keys.add(key)));
    const allColumns = Array.from(keys);
    if (viewMode === 'simple' && module?.essentialColumns?.length) {
      const essential = module.essentialColumns.filter((col) => allColumns.includes(col));
      return essential.length ? essential : allColumns;
    }
    return allColumns;
  }, [module?.essentialColumns, rows, viewMode]);

  const openCreate = () => {
    setEditing(null);
    const base = rows[0]
      ? Object.keys(rows[0]).reduce<AnyRecord>((acc, key) => {
        if (!READ_ONLY_FIELDS.has(key)) acc[key] = '';
        return acc;
      }, {})
      : (module?.essentialFields ?? []).reduce<AnyRecord>((acc, key) => {
        acc[key] = '';
        return acc;
      }, {});
    const scopedClienteId = selectedClienteId || user?.clienteId || '';
    if ((base as AnyRecord).cliente !== undefined && scopedClienteId) {
      base.cliente = scopedClienteId;
    }
    if (module.id === 'usuarios') {
      base.password = '';
    }
    setFormData(base);
    setJsonDraft(JSON.stringify(base, null, 2));
    setFormError('');
    setIsFormOpen(true);
  };

  const openEdit = (row: AnyRecord) => {
    setEditing(row);
    const editable = Object.keys(row).reduce<AnyRecord>((acc, key) => {
      if (!READ_ONLY_FIELDS.has(key)) acc[key] = row[key];
      return acc;
    }, {});
    if (module.id === 'usuarios') {
      editable.password = '';
    }
    setFormData(editable);
    setJsonDraft(JSON.stringify(editable, null, 2));
    setFormError('');
    setIsFormOpen(true);
  };

  const updateField = (key: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    setFormError('');
    try {
      const payload = jsonMode ? JSON.parse(jsonDraft) : formData;
      if (editing && editing.id) {
        await client.put(`${module.endpoint}/${editing.id}`, {
          body: payload,
          ifMatch: typeof editing.etag === 'string' ? editing.etag : undefined,
          headers,
        });
      } else {
        await client.post(module.endpoint, { body: payload, headers });
      }
      setIsFormOpen(false);
      await load();
    } catch (err: any) {
      setFormError(err?.message ?? 'Não foi possível salvar.');
    }
  };

  const handleDelete = async (row: AnyRecord) => {
    if (!row.id) return;
    const displayName = String(row.nome ?? row.titulo ?? row.email ?? row.id);
    if (!window.confirm(`Tem certeza? Isso pode afetar trilhas e tarefas.\nRegistro: ${displayName}`)) return;
    try {
      await client.del(`${module.endpoint}/${row.id}`, { headers });
      await load();
    } catch (err: any) {
      setError(err?.message ?? 'Não foi possível remover.');
    }
  };

  if (loading) {
    return <FullPageLoader message="Carregando dados do módulo..." />;
  }

  return (
    <div className={`admin-module admin-module--${module.id}`}>
      <PageHeader
        title={module.label}
        description={module.description}
        actions={(
          <div className="admin-module__actions">
            <Link to="/admin/console" className="admin-module__back">
              Voltar
            </Link>
            <button type="button" onClick={openCreate} className="admin-module__primary">
              Novo registro
            </button>
          </div>
        )}
      />

      <Card>
        <div className="admin-module__toolbar">
          <label>
            <span>Buscar</span>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Filtrar resultados"
            />
          </label>
          <label>
            <span>Página</span>
            <input
              type="number"
              min={1}
              value={page}
              onChange={(event) => setPage(Number(event.target.value) || 1)}
            />
          </label>
          <label>
            <span>Modo</span>
            <select value={viewMode} onChange={(event) => setViewMode(event.target.value as 'simple' | 'advanced')}>
              <option value="simple">Simples</option>
              <option value="advanced">Avançado</option>
            </select>
          </label>
          {isSuperAdmin && (
            <label>
              <span>Cliente</span>
              <select
                value={selectedClienteId === '' ? '' : String(selectedClienteId)}
                onChange={(event) => {
                  setSelectedClienteId(event.target.value ? Number(event.target.value) : '');
                  setPage(1);
                }}
              >
                <option value="">Todos</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nome}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {module.examples && (
          <div className="admin-module__examples">
            <strong>Exemplos:</strong> {module.examples.join(' · ')}
          </div>
        )}
        {module.quickFilters && module.quickFilters.length > 0 && (
          <div className="admin-module__quick-filters">
            <span>Filtros rápidos:</span>
            <button
              type="button"
              className={activeQuickFilter === 'all' ? 'is-active' : ''}
              onClick={() => setActiveQuickFilter('all')}
            >
              Todos
            </button>
            {module.quickFilters.map((filter) => (
              <button
                type="button"
                key={filter.id}
                className={activeQuickFilter === filter.id ? 'is-active' : ''}
                onClick={() => setActiveQuickFilter(filter.id)}
              >
                {filter.label}
              </button>
            ))}
          </div>
        )}
        {error && <p className="admin-module__error">{error}</p>}
        <div className="admin-module__table">
          <table>
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{module?.fieldLabels?.[col] ?? col}</th>
                ))}
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row) => (
                <tr key={String(row.id ?? Math.random())}>
                  {columns.map((col) => {
                    const label = module?.fieldLabels?.[col] ?? col;
                    return (
                      <td key={col} data-label={label}>
                        {typeof row[col] === 'object' && row[col] !== null ? JSON.stringify(row[col]) : String(row[col] ?? '')}
                      </td>
                    );
                  })}
                  <td className="admin-module__row-actions" data-label="Ações">
                    <button type="button" onClick={() => openEdit(row)}>
                      Editar
                    </button>
                    <button type="button" className="danger" onClick={() => handleDelete(row)}>
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
              {filteredRows.length === 0 && (
                <tr>
                  <td colSpan={columns.length + 1}>Nenhum registro encontrado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {isFormOpen && (
        <div className="admin-module__drawer">
          <div className="admin-module__drawer-content">
            <header>
              <h3>{editing ? 'Editar registro' : 'Novo registro'}</h3>
              <button type="button" onClick={() => setIsFormOpen(false)}>
                Fechar
              </button>
            </header>

            {viewMode === 'advanced' && (
              <div className="admin-module__mode">
                <label>
                  <input type="checkbox" checked={jsonMode} onChange={(event) => setJsonMode(event.target.checked)} />
                  Modo avançado (JSON)
                </label>
              </div>
            )}

            {jsonMode ? (
              <textarea
                className="admin-module__json"
                value={jsonDraft}
                onChange={(event) => setJsonDraft(event.target.value)}
                rows={16}
              />
            ) : (
              <div className="admin-module__form">
                {Object.keys(formData).length === 0 && (
                  <p className="admin-module__hint">
                    Sem campos detectados. Use o modo avançado (JSON) para criar o registro.
                  </p>
                )}
                {Object.entries(formData)
                  .filter(([key]) => {
                    if (READ_ONLY_FIELDS.has(key)) return false;
                    if (viewMode === 'simple' && module?.essentialFields?.length) {
                      return module.essentialFields.includes(key);
                    }
                    return true;
                  })
                  .sort(([a], [b]) => {
                    const order = module?.fieldOrder ?? module?.essentialFields ?? [];
                    if (!order.length) return 0;
                    const ai = order.indexOf(a);
                    const bi = order.indexOf(b);
                    if (ai === -1 && bi === -1) return 0;
                    if (ai === -1) return 1;
                    if (bi === -1) return -1;
                    return ai - bi;
                  })
                  .map(([key, value]) => {
                    if (READ_ONLY_FIELDS.has(key)) return null;
                    const inputType = inferInputType(value, key);
                    const fieldLabel = module?.fieldLabels?.[key] ?? key;
                    const helpText = module?.fieldHelp?.[key];
                    if (key === 'cliente') {
                      return (
                        <label key={key}>
                          <span>{fieldLabel}</span>
                          <select
                            value={value ? String(value) : ''}
                            onChange={(event) => updateField(key, Number(event.target.value) || '')}
                            disabled={!isSuperAdmin}
                          >
                            <option value="">Selecione</option>
                            {clientes.map((cliente) => (
                              <option key={cliente.id} value={cliente.id}>
                                {cliente.nome}
                              </option>
                            ))}
                          </select>
                        </label>
                      );
                    }
                    if (inputType === 'checkbox') {
                      return (
                        <label key={key} className="inline">
                          <span>{fieldLabel}</span>
                          <input
                            type="checkbox"
                            checked={Boolean(value)}
                            onChange={(event) => updateField(key, event.target.checked)}
                          />
                          {helpText && <small>{helpText}</small>}
                        </label>
                      );
                    }
                    if (inputType === 'textarea') {
                      return (
                        <label key={key}>
                          <span>{fieldLabel}</span>
                          <textarea
                            rows={4}
                            value={formatValue(value)}
                            onChange={(event) => updateField(key, parseValue(event.target.value, value, key))}
                          />
                          {helpText && <small>{helpText}</small>}
                        </label>
                      );
                    }
                    return (
                      <label key={key}>
                        <span>{fieldLabel}</span>
                        <input
                          type={inputType}
                          value={formatValue(value)}
                          onChange={(event) => updateField(key, parseValue(event.target.value, value, key))}
                        />
                        {helpText && <small>{helpText}</small>}
                      </label>
                    );
                  })}
              </div>
            )}

            {formError && <p className="admin-module__error">{formError}</p>}
            <div className="admin-module__drawer-actions">
              <button type="button" className="secondary" onClick={() => setIsFormOpen(false)}>
                Cancelar
              </button>
              <button type="button" className="primary" onClick={handleSubmit}>
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
