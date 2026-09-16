# 검증 가이드: Day 11 Interview·Reflection Transition

## 준비

아래 명령은 구현 후 로컬 개발 PostgreSQL과 fake Provider에서 실행한다. 운영·공유 DB 또는 실제 credential을 사용하지 않는다. [데이터 모델](data-model.md)과 [HTTP·Service 계약](contracts/interview-reflection-transition.md)을 기준으로 판정한다.

```powershell
docker compose up -d --wait db
uv sync --locked
$env:LLM_PROVIDER = 'fake'
uv run python src/manage.py check
uv run python src/manage.py showmigrations reflections
```

구현 직전 migration leaf를 확인하고 실제 번호로 다음을 실행한다.

```powershell
uv run python src/manage.py sqlmigrate reflections 0008
uv run python src/manage.py sqlmigrate reflections 0009
uv run python src/manage.py makemigrations --check --dry-run
```

SQL에서 nullable `user_skipped_at`, 2초 transaction-scoped lock timeout, status/Turn CHECK의 `NOT VALID`, 별도 `VALIDATE CONSTRAINT`, validation migration의 non-atomic 실행을 확인한다. 새 terminal 행 생성 후 운영 reverse는 수행하지 않는다.

## 좁은 자동 검사

```powershell
uv run pytest tests/reflections/test_models.py tests/reflections/test_migrations.py tests/reflections/test_services.py tests/reflections/test_drafts.py tests/reflections/test_views.py tests/integrations/llm/test_reflection.py tests/integrations/llm/test_structured_providers.py
```

| 시나리오 | 기대 결과 |
| --- | --- |
| 현재 질문 Skip | answer 없음, `user_skipped_at` 1회 저장, Coverage 불변, 다음 질문 또는 정책 destination |
| 실제 “모르겠어요” 답변 | answer로 보존, user skip 없음, 저정보 분석 경로 유지 |
| 반복 Skip | Turn·질문 수 중복 없음, 동일 후속 상태로 수렴 |
| answer/Skip concurrent 경합 | 하나만 최종 확정, DB CHECK 위반 없음 |
| Skip 후 Provider 실패·재요청 | Skip 보존, 안전 오류, 재요청에서 다음 단계 재개 |
| Skip-aware Provider payload | `user_skipped=true`, answer 없음, Coverage 불변, 건너뛴 질문 반복 방지 |
| 일반/절대 cap | answer+Skip이 budget에 포함되고 10개 초과 Turn 없음 |
| 모두 Skip 후 종료 | `ENDED_NO_REFLECTION`, Reflection 0개, 답변 부족 안내 |
| 일부 답변 후 종료 | `REFLECTION_READY`, 생성 화면 진입 가능 |
| 생성 Loading | status·aria-live·busy·disabled·중복 drop markup 확인; SC-001·008 |
| fake 생성 성공 | Reflection 1개, 최소 임시 결과로 redirect, Interview는 `REFLECTION_READY` 유지 |
| 생성 실패·Retry | answer·Coverage·기존 Reflection 불변, 503 안전 오류와 Retry, 재시도 성공 |
| 기존 Reflection 재요청 | Provider 호출 0회, 기존 id 결과로 수렴, 초안·수정본 불변 |
| concurrent 생성 저장 | 최종 Reflection 1개, conflict 요청도 기존 결과로 수렴 |
| 타인·stale·terminal 요청 | 404/409, 데이터 변경·민감 진단 노출 0건 |
| READY/READY_LIMITED 화면 | 내부 enum·“준비 수준”·RAG 노출 0건, 제한 상태의 기억 중심 non-alert 안내 |
| Desktop/Mobile·keyboard 계약 | 고정 폭 의존 없음, control label·focus·색상 외 status 존재 |
| migration 전후·역방향 | 기존 Interview/Turn/Decision/Reflection 보존, 새 제약 강제 |

외부 Provider transport만 fake/mock으로 격리하고 owner scope, ORM 상태 전이, transaction과 HTTP response는 실제 Django/PostgreSQL 경로로 검증한다. concurrency test는 별도 DB connection과 barrier를 사용한다.

## 수동 선택 검토

실제 브라우저 검토는 현재 완료 조건이 아니다. 구현자가 원하면 대표 Desktop/Mobile 폭에서 각 흐름을 한 번 확인할 수 있으나 자동 검사 실패를 대체하지 않으며 미실행을 미구현으로 판정하지 않는다.

