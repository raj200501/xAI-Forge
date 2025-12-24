"""Entry point for python -m xaiforge."""

from xaiforge.cli import app


def main() -> None:
    """Run the Typer CLI."""
    app()


if __name__ == "__main__":
    main()
