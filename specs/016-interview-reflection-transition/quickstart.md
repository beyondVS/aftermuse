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

구현 단계에서 이 아래에 실행 명령, pass/fail 수, migration SQL 검수, SC-001~010 대응과 미검증 범위를 기록한다. 계획 작성만으로 통과를 주장하지 않는다.
