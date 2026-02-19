from rich.console import Console
from rich.table import Table

from src.app import app
from src.commands.git import detect_repo
from src.commands.worktree import list_worktrees
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

    worktrees = list_worktrees(repo)

    if worktrees:
        wt_table = Table(title="Active Worktrees", title_style="bold cyan")
        wt_table.add_column("Branch", style="bold")
        wt_table.add_column("Type")
        wt_table.add_column("Path")

        type_styles = {
            "main": "green",
            "persistent": "cyan",
            "temporary": "yellow",
        }

        for wt in worktrees:
            wt_type = wt.get("type", "unknown")
            style = type_styles.get(wt_type, "dim")
            wt_table.add_row(
                wt.get("branch", "(detached)"),
                f"[{style}]{wt_type}[/{style}]",
                wt.get("path", ""),
            )
        console.print()
        console.print(wt_table)
