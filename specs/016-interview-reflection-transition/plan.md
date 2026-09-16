# 구현 계획: Interview 상호작용 완결과 Reflection 생성 Transition

**브랜치**: `feature/day-11-interview-reflection-transition` | **날짜**: 2026-09-16 | **사양**: [spec.md](spec.md)

**입력**: `specs/016-interview-reflection-transition/spec.md`

## 요약

IMP-096은 현재 Turn에 명시적 사용자 Skip 시각을 저장하고 답변과 상호 배타적으로 만든다. Skip은 Coverage 분석 없이 다음 질문 계약에 별도 신호로 전달하며, 질문 budget은 답변과 Skip을 모두 해결된 Turn으로 계산한다. 모든 Turn을 Skip한 채 종료 조건에 도달하면 새 `ENDED_NO_REFLECTION` Interview 상태로 종결한다. IMP-092는 기존 Day 10 생성·저장 Service를 동기식 POST로 연결하고 HTMX Loading/Error/Retry, 기존 Reflection 재사용, 최소 임시 결과 화면을 제공한다. IMP-095는 Interview 시작·질문 화면에서 내부 Knowledge enum을 제거하고 제한된 정보 상태를 기억 중심 안내로 표현한다.

## 기술적 맥락

**언어/버전**: Python 3.14, Django 6.1; 루트 `pyproject.toml`과 `uv.lock` 기준.

**주요 의존성**: 기존 Django Templates, HTMX 2.0.10, Alpine.js CSP 3.17.1, Psycopg 3.3 및 Day 10 Reflection Provider 경계. 새 패키지 없음.

**저장소**: PostgreSQL 18. 기존 `Interview`·`InterviewTurn`·`Reflection` 테이블에 additive/constraint 변경만 수행하며 새 생성 시도 테이블은 두지 않는다.

**테스트**: pytest·pytest-django, 실제 PostgreSQL ORM/transaction, Django test client의 HTML·HTMX 계약, fake Reflection/질문 Provider, migration 전후·경합 테스트, Django check·Ruff.

**대상 플랫폼**: 기존 서버 렌더링 Django Web. Desktop 우선 반응형 UI와 Mobile Web, Windows 호스트 개발 및 PostgreSQL 컨테이너.

**프로젝트 유형**: 단일 서버 렌더링 Web application.

**성능 목표**: Skip·생성 요청 시작 후 1초 이내 Loading/상태 피드백. Reflection 외부 호출은 요청당 최대 1회와 기존 Provider timeout을 따르며, 외부 호출 중 DB transaction·row lock을 유지하지 않는다. 최종 저장 transaction은 owner·snapshot 재검증과 단일 insert로 제한한다.

**제약 조건**: 질문 일반 상한 8개·절대 상한 10개. 답변 또는 사용자 Skip으로 해결된 Turn 수가 전체 질문 수와 일치해야 후속 전이를 허용한다. 생성은 자동 재시도·provider fallback·background polling 없이 명시적 사용자 요청 한 번으로 수행한다. 실제 브라우저 실행은 필수 검증이 아니다.

**규모/범위**: IMP-092·095·096. 새 nullable Turn 필드 하나, Interview terminal 상태 하나, HTTP endpoint 세 개, 관련 Service·template·CSS·테스트. Day 12 정식 결과/편집/완료/Home 연계, Credit, 공개·공유, Skip 취소는 제외.

## 헌법 검사

*헌법 1.1.0 기준 조사 전·설계 후 모두 통과.*

| 원칙 | 설계 증거 | 판정 |
| --- | --- | --- |
| I. 사용자 생각의 충실성 | Skip은 Answer를 만들거나 Coverage를 올리지 않고, 답변 0개면 Reflection을 만들지 않는다. 생성은 기존 Day 10 확정 답변 계약을 재사용한다. | 통과 |
| II. 핵심 루프와 범위 규율 | Interview 종료→생성→최소 결과 전이와 Skip만 연결하고 Day 12 편집·완료, Credit·공개·background worker는 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 모든 POST/GET은 owner scope로 재조회하고 Service만 상태를 변경한다. Provider 입력은 Skip과 확정 답변을 구분하며 오류에 원문·외부 응답을 노출하지 않는다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 FBV·Service·Django Template·HTMX와 Day 10 drafts 경계를 재사용한다. 생성 시도 모델·Celery·내부 HTTP API·Repository를 추가하지 않는다. | 통과 |
| V. 증거 기반·회복 UX | Loading/Error/Retry·키보드·색상 외 문구, 답변/Skip 경합, migration, 소유권, 실패 보존을 test client와 실제 ORM로 검증한다. | 통과 |

