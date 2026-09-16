# Tasks: Day 11 — Interview 상호작용 완결과 Reflection 생성 Transition

**Input**: Design documents from `/specs/016-interview-reflection-transition/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: 이 기능은 상태 전이, 동시성, 소유권, 마이그레이션 안전성을 포함하므로 각 사용자 스토리의 테스트를 구현보다 먼저 작성하고 실패를 확인한다.

**Organization**: 작업은 사용자 스토리별로 묶어 각 스토리를 독립적으로 구현하고 검증할 수 있게 구성한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 선행 작업 완료 후 다른 파일에서 독립적으로 병렬 수행 가능
- **[Story]**: 사용자 스토리 매핑 (`[US1]`, `[US2]`, `[US3]`)
- 모든 작업 설명은 변경 또는 검증 대상의 정확한 파일 경로를 포함한다.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 구현 전에 실제 migration graph와 설계 문서의 파일명을 일치시킨다.

- [X] T001 `src/reflections/migrations/`의 현재 leaf가 `0007_reflection`인지 확인한다. 다르면 구현을 시작하지 않고 실제 leaf에 맞춰 T005, T028 및 `specs/016-interview-reflection-transition/quickstart.md`의 migration 번호를 함께 조정한다.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 사용자 스토리가 공유하는 skip 상태와 종료 상태의 영속성 계약을 먼저 확립한다.

**⚠️ CRITICAL**: 이 단계가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

- [X] T002 [P] `InterviewTurn.user_skipped_at`의 nullable/불변성/answer 상호 배타 계약과 `Interview.Status.ENDED_NO_REFLECTION`을 검증하는 실패 테스트를 `tests/reflections/test_models.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T003 [P] 기존 answer 데이터 보존, `answer`와 `user_skipped_at` 동시 설정 거부, 신규 status 허용, forward/reverse migration을 검증하는 실패 테스트를 `tests/reflections/test_migrations.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T004 `InterviewTurn.user_skipped_at`, model validation/immutability, `ENDED_NO_REFLECTION`, DB constraint state를 `src/reflections/models.py`에 구현해 T002의 모델 계약을 충족한다.
- [X] T005 T001에서 `0007_reflection` leaf가 확인된 경우에만 `SET LOCAL lock_timeout='2s'`, nullable column 추가, 두 CHECK constraint의 `NOT VALID` 설치와 별도 `VALIDATE CONSTRAINT`를 `src/reflections/migrations/0008_interview_turn_user_skip.py` 및 `src/reflections/migrations/0009_validate_interview_turn_user_skip.py`에 `SeparateDatabaseAndState`와 `atomic=False` 요구사항에 맞게 구현한다.
- [X] T006 `tests/reflections/test_models.py`와 `tests/reflections/test_migrations.py`를 실행하고 `src/manage.py makemigrations --check --dry-run reflections`로 foundational schema 계약과 migration state 일치를 검증한다.

**Checkpoint**: skip/answer 상호 배타성과 Reflection 없는 종료 상태를 코드와 DB가 함께 강제한다.

---

## Phase 3: User Story 1 — 답변을 지키며 Reflection 생성 완료하기 (Priority: P1) 🎯 MVP

**Goal**: `REFLECTION_READY` Interview에서 Reflection 생성을 한 번의 명시적 동작으로 수행하고, 성공·실패·재시도·동시 요청 모두에서 답변과 단일 Reflection을 보존한다.

**Independent Test**: Reflection 준비 상태의 owner Interview로 생성 성공, provider 실패 후 재시도, 기존 Reflection 재사용, 동시 저장 충돌을 각각 실행해 로딩/오류/redirect 화면, 답변 보존, owner 범위, Reflection 개수 1개를 확인한다.

### Tests for User Story 1

- [X] T007 [P] [US1] 기존 Reflection이면 provider 미호출, provider 실패 시 원본 답변 보존, `ReflectionDraftConflict` 시 owner Reflection으로 수렴, 성공 시 단일 Reflection 반환을 검증하는 실패 테스트를 `tests/reflections/test_drafts.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T008 [P] [US1] 인증/소유권/CSRF, stale 상태 409, provider 실패 503와 재시도 UI, normal/HTMX 성공 redirect, `hx-indicator`·`hx-disabled-elt`·`hx-sync` 및 status/alert 계약, 최소 결과 화면의 body/edit/complete 비노출을 검증하는 실패 테스트를 `tests/reflections/test_views.py`에 추가하고 예상한 이유로 실패하는지 확인한다.

