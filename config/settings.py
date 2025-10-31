"""Configurações principais do backend Referencial Curricular."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    REFERENCIAL_SECRET_KEY=(str, "unsafe-secret"),
    REFERENCIAL_DATABASE_URL=(str, ""),
    REFERENCIAL_REDIS_URL=(str, "redis://127.0.0.1:6379/0"),
    MEDIA_BACKEND=(str, "local"),
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

# Configurações de CSRF para desenvolvimento
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

if render_host := os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    # Render injects the deployment hostname via environment variable
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
    "exports",
    "reviews",
    "comments",
    "notifications",
    "library",
    "api",
    "sockets",
    "tasks",
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

# Banco de dados
# Usamos env.db() para analisar a URL e configurar a conexão
DATABASE_URL = env("REFERENCIAL_DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")

DATABASES = {
    # O método 'env.db()' faz o parse (análise) da URL lida da variável de ambiente
    # 'REFERENCIAL_DATABASE_URL' e retorna o dicionário de configuração do Django.
    "default": env.db(
        "REFERENCIAL_DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Garantimos que, se for SQLite, configuramos corretamente o engine
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    # Se for SQLite, o nome é o caminho do arquivo
    DATABASES["default"]["NAME"] = str(BASE_DIR / "db.sqlite3")
elif DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    # Se for PostgreSQL, podemos adicionar opções de conexão.
    
    # 🚨 PONTO CRÍTICO: Se você estiver usando django-environ e ele analisou corretamente a URL,
    # o campo 'NAME' JÁ deve ser 'referencial_db'. 
    # O bloco original abaixo é para adicionar opções, não para corrigir o NAME.
    
    DATABASES["default"].setdefault("OPTIONS", {})
    # Define o search_path explicitamente para evitar problemas de visibilidade de tabelas
    DATABASES["default"]["OPTIONS"]["options"] = "-c search_path=public"
    
    # Se, mesmo assim, o erro persistir, o problema está na variável de ambiente.
    # Você pode forçar a correção se souber que o nome REAL do banco é referencial_db:
    # DATABASES["default"]["NAME"] = "referencial_db" 

# Durante o ajuste do ambiente, evitamos reuso de conexões para garantir
# que alterações de schema sejam percebidas imediatamente.
DATABASES["default"]["CONN_MAX_AGE"] = 0

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
MEDIA_ROOT = BASE_DIR / "media"

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
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    }
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
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
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
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
