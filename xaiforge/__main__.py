"""Entry point for python -m xaiforge."""

from xaiforge.cli import app


def main() -> None:
    """Run the Typer CLI."""
    import sys

    if "query" in sys.argv and "--fast" in sys.argv:
        args = list(sys.argv)
        args[args.index("query")] = "query-fast"
        args = [arg for arg in args if arg != "--fast"]
        sys.argv = args
    app()


if __name__ == "__main__":
    main()
