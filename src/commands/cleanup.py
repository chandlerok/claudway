import sys
from pathlib import Path

import typer
from rich.console import Console

from src.commands.shell import launch_shell
from src.commands.worktree import uncommitted_changes


console = Console()


def prompt_uncommitted_changes(
    worktree: Path,
    user_shell: str,
    shell_env: dict[str, str],
    activate_cmd: str,
) -> None:
    """If the worktree has uncommitted changes, warn and optionally re-enter shell."""
    if not sys.stdin.isatty() or not worktree.exists():
        return
    try:
        while changes := uncommitted_changes(worktree):
            console.print()
            console.print(
                "[bold yellow]\u26a0  Uncommitted changes[/bold yellow]"
            )
            console.print(
                "[dim]These will be lost when the worktree is "
                "removed.[/dim]\n"
            )
            print_change_summary(changes)
            keep_going = typer.confirm(
                "Return to shell to stash/stage/commit?",
                default=True,
            )
            if not keep_going:
                break
            console.print(
                "[dim]Returning to shell. "
                "Type 'exit' when done.[/dim]\n"
            )
            launch_shell(user_shell, shell_env, activate_cmd, worktree)
    except (EOFError, KeyboardInterrupt):
        pass


def print_change_summary(changes: str) -> None:
    """Pretty-print a short summary of porcelain status output."""
    lines = changes.splitlines()
    for line in lines[:15]:
        status, _, name = line.partition(" ")
        name = name.strip()
        color = {
            "M": "yellow", "A": "green",
            "D": "red", "??": "cyan",
        }.get(status.strip(), "white")
        console.print(f"  [{color}]{status}[/{color}] {name}")
    if len(lines) > 15:
        console.print(f"  [dim]... and {len(lines) - 15} more[/dim]")
    console.print()
