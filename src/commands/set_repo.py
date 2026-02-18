from typing import Annotated

import typer

from src.app import app
from src.settings import (
    CONFIG_FILE,
    set_repo_location_with_prompt,
    validate_path,
)


@app.command()
def set_repo_location(
    path: Annotated[
        str | None,
        typer.Argument(
            help="Path to the Headway repository. If omitted, you will be prompted.",
        ),
    ] = None,
) -> None:
    """Set the CLAUDWAY_REPO_LOCATION to a local repository path."""
    resolved = (
        validate_path(path) if path is not None else set_repo_location_with_prompt()
    )

    typer.echo(f"CLAUDWAY_REPO_LOCATION set to: {resolved}")
    typer.echo(f"Saved to {CONFIG_FILE}")
