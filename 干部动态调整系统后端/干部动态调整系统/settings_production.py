import os

from .settings import *  # noqa: F401,F403


def _csv(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = _csv("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _csv("CSRF_TRUSTED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

ONLYOFFICE_DOCUMENT_SERVER = os.environ["ONLYOFFICE_DOCUMENT_SERVER"]
ONLYOFFICE_BACKEND_PUBLIC_URL = os.environ["ONLYOFFICE_BACKEND_PUBLIC_URL"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
