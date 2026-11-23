import { Check, Circle } from "lucide-react";
import { passwordRules } from "@/utils/password";

/** Live checklist so people see exactly what the password still needs, before the server has to tell them. */
export function PasswordRules({ password }: { password: string }) {
  return (
    <ul className="mt-2 grid grid-cols-1 gap-x-4 gap-y-1 text-[0.8125rem] sm:grid-cols-2" aria-label="Password requirements">
      {passwordRules(password).map((r) => (
        <li key={r.id} className={`flex items-center gap-1.5 ${r.ok ? "text-ok" : "text-ink-2"}`}>
          {r.ok ? <Check className="h-3.5 w-3.5" aria-hidden /> : <Circle className="h-3.5 w-3.5" aria-hidden />}
          {r.label}
          <span className="sr-only">{r.ok ? " (met)" : " (not met yet)"}</span>
        </li>
      ))}
    </ul>
  );
}
