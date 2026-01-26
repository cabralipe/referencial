import { Link } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/common/Card';
import { useAuth } from '@/context/AuthContext';

import './RedatorConteudosPage.css';

type ConteudoCard = {
  title: string;
  description: string;
  to?: string;
  actionLabel: string;
  disabled?: boolean;
  helper?: string;
};

export function RedatorConteudosPage() {
  const { user } = useAuth();
  const isRedator = user?.role === 'articulador';

  const cards: ConteudoCard[] = [
    {
      title: 'Trilhas pedagógicas',
      description: 'Gerencie as trilhas, etapas e tarefas que estruturam a produção.',
      to: '/tarefas',
      actionLabel: 'Abrir',
    },
    {
      title: 'Textos',
      description: 'Acesse textos únicos e colaborativos para validar conteúdos.',
      to: '/texto-unico',
      actionLabel: 'Abrir',
    },
    {
      title: 'Quadros',
      description: 'Quadros de perguntas e referências para apoiar as revisões.',
      to: '/quadros',
      actionLabel: 'Abrir',
    },
    {
      title: 'Formulários',
      description: 'Formulários estruturados para coleta de informações.',
      to: '/formularios',
      actionLabel: isRedator ? 'Solicitar acesso' : 'Abrir',
      disabled: isRedator,
      helper: isRedator ? 'Disponível para administradores do cliente.' : undefined,
    },
  ];

  return (
    <div className="redator-conteudos">
      <PageHeader
        title="Conteúdos"
        description="Acesse os módulos existentes e organize as validações sem sair do fluxo."
      />

      <div className="redator-conteudos__grid">
        {cards.map((card) => (
          <Card key={card.title}>
            <div className="redator-conteudos__card">
              <div>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
                {card.helper && <small>{card.helper}</small>}
              </div>
              {card.to && !card.disabled ? (
                <Link className="redator-conteudos__cta" to={card.to}>
                  {card.actionLabel}
                </Link>
              ) : (
                <button className="redator-conteudos__cta is-disabled" type="button" disabled>
                  {card.actionLabel}
                </button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
