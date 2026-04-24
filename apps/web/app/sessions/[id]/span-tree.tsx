"use client";

import { useState } from "react";
import type { Span } from "@/lib/api";

const KIND_COLORS: Record<string, string> = {
  llm: "text-purple-400",
  tool: "text-blue-400",
  retrieval: "text-green-400",
  agent: "text-orange-400",
  other: "text-[var(--muted)]",
};

const STATUS_COLORS: Record<string, string> = {
  ok: "text-[var(--success)]",
  error: "text-[var(--error)]",
};

function formatNs(ns: number) {
  if (ns < 1_000_000) return `${(ns / 1000).toFixed(0)}us`;
  if (ns < 1_000_000_000) return `${(ns / 1_000_000).toFixed(0)}ms`;
  return `${(ns / 1_000_000_000).toFixed(1)}s`;
}

export function SpanTree({ span, depth }: { span: Span; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const [showDetail, setShowDetail] = useState(false);
  const hasChildren = span.children.length > 0;

  return (
    <div>
      <div
        className="flex items-center gap-2 py-1 px-2 hover:bg-[var(--card)] rounded cursor-pointer text-sm"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={() => setShowDetail(!showDetail)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="w-4 text-[var(--muted)] hover:text-[var(--fg)]"
          >
            {expanded ? "v" : ">"}
          </button>
        )}
        {!hasChildren && <span className="w-4" />}

        <span className={`font-mono text-xs ${KIND_COLORS[span.kind] || KIND_COLORS.other}`}>
          [{span.kind}]
        </span>

        <span className="truncate flex-1">{span.name}</span>

        {span.model && (
          <span className="text-xs text-[var(--muted)]">{span.model}</span>
        )}
        {span.tool_name && (
          <span className="text-xs text-blue-400">{span.tool_name}</span>
        )}

        <span className="text-xs text-[var(--muted)]">
          {formatNs(span.duration_ns)}
        </span>

        <span className={`text-xs ${STATUS_COLORS[span.status] || ""}`}>
          {span.status === "error" ? "ERR" : ""}
        </span>
      </div>

      {showDetail && (
        <div
          className="border border-[var(--border)] rounded mx-2 mb-2 p-3 text-xs bg-[var(--card)]"
          style={{ marginLeft: `${depth * 20 + 8}px` }}
        >
          <div className="grid grid-cols-2 gap-2 mb-3">
            <div>
              <span className="text-[var(--muted)]">Span ID:</span>{" "}
              <span className="font-mono">{span.span_id}</span>
            </div>
            <div>
              <span className="text-[var(--muted)]">Trace ID:</span>{" "}
              <span className="font-mono">{span.trace_id.slice(0, 16)}</span>
            </div>
            {span.input_tokens != null && (
              <div>
                <span className="text-[var(--muted)]">Input tokens:</span>{" "}
                {span.input_tokens}
              </div>
            )}
            {span.output_tokens != null && (
              <div>
                <span className="text-[var(--muted)]">Output tokens:</span>{" "}
                {span.output_tokens}
              </div>
            )}
            {span.cost_usd != null && (
              <div>
                <span className="text-[var(--muted)]">Cost:</span> $
                {span.cost_usd.toFixed(6)}
              </div>
            )}
          </div>

          {span.input && (
            <div className="mb-2">
              <div className="text-[var(--muted)] mb-1">Input:</div>
              <pre className="bg-black/30 p-2 rounded overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {span.input}
              </pre>
            </div>
          )}

          {span.output && (
            <div className="mb-2">
              <div className="text-[var(--muted)] mb-1">Output:</div>
              <pre className="bg-black/30 p-2 rounded overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                {span.output}
              </pre>
            </div>
          )}

          {span.error && (
            <div className="mb-2">
              <div className="text-[var(--error)] mb-1">Error:</div>
              <pre className="bg-red-950/30 p-2 rounded overflow-x-auto text-[var(--error)]">
                {span.error}
              </pre>
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <a
              href={`/annotate?type=span&id=${span.span_id}`}
              className="text-[var(--accent)] hover:underline"
            >
              Annotate this span
            </a>
          </div>
        </div>
      )}

      {expanded &&
        hasChildren &&
        span.children.map((child) => (
          <SpanTree key={child.span_id} span={child} depth={depth + 1} />
        ))}
    </div>
  );
}
