"""Configurações principais do backend Referencial Curricular."""

from __future__ import annotations

import os
from django.core.exceptions import ImproperlyConfigured
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    REFERENCIAL_SECRET_KEY=(str, "unsafe-secret"),
    REFERENCIAL_DATABASE_URL=(str, ""),
    REFERENCIAL_REDIS_URL=(str, "redis://127.0.0.1:6379/0"),
    REFERENCIAL_DATABASE_SSLMODE=(str, "require"),
    MEDIA_BACKEND=(str, "local"),
    MEDIA_ROOT_PATH=(str, ""),
    ALLOWED_HOSTS=(str, "localhost,127.0.0.1"),
    TIME_ZONE=(str, "America/Maceio"),
    LANGUAGE_CODE=(str, "pt-br"),
    DEFAULT_THROTTLE_RATES_USER=(str, "1000/day"),
    DEFAULT_THROTTLE_RATES_ANON=(str, "100/day"),
    DEFAULT_THEME=(str, "default"),
    DEFAULT_EXPORT_PLUGIN=(str, "default"),
    DEFAULT_SYNTHESIS_PLUGIN=(str, "default"),
    DEFAULT_HOOK_PLUGIN=(str, "default"),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 60),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    CSRF_TRUSTED_ORIGINS=(str, "http://localhost:5173,http://127.0.0.1:5173"),
)

if (env_file := BASE_DIR / ".env").exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("REFERENCIAL_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env("CSRF_TRUSTED_ORIGINS").split(",") if origin.strip()]

# Configurações de CSRF adicionais para desenvolvimento local
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ])

if render_host := os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    # Render injeta o hostname do deploy via env var
    if render_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(render_host)
    render_origin = f"https://{render_host}"
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

# Configurações de CSRF para permitir acesso do JavaScript
CSRF_COOKIE_HTTPONLY = False  # Permite que JavaScript acesse o cookie CSRF
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_USE_SESSIONS = False  # Usa cookies em vez de sessões para CSRF

# Configurações de CORS para desenvolvimento
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
    SESSION_COOKIE_SAMESITE = 'Lax'

SITE_ID = 1

# Aplicativos instalados
INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.forms",

    # Terceiros
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "channels",
    "storages",
    "django_celery_beat",
    "corsheaders",

    # Apps internos
    "core",
    "curriculum",
    "workshop",
    "dynamicforms",
    "courses",
    "documents",
    "bank",
    "analytics",
    "exports",
    "reviews",
    "comments",
    "notifications",
    "library",
    "consultas",
    "api",
    "sockets",
    "tasks",
    "meb",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ClienteScopeMiddleware",
]

# Permite embed em iframe no mesmo domínio (necessário para exibir PDFs via <iframe>)
X_FRAME_OPTIONS = "SAMEORIGIN"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Channels / Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REFERENCIAL_REDIS_URL")],
        },
    }
}

# -------------------------
# Banco de dados (robusto)
# -------------------------
def _sanitize_db_url(raw: str) -> str:
    """
    Corrige URLs malformadas como 'referencial_dbpostgresql://...' mantendo a partir de 'postgres...'.
    Também aceita 'postgres://' e 'postgresql://', 'sqlite:///'.
    """
    if not raw:
        return ""
    s = raw.strip()

    # Se já começa certo, retorna
    if s.startswith(("postgres://", "postgresql://", "sqlite://")):
        return s

    # Se contiver 'postgres' em alguma posição > 0, corta dali pra frente
    idx = s.find("postgres")
    if idx > 0:
        return s[idx:]

    # Último recurso: retorna original (pode ser NAME puro para sqlite)
    return s

def _parse_database_url(url: str) -> dict:
    """
    Parse manual da URL de DB para um dict em formato Django DATABASES['default'].
    - Suporta postgresql e sqlite.
    - Força SSL no PostgreSQL (sslmode=require).
    """
    if not url:
        # Default: SQLite local
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(BASE_DIR / "db.sqlite3"),
        }

    url = _sanitize_db_url(url)
    parsed = urlparse(url)

    # SQLite
    if parsed.scheme.startswith("sqlite"):
        # sqlite:///absolute/path.sqlite3  -> parsed.path
        # sqlite:///:memory:                -> ":memory:"
        path = parsed.path or ""
        if path in ("", "/", "/:memory:"):
            name = ":memory:"
        else:
            name = path.lstrip("/")
            # caminho absoluto
            if not name.startswith(("/", "\\")):
                name = str(BASE_DIR / name)
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }

    # Postgres
    if parsed.scheme in ("postgres", "postgresql"):
        name = parsed.path.lstrip("/") or ""
        qs = parse_qs(parsed.query or "")
        sslmode = qs.get("sslmode", [env("REFERENCIAL_DATABASE_SSLMODE")])[0]
        if (parsed.hostname in ("localhost", "127.0.0.1")) and sslmode == "require":
            sslmode = "disable"
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(name),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or "") if parsed.password else "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or "5432"),
            "OPTIONS": {
                "sslmode": sslmode,
                "options": "-c search_path=public",
            },
            # Em ambiente de migração/ajuste, zero ajuda a evitar conexões penduradas
            "CONN_MAX_AGE": 0,
        }

    # Fallback: trata como sqlite NAME
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }

RAW_DB_URL = env("REFERENCIAL_DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
DATABASES = {
    "default": _parse_database_url(RAW_DB_URL),
}

# Autenticação
AUTH_USER_MODEL = "core.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internacionalização
LANGUAGE_CODE = env("LANGUAGE_CODE")
LANGUAGES = [
    ("pt-br", "Português (Brasil)"),
    ("en-us", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

# Arquivos estáticos e mídia
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(
    env("MEDIA_ROOT_PATH")
    or ("/opt/render/project/src/media" if os.getenv("RENDER") else BASE_DIR / "media")
).resolve()

MEDIA_BACKEND = env("MEDIA_BACKEND")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

if MEDIA_BACKEND == "s3":
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
    if not AWS_STORAGE_BUCKET_NAME:
        raise ImproperlyConfigured("Defina AWS_STORAGE_BUCKET_NAME para usar MEDIA_BACKEND=s3.")
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    }
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "api.v1.throttling.LoggingUserRateThrottle",
        "api.v1.throttling.LoggingAnonRateThrottle",
        "api.v1.throttling.LoggingScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": env("DEFAULT_THROTTLE_RATES_USER"),
        "anon": env("DEFAULT_THROTTLE_RATES_ANON"),
        "comments-write": "20/min",
        "reviews-write": "20/min",
        "library-write": "20/min",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Celery
CELERY_BROKER_URL = env("REFERENCIAL_REDIS_URL")
CELERY_RESULT_BACKEND = env("REFERENCIAL_REDIS_URL")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "cleanup-soft-deleted": {
        "task": "tasks.cleanup.purge_soft_deleted",
        "schedule": 3600,
    },
    "cleanup-export-jobs": {
        "task": "tasks.cleanup.cleanup_exports",
        "schedule": 3600,
    },
}
CELERY_TASK_ALWAYS_EAGER = env.bool("REFERENCIAL_CELERY_ALWAYS_EAGER", default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = True

# Logging básico para auditoria
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Plugins padrão
DEFAULT_THEME = env("DEFAULT_THEME")
DEFAULT_EXPORT_PLUGIN = env("DEFAULT_EXPORT_PLUGIN")
DEFAULT_SYNTHESIS_PLUGIN = env("DEFAULT_SYNTHESIS_PLUGIN")
DEFAULT_HOOK_PLUGIN = env("DEFAULT_HOOK_PLUGIN")

# Internacionalização de formulários / admin
USE_L10N = True
