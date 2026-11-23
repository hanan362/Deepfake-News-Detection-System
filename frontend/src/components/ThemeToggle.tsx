import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

export function ThemeToggle() {
  const { resolved, toggle } = useTheme();
  const next = resolved === "dark" ? "light" : "dark";
  return (
    <button type="button" onClick={toggle} className="btn btn-ghost !px-2.5" aria-label={`Switch to the ${next} theme`} title={`Switch to the ${next} theme`}>
      {resolved === "dark" ? <Sun className="h-[1.05rem] w-[1.05rem]" aria-hidden /> : <Moon className="h-[1.05rem] w-[1.05rem]" aria-hidden />}
    </button>
  );
}
