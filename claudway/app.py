import typer


app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["--help", "-h"]},
)

import claudway.commands.set_repo  # noqa: E402
import claudway.commands.start  # noqa: E402
import claudway.commands.startup  # noqa: E402, F401
