import React from "react";

type IconName =
  | "dashboard"
  | "tasks"
  | "document"
  | "kanban"
  | "form"
  | "review"
  | "comment"
  | "bell"
  | "search"
  | "notifications"
  | "library"
  | "export"
  | "diff"
  | "audit"
  | "help"
  | "settings"
  | "users"
  | "chevron-left"
  | "chevron-right";

type Props = {
  name: IconName;
  size?: number;
  className?: string;
  label?: string;
  ariaHidden?: boolean;
};

export default function Icon({ name, size = 18, className, label, ariaHidden }: Props) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    role: "img",
    "aria-label": label,
    "aria-hidden": ariaHidden ? true : undefined,
    xmlns: "http://www.w3.org/2000/svg",
  } as React.SVGProps<SVGSVGElement>;

  switch (name) {
    case "dashboard":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="3" y="3" width="8" height="8" rx="1" />
          <rect x="13" y="3" width="8" height="5" rx="1" />
          <rect x="13" y="10" width="8" height="11" rx="1" />
          <rect x="3" y="13" width="8" height="8" rx="1" />
        </svg>
      );
    case "tasks":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M4 7h12" />
          <path d="M4 12h12" />
          <path d="M4 17h12" />
          <path d="M19 7l-2 2-1-1" />
          <path d="M19 12l-2 2-1-1" />
          <path d="M19 17l-2 2-1-1" />
        </svg>
      );
    case "document":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
          <path d="M14 3v6h6" />
        </svg>
      );
    case "kanban":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="3" y="4" width="6" height="16" rx="1" />
          <rect x="13" y="4" width="8" height="10" rx="1" />
        </svg>
      );
    case "form":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M7 8h10" />
          <path d="M7 12h10" />
          <path d="M7 16h6" />
        </svg>
      );
    case "review":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="11" cy="11" r="8" />
          <path d="M8 11l2 2 4-4" />
        </svg>
      );
    case "comment":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M21 15a3 3 0 0 1-3 3H8l-4 4V6a3 3 0 0 1 3-3h11a3 3 0 0 1 3 3v9z" />
        </svg>
      );
    case "bell":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
          <path d="M13.73 21a2 2 0 01-3.46 0" />
        </svg>
      );
    case "notifications":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7" />
          <path d="M13.73 21a2 2 0 01-3.46 0" />
        </svg>
      );
    case "search":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
      );
    case "library":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M4 19V5a2 2 0 012-2h3v16H6a2 2 0 01-2-2z" />
          <path d="M17 3h3a2 2 0 012 2v14a2 2 0 01-2 2h-3V3z" />
          <path d="M11 3h4v18h-4z" />
        </svg>
      );
    case "export":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M12 5v8" />
          <path d="M9 8l3-3 3 3" />
          <rect x="4" y="15" width="16" height="5" rx="1" />
        </svg>
      );
    case "diff":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M8 7h8" />
          <path d="M8 12h5" />
          <path d="M8 17h3" />
          <rect x="3" y="4" width="6" height="16" rx="1" />
          <rect x="15" y="4" width="6" height="16" rx="1" />
        </svg>
      );
    case "audit":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M9 3h6l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h3z" />
          <path d="M9 12l2 2 4-4" />
          <path d="M15 3v5h5" />
        </svg>
      );
    case "help":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="12" r="9" />
          <path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-2 2-2 4" />
          <path d="M12 17h.01" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6 1.65 1.65 0 0 0-.33 1.82 2 2 0 1 1-3.34 0A1.65 1.65 0 0 0 9 20a1.65 1.65 0 0 0-1-.6 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-.6-1 1.65 1.65 0 0 0-1.82-.33 2 2 0 1 1 0-3.34A1.65 1.65 0 0 0 4 9a1.65 1.65 0 0 0-.6-1A1.65 1.65 0 0 0 1.58 7.67a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 6 4.6c.43 0 .85-.16 1.18-.44A1.65 1.65 0 0 0 8.4 3a2 2 0 1 1 3.34 0A1.65 1.65 0 0 0 13 4a1.65 1.65 0 0 0 1 .6c.43 0 .85.16 1.18.44A1.65 1.65 0 0 0 15.6 6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9c.43 0 .85.16 1.18.44A2 2 0 1 1 19.4 15z" />
        </svg>
      );
    case "users":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "chevron-left":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M15 6l-6 6 6 6" />
        </svg>
      );
    case "chevron-right":
      return (
        <svg {...common} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
          <path d="M9 6l6 6-6 6" />
        </svg>
      );
    default:
      return null;
  }
}
