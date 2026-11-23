import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthShell } from "@/components/AuthShell";
import { Button } from "@/components/ui/Button";
import { PasswordInput, TextInput } from "@/components/ui/Field";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { ApiError } from "@/services/api";

export default function Login() {
  useDocumentTitle("Log in");
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [errors, setErrors] = useState<{ identifier?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (!identifier.trim()) next.identifier = "Enter your e-mail address or username.";
    if (!password) next.password = "Enter your password.";
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      const user = await login(identifier.trim(), password, remember);
      toast.success(`Welcome back, ${user.full_name || user.username}.`);
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Log in"
      subtitle="Pick up where you left off."
      footer={<>New here? <Link to="/register">Create an account</Link></>}
    >
      <form onSubmit={submit} className="space-y-5" noValidate>
        {formError && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{formError}</p>}
        <TextInput label="E-mail or username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" error={errors.identifier} autoFocus />
        <PasswordInput label="Password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" error={errors.password} />
        <div className="flex items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-ink-2">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 accent-[rgb(var(--link))]" />
            Keep me signed in on this device
          </label>
          <Link to="/forgot-password" className="text-sm">Forgot password?</Link>
        </div>
        <Button type="submit" busy={busy} className="w-full">Log in</Button>
      </form>
    </AuthShell>
  );
}
