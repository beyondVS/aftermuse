# 작업: Reflection 기본 모델과 생성 Prompt / Adapter

**입력**: `specs/015-reflection-draft-generation/`의 [명세](spec.md), [계획](plan.md), [조사](research.md), [데이터 모델](data-model.md), [생성 계약](contracts/reflection-generation.md), [검증 가이드](quickstart.md)

**범위**: Day 10 IMP-090·IMP-091. Day 11/12 생성 화면·Retry·편집/완료 UI·Home 연계는 제외한다.

**테스트**: 명세 FR-013의 기본 외부 격리 검증 및 헌법의 migration·소유자·LLM 회귀 요구에 따라 포함한다. 스토리별 테스트를 먼저 작성하여 대상 동작의 실패를 확인하고 구현 후 통과시킨다. 내부 정책·ORM을 mock하지 않고 외부 transport만 격리한다.

## 형식 및 경로 규칙

`- [ ] T번호 [P?] [US번호?] 설명`을 사용한다. `[P]`는 명시된 선행 작업 완료 후 서로 다른 파일에서 동시에 진행 가능한 작업이며 agent 실행 요청을 뜻하지 않는다. 경로는 저장소 루트 기준이다. 모든 체크박스는 구현·검증 후에만 완료 표시한다.

## Phase 1: 설정

**목적**: 기존 환경·작업 범위를 확인한다. 프로젝트 재초기화나 신규 의존성 추가는 없다.

- [x] T001 `specs/015-reflection-draft-generation/plan.md`, `.specify/feature.json`, `src/reflections/migrations/`를 대조해 활성 기능·현재 브랜치·작업 전 변경·migration leaf를 확인하고 기존 사용자 변경을 보존한다.
- [x] T002 `pyproject.toml`, `uv.lock`, `compose.yaml`, `rules/styles/python.md`, `rules/frameworks/django.md`, `rules/architecture/database-orm.md`, `rules/architecture/ai-llm-rag.md`를 확인하고 기존 PostgreSQL 테스트 환경·로컬 실행 방식을 준비한다. `.env` 비밀값을 출력하지 않는다.

## Phase 2: 기반 (스토리 공통 전제)

**목적**: 생성 없이도 초안 저장을 검증할 공통 자료 구조와 검증기를 제공한다.

- [x] T003 `src/integrations/llm/contracts.py`에 불변 ReflectionSourceTurn(sequence·question·answer), ReflectionGenerationContext(turns tuple), 신뢰되지 않은 proposal, ReflectionProvider Protocol 및 ReflectionGenerationError/Timeout/Unavailable/Rejected/ConfigurationError를 추가한다. `src/reflections/drafts.py`에 source Interview id·원래 turn snapshot·검증 sections·canonical Markdown을 가진 ReflectionDraftResult와 Policy/Validation/DraftConflict/Persistence 오류를 정의한다.
- [x] T004 [P] `src/reflections/drafts.py`에 저장·생성 공통 검증 및 canonical render를 구현한다. sections “1–10개”, title “비공백 string 1–120자, 단일 줄”, paragraphs “section당 1–10개”, text “비공백 string 1–2,000자”, evidence “문단당 1–10개, 중복 sequence·quote 거부”, sequence “bool 제외 양의 int”, quote “비공백 string 1–500자”와 원문 부분 문자열, 완성 초안 Markdown “1–22,000자”·수정본 “비공백 1–20,000자”를 강제한다. 정확한 key set·타입·표현 연결·짧은 답변 fallback 및 계약의 금지 형식을 검증하고 원문을 임의 절단하지 않는다. T003에 의존한다. 생성 계약의 허용/금지 형식 및 질문용 _QUESTION_PROHIBITED_PATTERNS의 NFKC·casefold·공백 정규화 비교를 적용하고 입력 answer·evidence는 출력 형식 검사에서 제외한다.
- [x] T005 [P] `tests/reflections/conftest.py`에 서로 다른 소유자, REFLECTION_READY/IN_PROGRESS, 미완료 Coverage, sequence 순 확정·미답변 Turn 및 prepared proposal/result fixture를 추가한다. 비문학·소설·제한된 맥락·짧은 답변·유보/반대·정책 변경 입력을 synthetic 원문으로 구성하고 실제 사용자 자료·credential을 사용하지 않는다. T003에 의존한다.

