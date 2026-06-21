import { useCallback, useEffect, useRef, useState } from "react";
import { getMetrics, getSuggestions, getTrending, submitSearch } from "./api";
import { formatCount, formatPercent } from "./lib/format";
import type {
  MetricsResponse,
  SearchResponse,
  Suggestion,
  SuggestionsResponse,
  TrendingItem
} from "./types";

const INITIAL_METRICS: MetricsResponse = {
  uptime_seconds: 0,
  suggestion_requests: 0,
  search_submissions: 0,
  cache_hits: 0,
  cache_misses: 0,
  cache_failovers: 0,
  database_reads: 0,
  database_write_statements: 0,
  events_flushed: 0,
  batch_flushes: 0,
  cache_hit_rate: 0,
  latency_ms: { p50: 0, p95: 0, samples: 0 },
  batching: {
    last_batch_size: 0,
    last_flush_duration_ms: 0,
    naive_write_baseline: 0,
    actual_write_statements: 0,
    write_reduction_percent: 0
  },
  cache_nodes: {}
};

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" />
      <path d="m19 16 .7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16Z" />
    </svg>
  );
}

function App() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestionMeta, setSuggestionMeta] = useState<SuggestionsResponse | null>(null);
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [metrics, setMetrics] = useState(INITIAL_METRICS);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const suppressNextSuggestionFetch = useRef(false);

  const loadTrending = useCallback(async () => {
    try {
      const data = await getTrending();
      setTrending(data.searches);
    } catch {
      // Trending is supplementary; the primary search remains usable.
    }
  }, []);

  useEffect(() => {
    void loadTrending();
    void getMetrics().then(setMetrics).catch(() => undefined);
    const timer = window.setInterval(() => {
      void getMetrics().then(setMetrics).catch(() => undefined);
    }, 4_000);
    return () => window.clearInterval(timer);
  }, [loadTrending]);

  useEffect(() => {
    if (suppressNextSuggestionFetch.current) {
      suppressNextSuggestionFetch.current = false;
      setIsOpen(false);
      return;
    }
    if (!query.trim()) {
      setSuggestions([]);
      setSuggestionMeta(null);
      setIsOpen(false);
      setError("");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await getSuggestions(query, controller.signal);
        setSuggestions(data.suggestions);
        setSuggestionMeta(data);
        setActiveIndex(-1);
        setIsOpen(true);
      } catch (caught) {
        if ((caught as Error).name !== "AbortError") {
          setError("Suggestions are taking a breather. You can still search.");
          setIsOpen(true);
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }, 160);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!searchRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const performSearch = async (value: string) => {
    const cleaned = value.trim();
    if (!cleaned || isSubmitting) return;
    setIsSubmitting(true);
    setError("");
    setIsOpen(false);
    suppressNextSuggestionFetch.current = true;
    setQuery(cleaned);
    try {
      const response = await submitSearch(cleaned);
      setResult(response);
      window.setTimeout(() => void loadTrending(), 350);
    } catch {
      setError("Search could not be submitted. Please try again.");
      setIsOpen(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((current) => Math.min(current + 1, suggestions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) => Math.max(current - 1, -1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      void performSearch(activeIndex >= 0 ? suggestions[activeIndex].query : query);
    } else if (event.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  };

  const selectSuggestion = (suggestion: Suggestion) => {
    setQuery(suggestion.query);
    void performSearch(suggestion.query);
  };

  const liveNodes = Object.values(metrics.cache_nodes).filter((node) => node.healthy).length;

  return (
    <main className="page-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />

      <header className="site-header">
        <a className="brand" href="#top" aria-label="Suggest home">
          <span className="brand-mark"><span /></span>
          <span>SUGGEST</span>
        </a>
        <div className="header-status">
          <span className="live-dot" />
          <span>{liveNodes || 3} cache nodes live</span>
        </div>
        <a className="docs-link" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
          API docs <ArrowIcon />
        </a>
      </header>

      <section className="hero" id="top">
        <div className="eyebrow"><SparkIcon /> DISTRIBUTED SEARCH, MADE TANGIBLE</div>
        <h1>Find anything.<br /><span>Before you finish typing.</span></h1>
        <p className="hero-copy">
          A low-latency search experience powered by distributed caching,
          live trends, and intelligent write batching.
        </p>

        <div className="search-stage" ref={searchRef}>
          <div className={`search-box ${isOpen ? "is-open" : ""}`}>
            <div className="search-icon"><SearchIcon /></div>
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => { setQuery(event.target.value); setResult(null); }}
              onFocus={() => query && setIsOpen(true)}
              onKeyDown={handleKeyDown}
              role="combobox"
              aria-autocomplete="list"
              aria-controls="suggestion-list"
              aria-expanded={isOpen}
              aria-activedescendant={activeIndex >= 0 ? `suggestion-${activeIndex}` : undefined}
              placeholder="Try “iphone”, “python”, or anything else"
              autoComplete="off"
              spellCheck="false"
            />
            {isLoading ? <span className="spinner" aria-label="Loading suggestions" /> : (
              <button
                className="search-submit"
                onClick={() => void performSearch(query)}
                disabled={!query.trim() || isSubmitting}
                aria-label="Submit search"
              >
                {isSubmitting ? <span className="spinner small" /> : <ArrowIcon />}
              </button>
            )}
          </div>

          {isOpen && (
            <div className="suggestion-panel" id="suggestion-list" role="listbox">
              <div className="panel-head">
                <span>{error ? "Something went wrong" : "Suggestions"}</span>
                {suggestionMeta && !error && (
                  <span className="served-by">
                    <i className={suggestionMeta.cached ? "cache-hit" : "cache-miss"} />
                    {suggestionMeta.cached ? "cache hit" : "fresh from index"} · {suggestionMeta.duration_ms}ms
                  </span>
                )}
              </div>
              {error ? (
                <div className="error-state"><span>!</span>{error}</div>
              ) : suggestions.length ? (
                suggestions.map((suggestion, index) => (
                  <button
                    key={suggestion.query}
                    id={`suggestion-${index}`}
                    role="option"
                    aria-selected={activeIndex === index}
                    className={`suggestion-row ${activeIndex === index ? "is-active" : ""}`}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => selectSuggestion(suggestion)}
                  >
                    <span className="row-search"><SearchIcon /></span>
                    <span className="suggestion-query">{suggestion.query}</span>
                    <span className="search-count">{formatCount(suggestion.count)} searches</span>
                    <span className="row-arrow"><ArrowIcon /></span>
                  </button>
                ))
              ) : !isLoading ? (
                <div className="empty-state">No matches yet. Press Enter to make this query trend.</div>
              ) : null}
              <div className="panel-foot">
                <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
                <span><kbd>↵</kbd> search</span>
                <span><kbd>esc</kbd> close</span>
              </div>
            </div>
          )}
        </div>

        {result && (
          <div className="search-result" role="status">
            <span className="result-check">✓</span>
            <div><strong>Searched</strong><span>“{result.query}” joined the next popularity batch.</span></div>
            <span className="queued-pill">queued</span>
          </div>
        )}
      </section>

      <section className="insights-section">
        <div className="section-heading">
          <div><span className="section-kicker">LIVE SIGNALS</span><h2>What the world is curious about</h2></div>
          <span className="refresh-note"><i /> refreshes continuously</span>
        </div>

        <div className="insight-grid">
          <article className="trending-card">
            <div className="card-header"><span>Trending now</span><span className="time-chip">Past 60 min</span></div>
            <div className="trend-list">
              {trending.map((item, index) => (
                <button key={item.query} onClick={() => { setQuery(item.query); inputRef.current?.focus(); }}>
                  <span className="trend-rank">{String(index + 1).padStart(2, "0")}</span>
                  <span className="trend-name">{item.query}</span>
                  <span className="trend-spark" aria-hidden="true">
                    {[42, 64, 38, 78, 55, 88, 68].map((height, bar) => (
                      <i key={bar} style={{ height: `${(height + index * 7) % 70 + 20}%` }} />
                    ))}
                  </span>
                  <ArrowIcon />
                </button>
              ))}
            </div>
          </article>

          <article className="pulse-card">
            <div className="card-header"><span>System pulse</span><span className="live-chip"><i /> live</span></div>
            <div className="pulse-primary">
              <div><span>p95 latency</span><strong>{metrics.latency_ms.p95 || "—"}<small>ms</small></strong></div>
              <div className="latency-orbit"><span>{metrics.latency_ms.samples}</span><small>samples</small></div>
            </div>
            <div className="metric-row">
              <div><span>Cache hit rate</span><strong>{formatPercent(metrics.cache_hit_rate)}</strong><div className="meter"><i style={{ width: `${metrics.cache_hit_rate * 100}%` }} /></div></div>
              <div><span>Writes saved</span><strong>{Math.round(metrics.batching.write_reduction_percent)}%</strong><div className="meter violet"><i style={{ width: `${metrics.batching.write_reduction_percent}%` }} /></div></div>
            </div>
            <div className="node-status">
              {["cache-1", "cache-2", "cache-3"].map((node, index) => (
                <div key={node}><span className={`node-orb node-${index + 1}`}><i /></span><span>{node}</span><small>{metrics.cache_nodes[node]?.healthy === false ? "offline" : "healthy"}</small></div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="architecture-strip">
        <span className="arch-label">ONE KEY · ONE ROUTE</span>
        <div className="arch-flow">
          <div className="arch-item"><span className="arch-icon"><SearchIcon /></span><div><strong>Prefix</strong><small>normalized input</small></div></div>
          <span className="connector"><i /></span>
          <div className="arch-item"><span className="arch-icon hash">#</span><div><strong>Hash ring</strong><small>128 virtual nodes</small></div></div>
          <span className="connector"><i /></span>
          <div className="arch-item"><span className="arch-icon bolt">ϟ</span><div><strong>Redis node</strong><small>sub-millisecond read</small></div></div>
          <span className="connector"><i /></span>
          <div className="arch-item"><span className="arch-icon database">▤</span><div><strong>PostgreSQL</strong><small>durable source of truth</small></div></div>
        </div>
      </section>

      <footer><span>Built for HLD101 · Search Typeahead</span><span>100,000 indexed queries · consistent hashing · durable batches</span></footer>
    </main>
  );
}

export default App;
