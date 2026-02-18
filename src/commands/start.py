import atexit
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from src.app import app
from src.commands.cleanup import prompt_uncommitted_changes
from src.commands.git import detect_repo, get_current_branch, resolve_branch
from src.commands.shell import build_shell_env, get_activate_cmd, launch_shell
from src.commands.worktree import (
    cleanup_worktree,
    create_worktree,
    link_deps,
    sync_untracked_files,
)
from src.settings import ClaudwaySettings


console = Console()


@app.command()
def go(
    branch: Annotated[
        str | None,
        typer.Argument(help="Git branch to work on. If omitted, you will be prompted."),
    ] = None,
    command: Annotated[
        str | None,
        typer.Option(
            "--command",
            "-c",
            help="Command to run instead of the default agent.",
        ),
    ] = None,
    shell_only: Annotated[
        bool,
        typer.Option(
            "--shell",
            "-s",
            help="Drop straight into a shell without launching the agent.",
        ),
    ] = False,
) -> None:
    """Start an isolated dev environment in a git worktree."""
    settings = ClaudwaySettings.load()
    repo = detect_repo()
    if repo is None:
        console.print("[red]Not inside a git repository.[/red]")
        raise typer.Exit(1)
    current_branch = get_current_branch(repo)
    resolved_branch = resolve_branch(repo, branch, base=current_branch)
    agent_cmd = command or settings.default_command
    user_shell = os.environ.get("SHELL", "/bin/sh")

    tmpdir = Path(tempfile.mkdtemp(prefix="cw-"))
    tmpdir.rmdir()  # git worktree add requires the target dir not to exist
    cleanup_done = False

    # Shell context - populated once the worktree is ready, used by cleanup
    # to offer a "return to shell" option.
    shell_ctx: dict[str, Any] = {}

    def do_cleanup() -> None:
        nonlocal cleanup_done
        if cleanup_done:
            return
        if shell_ctx and tmpdir.exists():
            prompt_uncommitted_changes(
                tmpdir,
                shell_ctx["user_shell"],
                shell_ctx["shell_env"],
                shell_ctx["activate_cmd"],
            )
        cleanup_done = True
        console.print("\n[yellow]Cleaning up worktree ...[/yellow]")
        cleanup_worktree(repo, tmpdir)
        console.print("[green]Done.[/green]")

    atexit.register(do_cleanup)
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def _signal_handler(signum: int, _frame: object) -> None:
        do_cleanup()
        sys.exit(128 + signum)

    try:
        with console.status("[bold cyan]Creating worktree ...", spinner="dots"):
            create_worktree(repo, tmpdir, resolved_branch)
        console.print(
            f"[green]\u2713[/green] Worktree created for [bold]{resolved_branch}[/bold]"
        )

        with console.status("[bold cyan]Syncing untracked files ...", spinner="dots"):
            sync_untracked_files(repo, tmpdir)
        console.print("[green]\u2713[/green] Untracked files synced")

        with console.status("[bold cyan]Linking dependencies ...", spinner="dots"):
            link_deps(repo, tmpdir)
        console.print("[green]\u2713[/green] Dependencies linked")

        if (tmpdir / "mise.toml").exists():
            subprocess.run(["mise", "trust"], cwd=tmpdir, capture_output=True)

        console.print()
        console.print(f"[bold green]Worktree ready![/bold green] [dim]{tmpdir}[/dim]")
        console.print(f"[dim]Branch:[/dim] [bold]{resolved_branch}[/bold]")
        console.print()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        if not shell_only:
            console.print(f"[bold cyan]Launching:[/bold cyan] {agent_cmd}\n")
            subprocess.run(agent_cmd, cwd=tmpdir, shell=True)

        console.print("[dim]Dropping into shell. Type 'exit' to clean up.[/dim]\n")

        shell_env = build_shell_env()
        venv_dir = tmpdir / "mamba" / "venv"
        activate_cmd = get_activate_cmd(user_shell, venv_dir)

        shell_ctx.update(
            user_shell=user_shell,
            shell_env=shell_env,
            activate_cmd=activate_cmd,
        )

        launch_shell(user_shell, shell_env, activate_cmd, tmpdir)

        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)
    finally:
        do_cleanup()