**체크포인트**: T001–T005 완료 후 스토리 구현 시작. prepared result로 US1을 생성 기능 없이 검증할 수 있다.

## Phase 3: US1 — 초안과 내 수정 내용을 구분해 보존하기 (P1, MVP / IMP-090)

**독립 테스트**: prepared result를 저장·재조회하고 수정본을 저장한다. 원래 초안·가변 구성·수정본이 각각 유지되고 자동 완료와 타인 접근은 없다.

### 테스트

- [x] T006 [P] [US1] `tests/reflections/test_models.py`에 Interview당 unique, 본문·수정본 비공백/길이 경계, JSON array shape, Draft-only·completed_at=None, 최초 관계·AI 내용 변경 거부 및 None 수정본을 검증하는 ORM 테스트를 작성한다. 초안 22,000자 허용·22,001자 거부와 수정본 20,000자 허용·20,001자 거부 경계를 각각 검증한다.
- [x] T007 [P] [US1] `tests/reflections/test_drafts.py`에 prepared result 저장·재조회·수정본 저장, canonical 일치, 타인/없는 대상·관계 불일치·준비 전·빈 답변 거부, 같은 Interview 재저장 conflict·원본 불변, 변조/cross-Interview/stale 결과 거부 및 Provider 미호출 테스트를 작성한다. 최대 입력 10개 × 2,000자에서 준비된 원문 보존 초안의 생성 없이 저장·재조회 성공을 검증한다.

### 구현

- [x] T008 [US1] `src/reflections/models.py`에 Reflection을 추가한다. id “BigAutoField”, interview “OneToOneField, related_name=reflection, CASCADE”, draft_markdown “최초 AI 초안, 비공백 1–22,000자”, draft_sections “순서 있는 section·문단·evidence 배열, canonical 본문과 일치”, revised_markdown “None은 수정본 없음, 저장 시 비공백 1–20,000자”, status “CharField, default=DRAFT”·“Day 10은 DRAFT만 허용”, completed_at “nullable DateTimeField”·“Day 10은 항상 None”, created_at “auto_now_add”, updated_at “auto_now”를 적용한다. DB CHECK·Model save validation 및 최초 interview·초안 불변을 구현하고 중복 Reading/Book/user FK는 추가하지 않는다.
- [x] T009 [US1] `src/reflections/migrations/0007_reflection.py`를 현재 leaf 다음 additive CreateModel로 생성하고 `sqlmigrate`에서 새 테이블·FK·unique·CHECK·잠금을 확인한다. 기존 2초 transaction-scoped lock timeout 관례와 안전 스킬을 적용하고 필요 시 FK database/state 분리를 사용한다. 기존 schema·기록 변경과 backfill은 금지한다. T008에 의존하며 실제 번호가 달라지면 설계·검증 명령도 맞춘다.
- [x] T010 [US1] `src/reflections/drafts.py`에 get_reflection_draft·save_reflection_draft·save_reflection_revision을 keyword-only Service로 구현한다. user scope 재조회, create의 REFLECTION_READY·book 관계·답변 조건, 짧은 atomic/Interview lock·snapshot/proposal 재검증·중복 conflict, 수정본의 Reflection lock·초안 불변·수정본/updated_at만 변경을 적용한다. 수정본은 원문에 없는 사용자 생각을 허용하고 형식/길이만 검증한다. T008–T009에 의존한다.
- [x] T011 [US1] `tests/reflections/test_migrations.py`에 실제 PostgreSQL migration 전후 Interview·Turn·Coverage·Decision 보존, 새 테이블 제약, 테스트 DB 역방향 및 최종 leaf 복원을 검증한다. 실제 생성 SQL의 additive 범위·lock timeout도 assertion으로 확인한다. T009에 의존한다.
- [x] T012 [US1] `tests/reflections/test_drafts.py`, `tests/reflections/test_models.py`, `tests/reflections/test_migrations.py`의 US1 검사를 실행하여 저장·수정본 없음·원본 불변·소유자·중복·rollback 인수 조건을 확인한다. 환경 실패는 회귀와 구분하고 `specs/015-reflection-draft-generation/quickstart.md`에 결과와 미검증 범위를 기록한다. T006–T011에 의존한다.

