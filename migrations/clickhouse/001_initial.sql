CREATE TABLE IF NOT EXISTS spans (
    trace_id String,
    span_id String,
    parent_span_id String,
    session_id String,
    name String,
    kind Enum8('llm'=1, 'tool'=2, 'retrieval'=3, 'agent'=4, 'other'=5),
    start_time DateTime64(9),
    end_time DateTime64(9),
    duration_ns UInt64,
    status Enum8('ok'=1, 'error'=2),
    model LowCardinality(String),
    input_tokens UInt32,
    output_tokens UInt32,
    cost_usd Float64,
    tool_name LowCardinality(String),
    attributes String,
    events String,
    input String,
    output String,
    error String,
    ingested_at DateTime DEFAULT now()
) ENGINE = MergeTree
PARTITION BY toYYYYMMDD(start_time)
ORDER BY (session_id, trace_id, start_time)
TTL start_time + INTERVAL 90 DAY;
