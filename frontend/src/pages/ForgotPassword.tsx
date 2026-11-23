import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AuthShell } from "@/components/AuthShell";
import { PasswordRules } from "@/components/PasswordRules";
import { Button } from "@/components/ui/Button";
import { PasswordInput, TextInput } from "@/components/ui/Field";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import { passwordIsValid } from "@/utils/password";

/** Two steps on one page: ask for a reset, then set a new password with the token. */
export default function ForgotPassword() {
  useDocumentTitle("Reset your password");
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [step, setStep] = useState<"request" | "reset">(params.get("token") ? "reset" : "request");
  return step === "request" ? <RequestStep onToken={(t) => { if (t) setToken(t); }} onContinue={() => setStep("reset")} /> : <ResetStep token={token} setToken={setToken} />;
}

function RequestStep({ onToken, onContinue }: { onToken: (t: string | null) => void; onContinue: () => void }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ message: string; token: string | null } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter a valid e-mail address.");
    setError(null);
    setBusy(true);
    try {
      const res = await api.auth.forgot(email.trim());
      onToken(res.reset_token ?? null);
      setDone({ message: res.message, token: res.reset_token ?? null });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Reset your password" subtitle="Enter the e-mail address of your account." footer={<Link to="/login">Back to log in</Link>}>
      {done ? (
        <div className="space-y-4" role="status">
          <p>{done.message}</p>
          {done.token ? (
            <div className="rounded-control border border-warn/40 bg-warn/5 p-3.5 text-sm">
              <p className="font-medium">Development mode</p>
              <p className="mt-1 text-ink-2">This installation has no e-mail service, so the server returned the reset token directly. It is never shown in a production setup.</p>
              <Button className="mt-3" size="sm" onClick={onContinue}>Continue to set a new password</Button>
            </div>
          ) : (
            <p className="text-sm text-ink-2">This installation has no e-mail service, so no message is sent. Ask an administrator to enable one, or set EXPOSE_RESET_TOKEN=true for local testing.</p>
          )}
          <Button variant="quiet" size="sm" onClick={onContinue}>I already have a token</Button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-5" noValidate>
          <TextInput label="E-mail address" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" error={error} autoFocus />
          <Button type="submit" busy={busy} className="w-full">Request reset</Button>
        </form>
      )}
    </AuthShell>
  );
}

function ResetStep({ token, setToken }: { token: string; setToken: (t: string) => void }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{ token?: string; password?: string; confirm?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: typeof errors = {};
    if (token.trim().length < 10) next.token = "Paste the reset token.";
    if (!passwordIsValid(password)) next.password = "The password does not meet the requirements below.";
    if (confirm !== password) next.confirm = "The passwords do not match.";
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      await api.auth.reset(token.trim(), password);
      toast.success("Password updated. Log in with your new password.");
      navigate("/login");
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Choose a new password" subtitle="Every session signed in with the old password will end." footer={<Link to="/login">Back to log in</Link>}>
      <form onSubmit={submit} className="space-y-5" noValidate>
        {formError && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{formError}</p>}
        <TextInput label="Reset token" value={token} onChange={(e) => setToken(e.target.value)} error={errors.token} autoComplete="off" />
        <div>
          <PasswordInput label="New password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" error={errors.password} />
          <PasswordRules password={password} />
        </div>
        <PasswordInput label="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" error={errors.confirm} />
        <Button type="submit" busy={busy} className="w-full">Update password</Button>
      </form>
    </AuthShell>
  );
}
