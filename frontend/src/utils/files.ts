const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;

/** Client-side check so people get an instant answer. The server repeats the check by inspecting the file itself. */
export function validateImageFile(file: File, maxMb: number): string | null {
  if (!ALLOWED_TYPES.includes(file.type) && !ALLOWED_EXT.test(file.name)) return "Choose a JPEG, PNG or WEBP image.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > maxMb * 1024 * 1024) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${maxMb} MB.`;
  return null;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const VIDEO_EXT = /\.(mp4|m4v|mov|webm|avi)$/i;
const VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"];

export function validateVideoFile(file: File, maxMb: number): string | null {
  if (!VIDEO_TYPES.includes(file.type) && !VIDEO_EXT.test(file.name)) return "Choose an MP4, MOV, WebM or AVI video.";
  if (file.size === 0) return "This file is empty.";
  if (file.size > maxMb * 1024 * 1024) return `This file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${maxMb} MB.`;
  return null;
}
