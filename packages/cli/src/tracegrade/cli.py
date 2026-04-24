import json
import sys
import time

import click
import yaml
from rich.console import Console
from rich.table import Table

from . import __version__
from .client import TraceGradeClient
from .config import load_config, save_auth
from .report import generate_ci_report

console = Console()


@click.group()
@click.version_option(__version__)
def main():
    """TraceGrade CLI - Turn AI agent failures into regression tests."""
    pass


@main.command()
def init():
    """Scaffold a tracegrade.yaml in the current directory."""
    config = {
        "project": "my-agent",
        "instance": "http://localhost:8000",
        "agent": {
            "entrypoint": "myagent.main:run_agent",
            "version": "${GIT_SHA}",
        },
        "suites": ["default"],
        "graders": {
            "llm_judge": {
                "model": "claude-haiku-4-5-20251001",
            },
        },
    }

    with open("tracegrade.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    console.print("[green]Created tracegrade.yaml[/green]")


@main.command()
@click.argument("url")
def login(url: str):
    """Authenticate to a TraceGrade instance."""
    api_key = click.prompt("API Key", hide_input=True)

    # Verify connection
    client = TraceGradeClient(instance=url, api_key=api_key)
    try:
        client.health()
        save_auth(url, api_key)
        console.print(f"[green]Authenticated to {url}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        sys.exit(1)


@main.group()
def trace():
    """Trace commands."""
    pass


@trace.command("export")
@click.argument("session_id")
@click.option("--output", "-o", default=None, help="Output file")
def trace_export(session_id: str, output: str | None):
    """Export a session as a replayable JSON fixture."""
    client = TraceGradeClient()
    data = client.export_session(session_id)

    json_str = json.dumps(data, indent=2, default=str)

    if output:
        with open(output, "w") as f:
            f.write(json_str)
        console.print(f"[green]Exported to {output}[/green]")
    else:
        click.echo(json_str)


@main.group("eval")
def eval_group():
    """Eval commands."""
    pass


@eval_group.command("list")
@click.option("--suite", "-s", default=None, help="Filter by suite ID")
def eval_list(suite: str | None):
    """List evals from the server."""
    client = TraceGradeClient()
    evals = client.list_evals(suite_id=suite)

    table = Table(title="Evals")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Grader")
    table.add_column("Enabled")

    for e in evals:
        table.add_row(
            str(e["id"])[:8],
            e["name"],
            e.get("grader_type", ""),
            "Yes" if e.get("enabled", True) else "No",
        )

    console.print(table)


@eval_group.command("run")
@click.option("--suite", "-s", default=None, help="Suite ID to run")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
def eval_run(suite: str | None, wait: bool):
    """Run evals locally against your agent."""
    config = load_config()
    client = TraceGradeClient()

    suite_id = suite or (config.suites[0] if config.suites else "default")
    agent_version = config.agent.version if config.agent else None

    console.print(f"Starting eval run for suite [bold]{suite_id}[/bold]...")
    result = client.run_suite(suite_id, agent_version=agent_version)
    run_id = result["id"]

    if not wait:
        console.print(f"Run started: {run_id}")
        return

    # Poll for completion
    with console.status("Running evals..."):
        while True:
            run = client.get_run(run_id)
            if run.get("status") in ("completed", "failed"):
                break
            time.sleep(2)

    run = client.get_run(run_id)

    if run.get("status") == "completed":
        passed = run.get("passed", 0)
        failed = run.get("failed", 0)
        regressed = run.get("regressed", 0)

        color = "green" if failed == 0 else "red"
        console.print(f"[{color}]Passed: {passed} | Failed: {failed} | Regressed: {regressed}[/{color}]")

        if regressed > 0:
            sys.exit(1)
    else:
        console.print("[red]Run failed[/red]")
        sys.exit(1)


@eval_group.command("sync")
def eval_sync():
    """Pull/push eval definitions."""
    console.print("[yellow]Eval sync not yet implemented[/yellow]")


@main.group()
def ci():
    """CI commands."""
    pass


@ci.command("report")
@click.option("--run-id", required=True, help="Run ID to report on")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def ci_report(run_id: str, output: str | None):
    """Produce a GitHub-flavored markdown CI report."""
    client = TraceGradeClient()
    run = client.get_run(run_id)

    report = generate_ci_report(run)

    if output:
        with open(output, "w") as f:
            f.write(report)
        console.print(f"[green]Report written to {output}[/green]")
    else:
        click.echo(report)