**체크포인트**: 생성 Provider 없이 IMP-090 저장 기반이 동작한다. 화면·최종 완료 전이는 추가하지 않는다.

## Phase 4: US2 — 내가 답한 생각으로 독서노트 초안 만들기 (P1 / IMP-091 생성 기반)

**독립 테스트**: fake 또는 주입한 외부 경계로 생성만 요청하고 DB 변경 없이 검증된 Markdown을 얻는다. 짧은 답변·유보 표현·가변 구성과 문단 근거를 확인한다.

### 테스트

- [x] T013 [P] [US2] `tests/integrations/llm/test_reflection.py`에 strict root/nested schema·decode, unknown/missing key·bool sequence·잘못된 배열/길이/인용·질문에서 복사한 근거·금지 형식 거부, 표현 연결 및 한 글자 답변 fallback, canonical render·instruction/payload 신뢰 분리 테스트를 작성한다. 초안 22,001자 거부, 계약의 링크/reference/자동 링크·이미지·HTML·heading·fence 허용/거부 사례 및 대소문자·공백·tab·개행·전각 패턴 변형을 검증한다.
- [x] T014 [P] [US2] `tests/reflections/test_drafts.py`에 owner·REFLECTION_READY·book 일치·확정 답변 sequence-only snapshot, 미답변/다른 기록/메모/Knowledge/meaning/Coverage 제외, factory 이전 정책 거부, 미완료 Coverage 허용, 비영속 생성·transaction 밖 외부 호출 및 생성 후 명시 저장 테스트를 추가한다. T012에 의존하며 US1 테스트 파일 수정 완료 후 진행한다.

### 구현

- [x] T015 [P] [US2] `src/integrations/llm/reflection.py`에 공통 schema·한국어 trusted instruction·untrusted turns payload·wire decode를 구현한다. 답변만 근거, 질문은 문맥, 새 사실/생각 금지, 유보·반대·감정 강도 유지, 가변 section·짧은 초안, 문단별 정확한 인용을 명시하고 별도 Markdown 출력은 받지 않는다.
- [x] T016 [P] [US2] `src/integrations/llm/fake.py`에 답변 원문 보존 문단·neutral title·정확한 quote의 deterministic FakeReflectionProvider를 구현한다. network·credential·DB 없이 공통 검증에 통과할 proposal을 만들며 금지 입력은 검증에서 거부될 수 있도록 한다. 최대 입력 10개 × 2,000자를 각 한 문단으로 보존하고 제목·canonical 구분자 포함 22,000자 이하를 보장한다.
- [x] T017 [US2] `src/reflections/drafts.py`에 generate_reflection_draft를 구현한다. owner·상태·관계·확정 답변 “최대 10개”·“각 원문 최대 2,000자”를 검증하고 factory 전에 부적합 입력을 거부한다. 기존 IN_PROGRESS-only helper 대신 별도 scope를 사용하고 외부 호출 후 T004 검증으로 비영속 결과를 반환한다. T015–T016에 의존하며 provider 주입으로 이 단계에서 독립 실행 가능하게 한다. 기본 factory 연결은 US3에서 완성한다.
- [x] T018 [US2] `tests/integrations/llm/test_reflection.py`, `tests/reflections/test_drafts.py`를 실행해 fake·prepared proposal의 짧은 답변/비문학/소설/유보 인수 조건과 생성→명시 저장을 검증한다. `specs/015-reflection-draft-generation/quickstart.md`에 자료별 형식·근거 판정 및 실제 Provider 의미 품질 미검증을 구분해 기록한다. T013–T017에 의존한다. 최대 입력 fake 생성→저장→재조회에서 답변 원문 모두 보존·22,000자 이하를 확인한다.

## Phase 5: US3 — 생성 방식과 실패에 관계없이 원문 지키기 (P2 / IMP-091 Provider 통합)

**독립 테스트**: 네 provider의 동일 계약을 격리된 transport로 검증하고 timeout·설정 오류·출력 거부에서 모든 기존 기록의 불변과 안전한 오류를 확인한다.

### 테스트

