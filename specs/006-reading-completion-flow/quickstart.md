# Quickstart: Bundle 04A 검증 가이드

세부 계약은 [Service](contracts/service-contract.md), [UI](contracts/ui-contract.md)와
[data model](data-model.md)을 기준으로 한다.

## 사전 조건

- Python 3.14와 `uv`
- 실행 중인 PostgreSQL 18
- `.env`의 기존 필수 환경변수
- Day 03 Book 선택 migration과 코드가 적용된 상태

## Migration 검증

생성된 migration의 SQL을 먼저 확인한다. 신규 빈 table 생성만 포함해야 하며 기존
`accounts`/`books` table 변경, data migration 또는 비동기 index 구축은 없어야 한다.

```powershell
uv run python src/manage.py sqlmigrate readings 0001
uv run python src/manage.py makemigrations --check --dry-run readings
```

자동 migration test는 빈 DB에서 `readings`를 미적용 상태로 내렸다가 `0001_initial`을
다시 적용해 table·CHECK·조건부 unique index와 빈 데이터 상태를 확인한다. 개발자의 기존
로컬 데이터베이스를 수동으로 되돌리지 않는다.

## 좁은 자동 검증

1. 세 상태 저장과 상태/완독일 CHECK 제약
2. 미래·누락·불필요 완독일 Form/Service 거부
3. 최초 상태 선택 전 Reading 미생성
4. 기존 활성 Reading 재사용과 완독 이력 우선 표시
5. 명시적 재독 생성과 과거 완독 Reading 보존
6. 같은 사용자·Book 동시 생성의 활성 Reading 최대 한 건
7. 완독 취소 시 다른 활성 Reading 충돌 처리
8. 인증·CSRF·소유자 404와 DB 실패 rollback
9. 전체/HTMX 응답의 동일 상태·오류·focus 계약
10. Book 선택 성공의 Reading 진입 redirect와 기존 실패 회귀

```powershell
uv run pytest tests/readings -v
uv run pytest tests/books/test_views.py tests/readings/test_views.py -v
uv run ruff format --check src tests
uv run ruff check src tests
uv run python src/manage.py check
```

## 전체 검증

```powershell
uv run python scripts/verify.py
```

기본 검증은 외부 Metadata Provider를 호출하지 않으며 credential이 필요하지 않다.

## 수동 browser 검증

1280px Desktop과 375px Mobile에서 각각 다음 흐름을 2회 연속 2분 이내에 확인한다.

1. 로그인 후 Book 검색·선택
2. Reading이 자동 생성되지 않았음을 확인
3. 세 상태 중 하나를 선택해 Reading 생성
4. 상태를 비순차적으로 변경하고 완독일을 과거 날짜로 저장·수정
5. 완독 취소 시 날짜가 제거되는지 확인
6. Book을 다시 선택해 최근 완독 Reading이 먼저 열리는지 확인
7. `다시 읽기` 후 초기 상태를 선택해 별도 Reading 생성
8. 완독 상세의 비활성 `AI 독서노트 만들기` CTA 확인

추가 확인:

- JavaScript를 끈 상태에서도 생성·상태 변경·재독 흐름이 완료된다.
- Tab/Shift+Tab/Enter/Space로 모든 Form을 조작하고 focus를 잃지 않는다.
- 현재 상태, 비활성 CTA, 성공과 오류가 색상 외 텍스트로 구분된다.
- 다른 사용자의 Reading URL은 내용을 노출하지 않고 동일한 찾을 수 없음 결과를 보인다.
- 상태 저장 실패 시 이전 상태와 완독일이 화면과 DB에 유지된다.

## 완료 동기화

구현과 검증이 끝나면 `README.md`, `CHANGELOG.md`, 구현 계획의 IMP-030~033 완료 상태와
검증 근거를 수술적으로 동기화한다. Day 05 계획에는 Interview 시작 시 Reading 상태와
완독일을 잠그는 Service 연결 계약을 전달한다.

## 검증 결과 (2026-09-07)

- PostgreSQL에서 Reading/Book 선택 회귀 테스트 42개(동시 생성·재독·소유자 POST·DB
  오류 rollback 포함)를 통과했다.
- 실제 브라우저에서 1280px Desktop의 최초 완독 생성과 HTMX 상태 변경, 375px Mobile의
  키보드 완독 처리와 재독 생성을 확인했다. 두 뷰포트에서 현재 상태·성공 결과·비활성 CTA는
  텍스트로 구분됐고, Mobile 가로 스크롤은 수정 후 재확인했다.
- JavaScript 비활성 흐름은 서버 렌더링 Form과 Django test client로 검증했다. 실제
  브라우저에서 JavaScript를 비활성화한 2회 반복 검증은 현재 자동화 환경에서 실행 제어를
  제공하지 않아 배포 전 수동 확인 항목(T034, T037)으로 남는다.
