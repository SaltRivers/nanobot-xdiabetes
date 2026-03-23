"""Dedicated X-Diabetes CLI entry point."""

import typer

from xdiabetes.cli import commands as legacy

app = typer.Typer(
    name="x-diabetes",
    help="X-Diabetes clinical workflow CLI",
    no_args_is_help=True,
)
learning_app = typer.Typer(help="Manage X-Diabetes continuous learning")
app.add_typer(learning_app, name="learning")


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", "-v", callback=legacy.version_callback, is_eager=True
    ),
):
    """X-Diabetes clinical workflow CLI."""
    pass


@app.command("onboard")
def onboard():
    """Initialize the X-Diabetes profile."""
    legacy.xdiabetes_onboard()


@app.command("agent")
def agent(
    message: str = typer.Option(None, "--message", "-m", help="Message to send to the X-Diabetes agent"),
    session_id: str = typer.Option("cli:direct", "--session", "-s", help="Session ID"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str = typer.Option("doctor", "--mode", help="Profile mode: doctor or patient"),
    learning: bool | None = typer.Option(
        None,
        "--learning/--no-learning",
        help="Temporarily enable or disable continuous learning for this run.",
    ),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="Render assistant output as Markdown"),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Show runtime logs during chat"),
):
    """Interact with the X-Diabetes profile directly."""
    legacy.xdiabetes_agent(
        message=message,
        session_id=session_id,
        workspace=workspace,
        config=config,
        mode=mode,
        learning=learning,
        markdown=markdown,
        logs=logs,
    )


@app.command("gateway")
def gateway(
    port: int | None = typer.Option(None, "--port", "-p", help="Gateway port"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to config file"),
):
    """Start the gateway."""
    legacy.gateway(port=port, workspace=workspace, verbose=verbose, config=config)


@app.command("status")
def status():
    """Show X-Diabetes runtime status."""
    legacy.status()


@learning_app.command("status")
def learning_status(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_status(workspace=workspace, config=config, mode=mode)


@learning_app.command("review")
def learning_review(
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_review(workspace=workspace, config=config, mode=mode)


@learning_app.command("eval")
def learning_eval(
    draft_id: str = typer.Argument(..., help="Draft identifier"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_eval(draft_id=draft_id, workspace=workspace, config=config, mode=mode)


@learning_app.command("approve")
def learning_approve(
    draft_id: str = typer.Argument(..., help="Draft identifier"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_approve(draft_id=draft_id, workspace=workspace, config=config, mode=mode)


@learning_app.command("reject")
def learning_reject(
    draft_id: str = typer.Argument(..., help="Draft identifier"),
    reason: str = typer.Option("", "--reason", help="Rejection reason"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_reject(
        draft_id=draft_id,
        reason=reason,
        workspace=workspace,
        config=config,
        mode=mode,
    )


@learning_app.command("activate")
def learning_activate(
    draft_id: str = typer.Argument(..., help="Draft identifier"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_activate(draft_id=draft_id, workspace=workspace, config=config, mode=mode)


@learning_app.command("deactivate")
def learning_deactivate(
    skill_name: str = typer.Argument(..., help="Live learned skill name"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_deactivate(
        skill_name=skill_name,
        workspace=workspace,
        config=config,
        mode=mode,
    )


@learning_app.command("rollback")
def learning_rollback(
    skill_name: str = typer.Argument(..., help="Learned skill name"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="X-Diabetes workspace directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
    mode: str | None = typer.Option(None, "--mode", help="Profile mode override"),
):
    legacy.xdiabetes_learning_rollback(
        skill_name=skill_name,
        workspace=workspace,
        config=config,
        mode=mode,
    )


@learning_app.command("enable")
def learning_enable(
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
):
    legacy.xdiabetes_learning_enable(config=config)


@learning_app.command("disable")
def learning_disable(
    config: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
):
    legacy.xdiabetes_learning_disable(config=config)
