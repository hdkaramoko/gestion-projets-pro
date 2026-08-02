"""Réglages de sécurité prévus pour un futur environnement de production."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

missing_variables = [
    name
    for name in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS")
    if not os.getenv(name)
]
if missing_variables:
    raise ImproperlyConfigured(
        "Configuration de production incomplète. Variables manquantes : "
        f"{', '.join(missing_variables)}."
    )

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
