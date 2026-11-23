import type {
  AdminStats, AdminUser, Analysis, AuditEntry, DashboardStats, EvaluationResponse, EvidenceEvaluationResponse, VideoEvaluationResponse, UrduEvaluationResponse, Feedback, MessageResponse,
  ModelsResponse, ModulesResponse, Page, TokenResponse, User,
} from "@/types/api";

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "/api/v1";
const TOKEN_KEY = "ddn.token";

/** The backend always answers errors as {"error": {"code", "message", "details"}}. */
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

// ---- token storage: session by default, localStorage only when the user asks to stay signed in ----
export const tokenStore = {
  get(): string | null {
    return sessionStorage.getItem(TOKEN_KEY) ?? localStorage.getItem(TOKEN_KEY);
  },
  set(token: string, remember: boolean) {
    this.clear();
    (remember ? localStorage : sessionStorage).setItem(TOKEN_KEY, token);
  },
  clear() {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_KEY);
  },
  isRemembered(): boolean {
    return localStorage.getItem(TOKEN_KEY) !== null;
  },
};

let unauthorizedHandler: (() => void) | null = null;
/** Called when the server rejects the stored token (expired, logged out elsewhere, password changed). */
export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler;
}

interface Options {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  json?: unknown;
  form?: FormData;
  auth?: boolean;
  signal?: AbortSignal;
  query?: Record<string, string | number | undefined | null>;
}

function buildUrl(path: string, query?: Options["query"]) {
  const url = `${API_BASE}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function send(path: string, opts: Options = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (opts.auth !== false && token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }
  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), { method: opts.method ?? "GET", headers, body, signal: opts.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "NETWORK", "Cannot reach the server. Check that the API is running and your connection is working.");
  }
  if (!res.ok) {
    let code = "ERROR";
    let message = `The server answered with status ${res.status}.`;
    let details: unknown;
    try {
      const data = await res.json();
      if (data?.error) ({ code, message, details } = data.error);
    } catch {
      /* the body was not JSON: keep the generic message */
    }
    if (res.status === 401 && token && (code === "INVALID_TOKEN" || code === "UNAUTHENTICATED")) unauthorizedHandler?.();
    throw new ApiError(res.status, code, message, details);
  }
  return res;
}

async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const res = await send(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function fetchBlob(path: string, signal?: AbortSignal): Promise<Blob> {
  return (await send(path, { signal })).blob();
}

/** Download a file that needs the Authorization header (a plain <a href> cannot send it). */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const blob = await fetchBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  health: () => request<{ status: string; database: string; text_model: string; version: string }>("/health", { auth: false }),
  /** What an ordinary visitor needs: which checks run, plain descriptions and the size limits. */
  modules: () => request<ModulesResponse>("/modules", { auth: false }),
  /** The model registry and the measured evaluations. The server answers these for administrators only. */
  models: () => request<ModelsResponse>("/models"),
  evaluation: () => request<EvaluationResponse>("/models/text/evaluation"),
  evidenceEvaluation: () => request<EvidenceEvaluationResponse>("/models/evidence/evaluation"),
  videoEvaluation: () => request<VideoEvaluationResponse>("/models/video/evaluation"),
  urduEvaluation: () => request<UrduEvaluationResponse>("/models/text-ur/evaluation"),

  auth: {
    register: (body: { email: string; username: string; password: string; full_name?: string }) =>
      request<User>("/auth/register", { method: "POST", json: body, auth: false }),
    login: (identifier: string, password: string) =>
      request<TokenResponse>("/auth/login", { method: "POST", json: { identifier, password }, auth: false }),
    logout: () => request<MessageResponse>("/auth/logout", { method: "POST" }),
    forgot: (email: string) => request<MessageResponse>("/auth/forgot-password", { method: "POST", json: { email }, auth: false }),
    reset: (token: string, new_password: string) =>
      request<MessageResponse>("/auth/reset-password", { method: "POST", json: { token, new_password }, auth: false }),
  },

  me: {
    get: () => request<User>("/users/me"),
    update: (body: { full_name?: string | null; username?: string }) => request<User>("/users/me", { method: "PATCH", json: body }),
    changePassword: (current_password: string, new_password: string) =>
      request<TokenResponse>("/users/me/password", { method: "POST", json: { current_password, new_password } }),
    uploadAvatar: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return request<User>("/users/me/avatar", { method: "POST", form });
    },
    removeAvatar: () => request<User>("/users/me/avatar", { method: "DELETE" }),
  },

  analysis: {
    text: (text: string, headline?: string) => request<Analysis>("/analysis/text", { method: "POST", json: { text, headline: headline || null } }),
    image: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return request<Analysis>("/analysis/image", { method: "POST", form });
    },
    video: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return request<Analysis>("/analysis/video", { method: "POST", form });
    },
    multimodal: (input: { file: File | null; text: string; headline: string }) => {
      const form = new FormData();
      if (input.file) form.append("file", input.file);
      if (input.text.trim()) form.append("text", input.text);
      if (input.headline.trim()) form.append("headline", input.headline.trim());
      return request<Analysis>("/analysis/multimodal", { method: "POST", form });
    },
    evidence: (text: string) => request<Analysis>("/analysis/evidence", { method: "POST", json: { text } }),
    url: (url: string) => request<Analysis>("/analysis/url", { method: "POST", json: { url } }),
    get: (id: number) => request<Analysis>(`/analysis/${id}`),
    list: (q: { page?: number; page_size?: number; analysis_type?: string; verdict?: string; q?: string }) =>
      request<Page<Analysis>>("/analysis", { query: q }),
    remove: (id: number) => request<void>(`/analysis/${id}`, { method: "DELETE" }),
    reportPdf: (id: number) => downloadFile(`/analysis/${id}/report.pdf`, `analysis-${id}.pdf`),
  },

  dashboard: () => request<DashboardStats>("/dashboard/stats"),

  feedback: {
    create: (body: { category: string; message: string; analysis_id?: number | null }) =>
      request<Feedback>("/feedback", { method: "POST", json: body }),
    mine: () => request<Feedback[]>("/feedback"),
  },

  admin: {
    stats: () => request<AdminStats>("/admin/stats"),
    users: (q: { page?: number; page_size?: number; q?: string }) => request<Page<AdminUser>>("/admin/users", { query: q }),
    updateUser: (id: number, body: { role?: "user" | "admin"; is_active?: boolean }) =>
      request<User>(`/admin/users/${id}`, { method: "PATCH", json: body }),
    feedback: (status?: string) => request<Feedback[]>("/admin/feedback", { query: { status } }),
    reviewFeedback: (id: number, status: "new" | "reviewed" | "dismissed") =>
      request<Feedback>(`/admin/feedback/${id}`, { method: "PATCH", json: { status } }),
    audit: (q: { page?: number; page_size?: number; action?: string }) => request<Page<AuditEntry>>("/admin/audit-logs", { query: q }),
  },
};

/** Field-level messages from a 422 response, keyed by field name, so a form can show them beside the right input. */
export function fieldErrors(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError) || err.code !== "VALIDATION_ERROR" || !Array.isArray(err.details)) return {};
  const out: Record<string, string> = {};
  for (const d of err.details as { field?: string; message?: string }[]) {
    if (d?.field && d.message && !out[d.field]) out[d.field] = d.message.replace(/^Value error, /, "");
  }
  return out;
}