### Implementation for User Story 1

- [X] T009 [US1] owner Reflection 사전 조회, transaction 밖 provider 호출, `save_reflection_draft` 저장, 충돌 후 owner-scoped 재조회로 성공 수렴하는 generate-or-get orchestration을 `src/reflections/drafts.py`에 구현한다.
- [X] T010 [US1] `POST /reflections/interviews/{id}/reflection/generate/`와 `GET /reflections/{reflection_id}/`의 auth/CSRF/owner/state/error/redirect 계약을 `src/reflections/views.py`와 `src/reflections/urls.py`에 구현한다.
- [X] T011 [US1] 생성 trigger와 loading/disabled/`hx-sync="this:drop"`, 안전한 오류와 Retry, book과 생성 완료 사실만 표시하는 최소 결과 화면을 `src/templates/reflections/interview_reflection_ready.html`, `src/templates/reflections/_interview_reflection_ready.html`, `src/templates/reflections/_reflection_generation_error.html`, `src/templates/reflections/reflection_draft_ready.html`에 구현한다.
- [X] T012 [US1] 생성 중/실패/재시도/최소 결과 상태의 focus-visible, disabled, status/alert 표현과 대표 Desktop·Mobile breakpoint에서 생성 행동과 상태 영역을 유지하는 반응형 규칙을 `src/static/css/app.css`에 추가한다.
- [X] T013 [US1] `tests/reflections/test_drafts.py`와 `tests/reflections/test_views.py`의 US1 테스트를 실행해 독립 테스트 기준과 Reflection 단일성 계약을 검증한다.

**Checkpoint**: User Story 1만 배포해도 준비된 Interview에서 안전하게 Reflection 초안을 생성하고 최소 결과 화면에 도달할 수 있다.

---

## Phase 4: User Story 2 — 답하기 어려운 질문 건너뛰기 (Priority: P1)

**Goal**: 사용자가 빈 answer 없이 질문을 명시적으로 건너뛰고, 재요청·동시 요청·provider 실패에도 하나의 terminal outcome과 올바른 budget/coverage를 유지한다.

**Independent Test**: 진행 중 Interview에서 skip을 수행해 다음 질문 또는 종료 상태로 이동하는지, 반복 skip이 멱등인지, answer/skip 경합에서 하나만 남는지, 모든 질문을 skip하면 Reflection 없이 종료되는지 확인한다.

### Tests for User Story 2

- [X] T014 [P] [US2] `NextQuestionContext`가 explicit skip을 low-information answer 및 `next_question_skipped_at`과 구분하고 `answer=None`, `user_skipped=True`, 누적 `skipped_questions`, 변경 없는 coverage를 provider payload에 전달하는 실패 테스트를 `tests/integrations/llm/test_structured_providers.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T015 [P] [US2] skip 선저장, provider 실패 후 resume, 반복 요청 멱등성, resolved budget, coverage 불변, answer/skip 경합, 답변 0개 종료를 검증하는 실패 테스트를 `tests/reflections/test_services.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T016 [P] [US2] skip endpoint의 인증/소유권/CSRF, stale 상태 409, provider 실패 503 recovery fragment, 즉시 Loading/disabled 상태, HTMX focus/retarget 복구, Reflection 없는 종료 화면을 검증하는 실패 테스트를 `tests/reflections/test_views.py`에 추가하고 예상한 이유로 실패하는지 확인한다.

### Implementation for User Story 2

