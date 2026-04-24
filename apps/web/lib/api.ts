const API_URL = process.env.API_URL || "http://localhost:8000";

interface FetchOptions {
  method?: string;
  body?: unknown;
  cache?: RequestCache;
  next?: { revalidate?: number; tags?: string[] };
}

export async function api<T = unknown>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { method = "GET", body, ...rest } = options;
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": process.env.TRACEGRADE_API_KEY || "dev",
    },
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  });

  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }

  return res.json();
}

export interface Session {
  id: string;
  project_id: string;
  first_seen: string;
  last_seen: string;
  trace_count: number;
  span_count: number;
  total_cost_usd: number | null;
  total_tokens_in: number | null;
  total_tokens_out: number | null;
  has_error: boolean;
  summary: string | null;
}

export interface SessionListResponse {
  items: Session[];
  next_cursor: string | null;
}

export interface Span {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  session_id: string | null;
  name: string;
  kind: string;
  start_time: string;
  end_time: string;
  duration_ns: number;
  status: string;
  model: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  tool_name: string | null;
  attributes: Record<string, unknown>;
  events: Record<string, unknown>[];
  input: string | null;
  output: string | null;
  error: string | null;
  children: Span[];
}

export interface Trace {
  trace_id: string;
  session_id: string | null;
  root_spans: Span[];
}

export interface Annotation {
  id: string;
  target_type: string;
  target_id: string;
  author_kind: string;
  verdict: number | null;
  failure_modes: string[] | null;
  note: string | null;
  created_at: string;
}

export interface EvalItem {
  id: string;
  suite_id: string;
  name: string;
  input_fixture: Record<string, unknown>;
  rubric_id: string;
  expected: Record<string, unknown> | null;
  origin_trace_id: string | null;
  version: number;
  enabled: boolean;
  created_at: string;
}

export interface Run {
  id: string;
  suite_id: string;
  agent_version: string | null;
  triggered_by: string | null;
  status: string;
  passed: number;
  failed: number;
  regressed: number;
  started_at: string | null;
  finished_at: string | null;
  report: Record<string, unknown> | null;
}
