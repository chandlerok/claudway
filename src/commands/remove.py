from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from src.app import app
from src.commands.git import detect_repo
from src.commands.picker import fuzzy_select, is_interactive
from src.commands.worktree import (
    cleanup_worktree,
    list_worktrees,
    uncommitted_changes,
)


console = Console()


@app.command()
def rm(
    name: Annotated[
        str | None,
        typer.Argument(
            help="Branch name of the persistent worktree to remove.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Remove without prompting, even with uncommitted changes.",
        ),
    ] = False,
) -> None:
    """Remove a persistent worktree."""
    repo = detect_repo()
    if repo is None:
        console.print("[red]Not inside a git repository.[/red]")
        raise typer.Exit(1)

    persistent = [wt for wt in list_worktrees(repo) if wt["type"] == "persistent"]

    if not persistent:
        console.print("[yellow]No persistent worktrees found.[/yellow]")
        raise typer.Exit(1)

    if name is not None:
        match = [wt for wt in persistent if wt.get("branch") == name]
        if not match:
            console.print(
                f"[red]No persistent worktree found for branch '{name}'.[/red]"
            )
            console.print("[dim]Available persistent worktrees:[/dim]")
            for wt in persistent:
                console.print(f"  {wt.get('branch', '(detached)')}  {wt['path']}")
            raise typer.Exit(1)
        selected = match[0]
    elif is_interactive():
        choices = [
            {
                "name": (f"{wt.get('branch', '(detached)')}  {wt['path']}"),
                "value": wt.get("branch", "(detached)"),
            }
            for wt in persistent
        ]
        picked = fuzzy_select("Select worktree to remove:", choices)
        selected = next(wt for wt in persistent if wt.get("branch") == picked)
    else:
        console.print("[red]No TTY — pass a branch name.[/red]")
        raise typer.Exit(1)

    wt_path = Path(selected["path"])
    branch = selected.get("branch", "(detached)")

    if not force and wt_path.exists():
        changes = uncommitted_changes(wt_path)
        if changes:
            console.print(
                f"[bold yellow]\u26a0  Uncommitted changes in"
                f" '{branch}':[/bold yellow]\n"
            )
            for line in changes.splitlines()[:10]:
                console.print(f"  {line}")
            if len(changes.splitlines()) > 10:
                extra = len(changes.splitlines()) - 10
                console.print(f"  [dim]... and {extra} more[/dim]")
            console.print()
            if not typer.confirm("Remove anyway?", default=False):
                console.print("[dim]Aborted.[/dim]")
                raise typer.Exit(1)

    console.print(f"[yellow]Removing worktree for '{branch}' ...[/yellow]")
    cleanup_worktree(repo, wt_path)
    console.print(
        f"[green]\u2713[/green] Removed persistent worktree for [bold]{branch}[/bold]"
    )
