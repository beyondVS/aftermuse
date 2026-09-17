# Tasks: Reflection 결과·수정과 Home 재진입

**Input**: Design documents from `/specs/017-reflection-result-edit-home/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: 기능 사양과 헌법이 모델·migration·service·view·Home·command의 결정적 테스트를 요구하므로, 각 사용자 스토리에서 테스트를 먼저 작성하고 실패를 확인한 뒤 구현한다.

**Organization**: 각 사용자 스토리는 가능한 한 독립적으로 구현·검증할 수 있도록 테스트와 구현 작업을 같은 단계에 배치한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 미완료 작업과 파일이 겹치지 않고 병렬 수행 가능
- **[Story]**: 작업이 속한 사용자 스토리 (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- 모든 작업 설명에는 변경하거나 검증할 정확한 파일 경로를 포함한다.

## Path Conventions

- 저장소 루트 기준 단일 Django 프로젝트 (`src/`, `tests/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 계획에서 확정한 안전한 Markdown 렌더링 의존성을 pyproject.toml에 추가하고 환경을 동기화한다.

- [X] T001 `Markdown~=3.10.3` 런타임 의존성을 추가하고 lockfile을 동기화한 뒤 import 가능한지 확인한다: `pyproject.toml`, `uv.lock`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리가 공유하는 Reflection 완료 상태 모델 제약과 단일 표준 migration 기반을 확립한다.

**⚠️ CRITICAL**: 이 단계가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

- [X] T002 [P] `Reflection.Status.COMPLETED` 추가, `completed_at` 일관성 `(DRAFT, completed_at IS NULL)` / `(COMPLETED, completed_at IS NOT NULL)`, 기존 DRAFT 보존 및 단일 migration 왕복을 검증하는 실패 테스트를 추가한다: `tests/reflections/test_models.py`, `tests/reflections/test_migrations.py`
- [X] T003 `Reflection.Status.COMPLETED` 추가 및 `(DRAFT, completed_at IS NULL)` 또는 `(COMPLETED, completed_at IS NOT NULL)` 상태 불변식을 모델에 구현한다: `src/reflections/models.py`
- [X] T004 기존 draft-only CHECK 제약을 새 완료 제약으로 교체하는 단일 표준 migration을 구현한다: `src/reflections/migrations/0010_reflection_completed_status.py`
- [X] T005 Foundational 모델 및 migration 테스트를 실행해 상태 제약과 마이그레이션이 통과하는지 확인한다: `tests/reflections/test_models.py`, `tests/reflections/test_migrations.py`

**Checkpoint**: Reflection 완료 상태를 지원하는 DB 스키마와 모델 제약이 준비되어 사용자 스토리 구현을 시작할 수 있다.

---

## Phase 3: User Story 1 — 생성된 독서노트를 내 기록으로 읽기 (Priority: P1) 🎯 MVP

**Goal**: 소유자가 Reflection을 책 정보와 안전하게 렌더링된 본문이 있는 읽기 중심 결과 화면으로 확인하고 수정 또는 Home 이동을 선택한다.

**Independent Test**: 짧고 긴 소유자 Reflection을 결과 URL로 열어 책 메타데이터(제목, 저자), 작성일, 전체 현재 본문, DRAFT 상태(`작성 중`), `[수정] [완료] [Home으로]` 행동을 확인하고, 타인 및 없는 ID 404 및 사용자 입력 raw HTML 비실행 보안 불변식을 검증한다.

### Tests for User Story 1

- [X] T006 [P] [US1] 소유자 조회, bounded `select_related` 조회, 책 메타데이터, 현재 본문 선택(`revised_markdown` 우선), 기본 Markdown 구조(headings, 문단, 목록, 인용, 강조) 보존, 사용자 입력 raw HTML 비실행 보안 불변식, DRAFT 행동(`[수정] [완료] [Home으로]`), AI 작성자/Chat transcript 비노출 및 타인/없는 기록 404를 검증하는 실패 테스트를 추가한다: `tests/reflections/test_views.py`, `tests/reflections/test_drafts.py`

### Implementation for User Story 1

