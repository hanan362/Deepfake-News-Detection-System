export interface PasswordRule {
  id: string;
  label: string;
  ok: boolean;
}

/** Mirrors backend/app/core/security.py: at least 8 characters, a letter and a digit, at most 72 bytes. */
export function passwordRules(password: string): PasswordRule[] {
  return [
    { id: "length", label: "At least 8 characters", ok: password.length >= 8 },
    { id: "letter", label: "Contains a letter", ok: /[A-Za-z]/.test(password) },
    { id: "digit", label: "Contains a digit", ok: /\d/.test(password) },
    { id: "bytes", label: "At most 72 bytes", ok: new TextEncoder().encode(password).length <= 72 },
  ];
}

export const passwordIsValid = (password: string) => passwordRules(password).every((r) => r.ok);
