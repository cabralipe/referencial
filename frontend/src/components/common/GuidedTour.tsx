import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from 'react';

import './GuidedTour.css';

export type TourStep = {
  /** Título curto da etapa. */
  title: string;
  /** Texto explicativo (didático e objetivo). */
  body: string;
  /** Seletor CSS do elemento destacado. Se ausente/oculto, a etapa fica centralizada. */
  target?: string;
  /** Posição preferida do balão em relação ao alvo. */
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'center';
};

interface GuidedTourProps {
  steps: TourStep[];
  open: boolean;
  onClose: () => void;
  onFinish?: () => void;
}

type Rect = { top: number; left: number; width: number; height: number } | null;

const PADDING = 8;
const CARD_WIDTH = 340;
const CARD_GAP = 14;
const CARD_EST_HEIGHT = 240;

function getRect(selector?: string): Rect {
  if (!selector) return null;
  const el = document.querySelector(selector) as HTMLElement | null;
  if (!el) return null;
  const r = el.getBoundingClientRect();
  if (r.width === 0 && r.height === 0) return null;
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), Math.max(min, max));
}

export function GuidedTour({ steps, open, onClose, onFinish }: GuidedTourProps) {
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect>(null);
  const [cardStyle, setCardStyle] = useState<CSSProperties>({
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
  });
  const cardRef = useRef<HTMLDivElement | null>(null);

  const total = steps.length;
  const step = steps[index];

  // Calcula a posição do cartão a partir do alvo, sempre dentro da viewport.
  const positionCard = useCallback(
    (targetRect: Rect, placement: TourStep['placement']) => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const cardW = cardRef.current?.offsetWidth || CARD_WIDTH;
      const cardH = cardRef.current?.offsetHeight || CARD_EST_HEIGHT;

      const resolved = placement ?? (targetRect ? 'bottom' : 'center');

      if (!targetRect || resolved === 'center') {
        setCardStyle({
          top: clamp((vh - cardH) / 2, CARD_GAP, vh - cardH - CARD_GAP),
          left: clamp((vw - cardW) / 2, CARD_GAP, vw - cardW - CARD_GAP),
          transform: 'none',
        });
        return;
      }

      let top: number;
      let left: number;

      switch (resolved) {
        case 'right':
          left = targetRect.left + targetRect.width + CARD_GAP;
          top = targetRect.top;
          break;
        case 'left':
          left = targetRect.left - cardW - CARD_GAP;
          top = targetRect.top;
          break;
        case 'top':
          left = targetRect.left + targetRect.width / 2 - cardW / 2;
          top = targetRect.top - cardH - CARD_GAP;
          break;
        case 'bottom':
        default:
          left = targetRect.left + targetRect.width / 2 - cardW / 2;
          top = targetRect.top + targetRect.height + CARD_GAP;
          break;
      }

      // Se não couber ao lado direito, reposiciona abaixo (ou acima) do alvo.
      if (resolved === 'right' && left + cardW > vw - CARD_GAP) {
        left = targetRect.left + targetRect.width / 2 - cardW / 2;
        top = targetRect.top + targetRect.height + CARD_GAP;
      }
      if (resolved === 'left' && left < CARD_GAP) {
        left = targetRect.left + targetRect.width / 2 - cardW / 2;
        top = targetRect.top + targetRect.height + CARD_GAP;
      }
      // Se ficaria abaixo da viewport, joga para cima do alvo.
      if (top + cardH > vh - CARD_GAP) {
        const above = targetRect.top - cardH - CARD_GAP;
        if (above >= CARD_GAP) top = above;
      }

      setCardStyle({
        top: clamp(top, CARD_GAP, vh - cardH - CARD_GAP),
        left: clamp(left, CARD_GAP, vw - cardW - CARD_GAP),
        transform: 'none',
      });
    },
    [],
  );

  const recompute = useCallback(() => {
    if (!open || !step) return;
    const el = step.target ? (document.querySelector(step.target) as HTMLElement | null) : null;
    if (el) {
      el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
    }
    const nextRect = getRect(step.target);
    setRect(nextRect);
    positionCard(nextRect, step.placement);
  }, [open, step, positionCard]);

  // Reinicia no começo sempre que abre.
  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  useLayoutEffect(() => {
    if (!open) return;
    recompute();
    // Recalcula após o scroll suave e após o cartão renderizar com a altura real.
    const id1 = window.setTimeout(recompute, 80);
    const id2 = window.setTimeout(recompute, 360);
    window.addEventListener('resize', recompute);
    window.addEventListener('scroll', recompute, true);
    return () => {
      window.clearTimeout(id1);
      window.clearTimeout(id2);
      window.removeEventListener('resize', recompute);
      window.removeEventListener('scroll', recompute, true);
    };
  }, [open, index, recompute]);

  // Trava o scroll do corpo e foca o cartão.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusId = window.setTimeout(() => cardRef.current?.focus(), 60);
    return () => {
      document.body.style.overflow = previous;
      window.clearTimeout(focusId);
    };
  }, [open, index]);

  const finish = useCallback(() => {
    onFinish?.();
    onClose();
  }, [onClose, onFinish]);

  const next = useCallback(() => {
    setIndex((current) => {
      if (current >= total - 1) {
        finish();
        return current;
      }
      return current + 1;
    });
  }, [finish, total]);

  const back = useCallback(() => setIndex((current) => Math.max(0, current - 1)), []);

  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      } else if (event.key === 'ArrowRight' || event.key === 'Enter') {
        event.preventDefault();
        next();
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        back();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, next, back, onClose]);

  if (!open || !step) return null;

  const spotlightStyle: CSSProperties | undefined = rect
    ? {
        top: rect.top - PADDING,
        left: rect.left - PADDING,
        width: rect.width + PADDING * 2,
        height: rect.height + PADDING * 2,
      }
    : undefined;

  return (
    <div className="guided-tour" role="dialog" aria-modal="true" aria-labelledby="guided-tour-title">
      {rect ? (
        <div className="guided-tour__spotlight" style={spotlightStyle} aria-hidden="true" />
      ) : (
        <div className="guided-tour__backdrop" aria-hidden="true" onClick={onClose} />
      )}

      <div
        ref={cardRef}
        className="guided-tour__card"
        style={cardStyle}
        tabIndex={-1}
        aria-describedby="guided-tour-body"
      >
        <div className="guided-tour__progress" aria-hidden="true">
          {steps.map((_, i) => (
            <span key={i} className={`guided-tour__dot ${i === index ? 'is-active' : ''}`} />
          ))}
        </div>

        <p className="guided-tour__step-count">Passo {index + 1} de {total}</p>
        <h2 id="guided-tour-title" className="guided-tour__title">{step.title}</h2>
        <p id="guided-tour-body" className="guided-tour__body">{step.body}</p>

        <div className="guided-tour__actions">
          <button type="button" className="guided-tour__skip" onClick={onClose}>
            Pular tutorial
          </button>
          <div className="guided-tour__nav">
            {index > 0 && (
              <button type="button" className="guided-tour__btn guided-tour__btn--ghost" onClick={back}>
                Voltar
              </button>
            )}
            <button type="button" className="guided-tour__btn guided-tour__btn--primary" onClick={next}>
              {index >= total - 1 ? 'Concluir' : 'Próximo'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
