# AfterMuse Initial Project Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python 3.14, Django 6.1, PostgreSQL 18 기반의 재현 가능한 개발 환경과 공통 서버 렌더링 UI 토대를 구축한다.

**Architecture:** Django는 호스트의 uv 환경에서 실행하고 PostgreSQL만 Docker Compose로 구동한다. 초기 Django project에는 `config`만 두며 도메인 app, model, service, selector는 만들지 않는다. 공통 화면은 Django Templates와 Template Partials로 렌더링하고, 로컬에 고정한 HTMX와 Alpine.js CSP build로 점진적 향상을 검증한다.

**Tech Stack:** Python 3.14, Django 6.1, PostgreSQL 18.6, Psycopg 3.3, uv, pytest 9.1, pytest-django 4.14, Ruff 0.16, HTMX 2.0.10, Alpine.js CSP 3.17.1

**Spec:** `docs/superpowers/specs/2026-09-01-initial-project-setup-design.md`

## Global Constraints

- 내부 PK는 Django의 `BigAutoField`를 유지한다. UUID7 field나 model은 만들지 않는다.
- `accounts`, `books`, `readings`, `knowledge`, `reflections`, `credits`, `insights`, `backoffice`, `integrations`, `common` app을 만들지 않는다.
- SQLite fallback, dotenv package, Node build chain, CSS framework를 추가하지 않는다.
- 실제 `.env`와 credential은 커밋하지 않는다.
- 각 커밋 단계는 프로젝트 승인 정책에 따라 사용자 승인을 받은 뒤 실행한다.
- 검증은 PostgreSQL 18 container가 healthy인 상태에서 수행한다.

---

### Task 1: 프로젝트 도구 체인과 PostgreSQL 개발 환경 정의

**Files:**

- Create: `.python-version`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `compose.yaml`
- Modify: `.gitignore`
- Create: `tests/test_repository_contract.py`

- [ ] **Step 1: 저장소 계약을 검사하는 실패 테스트 작성**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_minor_is_pinned() -> None:
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14"


def test_example_environment_has_required_names() -> None:
    content = (ROOT / ".env.example").read_text(encoding="utf-8")
    required_names = {
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    }

    configured_names = {
        line.partition("=")[0]
        for line in content.splitlines()
        if line and not line.startswith("#")
    }

    assert required_names == configured_names


def test_compose_uses_postgresql_18_volume_layout() -> None:
    content = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "image: postgres:18.6-trixie" in content
    assert "postgres_data:/var/lib/postgresql" in content
    assert "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}" in content
```

- [ ] **Step 2: 테스트가 필수 파일 부재로 실패하는지 확인**

Run:

```powershell
uv run --with pytest pytest tests/test_repository_contract.py -q
```

Expected: `.python-version`, `.env.example` 또는 `compose.yaml`을 찾지 못해 `FAILED`.

- [ ] **Step 3: Python 및 dependency metadata 작성**

`.python-version`:

```text
3.14
```

`pyproject.toml`:

```toml
[project]
name = "aftermuse"
version = "0.1.0"
description = "독서 경험을 깊이 있는 AI 인터뷰와 독서노트로 이어주는 리플렉션 서비스"
readme = "README.md"
requires-python = ">=3.14,<3.15"
dependencies = [
    "Django~=6.1.0",
    "psycopg[binary]~=3.3.4",
]

