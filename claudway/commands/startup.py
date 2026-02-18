import typer

from claudway.app import app
from claudway.settings import (
    CONFIG_FILE,
    ClaudwaySettings,
    set_repo_location_with_prompt,
)


@app.callback()
def _startup(ctx: typer.Context) -> None:  # pyright: ignore[reportUnusedFunction]
    """Claudway — an isolated dev environment for working with AI agents."""
    settings = ClaudwaySettings()
    if settings.repo_location is not None:
        return

    # Allow --help and set-repo to run without the repo being configured
    if ctx.invoked_subcommand in ("set-repo-location", None):
        return

    path = set_repo_location_with_prompt()
    typer.echo(f"Repo location {path} saved to {CONFIG_FILE}\n")
