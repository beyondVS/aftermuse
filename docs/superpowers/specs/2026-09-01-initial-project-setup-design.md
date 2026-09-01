# AfterMuse Initial Project Setup Design

## 목적

AfterMuse의 2주 Core MVP 구현을 시작할 수 있도록 `IMP-001`부터 `IMP-004`까지의 개발 기반을 구성한다. 초기 설정은 실행 가능성, 재현성, 기본 품질 검증과 공통 웹 UI 토대만 제공하며, 실제 Django 앱과 도메인 모델은 각 구현 작업에 진입할 때 추가한다.

## 성공 기준

- Python 3.14와 Django 6.1 조합으로 프로젝트가 실행된다.
- PostgreSQL 18 개발 데이터베이스가 Docker Compose로 구동된다.
- 빈 데이터베이스에서 Django 기본 migration을 재현할 수 있다.
- 단일 명령으로 formatter, linter, test와 Django system check를 실행할 수 있다.
- 공통 Django Template이 Desktop과 Mobile에서 정상 렌더링된다.
- HTMX 요청과 Alpine.js의 최소 동작을 로컬 정적 자산으로 확인할 수 있다.
- 비밀값 없이 저장소를 복제한 개발자가 `.env.example`을 기준으로 환경을 재현할 수 있다.

## 확정 기술

- Python 3.14 최신 patch release
- Django 6.1 최신 patch release
- PostgreSQL 18 최신 patch release
- Psycopg 3
- uv 기반 Python 및 의존성 관리
- pytest, pytest-django 기반 테스트
- Ruff 기반 format 및 lint
- Django Templates, HTMX, Alpine.js
- Docker Compose는 PostgreSQL에만 사용

`pyproject.toml`은 `requires-python = ">=3.14,<3.15"`로 제한한다. `.python-version`은 `3.14`를 지정해 uv가 해당 minor series의 최신 patch를 사용하게 한다. 직접 의존성은 호환 가능한 minor 범위로 선언하고, 실제 설치 버전은 `uv.lock`으로 고정한다.

## 런타임 구조

```text
Host
├─ uv가 Python 3.14와 .venv 관리
├─ Django 개발 서버
└─ pytest / Ruff / Django management commands

Docker Compose
└─ PostgreSQL 18
```

Django 앱까지 컨테이너에 넣지 않는다. 이 구성은 Windows의 bind mount와 디버깅 복잡성을 피하면서 데이터베이스 버전 차이는 격리한다.

## 초기 파일 구조

```text
.
├─ .env.example
├─ .gitignore
├─ .python-version
├─ compose.yaml
├─ pyproject.toml
├─ uv.lock
├─ README.md
├─ scripts/
│  └─ verify.py
├─ src/
│  ├─ manage.py
│  ├─ config/
│  │  ├─ __init__.py
│  │  ├─ asgi.py
│  │  ├─ settings.py
│  │  ├─ urls.py
│  │  └─ wsgi.py
│  ├─ static/
│  │  ├─ css/app.css
│  │  ├─ js/app.js
│  │  └─ vendor/
│  │     ├─ htmx.min.js
│  │     ├─ alpine.min.js
│  │     └─ third-party license files
│  └─ templates/
│     ├─ base.html
│     └─ pages/home.html
└─ tests/
   ├─ conftest.py
   └─ test_project_setup.py
```

초기 설정에서는 `accounts`, `books`, `readings`, `knowledge`, `reflections`, `credits`, `insights`, `backoffice`, `integrations`, `common` 앱을 만들지 않는다. 해당 앱은 연결된 `IMP` 작업에서 실제 책임과 함께 생성한다. 임시 service, selector, model 파일도 만들지 않는다.

## Django 설정

초기 단계에서는 단일 `config/settings.py`를 사용한다. 배포 환경이 확정되기 전에 설정 모듈을 여러 파일로 나누지 않는다.

환경변수는 다음으로 제한한다.

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

`.env.example`에는 로컬 개발용 비밀이 아닌 예시값만 기록한다. 실제 `.env`는 Git에서 제외한다. `django-environ`이 저장소 루트의 `.env`를 자동으로 읽되, 배포 환경에서 주입한 OS 환경변수를 우선한다.

기본 설정 원칙은 다음과 같다.

- `LANGUAGE_CODE = "ko-kr"`
- `TIME_ZONE = "Asia/Seoul"`
- `USE_I18N = True`
- `USE_TZ = True`
- PostgreSQL 연결만 지원하고 SQLite fallback은 제공하지 않는다.
- 정적 파일은 `src/static`에서 로드한다.
- 프로젝트 공통 Template은 `src/templates`에서 로드한다.
- 배포 설정과 운영용 static serving 도구는 배포 작업까지 미룬다.

## 식별자 정책

- 내부 PK는 Django 기본 `BigAutoField`를 사용한다.
- PostgreSQL에서는 `bigint` PK와 FK로 저장한다.
- UUID7을 모든 모델의 PK로 강제하지 않는다.
- 공개 URL, 외부 API 또는 분산 생성 요구가 생긴 모델에만 별도의 `public_id`를 추가할 수 있다.
- Python 3.14 표준 라이브러리의 `uuid.uuid7()`을 우선 사용하며 별도 UUID 패키지를 추가하지 않는다.
- UUID7 필드는 실제 요구가 생긴 앱의 설계에서 결정한다.

## Template, HTMX, Alpine.js

