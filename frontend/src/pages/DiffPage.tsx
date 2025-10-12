import { FormEvent, useState } from 'react';

import { PageInstructions } from '@/components/common/PageInstructions';
import { useBuildDiff } from '@/hooks/useDiff';

import './DiffPage.css';

const DIFF_TARGETS = [
  { value: 'resposta', label: 'Resposta' },
  { value: 'texto_unico', label: 'Texto único' },
];

export function DiffPage() {
  const [alvoTipo, setAlvoTipo] = useState('resposta');
  const [alvoId, setAlvoId] = useState('');
  const [fromVersion, setFromVersion] = useState('');
  const [toVersion, setToVersion] = useState('');
  const [diffHtml, setDiffHtml] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const diffMutation = useBuildDiff();

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErro(null);
    setDiffHtml(null);
    if (!alvoTipo || !alvoId || !fromVersion || !toVersion) {
      return;
    }
    try {
      const response = await diffMutation.mutateAsync({
        alvoTipo,
        alvoId: Number(alvoId),
        fromVersion: Number(fromVersion),
        toVersion: Number(toVersion),
      });
      setDiffHtml(response.html);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Não foi possível gerar o diff';
      setErro(message);
    }
  };

  return (
    <div className="diff">
      <header className="diff__header">
        <div>
          <h1>Comparar versões</h1>
          <p>Visualize as diferenças entre duas versões de respostas ou textos únicos.</p>
        </div>
      </header>

      <PageInstructions
        title="Como gerar um diff"
        description="Informe o alvo, a versão inicial e a versão final para gerar o HTML com marcações."
        items={[
          {
            title: 'Identifique o alvo',
            description: 'Use `resposta`, `texto_unico` ou outro tipo exposto pela API de diff.',
          },
          {
            title: 'Defina o intervalo',
            description: 'Versão “from” representa o ponto inicial, “to” representa o estado atual para comparação.',
          },
          {
            title: 'Interprete o resultado',
            description: 'O HTML retorna marcações de inserção/remoção; utilize para revisão editorial.',
          },
        ]}
      />

      <section className="diff__form">
        <form onSubmit={handleSubmit}>
          <label>
            <span>Alvo tipo</span>
            <select value={alvoTipo} onChange={(event) => setAlvoTipo(event.target.value)} required>
              {DIFF_TARGETS.map((target) => (
                <option key={target.value} value={target.value}>
                  {target.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Alvo ID</span>
            <input type="number" value={alvoId} onChange={(event) => setAlvoId(event.target.value)} required />
          </label>
          <label>
            <span>Versão inicial (from)</span>
            <input type="number" value={fromVersion} onChange={(event) => setFromVersion(event.target.value)} required />
          </label>
          <label>
            <span>Versão final (to)</span>
            <input type="number" value={toVersion} onChange={(event) => setToVersion(event.target.value)} required />
          </label>
          <button type="submit" disabled={diffMutation.isPending}>
            {diffMutation.isPending ? 'Gerando...' : 'Gerar diff'}
          </button>
        </form>
      </section>

      {erro && <p className="diff__erro">{erro}</p>}

      {diffHtml && (
        <section className="diff__resultado">
          <h2>Resultado</h2>
          <div dangerouslySetInnerHTML={{ __html: diffHtml }} />
        </section>
      )}
    </div>
  );
}
