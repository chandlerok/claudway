import typer

from src.app import app


@app.callback()
def _startup(ctx: typer.Context) -> None:  # pyright: ignore[reportUnusedFunction]
    """Claudway — an isolated dev environment tailor-made for working with AI agents."""