실제 Provider 연결은 Day 10 opt-in 정책을 유지한다. 사용자가 provider·credential·비용을 명시적으로 선택한 경우에만 별도 live Reflection smoke를 실행하며, Day 11 기본 검증에는 포함하지 않는다.

## 완료 게이트

```powershell
uv run python scripts/verify.py
```

Django check, Ruff format/lint, 기본 pytest 결과를 기록한다. 실패는 code regression, 기존 실패, 명령·환경 문제로 구분한다. 구현이 완료된 IMP만 체크하고 README·docs 구현 계획·CHANGELOG를 같은 변경에서 동기화한다.

## 구현 후 증거 기록

### 1. T028: PostgreSQL Safe 2-Stage Migration SQL 검수

```powershell
uv run python src/manage.py sqlmigrate reflections 0008
uv run python src/manage.py sqlmigrate reflections 0009
```

- **0008_interview_turn_user_skip SQL 분석**:
  - `SET LOCAL lock_timeout = '2s';` 적용 확인
  - `ALTER TABLE "reflections_interviewturn" ADD COLUMN "user_skipped_at" timestamp with time zone NULL;` (nullable 추가로 테이블 락 및 rewrite 방지)
  - `ALTER TABLE "reflections_interview" ADD CONSTRAINT "reflections_interview_status_valid" CHECK (status IN ('IN_PROGRESS', 'REFLECTION_READY', 'COMPLETED', 'ENDED_NO_REFLECTION')) NOT VALID;` (`NOT VALID`로 즉시 검증 회피)
  - `ALTER TABLE "reflections_interviewturn" ADD CONSTRAINT "reflections_turn_result_mutually_exclusive" CHECK ((answer IS NULL AND user_skipped_at IS NULL) OR (answer IS NOT NULL AND user_skipped_at IS NULL) OR (answer IS NULL AND user_skipped_at IS NOT NULL)) NOT VALID;` (`NOT VALID`로 즉시 검증 회피)
- **0009_validate_interview_turn_user_skip SQL 분석**:
  - `atomic = False` 속성 확인 (non-blocking validation 트랜잭션 분리)
  - `ALTER TABLE "reflections_interview" VALIDATE CONSTRAINT "reflections_interview_status_valid";` (ShareUpdateExclusiveLock 수준으로 동시 쓰기 허용)
  - `ALTER TABLE "reflections_interviewturn" VALIDATE CONSTRAINT "reflections_turn_result_mutually_exclusive";`

### 2. T031: 자동 테스트 및 마이그레이션 변경 감지

- `uv run python src/manage.py makemigrations --check --dry-run reflections`
  - 결과: `No changes detected in app 'reflections'.` (누락된 마이그레이션 0건)
- `uv run pytest tests/reflections/ tests/integrations/llm/`
  - 결과: 295 passed, 0 failed

### 3. T032: 독립 감사(Auditor Subagent) 검토 결과 및 조치 내역

- **검토자**: Day 11 Transition Auditor (Subagent: `e14f0026-7ace-4bc3-a53b-da84cb3d0a6f`)
- **검토 결과**: SC-001 ~ SC-010 핵심 안전성 확인. 2건의 잠재 결함 지적 및 즉각 조치:
  1. `src/reflections/views.py`: `turn_skip`의 all-skip(`ENDED_NO_REFLECTION`) 분기에서 HTMX 요청 시 전체 HTML 페이지가 반환되던 결함 수정 -> `reflections/_interview_ended_no_reflection.html` fragment만 반환하도록 개선. (`test_turn_skip_htmx_all_skip_returns_fragment_without_full_page`로 검증)
  2. `src/reflections/views.py`: `reflection_generate` POST 처리 시 허용되지 않은 불필요한 form field 인입 차단 검증 누락 수정 -> `set(request.POST) - {"csrfmiddlewaretoken"}` 검사를 추가하여 409 반환. (`test_reflection_generate_with_unexpected_form_field_returns_409`로 검증)
  3. Day 12 비목표(독서노트 본문 출력, 수정 textarea, 완료 버튼, Home 링크 노출) 100% 격리 확인.

### 4. T033: 표준 품질 게이트 (`scripts/verify.py`) 실행 결과

```powershell
uv run python scripts/verify.py
```

- **Django system check**: 정상 통과 (0 errors, 4 RawSQL W045 경고는 DB CHECK 제약 특성으로 유지)
- **Ruff format check**: 120 files already formatted
- **Ruff lint**: All checks passed! (0 errors, 0 warnings, McCabe complexity <= 10)
- **pytest 전체 스위트**: 491 passed, 1 skipped, 7 deselected, 1 warning (48.09s)