- [X] T017 [US2] optional answer, `user_skipped`, `skipped_questions`, skip 시 `meaning=None`/`low_information=False` 계약을 `src/integrations/llm/contracts.py`, `src/integrations/llm/interview.py`, `src/integrations/llm/fake.py`에 구현한다.
- [X] T018 [US2] `question_count`, `answered_count`, `user_skipped_count`, `resolved_count` budget와 skip용 terminal decision을 `src/reflections/services.py`에 구현한다.
- [X] T019 [US2] 짧은 transaction의 skip 선저장, transaction 밖 다음 질문 생성, 재검증 후 insert, 실패 후 resume, answer/skip 상호 배타 수렴을 `src/reflections/services.py`에 구현한다.
- [X] T020 [US2] 답변이 하나 이상이면 `REFLECTION_READY`, 답변이 0개면 `ENDED_NO_REFLECTION`로 끝나는 목적지 매핑과 기존 answer 경로의 skip 충돌 처리를 `src/reflections/services.py`에 구현한다.
- [X] T021 [US2] `POST /reflections/interviews/{id}/turns/{sequence}/skip/`의 owner/state/idempotency/error/HTMX 계약과 no-reflection destination을 `src/reflections/views.py`와 `src/reflections/urls.py`에 구현한다.
- [X] T022 [US2] 질문별 건너뛰기 control, provider 실패 후 동일 turn 재개 fragment, Reflection 없는 종료 안내를 `src/templates/reflections/interview_detail.html`, `src/templates/reflections/_interview_question.html`, `src/templates/reflections/_interview_skip_error.html`, `src/templates/reflections/interview_ended_no_reflection.html`에 구현한다.
- [X] T023 [US2] skip/answer control과 오류/종료 상태의 keyboard focus, disabled, status/alert 스타일 및 대표 Desktop·Mobile breakpoint에서 Skip/Retry 행동을 유지하는 반응형 규칙을 `src/static/css/app.css`에 추가하고, HTML·CSS 계약을 포함한 `tests/integrations/llm/test_structured_providers.py`, `tests/reflections/test_services.py`, `tests/reflections/test_views.py`의 US2 테스트를 실행한다.

**Checkpoint**: User Story 2는 User Story 1의 UI에 의존하지 않고 진행 중 Interview fixture로 독립 검증할 수 있으며, 모든 질문을 skip한 경우 Reflection을 만들지 않는다.

---

## Phase 5: User Story 3 — 내부 상태 대신 친화적인 안내로 Interview 진행하기 (Priority: P2)

**Goal**: READY/READY_LIMITED 같은 내부 용어를 숨기고, 제한된 근거에서도 책 사실을 지어내지 않는 기억·감정 중심 안내를 제공한다.

**Independent Test**: READY와 READY_LIMITED Interview를 각각 열어 내부 enum/RAG/Knowledge readiness 문구가 보이지 않고, READY_LIMITED에서는 비오류성 안내와 기억·감정 중심 질문만 노출되는지 확인한다.

### Tests for User Story 3

- [X] T024 [P] [US3] READY/READY_LIMITED 화면에 내부 enum, RAG, Knowledge readiness가 노출되지 않고 제한 상태가 친화적인 비오류 문구로 표시되는 실패 테스트를 `tests/reflections/test_views.py`에 추가하고 예상한 이유로 실패하는지 확인한다.
- [X] T025 [P] [US3] READY_LIMITED와 skip 누적 context에서도 unsupported book fact가 질문에 포함되지 않고 memory/feeling 중심 질문으로 fallback하는 회귀 테스트를 `tests/integrations/llm/test_reflection.py`에 추가한다.

### Implementation for User Story 3

- [X] T026 [US3] READY/READY_LIMITED의 내부 상태 표현을 사용자 친화적 시작/진행 안내로 교체하고 제한 상태를 오류처럼 표시하지 않도록 `src/templates/reflections/interview_start.html`과 `src/templates/reflections/interview_detail.html`을 수정한다.
- [X] T027 [US3] `tests/reflections/test_views.py`와 `tests/integrations/llm/test_reflection.py`의 US3 테스트를 실행해 copy 격리와 unsupported fact 방지 계약을 검증한다.

