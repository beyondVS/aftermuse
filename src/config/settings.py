import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent


def required_environment(name: str) -> str:
    """필수 환경변수를 공백이 아닌 값으로 반환한다."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"필수 환경변수가 없습니다: {name}")
    return value


def boolean_environment(name: str) -> bool:
    """명시적으로 허용한 문자열만 boolean으로 변환한다."""
    value = required_environment(name).lower()
    mapping = {"0": False, "1": True, "false": False, "true": True}
    try:
        return mapping[value]
    except KeyError as error:
        raise ImproperlyConfigured(
            f"{name}은 true, false, 1, 0 중 하나여야 합니다."
        ) from error


SECRET_KEY = required_environment("DJANGO_SECRET_KEY")
DEBUG = boolean_environment("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    host.strip()
    for host in required_environment("DJANGO_ALLOWED_HOSTS").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required_environment("POSTGRES_DB"),
        "USER": required_environment("POSTGRES_USER"),
        "PASSWORD": required_environment("POSTGRES_PASSWORD"),
        "HOST": required_environment("POSTGRES_HOST"),
        "PORT": required_environment("POSTGRES_PORT"),
    }
}

PASSWORD_VALIDATOR_MODULE = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{PASSWORD_VALIDATOR_MODULE}.UserAttributeSimilarityValidator"},
    {"NAME": f"{PASSWORD_VALIDATOR_MODULE}.MinimumLengthValidator"},
    {"NAME": f"{PASSWORD_VALIDATOR_MODULE}.CommonPasswordValidator"},
    {"NAME": f"{PASSWORD_VALIDATOR_MODULE}.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_CSP = {
    "connect-src": [CSP.SELF],
    "default-src": [CSP.SELF],
    "font-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:", "https:"],
    "script-src": [CSP.SELF],
    "style-src": [CSP.SELF],
}
