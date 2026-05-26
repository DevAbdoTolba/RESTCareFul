"""
Production settings. Loaded explicitly via DJANGO_SETTINGS_MODULE=config.settings.prod.

Anything secret / environment-specific MUST come from env vars — never hardcoded.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Fail loudly if these aren't provided in prod.
SECRET_KEY = env('DJANGO_SECRET_KEY')  # noqa: F405
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')  # noqa: F405

# Behind a TLS-terminating proxy.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days; raise to a year once stable
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
