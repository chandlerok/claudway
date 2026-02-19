import typer

from src.app import app


@app.callback()
def _startup(ctx: typer.Context) -> None:  # pyright: ignore[reportUnusedFunction]
    """Claudway — isolated dev environments powered by git worktrees, tailor-made for AI agents."""
