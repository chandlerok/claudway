import tomllib
from pathlib import Path
from typing import Any

import tomli_w
import typer
from pydantic import BaseModel


CONFIG_DIR = Path.home() / ".config" / "claudway"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ClaudwaySettings(BaseModel):
    default_command: str = "claude"

    @classmethod
    def load(cls) -> "ClaudwaySettings":
        """Load settings from the TOML config file."""
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            typer.echo(f"Error: failed to parse config at {CONFIG_FILE}: {e}")
            typer.echo("Fix or remove the file, then try again.")
            raise typer.Exit(1) from None
        return cls.model_validate(data)


# Directory prefixes to skip when syncing untracked files.
# These are large/regenerable and either get symlinked (deps) or aren't needed.
SKIP_PREFIXES = (
    "node_modules/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".next/",
    ".turbo/",
    ".nuxt/",
    ".cache/",
    "dist/",
    "build/",
    "coverage/",
)

SKIP_SUFFIXES = (".sqlite3", ".db", ".pyc")
SKIP_NAMES = frozenset({".DS_Store", ".coverage"})

# Directories to symlink from the main repo into the worktree
DEP_SYMLINKS = (
    "web/node_modules",
    "mamba/venv",
)


def save_setting(key: str, value: str) -> None:
    """Persist a single setting to the TOML config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        try:
            data = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
            typer.echo(f"Warning: failed to parse config at {CONFIG_FILE}: {e}")
            typer.echo("Overwriting with new config.")
            data = {}
    data[key] = value
    CONFIG_FILE.write_bytes(tomli_w.dumps(data).encode())
