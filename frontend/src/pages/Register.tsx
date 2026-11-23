import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthShell } from "@/components/AuthShell";
import { PasswordRules } from "@/components/PasswordRules";
import { Button } from "@/components/ui/Button";
import { PasswordInput, TextInput } from "@/components/ui/Field";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError, fieldErrors } from "@/services/api";
import { passwordIsValid } from "@/utils/password";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME = /^[A-Za-z0-9_.-]{3,50}$/;

type Errors = Partial<Record<"email" | "username" | "password" | "confirm", string>>;

export default function Register() {
  useDocumentTitle("Create an account");
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", username: "", full_name: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const next: Errors = {};
    if (!EMAIL.test(form.email)) next.email = "Enter a valid e-mail address.";
    if (!USERNAME.test(form.username)) next.username = "Use 3 to 50 letters, digits, dots, dashes or underscores.";
    if (!passwordIsValid(form.password)) next.password = "The password does not meet the requirements below.";
    if (form.confirm !== form.password) next.confirm = "The passwords do not match.";
    setErrors(next);
    setFormError(null);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      await api.auth.register({ email: form.email.trim(), username: form.username.trim(), password: form.password, full_name: form.full_name.trim() || undefined });
      toast.success("Account created. Log in to continue.");
      navigate("/login");
    } catch (err) {
      if (err instanceof ApiError && err.code === "EMAIL_TAKEN") setErrors({ email: err.message });
      else if (err instanceof ApiError && err.code === "USERNAME_TAKEN") setErrors({ username: err.message });
      else if (Object.keys(fieldErrors(err)).length) {
        const f = fieldErrors(err);
        setErrors({ email: f.email, username: f.username, password: f.password });
        if (!f.email && !f.username && !f.password) setFormError("Some details were not accepted. Check the form and try again.");
      } else setFormError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Create an account" subtitle="Your analyses and reports are private to your account." footer={<>Already registered? <Link to="/login">Log in</Link></>}>
      <form onSubmit={submit} className="space-y-5" noValidate>
        {formError && <p className="rounded-control border border-bad/40 bg-bad/5 px-3 py-2.5 text-sm text-bad" role="alert">{formError}</p>}
        <TextInput label="E-mail address" type="email" value={form.email} onChange={set("email")} autoComplete="email" error={errors.email} autoFocus />
        <TextInput label="Username" value={form.username} onChange={set("username")} autoComplete="username" error={errors.username} hint="Letters, digits, dots, dashes and underscores." />
        <TextInput label="Full name" value={form.full_name} onChange={set("full_name")} autoComplete="name" optional />
        <div>
          <PasswordInput label="Password" value={form.password} onChange={set("password")} autoComplete="new-password" error={errors.password} />
          <PasswordRules password={form.password} />
        </div>
        <PasswordInput label="Confirm password" value={form.confirm} onChange={set("confirm")} autoComplete="new-password" error={errors.confirm} />
        <Button type="submit" busy={busy} className="w-full">Create account</Button>
      </form>
    </AuthShell>
  );
}
