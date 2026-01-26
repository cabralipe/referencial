import { Link, useLocation } from 'react-router-dom';

import './Breadcrumbs.css';

const LABELS: Record<string, string> = {
  inicio: 'Início',
  'minha-trilha': 'Minha Trilha',
  texto: 'Construção de Texto',
  cadernos: 'Cadernos',
  mural: 'Mural',
  ajuda: 'Ajuda',
  ppp: 'PPP',
  admin: 'Admin',
  redator: 'Redator',
  trilhas: 'Trilhas',
  revisoes: 'Revisões',
};

function resolveLabel(segment: string, index: number, segments: string[]) {
  if (LABELS[segment]) return LABELS[segment];
  if (/^\d+$/.test(segment)) {
    const previous = segments[index - 1];
    if (previous === 'minha-trilha' || previous === 'ppp') {
      return `Trilha #${segment}`;
    }
    if (previous === 'cadernos') {
      return `Caderno #${segment}`;
    }
    if (previous === 'texto') {
      return `Texto #${segment}`;
    }
  }
  return segment;
}

export function Breadcrumbs() {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);
  if (segments.length === 0) return null;

  const paths = segments.map((segment, index) => {
    const path = `/${segments.slice(0, index + 1).join('/')}`;
    return {
      segment,
      path,
      label: resolveLabel(segment, index, segments),
    };
  });

  return (
    <nav className="breadcrumbs" aria-label="Você está aqui">
      {paths.map((item, index) => {
        const isLast = index === paths.length - 1;
        return (
          <span key={item.path} className={isLast ? 'breadcrumbs__current' : 'breadcrumbs__item'}>
            {isLast ? (
              item.label
            ) : (
              <Link to={item.path}>{item.label}</Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
