import { api } from "@/services/api";
import type { ModelEntry, ModelsResponse, ModulesResponse, PublicModule } from "@/types/api";
import { useAsync } from "./useAsync";

/** Which checks run and their size limits. Public and rarely changing, so one request is shared by everything on the page. */
let cached: Promise<ModulesResponse> | null = null;

export function loadModels(force = false): Promise<ModulesResponse> {
  if (!cached || force) {
    cached = api.modules().catch((e) => {
      cached = null; // do not cache a failure
      throw e;
    });
  }
  return cached;
}

export function useModels() {
  const state = useAsync(() => loadModels(), []);
  const byModule = (m: string): PublicModule | undefined => state.data?.models.find((x) => x.module === m);
  return { ...state, byModule };
}

/** The full registry with model names, measured numbers and limits. Only the administrator pages call this; the server refuses everyone else. */
export function useAdminModels() {
  const state = useAsync<ModelsResponse>(() => api.models(), []);
  const byModule = (m: string): ModelEntry | undefined => state.data?.models.find((x) => x.module === m);
  return { ...state, byModule };
}

export function resetModelCache() {
  cached = null;
}