### 5. Convergence (T034, T035) 검증 결과

- **T034 (Terminal 상태 마지막 Turn 반복 Skip 멱등 수렴)**:
  - `src/reflections/services.py`의 `skip_interview_turn`에서 `_validate_interview_state` 호출 순서를 재구성하여, 이미 건너뛴 마지막 Turn의 재요청이 `ENDED_NO_REFLECTION` 또는 `REFLECTION_READY` terminal 상태에서도 409 Conflict 없이 목적지로 정상 멱등 수렴하도록 수정.
  - 검증: `test_skip_interview_turn_idempotent_on_ended_no_reflection_last_turn`, `test_skip_interview_turn_idempotent_on_reflection_ready_last_turn` (서비스), `test_turn_skip_repeated_post_on_ended_no_reflection_converges_idempotently`, `test_turn_skip_repeated_post_on_reflection_ready_converges_idempotently` (HTTP/HTMX) 통과.
- **T035 (Answer/Skip 동시 경합 검증 및 상호 배타 보장)**:
  - `select_for_update` 및 상호 배타 체크를 통해 별도 DB connection에서 동일 Turn에 answer 제출과 Skip이 동시 발생해도 정확히 하나의 결과만 확정되고 `answer`와 `user_skipped_at`이 절대 공존하지 않음을 확인.
  - 검증: `test_concurrent_answer_and_skip_on_same_turn` 통과.

### 6. Convergence Correction 3 (T036~T040) 검증 결과

- **T036 (Skip된 Turn의 ProgressDecision 처리 정합성)**:
  - `InterviewProgressDecision.clean()`: `turn.answer is None and turn.user_skipped_at is None`으로 수정하여 확정 건너뛰기 Turn도 ProgressDecision 대상으로 허용.
  - `decide_interview_progress()`: Turn 조회 시 `Q(answer__isnull=False) | Q(user_skipped_at__isnull=False)`로 수정하여 Skip Turn의 의사결정 처리 지원.
  - 검증: `test_progress_decision_allows_explicit_user_skipped_turn` (모델), `test_decide_interview_progress_on_user_skipped_turn_soft_stop_end`, `test_decide_interview_progress_on_user_skipped_turn_soft_stop_continue`, `test_decide_interview_progress_on_user_skipped_turn_cap_extension` (서비스).
- **T037 (HTMX Soft Stop END 후 Reflection 생성 버튼 누락 보정)**:
  - `src/reflections/views.py`: `interview_decision`의 HTMX 성공 분기에서 `reflections/_interview_reflection_ready.html` 렌더링 시 `{"interview": interview}` context 전달 누락 보정.
  - 검증: `test_interview_decision_soft_stop_end_htmx_renders_reflection_generate_button` (뷰).
- **T038 (Skip + ProgressDecision 재진입 화면 우선순위 보정)**:
  - `src/templates/reflections/interview_detail.html`: pending `progress_decision`이 존재할 때 Soft Stop/CAP Extension 선택 UI를 최우선 렌더링하고, decision이 없는 skip Provider 실패 상태(재진입)에서는 기존 retry UI 유지.
  - 검증: `test_interview_detail_renders_soft_stop_on_skipped_turn_with_pending_decision`, `test_interview_detail_renders_cap_extension_on_skipped_turn_with_pending_decision`, `test_interview_detail_renders_retry_ui_on_skipped_turn_without_decision` (뷰).
- **T039 (stale Skip replay 안전 수렴)**:
  - `src/reflections/services.py`: 과거 sequence에 대한 stale Skip replay 도착 시 과거 UI로 후퇴하거나 새 Turn을 생성하지 않고 현재 최신 진행 Turn(`latest`) 또는 종결 destination으로 안전하게 수렴하도록 보정.
  - 검증: `test_stale_skip_replay_converges_to_current_state` (서비스).
- **T040 (Skip Provider wire schema 및 Application validation 정합화)**:
  - `src/reflections/services.py`: `_validate_skip_proposal()`에서 `and not context.user_skipped`를 제거하여 NORMAL mode + 미완료 Coverage 시 explicit user skip 후라도 Provider의 `kind=skip` 제안을 애플리케이션 계층에서 엄격하게 거부(`QuestionGenerationRejected`)하도록 동기화.
  - 검증: `test_skip_provider_validation_rejects_skip_proposal_when_coverage_uncompleted` (서비스).

