import { forwardRef, useId, useState, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";

interface FieldShellProps {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  children: (ids: { id: string; describedBy: string | undefined; invalid: boolean }) => ReactNode;
  optional?: boolean;
}

export function FieldShell({ label, hint, error, children, optional }: FieldShellProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errId = `${id}-err`;
  const describedBy = [hint ? hintId : null, error ? errId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
        {optional && <span className="ml-1.5 font-normal text-ink-3">optional</span>}
      </label>
      {children({ id, describedBy, invalid: Boolean(error) })}
      {hint && !error && <p id={hintId} className="hint">{hint}</p>}
      {error && <p id={errId} className="error-text" role="alert">{error}</p>}
    </div>
  );
}

interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  optional?: boolean;
}

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(function TextInput({ label, hint, error, optional, className, ...rest }, ref) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional}>
      {({ id, describedBy, invalid }) => (
        <input ref={ref} id={id} className={`field ${className ?? ""}`} aria-invalid={invalid || undefined} aria-describedby={describedBy} {...rest} />
      )}
    </FieldShell>
  );
});

export const PasswordInput = forwardRef<HTMLInputElement, TextInputProps>(function PasswordInput({ label, hint, error, className, ...rest }, ref) {
  const [shown, setShown] = useState(false);
  return (
    <FieldShell label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <div className="relative">
          <input
            ref={ref}
            id={id}
            type={shown ? "text" : "password"}
            className={`field pr-11 ${className ?? ""}`}
            aria-invalid={invalid || undefined}
            aria-describedby={describedBy}
            {...rest}
          />
          <button
            type="button"
            onClick={() => setShown((s) => !s)}
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-2 text-ink-3 hover:text-ink"
            aria-label={shown ? "Hide password" : "Show password"}
            aria-pressed={shown}
          >
            {shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      )}
    </FieldShell>
  );
});

interface TextAreaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> {
  label: string;
  hint?: ReactNode;
  error?: string | null;
  optional?: boolean;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea({ label, hint, error, optional, className, ...rest }, ref) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional}>
      {({ id, describedBy, invalid }) => (
        <textarea ref={ref} id={id} className={`field leading-relaxed ${className ?? ""}`} aria-invalid={invalid || undefined} aria-describedby={describedBy} {...rest} />
      )}
    </FieldShell>
  );
});
