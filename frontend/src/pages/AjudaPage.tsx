import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';

import './AjudaPage.css';

export function AjudaPage() {
  return (
    <div className="ajuda">
      <PageHeader
        title="Ajuda"
        description="Veja orientações rápidas para concluir suas trilhas."
      />

      <div className="ajuda__grid">
        <Card>
          <h2>Como responder uma missão</h2>
          <p>Entre em Minha Trilha, escolha a etapa e clique em “Abrir texto”.</p>
        </Card>
        <Card>
          <h2>Como acompanhar pareceres</h2>
          <p>Os pareceres do redator ficam no Início e nos detalhes da trilha.</p>
        </Card>
        <Card>
          <h2>Precisa falar com a equipe?</h2>
          <p>Use o chat do PROLUC no canto da tela para registrar dúvidas.</p>
        </Card>
      </div>
    </div>
  );
}
