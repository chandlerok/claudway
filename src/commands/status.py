from rich.console import Console
from rich.table import Table

from src.app import app
from src.settings import CONFIG_FILE, ClaudwaySettings


console = Console()


@app.command()
def status() -> None:
    """Show current configuration."""
    settings = ClaudwaySettings.load()

    table = Table(title="Claudway Config", title_style="bold cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")

    repo = settings.default_repo_location
    table.add_row(
        "default_repo_location",
        str(repo) if repo else "[dim]not set[/dim]",
    )
    table.add_row("agent", settings.agent)
    table.add_row("config file", str(CONFIG_FILE))

    console.print(table)
