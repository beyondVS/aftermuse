# 작업: Reflection 결과·수정과 Home 재진입

**입력**: `/specs/017-reflection-result-edit-home/`의 설계 문서  
**선행 조건**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**테스트**: 기능 사양과 헌법이 모델·migration·service·view·Home·command의 결정적 테스트를 요구하므로, 각 사용자 스토리에서 테스트를 먼저 작성하고 실패를 확인한 뒤 구현한다.

**구성**: 각 사용자 스토리는 가능한 한 독립적으로 구현·검증할 수 있도록 테스트와 구현 작업을 같은 단계에 배치한다.

## 형식: `TID [P?] [Story?] 설명과 파일 경로`

- **[P]**: 다른 미완료 작업과 파일이 겹치지 않고 병렬 수행 가능
- **[US1]–[US4]**: 작업이 속한 사용자 스토리
- 모든 작업 설명에는 변경하거나 검증할 정확한 파일 경로를 포함한다.

## 1단계: 설정

**목적**: 계획에서 확정한 안전한 Markdown 렌더링 의존성을 재현 가능한 환경에 추가한다.

- [ ] T001 `Markdown~=3.10.3` 런타임 의존성을 추가하고 lockfile을 동기화한 뒤 import 가능한지 확인한다: `pyproject.toml`, `uv.lock`

---

## 2단계: 공통 기반

**목적**: 모든 사용자 스토리가 공유하는 Reflection 상태 불변식, migration 안전성, 현재 본문 선택 및 렌더링 경계를 확립한다.

**중요**: 이 단계가 완료되기 전에는 사용자 스토리 구현을 시작하지 않는다.

- [ ] T002 [P] DRAFT/COMPLETED와 `completed_at` 조합, 기존 DRAFT 보존, migration 왕복 및 실제 SQL의 2초 `lock_timeout`·`NOT VALID`·별도 `VALIDATE CONSTRAINT`를 먼저 실패하는 테스트로 명세한다: `tests/reflections/test_models.py`, `tests/reflections/test_migrations.py`
- [ ] T003 [P] `revised_markdown` 우선 현재 본문 선택과 HTML 선행 escape 후 extension 없는 Markdown 변환이 heading·paragraph·list·blockquote·emphasis는 보존하고 raw HTML·script·event attribute·link·image·iframe·form은 실행 가능한 markup으로 만들지 않는지 먼저 실패하는 테스트로 명세한다: `tests/reflections/test_drafts.py`
- [ ] T004 `Reflection.Status.COMPLETED`, 현재 본문 선택 규칙, `(DRAFT, completed_at IS NULL)` 또는 `(COMPLETED, completed_at IS NOT NULL)`만 허용하는 ORM 상태 제약을 구현한다: `src/reflections/models.py`
- [ ] T005 기존 status/completed_at 제약을 교체하되 첫 migration은 transaction-scoped `lock_timeout = '2s'`, `NOT VALID`, `SeparateDatabaseAndState`를 사용하고 두 번째 `atomic = False` migration은 검증만 수행하도록 작성한다: `src/reflections/migrations/0010_reflection_completion_constraints.py`, `src/reflections/migrations/0011_validate_reflection_completion_constraints.py`
- [ ] T006 현재 본문을 HTML escape한 뒤 extension 없이 Markdown으로 변환하는 단일 안전 렌더 경계를 구현하고 저장 validator를 우회한 legacy 값도 실행 불가능하게 만든다: `src/reflections/drafts.py`
- [ ] T007 공통 기반 테스트를 실행해 모델 불변식, migration 왕복/SQL 계약 및 안전 렌더링이 통과하는지 확인한다: `tests/reflections/test_models.py`, `tests/reflections/test_migrations.py`, `tests/reflections/test_drafts.py`

**체크포인트**: schema-first 배포가 가능하고 기존 DRAFT 쓰기와 호환되는 공통 기반이 준비된다.

---

## 3단계: 사용자 스토리 1 — 생성된 독서노트를 내 기록으로 읽기 (우선순위: P1) 🎯 MVP

**목표**: 소유자가 Reflection을 책 정보와 안전하게 렌더링된 전체 본문이 있는 읽기 중심 결과 화면으로 확인하고 수정 또는 Home 이동을 선택한다.