- [X] T007 [US1] `revised_markdown` 우선 현재 본문 선택(`current_markdown`)과 사용자 입력 raw HTML이 브라우저에서 실행되지 않도록 안전하게 Markdown 변환하는 렌더링 함수를 구현한다: `src/reflections/drafts.py`
- [X] T008 [US1] 소유자 범위 Reflection 결과 조회 및 안전 렌더 context를 전달하는 뷰와 URL을 구현한다: `src/reflections/views.py`, `src/reflections/urls.py`
- [X] T009 [US1] 책 제목, 선택적 저자, 작성일, 전체 본문, 상태 텍스트(`작성 중`) 및 `[수정] [완료] [Home으로]` 행동을 갖춘 읽기 중심 결과 화면 템플릿을 구현한다: `src/templates/reflections/reflection_detail.html`
- [X] T010 [US1] 긴 글의 문단·제목·목록 순서를 유지하고 Desktop/Mobile 폭에서 읽히도록 본문과 버튼 group wrapping, 키보드 focus 표시 등 반응형 스타일을 추가한다: `src/static/css/app.css`
- [X] T011 [US1] 사용자 스토리 1의 테스트를 실행해 결과 화면 읽기 경험과 보안 불변식 독립 인수를 검증한다: `tests/reflections/test_drafts.py`, `tests/reflections/test_views.py`

**Checkpoint**: 수정 저장과 Home 카드가 없어도 소유자의 독서노트 읽기 경험(MVP)을 독립적으로 제공한다.

---

## Phase 4: User Story 2 — 초안을 수정하고 최종 기록으로 확인하기 (Priority: P1)

**Goal**: 소유자가 DRAFT 본문을 안전하게 수정·저장(DRAFT 유지)하고, 별도 확인 후 Reflection과 Interview를 원자적으로 완료하며, 완료본은 읽기 전용으로 보존한다.

**Independent Test**: 수정 화면 GET에서 최신 본문을 확인하고 유효한 저장 후 결과 화면 PRG redirect를 검증하며, 비공백/20,000자 초과 validation 실패를 확인한다. 완료 확인 GET(무변경) 후 완료 POST 시 Reflection(COMPLETED)과 Interview(COMPLETED)의 원자적 전이를 확인하고, 완료 후 수정 요청이 차단됨을 검증한다.

### Tests for User Story 2

- [X] T012 [P] [US2] DRAFT 본문 수정 저장(최초 `draft_markdown` 보존 및 `revised_markdown` 갱신), Form 유효성(비공백, 최대 20,000자), 단일 트랜잭션 내 원자적 완료 전환(`Reflection` + `Interview` COMPLETED), 완료 시각 보존, 완료 후 읽기 전용화(`[수정] [완료]` 버튼 비노출), 완료본 수정 거부(차단), 중복 완료 멱등 수렴을 검증하는 실패 테스트를 추가한다: `tests/reflections/test_models.py`, `tests/reflections/test_drafts.py`, `tests/reflections/test_views.py`

### Implementation for User Story 2

- [X] T013 [US2] 현재 본문 시작값과 비공백 1–20,000자 유효성 검사를 수행하는 수정 Form을 구현한다: `src/reflections/forms.py`
- [X] T014 [US2] DRAFT 본문 수정본을 `revised_markdown`에 저장하는 `save_reflection_revision()`과 단일 트랜잭션에서 Reflection과 Interview를 원자적으로 완료하는 `complete_reflection()` 서비스를 구현한다: `src/reflections/drafts.py`
- [X] T015 [US2] 수정 화면 GET/POST(성공 시 결과 화면 PRG redirect, 완료본 수정 차단) 및 완료 확인 GET/POST 뷰와 URL을 구현한다: `src/reflections/views.py`, `src/reflections/urls.py`
- [X] T016 [US2] 최신 본문 편집 textarea와 `[취소] [수정 저장]` 버튼을 갖춘 수정 화면 및 취소 링크와 명시적 완료 POST 버튼을 갖춘 완료 확인 화면을 구현한다: `src/templates/reflections/reflection_edit.html`, `src/templates/reflections/reflection_complete_confirm.html`
- [X] T017 [US2] 완료본 결과 화면에서 `[수정] [완료]` 버튼을 숨기고 완료 안내 텍스트를 표시하도록 결과 화면 템플릿을 업데이트한다: `src/templates/reflections/reflection_detail.html`
- [X] T018 [US2] 사용자 스토리 2의 Form, Service, View 테스트를 실행해 수정 저장과 원자적 완료 계약을 독립 검증한다: `tests/reflections/test_models.py`, `tests/reflections/test_drafts.py`, `tests/reflections/test_views.py`

**Checkpoint**: AI 초안이 안전하게 보존되면서 사용자 수정본이 반영되고, 명시적 완료 시 원자적으로 상태가 확정된다.

---

## Phase 5: User Story 3 — Home에서 최근 독서노트로 돌아가기 (Priority: P1)

**Goal**: 인증 사용자가 Home에서 마지막 활동(생성·수정·완료) 기준 가장 최근인 자신의 Reflection 1건을 상태(`작성 중` / `완료`)와 함께 확인하고 결과 화면으로 재진입한다.

