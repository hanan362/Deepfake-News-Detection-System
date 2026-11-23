import { useRef, useState, type FormEvent } from "react";
import { Camera, Trash2 } from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/ui/Button";
import { TextInput } from "@/components/ui/Field";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import { formatDate } from "@/utils/format";
import { validateImageFile } from "@/utils/files";

export default function Profile() {
  useDocumentTitle("Profile");
  const { user, setUser } = useAuth();
  const toast = useToast();
  const fileInput = useRef<HTMLInputElement>(null);
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [username, setUsername] = useState(user?.username ?? "");
  const [errors, setErrors] = useState<{ username?: string; avatar?: string }>({});
  const [saving, setSaving] = useState(false);
  const [avatarBusy, setAvatarBusy] = useState(false);
  const [avatarVersion, setAvatarVersion] = useState(0);
  if (!user) return null;

  const dirty = fullName.trim() !== (user.full_name ?? "") || username.trim() !== user.username;

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!/^[A-Za-z0-9_.-]{3,50}$/.test(username.trim())) return setErrors({ username: "Use 3 to 50 letters, digits, dots, dashes or underscores." });
    setErrors({});
    setSaving(true);
    try {
      setUser(await api.me.update({ full_name: fullName.trim() || null, username: username.trim() }));
      toast.success("Profile saved.");
    } catch (err) {
      if (err instanceof ApiError && err.code === "USERNAME_TAKEN") setErrors({ username: err.message });
      else toast.error(err instanceof ApiError ? err.message : "The profile could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function chooseAvatar(file: File | undefined) {
    if (!file) return;
    const problem = validateImageFile(file, 2);
    if (problem) return setErrors({ avatar: problem });
    setErrors({});
    setAvatarBusy(true);
    try {
      setUser(await api.me.uploadAvatar(file));
      setAvatarVersion((v) => v + 1);
      toast.success("Profile picture updated.");
    } catch (err) {
      setErrors({ avatar: err instanceof ApiError ? err.message : "The picture could not be uploaded." });
    } finally {
      setAvatarBusy(false);
    }
  }

  async function removeAvatar() {
    setAvatarBusy(true);
    try {
      setUser(await api.me.removeAvatar());
      setAvatarVersion((v) => v + 1);
      toast.success("Profile picture removed.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The picture could not be removed.");
    } finally {
      setAvatarBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1>Profile</h1>
      <p className="mt-2 text-ink-2">How you appear in the app. Your e-mail address is used to log in and cannot be changed here.</p>

      <section className="panel panel-pad mt-8">
        <div className="flex flex-wrap items-center gap-5">
          <Avatar user={user} size={84} version={avatarVersion} />
          <div>
            <p className="font-medium">Profile picture</p>
            <p className="text-sm text-ink-2">JPEG, PNG or WEBP, up to 2 MB. It is cropped to a square.</p>
            <div className="mt-3 flex gap-2.5">
              <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label="Choose a profile picture" onChange={(e) => { chooseAvatar(e.target.files?.[0]); e.target.value = ""; }} />
              <Button variant="quiet" size="sm" onClick={() => fileInput.current?.click()} busy={avatarBusy}><Camera className="h-4 w-4" aria-hidden />{user.has_avatar ? "Change picture" : "Upload picture"}</Button>
              {user.has_avatar && <Button variant="ghost" size="sm" onClick={removeAvatar} disabled={avatarBusy}><Trash2 className="h-4 w-4" aria-hidden />Remove</Button>}
            </div>
          </div>
        </div>
        {errors.avatar && <p className="error-text" role="alert">{errors.avatar}</p>}
      </section>

      <form onSubmit={save} className="panel panel-pad mt-6 space-y-5" noValidate>
        <h2 className="text-xl">Details</h2>
        <TextInput label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={120} optional />
        <TextInput label="Username" value={username} onChange={(e) => setUsername(e.target.value)} error={errors.username} />
        <TextInput label="E-mail address" value={user.email} readOnly disabled />
        <div className="flex justify-end"><Button type="submit" busy={saving} disabled={!dirty}>Save changes</Button></div>
      </form>

      <section className="panel panel-pad mt-6">
        <h2 className="text-xl">Account</h2>
        <dl className="mt-4 divide-y divide-line text-sm">
          {[["Role", user.role === "admin" ? "Administrator" : "User"], ["Member since", formatDate(user.created_at)], ["Last login", formatDate(user.last_login_at)]].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-2.5"><dt className="text-ink-2">{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </section>
    </div>
  );
}
