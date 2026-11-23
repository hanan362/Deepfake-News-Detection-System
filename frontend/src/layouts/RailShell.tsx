import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X, type LucideIcon } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { UserMenu } from "@/components/UserMenu";
import { Wordmark } from "@/components/Logo";

export interface RailItem { to: string; label: string; Icon: LucideIcon; end?: boolean }
export interface RailGroup { title: string; items: RailItem[] }

interface ShellProps {
  groups: RailGroup[];
  /** Where the logo leads. */
  home: string;
  /** A short line at the bottom of the rail. */
  note: string;
  /** Shown under the logo, for example to say this is the administrator console. */
  badge?: ReactNode;
  /** Extra links pinned to the bottom of the rail. */
  pinned?: ReactNode;
  /** Words at the left of the top bar. */
  topLeft?: ReactNode;
}

function Nav({ groups, onNavigate }: { groups: RailGroup[]; onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="space-y-6">
      {groups.map((g) => (
        <div key={g.title}>
          <p className="mb-1.5 px-3 text-[0.8rem] font-semibold text-rail-dim">{g.title}</p>
          <ul className="space-y-0.5">
            {g.items.map(({ to, label, Icon, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    `relative flex items-center gap-3 rounded-control px-3 py-2 text-[0.92rem] font-medium hover:no-underline ${
                      isActive ? "bg-white/10 text-white before:absolute before:inset-y-1.5 before:-left-3 before:w-1 before:rounded-r before:bg-primary" : "text-rail-ink hover:bg-white/5 hover:text-white"
                    }`
                  }
                >
                  <Icon className="h-[1.1rem] w-[1.1rem] shrink-0" aria-hidden />
                  <span className="flex-1">{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** The signed-in frame: a dark navigation rail on the left, a quiet top bar, and the page. The user app and the admin console both use it. */
export function RailShell({ groups, home, note, badge, pinned, topLeft }: ShellProps) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);

  const brand = (
    <div className="px-3">
      <Link to={home} className="block hover:no-underline" aria-label="Home"><Wordmark onDark /></Link>
      {badge && <div className="mt-3">{badge}</div>}
    </div>
  );
  const foot = (
    <div className="mt-auto space-y-4">
      {pinned}
      <p className="px-3 text-xs leading-relaxed text-rail-dim">{note}</p>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_1fr]">
      <aside className="no-print sticky top-0 hidden h-screen flex-col gap-7 overflow-y-auto bg-rail px-3 py-6 lg:flex">
        {brand}
        <Nav groups={groups} />
        {foot}
      </aside>

      <AnimatePresence>
        {open && (
          <motion.div className="fixed inset-0 z-40 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}>
            <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
            <motion.aside initial={{ x: -290 }} animate={{ x: 0 }} exit={{ x: -290 }} transition={{ duration: 0.18 }} className="absolute inset-y-0 left-0 flex w-72 flex-col gap-7 overflow-y-auto bg-rail px-3 py-6" aria-label="Navigation">
              <button type="button" onClick={() => setOpen(false)} className="absolute right-3 top-4 rounded p-1 text-rail-ink hover:text-white" aria-label="Close navigation"><X className="h-5 w-5" /></button>
              {brand}
              <Nav groups={groups} onNavigate={() => setOpen(false)} />
              {foot}
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-col">
        <header className="no-print sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" onClick={() => setOpen(true)} className="btn btn-ghost !px-2 lg:hidden" aria-label="Open navigation"><Menu className="h-5 w-5" /></button>
            {topLeft && <div className="hidden min-w-0 truncate text-sm text-ink-2 lg:block">{topLeft}</div>}
          </div>
          <div className="flex items-center gap-1"><ThemeToggle /><UserMenu /></div>
        </header>
        <main id="main" className="app-main flex-1 px-4 py-8 sm:px-6 lg:px-10"><Outlet /></main>
      </div>
    </div>
  );
}
