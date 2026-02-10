from typing import Annotated

import typer


app = typer.Typer(
    invoke_without_command=True,
    no_args_is_help=True,
    context_settings={"help_option_names": ["--help", "-h"]},
)


@app.command()
def hello(
    name: Annotated[str, typer.Argument()],
    formal: Annotated[bool, typer.Option(help="use a formal tone")] = False,
) -> None:
    if formal:
        print(f"Good day {name}")
    else:
        print(f"Hello {name}")


@app.command()
def goodbye(
    name: Annotated[str, typer.Argument()],
    formal: Annotated[bool, typer.Option(help="use a formal tone")] = False,
) -> None:
    if formal:
        print(f"Good morrow {name}")
    else:
        print(f"See ya {name}!")


if __name__ == "__main__":
    app()