**Independent Test**: Reflection 없음, DRAFT 1건, COMPLETED 1건, 여러 건의 Reflection 및 다중 사용자 조건에서 `updated_at DESC, id DESC` 최신 1건 선택, 소유자 격리, 상태별 텍스트, 결과 화면 링크 및 N+1 없는 고정 query count를 검증한다.

### Tests for User Story 3

- [X] T019 [P] [US3] Home의 최근 Reflection 조회(`updated_at DESC, id DESC`, limit 1), 소유자 격리, DRAFT(`작성 중`) / COMPLETED(`완료`) 텍스트, 결과 화면 이동 링크, 빈 상태 보존 및 고정 query count를 검증하는 실패 테스트를 추가한다: `tests/test_home_page.py`

### Implementation for User Story 3

- [X] T020 [US3] `get_home_reading_groups()`에 현재 사용자의 최근 Reflection을 `select_related("interview__reading__book")`, `-updated_at`, `-id`, limit 1로 조회하는 단일 bounded query와 `recent_reflection` context를 추가한다: `src/config/views.py`
- [X] T021 [US3] Reflection이 있을 때만 책 정보, 상태 텍스트(`작성 중` / `완료`), 결과 화면 링크를 표시하는 최근 독서노트 카드를 Home 템플릿에 추가하고 기존 Reading/Interview/빈 상태를 보존한다: `src/templates/pages/home.html`
- [X] T022 [US3] 최근 독서노트 카드의 반응형 스타일 및 focus-visible 스타일을 추가한다: `src/static/css/app.css`
- [X] T023 [US3] 사용자 스토리 3의 Home 테스트를 실행해 최근 활동 선택, 상태 텍스트, 사용자 격리 및 쿼리 수 계약을 독립 검증한다: `tests/test_home_page.py`

**Checkpoint**: 전체 Library 없이도 사용자는 Home의 최근 독서노트 카드를 통해 자신의 작업 중 또는 완료된 독서노트로 언제든 재진입할 수 있다.

---

## Phase 6: User Story 4 — 대표 책 세트로 다음 검증 준비하기 (Priority: P2)

**Goal**: 명시적 비운영 커맨드로 승인 Seed Knowledge 소설 1권·비문학 1권(READY)과 Knowledge가 없는 문학 1권(READY_LIMITED)을 원자적이고 멱등하게 준비한다.

**Independent Test**: 빈 DB와 기존 Book DB에서 커맨드를 연속 두 번 실행해 정확히 3권(READY 2권, READY_LIMITED 1권), READY 2권의 승인 Claim 총 8개 적용, LIMITED Claim 0개, 두 번째 실행 신규 생성 0개, 기존 서지정보·사용자 데이터 무변경 및 오류 시 rollback을 검증한다.

### Tests for User Story 4

- [X] T024 [P] [US4] 3권 descriptor 형식 검증, ISBN13 멱등 생성 및 기존 메타데이터 보존, READY 2권 승인 Claim 총 8개 적용, LIMITED Claim 0개, 두 번 실행 수렴, 사용자 데이터 무변경, 불일치/실패 시 rollback을 검증하는 실패 테스트를 추가한다: `tests/knowledge/test_validation_books.py`

### Implementation for User Story 4

- [X] T025 [US4] 《1984》(fiction READY), 《Thinking, Fast and Slow》(nonfiction READY), 《The Left Hand of Darkness》(fiction READY_LIMITED) 3권의 정확한 메타데이터와 기대 상태를 담은 descriptor JSON을 추가한다: `src/knowledge/seed_data/validation_books.json`
- [X] T026 [US4] descriptor 검증 후 ISBN13 `get_or_create`, 기존 메타데이터 보존, 승인 Seed 적용 및 LIMITED 무지식을 보장하는 원자적 데이터 준비 서비스를 구현한다: `src/knowledge/services.py`
- [X] T027 [US4] application 시작이나 migration에서 자동 실행되지 않는 명시적 `prepare_validation_books` management command를 구현한다: `src/knowledge/management/commands/prepare_validation_books.py`
- [X] T028 [US4] 사용자 스토리 4와 기존 Seed 회귀 테스트를 실행해 멱등성, 원자성 및 승인 Claim 계약을 검증한다: `tests/knowledge/test_validation_books.py`, `tests/knowledge/test_seed_command.py`

**Checkpoint**: Day 13 검증용 3권이 운영/사용자 데이터에 영향 없는 명시적 command로 반복 준비된다.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 마이그레이션 점검, 관련 범위 전체 회귀, 표준 품질 게이트 및 문서 동기화를 마무리한다.

