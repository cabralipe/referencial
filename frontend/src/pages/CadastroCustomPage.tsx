import { useEffect, useState } from 'react';
import { useApiClient } from '@/api/client';
import { FullPageLoader } from '@/components/common/FullPageLoader';
import { PageInstructions } from '@/components/common/PageInstructions';
import './CadastroCustomPage.css';

interface ConfigEntry {
  id: number;
  chave: string;
  valor_texto: string;
}

interface FieldDef {
  chave: string;
  label: string;
  placeholder: string;
  hint?: string;
}

const SECTIONS: { title: string; fields: FieldDef[] }[] = [
  {
    title: 'Textos gerais da página',
    fields: [
      { chave: 'cadastro_titulo', label: 'Título', placeholder: 'Criar Conta', hint: 'Cabeçalho principal do formulário.' },
      { chave: 'cadastro_subtitulo', label: 'Subtítulo', placeholder: 'Preencha os dados abaixo para se cadastrar na plataforma.', hint: 'Texto de apoio abaixo do título.' },
    ],
  },
  {
    title: 'Campo Município',
    fields: [
      { chave: 'cadastro_label_municipio', label: 'Label', placeholder: 'Município (Cliente)' },
      { chave: 'cadastro_placeholder_municipio', label: 'Placeholder', placeholder: 'Digite para buscar um município' },
    ],
  },
  {
    title: 'Campo Escola',
    fields: [
      { chave: 'cadastro_label_escola', label: 'Label', placeholder: 'Escola' },
      { chave: 'cadastro_placeholder_escola', label: 'Placeholder', placeholder: 'Digite para buscar uma escola' },
    ],
  },
  {
    title: 'Campo Tipo de Usuário',
    fields: [
      { chave: 'cadastro_label_tipo_usuario', label: 'Label', placeholder: 'Eu sou um(a)' },
    ],
  },
  {
    title: 'Campo Nome',
    fields: [
      { chave: 'cadastro_label_nome', label: 'Label', placeholder: 'Nome Completo' },
      { chave: 'cadastro_placeholder_nome', label: 'Placeholder', placeholder: 'Seu nome' },
    ],
  },
  {
    title: 'Campo E-mail',
    fields: [
      { chave: 'cadastro_label_email', label: 'Label', placeholder: 'E-mail' },
      { chave: 'cadastro_placeholder_email', label: 'Placeholder', placeholder: 'nome@instituicao.com.br' },
    ],
  },
  {
    title: 'Campos de Senha',
    fields: [
      { chave: 'cadastro_label_senha', label: 'Label "Senha"', placeholder: 'Senha' },
      { chave: 'cadastro_label_confirmar_senha', label: 'Label "Confirmar Senha"', placeholder: 'Confirmar Senha' },
    ],
  },
];

const ALL_KEYS = SECTIONS.flatMap((s) => s.fields.map((f) => f.chave));

export function CadastroCustomPage() {
  const api = useApiClient();

  const [entries, setEntries] = useState<ConfigEntry[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get<ConfigEntry[]>('admin/clientes-config');
        const all: ConfigEntry[] = res.data ?? [];
        const cadastro = all.filter((e) => e.chave.startsWith('cadastro_'));
        setEntries(cadastro);
        const map: Record<string, string> = {};
        for (const e of cadastro) {
          map[e.chave] = e.valor_texto;
        }
        setValues(map);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [api]);

  const handleSave = async () => {
    setIsSaving(true);
    setStatus('idle');
    try {
      for (const chave of ALL_KEYS) {
        const valor = (values[chave] ?? '').trim();
        const existing = entries.find((e) => e.chave === chave);

        if (existing) {
          if (valor === '') {
            await api.del(`admin/clientes-config/${existing.id}`);
          } else if (valor !== existing.valor_texto) {
            await api.patch(`admin/clientes-config/${existing.id}`, {
              body: { valor_texto: valor },
            });
          }
        } else if (valor !== '') {
          await api.post('admin/clientes-config', {
            body: { chave, valor_texto: valor },
          });
        }
      }

      // Reload entries to get fresh IDs after creates/deletes
      const res = await api.get<ConfigEntry[]>('admin/clientes-config');
      const all: ConfigEntry[] = res.data ?? [];
      const cadastro = all.filter((e) => e.chave.startsWith('cadastro_'));
      setEntries(cadastro);

      setStatus('success');
    } catch {
      setStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <FullPageLoader message="Carregando configurações..." />;

  return (
    <div className="cadastro-custom">
      <header className="cadastro-custom__header">
        <div>
          <h1>Personalizar tela de Criar Conta</h1>
          <p>Defina os textos exibidos no formulário público de cadastro para o seu município.</p>
        </div>
        <button
          type="button"
          className="cadastro-custom__save-btn"
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? 'Salvando...' : 'Salvar alterações'}
        </button>
      </header>

      <PageInstructions
        title="Como funciona"
        description="Cada campo abaixo corresponde a um texto exibido no formulário público de cadastro. Deixe o campo em branco para usar o texto padrão da plataforma."
        items={[
          { title: 'Label', description: 'O nome do campo exibido acima do input.' },
          { title: 'Placeholder', description: 'O texto de dica dentro do input quando vazio.' },
          { title: 'Texto padrão', description: 'Mostrado em cinza — é o valor usado quando o campo está em branco.' },
        ]}
      />

      <div className="cadastro-custom__sections">
        {SECTIONS.map((section) => (
          <section key={section.title} className="cadastro-custom__section">
            <h2 className="cadastro-custom__section-title">{section.title}</h2>
            <div className="cadastro-custom__fields">
              {section.fields.map((field) => (
                <div key={field.chave} className="cadastro-custom__field">
                  <label className="cadastro-custom__label">
                    {field.label}
                    {field.hint && <span className="cadastro-custom__hint">{field.hint}</span>}
                  </label>
                  <input
                    className="cadastro-custom__input"
                    type="text"
                    value={values[field.chave] ?? ''}
                    placeholder={field.placeholder}
                    onChange={(e) =>
                      setValues((prev) => ({ ...prev, [field.chave]: e.target.value }))
                    }
                  />
                  <span className="cadastro-custom__default">Padrão: "{field.placeholder}"</span>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {status === 'success' && (
        <div className="cadastro-custom__status success">
          Configurações salvas com sucesso. As alterações já aparecem no formulário de cadastro.
        </div>
      )}
      {status === 'error' && (
        <div className="cadastro-custom__status error">
          Não foi possível salvar. Verifique sua conexão e tente novamente.
        </div>
      )}
    </div>
  );
}
