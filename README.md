# AfterMuse

> 책을 덮은 뒤, 생각이 시작됩니다.

## 제품 개요

AfterMuse는 책을 읽은 사용자가 AI와 인터뷰하듯 대화하면, AI가 사용자의 생각을
끌어내고 사용자가 실제로 말한 범위에서 구조화된 독서노트(Reflection)를 만들어주는
서비스입니다.

## 해결하려는 문제

독서 후 빈 노트를 마주하면 무엇을 써야 할지 막막합니다. 템플릿이 있어도 결국
사용자가 스스로 생각을 떠올리고 문장으로 작성해야 하므로, 기록을 시작하기가
어렵습니다. AfterMuse는 이 부담을 질문과 대화로 바꿉니다.

## 핵심 경험

책을 읽음 → AI 질문 → 사용자 답변 → 필요한 꼬리질문 → 생각 구체화 → Reflection
생성·수정

## 제품 원칙

- AI가 독후감이나 해석을 대신 쓰지 않습니다.
- 사용자가 말하지 않은 생각을 추가하지 않습니다.
- 빈 노트에 쓰게 하지 말고, 답변하게 해서 노트를 만듭니다.

## MVP 범위

현재 2주 Core MVP는 책 선택부터 AI Interview, Reflection 생성·수정, 실제 책 기반
검증까지의 핵심 경험을 연결합니다. Books-first 전략을 따르며 Responsive Web으로
제공합니다(Desktop 우선, Mobile 지원).

Credit, Reader Insight, Book Knowledge 자동 Research, Backoffice 및 기타 콘텐츠
확장은 Full MVP 이후의 장기 항목입니다.

## 현재 구현 상태

현재 저장소에는 2주 Core MVP 구현을 시작하기 위한 Django 개발 기반과 공통 웹 UI
토대가 구성되어 있습니다. 도메인 앱과 모델은 각 구현 계획에서 책임과 경계를 확정한
뒤 점진적으로 추가합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Runtime | Python 3.14 |
| Backend | Django 6.1 |
| Database | PostgreSQL 18, Psycopg 3 |
| UI | Django Templates, HTMX 2.0.10, Alpine.js CSP 3.17.1 |
| 개발 도구 | uv, pytest, pytest-django, Ruff |
| 로컬 인프라 | Docker Compose |

Django와 개발 도구는 호스트에서 실행하고 PostgreSQL만 컨테이너로 구동합니다.
HTMX와 Alpine.js는 CDN 없이 저장소의 로컬 정적 자산을 사용합니다.

## 프로젝트 구조

```text
.
├─ docs/                 기획, 아키텍처 및 구현 계획
├─ scripts/              개발 검증 스크립트
├─ src/
│  ├─ config/            Django 프로젝트 설정
│  ├─ static/            공통 CSS, JavaScript 및 vendor 자산
│  ├─ templates/         공통 Template과 초기 화면
│  └─ manage.py
├─ tests/                프로젝트 설정 및 통합 테스트
├─ .env.example          로컬 환경변수 예시
├─ compose.yaml          PostgreSQL 개발 환경
├─ pyproject.toml        프로젝트 및 개발 도구 설정
└─ uv.lock               재현 가능한 의존성 잠금 파일
```

## 개발 환경 시작

### 요구 도구

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop 또는 Docker Engine과 Compose plugin

Python은 `.python-version`에 지정된 3.14 계열을 uv가 관리합니다.

### 처음 실행

PowerShell에서 다음 명령을 실행합니다.

```powershell
Copy-Item .env.example .env
docker compose up -d --wait db
uv sync --locked
uv run python src/manage.py migrate --noinput
uv run python src/manage.py runserver
```

개발 서버가 시작되면 <http://127.0.0.1:8000/>에서 초기 화면을 확인할 수 있습니다.
`.env.example`의 값은 로컬 개발 예시이며 운영 credential로 사용하지 않습니다.

### 환경변수

| 변수 | 용도 |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django 서명용 비밀값 |
| `DJANGO_DEBUG` | boolean debug 설정 |
| `DJANGO_ALLOWED_HOSTS` | 쉼표로 구분한 허용 host |
| `POSTGRES_DB` | PostgreSQL database 이름 |
| `POSTGRES_USER` | PostgreSQL 사용자 |
| `POSTGRES_PASSWORD` | PostgreSQL 비밀번호 |
| `POSTGRES_HOST` | PostgreSQL host |
| `POSTGRES_PORT` | PostgreSQL port |

필수 환경변수가 없으면 Django는 시작 단계에서 명시적으로 실패합니다. Django는 저장소
루트의 `.env`를 자동으로 읽으며, 같은 이름의 OS 환경변수가 있으면 OS 값을 우선합니다.
SQLite fallback은 제공하지 않습니다.

## 개발 명령

PostgreSQL 컨테이너가 healthy인 상태에서 전체 검증을 실행합니다.

```powershell
uv run python scripts/verify.py
```

전체 검증은 Django system check, Ruff format 검사, Ruff lint와 pytest를 차례로
실행합니다. 개별 명령은 다음과 같습니다.

```powershell
uv run python src/manage.py check
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

데이터베이스 컨테이너의 상태 확인과 종료에는 다음 명령을 사용합니다.

```powershell
docker compose ps
docker compose stop db
```

## 개발 원칙

- 도메인 앱은 초기 설정에서 미리 만들지 않고 실제 MVP 작업에 맞춰 추가합니다.
- 내부 PK는 Django 기본 `BigAutoField`를 사용하며 PostgreSQL에서는 `bigint`로
  저장합니다.
- UUIDv7은 공개 URL이나 외부 API 등 별도 식별자가 필요한 모델의 `public_id`로만
  검토하며, 필요한 경우 Python 3.14의 `uuid.uuid7()`을 우선 사용합니다.
- 현재는 단일 `config/settings.py`를 사용합니다. 배포 환경이 확정되기 전에는 설정을
  여러 모듈로 분리하지 않습니다.
- 핵심 콘텐츠는 서버 렌더링하며 HTMX와 Alpine.js는 점진적 향상에 사용합니다.

## 문서

- [기획 문서 인덱스](docs/README.md)
- [Core MVP 구현 계획](docs/AfterMuse_MVP_Implementation_Plan_v5.md)
- [아키텍처 결정](docs/AfterMuse_Architecture_Decisions_v4.md)
- [초기 프로젝트 설정 설계](docs/superpowers/specs/2026-09-01-initial-project-setup-design.md)
- [변경 이력](CHANGELOG.md)

문서 간 내용이 충돌하면 기획 문서 인덱스에 명시된 우선순위를 따릅니다.

## License

이 프로젝트는 [MIT License](LICENSE)를 따릅니다.