- [X] T029 [P] migration `0010`에 대해 `makemigrations --check --dry-run` 및 `sqlmigrate`를 실행해 스키마 drift가 없는지 점검한다: `src/reflections/migrations/0010_reflection_completed_status.py`
- [X] T030 [P] `reflections`, `knowledge`, Home 페이지 관련 단위/통합 테스트 전체를 실행해 컴포넌트 간 회귀가 없는지 검증한다: `tests/reflections/`, `tests/knowledge/`, `tests/test_home_page.py`
- [X] T031 표준 전체 품질 게이트를 실행해 코딩 표준과 타입 일관성을 점검한다: `scripts/verify.py`
- [X] T032 [P] 구현 결과와 실제 동작, 명시적 검증 command, Day 12 완료 상태 및 사용자 관점 변경 사항을 관련 문서에 동기화한다: `README.md`, `docs/README.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`, `CHANGELOG.md`, `specs/017-reflection-result-edit-home/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 후 시작; 모든 사용자 스토리의 선행 차단 조건
- **User Story 1 (Phase 3)**: Foundational 완료 후 시작 (Core MVP)
- **User Story 2 (Phase 4)**: Foundational 완료 후 시작; 결과 화면(US1) 기반으로 PRG 및 UI 연계
- **User Story 3 (Phase 5)**: Foundational 완료 후 시작; 결과 화면(US1) 링크 연계
- **User Story 4 (Phase 6)**: Foundational 완료 후 US1~US3과 독립적으로 병렬 수행 가능
- **Polish (Phase 7)**: 모든 사용자 스토리가 완료된 후 실행

### User Story Dependencies

```text
Phase 1 (Setup) → Phase 2 (Foundational) ─┬→ Phase 3 (US1 - MVP) ─┬→ Phase 4 (US2)
                                          │                       └→ Phase 5 (US3)
                                          └→ Phase 6 (US4)

Phase 3 + Phase 4 + Phase 5 + Phase 6 → Phase 7 (Polish)
```

### Within Each User Story

- 해당 스토리의 테스트를 먼저 작성하고 대상 동작의 실패를 확인한다.
- 모델/서비스/폼을 뷰와 템플릿보다 먼저 구현한다.
- 정상 흐름과 함께 소유권 격리, 상태 제약, 보안 불변식을 충족한다.
- 스토리별 독립 테스트가 통과한 뒤 다음 체크포인트로 이동한다.

### Parallel Opportunities

- T002 테스트 작성은 Phase 1 환경 준비와 병렬 준비 가능하다.
- Foundational 완료 후 US1의 T006 테스트와 US4의 T024 테스트는 완전히 독립적인 도메인이므로 병렬 작성이 가능하다.
- US1 완료 후 US2(수정/완료)와 US3(Home 재진입)은 서로 다른 파일(`reflections/forms.py`, `config/views.py`)을 다루므로 병렬 진행이 가능하다.
- Polish 단계의 T029, T030, T032는 병렬 수행 가능하다.

---

## Parallel Example: User Story 2 & User Story 4

```bash
# US1 완료 후, 서로 다른 도메인 작업 동시 진행:
Task: "T012 [P] [US2] DRAFT 수정 저장 및 원자적 완료 테스트" (tests/reflections/)
Task: "T024 [P] [US4] 3권 descriptor 및 준비 커맨드 테스트" (tests/knowledge/)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (`pyproject.toml`, `uv.lock`) 완료
2. Phase 2: Foundational (단일 migration `0010`, 모델 제약) 완료
3. Phase 3: User Story 1 (결과 화면 읽기, 안전한 Markdown 렌더링) 완료
4. **독립 검증**: 소유자가 Reflection 결과 화면을 안전한 Markdown 에세이로 읽을 수 있는지 확인 (Day 12 핵심 MVP 달성!)

### Incremental Delivery

1. **기반**: 단일 migration `0010` 및 상태 제약
2. **US1**: 읽을 수 있는 소유자 전용 독서노트 결과 화면 (MVP)
3. **US2**: 사용자 통제권을 보장하는 수정 저장 및 원자적 최종 완료
4. **US3**: Home 최근 독서노트 카드 통한 안전한 재진입
5. **US4**: Day 13 검증을 위한 3권 멱등 데이터 준비 (IMP-100)
6. **Polish**: 마이그레이션 점검, 회귀 검증, 품질 게이트 및 문서 동기화

---

## Notes

- `[P]` 작업은 선행 작업 완료 후 서로 다른 파일에서 독립적으로 병렬 수행 가능한 작업이다.
- `[Story]` 태그는 추적성을 위해 작업이 속한 사용자 스토리(`[US1]`~`[US4]`)를 명시한다.
- 완료본의 재수정 또는 DRAFT 복귀, 전체 Library, 공유, Credit, Reader Insight 등은 이번 범위에 포함하지 않는다.
- 각 체크박스는 코드 작성과 검증이 가능한 하나의 구체적 결과를 나타낸다.
