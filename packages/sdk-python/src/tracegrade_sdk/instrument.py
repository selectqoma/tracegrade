"""TraceGrade instrumentation SDK.

Usage:
    from tracegrade_sdk import instrument
    instrument(service_name="my-agent", endpoint="http://localhost:8000/v1/traces")
"""

import contextvars
import importlib
import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

_session_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tracegrade_session_id", default=None
)


def instrument(
    service_name: str = "agent",
    endpoint: str = "http://localhost:8000/v1/traces",
    api_key: str | None = None,
    session_id: str | None = None,
) -> None:
    """Instrument the current process for TraceGrade.

    Three lines to get started:
        from tracegrade_sdk import instrument
        instrument(service_name="my-agent", endpoint="http://localhost:4318")
        # ...existing agent code unchanged...
    """
    attrs = {"service.name": service_name}
    if session_id:
        attrs["gen_ai.session.id"] = session_id
        _session_id_var.set(session_id)

    resource = Resource.create(attrs)
    provider = TracerProvider(resource=resource)

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _auto_instrument()


def _auto_instrument() -> None:
    """Try to instrument known AI libraries if they're installed."""
    instrumentors = [
        ("opentelemetry.instrumentation.anthropic", "AnthropicInstrumentor"),
        ("opentelemetry.instrumentation.openai", "OpenAIInstrumentor"),
        ("opentelemetry.instrumentation.langchain", "LangchainInstrumentor"),
    ]
    for module_path, class_name in instrumentors:
        try:
            mod = importlib.import_module(module_path)
            instrumentor_cls = getattr(mod, class_name)
            instrumentor_cls().instrument()
            logger.info("Auto-instrumented %s", module_path)
        except ImportError:
            pass
        except Exception:
            logger.debug("Failed to auto-instrument %s", module_path, exc_info=True)


def set_session_id(session_id: str) -> None:
    """Set the session ID for the current async context."""
    _session_id_var.set(session_id)


def get_session_id() -> str | None:
    """Get the current session ID."""
    return _session_id_var.get()
