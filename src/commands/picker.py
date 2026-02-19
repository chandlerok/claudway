"""Shared fuzzy picker helpers using InquirerPy."""

import sys
from collections.abc import Sequence
from typing import Any


PICKER_STYLE_DICT = {
    "questionmark": "ansiyellow bold",
    "pointer": "ansicyan bold",
    "highlighted": "ansicyan",
    "selected": "ansigreen",
    "answer": "ansigreen",
    "input": "ansimagenta bold",
    "fuzzy_prompt": "ansimagenta bold",
    "fuzzy_info": "ansiwhite",
    "fuzzy_border": "ansiblue",
    "fuzzy_match": "ansiyellow bold",
}


def is_interactive() -> bool:
    return sys.stdin.isatty()


def fuzzy_select(
    message: str,
    choices: Sequence[str | dict[str, Any]],
) -> str:
    """Show a fuzzy-filterable picker and return the selected value.

    Each choice can be a plain string or a dict with "name" (display)
    and "value" (returned on selection) keys.
    """
    from InquirerPy import inquirer  # pyright: ignore[reportPrivateImportUsage]
    from InquirerPy.utils import (  # pyright: ignore[reportPrivateImportUsage]
        get_style,
    )

    style = get_style(PICKER_STYLE_DICT, style_override=False)

    result: str = inquirer.fuzzy(  # pyright: ignore[reportPrivateImportUsage]
        message=message,
        choices=list(choices),
        style=style,
    ).execute()
    return result
