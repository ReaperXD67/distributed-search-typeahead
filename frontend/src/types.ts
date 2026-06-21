export interface Suggestion {
  query: string;
  count: number;
}

export interface SuggestionsResponse {
  query: string;
  suggestions: Suggestion[];
  cached: boolean;
  cache_node: string | null;
  duration_ms: number;
}

export interface SearchResponse {
  status: string;
  query: string;
  event_id: string;
  queued: boolean;
  message: string;
}

export interface TrendingItem {
  query: string;
  score: number;
  rank: number;
}

export interface TrendingResponse {
  window_minutes: number;
  generated_at: string;
  source: string;
  searches: TrendingItem[];
}

export interface MetricsResponse {
  uptime_seconds: number;
  suggestion_requests: number;
  search_submissions: number;
  cache_hits: number;
  cache_misses: number;
  cache_failovers: number;
  database_reads: number;
  database_write_statements: number;
  events_flushed: number;
  batch_flushes: number;
  cache_hit_rate: number;
  latency_ms: { p50: number; p95: number; samples: number };
  batching: {
    last_batch_size: number;
    last_flush_duration_ms: number;
    naive_write_baseline: number;
    actual_write_statements: number;
    write_reduction_percent: number;
  };
  cache_nodes: Record<string, { healthy: boolean; url: string }>;
}

