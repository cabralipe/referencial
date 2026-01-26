import { ROLE_OPTIONS, type RoleOption } from './roles';

type RoleSelectorProps = {
  value: RoleOption | '';
  onChange: (value: RoleOption) => void;
  onBlur?: () => void;
  error?: string | null;
  describedById?: string;
};

export function RoleSelector({ value, onChange, onBlur, error, describedById }: RoleSelectorProps) {
  return (
    <fieldset
      className="space-y-3"
      aria-describedby={describedById}
    >
      <legend className="text-sm font-semibold text-slate-700">Selecione seu perfil</legend>
      <p id="login-role-help" className="text-sm text-slate-500">
        Selecione seu perfil para entrar. Se tiver dúvida, veja a descrição abaixo.
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        {(Object.keys(ROLE_OPTIONS) as RoleOption[]).map((key) => {
          const option = ROLE_OPTIONS[key];
          const isActive = value === key;
          return (
            <label
              key={key}
              className={`cursor-pointer rounded-2xl border px-4 py-3 text-sm font-semibold transition-all ${
                isActive
                  ? 'border-sky-500 bg-sky-50 text-sky-700'
                  : 'border-slate-200 text-slate-600 hover:border-slate-300'
              }`}
            >
              <input
                type="radio"
                name="role"
                value={key}
                checked={isActive}
                onChange={() => onChange(key)}
                onBlur={onBlur}
                className="sr-only"
              />
              {option.label}
            </label>
          );
        })}
      </div>
      {error && (
        <p id="login-role-error" className="text-sm text-red-600">
          {error}
        </p>
      )}
    </fieldset>
  );
}
