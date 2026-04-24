"use client";

import { useState } from "react";

const FAILURE_MODES = [
  "wrong_tool_choice",
  "arg_formatting",
  "infinite_loop",
  "stale_context",
  "hallucinated_citation",
  "incorrect_reasoning",
  "missing_tool_call",
  "premature_termination",
  "other",
];

export function AnnotatePanel({ sessionId }: { sessionId: string }) {
  const [verdict, setVerdict] = useState<number | null>(null);
  const [selectedModes, setSelectedModes] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">(
    "idle"
  );

  const toggleMode = (mode: string) => {
    setSelectedModes((prev) =>
      prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]
    );
  };

  const submit = async () => {
    setStatus("saving");
    try {
      const res = await fetch("/api/proxy/annotations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: "session",
          target_id: sessionId,
          author_kind: "human",
          verdict,
          failure_modes: selectedModes.length > 0 ? selectedModes : null,
          note: note || null,
        }),
      });
      if (res.ok) {
        setStatus("saved");
        setTimeout(() => setStatus("idle"), 2000);
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="border border-[var(--border)] rounded-lg p-4 space-y-4">
      <h3 className="text-sm font-medium">Annotate Session</h3>

      <div>
        <label className="text-xs text-[var(--muted)] block mb-2">
          Verdict
        </label>
        <div className="flex gap-2">
          <button
            onClick={() => setVerdict(1)}
            className={`px-3 py-1 rounded text-sm border ${
              verdict === 1
                ? "border-[var(--success)] text-[var(--success)]"
                : "border-[var(--border)] text-[var(--muted)]"
            }`}
          >
            Good
          </button>
          <button
            onClick={() => setVerdict(0)}
            className={`px-3 py-1 rounded text-sm border ${
              verdict === 0
                ? "border-[var(--warning)] text-[var(--warning)]"
                : "border-[var(--border)] text-[var(--muted)]"
            }`}
          >
            Neutral
          </button>
          <button
            onClick={() => setVerdict(-1)}
            className={`px-3 py-1 rounded text-sm border ${
              verdict === -1
                ? "border-[var(--error)] text-[var(--error)]"
                : "border-[var(--border)] text-[var(--muted)]"
            }`}
          >
            Bad
          </button>
        </div>
      </div>

      <div>
        <label className="text-xs text-[var(--muted)] block mb-2">
          Failure Modes
        </label>
        <div className="flex flex-wrap gap-1.5">
          {FAILURE_MODES.map((mode) => (
            <button
              key={mode}
              onClick={() => toggleMode(mode)}
              className={`px-2 py-0.5 rounded text-xs border ${
                selectedModes.includes(mode)
                  ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent)]/10"
                  : "border-[var(--border)] text-[var(--muted)]"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs text-[var(--muted)] block mb-2">Note</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="What went wrong?"
          rows={3}
          className="w-full bg-black/30 border border-[var(--border)] rounded p-2 text-sm"
        />
      </div>

      <button
        onClick={submit}
        disabled={status === "saving"}
        className="w-full bg-[var(--accent)] text-white rounded py-2 text-sm hover:opacity-90 disabled:opacity-50"
      >
        {status === "saving"
          ? "Saving..."
          : status === "saved"
            ? "Saved!"
            : status === "error"
              ? "Error - retry"
              : "Save Annotation"}
      </button>
    </div>
  );
}
