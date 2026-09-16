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
- **pytest 전체 스위트**: 476 passed, 1 skipped, 7 deselected, 1 warning (46.04s)

### 5. 성공 기준 (SC-001 ~ SC-010) 정합성 매핑

| 성공 기준 | 구현 내용 및 검증 증거 |
| --- | --- |
| **SC-001 (소유자 격리)** | 모든 엔드포인트와 서비스에서 `reading__user=user` 기반 격리, 비소유자 404 차단 |
| **SC-002 (단일 Reflection)** | 선조회 및 중복 저장 경합 시 `ReflectionDraftConflict`를 거쳐 기존 Reflection으로 수렴 |
| **SC-003 (Skip 트랜잭션 및 예산)** | `user_skipped_at` 원자적 1회 기록, coverage 불변, 질문 예산 산정에 skip 포함 |
| **SC-004 (All-skip 종결)** | 확정 답변 0개 시 `ENDED_NO_REFLECTION`으로 안전 종결, Reflection 생성 시 409 반환 |
| **SC-005 (안전한 2단계 마이그레이션)** | 0008 (lock_timeout 2s, NOT VALID), 0009 (atomic=False, VALIDATE CONSTRAINT) 완성 |
| **SC-006 (사용자 친화적 안내)** | `READY`, `READY_LIMITED`, `준비 수준`, `RAG` 노출 0건 및 자연스러운 비오류 안내문 제공 |
| **SC-007 (장애 시 답변 보존)** | Provider 호출 실패 시 사용자 답변/인터뷰 상태 100% 보존, 503 복구 fragment 제공 |
| **SC-008 (로딩 및 중복 방지)** | HTMX aria-live, busy 상태 및 폼 disabled, 중복 요청 멱등 수렴 |
| **SC-009 (반응형 및 접근성)** | 시맨틱 버튼, 고정폭 비의존 레이아웃, 스크린리더 aria-label/live 적용 |
| **SC-010 (Day 12 경계 보호)** | Reflection 본문 표시, 편집 textarea, 완료 처리, Home 링크의 Day 12 범위 침범 0건 |

### 6. 미검증 범위 및 잔여 위험

- **실제 LLM Live API**: Day 10 opt-in 정책에 따라 과금 방지를 위해 fake Provider로 격리 검증됨. 실제 API 키 설정 시 live smoke 가능.
- **W045 경고**: RawSQL을 활용한 Django CHECK 제약 조건에 대한 프레임워크 경고로, SQLite/PostgreSQL 환경에서 의도된 동작임.
