---
description: "Reading 생성 및 완독 관리 구현 작업 목록"
---

# 작업: Reading 생성 및 완독 관리

**입력**: `/specs/006-reading-completion-flow/`의 설계 문서

**사전 조건**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [Service 계약](contracts/service-contract.md), [UI 계약](contracts/ui-contract.md), [quickstart.md](quickstart.md)

**테스트**: 프로젝트 헌법, 구현 계획 및 quickstart가 관련 회귀 테스트를 요구한다. 각 사용자 스토리의 테스트를 구현 전 작성하고 PostgreSQL에서 실행한다.

**구성**: 작업은 사용자 스토리별로 묶어 독립 검증 가능하며, 모든 변경은 Django Template/HTMX 서버 렌더링 흐름과 Service Layer 계약을 따른다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일이며 앞선 미완료 작업에 의존하지 않아 병렬 실행 가능
- **[Story]**: 해당 사용자 스토리 (`US1`, `US2`, `US3`)
- 모든 설명은 변경할 정확한 파일 경로를 포함한다.

## 경로 규칙

- Django 소스: `src/`
- Django 테스트: `tests/`
- 기능 설계 문서: `specs/006-reading-completion-flow/`

---

## Phase 1: 설정 (공유 인프라)

**목적**: 신규 Reading 도메인을 Django 프로젝트에 인식시키고 URL 진입점을 준비한다.

- [X] T001 `src/readings/__init__.py`와 `src/readings/apps.py`에 `readings` Django 앱 기본 구조를 생성한다.
- [X] T002 `src/config/settings.py`에 `readings`를 등록하고 `src/config/urls.py`에 `readings.urls` include를 추가한다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 Reading 흐름이 공유하는 영속 모델, DB 무결성, migration 안전성을 확립한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 작업을 시작할 수 없다.

- [X] T003 `tests/readings/test_models.py`에 세 상태와 상태·완독일 모델 검증의 실패/성공 사례를 작성하고 `tests/readings/test_migrations.py`에 빈 DB migration round-trip 및 제약 검증을 작성한다.
- [X] T004 `src/readings/models.py`에 사용자·Book 소유, 상태 choices, `completed_on`, timestamp와 모델 수준 상태·날짜 검증을 가진 `Reading`을 구현한다.
- [X] T005 `src/readings/migrations/0001_initial.py`에 `readings_reading` table, FK, `readings_completion_date_state` CHECK 및 `readings_active_user_book_uniq` 조건부 unique index를 생성한다.
- [X] T006 `tests/readings/test_models.py`와 `tests/readings/test_migrations.py`에서 PostgreSQL CHECK, 활성 `(user, book)` 유일성, 여러 completed Reading 허용을 실행해 T004-T005의 DB 불변식을 검증한다.

**체크포인트**: 신규 table과 제약이 additive initial migration으로 생성되고, 모든 사용자 스토리가 공통 Reading 모델을 사용할 수 있다.

---

## Phase 3: 사용자 스토리 1 - 선택한 책으로 Reading 시작 또는 계속하기 (우선순위: P1) 🎯 MVP

**목표**: 사용자가 상태를 명시적으로 선택할 때만 첫 Reading 또는 재독을 만들고, 기존 활성 Reading이나 최근 완독 이력으로 안전하게 이어진다.

**독립 테스트**: 이력이 없는 Book에서 세 상태 중 하나를 골라 Reading을 만들고, 동일 Book의 반복·동시 시작은 같은 활성 Reading을 열며, 완독 이력만 있으면 명시적 재독 전 최근 완독을 보여주는지 확인한다.

### 사용자 스토리 1 테스트

- [X] T007 [US1] `tests/readings/test_services.py`에 최초 생성, 활성 Reading 재사용, 완독 이력의 자동 재독 거부, 명시적 재독과 과거 Reading 보존 Service 테스트를 작성한다.
- [X] T008 [US1] `tests/readings/test_services.py`에 `transaction=True`, thread별 DB connection과 barrier를 사용한 같은 사용자·Book 동시 최초/재독 생성 테스트를 작성한다.
- [X] T009 [P] [US1] `tests/readings/test_views.py`에 Book-entry의 이력 없음·활성·완독 이력 상태, 초기 생성·재독 POST, 로그인/CSRF/Book 없음 응답과 Credit/Coupon 요구 문구가 없음을 검증하는 View 테스트를 작성한다.
- [X] T010 [P] [US1] `tests/books/test_views.py`에 `books:select` 성공이 일반 요청에서는 redirect, HTMX 요청에서는 `HX-Redirect`로 `readings:book_entry`에 연결되는 회귀 테스트를 작성한다.

