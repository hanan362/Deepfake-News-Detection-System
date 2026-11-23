import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ThemePreference = "light" | "dark" | "system";
const KEY = "ddn.theme";

interface ThemeApi {
  preference: ThemePreference;
  resolved: "light" | "dark";
  setPreference: (p: ThemePreference) => void;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeApi | null>(null);

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function readPreference(): ThemePreference {
  const saved = localStorage.getItem(KEY);
  return saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPref] = useState<ThemePreference>(readPreference);
  const [systemDark, setSystemDark] = useState(systemPrefersDark);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const resolved: "light" | "dark" = preference === "system" ? (systemDark ? "dark" : "light") : preference;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", resolved);
  }, [resolved]);

  const setPreference = useCallback((p: ThemePreference) => {
    localStorage.setItem(KEY, p);
    setPref(p);
  }, []);

  const value = useMemo<ThemeApi>(
    () => ({ preference, resolved, setPreference, toggle: () => setPreference(resolved === "dark" ? "light" : "dark") }),
    [preference, resolved, setPreference],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeApi {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
