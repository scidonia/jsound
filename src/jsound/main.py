"""Main entry point for jsound CLI."""

import typer
from .cli.commands import app


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
