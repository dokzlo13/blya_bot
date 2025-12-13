from importlib.metadata import version as _v

__version__: str = _v("blya_bot")


def main() -> None:
    """Entry point for blya_bot."""
    from .main import main as _main

    _main()


__all__ = ["__version__", "main"]