**독립 테스트**: 짧고 긴 소유자 Reflection을 결과 URL로 열어 제목·선택적 저자·최초 작성일·전체 현재 본문·`작성 중` 상태·수정/완료/Home 행동을 확인하고, 타인 및 없는 ID는 동일한 404이며 악성 legacy 본문은 실행 가능한 HTML이 되지 않음을 검증한다.

### 사용자 스토리 1 테스트

- [ ] T008 [US1] 결과 GET의 owner scope, bounded `select_related` 조회, 책 메타데이터, 20개 이상 문단의 순서, 허용 Markdown 구조, 실행 불가 콘텐츠, DRAFT 행동 및 타인/없는 기록 404를 먼저 실패하는 HTTP 테스트로 작성한다. 결과에 Chat transcript 구조, assistant/user 역할 label, 생성 진행 상태 또는 AI를 최종 저자로 표현하는 문구가 없고 독서노트 본문이 주 콘텐츠인지도 검증한다: `tests/reflections/test_views.py`

### 사용자 스토리 1 구현

- [ ] T009 [US1] 기존 임시 성공 응답을 소유자 범위의 Reflection 상세 조회와 안전 렌더 context로 교체하고 책/Interview를 한정된 query로 함께 가져온다: `src/reflections/views.py`
- [ ] T010 [US1] 책 제목·선택적 저자·`created_at` 작성일·전체 현재 본문·색상 외 상태 텍스트·DRAFT의 수정/완료/Home 행동을 갖춘 읽기 중심 결과 화면을 구현하고, Reflection을 사용자의 독서노트로 표현하되 AI 작성자·Chat transcript·생성 도구 상태는 표시하지 않는다: `src/templates/reflections/reflection_detail.html`
- [ ] T011 [US1] 긴 글의 문단·제목·목록·인용 순서를 유지하고 Desktop/Mobile 폭에서 읽히도록 본문과 form control의 `max-width: 100%`, 긴 문자열 `overflow-wrap`, action group wrapping, keyboard focus 및 고정 폭 금지 규칙을 추가한다: `src/static/css/app.css`
- [ ] T012 [US1] 사용자 스토리 1의 결과 화면 테스트를 실행하고 독립 인수 기준이 통과하는지 확인한다: `tests/reflections/test_views.py`

**체크포인트**: 수정 저장과 Home 최근 카드가 없어도 소유자의 Reflection 읽기 경험을 독립적으로 제공한다.

---

## 4단계: 사용자 스토리 2 — 초안을 수정하고 최종 기록으로 확인하기 (우선순위: P1)

**목표**: 소유자가 DRAFT의 현재 본문을 안전하게 수정·저장하고, 별도 확인 후 Reflection과 Interview를 원자적으로 완료하며 완료본은 계속 읽기 전용으로 유지한다.

**독립 테스트**: 수정 GET의 현재 본문과 token을 확인하고 유효한 저장·동일 내용 저장·validation 실패·stale token·DB 실패를 검증한 뒤, 완료 확인 GET이 쓰지 않으며 POST가 두 상태를 함께 완료하고 반복 완료는 쓰기 없이 성공하며 완료 후 수정은 거부되는지 확인한다.

### 사용자 스토리 2 테스트

- [ ] T013 [P] [US2] row lock 뒤 owner/DRAFT/token을 재검사하는 저장, 동일 내용의 멱등 수렴, 수정/완료 경합, 완료 후 수정 거부, 반복 완료, 완료 시각 보존 및 DB 실패 시 Reflection·Interview 동시 rollback을 먼저 실패하는 service 테스트로 작성한다: `tests/reflections/test_drafts.py`
- [ ] T014 [P] [US2] 수정/완료 Form의 비공백 1–20,000자·raw HTML/link/image/금지 지시 거부와 hidden `expected_updated_at` 검증을 먼저 실패하는 테스트로 작성한다: `tests/reflections/test_models.py`
- [ ] T015 [US2] 수정 GET/POST와 완료 확인 GET/POST의 로그인/owner scope, CSRF 쓰기 경계, PRG, 저장 message, 400 validation, 409 stale/completed, 503 persistence, 취소 무변경 및 완료본 control 제거를 먼저 실패하는 HTTP 테스트로 작성한다. 핵심 행동이 native link·button·label을 사용하고 상태·오류가 텍스트로 제공되는지도 검증한다: `tests/reflections/test_views.py`

### 사용자 스토리 2 구현

