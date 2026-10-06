"""Configurações do microsserviço de boletim."""

import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-secret-key-not-for-production"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
]

_POOL_OPTIONS: dict[str, Any] = {
    "POOL_SIZE": int(os.environ.get("DB_POOL_SIZE", "5")),
    "MAX_OVERFLOW": 0,
    "POOL_TIMEOUT": 30,
    "POOL_RECYCLE": 1800,
    "PRE_PING": True,
}


def _parse_db_url(url: Any) -> dict[str, Any]:
    """Converte uma URL PostgreSQL em configuração de banco do Django."""
    if not url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
    if isinstance(url, bytes):
        url = url.decode("utf-8")
    parsed = urllib.parse.urlparse(str(url))
    return {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "postgres",
        "PASSWORD": parsed.password or "postgres",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "POOL_OPTIONS": _POOL_OPTIONS,
    }


INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.core.apps.CoreConfig",
    "apps.boletim.apps.BoletimConfig",
]

MIDDLEWARE = [
    "sme_sidecar_sdk.integrations.django.ObservabilityMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": _parse_db_url(os.environ.get("URL_BANCO_BOLETIM", ""))}
_EM_TESTE = "test" in sys.argv or os.environ.get(
    "USE_SQLITE_TEST", "False"
).lower() in ("true", "1")
if _EM_TESTE:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

KEYDB_URL = os.environ.get("KEYDB_URL", "")
KEYDB_ENABLED = bool(KEYDB_URL and not _EM_TESTE)
CACHE_BOLETIM_TTL = int(os.environ.get("CACHE_BOLETIM_TTL", "1800"))
CACHE_ABRANGENCIA_TTL = int(os.environ.get("CACHE_ABRANGENCIA_TTL", "300"))
CACHE_LOCK_TTL = int(os.environ.get("CACHE_LOCK_TTL", "30"))
CACHE_LOCK_WAIT_TIMEOUT = float(os.environ.get("CACHE_LOCK_WAIT_TIMEOUT", "2"))
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "keydb": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": KEYDB_URL,
            "KEY_FUNCTION": "apps.core.cache.preservar_chave_cache",
        }
        if KEYDB_ENABLED
        else {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    ),
}

API_KEY_HEADER = os.environ.get("API_KEY_HEADER", "x-api-key")
API_KEY = os.environ.get("API_KEY", "dev-key-default")
PEDAGOGICO_API_URL = os.environ.get("PEDAGOGICO_API_URL", "").rstrip("/")
PEDAGOGICO_API_KEY = os.environ.get("PEDAGOGICO_API_KEY", "")
PEDAGOGICO_API_KEY_HEADER = os.environ.get(
    "PEDAGOGICO_API_KEY_HEADER", "x-api-eol-key"
)
BEARER_TOKEN_SIGNING_KEY = os.environ.get(
    "BEARER_TOKEN_SIGNING_KEY", ""
).replace("\\n", "\n")
BEARER_TOKEN_ISSUER = os.environ.get("BEARER_TOKEN_ISSUER", "")
BEARER_TOKEN_AUDIENCE = os.environ.get("BEARER_TOKEN_AUDIENCE", "")
BEARER_TOKEN_ALGORITHMS = [
    algorithm.strip()
    for algorithm in os.environ.get("BEARER_TOKEN_ALGORITHMS", "HS256").split(
        ","
    )
    if algorithm.strip()
]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.ApiKeyAuthentication",
        "apps.core.authentication.BearerTokenAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SME SGP Boletim MS API",
    "DESCRIPTION": "Microsserviço de boletim do SGP",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

TEST_RUNNER = "config.test_runner.BoletimTestRunner"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True
USE_I18N = True
SILENCED_SYSTEM_CHECKS = ["models.W047"]
