# AfterMuse Day 01 Completion Design

## 목적

`docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 Day 01에 포함된 `IMP-001`부터
`IMP-004`까지를 기존 초기 프로젝트 설정 산출물을 기반으로 검증하고 완료 처리한다.
이미 존재하고 검증된 설정을 다시 만들지 않으며, 완료 조건과 실제 구현 사이의 차이가
발견된 경우에만 테스트를 먼저 추가한 뒤 최소 범위로 보완한다.

## 현재 기준선

초기 프로젝트 설정 작업에서 다음 산출물이 이미 구현되어 있다.

- Python 3.14, Django 6.1, Psycopg 3와 uv dependency metadata
- PostgreSQL 18.6 Docker Compose service와 healthcheck
- `django-environ` 기반 `.env` 및 OS 환경변수 로딩
- Django system check, Ruff와 pytest를 묶은 `scripts/verify.py`
- Django Template, HTMX 2.0.10, Alpine.js CSP 3.17.1과 공통 반응형 Layout
- 설정, 저장소 계약, 기본 페이지, HTMX partial, CSP와 검증 스크립트 테스트

2026-09-01 현재 PostgreSQL container는 healthy이며 `uv run python
scripts/verify.py`가 Django system check, Ruff format, Ruff lint와 12개 테스트를 모두
통과한다. 이 결과는 현재 checkout의 기준선일 뿐, 깨끗한 환경과 빈 database에서의
재현성을 대신하지 않는다.

## 검토한 접근

### 1. Day 01 전체 재구현

기존 초기화 파일을 지우거나 다시 생성해 IMP 순서대로 구현한다. 실패 테스트부터 모든
단계를 재현할 수 있지만, 이미 검증된 코드를 불필요하게 변경하고 회귀 위험과 의미 없는
diff를 만든다. 채택하지 않는다.

### 2. 기존 테스트 통과만으로 완료 처리

현재 전체 검증 결과를 근거로 체크박스만 완료한다. 가장 빠르지만 빈 database migration,
깨끗한 checkout 재현성과 실제 browser의 HTMX/Alpine 동작을 증명하지 못한다. 채택하지
않는다.

### 3. 증거 기반 차이 보완 및 완료 검증

기존 구현을 보존하고 각 IMP의 완료 조건을 독립된 검증 증거에 연결한다. 자동화되지 않은
재현성 및 browser 검증을 수행하고, 실패가 발견된 경우에만 TDD로 보완한다. 검증이 모두
통과한 뒤 구현 계획의 체크박스와 관련 문서를 동기화한다. 이 접근을 채택한다.

## IMP별 완료 계약

### IMP-001 — Django 프로젝트 Bootstrap

- `src/manage.py`와 `src/config`가 최소 Django project entrypoint를 제공한다.
- 아직 사용하지 않는 도메인 app, model, service 또는 selector가 존재하지 않는다.
- `.env.example`로 환경을 준비한 상태에서 `python src/manage.py check`가 통과한다.
- 개발 서버가 시작되고 `/` 요청에 HTTP 200으로 응답한다.

### IMP-002 — PostgreSQL 개발 환경 구성

- application database backend는 PostgreSQL만 사용하고 SQLite fallback을 제공하지 않는다.
- PostgreSQL 18.6 container가 healthcheck를 통과한다.
- 별도의 임시 database를 생성해 Django 기본 migration을 처음부터 적용할 수 있다.
- 재현성 검증용 database는 운영 또는 사용자의 기존 개발 database를 변경하지 않는다.
- 검증이 끝난 임시 database의 삭제는 파괴적 작업이므로 별도 승인 없이 수행하지 않는다.

### IMP-003 — 테스트 및 품질 명령 구성

- `uv sync --locked`로 lockfile과 일치하는 환경을 구성할 수 있다.
- `uv run python scripts/verify.py` 한 번으로 Django system check, Ruff format check,
  Ruff lint와 pytest가 순서대로 실행된다.
- 하위 검증이 실패하면 검증 스크립트가 첫 번째 비정상 종료 코드를 반환한다.
- 저장소 계약, 환경 설정, 공통 페이지와 검증 스크립트의 핵심 동작이 회귀 테스트로
  보호된다.

### IMP-004 — 공통 Layout과 HTMX/Alpine 토대

- 공통 Template은 skip link, header, main landmark와 message 영역을 제공한다.
- 핵심 콘텐츠는 JavaScript 없이도 서버 렌더링된다.
- HTMX 요청은 full document가 아닌 Django Template Partial을 반환하고 대상 영역을
  교체한다.
- Alpine.js CSP build의 browser-only 상태 전환이 동작하며 CSP에 `unsafe-eval`을
  추가하지 않는다.
- Desktop과 Mobile viewport에서 콘텐츠가 수평 overflow 없이 표시되고 keyboard focus가
  식별 가능하다.
- HTMX와 Alpine.js는 저장소에 고정된 local asset과 license를 사용한다.

## 실행 흐름

1. Day 01 요구사항과 현재 파일 및 테스트의 추적표를 작성한다.
2. 기존 전체 검증을 실행해 현재 checkout 기준선을 다시 확인한다.
3. 별도의 임시 PostgreSQL database에서 migration 재현성을 확인한다.
4. 개발 서버를 실행해 `/`와 `/setup-status/` 응답을 확인한다.
5. Desktop과 Mobile viewport에서 Layout, HTMX 교체, Alpine 상태 전환, focus와 CSP를
   수동 확인한다.
6. 실패가 없다면 구현 코드를 변경하지 않는다.
7. 실패가 있으면 해당 관찰 가능한 동작의 실패 테스트를 먼저 작성하고 최소 구현으로
   통과시킨다.
8. 전체 검증을 다시 실행한다.
9. 완료 증거가 모두 확보되면 `IMP-001`부터 `IMP-004`까지 체크하고 관련 상태 문서를
   수술적으로 동기화한다.

## 변경 범위

검증이 모두 통과하는 경우 다음 문서만 생성하거나 수정한다.

- `docs/superpowers/specs/2026-09-01-day-01-completion-design.md`: Day 01 완료 검증 설계
- `docs/superpowers/plans/2026-09-01-day-01-completion.md`: 실행 단계와 검증 증거
- `docs/AfterMuse_MVP_Implementation_Plan_v5.md`: `IMP-001`~`IMP-004` 완료 표시
- 필요할 경우 `README.md`: 실제 재현 절차와 다른 설명만 수정
- 필요할 경우 `CHANGELOG.md`: Day 01 완료 상태를 별도 기록할 필요가 있을 때만 수정

검증 실패가 발견된 경우 실패 원인과 직접 관련된 설정, source, test 또는 문서만 추가로
수정한다. Day 02의 인증, Book 또는 검색 기능은 만들지 않는다.

## 검증 증거

완료 보고에는 다음 결과를 포함한다.

- 사용한 Python, Django, PostgreSQL, uv와 Docker Compose version
- PostgreSQL healthcheck 상태
- 임시 database에 적용한 migration 결과
- `scripts/verify.py`의 검사 항목과 test 통과 수
- Desktop 및 Mobile browser 확인 항목
- HTMX partial 교체와 Alpine.js 상태 전환 확인 결과
- 수정한 파일과 남은 위험

## 오류 처리

- baseline 검증이 실패하면 기존 결함인지 현재 변경으로 생긴 결함인지 먼저 구분한다.
- Docker 또는 uv가 sandbox에서만 실패하면 동일한 최소 명령을 승인받아 사용자 환경에서
  다시 실행한다.
- 빈 database 검증이 기존 database를 덮어쓸 가능성이 있으면 실행하지 않고 별도 database
  이름을 사용한다.
- browser 동작이 자동 테스트와 다르면 browser 관찰을 재현하는 실패 테스트를 추가할 수
  있는지 먼저 검토한다.
- 동일 가설의 수정이 반복 실패하거나 요구사항 충돌이 발견되면 구현을 멈추고 보고한다.

## 비목표

- 기존 초기 프로젝트 설정의 재작성
- 새로운 Django domain app 또는 model 생성
- 인증, Book, Reading, Interview 또는 Reflection 기능
- Node asset pipeline, CSS framework 또는 JSON API 도입
- 운영 배포 설정과 production static serving
- 사용자의 기존 개발 database 또는 Docker volume 삭제

## 완료 판단

네 IMP의 완료 계약과 검증 증거가 모두 충족되고 전체 검증이 통과하면 Day 01을 완료로
판단한다. 자동 검증이 통과하더라도 빈 database migration이나 browser 검증 중 하나가
확인되지 않으면 해당 IMP를 완료 표시하지 않는다.
