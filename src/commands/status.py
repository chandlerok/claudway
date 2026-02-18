from rich.console import Console
from rich.table import Table

from src.app import app
from src.commands.git import detect_repo, git
from src.settings import CONFIG_FILE, ClaudwaySettings


console = Console()


@app.command()
def status() -> None:
    """Show current configuration and active worktrees."""
    settings = ClaudwaySettings.load()

    table = Table(title="Claudway Config", title_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    table.add_row("default_command", settings.default_command)
    table.add_row("config file", str(CONFIG_FILE))

    console.print(table)

    repo = detect_repo()
    if repo is None:
        console.print(
            "\n[dim]Not inside a git repository — skipping worktree listing.[/dim]"
        )
        return

    try:
        result = git(repo, "worktree", "list", "--porcelain")
    except Exception:
        return

    worktrees = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].removeprefix("refs/heads/")
        elif line == "" and current:
            worktrees.append(current)
            current = {}
    if current:
        worktrees.append(current)

    if worktrees:
        wt_table = Table(title="Active Worktrees", title_style="bold cyan")
        wt_table.add_column("Branch", style="bold")
        wt_table.add_column("Path")
        for wt in worktrees:
            wt_table.add_row(wt.get("branch", "(detached)"), wt.get("path", ""))
        console.print()
        console.print(wt_table)