**Checkpoint**: 세 사용자 스토리가 각각의 독립 테스트 기준을 충족한다.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 전체 계약 정합성, 문서 동기화, migration SQL, 접근성, 표준 품질 게이트를 마무리한다.

- [X] T028 `src/manage.py sqlmigrate reflections 0008` 및 `0009` 결과에서 nullable add, `NOT VALID`, 별도 `VALIDATE CONSTRAINT`, lock timeout을 검토하고 실제 명령과 확인 결과를 `specs/016-interview-reflection-transition/quickstart.md`에 기록한다.
- [X] T029 [P] auth/owner/CSRF, invalid state, repeated request, answer/skip 경합, provider failure/retry, all-skip 종료를 묶은 cross-story 회귀 테스트를 `tests/reflections/test_views.py`, `tests/reflections/test_services.py`, `tests/reflections/test_drafts.py`에서 보강한다.
- [X] T030 기능 범위와 Day 12 비목표, 사용자 흐름, 신규 endpoint/status를 `README.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`, `CHANGELOG.md`에 현재 프로젝트 문서 관례대로 동기화한다.
- [X] T031 `tests/reflections/`와 `tests/integrations/llm/`의 관련 테스트 전체 및 `src/manage.py makemigrations --check --dry-run reflections`를 실행하고 결과를 `specs/016-interview-reflection-transition/quickstart.md`에 기록한다.
- [X] T032 owner leakage, 중복 Reflection, 내부 상태 노출, unsafe migration, 모든 skip 뒤 Reflection 생성 가능성이 남지 않았는지 `specs/016-interview-reflection-transition/spec.md`, `plan.md`, `contracts/interview-reflection-transition.md`와 구현 diff를 대조해 독립 검토하고 결과를 `specs/016-interview-reflection-transition/quickstart.md`에 기록한다.
- [X] T033 `uv run python scripts/verify.py`를 실행하고 최종 성공 결과 또는 기존/환경 실패의 구분과 잔여 위험을 `specs/016-interview-reflection-transition/quickstart.md`에 기록한다.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 후 시작하며 모든 사용자 스토리를 차단
- **User Story 1 (Phase 3)**: Foundational 완료 후 시작 가능
- **User Story 2 (Phase 4)**: Foundational 완료 후 시작 가능; User Story 1과 독립적으로 개발 가능
- **User Story 3 (Phase 5)**: Foundational 완료 후 시작 가능; skip-aware provider 회귀 검증은 T017 완료 후 수행
- **Polish (Phase 6)**: 목표 사용자 스토리들이 완료된 뒤 수행

### User Story Dependencies

- **US1 (P1)**: Foundational에만 의존하며 `REFLECTION_READY` fixture로 독립 검증 가능
- **US2 (P1)**: Foundational에만 의존하며 진행 중 Interview fixture로 독립 검증 가능
- **US3 (P2)**: copy 변경은 Foundational 이후 독립 수행 가능하고, skip-aware hallucination 회귀는 US2의 T017에 의존

### Within Each User Story

- 해당 스토리의 테스트를 먼저 작성하고 예상한 이유로 실패하는지 확인한다.
- contract/model/service를 view와 template보다 먼저 구현한다.
- 정상 흐름보다 소유권, invalid state, 동시성, provider failure 계약을 함께 충족한다.
- 스토리별 독립 테스트가 통과한 뒤 다음 checkpoint로 이동한다.

### Parallel Opportunities

- T002와 T003은 서로 다른 테스트 파일에서 병렬 수행 가능하다.
- Foundational 완료 후 US1의 T007과 T008은 병렬 수행 가능하다.
- Foundational 완료 후 US2의 T014, T015, T016은 서로 다른 테스트 경계에서 병렬 수행 가능하다.
- Foundational 완료 후 US3의 T024와 T025는 서로 다른 테스트 파일에서 병렬 수행 가능하다.
- 팀 역량이 충분하면 Foundational 완료 후 US1과 US2의 작업 스트림을 병렬 진행할 수 있다.
- T029는 문서 동기화 준비와 병렬 검토할 수 있지만 T030의 최종 문서 내용은 구현과 회귀 결과가 확정된 뒤 작성한다.

