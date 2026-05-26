"""
Local-development settings — used by manage.py / runserver by default.
"""

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['*']

# Friendly errors when a teammate forgets to set DJANGO_SECRET_KEY in .env.
SECRET_KEY = SECRET_KEY or 'dev-insecure-change-me'  # noqa: F405
