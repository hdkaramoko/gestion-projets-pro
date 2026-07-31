#!/usr/bin/env python
"""Point d'entrée des commandes d'administration Django."""

import os
import sys


def main() -> None:
    """Exécute une commande Django avec les réglages de développement par défaut."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django est introuvable. Exécutez d'abord `uv sync`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
