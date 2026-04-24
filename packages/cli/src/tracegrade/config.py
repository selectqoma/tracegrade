import json
import os
from pathlib import Path

import yaml
from pydantic import BaseModel


class AgentConfig(BaseModel):
    entrypoint: str = ""
    version: str = "${GIT_SHA}"


class TraceGradeConfig(BaseModel):
    project: str = ""
    instance: str = "http://localhost:8000"
    api_key: str = ""
    agent: AgentConfig | None = None
    suites: list[str] = ["default"]
    graders: dict = {}


def find_config_file() -> Path | None:
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        cfg = d / "tracegrade.yaml"
        if cfg.exists():
            return cfg
        cfg = d / "tracegrade.yml"
        if cfg.exists():
            return cfg
    return None


def load_config() -> TraceGradeConfig:
    cfg_file = find_config_file()
    data = {}

    if cfg_file:
        with open(cfg_file) as f:
            data = yaml.safe_load(f) or {}

    # Merge with ~/.tracegrade/config.json for auth
    home_cfg = Path.home() / ".tracegrade" / "config.json"
    if home_cfg.exists():
        with open(home_cfg) as f:
            home_data = json.load(f)
            if "api_key" not in data and "api_key" in home_data:
                data["api_key"] = home_data["api_key"]
            if "instance" not in data and "instance" in home_data:
                data["instance"] = home_data["instance"]

    # Env vars override
    if os.environ.get("TRACEGRADE_API_KEY"):
        data["api_key"] = os.environ["TRACEGRADE_API_KEY"]
    if os.environ.get("TRACEGRADE_URL"):
        data["instance"] = os.environ["TRACEGRADE_URL"]

    return TraceGradeConfig(**data)


def save_auth(instance: str, api_key: str) -> None:
    home_dir = Path.home() / ".tracegrade"
    home_dir.mkdir(exist_ok=True)
    cfg_path = home_dir / "config.json"

    data = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            data = json.load(f)

    data["instance"] = instance
    data["api_key"] = api_key

    with open(cfg_path, "w") as f:
        json.dump(data, f, indent=2)
