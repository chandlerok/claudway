import typer

from headway_dev.app import app
from headway_dev.settings import (
    CONFIG_FILE,
    HeadwaySettings,
    set_repo_location_with_prompt,
)


@app.callback()
def _startup(ctx: typer.Context) -> None:  # pyright: ignore[reportUnusedFunction]
    """Headway Dev CLI — an isolated dev environment for working with AI agents."""
    settings = HeadwaySettings()
    if settings.repo_location is not None:
        return

    # Allow --help and set-repo to run without the repo being configured
    if ctx.invoked_subcommand in ("set-repo-location", None):
        return

    path = set_repo_location_with_prompt()
    typer.echo(f"Repo location {path} saved to {CONFIG_FILE}\n")
