import { api, type Session, type Trace, type Span } from "@/lib/api";
import { SpanTree } from "./span-tree";
import { AnnotatePanel } from "./annotate-panel";

export default async function SessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let session: Session;
  let timeline: Trace[];
  try {
    [session, timeline] = await Promise.all([
      api<Session>(`/api/sessions/${id}`),
      api<Trace[]>(`/api/sessions/${id}/timeline`),
    ]);
  } catch {
    return (
      <div className="text-center py-12 text-[var(--muted)]">
        Session not found or API unavailable
      </div>
    );
  }

  const totalSpans = timeline.reduce(
    (acc, t) => acc + countSpans(t.root_spans),
    0
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <a
            href="/sessions"
            className="text-sm text-[var(--muted)] hover:text-[var(--fg)]"
          >
            &larr; Sessions
          </a>
          <h1 className="text-xl font-bold font-mono mt-1">{id}</h1>
        </div>
        <div className="flex items-center gap-4 text-sm text-[var(--muted)]">
          <span>
            {session.trace_count} trace{session.trace_count !== 1 ? "s" : ""}
          </span>
          <span>{totalSpans} spans</span>
          {session.total_cost_usd && (
            <span>${session.total_cost_usd.toFixed(4)}</span>
          )}
          {session.has_error && (
            <span className="text-[var(--error)] font-medium">Has errors</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {timeline.map((trace) => (
            <div
              key={trace.trace_id}
              className="border border-[var(--border)] rounded-lg overflow-hidden"
            >
              <div className="px-4 py-2 border-b border-[var(--border)] bg-[var(--card)] flex items-center justify-between">
                <span className="font-mono text-xs text-[var(--muted)]">
                  trace:{trace.trace_id.slice(0, 16)}
                </span>
                <span className="text-xs text-[var(--muted)]">
                  {countSpans(trace.root_spans)} spans
                </span>
              </div>
              <div className="p-2">
                {trace.root_spans.map((span) => (
                  <SpanTree key={span.span_id} span={span} depth={0} />
                ))}
              </div>
            </div>
          ))}
          {timeline.length === 0 && (
            <div className="text-center py-12 text-[var(--muted)]">
              No traces found for this session
            </div>
          )}
        </div>

        <div className="space-y-4">
          <AnnotatePanel sessionId={id} />

          {session.summary && (
            <div className="border border-[var(--border)] rounded-lg p-4">
              <h3 className="text-sm font-medium mb-2">Summary</h3>
              <p className="text-sm text-[var(--muted)]">{session.summary}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function countSpans(spans: Span[]): number {
  return spans.reduce((acc, s) => acc + 1 + countSpans(s.children), 0);
}
