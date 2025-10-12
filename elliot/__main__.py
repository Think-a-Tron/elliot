"""Support `python -m elliot` by forwarding to the CLI entry point."""

from elliot.cli import main


if __name__ == "__main__":  # pragma: no cover - module entry point
    main()
