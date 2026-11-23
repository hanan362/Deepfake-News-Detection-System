import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Wordmark } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

/** Sign-in pages: a dark side that says what the tool is for, and the form on the other. */
export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1fr)]">
      <aside className="hidden flex-col justify-between bg-rail p-10 text-rail-ink lg:flex">
        <Link to="/" className="hover:no-underline" aria-label="Home"><Wordmark onDark /></Link>
        <div>
          <p className="max-w-md font-display text-[2.6rem] font-extrabold leading-[1.04] tracking-tight text-white">Check a story before you share it.</p>
          <p className="mt-5 max-w-sm text-rail-ink">Plain answers, the reasons behind them, and an honest <span className="marked !text-on-primary">Unverified</span> whenever it cannot tell.</p>
        </div>
        <p className="max-w-sm text-sm text-rail-dim">A student research project. A result is a hint for a human reader, never proof.</p>
      </aside>
      <div className="flex min-h-screen flex-col">
        <div className="flex items-center justify-between px-4 py-4 sm:px-8">
          <Link to="/" className="hover:no-underline lg:invisible" aria-label="Home"><Wordmark /></Link>
          <ThemeToggle />
        </div>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center px-4 pb-14 sm:px-0">
          <h1 className="text-[2.2rem]">{title}</h1>
          {subtitle && <p className="mt-2 text-ink-2">{subtitle}</p>}
          <div className="mt-7">{children}</div>
          {footer && <div className="mt-6 text-sm text-ink-2">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
