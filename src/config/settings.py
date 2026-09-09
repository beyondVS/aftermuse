from pathlib import Path

import environ
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"
env = environ.Env(
    DJANGO_SECRET_KEY=str,
    DJANGO_DEBUG=bool,
    DJANGO_ALLOWED_HOSTS=list,
    POSTGRES_DB=str,
    POSTGRES_USER=str,
    POSTGRES_PASSWORD=str,
    POSTGRES_HOST=str,
    POSTGRES_PORT=int,
    ALADIN_TTB_KEY=str,
    KAKAO_REST_API_KEY=str,
    LLM_PROVIDER=str,
    OPENAI_MODEL=str,
    OPENAI_API_KEY=str,
    OPENAI_TIMEOUT_SECONDS=float,
)

if ENV_FILE.is_file():
    env.read_env(ENV_FILE, overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
ALADIN_TTB_KEY = env("ALADIN_TTB_KEY", default="")
KAKAO_REST_API_KEY = env("KAKAO_REST_API_KEY", default="")

# fake provider는 일상 개발과 자동 테스트에서 credential 없이 동작한다.
# OpenAI adapter는 명시적으로 선택된 경우에만 빈 key를 거부한다.
LLM_PROVIDER = env("LLM_PROVIDER", default="fake")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-5.4-mini-2026-03-17")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_TIMEOUT_SECONDS = env("OPENAI_TIMEOUT_SECONDS", default=30.0)

INSTALLED_APPS = [
    "accounts.apps.AccountsConfig",
    "books.apps.BooksConfig",
    "knowledge.apps.KnowledgeConfig",
    "readings.apps.ReadingsConfig",
    "reflections.apps.ReflectionsConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"

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
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env("POSTGRES_PORT"),
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
