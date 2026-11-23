import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Monitor, Moon, Sun } from "lucide-react";
import { PasswordRules } from "@/components/PasswordRules";
import { Button } from "@/components/ui/Button";
import { PasswordInput } from "@/components/ui/Field";
import { useAuth } from "@/context/AuthContext";
import { useTheme, type ThemePreference } from "@/context/ThemeContext";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import { passwordIsValid } from "@/utils/password";

const THEMES: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: "system", label: "Match my device", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
];

export default function Settings() {
  useDocumentTitle("Settings");
  const { preference, setPreference } = useTheme();
  const { adoptSession, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{ current?: string; next?: string; confirm?: string }>({});
  const [busy, setBusy] = useState(false);

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    const found: typeof errors = {};
    if (!current) found.current = "Enter your current password.";
    if (!passwordIsValid(next)) found.next = "The new password does not meet the requirements below.";
    if (confirm !== next) found.confirm = "The passwords do not match.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const res = await api.me.changePassword(current, next);
      adoptSession(res.access_token, res.user); // the old token no longer works, so continue with the fresh one
      setCurrent(""); setNext(""); setConfirm("");
      toast.success("Password changed. Other devices have been signed out.");
    } catch (err) {
      if (err instanceof ApiError && err.code === "WRONG_PASSWORD") setErrors({ current: err.message });
      else toast.error(err instanceof ApiError ? err.message : "The password could not be changed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1>Settings</h1>

      <section className="panel panel-pad mt-8" aria-labelledby="appearance">
        <h2 id="appearance" className="text-xl">Appearance</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Theme">
          {THEMES.map(({ value, label, Icon }) => (
            <button key={value} type="button" role="radio" aria-checked={preference === value} onClick={() => setPreference(value)}
              className={`flex items-center gap-3 rounded-control border px-4 py-3 text-left text-sm transition-colors ${preference === value ? "border-cyan bg-cyan/10" : "border-line hover:bg-raised"}`}>
              <Icon className="h-4 w-4" aria-hidden />{label}
            </button>
          ))}
        </div>
      </section>

      <form onSubmit={changePassword} className="panel panel-pad mt-6 space-y-5" noValidate aria-labelledby="security">
        <h2 id="security" className="text-xl">Change password</h2>
        <PasswordInput label="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" error={errors.current} />
        <div>
          <PasswordInput label="New password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" error={errors.next} />
          <PasswordRules password={next} />
        </div>
        <PasswordInput label="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" error={errors.confirm} />
        <p className="text-sm text-ink-2">Changing your password signs you out everywhere else.</p>
        <div className="flex justify-end"><Button type="submit" busy={busy}>Change password</Button></div>
      </form>

      <section className="panel panel-pad mt-6" aria-labelledby="session">
        <h2 id="session" className="text-xl">Session</h2>
        <p className="mt-2 text-sm text-ink-2">Logging out ends this session on the server, so the saved login can no longer be used.</p>
        <Button variant="quiet" className="mt-4" onClick={async () => { await logout(); toast.success("Logged out."); navigate("/login"); }}><LogOut className="h-4 w-4" aria-hidden />Log out</Button>
      </section>
    </div>
  );
}