- [x] T019 [P] [US3] `tests/integrations/llm/test_structured_providers.py`에 reflection task·공통 prompt/payload/schema, OpenAI format name·store=False·tools 없음·재시도 없음, Gemini AFC disable·한 번 시도, Ollama loopback/schema, 전용 Timeout/Unavailable/Rejected 매핑과 기존 first/analysis/next 회귀 테스트를 추가한다.
- [x] T020 [P] [US3] `tests/integrations/llm/test_factory.py`에 fake/openai/gemini/ollama Reflection 선택, unknown/잘못된 설정의 reflection ConfigurationError, 자동 fallback·재요청 없음 테스트를 추가한다.

### 구현과 인수

- [x] T021 [US3] `src/integrations/llm/interview.py`에 generate_reflection capability를 추가하고 `src/integrations/llm/openai.py`, `gemini.py`, `ollama.py`의 `_request(task="reflection")`·오류 분기를 명시 확장한다. OpenAI name=reflection_draft 및 기존 transport 안전 설정을 유지하며 기존 클래스명·세 capability를 변경하지 않는다.
- [x] T022 [US3] `src/integrations/llm/factory.py`에 get_reflection_provider를 추가하여 기존 LLM_PROVIDER/model/timeout 설정을 사용하고 constructor의 질문 ConfigurationError를 reflection 오류로 변환한다. `src/reflections/drafts.py`의 provider=None 기본 경로에 연결한다. T021에 의존한다.
- [x] T023 [US3] `tests/reflections/test_drafts.py`에 provider 실패·빈/잘못된 출력·악성 입력에서 기존 질문·답변·Coverage·Reflection·수정본·Interview 상태 불변, 호출 1회, 안전 오류/log 비노출을 검증한다. synthetic secret·원문 sentinel로 유출을 assertion하고 필요 시 `src/reflections/drafts.py`의 안전 reason code 처리를 완성한다. T021–T022에 의존한다. 입력 answer 속 정책 변경 문구를 지시로 실행하지 않는 검사와 출력에 복사된 금지 패턴 거부 검사를 분리한다. revised_markdown의 일반 Markdown 제목·목록 허용 및 링크·이미지·HTML·정규화 지시 패턴 거부도 검증한다.
- [x] T024 [US3] `tests/integrations/llm/test_live_smoke.py`에 reflection opt-in smoke를 추가한다. 기존 live marker·credential skip·Ollama OLLAMA_LIVE_TEST 조건과 application 검증을 사용하고 자료별 모든 제목·서술의 원문 대조 방법을 `specs/015-reflection-draft-generation/quickstart.md`에 정리한다. 실제 유료 호출·모델 다운로드는 이 테스트 작성으로 실행하지 않는다.
- [x] T025 [US3] `tests/integrations/llm/test_structured_providers.py`, `test_factory.py`, `tests/reflections/test_drafts.py`의 기본 외부 격리 검사를 실행한다. `specs/015-reflection-draft-generation/quickstart.md`에 provider별 계약 결과와 실제 연결·의미 품질의 실행/미실행을 구분해 기록한다. 실제 호출은 사용자가 별도로 선택한 환경에서만 `-m live ... -k reflection`으로 수행하며 미실행을 통과로 표시하지 않는다. T019–T024에 의존한다.


## Phase 6: 마무리 및 교차 검증

