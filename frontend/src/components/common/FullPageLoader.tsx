import './FullPageLoader.css';

interface FullPageLoaderProps {
  message?: string;
}

export function FullPageLoader({ message = 'Carregando…' }: FullPageLoaderProps) {
  return (
    <div className="full-page-loader">
      <div className="full-page-loader__spinner" aria-hidden="true" />
      <p className="full-page-loader__message">{message}</p>
    </div>
  );
}