- [ ] T016 [US2] 현재 본문, 비공백 1–20,000자 validator 및 hidden `expected_updated_at`를 처리하는 수정 Form과 완료 token Form을 구현한다: `src/reflections/forms.py`
- [ ] T017 [US2] `save_reflection_revision()`에 owner/DRAFT/token의 transaction 내 잠금 후 재검사, stale/completed 전용 예외, 동일 내용 멱등 처리 및 저장 실패 rollback을 구현한다: `src/reflections/drafts.py`
- [ ] T018 [US2] `complete_reflection()`에 같은 낙관적 token과 row lock을 적용하고 현재 본문을 보존한 채 Reflection status/completed_at과 Interview status를 한 transaction에서 갱신하며 반복 완료는 쓰기 없이 수렴하게 한다: `src/reflections/drafts.py`
- [ ] T019 [US2] 수정 및 완료 확인 URL과 얇은 GET/POST view를 추가해 400/404/409/503 계약, Django messages, 안전한 오류 문구 및 결과 화면 PRG를 매핑한다: `src/reflections/urls.py`, `src/reflections/views.py`
- [ ] T020 [US2] 현재 본문·label·field error·token·저장/취소를 갖춘 수정 화면과 GET 무변경·명시적 완료 POST·결과 복귀 취소를 갖춘 확인 화면을 구현한다: `src/templates/reflections/reflection_edit.html`, `src/templates/reflections/reflection_complete_confirm.html`
- [ ] T021 [US2] 저장 완료 `aria-live`, validation/conflict/persistence 상태와 focus target, 완료본 읽기 전용 안내 및 색상 외 상태 표현을 결과/수정/완료 화면에 연결한다. 기존 접근성 색상 token만 사용하고 상태·오류·focus가 색상에만 의존하지 않는지 HTML class와 stylesheet 계약으로 검증한다: `src/templates/reflections/reflection_detail.html`, `src/templates/reflections/reflection_edit.html`, `src/templates/reflections/reflection_complete_confirm.html`, `src/static/css/app.css`
- [ ] T022 [US2] 사용자 스토리 2의 model/form, service 및 HTTP 테스트를 실행해 수정과 완료 계약이 독립적으로 통과하는지 확인한다: `tests/reflections/test_models.py`, `tests/reflections/test_drafts.py`, `tests/reflections/test_views.py`

**체크포인트**: AI 초안은 보존되고 최신 수정본만 표시되며, 명시적 완료 전후의 상태와 데이터가 충돌·오류 상황에서도 일관된다.

---

## 5단계: 사용자 스토리 3 — Home에서 최근 독서노트로 돌아가기 (우선순위: P1)

**목표**: 인증 사용자가 Home에서 마지막 생성·수정·완료 활동이 가장 최근인 자신의 Reflection 하나를 상태와 함께 확인하고 결과 화면으로 재진입한다.

**독립 테스트**: Reflection 없음, DRAFT 하나, COMPLETED 하나, 같은/다른 생성시각과 `updated_at`을 가진 여러 기록 및 여러 사용자를 준비해 `updated_at DESC, id DESC` 선택·상태·결과 URL·기존 카드 보존과 기록 수에 무관한 query count를 검증한다.

### 사용자 스토리 3 테스트

- [ ] T023 [US3] Home의 owner-only 최신 Reflection 선택, `updated_at`/`id` tie-break, DRAFT `작성 중`, COMPLETED `완료`, 결과 링크, 빈 상태, 기존 Home 행동 보존 및 N+1 없는 고정 query count를 먼저 실패하는 테스트로 작성한다: `tests/test_home_page.py`

### 사용자 스토리 3 구현

- [ ] T024 [US3] `get_home_reading_groups()`에 현재 사용자 Reflection을 `select_related("interview__reading__book")`, `-updated_at`, `-id`, limit 1로 조회하는 독립 bounded query와 `recent_reflection` context를 추가한다: `src/config/views.py`
- [ ] T025 [US3] Reflection이 있을 때만 책 정보, `작성 중`/`완료` 텍스트 및 같은 결과 URL을 표시하는 최근 독서노트 카드를 추가하고 기존 Reading/Interview/사색 대기/빈 상태를 보존한다: `src/templates/pages/home.html`
- [ ] T026 [US3] 최근 독서노트 카드가 Mobile 폭에서도 넘치지 않고 상태와 링크의 focus가 색상 외 방식으로 식별되도록 스타일을 추가한다: `src/static/css/app.css`
- [ ] T027 [US3] 사용자 스토리 3의 Home 테스트를 실행해 최근 활동 선택, 사용자 격리 및 고정 query count가 통과하는지 확인한다: `tests/test_home_page.py`

