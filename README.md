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

현재 저장소에는 Custom User 기반의 세션 인증 흐름이 구현되어 있습니다. 사용자는
`/accounts/signup/`에서 가입하고, `/accounts/login/`에서 로그인하며, POST
`/accounts/logout/`으로 로그아웃할 수 있습니다.

Day 03까지 ISBN13 중심의 Book 모델, Provider 중립 Metadata 계약과 검색 Service,
Kakao 도서 검색 Adapter 및 로그인 사용자용 `/books/search/` 화면이 구현되어 있습니다.
검색 화면은 HTMX로 Loading·Empty·Error 상태와 판본 식별용 서지정보를 제공하며, 사용자가
선택한 검색 결과는 기존 Book을 재사용하거나 새 Book으로 안전하게 등록한 뒤 Reading
진입 화면으로 이동합니다. 사용자는 상태를 명시적으로 선택해 Reading을 시작하며, 활성
Reading 재사용·완독 이력 보존·재독, 상태/완독일 변경과 소유자 전용 상세 화면을 사용할 수
있습니다. 완독 후 `AI 독서노트 만들기` CTA에서 대상 책과 준비 상태를 확인하고 Interview를
시작할 수 있으며, 시작된 Interview에는 Reading과 Book이 고정되고 진행 상태로 재진입할 수
있습니다. 진행 중 Interview에서는 준비 수준에 맞는 첫 질문을 생성하며, `READY`는 검증된
Claim만 사용하고 `READY_LIMITED`는 기억·인상 중심으로 묻습니다. 첫 답변은 한 번만 확정되며
동일 재제출은 안전하게 재사용하고, 질문 생성 실패는 같은 화면의 명시적 재시도로 복구합니다.
생성 질문은 저장 전에 형식·금지 지시를 검사하며, HTMX의 validation·정책·저장 오류는 입력과
내부 정보를 안전하게 보호하면서 Interview 영역 전체를 교체하고 오류 위치로 focus를 옮깁니다.
기존 첫 질문 재사용과 Interview 정책 검증은 Provider 생성보다 먼저 수행되므로 외부 설정
오류가 이미 저장된 질문이나 정책 충돌 응답을 가리지 않습니다. 확정 답변은 비영속 Answer
Analysis 계약으로 의미와 low-information 여부, 현재 상태보다 높은 Core Coverage 후보를 얻을
수 있습니다. 후보별 근거 인용은 답변 원문과 대조하고 Provider 출력 전체를 Application에서
재검증하며, 분석 성공·실패 모두 답변·Turn·Coverage를 직접 변경하지 않습니다.
확정 답변 뒤에는 분석과 Coverage를 반영해 다음 질문 하나를 이어갑니다. 후속 질문은 답변
원문의 검증된 인용과 Coverage 축으로 구성해 확인되지 않은 책 사실을 전제하지 않습니다.
네 축이 모두 완료되고 답변에 추가 탐색 근거가 없다는 명시적 신호가 확인되면 질문 생략을
기록합니다. 질문 준비에 실패해도 답변 원문은 유지되고 재시도할 수 있습니다.

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
│  ├─ accounts/          Custom User와 인증 흐름
│  ├─ books/             Book 모델, 검색·선택 Service와 화면
│  ├─ config/            Django 프로젝트 설정
│  ├─ integrations/      외부 Metadata Provider Adapter
│  ├─ static/            공통 CSS, JavaScript 및 vendor 자산
│  ├─ templates/         공통·인증·도서 검색 Template
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
| `KAKAO_REST_API_KEY` | 기본 Kakao 도서 검색 Adapter용 REST API key (일반 자동 테스트에서는 불필요) |
| `ALADIN_TTB_KEY` | IMP-021 legacy 알라딘 Adapter용 TTB key (신규 발급 종료, 자동 테스트에서는 불필요) |
| `LLM_PROVIDER` | Interview LLM Provider (`fake` 기본값, 실제 연결 시 `openai`) |
| `OPENAI_MODEL` | OpenAI 질문·답변 분석에 사용할 고정 모델 snapshot |
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai`일 때 필요한 API key |
| `OPENAI_TIMEOUT_SECONDS` | Interview LLM Provider 전체 timeout (기본 30초) |

필수 환경변수가 없으면 Django는 시작 단계에서 명시적으로 실패합니다. Django는 저장소
루트의 `.env`를 자동으로 읽으며, 같은 이름의 OS 환경변수가 있으면 OS 값을 우선합니다.
SQLite fallback은 제공하지 않습니다.

기본 Metadata Provider는 Kakao 도서 검색 API입니다. 일반 자동 테스트와 개발 검증은 실제
key 없이 실행할 수 있고, 실제 검색이나 명시적 live smoke를 실행할 때만
`KAKAO_REST_API_KEY`가 필요합니다. `ALADIN_TTB_KEY`는 기존 Adapter 호환을 위해 유지하며
신규 검색 경로에서는 사용하지 않습니다. key와 Provider 원본 오류 내용은 반환값이나 오류
메시지에 포함하지 않습니다.

Interview LLM의 기본 Provider는 `fake`이므로 자동 테스트와 일반 개발 흐름에 OpenAI credential이
필요하지 않습니다. 실제 OpenAI Adapter는 `store=False`, tools 없이 고정 모델 snapshot으로
질문 또는 답변 분석 결과만 생성하며, timeout·Provider·출력 오류는 원문을 노출하지 않는 상태로
변환합니다. 기존 질문 재사용과 Interview 소유권·관계·상태 검증이 끝난 뒤에만 Provider를
생성하므로, 저장된 질문을 표시하는 경로는 Provider credential이나 구성 상태에 의존하지
않습니다.

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

기본 pytest 실행은 network와 실제 credential이 필요한 `live` marker 테스트를 제외합니다.
외부 I/O는 기본 테스트에서 fake 또는 mock으로 대체하고 내부 business logic은 실제로
검증합니다. 실제 외부 연결을 확인할 때만 대상 테스트에 `live` marker를 지정하고
`uv run pytest -m live <테스트 경로>`로 명시적으로 실행합니다. live 테스트는 credential,
authorization header와 원본 응답을 출력하지 않아야 합니다.

Kakao 도서 검색을 실제로 확인할 때만 로컬 `.env`에 `KAKAO_REST_API_KEY`를 설정한 뒤
`uv run pytest -m live tests/integrations/kakao/test_live_smoke.py -v`를 실행합니다.

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
