from typing import Annotated

import typer

from src.app import app
from src.settings import CONFIG_FILE, save_setting


@app.command()
def set_default_command(
    command: Annotated[
        str,
        typer.Argument(help="Command to run in new sessions."),
    ],
) -> None:
    """Set the default_command to run in new sessions."""
    save_setting("default_command", command)
    typer.echo(f"default_command set to: {command}")
    typer.echo(f"Saved to {CONFIG_FILE}")
