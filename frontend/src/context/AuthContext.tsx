import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, onUnauthorized, tokenStore } from "@/services/api";
import type { User } from "@/types/api";
import { useToast } from "./ToastContext";

interface AuthApi {
  user: User | null;
  /** True while the stored token is being checked on first load. */
  loading: boolean;
  login: (identifier: string, password: string, remember: boolean) => Promise<User>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
  /** Adopt a fresh token and user (after a password change the old token stops working). */
  adoptSession: (token: string, user: User) => void;
}

const AuthContext = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const toast = useToast();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => tokenStore.get() !== null);

  useEffect(() => {
    onUnauthorized(() => {
      if (tokenStore.get()) {
        tokenStore.clear();
        setUser(null);
        toast.info("Your session ended. Log in again to continue.");
      }
    });
    return () => onUnauthorized(null);
  }, [toast]);

  useEffect(() => {
    if (!tokenStore.get()) return;
    let cancelled = false;
    api.me
      .get()
      .then((u) => !cancelled && setUser(u))
      .catch((err) => {
        // A rejected token is cleared by the 401 handler. Any other failure (server down) keeps the token for a retry.
        if (!(err instanceof ApiError) || err.status !== 401) toast.error("Could not reach the server to restore your session.");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const login = useCallback(async (identifier: string, password: string, remember: boolean) => {
    const res = await api.auth.login(identifier, password);
    tokenStore.set(res.access_token, remember);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      /* the session is ended locally either way */
    }
    tokenStore.clear();
    setUser(null);
  }, []);

  const adoptSession = useCallback((token: string, u: User) => {
    tokenStore.set(token, tokenStore.isRemembered());
    setUser(u);
  }, []);

  const value = useMemo(() => ({ user, loading, login, logout, setUser, adoptSession }), [user, loading, login, logout, adoptSession]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
