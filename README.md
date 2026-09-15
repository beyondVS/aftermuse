# AfterMuse

> 책을 덮은 뒤, 생각이 시작됩니다.

AfterMuse는 AI 질문으로 독자의 생각을 끌어내고, 사용자가 실제로 답한 내용으로
독서노트(Reflection) 초안을 만드는 서비스입니다. 빈 노트에서 글을 시작하는 부담을
질문과 답변으로 줄이고, 사용자가 초안을 직접 다듬어 자신의 기록으로 남기게 합니다.

**핵심 흐름:** 책 선택 → Reading → AI Interview → Reflection 초안 → 수정·확인

AI는 사용자가 말하지 않은 생각이나 책의 사실을 추가하지 않습니다. Books-first 전략의
Responsive Web(Desktop 우선, Mobile 지원)을 개발하며, Credit·Reader Insight·자동 Book
Knowledge Research·공개/공유 기능은 후속 범위입니다.

[현재 구현 상태](#현재-구현-상태) · [개발 환경 시작](#개발-환경-시작) ·
[LLM 설정과 오류 진단](#llm-설정과-오류-진단) · [개발 명령](#개발-명령) · [문서](#문서)

## 현재 구현 상태

2026-09-16 기준, Day 10의 데이터·생성 기반까지 구현했습니다.

| 영역 | 사용할 수 있는 기능 |
| --- | --- |
| 인증 | 세션 기반 회원가입·로그인·POST 로그아웃 |
| 책 검색 | Kakao 검색, HTMX Loading·Empty·Error, 판본 확인 및 Book 등록·재사용 |
| Reading | 명시적 시작·재독, 상태·완독일 변경, 소유자 전용 상세 |
| Interview | 완독 후 시작, 첫 질문·답변 분석·후속 질문, Coverage·Soft Stop·질문 상한, 실패 재시도 |
| Home | 실제 Reading 상태별 카드·빈 상태, 진행 중 Interview 재진입과 확정 질문·답변 조회 |
| Reflection 기반 | Interview당 하나의 초안 저장·조회, 별도 수정본 보존, 답변 기반 비영속 생성 Service |

Interview는 `READY`에서 검증된 Claim을 사용하고, `READY_LIMITED`에서는 기억·인상 중심으로
질문합니다. 확정 답변은 보존하며 기존 질문을 재사용하고, 실패 시 명시적으로 재시도합니다.
네 Core Coverage 축 완료 후 네 번째~일곱 번째 답변에서 Soft Stop을 선택할 수 있습니다.
여덟 번째 답변에 일반 상한을 적용하며, 미충족 축의 근거 있는 질문을 사용자가 선택한 경우에만
최대 열 번째 질문까지 진행합니다.

Reflection 생성 대상은 최종 완료된 Interview가 아니라 `REFLECTION_READY` 상태입니다.
생성은 DB transaction 밖에서 비영속 결과를 반환하고, 별도의 저장 Service가 초안을 보존합니다.
최초 초안은 Model 검증으로 변경을 거부하고, DB는 Interview당 하나·길이·Draft 상태를 제한합니다.
수정본은 초안과 분리하며 생성·수정본 저장만으로 완료 처리하지 않습니다.
저장 잠금 후 소유자·책 관계·상태·확정 답변 snapshot을 다시 검증합니다.

fake·OpenAI·Gemini·Ollama는 같은 구조화 생성 계약을 사용합니다. 서버는 최상위·중첩 키,
길이, 답변 원문 인용, 표현 연결과 금지 형식을 검증하고 canonical Markdown을 조립합니다.
이 검사는 실제 LLM 출력의 의미적 충실성을 완전히 증명하지 않습니다.

**남은 범위:** Reflection 생성/실패/Retry 화면(Day 11), 결과·수정 화면과 Home 재진입(Day 12).
실제 Reflection Provider 연결·의미 품질 평가는 별도 opt-in 인수로 남아 있습니다.
자세한 완료 상태는 [구현 계획](docs/AfterMuse_MVP_Implementation_Plan_v5.md), 검증 근거는
[Day 10 검증 기록](specs/015-reflection-draft-generation/quickstart.md)을 참조합니다.

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
│  ├─ integrations/      Metadata·LLM Provider Adapter
│  ├─ knowledge/         검증된 Book Claim과 준비 상태
│  ├─ readings/          독서 상태·완독·재독
│  ├─ reflections/       Interview·Coverage·Reflection 모델과 Service
│  ├─ static/            공통 CSS, JavaScript 및 vendor 자산
│  ├─ templates/         공통·인증·독서·Interview Template
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
| `LLM_PROVIDER` | Interview·Reflection LLM Provider (`fake` 기본값, `openai`·`gemini`·`ollama` 선택) |
| `OPENAI_MODEL` | OpenAI 질문·답변 분석·Reflection 생성에 사용할 고정 모델 snapshot |
| `OPENAI_API_KEY` | `LLM_PROVIDER=openai`일 때 필요한 API key |
| `OPENAI_TIMEOUT_SECONDS` | LLM Provider 호출 timeout (기본 30초) |
| `GEMINI_MODEL`, `GEMINI_API_KEY`, `GEMINI_TIMEOUT_SECONDS` | Gemini의 정확한 모델명·명시적 API key·호출 timeout |
| `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_TIMEOUT_SECONDS` | 설치된 로컬 모델명·loopback API URL·호출 timeout |

필수 환경변수가 없으면 Django는 시작 단계에서 명시적으로 실패합니다. Django는 저장소
루트의 `.env`를 자동으로 읽으며, 같은 이름의 OS 환경변수가 있으면 OS 값을 우선합니다.
SQLite fallback은 제공하지 않습니다.

기본 Metadata Provider는 Kakao 도서 검색 API입니다. 일반 자동 테스트와 개발 검증은 실제
key 없이 실행할 수 있고, 실제 검색이나 명시적 live smoke를 실행할 때만
`KAKAO_REST_API_KEY`가 필요합니다. `ALADIN_TTB_KEY`는 기존 Adapter 호환을 위해 유지하며
신규 검색 경로에서는 사용하지 않습니다. key와 Provider 원본 오류 내용은 반환값이나 오류
메시지에 포함하지 않습니다.

## LLM 설정과 오류 진단

기본 `LLM_PROVIDER=fake`는 credential이나 실행 중인 Ollama 없이 동작합니다.
실제 Provider는 `.env`에 선택한 Provider의 모델·key·timeout을 명시합니다.
Ollama는 설치된 모델명과 loopback HTTP URL을 사용하며 모델을 자동 다운로드하지 않습니다.
질문 생성·답변 분석·후속 질문·Reflection 생성은 자동 재요청이나 다른 유료 Provider로의
fallback 없이 한 번 호출합니다. OpenAI는 `store=False`와 tools 없는 요청을 사용하고,
Gemini는 AFC를 비활성화하며 Ollama는 JSON schema를 전달합니다.

기존 질문 표시·Reflection 조회·수정본 저장은 Provider 구성에 의존하지 않습니다.
Reflection 오류는 `ReflectionGenerationError` 아래 Timeout·Unavailable·Rejected·ConfigurationError로
구분하고, 소유자 정책·출력 검증·중복 초안·저장 오류는 Service 오류로 구분합니다.

Interview 질문 준비는 자동으로 시작하며 요청 중 버튼과 같은 form의 추가 submit을 차단합니다.
JavaScript 없이도 버튼으로 준비를 요청할 수 있습니다. 503 화면은 고정 실패 사유·오류 코드·질문
번호를 표시하고 답변을 보존합니다. `reflections.views`의 `Interview pipeline failed` 로그는
단계·Interview id·sequence·예외 타입/위치·HTTP 상태·검증 `reason`으로 진단합니다.
예외 메시지·답변·credential·Provider 원문은 로그에 기록하지 않습니다.

실제 연결은 아래 명령으로 선택한 경우에만 검증합니다. Ollama는 `OLLAMA_LIVE_TEST=1`도 필요합니다.

```powershell
uv run pytest -m live tests/integrations/llm/test_live_smoke.py
# Reflection만 확인
uv run pytest -m live tests/integrations/llm/test_live_smoke.py -k reflection
```

Interview의 과거 live 실행 결과와 Reflection의 미실행 범위는
[문서 인덱스](docs/README.md)와 [Day 10 검증 기록](specs/015-reflection-draft-generation/quickstart.md)에
구분하여 기록합니다.

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
