import { Film, FileText, Globe, Image as ImageIcon, Images, ScanSearch, type LucideIcon } from "lucide-react";

/** The kinds of check a person can run, in the order they are offered. `module` is the key the server uses for it. */
export const CHECKS: { module: string; title: string; to: string; Icon: LucideIcon }[] = [
  { module: "text", title: "Article text", to: "/analyze/text", Icon: FileText },
  { module: "url", title: "News link", to: "/analyze/url", Icon: Globe },
  { module: "image", title: "Photo", to: "/analyze/image", Icon: ImageIcon },
  { module: "video", title: "Video", to: "/analyze/video", Icon: Film },
  { module: "multimodal", title: "Photo with its caption", to: "/analyze/multimodal", Icon: Images },
  { module: "evidence", title: "Claims against evidence", to: "/analyze/evidence", Icon: ScanSearch },
];
