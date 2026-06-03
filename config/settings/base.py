"""
Shared base settings — imported by dev.py and prod.py.

Everything that varies by environment (secret key, DEBUG, allowed hosts, db
URL, CORS origins) is read from environment variables via django-environ so
nothing per-machine ever lands in version control. Defaults are chosen so a
fresh clone + `pip install -r requirements.txt` + `python manage.py migrate`
runs without any .env at all.
"""

from pathlib import Path

import environ

# Project root (the directory that contains manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Environment ------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:5173', 'http://127.0.0.1:5173']),
)
# Load .env if present; missing file is fine in CI/prod where vars are injected.
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='dev-insecure-change-me')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('DJANGO_ALLOWED_HOSTS')

# --- Apps -------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'anymail',  # HTTP-API email (Brevo) — used where SMTP is blocked (free PythonAnywhere).
    # SimpleJWT doesn't need to be in INSTALLED_APPS — its views are imported directly.
]

LOCAL_APPS = [
    # Order is dependency-aware: things with FKs come AFTER their targets so
    # makemigrations resolves cleanly on a fresh database. Ownership lives in
    # .github/CODEOWNERS — change it there, not here.
    'core',
    'accounts',
    'specialties',
    'doctors',
    'appointments',
    'payments',
    'ratings',
    'dashboard',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware -------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # CORS must sit ABOVE CommonMiddleware to short-circuit preflight requests.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# --- Database ---------------------------------------------------------------
# Defaults to SQLite so a fresh clone just works. Set DATABASE_URL=postgres://…
# in .env to switch to Postgres (the psycopg driver is already in requirements).
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
    ),
}

# --- Auth -------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- I18n / Time ------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static / Media ---------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DRF + JWT --------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

from datetime import timedelta  # noqa: E402  (kept local to its config block)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- CORS -------------------------------------------------------------------
# Locked down by default — only origins listed in CORS_ALLOWED_ORIGINS may call us.
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# Public base URL of the React app — used to build links inside emails
# (e.g. the "rate your doctor" link).
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:5173')

# --- Email ------------------------------------------------------------------
# Gmail SMTP via an app password. With no credentials we fall back to the
# console backend, so dev/CI never tries to actually send. Notification sends
# are best-effort and never break a request (see core.emails).
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
# Google shows the app password as 4 space-separated groups — strip the spaces
# so it works whether the admin pastes it with or without them.
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='').replace(' ', '')
DEFAULT_FROM_EMAIL = env(
    'DEFAULT_FROM_EMAIL',
    default=(f'useCare <{EMAIL_HOST_USER}>' if EMAIL_HOST_USER else 'useCare <no-reply@usecare.test>'),
)
# Brevo (HTTP API) is preferred where outbound SMTP is blocked — e.g. free
# PythonAnywhere, whose outbound whitelist is HTTPS-only and never lists SMTP
# hosts. Set BREVO_API_KEY to send over HTTPS via Anymail instead. Priority:
# Brevo HTTP API -> Gmail SMTP -> console (prints, never sends). Same send code
# in core.emails either way — send_mail is backend-agnostic.
BREVO_API_KEY = env('BREVO_API_KEY', default='')
ANYMAIL = {'BREVO_API_KEY': BREVO_API_KEY}

if BREVO_API_KEY:
    EMAIL_BACKEND = 'anymail.backends.brevo.EmailBackend'
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
