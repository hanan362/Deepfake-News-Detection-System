import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Spinner } from "@/components/ui/Feedback";
import { Button } from "@/components/ui/Button";
import { useSlowFlag } from "@/hooks/useSlowFlag";

/** Full-page wait while the stored token is checked. If the server stays silent, say why and offer a way out. */
export function SessionCheck({ label, afterMs = 8000 }: { label: string; afterMs?: number }) {
  const slow = useSlowFlag(true, afterMs);
  return (
    <div className="grid min-h-screen place-items-center px-6">
      <div className="max-w-md">
        <Spinner label={label} />
        {slow && (
          <div className="rounded-control border border-warn/40 bg-warn/5 px-4 py-3 text-sm text-ink-2" data-testid="server-slow">
            <p className="font-medium text-ink">The server is taking a long time to answer.</p>
            <p className="mt-1.5">It may be busy loading a model for the first time, which can take several minutes, or it may not be running. You can keep waiting, or try again.</p>
            <Button variant="quiet" size="sm" className="mt-3" onClick={() => window.location.reload()}>Try again</Button>
          </div>
        )}
      </div>
    </div>
  );
}

/** Pages that need an account. Visitors are sent to the login page and brought back afterwards. */
export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <SessionCheck label="Restoring your session" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}

export function RequireAdmin() {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

/** Login and registration make no sense for someone who is already signed in. */
export function GuestOnly() {
  const { user, loading } = useAuth();
  if (loading) return <SessionCheck label="Loading" />;
  if (user) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