### 사용자 스토리 1 구현

- [X] T011 [US1] `src/readings/forms.py`에 최초/재독 상태 선택과 completed 상태의 오늘 기본값·과거 날짜 검증을 수행하는 Form을 구현한다.
- [X] T012 [US1] `src/readings/services.py`에 사용자 행 잠금과 짧은 atomic transaction을 사용하는 `create_initial_reading`, `create_rereading`, 생성 결과 및 정책 오류를 구현한다.
- [X] T013 [US1] `src/readings/urls.py`와 `src/readings/views.py`에 `book_entry`, `create`, `reread` URL/View를 구현하고, 소유자·Book 확인과 Service 오류를 안전한 화면 메시지로 매핑한다.
- [X] T014 [US1] `src/templates/readings/book_entry.html`에 이력 없음의 세 상태 선택, 활성 Reading의 계속 보기, 최근 완독 Reading 및 명시적 재독 선택 화면을 구현한다.
- [X] T015 [US1] `src/books/views.py`에서 Book 선택 성공을 일반 redirect 또는 `HX-Redirect`로 `readings:book_entry`에 연결하고, `src/templates/books/_selection_result.html`의 기존 선택 완료 화면이 더 이상 성공 경로에서 렌더링되지 않도록 정리한다.
- [X] T016 [US1] `src/static/css/app.css`에 `book_entry.html`의 Desktop/Mobile 상태 선택 Form, 오류와 키보드 focus 표시를 추가한다.
- [X] T017 [US1] `tests/readings/test_services.py`, `tests/readings/test_views.py`, `tests/books/test_views.py`를 실행하여 최초·반복·동시 생성과 Book 선택 연결을 검증한다.

**체크포인트**: 사용자는 Book 선택 뒤 상태를 직접 골라 한 번의 Reading을 시작할 수 있고, 재방문·중복 요청은 활성 Reading을 재사용하며 완독 이력은 명시적 재독으로만 보존된다.

---

## Phase 4: 사용자 스토리 2 - 독서 상태 및 완독일 관리 (우선순위: P1)

**목표**: 소유자는 세 상태 사이를 순서 제한 없이 변경하고, 완독일은 유효성·잠금·활성 Reading 충돌을 보존하면서 원자적으로 관리한다.

**독립 테스트**: 한 Reading을 모든 상태 사이에서 변경하고, 오늘/과거 완독일 저장과 수정, 완독 취소 시 날짜 제거, 미래 날짜·다른 활성 Reading·Interview 잠금 실패 시 이전 값 보존을 확인한다.

### 사용자 스토리 2 테스트

- [X] T018 [P] [US2] `tests/readings/test_forms.py`에 completed 전이와 날짜 수정의 오늘 기본값, 과거 날짜 허용, 미래·누락·불필요 날짜 거부 테스트를 작성한다.
- [X] T019 [P] [US2] `tests/readings/test_services.py`에 비순차 상태 전이, 같은 상태 멱등성, 완독일 수정·취소, 다른 활성 Reading 충돌과 Credit/Coupon 입력·의존성 없는 동작을 작성하고, `has_started_interview`를 `True`로 대체해 잠금 시 기존 상태와 날짜가 보존되는지 테스트한다.
- [X] T020 [P] [US2] `tests/readings/test_views.py`에 상태 변경 POST의 소유자 404, CSRF, 전체/HTMX 성공·Form 오류·DB 실패 rollback 응답 테스트를 작성한다.

### 사용자 스토리 2 구현

