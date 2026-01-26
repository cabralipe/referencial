import { ROLE_OPTIONS, type RoleOption } from './roles';

type RoleInfoCardProps = {
  role: RoleOption;
};

export function RoleInfoCard({ role }: RoleInfoCardProps) {
  const info = ROLE_OPTIONS[role];
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <h3 className="text-sm font-semibold text-slate-800">{info.title}</h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Você faz</p>
          <ul className="mt-2 space-y-2 text-sm text-slate-600">
            {info.does.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="material-symbols-outlined text-base text-emerald-600">done</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Você não faz</p>
          <ul className="mt-2 space-y-2 text-sm text-slate-600">
            {info.doesNot.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="material-symbols-outlined text-base text-rose-500">close</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
