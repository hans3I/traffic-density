import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';

interface BackendLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | string;
  source: string;
  message: string;
  trace_id: string;
  server_host: string;
  details?: Record<string, unknown> | null;
  stack_trace?: string | null;
}

interface BackendLogsResponse {
  logs: BackendLogEntry[];
  total: number;
  filtered_total: number;
  sources: string[];
  levels: string[];
}

function levelClass(level: string) {
  if (level === 'ERROR') return 'bg-error-container text-on-error-container border-error/20';
  if (level === 'WARN') return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-surface-container-highest text-on-surface-variant border-outline-variant/30';
}

function formatDateTime(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return { date: '--', time: '--' };
  }

  return {
    date: date.toISOString().slice(0, 10),
    time: `${date.toISOString().slice(11, 23)} UTC`,
  };
}

function formatDetails(details?: Record<string, unknown> | null) {
  if (!details || Object.keys(details).length === 0) return 'No structured details available.';
  return JSON.stringify(details, null, 2);
}

export default function LogsPage() {
  const [logs, setLogs] = useState<BackendLogEntry[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [levels, setLevels] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [filteredTotal, setFilteredTotal] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [level, setLevel] = useState('');
  const [source, setSource] = useState('');
  const [sinceHours, setSinceHours] = useState('24');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadLogs = async () => {
      const params = new URLSearchParams({ limit: '200', since_hours: sinceHours });
      if (search.trim()) params.set('search', search.trim());
      if (level) params.set('level', level);
      if (source) params.set('source', source);

      try {
        const response = await fetch(`/api/logs?${params.toString()}`);
        if (!response.ok) {
          const payload = await response.json().catch(() => ({ message: 'Failed to load backend logs' }));
          throw new Error(payload.message || 'Failed to load backend logs');
        }

        const payload: BackendLogsResponse = await response.json();
        if (!isMounted) return;

        setLogs(payload.logs);
        setSources(payload.sources);
        setLevels(payload.levels);
        setTotal(payload.total);
        setFilteredTotal(payload.filtered_total);
        setSelectedId((current) => {
          if (current && payload.logs.some((log) => log.id === current)) return current;
          return payload.logs[0]?.id ?? null;
        });
        setError(null);
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || 'Failed to load backend logs');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadLogs();
    const interval = window.setInterval(loadLogs, 3000);

    return () => {
      isMounted = false;
      window.clearInterval(interval);
    };
  }, [search, level, source, sinceHours]);

  const selectedLog = logs.find((log) => log.id === selectedId) ?? logs[0] ?? null;
  const activeFilters = [
    level ? `Level: ${level}` : null,
    source ? `Source: ${source}` : null,
    search.trim() ? `Search: ${search.trim()}` : null,
  ].filter((filter): filter is string => Boolean(filter));

  return (
    <div className="bg-background text-on-background font-body-md min-h-screen flex antialiased">
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar activePage="logs" />

        <main className="flex-1">
          <div className="grid min-h-[calc(100vh-65px)] grid-cols-1 xl:grid-cols-[minmax(0,1fr)_380px] bg-surface">
            <section className="min-w-0 border-r border-outline-variant/40">
              <div className="border-b border-outline-variant/40 bg-surface-container-lowest/80 px-6 py-4">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h1 className="font-headline-sm text-headline-sm text-on-surface">System Logs</h1>
                    <p className="text-xs text-on-surface-variant">Real-time backend event stream</p>
                  </div>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <label className="relative block">
                      <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant">search</span>
                      <input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        className="w-full sm:w-72 rounded border border-outline-variant/70 bg-surface-container-lowest py-2 pl-10 pr-3 text-sm text-on-surface outline-none transition-colors placeholder:text-on-surface-variant/70 focus:border-primary"
                        placeholder="Search logs, IDs, hosts..."
                      />
                    </label>

                    <select
                      value={level}
                      onChange={(event) => setLevel(event.target.value)}
                      className="rounded border border-outline-variant/70 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none focus:border-primary"
                    >
                      <option value="">All levels</option>
                      {levels.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>

                    <select
                      value={source}
                      onChange={(event) => setSource(event.target.value)}
                      className="rounded border border-outline-variant/70 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none focus:border-primary"
                    >
                      <option value="">All sources</option>
                      {sources.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>

                    <select
                      value={sinceHours}
                      onChange={(event) => setSinceHours(event.target.value)}
                      className="rounded border border-outline-variant/70 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface outline-none focus:border-primary"
                    >
                      <option value="1">Last 1h</option>
                      <option value="6">Last 6h</option>
                      <option value="24">Last 24h</option>
                      <option value="168">Last 7d</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 border-b border-outline-variant/40 bg-surface-container-low px-6 py-3 text-xs">
                <span className="font-semibold text-on-surface-variant">Active Filters:</span>
                {activeFilters.length > 0 ? (
                  activeFilters.map((filter) => (
                    <span key={filter} className="rounded-full bg-surface-container-highest px-3 py-1 text-on-surface-variant">
                      {filter}
                    </span>
                  ))
                ) : (
                  <span className="text-on-surface-variant/70">None</span>
                )}
                {(activeFilters.length > 0 || sinceHours !== '24') && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearch('');
                      setLevel('');
                      setSource('');
                      setSinceHours('24');
                    }}
                    className="ml-2 font-semibold text-primary hover:underline"
                  >
                    Clear all
                  </button>
                )}
              </div>

              {error && (
                <div className="m-6 rounded-xl border border-error/25 bg-error-container p-4 text-sm text-on-error-container">
                  {error}
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] border-collapse text-left text-sm">
                  <thead className="bg-surface-container-high text-xs uppercase tracking-wide text-on-surface-variant">
                    <tr>
                      <th className="w-44 px-5 py-3 font-semibold">Timestamp (UTC)</th>
                      <th className="w-24 px-5 py-3 font-semibold">Level</th>
                      <th className="w-48 px-5 py-3 font-semibold">Source</th>
                      <th className="px-5 py-3 font-semibold">Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => {
                      const timestamp = formatDateTime(log.timestamp);
                      const isSelected = selectedLog?.id === log.id;

                      return (
                        <tr
                          key={log.id}
                          onClick={() => setSelectedId(log.id)}
                          className={`cursor-pointer border-b border-outline-variant/30 transition-colors hover:bg-surface-container-low ${
                            isSelected ? 'bg-primary-fixed/35' : 'bg-surface-container-lowest'
                          }`}
                        >
                          <td className="px-5 py-4 align-top font-label-mono text-[12px] text-on-surface">
                            <div>{timestamp.date}</div>
                            <div>{timestamp.time}</div>
                          </td>
                          <td className="px-5 py-4 align-top">
                            <span className={`rounded-full border px-2 py-1 font-label-mono text-[10px] ${levelClass(log.level)}`}>
                              {log.level}
                            </span>
                          </td>
                          <td className="px-5 py-4 align-top font-semibold text-on-surface">{log.source}</td>
                          <td className="px-5 py-4 align-top text-on-surface">{log.message}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {!isLoading && logs.length === 0 && !error && (
                <div className="flex min-h-64 items-center justify-center text-sm text-on-surface-variant">
                  No backend logs match the current filters.
                </div>
              )}

              <div className="sticky bottom-0 border-t border-outline-variant/40 bg-surface-container-lowest px-6 py-3 text-xs text-on-surface-variant">
                Showing {filteredTotal === 0 ? 0 : Math.min(logs.length, filteredTotal)} of {filteredTotal} filtered logs, {total} total
              </div>
            </section>

            <aside className="border-t border-outline-variant/40 bg-surface-container-lowest xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto xl:border-t-0">
              <div className="flex items-center justify-between border-b border-outline-variant/40 px-6 py-4">
                <h2 className="font-headline-sm text-headline-sm text-on-surface">Log Details</h2>
              </div>

              {selectedLog ? (
                <div className="space-y-6 p-6 text-sm">
                  <div className="flex items-start justify-between gap-4">
                    <span className={`rounded-full border px-3 py-1 font-label-mono text-[10px] ${levelClass(selectedLog.level)}`}>
                      {selectedLog.level}
                    </span>
                    <div className="text-right font-label-mono text-[12px] text-on-surface-variant">
                      <div>{formatDateTime(selectedLog.timestamp).date}</div>
                      <div>{formatDateTime(selectedLog.timestamp).time}</div>
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Log ID</p>
                    <p className="font-label-mono text-primary">{selectedLog.id}</p>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Source Service</p>
                    <div className="border border-outline-variant/40 bg-surface px-3 py-2 text-on-surface">{selectedLog.source}</div>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Server Host</p>
                    <p className="font-semibold text-on-surface">{selectedLog.server_host}</p>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Trace ID</p>
                    <p className="font-label-mono text-primary">{selectedLog.trace_id}</p>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Message</p>
                    <div className="rounded border border-error/20 bg-error-container/35 p-4 leading-6 text-on-surface">
                      {selectedLog.message}
                    </div>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Details</p>
                    <pre className="max-h-56 overflow-auto rounded bg-inverse-surface p-4 font-label-mono text-[11px] leading-5 text-inverse-on-surface">{formatDetails(selectedLog.details)}</pre>
                  </div>

                  <div>
                    <p className="mb-2 font-label-mono text-[11px] uppercase tracking-wider text-on-surface-variant">Stack Trace</p>
                    <pre className="max-h-72 overflow-auto rounded bg-[#111827] p-4 font-label-mono text-[11px] leading-5 text-slate-200">{selectedLog.stack_trace || 'No stack trace for this event.'}</pre>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-96 items-center justify-center p-6 text-sm text-on-surface-variant">
                  Select a log entry to inspect details.
                </div>
              )}
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
