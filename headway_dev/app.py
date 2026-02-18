import typer


app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["--help", "-h"]},
)

import headway_dev.commands.set_repo  # noqa: E402, F401
import headway_dev.commands.start  # noqa: E402, F401
import headway_dev.commands.startup  # noqa: E402, F401
