import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { useApiClient } from '@/api/client';
import { buildBackendUrl } from '@/config/env';
import { useAdminScope } from '@/hooks/useAdminScope';
import { ADMIN_MODULES } from './adminModules';

import './AdminConsolePage.css';

type AdminShortcut = {
  id: string;
  label: string;
  description: string;
  to?: string;
  href?: string;
  external?: boolean;
};

export function AdminConsolePage() {
  const [search, setSearch] = useState('');
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    if (typeof window === 'undefined') return [];
    const stored = window.localStorage.getItem('adminConsoleRecentSearches');
    if (!stored) return [];
    try {
      return JSON.parse(stored);
    } catch {
      return [];
    }
  });
  const [checklistStatus, setChecklistStatus] = useState<Record<string, boolean | null>>({});
  const [checklistLoading, setChecklistLoading] = useState(false);
  const checklistInFlight = useRef(false);
  const client = useApiClient();
  const navigate = useNavigate();
  const { isSuperAdmin, clientes, selectedClienteId, setSelectedClienteId } = useAdminScope();
  const avaHref = buildBackendUrl('/ava/catalogo/');

  const filteredModules = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return ADMIN_MODULES;
    return ADMIN_MODULES.filter((module) => {
      const examples = module.examples?.join(' ').toLowerCase() ?? '';
      const tags = module.tags?.join(' ').toLowerCase() ?? '';
      return (
        module.label.toLowerCase().includes(term) ||
        module.description.toLowerCase().includes(term) ||
        examples.includes(term) ||
        tags.includes(term)
      );
    });
  }, [search]);

  const comecePorAqui = useMemo(
    () => filteredModules.filter((module) => module.tags?.includes('comece-aqui')),
    [filteredModules],
  );

  const grouped = useMemo(() => {
    const modules = filteredModules.filter((module) => !module.tags?.includes('comece-aqui'));
    return modules.reduce<Record<string, typeof ADMIN_MODULES>>((acc, module) => {
      if (!acc[module.category]) acc[module.category] = [];
      acc[module.category].push(module);
      return acc;
    }, {});
  }, [filteredModules]);

  const suggestions = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return [];
    return filteredModules.slice(0, 6);
  }, [filteredModules, search]);

  const shortcuts: AdminShortcut[] = [
    {
      id: 'novo-gt',
      label: 'Criar GT',
      description: 'Monte os grupos de trabalho.',
      to: '/admin/console/gts?new=1',
    },
    {
      id: 'nova-escola',
      label: 'Criar escola',
      description: 'Cadastre as escolas do cliente.',
      to: '/admin/console/escolas?new=1',
    },
    {
      id: 'nova-tarefa',
      label: 'Criar tarefa',
      description: 'Defina trilhas e etapas.',
      to: '/admin/console/tarefas?new=1',
    },
    {
      id: 'nova-pergunta',
      label: 'Criar pergunta',
      description: 'Estruture os blocos.',
      to: '/admin/console/perguntas?new=1',
    },
    {
      id: 'revisoes',
      label: 'Ver revisões pendentes',
      description: 'Priorize o que está em revisão.',
      to: '/admin/console/revisoes?filter=pendentes',
    },
    {
      id: 'mural',
      label: 'Publicar aviso no mural',
      description: 'Envie comunicados ao GT.',
      to: '/admin/mural',
    },
    {
      id: 'ava',
      label: 'Abrir AVA',
      description: 'Entrar direto no ambiente virtual.',
      href: avaHref,
      external: true,
    },
    {
      id: 'relatorios',
      label: 'Ver relatórios rápidos',
      description: 'Gere resumos de utilização.',
      to: '/relatorios',
    },
    {
      id: 'producao-redator',
      label: 'Produção por Redator',
      description: 'Acompanhe e exporte textos.',
      to: '/admin/producao-redatores',
    },
    {
      id: 'exports',
      label: 'Exportar documento',
      description: 'Gere relatórios finais.',
      to: '/admin/console/exports?new=1',
    },
    {
      id: 'cadastro-custom',
      label: 'Personalizar tela de cadastro',
      description: 'Edite textos e labels do formulário público.',
      to: '/admin/cadastro-custom',
    },
  ];

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('adminConsoleRecentSearches', JSON.stringify(recentSearches.slice(0, 6)));
  }, [recentSearches]);

  useEffect(() => {
    const loadChecklist = async () => {
      if (checklistInFlight.current) return;
      checklistInFlight.current = true;
      setChecklistLoading(true);
      const baseHeaders = isSuperAdmin && selectedClienteId ? { 'X-Cliente-ID': String(selectedClienteId) } : undefined;
      const steps = [
        { id: 'usuarios', endpoint: '/admin/usuarios' },
        { id: 'gts', endpoint: '/admin/gts' },
        { id: 'escolas', endpoint: '/admin/escolas' },
        { id: 'tarefas', endpoint: '/admin/tarefas' },
        { id: 'perguntas', endpoint: '/admin/perguntas' },
        { id: 'notificacoes', endpoint: '/admin/notificacoes' },
      ];
      const results: Record<string, boolean | null> = {};
      for (const step of steps) {
        try {
          const response = await client.get<any>(step.endpoint, {
            query: { page_size: 1 },
            headers: baseHeaders,
          });
          const payload = response.data;
          const list = Array.isArray(payload) ? payload : payload?.results ?? [];
          results[step.id] = list.length > 0;
        } catch {
          results[step.id] = null;
        }
      }
      setChecklistStatus((prev) => ({ ...prev, ...results }));
      setChecklistLoading(false);
      checklistInFlight.current = false;
    };
    loadChecklist();
  }, [client, isSuperAdmin, selectedClienteId]);

  const handleSearchSubmit = (value: string) => {
    const term = value.trim();
    if (!term) return;
    setRecentSearches((prev) => [term, ...prev.filter((item) => item !== term)].slice(0, 6));
  };

  const checklistSteps = [
    {
      id: 'cliente',
      label: 'Cliente selecionado',
      description: isSuperAdmin ? 'Escolha o município para operar.' : 'Você já está no cliente correto.',
      ok: isSuperAdmin ? Boolean(selectedClienteId) : true,
      action: isSuperAdmin ? () => navigate('/admin/console') : undefined,
      actionLabel: isSuperAdmin ? 'Selecionar cliente' : '',
    },
    {
      id: 'usuarios',
      label: 'Usuários criados',
      description: 'Cadastre admin, redator e GT.',
      ok: checklistStatus.usuarios ?? null,
      action: () => navigate('/admin/console/usuarios'),
      actionLabel: 'Ir para usuários',
    },
    {
      id: 'gts',
      label: 'GTs criados',
      description: 'Organize os grupos por etapa.',
      ok: checklistStatus.gts ?? null,
      action: () => navigate('/admin/console/gts'),
      actionLabel: 'Ir para GTs',
    },
    {
      id: 'escolas',
      label: 'Escolas cadastradas',
      description: 'Registre as escolas do cliente.',
      ok: checklistStatus.escolas ?? null,
      action: () => navigate('/admin/console/escolas'),
      actionLabel: 'Ir para escolas',
    },
    {
      id: 'tarefas',
      label: 'Trilhas cadastradas',
      description: 'Defina etapas e sequência.',
      ok: checklistStatus.tarefas ?? null,
      action: () => navigate('/admin/console/tarefas'),
      actionLabel: 'Ir para trilhas',
    },
    {
      id: 'perguntas',
      label: 'Perguntas criadas',
      description: 'Preencha os blocos de escrita.',
      ok: checklistStatus.perguntas ?? null,
      action: () => navigate('/admin/console/perguntas'),
      actionLabel: 'Ir para perguntas',
    },
    {
      id: 'notificacoes',
      label: 'Mural publicado',
      description: 'Envie um primeiro aviso.',
      ok: checklistStatus.notificacoes ?? null,
      action: () => navigate('/admin/mural'),
      actionLabel: 'Publicar mural',
    },
  ];

  return (
    <div className="admin-console">
      <PageHeader
        title="Admin Console"
        description="Ajuste dados, vínculos e regras sem depender do Django Admin."
      />

      <section className="admin-console__hero">
        <Card>
          <div className="admin-console__hero-header">
            <div>
              <h2>O que você quer fazer hoje?</h2>
              <p>Atalhos rápidos para as tarefas mais comuns.</p>
            </div>
            <div className="admin-console__filters">
              <label>
                <span>Buscar qualquer coisa</span>
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  onBlur={(event) => handleSearchSubmit(event.target.value)}
                  placeholder="Ex.: GTs, trilhas, revisões"
                />
              </label>
              {isSuperAdmin && (
                <label>
                  <span>Escopo de cliente</span>
                  <select
                    value={selectedClienteId === '' ? '' : String(selectedClienteId)}
                    onChange={(event) =>
                      setSelectedClienteId(event.target.value ? Number(event.target.value) : '')
                    }
                  >
                    <option value="">Todos os clientes</option>
                    {clientes.map((cliente) => (
                      <option key={cliente.id} value={cliente.id}>
                        {cliente.nome}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </div>
          {suggestions.length > 0 && (
            <div className="admin-console__suggestions">
              <span>Sugestões:</span>
              {suggestions.map((module) => (
                <button
                  type="button"
                  key={module.id}
                  onClick={() => navigate(`/admin/console/${module.id}`)}
                >
                  {module.label}
                </button>
              ))}
            </div>
          )}
          {recentSearches.length > 0 && (
            <div className="admin-console__recent">
              <span>Buscas recentes:</span>
              {recentSearches.map((term) => (
                <button
                  type="button"
                  key={term}
                  onClick={() => setSearch(term)}
                >
                  {term}
                </button>
              ))}
            </div>
          )}
        </Card>

        <div className="admin-console__hero-grid">
          <Card>
            <div className="admin-console__shortcut-grid">
              {shortcuts.map((shortcut) =>
                shortcut.external ? (
                  <a
                    key={shortcut.id}
                    href={shortcut.href}
                    className="admin-console__shortcut"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <h4>{shortcut.label}</h4>
                    <p>{shortcut.description}</p>
                  </a>
                ) : (
                  <Link key={shortcut.id} to={shortcut.to!} className="admin-console__shortcut">
                    <h4>{shortcut.label}</h4>
                    <p>{shortcut.description}</p>
                  </Link>
                ),
              )}
            </div>
          </Card>

          <Card>
            <div className="admin-console__checklist">
              <div className="admin-console__checklist-header">
                <h3>Configuração mínima</h3>
                <p>Veja o que já está pronto para começar.</p>
              </div>
              <div className="admin-console__checklist-items">
                {checklistSteps.map((step) => (
                  <div key={step.id} className="admin-console__checklist-item">
                    <div>
                      <strong>{step.label}</strong>
                      <small>{step.description}</small>
                    </div>
                    <div className="admin-console__checklist-action">
                      <span className={`status ${step.ok === null ? 'status--pending' : step.ok ? 'status--ok' : 'status--warn'}`}>
                        {step.ok === null ? '...' : step.ok ? 'OK' : 'Faltando'}
                      </span>
                      {step.action && (
                        <button type="button" onClick={step.action} disabled={checklistLoading}>
                          {step.actionLabel}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card>
            <div className="admin-console__help">
              <h3>Ajuda rápida</h3>
              <p>Passos rápidos para não se perder.</p>
              <ul>
                <li>Comece criando usuários e GTs.</li>
                <li>Defina trilhas e perguntas antes de liberar escrita.</li>
                <li>Use o mural para avisos de calendário.</li>
              </ul>
              <div className="admin-console__help-actions">
                <Link to="/ajuda">Abrir ajuda</Link>
                <a href={avaHref} target="_blank" rel="noopener noreferrer">Abrir AVA</a>
                <Link to="/admin/console/usuarios">Gerenciar usuários</Link>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {comecePorAqui.length > 0 && (
        <section className="admin-console__section">
          <h3>Comece por aqui</h3>
          <div className="admin-console__grid">
            {comecePorAqui.map((module) => (
              <Card key={module.id}>
                <div className="admin-console__card">
                  <div>
                    <h4>{module.label}</h4>
                    <p>{module.description}</p>
                    {module.examples && (
                      <p className="admin-console__examples">Ex.: {module.examples.join(' · ')}</p>
                    )}
                    {module.tags && (
                      <div className="admin-console__tags">
                        {module.tags.map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <Link to={`/admin/console/${module.id}`} className="admin-console__link">
                    Abrir módulo
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {Object.entries(grouped).map(([category, modules]) => (
        <section key={category} className="admin-console__section">
          <h3>{category}</h3>
          <div className="admin-console__grid">
            {modules.map((module) => (
              <Card key={module.id}>
                <div className="admin-console__card">
                  <div>
                    <h4>{module.label}</h4>
                    <p>{module.description}</p>
                    {module.examples && (
                      <p className="admin-console__examples">Ex.: {module.examples.join(' · ')}</p>
                    )}
                    {module.tags && (
                      <div className="admin-console__tags">
                        {module.tags.map((tag) => (
                          <span key={tag}>{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <Link to={`/admin/console/${module.id}`} className="admin-console__link">
                    Abrir módulo
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
