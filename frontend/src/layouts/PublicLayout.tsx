import { Link, NavLink, Outlet } from "react-router-dom";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Wordmark } from "@/components/Logo";
import { buttonClass } from "@/components/ui/Button";
import { PROJECT } from "@/config/project";
import { useAuth } from "@/context/AuthContext";

export function PublicLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-canvas">
        <div className="mx-auto flex h-[4.25rem] max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" className="rounded hover:no-underline" aria-label="Deepfake News Detection System, home"><Wordmark /></Link>
          <div className="flex items-center gap-1.5">
            <NavLink to="/about" className={({ isActive }) => `hidden rounded-control px-3 py-2 text-sm font-medium hover:no-underline sm:block ${isActive ? "text-ink" : "text-ink-2 hover:text-ink"}`}>About</NavLink>
            <ThemeToggle />
            {user ? (
              <Link to="/dashboard" className={buttonClass("primary", "sm")}>Your checks</Link>
            ) : (
              <>
                <Link to="/login" className={buttonClass("ghost", "sm")}>Log in</Link>
                <Link to="/register" className={buttonClass("primary", "sm")}>Create account</Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="flex-1"><Outlet /></main>
      <footer className="bg-rail text-rail-ink">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 text-sm sm:px-6 md:grid-cols-[1fr_auto] md:items-end">
          <div>
            <Wordmark onDark />
            <p className="mt-4 max-w-md text-rail-dim">A student research project. A result is a hint for a human reader, never proof.</p>
            {PROJECT.institution && <p className="mt-1 text-rail-dim">{PROJECT.department ? `${PROJECT.department}, ` : ""}{PROJECT.institution}</p>}
          </div>
          <nav className="flex gap-6" aria-label="Footer">
            <Link to="/about" className="font-medium !text-rail-ink">About</Link>
            <Link to="/contact" className="font-medium !text-rail-ink">Contact</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
