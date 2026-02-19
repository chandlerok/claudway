import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from src.app import app
from src.commands.git import detect_repo
from src.commands.picker import fuzzy_select, is_interactive
from src.commands.shell import build_shell_env, launch_shell
from src.commands.worktree import list_worktrees


console = Console()

_SWITCHABLE_TYPES = ("main", "persistent", "temporary")


def _format_choice(wt: dict[str, str]) -> dict[str, str]:
    """Build a fuzzy picker choice with plain-text display."""
    branch = wt.get("branch", "(detached)")
    wt_type = wt["type"]
    label = f"{branch}  ({wt_type})  {wt['path']}"
    return {"name": label, "value": wt["path"]}


@app.command()
def switch(
    name: Annotated[
        str | None,
        typer.Argument(help="Branch name of the worktree to switch to."),
    ] = None,
) -> None:
    """Open a shell in an existing worktree."""
    repo = detect_repo()
    if repo is None:
        console.print("[red]Not inside a git repository.[/red]")
        raise typer.Exit(1)

    switchable = [wt for wt in list_worktrees(repo) if wt["type"] in _SWITCHABLE_TYPES]

    if not switchable:
        console.print("[yellow]No worktrees found.[/yellow]")
        console.print("[dim]Create one with: cw go <branch>[/dim]")
        raise typer.Exit(1)

    if name is not None:
        match = [wt for wt in switchable if wt.get("branch") == name]
        if not match:
            console.print(f"[red]No worktree found for branch '{name}'.[/red]")
            console.print("[dim]Available worktrees:[/dim]")
            for wt in switchable:
                console.print(f"  {wt.get('branch', '(detached)')}  ({wt['type']})")
            raise typer.Exit(1)
        selected = match[0]
    elif is_interactive():
        choices = [_format_choice(wt) for wt in switchable]
        picked = fuzzy_select("Select a worktree:", choices)
        selected = next(wt for wt in switchable if wt["path"] == picked)
    else:
        console.print("[red]No TTY — pass a branch name.[/red]")
        raise typer.Exit(1)

    wt_path = Path(selected["path"])
    if not wt_path.exists():
        console.print(f"[red]Worktree directory does not exist: {wt_path}[/red]")
        raise typer.Exit(1)

    branch = selected.get("branch", "(detached)")

    if selected["type"] == "temporary":
        console.print(
            "\n[yellow]Warning: This is a temporary worktree. It will"
            " be deleted when the original session exits.[/yellow]"
        )
        console.print(
            "[dim]Tip: Use 'cw go -p <branch>' to create persistent"
            " worktrees that won't be cleaned up.[/dim]"
        )

    console.print(f"\n[bold green]Switching to:[/bold green] {branch}")
    console.print(f"[dim]{wt_path}[/dim]")
    console.print("[dim]Type 'exit' to leave.[/dim]\n")

    user_shell = os.environ.get("SHELL", "/bin/sh")
    shell_env = build_shell_env()
    launch_shell(user_shell, shell_env, wt_path)
