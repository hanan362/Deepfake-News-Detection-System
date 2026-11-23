import { useAuth } from "@/context/AuthContext";
import { AppLayout } from "./AppLayout";
import { PublicLayout } from "./PublicLayout";

/** Pages for everyone (About, and the page that says an address does not exist) look right before and after signing in. */
export function ShellByAuth() {
  const { user } = useAuth();
  return user ? <AppLayout /> : <PublicLayout />;
}
