import httpx

from .config import load_config


class TraceGradeClient:
    def __init__(self, instance: str | None = None, api_key: str | None = None):
        config = load_config()
        self.instance = (instance or config.instance).rstrip("/")
        self.api_key = api_key or config.api_key
        self._client = httpx.Client(
            base_url=self.instance,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=30.0,
        )

    def get_sessions(self, **params) -> dict:
        r = self._client.get("/api/sessions", params=params)
        r.raise_for_status()
        return r.json()

    def get_session(self, session_id: str) -> dict:
        r = self._client.get(f"/api/sessions/{session_id}")
        r.raise_for_status()
        return r.json()

    def get_trace(self, trace_id: str) -> dict:
        r = self._client.get(f"/api/traces/{trace_id}")
        r.raise_for_status()
        return r.json()

    def export_session(self, session_id: str) -> dict:
        r = self._client.get(f"/api/sessions/{session_id}/timeline")
        r.raise_for_status()
        return r.json()

    def list_evals(self, suite_id: str | None = None) -> list[dict]:
        params = {}
        if suite_id:
            params["suite_id"] = suite_id
        r = self._client.get("/api/evals", params=params)
        r.raise_for_status()
        return r.json()

    def run_suite(self, suite_id: str, agent_version: str | None = None) -> dict:
        body = {}
        if agent_version:
            body["agent_version"] = agent_version
        r = self._client.post(f"/api/suites/{suite_id}/run", json=body)
        r.raise_for_status()
        return r.json()

    def get_run(self, run_id: str) -> dict:
        r = self._client.get(f"/api/runs/{run_id}")
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        r = self._client.get("/health")
        r.raise_for_status()
        return r.json()