### 7. 성공 기준 (SC-001 ~ SC-010) 정합성 매핑

| 성공 기준 | 구현 내용 및 검증 증거 |
| --- | --- |
| **SC-001 (생성 진행 및 최소 임시 결과 화면 도달)** | Soft Stop 종료 및 질문 한도 도달 후 Reflection 생성 성공 시 최소 임시 결과 화면(`reflection_draft_ready.html`)으로 자동 도달 검증 (`test_views.py::test_reflection_generate_success_redirects_to_draft_ready`, `test_interview_decision_soft_stop_end_htmx_renders_reflection_generate_button`) |
| **SC-002 (생성 실패/재시도 시 답변 보존 및 재시도 제공)** | 생성 실패·시간 초과·비정상 응답 시 기존 질문/답변/Coverage 유실 0건, 503 안전 오류와 Retry 폼 제공 검증 (`test_drafts.py`, `test_views.py::test_reflection_generate_provider_failure_returns_503_and_retry`) |
| **SC-003 (동일 Interview 단일 Reflection 및 덮어쓰기 방지)** | 반복 요청, 동시 생성 경합(`ReflectionDraftConflict`), 유실 후 재요청 시 최종 Reflection 1개 및 기존 초안 보존 검증 (`test_drafts.py`, `test_views.py::test_reflection_generate_conflict_converges_to_existing_draft`) |
| **SC-004 (질문 Skip 단방향 확정 및 답변/Skip 상호 배타)** | 질문 Skip 시 한 번의 동작으로 후속 상태 전이, 빈 Answer 미생성, `answer`와 `user_skipped_at` 상호 배타 보장 (`test_models.py`, `test_services.py::test_concurrent_answer_and_skip_on_same_turn`, `test_views.py::test_turn_skip_success_advances_to_next_question`) |
| **SC-005 (Skip/저정보 답변/다음 질문 생략 구분 및 Coverage 불변)** | Skip과 저정보 텍스트 답변(`low_information=False`), 확정 답변 후 생략 구분, Skip으로 Coverage 미증가 확인 (`test_structured_providers.py`, `test_services.py`) |
| **SC-006 (READY/READY_LIMITED 친화적 안내 및 내부 용어 격리)** | READY 및 READY_LIMITED fixture에서 정상 동작, `READY`, `READY_LIMITED`, `RAG`, `Knowledge readiness` 등 기술 용어 노출 0건 및 친화적 안내문 제공 검증 (`test_views.py::test_interview_start_and_detail_hide_internal_readiness_terms`) |
| **SC-007 (제한적 도서 정보 시 사실 왜곡 방지 및 기억/감상 중심 질문)** | READY_LIMITED 및 skip 누적 상태에서 미확인 책 사실 전제 0건, 기억·인상 중심 질문 생성 검증 (`test_reflection.py::test_ready_limited_avoids_unsupported_book_facts_in_questions`) |
| **SC-008 (로딩/Disabled 즉시 표시, 키보드 접근성 및 반응형 유지)** | 생성·Retry·Skip 흐름에서 `aria-live`, `aria-busy`, `disabled`, `hx-sync="this:drop"` 즉시 적용, 시맨틱 버튼 및 Desktop/Mobile 폭 지원 (`test_views.py`, `app.css`) |
| **SC-009 (소유권 격리, 부적합 상태 거부 및 민감 정보 보호)** | 비소유자 404 차단, terminal/stale 상태 409, 예외 원문/credential 비노출 검증 (`test_views.py::test_views_enforce_owner_boundaries_and_mask_internal_diagnostics`) |
| **SC-010 (All-skip 시 Reflection 없는 종결 및 안내)** | 모든 질문 Skip 시 `ENDED_NO_REFLECTION`으로 종결, Reflection 0개 생성, 답변 부족 안내 문구 제공 검증 (`test_services.py`, `test_views.py::test_turn_skip_htmx_all_skip_returns_fragment_without_full_page`) |

### 8. 미검증 범위 및 잔여 위험

- **실제 LLM Live API**: Day 10 opt-in 정책에 따라 과금 방지를 위해 fake Provider로 격리 검증됨. 실제 API 키 설정 시 live smoke 가능.
- **W045 경고**: RawSQL을 활용한 Django CHECK 제약 조건에 대한 프레임워크 경고로, SQLite/PostgreSQL 환경에서 의도된 동작임.