[dependency-groups]
dev = [
    "pytest~=9.1.0",
    "pytest-django~=4.14.0",
    "ruff~=0.16.5",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
pythonpath = ["src"]
testpaths = ["tests"]
addopts = ["--strict-config", "--strict-markers"]

[tool.ruff]
line-length = 88
target-version = "py314"
extend-exclude = [".agents", ".tmp"]

[tool.ruff.lint]
select = ["B", "C4", "C90", "DJ", "E", "F", "I", "UP"]

[tool.ruff.lint.mccabe]
max-complexity = 10
```

이 저장소는 배포용 Python package가 아닌 application이므로 build backend를 만들지 않고 `[tool.uv] package = false`로 명시한다.

- [ ] **Step 4: 예시 환경과 PostgreSQL Compose 작성**

`.env.example`:

```dotenv
DJANGO_SECRET_KEY=local-development-only-change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
POSTGRES_DB=aftermuse
POSTGRES_USER=aftermuse
POSTGRES_PASSWORD=aftermuse-local
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

`compose.yaml`:

```yaml
services:
  db:
    image: postgres:18.6-trixie
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

volumes:
  postgres_data:
```

- [ ] **Step 5: `.gitignore`를 수술적으로 보완**

기존 파일 끝에 다음 항목만 추가한다.

```gitignore

# Project-local temporary artifacts
.tmp/
```

`.env`, `.venv`, `uv.lock` 정책은 기존 파일에 이미 있으므로 중복하지 않는다. `uv.lock`은 주석만 존재해 추적 가능한 상태를 유지한다.

- [ ] **Step 6: lockfile 생성과 테스트 통과 확인**

Run:

```powershell
uv lock
uv sync --locked
uv run pytest tests/test_repository_contract.py -q
```

Expected: lockfile 생성, 환경 동기화 성공, `3 passed`.

- [ ] **Step 7: 변경 검토 후 승인된 경우 커밋**

```powershell
git diff -- .python-version .env.example pyproject.toml compose.yaml .gitignore tests/test_repository_contract.py uv.lock
git add .python-version .env.example pyproject.toml compose.yaml .gitignore tests/test_repository_contract.py uv.lock
git commit -m "chore: Python과 PostgreSQL 개발 환경 구성"
```

---

### Task 2: 최소 Django project와 엄격한 환경 설정 구성

**Files:**

- Create: `src/manage.py`
- Create: `src/config/__init__.py`
- Create: `src/config/asgi.py`
- Create: `src/config/settings.py`
- Create: `src/config/urls.py`
- Create: `src/config/views.py`
- Create: `src/config/wsgi.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: 설정 계약 실패 테스트 작성**

```python
import os
import subprocess
import sys

from django.conf import settings


def test_database_uses_postgresql() -> None:
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_project_defaults_are_localized() -> None:
    assert settings.LANGUAGE_CODE == "ko-kr"
    assert settings.TIME_ZONE == "Asia/Seoul"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_invalid_debug_value_fails_at_startup() -> None:
    environment = os.environ.copy()
    environment["DJANGO_DEBUG"] = "sometimes"

    result = subprocess.run(
        [sys.executable, "src/manage.py", "check"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert "DJANGO_DEBUG" in result.stderr
```

- [ ] **Step 2: Django project 부재로 테스트 실패 확인**

Run:

```powershell
uv run --env-file .env pytest tests/test_settings.py -q
```

Expected: `config.settings` import 오류로 collection 실패.

- [ ] **Step 3: Django 진입점 파일 작성**

`src/manage.py`:

```python
#!/usr/bin/env python
import os
import sys


def main() -> None:
    """Django 관리 명령을 실행한다."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`src/config/asgi.py`와 `src/config/wsgi.py`는 각각 `DJANGO_SETTINGS_MODULE`을 `config.settings`로 지정한 뒤 Django의 표준 `get_asgi_application()`과 `get_wsgi_application()` 반환값을 `application`에 할당한다. `src/config/__init__.py`는 빈 파일로 만든다.

- [ ] **Step 4: 엄격한 단일 settings module 작성**

`src/config/settings.py`의 환경 parsing은 다음 계약을 그대로 사용한다.

```python
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
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
```

- [ ] **Step 5: URL과 최소 view 작성**

`src/config/views.py`:

```python
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """초기 설정 확인 페이지 또는 HTMX partial을 반환한다."""
    template_name = (
        "pages/home.html#setup-status"
        if request.headers.get("HX-Request") == "true"
        else "pages/home.html"
    )
    return render(request, template_name)
```

`src/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path

from config import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("setup-status/", views.home, name="setup-status"),
]
```

- [ ] **Step 6: PostgreSQL 구동, 기본 migration, 설정 테스트 확인**

Run:

```powershell
Copy-Item .env.example .env
docker compose up -d db
docker compose ps
uv run --env-file .env python src/manage.py migrate --noinput
uv run --env-file .env python src/manage.py check
uv run --env-file .env pytest tests/test_settings.py -q
```

Expected: `db`가 `healthy`, Django 기본 migration 적용, system check 무오류, `3 passed`.

- [ ] **Step 7: 변경 검토 후 승인된 경우 커밋**

```powershell
git diff -- src tests/test_settings.py
git add src/manage.py src/config tests/test_settings.py
git commit -m "feat: 최소 Django 프로젝트와 PostgreSQL 설정 추가"
```

---

### Task 3: 공통 Template, HTMX partial, Alpine.js CSP 동작 구성

**Files:**

- Create: `src/templates/base.html`
- Create: `src/templates/pages/home.html`
- Create: `src/static/css/app.css`
- Create: `src/static/js/app.js`
- Create: `src/static/vendor/htmx.min.js`
- Create: `src/static/vendor/alpine.min.js`
- Create: `src/static/vendor/HTMX-LICENSE.txt`
- Create: `src/static/vendor/ALPINE-LICENSE.txt`
- Create: `tests/test_home_page.py`

- [ ] **Step 1: 페이지, partial, CSP 계약 실패 테스트 작성**

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_contains_progressive_enhancement_assets(client) -> None:
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<main id="main-content"' in content
    assert "static/vendor/htmx.min.js" in content
    assert "static/vendor/alpine.min.js" in content
    assert 'hx-get="/setup-status/"' in content
    assert "x-data" in content


@pytest.mark.django_db
def test_htmx_request_returns_only_setup_partial(client) -> None:
    response = client.get(reverse("setup-status"), headers={"HX-Request": "true"})
    content = response.content.decode()

    assert response.status_code == 200
    assert '<section id="setup-status"' in content
    assert "<html" not in content
    assert "<main" not in content


@pytest.mark.django_db
def test_home_page_enforces_same_origin_csp(client) -> None:
    response = client.get(reverse("home"))
    policy = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy
    assert "img-src 'self' data: https:" in policy
    assert "'unsafe-eval'" not in policy
```

- [ ] **Step 2: Template 부재로 실패 확인**

Run:

```powershell
uv run --env-file .env pytest tests/test_home_page.py -q
```

Expected: `TemplateDoesNotExist: pages/home.html`로 `FAILED`.

- [ ] **Step 3: 버전 고정 browser asset과 license 내려받기**

이 단계는 외부 다운로드이므로 사용자 승인을 받은 뒤 실행한다.

```powershell
New-Item -ItemType Directory -Force src/static/vendor
Invoke-WebRequest https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js -OutFile src/static/vendor/htmx.min.js
Invoke-WebRequest https://cdn.jsdelivr.net/npm/@alpinejs/csp@3.17.1/dist/cdn.min.js -OutFile src/static/vendor/alpine.min.js
Invoke-WebRequest https://raw.githubusercontent.com/bigskysoftware/htmx/v2.0.10/LICENSE -OutFile src/static/vendor/HTMX-LICENSE.txt
Invoke-WebRequest https://raw.githubusercontent.com/alpinejs/alpine/v3.17.1/LICENSE.md -OutFile src/static/vendor/ALPINE-LICENSE.txt
```

Run:

```powershell
Get-FileHash src/static/vendor/htmx.min.js -Algorithm SHA256
Get-FileHash src/static/vendor/alpine.min.js -Algorithm SHA256
Select-String -Path src/static/vendor/htmx.min.js -Pattern "2.0.10"
Select-String -Path src/static/vendor/alpine.min.js -Pattern "3.17.1"
```

Expected: 두 파일의 SHA256이 출력되고 각 고정 버전 문자열이 발견된다. 실행 시 출력된 SHA256은 같은 커밋의 검증 기록에 남긴다.

- [ ] **Step 4: base Template과 page partial 작성**

`src/templates/base.html`:

```html
{% load static %}
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}AfterMuse{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/app.css' %}">
    <script defer src="{% static 'vendor/htmx.min.js' %}"></script>
    <script defer src="{% static 'vendor/alpine.min.js' %}"></script>
    <script defer src="{% static 'js/app.js' %}"></script>
  </head>
  <body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <a class="skip-link" href="#main-content">본문으로 건너뛰기</a>
    <header class="site-header">
      <a class="brand" href="{% url 'home' %}">AfterMuse</a>
    </header>
    {% if messages %}
      <div class="messages" aria-live="polite">
        {% for message in messages %}<p>{{ message }}</p>{% endfor %}
      </div>
    {% endif %}
    <main id="main-content" class="page-shell">
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

`src/templates/pages/home.html`:

```html
{% extends "base.html" %}

{% block title %}개발 환경 확인 · AfterMuse{% endblock %}

{% block content %}
  <section class="intro" aria-labelledby="page-title">
    <p class="eyebrow">Core MVP 기반</p>
    <h1 id="page-title">AfterMuse 개발 환경이 준비되었습니다.</h1>
    <p>도메인 앱은 각 구현 계획에 진입할 때 책임과 함께 추가합니다.</p>
  </section>

  {% partialdef setup-status inline %}
    <section id="setup-status" class="status" aria-live="polite">
      <h2>서버 렌더링 상태</h2>
      <p>Django Template Partial 응답이 정상입니다.</p>
    </section>
  {% endpartialdef setup-status %}

  <div class="actions" x-data="{ detailsOpen: false }">
    <button
      type="button"
      hx-get="{% url 'setup-status' %}"
      hx-target="#setup-status"
      hx-swap="outerHTML"
    >
      HTMX partial 다시 확인
    </button>
    <button
      type="button"
      x-on:click="detailsOpen = !detailsOpen"
      x-bind:aria-expanded="detailsOpen"
      aria-controls="alpine-status"
    >
      Alpine.js 상태 확인
    </button>
    <p id="alpine-status" x-cloak x-show="detailsOpen">
      Alpine.js CSP build가 동작합니다.
    </p>
  </div>
{% endblock %}
```

- [ ] **Step 5: 최소 CSS와 JavaScript 작성**

`src/static/js/app.js`:

```javascript
document.addEventListener("htmx:responseError", () => {
  document.body.dataset.htmxError = "true";
});
```

`src/static/css/app.css`는 다음 계약을 만족하도록 작성한다.

```css
:root {
  color-scheme: light;
  font-family: system-ui, sans-serif;
  line-height: 1.6;
  color: #20211f;
  background: #f6f5f1;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

[x-cloak] {
  display: none !important;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
}

.skip-link:focus {
  top: 1rem;
}

.site-header,
.page-shell {
  width: min(100% - 2rem, 52rem);
  margin-inline: auto;
}

.site-header {
  padding-block: 1.25rem;
}

.brand {
  color: inherit;
  font-weight: 700;
}

.page-shell {
  padding-block: clamp(2rem, 7vw, 5rem);
}

.eyebrow {
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1 {
  max-width: 18ch;
  font-size: clamp(2rem, 8vw, 4rem);
  line-height: 1.08;
}

.status {
  margin-block: 2rem;
  padding-block: 1rem;
  border-block: 1px solid #b8b7b1;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}

button {
  min-height: 2.75rem;
  padding-inline: 1rem;
  border: 1px solid currentColor;
  border-radius: 0.25rem;
  color: inherit;
  background: transparent;
  font: inherit;
  cursor: pointer;
}

a:focus-visible,
button:focus-visible {
  outline: 3px solid #315f78;
  outline-offset: 3px;
}
```

- [ ] **Step 6: page 테스트와 static 검증**

Run:

```powershell
uv run --env-file .env pytest tests/test_home_page.py -q
uv run --env-file .env python src/manage.py findstatic css/app.css vendor/htmx.min.js vendor/alpine.min.js --verbosity 0
```

Expected: `3 passed`, 세 static asset의 절대경로 출력.

- [ ] **Step 7: 개발 서버에서 Desktop/Mobile 수동 확인**

Run:

```powershell
uv run --env-file .env python src/manage.py runserver
```

확인 항목:

- 1280px와 390px viewport에서 가로 overflow가 없다.
- Tab으로 skip link와 두 button의 focus가 보인다.
- HTMX button은 전체 문서 reload 없이 `#setup-status`를 교체한다.
- Alpine.js button은 문구를 표시하고 CSP console 오류가 없다.
- JavaScript를 차단해도 제목과 setup 상태가 보인다.

- [ ] **Step 8: 변경 검토 후 승인된 경우 커밋**

```powershell
git diff -- src/templates src/static tests/test_home_page.py
git add src/templates src/static tests/test_home_page.py
git commit -m "feat: 공통 Template과 점진적 향상 기반 추가"
```

---

### Task 4: 단일 검증 명령과 개발자 문서 완성

**Files:**

- Create: `scripts/verify.py`
- Create: `tests/test_verify_script.py`
- Modify: `README.md`

- [ ] **Step 1: 검증 순서 실패 테스트 작성**

```python
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_verify_module():
    spec = importlib.util.spec_from_file_location(
        "verify", ROOT / "scripts" / "verify.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verify_commands_are_stable() -> None:
    verify = load_verify_module()

    assert verify.COMMANDS == (
        ("Django system check", ("src/manage.py", "check")),
        ("Ruff format check", ("-m", "ruff", "format", "--check", ".")),
        ("Ruff lint", ("-m", "ruff", "check", ".")),
        ("pytest", ("-m", "pytest")),
    )
```

- [ ] **Step 2: script 부재로 실패 확인**

Run:

```powershell
uv run --env-file .env pytest tests/test_verify_script.py -q
```

Expected: `scripts/verify.py`를 찾지 못해 `FAILED`.

- [ ] **Step 3: 첫 실패 종료 코드를 전달하는 검증 script 작성**

`scripts/verify.py`:

```python
import subprocess
import sys


COMMANDS = (
    ("Django system check", ("src/manage.py", "check")),
    ("Ruff format check", ("-m", "ruff", "format", "--check", ".")),
    ("Ruff lint", ("-m", "ruff", "check", ".")),
    ("pytest", ("-m", "pytest")),
)


def main() -> int:
    """품질 검사를 순서대로 실행하고 첫 실패를 반환한다."""
    for label, arguments in COMMANDS:
        print(f"\n==> {label}", flush=True)
        result = subprocess.run((sys.executable, *arguments), check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: README를 실행 중심 문서로 수술적 확장**

기존 한 줄 소개는 유지하고 아래 내용을 추가한다.

````markdown

## 개발 환경

### 요구 도구

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop 또는 Docker Engine과 Compose plugin

Python 3.14는 `.python-version`을 기준으로 uv가 관리한다. Django는 호스트에서 실행하고 PostgreSQL 18만 container로 구동한다.

### 처음 실행

```powershell
Copy-Item .env.example .env
docker compose up -d db
uv sync --locked
uv run --env-file .env python src/manage.py migrate --noinput
uv run --env-file .env python src/manage.py runserver
```

`.env.example`의 값은 로컬 개발 예시이며 운영 credential로 사용하지 않는다.

### 품질 검증

PostgreSQL container가 healthy인 상태에서 전체 검증을 실행한다.

```powershell
uv run --env-file .env python scripts/verify.py
```

개별 명령은 다음과 같다.

```powershell
uv run --env-file .env python src/manage.py check
uv run --env-file .env ruff format --check .
uv run --env-file .env ruff check .
uv run --env-file .env pytest
```

## Django 앱 생성 원칙

도메인 app은 초기 설정에서 미리 만들지 않는다. 각 MVP 구현 계획에서 실제 책임과 model 경계가 확정될 때 app, service, selector를 함께 추가한다. 내부 PK는 기본 `BigAutoField`를 사용하며 UUID7은 공개 식별자가 필요한 model에서만 별도로 검토한다.
````

- [ ] **Step 5: formatter 적용 후 전체 자동 검증**

Run:

```powershell
uv run --env-file .env ruff format .
uv run --env-file .env python scripts/verify.py
```

Expected:

- Django system check: `System check identified no issues`
- Ruff format check: exit code 0
- Ruff lint: `All checks passed!`
- pytest: 모든 테스트 통과
- `scripts/verify.py`: exit code 0

- [ ] **Step 6: 빈 PostgreSQL volume 재현성 검증**

이 단계는 기존 개발 데이터를 제거하므로 사용자에게 volume 삭제 승인을 받은 경우에만 실행한다.

```powershell
docker compose down --volumes
docker compose up -d db
docker compose ps
uv run --env-file .env python src/manage.py migrate --noinput
uv run --env-file .env python scripts/verify.py
```

Expected: 새 volume에서 `db`가 healthy가 되고 기본 migration 및 전체 검증 통과.

- [ ] **Step 7: 최종 범위 감사**

Run:

```powershell
Get-ChildItem src -Directory -Recurse | Select-Object -ExpandProperty FullName
git status --short
git diff --check
```

Expected:

- `src/config`, `src/static`, `src/templates` 외 도메인 app directory가 없다.
- `.env`와 `.tmp`는 Git status에 나타나지 않는다.
- whitespace 오류가 없다.
- 사용자가 제공한 기존 미추적 문서는 변경되지 않았다.

- [ ] **Step 8: 변경 검토 후 승인된 경우 커밋**

```powershell
git diff -- README.md scripts tests/test_verify_script.py
git add README.md scripts/verify.py tests/test_verify_script.py
git commit -m "docs: 개발 및 검증 절차 문서화"
```

---

## Final Verification Checklist

- [ ] `docker compose config`가 오류 없이 PostgreSQL 18.6 service를 출력한다.
- [ ] `docker compose ps`에서 database health가 `healthy`다.
- [ ] `uv sync --locked`가 Python 3.14 환경을 재현한다.
- [ ] 빈 database에서 `migrate --noinput`이 통과한다.
- [ ] `python scripts/verify.py`가 exit code 0으로 끝난다.
- [ ] Desktop 1280px 및 Mobile 390px에서 공통 화면을 확인한다.
- [ ] HTMX partial 교체와 Alpine.js 상태 토글이 CSP 위반 없이 동작한다.
- [ ] Django domain app과 UUID7 field가 생성되지 않았다.
- [ ] `.env`나 credential이 추적되지 않았다.