Migration은 nullable 열 추가와 CHECK 교체가 요구하는 짧은 `ACCESS EXCLUSIVE` lock에 프로젝트 관례의 `SET LOCAL lock_timeout = '2s'`를 적용한다. 기존 행 scan은 `NOT VALID`와 후속 `VALIDATE CONSTRAINT`로 분리하며, validation migration은 `atomic = False`로 둔다. 구현 시 `sqlmigrate` 결과를 실제 PostgreSQL SQL 기준으로 검수한다.

사용자 권한·답변 보존·Reflection 멱등성은 관련 테스트와 diff를 분리된 검토 관점에서 대조한다. 실제 브라우저 검증은 필수 작업으로 추가하지 않는다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/016-interview-reflection-transition/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/interview-reflection-transition.md
```

`tasks.md`는 다음 `$speckit-tasks` 단계에서 생성한다.

### 소스 코드 (저장소 루트)

| 경로 | 변경 책임 |
| --- | --- |
| `src/reflections/models.py` | `user_skipped_at`, Turn 결과 배타 제약, `ENDED_NO_REFLECTION` 상태 |
| `src/reflections/migrations/0008_*.py`, `0009_*.py` | nullable 열·CHECK의 짧은 DDL과 별도 non-blocking validation; leaf는 구현 시 재확인 |
| `src/reflections/services.py` | Skip 저장·재개, budget/상태 전이, 새 terminal destination |
| `src/reflections/drafts.py` | 기존 Reflection 선조회, 생성·저장·conflict 후 재조회 orchestration |
| `src/integrations/llm/contracts.py`, `interview.py` | 다음 질문 입력에서 사용자 Skip과 저정보 답변 구분 |
| `src/reflections/views.py`, `urls.py` | Skip POST, Reflection 생성 POST, 최소 결과 GET 및 HTMX/일반 응답 |
| `src/templates/reflections/` | 친화적 Knowledge 문구, Skip, 생성 Loading/Error/Retry, no-reflection 종결, 최소 결과 |
| `src/static/css/app.css` | 기존 progressive enhancement 패턴에 맞춘 상태·focus·disabled 및 대표 Desktop·Mobile breakpoint 표현 |
| `tests/reflections/test_models.py`, `test_migrations.py` | 제약·상태·migration 보존/역방향·SQL 안전성 |
| `tests/reflections/test_services.py`, `test_drafts.py` | Skip·budget·경합·생성 멱등성과 실패 불변 |
| `tests/reflections/test_views.py` | owner scope, HTML/HTMX, Loading/Error/Retry, 문구·접근성·redirect 계약 |
| `tests/integrations/llm/` | Skip-aware 다음 질문 wire/prompt와 기존 답변 경로 회귀 |

**구조 결정**: Interview 흐름은 기존 `services.py`에 유지하고 Day 10 Reflection orchestration은 기존 `drafts.py`에 둔다. 파일 분리 자체를 목적으로 기존 Service를 재구성하지 않으며, 새 persistence abstraction이나 background subsystem을 도입하지 않는다.

## 실행 및 검증 순서

1. 상태·Turn schema와 안전한 두 단계 CHECK migration을 구현하고 model/migration 테스트로 기존 데이터와 역방향 조건을 확인한다.
2. Reflection 생성 orchestration과 Loading/Error/Retry·최소 결과 화면을 연결한다. 기존 결과 선조회, concurrent save conflict 수렴, 실패 시 원문·상태 불변을 검증한다.
3. 사용자 Skip의 저장→외부 호출 없는 budget 판정 또는 skip-aware 다음 질문 생성→짧은 commit 흐름을 구현한다. 답변/Skip 경합과 실패 후 재개를 먼저 검증한다.
4. Knowledge 사용자 문구와 Skip HTTP/HTMX UI를 연결한다. 내부 enum 0건, keyboard/focus, Desktop/Mobile HTML 계약을 검증한다.
5. [quickstart.md](quickstart.md)의 좁은 회귀 후 `uv run python scripts/verify.py`를 실행한다. README·docs 구현 계획·CHANGELOG는 실제 완료 상태만 동기화한다.

## 설계 후 헌법 재검사

Phase 0·1 산출물은 사용자 발화 충실성, owner scope, Service-only mutation, 동기식 단순 전이 및 결정적 검증 원칙을 유지한다. 새 상태는 Reflection 완료와 답변 없는 종결을 혼동하지 않기 위해 필요하며, 새 테이블 없이 기존 상태 enum을 확장한다. 위반 또는 예외 없음.

## 복잡성 추적

헌법 위반 없음. 두 migration 파일은 구조 확장이 아니라 기존 행 scan을 쓰기 차단 lock에서 분리하기 위한 배포 안전 요구다. 생성 시도 persistence와 worker는 현재 범위에 비해 복잡하여 도입하지 않는다.