**체크포인트**: 전체 Library 없이도 사용자는 Home에서 자신의 가장 최근 DRAFT 또는 COMPLETED Reflection으로 돌아갈 수 있다.

---

## 6단계: 사용자 스토리 4 — 대표 책 세트로 다음 검증 준비하기 (우선순위: P2)

**목표**: 명시적 비운영 command로 승인 Seed Knowledge 소설 1권·비문학 1권과 Knowledge가 없는 READY_LIMITED 1권을 원자적이고 멱등하게 준비한다.

**독립 테스트**: 빈 DB와 일부 기존 Book DB에서 command를 연속 두 번 실행해 정확히 세 descriptor, 두 READY 책의 기존 승인 Claim 총 8개(책별 4개), LIMITED의 Claim 0개, 두 번째 실행 신규 Book/Claim 0개, 기존 서지정보·다른 책·모든 사용자 기록 불변 및 오류 시 전체 rollback을 검증한다.

### 사용자 스토리 4 테스트

- [ ] T028 [US4] descriptor 형식/구성, ISBN13 멱등 생성·기존 메타데이터 보존, READY 두 권에 기존 `book_knowledge.json`의 승인 Claim 총 8개가 중복 없이 적용되는지, LIMITED 무지식, 두 번 실행 수렴, 사용자 데이터 무변경, LIMITED 불일치/잘못된 입력/DB 실패 전체 rollback을 먼저 실패하는 command/service 테스트로 작성한다: `tests/knowledge/test_validation_books.py`

### 사용자 스토리 4 구현

- [ ] T029 [US4] 정확히 `1984` fiction READY, `Thinking, Fast and Slow` nonfiction READY, `The Left Hand of Darkness` fiction READY_LIMITED의 ISBN13·제목·저자·genre·기대 상태만 담은 descriptor를 추가한다: `src/knowledge/seed_data/validation_books.json`
- [ ] T030 [US4] descriptor가 정확히 3권이고 READY fiction 1권·READY nonfiction 1권·READY_LIMITED 1권인지 검증한 뒤 ISBN13 `get_or_create`, 기존 서지정보 보존, 기존 승인 Seed 적용 및 LIMITED Knowledge 존재 시 삭제 없이 실패하는 원자적 준비 service를 구현한다: `src/knowledge/services.py`
- [ ] T031 [US4] application 시작이나 migration에서 자동 실행되지 않는 명시적 `prepare_validation_books` command를 추가하고 생성/재사용 Book·Claim 수만 출력한다: `src/knowledge/management/commands/prepare_validation_books.py`
- [ ] T032 [US4] 사용자 스토리 4와 기존 Seed 회귀 테스트를 실행해 멱등성, 원자성 및 승인 Claim 계약이 통과하는지 확인한다: `tests/knowledge/test_validation_books.py`, `tests/knowledge/test_seed_command.py`

**체크포인트**: Day 13 검증용 세 권이 운영/사용자 데이터에 손대지 않는 명시적 command로 반복 준비된다.

---

## 7단계: 마무리 및 교차 관심사

**목적**: migration SQL, 관련 범위 회귀, 문서 및 프로젝트 전체 품질 게이트를 실제 증거와 일치시킨다.

- [ ] T033 두 migration에 대해 `makemigrations --check --dry-run`과 `sqlmigrate`를 실행해 예상 밖 schema drift가 없고 SQL이 2초 lock timeout, `NOT VALID`, 별도 non-atomic validation 및 정확한 constraint 이름을 사용하는지 재검토한다: `src/reflections/migrations/0010_reflection_completion_constraints.py`, `src/reflections/migrations/0011_validate_reflection_completion_constraints.py`
- [ ] T034 관련 범위 전체 테스트를 실행해 Reflection, Knowledge 및 Home 변경 사이의 회귀가 없는지 확인한다: `tests/reflections/`, `tests/knowledge/`, `tests/test_home_page.py`
- [ ] T035 표준 전체 품질 게이트를 실행하되 실제 브라우저와 live Provider 검증은 필수 완료 조건으로 추가하지 않는다: `scripts/verify.py`
- [ ] T036 T033–T035의 실제 검증 결과를 근거로 구현 동작, 명시적 검증 command, Day 12 IMP-093/IMP-094/IMP-100 완료 상태, 사용자 관점 변경 사항 및 잔여 위험을 수술적으로 동기화한다: `README.md`, `docs/README.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`, `CHANGELOG.md`, `specs/017-reflection-result-edit-home/quickstart.md`

