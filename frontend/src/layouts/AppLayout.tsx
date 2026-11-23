import { Link } from "react-router-dom";
import { Clock, FileText, Film, Globe, Home, Image as ImageIcon, Images, Info, LifeBuoy, ScanSearch, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { RailShell, type RailGroup } from "./RailShell";

const GROUPS: RailGroup[] = [
  { title: "Check something", items: [
    { to: "/analyze/text", label: "Article text", Icon: FileText },
    { to: "/analyze/url", label: "News link", Icon: Globe },
    { to: "/analyze/image", label: "Photo", Icon: ImageIcon },
    { to: "/analyze/video", label: "Video", Icon: Film },
    { to: "/analyze/multimodal", label: "Photo with its caption", Icon: Images },
    { to: "/analyze/evidence", label: "Claims against evidence", Icon: ScanSearch },
  ] },
  { title: "Your work", items: [
    { to: "/dashboard", label: "Home", Icon: Home },
    { to: "/history", label: "Past checks", Icon: Clock },
  ] },
  { title: "More", items: [
    { to: "/contact", label: "Contact and feedback", Icon: LifeBuoy },
    { to: "/about", label: "About the project", Icon: Info },
  ] },
];

/** The signed-in app for everyone. Administrators also get a link to their console, which ordinary users never see. */
export function AppLayout() {
  const { user } = useAuth();
  const admin = user?.role === "admin";
  return (
    <RailShell
      groups={GROUPS}
      home="/dashboard"
      note="Research prototype. A result is a hint, not proof. Check important claims against reliable sources."
      topLeft="Check a story before you share it."
      pinned={admin ? (
        <Link to="/admin" className="mx-1 flex items-center gap-2.5 rounded-control border border-white/20 px-3 py-2 text-[0.92rem] font-semibold text-white hover:bg-white/10 hover:no-underline">
          <ShieldCheck className="h-[1.1rem] w-[1.1rem] text-primary" aria-hidden />Admin console
        </Link>
      ) : null}
    />
  );
}
