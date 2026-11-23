import { Link } from "react-router-dom";
import { ArrowLeft, FlaskConical, Gauge, LayoutDashboard, Users } from "lucide-react";
import { RailShell, type RailGroup } from "./RailShell";

const GROUPS: RailGroup[] = [
  { title: "Run the system", items: [
    { to: "/admin", label: "Overview", Icon: LayoutDashboard, end: true },
    { to: "/admin/users", label: "Users", Icon: Users },
  ] },
  { title: "How it works", items: [
    { to: "/admin/models", label: "Models and measurements", Icon: Gauge },
    { to: "/admin/methodology", label: "Methodology", Icon: FlaskConical },
  ] },
];

/** The administrator console. A different rail and a badge, so nobody mistakes it for the everyday app. Only administrators reach it. */
export function AdminLayout() {
  return (
    <RailShell
      groups={GROUPS}
      home="/admin"
      note="You are using the administrator console. Other people's checks and files are never shown here."
      topLeft="Administrator console"
      badge={<span className="inline-block rounded-full bg-primary px-3 py-1 text-xs font-bold text-on-primary">Admin console</span>}
      pinned={
        <Link to="/dashboard" className="mx-1 flex items-center gap-2.5 rounded-control border border-white/20 px-3 py-2 text-[0.92rem] font-semibold text-white hover:bg-white/10 hover:no-underline">
          <ArrowLeft className="h-[1.1rem] w-[1.1rem]" aria-hidden />Back to the app
        </Link>
      }
    />
  );
}
