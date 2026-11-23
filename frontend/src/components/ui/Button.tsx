import { forwardRef, type ButtonHTMLAttributes } from "react";
import clsx from "clsx";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "quiet" | "ghost" | "danger";

export function buttonClass(variant: Variant = "primary", size: "md" | "sm" | "lg" = "md", extra?: string) {
  return clsx("btn", `btn-${variant}`, size === "sm" && "btn-sm", size === "lg" && "btn-lg", extra);
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "md" | "sm" | "lg";
  busy?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", size = "md", busy = false, className, children, disabled, type = "button", ...rest },
  ref,
) {
  return (
    <button ref={ref} type={type} className={buttonClass(variant, size, className)} disabled={disabled || busy} aria-busy={busy || undefined} {...rest}>
      {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});