HTMX와 Alpine.js는 정확한 버전의 browser build를 `src/static/vendor`에 저장한다. CDN 런타임 의존성과 Node 빌드 체인은 도입하지 않는다. 각 자산의 license 고지를 함께 보존한다.

`base.html`은 다음 책임만 가진다.

- 공통 HTML metadata와 viewport
- 공통 CSS 및 로컬 vendor script 로드
- 접근 가능한 skip link와 main landmark
- message 영역과 content block
- HTMX CSRF header 설정

`pages/home.html`은 초기 설정 확인용 임시 진입 화면이다. 최종 제품 화면으로 취급하지 않으며 첫 실제 화면 구현 시 교체할 수 있다.

Alpine.js는 작은 browser-only 상태 확인에만 사용한다. HTMX는 same-origin endpoint의 HTML partial 교체만 확인한다. Django 6.1 Template Partials를 사용해 별도 임시 app 없이 setup 확인용 partial을 렌더링한다.

## 기본 Visual Direction

초기 공통 스타일은 UI/UX Guide의 다음 원칙만 토대로 한다.

- Neutral palette
- 읽기 쉬운 typography와 충분한 line-height
- Desktop과 Mobile에 대응하는 제한된 content width
- 명확한 focus state와 색상 외 상태 표현
- 과도한 gradient, glassmorphism, chat bubble, card grid 배제

CSS framework와 디자인 시스템 패키지를 추가하지 않는다. `app.css`에는 reset, typography, layout, focus와 최소 상태 스타일만 둔다.

## Content Security Policy

Django 6.1의 내장 CSP middleware를 사용한다. 정적 JavaScript를 로컬에서 제공하므로 기본 정책은 same-origin을 중심으로 구성한다.

- `default-src 'self'`
- `script-src 'self'`
- `style-src 'self'`
- `connect-src 'self'`
- `font-src 'self'`
- `img-src 'self' data: https:`

외부 책 표지는 HTTPS 출처를 허용하되 외부 script와 style은 허용하지 않는다. 이후 외부 provider가 추가되면 필요한 directive만 국소적으로 확장한다.

## 요청 흐름

```text
Browser
  → Django URL
  → TemplateView 또는 최소 view
  → full page / Django 6.1 template partial
  → HTMX가 대상 영역 교체
```

초기 확인 view에는 비즈니스 로직이나 데이터베이스 상태 변경을 넣지 않는다. 앱을 추가한 뒤에도 View와 HTMX endpoint는 Service 또는 Selector를 호출하는 interface 역할만 맡는다.

## 실패 처리

- 필수 환경변수가 없으면 시작 시 어떤 변수가 누락됐는지 명확하게 실패한다.
- PostgreSQL 연결 실패를 SQLite로 숨기지 않는다.
- Docker healthcheck로 PostgreSQL 준비 상태를 확인한다.
- `DJANGO_DEBUG`는 `django-environ`의 boolean 타입 변환을 사용한다.
- HTMX가 비활성화되거나 JavaScript가 실패해도 초기 페이지의 핵심 콘텐츠는 서버 렌더링으로 보인다.
- 초기 setup endpoint는 외부 API나 LLM을 호출하지 않는다.

## 품질과 테스트

Ruff는 Python format과 lint를 담당한다. pytest-django는 Django integration test를 담당한다. 초기 검증은 실제 PostgreSQL 18을 사용하며 SQLite 대체 테스트는 만들지 않는다.

최소 테스트 범위:

- Django system check 통과
- 설정이 PostgreSQL backend를 사용함
- 기본 페이지가 HTTP 200과 핵심 landmark를 반환함
- HTMX 요청이 full document가 아닌 partial을 반환함
- CSP header가 설정됨
- 정적 vendor 자산 경로가 Template에 포함됨

표준 검증 명령:

```powershell
docker compose up -d db
uv sync --locked
uv run python src/manage.py migrate --noinput
uv run python src/manage.py check
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

`scripts/verify.py`는 Django system check, Ruff format check, Ruff lint와 pytest를 순서대로 실행하고 첫 실패의 종료 코드를 그대로 반환한다. PostgreSQL이 실행 중인 상태에서 다음 단일 명령으로 기본 검증 전체를 수행한다.

```powershell
uv run python scripts/verify.py
```

개발 서버 실행:

```powershell
uv run python src/manage.py runserver
```

## README 갱신

루트 README에는 다음 정보만 추가한다.

- 요구 도구: uv, Docker
- `.env.example`에서 `.env`를 준비하는 방법
- PostgreSQL 시작, migration, 개발 서버 실행 명령
- format, lint, test, system check 명령
- Django 앱은 구현 계획에 따라 점진적으로 추가한다는 원칙

## 비목표

- 도메인 Django 앱 사전 생성
- 인증 화면과 사용자 모델 커스터마이징
- Book, Reading, Interview, Reflection 모델
- 외부 API, LLM, Book metadata provider 연동
- Credit, Reader Insight, Backoffice
- Background worker
- JSON API
- Node 기반 asset pipeline
- CSS framework
- 운영 배포, APM, production static serving

## 완료 판단

위 표준 검증 명령이 깨끗한 checkout과 빈 PostgreSQL volume에서 모두 통과하고, Desktop 및 Mobile viewport에서 초기 페이지와 HTMX/Alpine 최소 동작을 수동 확인하면 `IMP-001`부터 `IMP-004`까지 완료로 판단한다.
