# 빠른 검증: Reflection 결과·수정과 Home 재진입

## 목적과 전제

Day 12 구현이 결과 읽기, 수정 저장, 명시적 완료, Home 재진입과 검증용 책 준비 계약을
충족하는지 결정적인 자동 검사로 확인한다. PostgreSQL test DB와 기본 fake LLM 설정을
사용하며 실제 Provider, credential, 비용 발생 요청 및 브라우저 자동화는 사용하지 않는다.

## 1. Schema와 안전한 Migration

```powershell
uv run python src/manage.py makemigrations --check --dry-run reflections
uv run python src/manage.py sqlmigrate reflections 0010
```

확인 항목:

- 기존 DRAFT-only CHECK 제거와 새 status/완료시각 CHECK 추가가 `0010` migration에 있다.
- column rewrite, backfill, table/index 생성이 없다.
- 기존 DRAFT와 Interview/Reading/Book 관계가 forward migration 뒤 보존된다.

## 2. Reflection 모델·Service

```powershell
uv run pytest tests/reflections/test_models.py tests/reflections/test_migrations.py tests/reflections/test_drafts.py -q
```

| 시나리오 | 기대 결과 |
| --- | --- |
| DRAFT 수정 저장 | revised만 변경, 최초 draft/sections 불변 |
| 수정 없이 저장 | 동일 현재 본문으로 성공 수렴 |
| 공백·길이 초과 | validation 거부, 기존 값 보존 |
| 완료 | Reflection과 Interview 함께 COMPLETED, 완료시각 설정 |
| 완료 취소 | 쓰기 0건 |
| 반복 완료 | 기존 완료 결과로 수렴, 상태/완료시각 불변 |
| 완료 후 수정 | 거부, 완료 본문 불변 |
| DB 실패 | transaction rollback, 두 status 불일치 0건 |

## 3. 결과·수정·완료 HTTP와 안전 렌더링

```powershell
uv run pytest tests/reflections/test_views.py -q
```

확인 항목:

- 소유자는 책 제목, 선택적 저자, 최초 작성일, 전체 현재 본문과 상태를 본다.
- headings, 문단, 목록, 인용, 강조 등 기본 마크다운이 시맨틱 HTML에 표시된다.
- 사용자 작성 raw HTML은 실행 가능한 markup이 되지 않는다.
- 수정 GET/POST, 저장 완료 message, PRG redirect, 완료 확인 GET/POST가 계약대로 동작한다.
- validation 실패 시 form error 유지, COMPLETED 상태에서 수정 시도 시 차단, 타인/없는 기록 404를 확인한다.
- 완료본에는 수정·완료 control이 없고 Home 링크 및 읽기 전용 상태만 유지된다.
- 버튼·링크·label·error/status text·focus target을 키보드 및 색상 외 표현으로 확인한다.

## 4. Home 재진입

```powershell
uv run pytest tests/test_home_page.py -q
```

| 데이터 상태 | 기대 결과 |
| --- | --- |
| Reflection 없음 | 최근 카드 없음, 기존 Reading/Interview 행동 유지 |
| DRAFT 하나 | `작성 중`, 같은 결과 URL |
| COMPLETED 하나 | `완료`, 같은 결과 URL |
| 여러 Reflection | updated_at/id 기준 하나만 표시 |
| 오래된 책 최근 수정 | 생성일이 최신인 다른 기록보다 우선 |
| 여러 사용자 | 현재 사용자 기록만 표시 |
| 카드 수 증가 | query count 고정, N+1 없음 |

## 5. 검증용 책 세트

검증 DB에서만 실행한다.

```powershell
uv run python src/manage.py prepare_validation_books
uv run python src/manage.py prepare_validation_books
uv run pytest tests/knowledge/test_validation_books.py tests/knowledge/test_seed_command.py -q
```

확인 항목:

- 《1984》 fiction READY, 《Thinking, Fast and Slow》 nonfiction READY,
  《The Left Hand of Darkness》 READY_LIMITED가 ISBN13 기준으로 존재한다.
- 두 번째 실행에서 신규 Book·Claim 0건이고 기존 서지정보를 덮어쓰지 않는다.
- LIMITED 대상에 Knowledge가 있으면 자동 삭제 없이 전체 실행이 실패한다.
- 사용자 Reading, Interview, Reflection을 만들거나 바꾸지 않는다.

## 6. 관련 범위와 전체 품질 게이트

```powershell
uv run pytest tests/reflections/ tests/knowledge/ tests/test_home_page.py -q
uv run python scripts/verify.py
```

실패는 이번 변경의 regression, 기존 실패, 명령·환경 문제로 구분한다. 구현이 안정된 뒤에만
README, docs 구현 계획과 CHANGELOG를 실제 완료 증거에 맞춰 갱신한다.

## 선택형 인간 UX 확인

현재 기능의 완료 조건이 아니며 자동 검사를 대체하지 않는다. 구현자가 원하면 대표 Desktop과
Mobile 폭에서 결과 읽기→수정→저장→완료→Home 재진입을 각 한 번 확인할 수 있다. 미실행을
미구현으로 판정하지 않는다.
