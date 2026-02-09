"""Module entrypoint: `python -m realms_launcher`."""

from __future__ import annotations

from .app import create_app
from .util.logging import configure_logging


def main() -> None:
    configure_logging()
    app = create_app()
    app.mainloop()


if __name__ == "__main__":
    main()

