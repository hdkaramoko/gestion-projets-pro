"""Réglages destinés au développement local."""

import os

from .base import *  # noqa: F403

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]  # noqa: F405

# En local et pendant les tests, les fichiers statiques sont servis directement
# depuis leurs sources et ne nécessitent donc pas de manifeste `collectstatic`.
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
}
