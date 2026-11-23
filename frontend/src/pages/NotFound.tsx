import { Link } from "react-router-dom";
import { buttonClass } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export default function NotFound() {
  useDocumentTitle("Page not found");
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="text-[4rem] font-medium leading-none text-ink-3">404</p>
      <h1 className="mt-4 text-[2.2rem]">There is nothing at this address</h1>
      <p className="mx-auto mt-3 text-ink-2">The page may have moved, or the link may be mistyped.</p>
      <div className="mt-8 flex justify-center gap-3">
        <Link to={user ? "/dashboard" : "/"} className={buttonClass("primary")}>{user ? "Go to the dashboard" : "Go to the home page"}</Link>
        <Link to="/about" className={buttonClass("quiet")}>About the project</Link>
      </div>
    </div>
  );
}
