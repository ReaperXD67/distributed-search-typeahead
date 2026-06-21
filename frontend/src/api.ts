import type {
  MetricsResponse,
  SearchResponse,
  SuggestionsResponse,
  TrendingResponse
} from "./types";

const API = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getSuggestions(query: string, signal?: AbortSignal) {
  return request<SuggestionsResponse>(`/suggestions?q=${encodeURIComponent(query)}`, { signal });
}

export function submitSearch(query: string) {
  return request<SearchResponse>("/search", {
    method: "POST",
    body: JSON.stringify({ query })
  });
}

export function getTrending() {
  return request<TrendingResponse>("/trending?limit=8&window_minutes=60");
}

export function getMetrics() {
  return request<MetricsResponse>("/metrics");
}