- [X] T021 [US2] `src/readings/forms.py`에 상태 전이와 별도 완독일 수정 의도를 구분하고 field 오류·접근성 속성을 제공하는 Form을 추가한다.
- [X] T022 [US2] `src/readings/services.py`에 `has_started_interview` 확장 지점과 소유 Reading 잠금, `change_reading_state`, 날짜 수정, 멱등 처리, 활성 Reading 충돌 및 `ReadingLockedError`를 구현한다.
- [X] T023 [US2] `src/readings/views.py`와 `src/readings/urls.py`에 `change_state` POST와 소유자 범위 조회를 구현하고 HTMX에는 동일한 상태·오류를 담은 panel 응답을 반환한다.
- [X] T024 [US2] `src/templates/readings/_reading_panel.html`에 상태 변경 Form, 날짜 입력, 성공 `aria-live`, field 연결 `role=alert`, 잠금·충돌 안내를 구현한다.
- [X] T025 [US2] `tests/readings/test_forms.py`, `tests/readings/test_services.py`, `tests/readings/test_views.py`를 실행하여 상태·완독일 원자성과 실패 rollback을 검증한다.

**체크포인트**: 상태와 완독일은 일관되게 저장되며, 잘못된 입력·경합·잠금은 어떤 부분 변경도 남기지 않고 다시 시도 가능한 안내를 제공한다.

---

## Phase 5: 사용자 스토리 3 - Reading 상세에서 현재 상태와 다음 행동 확인 (우선순위: P2)

**목표**: 소유자가 Desktop/Mobile Reading 상세에서 책 식별 정보, 현재 상태, 완독일과 상태별 다음 행동을 접근 가능하게 확인한다.

**독립 테스트**: 세 상태의 상세 화면에서 Book 정보와 현재 상태를 확인하고, completed에서만 완독일·비활성 AI 독서노트 CTA·재독 행동이 보이며 다른 사용자에게는 동일한 404가 반환되는지 확인한다.

### 사용자 스토리 3 테스트

- [X] T026 [US3] `tests/readings/test_views.py`에 Reading detail의 세 상태 표시, 선택 서지정보 누락 fallback, completed 전용 CTA/재독 노출, owner-only 404와 접근성 속성 테스트를 작성한다.

### 사용자 스토리 3 구현

- [X] T027 [US3] `src/readings/views.py`와 `src/readings/urls.py`에 owner-scoped `detail` GET을 구현하고 전체 page 또는 HTMX panel을 조합한다.
- [X] T028 [US3] `src/templates/readings/detail.html`과 `src/templates/readings/_reading_panel.html`에 Book 식별 정보, 텍스트 상태, completed 전용 완독일·재독 Form·비활성 `AI 독서노트 만들기` CTA 및 다음 단계 설명을 구현한다.
- [X] T029 [US3] `src/static/css/app.css`에 Reading detail의 1280px/375px responsive layout, 상태·비활성 CTA·오류의 비색상 구분과 focus 이동 스타일을 추가한다.
- [X] T030 [US3] `tests/readings/test_views.py`를 실행하여 상태별 detail 표시, CTA 범위와 소유권 비노출을 검증한다.

**체크포인트**: 사용자는 어느 기기에서도 현재 Reading과 다음 행동을 명확히 파악하며, Day 05 전에는 AI 독서노트 CTA가 기능하지 않는다는 상태가 접근 가능하게 전달된다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: migration 안전성, 문서 동기화 및 전체 품질 게이트로 기능을 완료한다.

- [X] T031 `src/manage.py`와 `src/readings/migrations/0001_initial.py`를 대상으로 `sqlmigrate readings 0001` 및 `makemigrations --check --dry-run readings`을 실행해 additive migration SQL과 migration drift가 없음을 확인한다.
- [X] T032 자동·수동 검증 절차를 실제 구현 URL, 테스트 경로와 CTA 동작에 맞게 수술적으로 갱신한다: `specs/006-reading-completion-flow/quickstart.md`.
- [X] T033 `README.md`, `CHANGELOG.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`에 Bundle 04A 구현 범위, 검증 근거 및 IMP-030~033 완료 상태를 수술적으로 동기화한다.
- [ ] T034 1280px Desktop과 375px Mobile에서 JavaScript 활성/비활성 및 키보드 전용 흐름을 각각 2회 실행하고, 각 실행이 2분 이내이며 가로 scroll·focus 손실·색상 전용 상태 표현이 없음을 검증 결과로 기록한다: `specs/006-reading-completion-flow/quickstart.md`.
- [X] T035 `tests/readings/`, `tests/books/test_views.py`, `src/`에 `uv run ruff format --check src tests`, `uv run ruff check src tests`, `uv run python src/manage.py check`, `uv run pytest tests/readings tests/books/test_views.py -v`, `uv run python scripts/verify.py`를 실행하고 실패를 분류·해결한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **설정 (Phase 1)**: 의존성 없음 — T001과 T002를 순서대로 완료한다.
- **기반 (Phase 2)**: 설정 완료 후 시작 — T003 → T004 → T005 → T006으로 DB 계약을 확정한다.
- **US1 (Phase 3)**: 기반 완료 후 시작 — 테스트 T007~T010을 먼저 작성한 뒤 T011 → T012 → T013~T016 → T017 순서로 진행한다.
- **US2 (Phase 4)**: US1의 Form·Service·panel 기반을 사용하므로 US1 완료 후 시작 — T018~T020 → T021 → T022 → T023 → T024 → T025 순서다.
- **US3 (Phase 5)**: US2의 detail panel과 상태 변경 계약을 확장하므로 US2 완료 후 시작 — T026 → T027 → T028 → T029 → T030 순서다.
- **마무리 (Phase 6)**: 모든 사용자 스토리 완료 후 T031~T035를 수행한다.

