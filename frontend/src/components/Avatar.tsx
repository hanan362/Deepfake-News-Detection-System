import { useAuthedImage } from "@/hooks/useAuthedImage";
import type { User } from "@/types/api";

export function initials(user: Pick<User, "full_name" | "username">): string {
  const source = (user.full_name || user.username).trim();
  const parts = source.split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : source.slice(0, 2)).toUpperCase();
}

export function Avatar({ user, size = 36, version = 0 }: { user: User; size?: number; version?: number }) {
  // `version` lets a caller force a reload after the picture changes.
  const { url } = useAuthedImage(user.has_avatar ? `/users/me/avatar?v=${version}` : null);
  const style = { width: size, height: size };
  if (url) return <img src={url} alt="" style={style} className="rounded-full object-cover" />;
  return (
    <span style={{ ...style, fontSize: size * 0.38 }} className="inline-flex select-none items-center justify-center rounded-full bg-link/15 font-semibold text-link" aria-hidden>
      {initials(user)}
    </span>
  );
}
