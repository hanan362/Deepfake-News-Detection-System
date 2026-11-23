import { useEffect, useState } from "react";
import { Search, ShieldCheck, ShieldOff, UserCheck, UserX } from "lucide-react";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EmptyState, ErrorNotice, Spinner } from "@/components/ui/Feedback";
import { Pagination } from "@/components/ui/Pagination";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { useAsync } from "@/hooks/useAsync";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, ApiError } from "@/services/api";
import type { AdminUser } from "@/types/api";
import { formatDate } from "@/utils/format";

const PAGE_SIZE = 10;
type Change = { user: AdminUser; body: { role?: "user" | "admin"; is_active?: boolean }; title: string; text: string; label: string };

export default function AdminUsers() {
  useDocumentTitle("User management");
  const { user: me } = useAuth();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => {
    const t = window.setTimeout(() => { setQ(draft.trim()); setPage(1); }, 300);
    return () => window.clearTimeout(t);
  }, [draft]);

  const list = useAsync(() => api.admin.users({ page, page_size: PAGE_SIZE, q: q || undefined }), [page, q]);
  const [pending, setPending] = useState<Change | null>(null);
  const [busy, setBusy] = useState(false);

  async function apply() {
    if (!pending) return;
    setBusy(true);
    try {
      await api.admin.updateUser(pending.user.id, pending.body);
      toast.success("User updated.");
      setPending(null);
      list.reload();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "The user could not be updated.");
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  const ask = (u: AdminUser, body: Change["body"]): Change => {
    if (body.is_active === false) return { user: u, body, title: `Deactivate ${u.username}?`, text: "They will be logged out and cannot log in until you reactivate the account. Their analyses are kept.", label: "Deactivate" };
    if (body.is_active === true) return { user: u, body, title: `Reactivate ${u.username}?`, text: "They will be able to log in again.", label: "Reactivate" };
    if (body.role === "admin") return { user: u, body, title: `Make ${u.username} an administrator?`, text: "Administrators can manage users and read feedback and audit logs. They still cannot open other people's analyses.", label: "Make administrator" };
    return { user: u, body, title: `Remove administrator rights from ${u.username}?`, text: "They will become an ordinary user.", label: "Remove rights" };
  };

  return (
    <div className="mx-auto max-w-6xl">
      <h1>User management</h1>
      <p className="mt-2 text-ink-2">Change roles and access. You cannot change your own account here, so you cannot lock yourself out.</p>

      <div className="relative mt-8 max-w-md" role="search">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
        <input type="search" className="field pl-9" placeholder="Search by name, username or e-mail" aria-label="Search users" value={draft} onChange={(e) => setDraft(e.target.value)} />
      </div>

      <section className="panel mt-5 overflow-hidden" aria-label="Users">
        {list.error ? <div className="p-5"><ErrorNotice error={list.error} onRetry={list.reload} /></div>
          : !list.data ? <div className="px-5"><Spinner label="Loading users" /></div>
          : list.data.items.length === 0 ? <EmptyState title="No users found">Try a different search.</EmptyState>
          : (
            <div className="overflow-x-auto">
              <table>
                <thead><tr><th className="th">User</th><th className="th">Role</th><th className="th">Status</th><th className="th text-right">Analyses</th><th className="th">Joined</th><th className="th"><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  {list.data.items.map((u) => {
                    const self = u.id === me?.id;
                    return (
                      <tr key={u.id} className="row">
                        <td className="td"><div className="flex items-center gap-3"><Avatar user={u} size={32} /><div className="min-w-0"><p className="truncate font-medium">{u.full_name || u.username}{self && <span className="ml-2 text-xs text-ink-3">you</span>}</p><p className="truncate text-xs text-ink-2">{u.email}</p></div></div></td>
                        <td className="td">{u.role === "admin" ? "Administrator" : "User"}</td>
                        <td className="td">{u.is_active ? <span className="text-ok">Active</span> : <span className="text-bad">Deactivated</span>}</td>
                        <td className="td text-right tabular-nums">{u.analysis_count}</td>
                        <td className="td whitespace-nowrap text-ink-2">{formatDate(u.created_at)}</td>
                        <td className="td">
                          <div className="flex justify-end gap-1.5">
                            {u.role === "admin"
                              ? <Button size="sm" variant="ghost" disabled={self} onClick={() => setPending(ask(u, { role: "user" }))} aria-label={`Remove administrator rights from ${u.username}`}><ShieldOff className="h-4 w-4" aria-hidden />Demote</Button>
                              : <Button size="sm" variant="ghost" onClick={() => setPending(ask(u, { role: "admin" }))} aria-label={`Make ${u.username} an administrator`}><ShieldCheck className="h-4 w-4" aria-hidden />Promote</Button>}
                            {u.is_active
                              ? <Button size="sm" variant="ghost" disabled={self} onClick={() => setPending(ask(u, { is_active: false }))} aria-label={`Deactivate ${u.username}`}><UserX className="h-4 w-4" aria-hidden />Deactivate</Button>
                              : <Button size="sm" variant="ghost" onClick={() => setPending(ask(u, { is_active: true }))} aria-label={`Reactivate ${u.username}`}><UserCheck className="h-4 w-4" aria-hidden />Reactivate</Button>}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        {list.data && list.data.total > 0 && <Pagination page={page} pageSize={PAGE_SIZE} total={list.data.total} onPage={setPage} />}
      </section>

      <ConfirmDialog open={pending !== null} title={pending?.title ?? ""} confirmLabel={pending?.label ?? "Confirm"} tone="primary" busy={busy} onConfirm={apply} onCancel={() => setPending(null)}>{pending?.text}</ConfirmDialog>
    </div>
  );
}