### 사용자 스토리 의존성

- **US1 (P1)**: 기반 단계만 완료되면 시작 가능하며 MVP다.
- **US2 (P1)**: US1에서 만든 `Reading` 생성 Form·Service·View 구조에 상태 변경을 추가한다.
- **US3 (P2)**: US2의 공용 Reading panel을 사용해 표시와 다음 행동을 완성한다.

### 각 사용자 스토리 내부

- 테스트는 해당 구현 작업보다 먼저 작성하고, 변경 전 실패 및 구현 후 성공을 확인한다.
- Form은 Service보다 먼저, Service는 View보다 먼저, View는 Template/CSS 연결보다 먼저 구현한다.
- 외부 Provider, Interview 생성, Book Knowledge, Credit 변경은 어떤 단계에도 추가하지 않는다.

## 병렬 작업 기회

- **US1**: T007~T010은 서로 다른 테스트 책임으로 병렬 착수할 수 있다. 단, T007과 T008은 같은 파일을 수정하므로 실제 동시 편집 대신 테스트 범위를 합쳐 순차 편집한다.
- **US2**: T018~T020은 서로 다른 파일이므로 병렬 가능하다. 이후 T021~T024는 shared Form·Service·View·panel 의존성 때문에 순차 진행한다.
- **US3**: T026 이후 detail View, Template/panel, CSS는 각 결과물을 확인하며 순차 진행한다.

## 병렬 예시: 사용자 스토리 1

```text
Task: "tests/readings/test_views.py에 Book-entry, 생성·재독 POST, 인증·CSRF 계약 테스트 작성"
Task: "tests/books/test_views.py에 Book 선택 성공의 redirect/HX-Redirect 회귀 테스트 작성"
```

## 구현 전략

### MVP 우선 (사용자 스토리 1만)

1. Phase 1과 Phase 2에서 `readings` 앱, additive migration, DB 불변식을 완료한다.
2. Phase 3에서 명시적 최초 생성·재독·활성 Reading 재사용과 Book 선택 연결을 구현한다.
3. US1 테스트와 PostgreSQL 동시성 테스트를 통과시켜 독립 검증한다.
4. 이후에만 상태·완독일 관리와 상세 UX를 추가한다.

### 점진적 제공

1. Phase 1 + Phase 2 → 안전한 Reading 영속 기반
2. US1 → Book 선택에서 Reading 시작/계속/재독까지의 MVP
3. US2 → 정확한 상태와 완독일 관리
4. US3 → Reading detail의 명확한 다음 행동과 접근성
5. Phase 6 → migration, 문서, 전체 품질 게이트 동기화

## 참고 사항

- [P]는 서로 다른 파일과 미완료 의존성이 없는 작업에만 표시했다.
- 각 사용자 스토리 작업에는 추적 가능한 `[US#]` 라벨과 정확한 파일 경로가 있다.
- T007과 T008은 같은 `tests/readings/test_services.py`를 편집하므로 한 작업자가 연속으로 처리한다.
- 완료 후 Day 05는 `change_reading_state`의 Interview 잠금 확장 계약을 구현해야 한다.