- [x] T026 `specs/015-reflection-draft-generation/quickstart.md`의 좁은 검사와 `src/manage.py makemigrations --check --dry-run`을 실행하고 현재 수정 파일에 Ruff format·safe lint fix를 적용한다. 이미 성공한 좁은 검사는 새 영향이 있을 때만 재실행하고 SQL 번호·명령 경로를 실제 구현과 맞춘다. T025에 의존한다.
- [x] T027 `src/reflections/models.py`, `src/reflections/drafts.py`, `src/integrations/llm/reflection.py`, 세 transport 및 관련 tests의 diff·검사 결과를 독립된 검토 관점으로 대조해 owner scope·최초 초안 불변·실패 보존·입력/출력 신뢰 경계를 확인한다. `specs/015-reflection-draft-generation/quickstart.md`에 근거·잔여 의미 품질 한계·필요 수정 및 영향 검사 결과를 기록한다. T026에 의존한다.
- [x] T028 [P] `README.md`의 구현 상태·LLM capability/오류 안내와 `CHANGELOG.md`를 실제 구현·검증 범위에 맞게 수술적으로 동기화한다. 미검증 Provider 품질이나 후속 UI를 구현 완료로 표현하지 않는다. T027에 의존한다.
- [x] T029 `scripts/verify.py`의 표준 명령 `uv run python scripts/verify.py`를 실행하여 Django check·Ruff format/lint·기본 pytest를 확인하고 `specs/015-reflection-draft-generation/quickstart.md`에 실행 결과 또는 환경 차단·미검증을 기록한다. T027에 의존하며 T028 문서 작업과 별도로 실행 가능하다. 검토로 코드가 변경되면 해당 좁은 검사도 먼저 수행한다.
- [x] T030 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-090·091 및 `specs/015-reflection-draft-generation/tasks.md` 완료 상태를 확보한 증거로 갱신한다. 실제 생성/품질 인수가 미실행이면 IMP-091 전체 완료를 주장하지 않고 남은 범위를 명시한다. T028–T029에 의존한다. 브라우저 실행·배포·commit/push는 추가하지 않는다.

## 의존성 및 실행 순서

```text
T001 → T002 → T003 → (T004 ∥ T005)
  → US1: (T006 ∥ T007) → T008 → T009 → T010 → T011 → T012
  → US2: (T013 ∥ T014) → (T015 ∥ T016) → T017 → T018
  → US3: (T019 ∥ T020) → T021 → T022 → T023 → T024 → T025
  → T026 → T027 → (T028 ∥ T029) → T030
```

공통 기초 이후 US1은 prepared result로 독립 동작한다. US2 생성은 저장 없이 독립 검증 가능하지만 같은 `drafts.py`를 수정하므로 실행 순서는 US1 뒤로 고정한다. US3은 US2 생성 계약을 재사용하여 네 provider와 실패 흐름을 완성한다. 테스트 DB의 migration/역방향 검사를 별도 동시 pytest 프로세스로 공유하지 않는다.

## 병렬 예시

- 기반: T003 이후 T004의 `src/reflections/drafts.py` 검증기와 T005의 `tests/reflections/conftest.py` 자료 작성.
- US1: T006 모델 테스트와 T007 Service 테스트는 서로 다른 파일이므로 병렬 작성 가능하다.
- US2: T015 schema/prompt helper와 T016 fake 구현은 공유 계약 이후 병렬 작성 가능하다. T017 통합은 둘 완료 후 수행한다.
- US3: T019 transport 계약 테스트와 T020 factory 테스트는 병렬 작성 가능하다. 세 transport 구현 T021은 공통 capability와 함께 하나의 논리적 작업으로 처리한다.
- 마무리: 검토 완료 후 T028 문서 갱신과 T029 표준 검사 실행은 파일 쓰기 충돌 없이 진행 가능하다.

## 요구사항 추적

| 요구사항 | 작업 |
| --- | --- |
| FR-001·FR-002 | T004, T006, T008–T012 |
| FR-003·FR-005 | T006–T008, T010, T012 |
| FR-004 | T007, T010, T014, T017, T023, T027 |
| FR-006 | T003, T005, T014, T017 |
| FR-007·FR-008 | T005, T013, T015–T018, T024–T025 |
| FR-009 | T016–T022, T024–T025 |
| FR-010·FR-011 | T004, T013, T015, T017, T023, T027 |
| FR-012·FR-013 | T014, T017, T019–T025, T029 |
| FR-014 | T001, T028, T030 및 전체 단계의 범위 제한 |

## 구현 전략

첫 증가분은 Phase 1–3의 US1, 즉 생성 없이 prepared 초안을 저장·조회하고 수정본을 보존하는 IMP-090 기반이다. 다음 증가분은 US2의 fake/주입 Provider 생성 계약, 마지막 증가분은 US3의 실제 transport capability·실패 보존이다. 각 체크포인트에서 독립 인수 조건을 검증하고 계속 진행한다. 생성 결과를 만든 것만으로 저장·최종 완료를 처리하지 않는다. 실제 연결·품질의 미검증은 기본 자동 검사 통과와 별도로 보고한다.
