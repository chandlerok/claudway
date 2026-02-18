from typing import Annotated

import typer

from src.app import app
from src.settings import (
    CONFIG_FILE,
    set_default_repo_location_with_prompt,
    validate_path,
)


@app.command()
def set_default_repo(
    path: Annotated[
        str | None,
        typer.Argument(
            help="Path to the repository. If omitted, you will be prompted.",
        ),
    ] = None,
) -> None:
    """Set the default_repo_location to a local repository path."""
    resolved = (
        validate_path(path)
        if path is not None
        else set_default_repo_location_with_prompt()
    )

    typer.echo(f"default_repo_location set to: {resolved}")
    typer.echo(f"Saved to {CONFIG_FILE}")