---

## Parallel Example: User Story 1

```text
Task T007: "draft orchestration 실패/충돌 테스트 — tests/reflections/test_drafts.py"
Task T008: "생성 endpoint/화면 계약 테스트 — tests/reflections/test_views.py"
```

## Parallel Example: User Story 2

```text
Task T014: "provider context 계약 테스트 — tests/integrations/llm/test_structured_providers.py"
Task T015: "skip service/동시성 테스트 — tests/reflections/test_services.py"
Task T016: "skip endpoint/HTMX 테스트 — tests/reflections/test_views.py"
```

## Parallel Example: User Story 3

```text
Task T024: "친화적 상태 copy 테스트 — tests/reflections/test_views.py"
Task T025: "unsupported book fact 방지 테스트 — tests/integrations/llm/test_reflection.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup을 완료한다.
2. Phase 2 Foundational을 완료한다.
3. Phase 3 User Story 1을 완료한다.
4. US1 독립 테스트 기준으로 Reflection 생성/재시도/단일성/소유권을 검증한다.
5. 이 지점에서 `REFLECTION_READY → 최소 결과 화면` vertical slice를 시연할 수 있다.

### Incremental Delivery

1. Setup + Foundational로 상태와 DB 계약을 고정한다.
2. US1을 추가해 Reflection 생성 transition을 완성한다.
3. US2를 추가해 skip 및 Reflection 없는 종료를 완성한다.
4. US3를 추가해 내부 상태를 숨기고 제한된 근거의 안내를 정리한다.
5. 각 스토리 checkpoint에서 독립 테스트 후 마지막에 cross-cutting 검증을 수행한다.

### Parallel Team Strategy

1. 한 작업자가 Setup + Foundational을 완료한다.
2. 이후 작업을 다음처럼 분리한다.
   - 작업자 A: US1 draft generation과 결과 transition
   - 작업자 B: US2 skip service와 endpoint
   - 작업자 C: US3 copy와 hallucination regression
3. 공용 파일인 `src/reflections/services.py`, `src/reflections/views.py`, `tests/reflections/test_views.py` 변경은 task 순서와 병합 시점을 조율한다.
4. 모든 스토리 완료 후 Phase 6에서 migration SQL, 문서, 전체 품질 게이트를 통합 검증한다.

---

## Notes

- `[P]` 작업은 서로 다른 파일 또는 독립 테스트 경계를 전제로 한다.
- 각 task는 하나의 의미적으로 완결된 결과와 관찰 가능한 검증을 남긴다.
- UI 검증은 명시적 요청이 없는 한 browser 자동화를 필수 게이트로 삼지 않고 Django test client와 HTML/accessibility assertion을 사용한다.
- Reflection 본문 표시, 편집, 완료 처리, Home/목록 노출은 Day 12 범위이므로 구현하지 않는다.
- 실제 commit은 별도 사용자 요청이 있을 때만 수행한다.

## Phase 7: Convergence

- [X] T034 이미 Skip된 마지막 Turn의 반복 요청이 `ENDED_NO_REFLECTION` 또는 `REFLECTION_READY` terminal 상태에서도 policy conflict가 아니라 현재 목적지로 멱등 수렴하도록 `src/reflections/services.py`의 상태 검증 순서를 수정하고 `tests/reflections/test_services.py`와 `tests/reflections/test_views.py`에 service/HTTP 재요청 회귀 테스트를 추가한다. per FR-012, US2/AC5 (contradicts)
- [X] T035 별도 DB connection에서 동일 Turn의 answer 제출과 Skip을 동시에 실행해 정확히 하나의 최종 결과만 확정되고 `answer`와 `user_skipped_at`이 공존하지 않으며 질문 수와 상태 전이가 중복되지 않음을 `tests/reflections/test_services.py`에서 검증하고 필요한 경우 `src/reflections/services.py`의 잠금·재검증 경로를 보완한다. per FR-012, answer/Skip 경합 예외 상황, Constitution V (partial)
