import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.app import app
from src.settings import CONFIG_FILE, ClaudwaySettings


console = Console()


def _list_worktrees(repo: Path) -> list[tuple[str, str]]:
    """Return a list of (path, branch) tuples for all worktrees in the repo."""
    result = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    worktrees: list[tuple[str, str]] = []
    path = ""
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line.startswith("branch "):
            branch = line.removeprefix("branch refs/heads/")
            worktrees.append((path, branch))
        elif line == "bare":
            worktrees.append((path, "(bare)"))
    return worktrees


@app.command()
def status() -> None:
    """Show current configuration and active worktrees."""
    settings = ClaudwaySettings.load()

    table = Table(title="Claudway Config", title_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    repo = settings.default_repo_location
    table.add_row(
        "default_repo_location",
        str(repo) if repo else "[dim]not set[/dim]",
    )
    table.add_row("default_command", settings.default_command)
    table.add_row("config file", str(CONFIG_FILE))

    console.print(table)

    if not repo:
        return

    worktrees = _list_worktrees(Path(repo))
    if not worktrees:
        return

    console.print()
    wt_table = Table(title="Git Worktrees", title_style="bold cyan")
    wt_table.add_column("Path", style="dim")
    wt_table.add_column("Branch", style="bold")

    for path, branch in worktrees:
        wt_table.add_row(path, branch)

    console.print(wt_table)
