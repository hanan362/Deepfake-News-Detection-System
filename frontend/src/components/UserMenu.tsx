import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Settings, UserRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { Avatar } from "./Avatar";

export function UserMenu() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => root.current && !root.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!user) return null;

  const signOut = async () => {
    setOpen(false);
    await logout();
    toast.success("Logged out.");
    navigate("/login");
  };

  return (
    <div ref={root} className="relative">
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex items-center gap-2 rounded-control p-1 pr-2 hover:bg-raised" aria-haspopup="menu" aria-expanded={open} aria-label="Account menu">
        <Avatar user={user} size={32} />
        <span className="hidden max-w-[10rem] truncate text-sm sm:block">{user.full_name || user.username}</span>
        <ChevronDown className="h-4 w-4 text-ink-3" aria-hidden />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-40 mt-2 w-60 rounded-panel border border-line bg-raised p-1.5 shadow-xl shadow-black/20">
          <div className="border-b border-line px-3 py-2.5">
            <p className="truncate text-sm font-medium">{user.full_name || user.username}</p>
            <p className="truncate text-xs text-ink-2">{user.email}</p>
          </div>
          <Link role="menuitem" to="/profile" onClick={() => setOpen(false)} className="mt-1 flex items-center gap-2.5 rounded-control px-3 py-2 text-sm text-ink hover:bg-panel hover:no-underline"><UserRound className="h-4 w-4" aria-hidden />Profile</Link>
          <Link role="menuitem" to="/settings" onClick={() => setOpen(false)} className="flex items-center gap-2.5 rounded-control px-3 py-2 text-sm text-ink hover:bg-panel hover:no-underline"><Settings className="h-4 w-4" aria-hidden />Settings</Link>
          <button role="menuitem" type="button" onClick={signOut} className="flex w-full items-center gap-2.5 rounded-control px-3 py-2 text-left text-sm hover:bg-panel"><LogOut className="h-4 w-4" aria-hidden />Log out</button>
        </div>
      )}
    </div>
  );
}