---

## 의존성과 실행 순서

### 단계 의존성

- **1단계 설정**: 즉시 시작 가능하다.
- **2단계 공통 기반**: 1단계 의존; 모든 사용자 스토리를 차단한다.
- **US1**: 공통 기반 이후 시작하며 최초 MVP를 구성한다.
- **US2**: 공통 기반 이후 service/form 테스트를 시작할 수 있으나 결과 화면 PRG와 control 통합은 US1 결과 화면을 사용한다.
- **US3**: 공통 기반 이후 조회 로직을 시작할 수 있으나 결과 링크의 최종 화면은 US1을 사용한다.
- **US4**: 공통 기반 이후 다른 사용자 스토리와 독립적으로 진행할 수 있다.
- **마무리**: 필요한 사용자 스토리가 완료된 뒤 실행한다.

### 사용자 스토리 의존성 그래프

```text
설정 → 공통 기반 ─┬→ US1 (MVP) ─┬→ US2
                  │             └→ US3
                  └→ US4

US1 + US2 + US3 + US4 → 마무리
```

### 각 사용자 스토리 내부 순서

1. 테스트를 작성하고 대상 동작이 아직 실패함을 확인한다.
2. model/service/form 또는 selector를 구현한다.
3. view/template/command 경계를 구현한다.
4. 해당 스토리의 좁은 테스트를 통과시킨다.
5. 다음 스토리로 이동하기 전에 독립 인수 기준을 확인한다.

### 병렬 수행 기회

- T002와 T003은 서로 다른 테스트 파일을 중심으로 병렬 작성할 수 있다.
- 공통 기반 이후 T013과 T014는 서로 다른 service/form 계약을 병렬 작성할 수 있다.
- US1 완료 뒤 US2의 backend 작업과 US3의 Home 작업은 파일 충돌을 조정하면 병렬 진행할 수 있다.
- US4의 T028–T032는 공통 기반 이후 US1–US3과 독립적으로 진행할 수 있다.
- T036 문서 동기화는 T033–T035의 실제 검증 결과가 확정된 뒤 수행한다.

---

## 병렬 실행 예시

### 사용자 스토리 2

```text
작업 A: T013 — 저장·완료 service의 충돌/원자성 테스트
작업 B: T014 — Form validation 및 revision token 테스트
```

### 사용자 스토리 3과 사용자 스토리 4

```text
작업 A: T023–T027 — Home 최근 Reflection 재진입
작업 B: T028–T032 — 검증용 책 세트와 명시적 command
```

---

## 구현 전략

### MVP 우선

1. 설정과 공통 기반(T001–T007)을 완료한다.
2. 사용자 스토리 1(T008–T012)을 완료한다.
3. 결과 화면의 독립 인수 테스트를 통과시켜 읽기 중심 MVP를 확인한다.
4. 이후 수정·완료, Home 재진입, 검증 데이터 준비를 순서대로 확장한다.

### 점진적 전달

1. **기반**: 안전한 schema와 렌더링 경계
2. **US1**: 읽을 수 있는 소유자 전용 결과 화면
3. **US2**: 충돌에 안전한 수정과 명시적 최종 완료
4. **US3**: Home 최근 기록 재진입
5. **US4**: 다음 검증을 위한 멱등 데이터 준비
6. **마무리**: SQL·회귀·문서·전체 품질 게이트

## 참고

- `[P]` 작업도 같은 파일을 수정하게 되면 순차 실행으로 전환한다.
- 완료본의 수정 또는 DRAFT 복귀, 전체 Library, 공유, Credit, Reader Insight, live Provider 및 필수 브라우저 자동화는 이번 범위에 포함하지 않는다.
- 실제 브라우저 Desktop/Mobile 확인은 선택형 인간 UX 검토이며 T036의 완료 조건이 아니다.
- 각 체크박스는 코드 작성과 검증이 가능한 하나의 구체적 결과를 나타낸다.
