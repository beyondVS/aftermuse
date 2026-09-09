---
description: "첫 인터뷰 Turn 구현을 위한 의존성 순서 작업 목록"
---

# 작업: 첫 인터뷰 Turn

**입력**: `/specs/009-first-interview-turn/`의 `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**테스트**: 기능 사양과 프로젝트 헌법이 코드 변경의 관련 테스트를 요구하므로 각 사용자 스토리에 테스트 작업을 포함한다. 새 동작 테스트는 구현 전에 작성하고 예상한 이유로 실패하는지 확인하며, 기존 schema 회귀 테스트는 현재 동작을 기준선으로 확인한다.

**구성**: 공유 기반을 먼저 마련한 뒤 각 사용자 스토리를 독립적으로 구현·검증할 수 있도록 단계별로 그룹화한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 선행 작업 완료 후 서로 다른 파일에서 병렬 실행 가능
- **[Story]**: 사용자 스토리 추적 레이블 (`US1`~`US4`)
- 모든 작업 설명은 수정하거나 실행할 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 인프라)

**목적**: OpenAI SDK와 첫 질문 Provider 설정을 프로젝트 실행 환경에 추가한다.

- [X] T001 `pyproject.toml`에 `openai~=3.10.0` 런타임 의존성을 추가하고 `uv.lock`을 갱신한다.
- [X] T002 [P] `.env.example`과 `src/config/settings.py`에 provider, pinned model, API key, 30초 timeout 설정을 추가하고 필수/선택 설정의 시작 실패 정책을 반영한다.
- [X] T003 [P] `src/integrations/__init__.py`와 `src/integrations/llm/__init__.py`를 생성해 LLM integration package 구조를 마련한다.

**체크포인트**: lockfile로 재현 가능한 의존성과 credential을 노출하지 않는 설정 경계가 준비된다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 사용자 스토리가 공유하는 Provider-neutral 타입, 오류, fake와 factory를 구현한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 작업을 시작하지 않는다.

- [X] T004 `src/integrations/llm/contracts.py`에 immutable 질문 Context/결과 타입, `QuestionProvider` protocol, timeout·unavailable·rejected·configuration 오류 taxonomy를 정의한다.
- [X] T005 [P] `src/integrations/llm/fake.py`에 정상, 실패, 시간 초과, 사용할 수 없는 결과를 network 없이 결정적으로 재현하는 fake provider를 구현한다.
- [X] T006 [P] `src/integrations/llm/factory.py`에 Django 설정을 읽어 fake provider를 생성하고 알려지지 않은 provider 설정을 안전하게 거부하는 factory 기본 구조를 구현한다.

**체크포인트**: Provider 경계를 통해 실제 외부 호출 없이 모든 핵심 흐름을 테스트할 수 있다.

---

## Phase 3: 사용자 스토리 1 - 준비 수준에 맞는 첫 질문 받기 (우선순위: P1) 🎯 MVP

**목표**: `READY`와 `READY_LIMITED`의 신뢰 경계를 지키면서 첫 질문 하나를 생성하고 반복 접근에서는 기존 Turn을 재사용한다.

**독립 테스트**: 두 준비 수준의 Interview 각각에서 Context와 질문 정책을 검증하고, 동일 Interview에 대한 반복·동시 생성이 sequence 1 Turn 한 건으로 수렴하는지 확인한다.

### 사용자 스토리 1 테스트

- [X] T007 [P] [US1] `tests/reflections/test_context.py`에 소유 관계, 진행 상태, 안정된 Knowledge 순서, `READY` 포함 및 `READY_LIMITED` 배제, trusted/untrusted 분리 테스트를 작성하고 실패를 확인한다.
- [X] T008 [P] [US1] `tests/integrations/llm/test_fake.py`에 fake provider 정상 결과와 호출 기록이 Context 계약을 보존하는 테스트를 작성하고 실패를 확인한다.
- [X] T009 [P] [US1] `tests/integrations/llm/test_openai.py`에 Responses API strict structured output, pinned model, `store=False`, tools 미전달, 30초 timeout, retry 0 설정과 함께 `READY`에는 확인된 맥락을 사용하고 `READY_LIMITED`에는 기억·인상·감정 중심 지침만 전달되는지 SDK client mock으로 검증하고 실패를 확인한다.
- [X] T010 [US1] `tests/reflections/test_services.py`에 `READY` 질문 후보의 확인된 책 맥락 사용, `READY_LIMITED` 질문 후보의 기억 중심 정책, 유효 질문의 sequence 1 저장, 기존 Turn 재사용 시 provider 미호출, 한 문장·300자 검증과 경쟁 생성의 단일 Turn 수렴 테스트를 작성하고 실패를 확인한다.
- [X] T011 [US1] `tests/reflections/test_views.py`에 익명 사용자의 detail·first-question 접근 차단, detail GET의 무변경 Loading 상태, first-question POST의 owner 404·관계/status 409, HTMX fragment와 일반 redirect 계약 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 1 구현

- [X] T012 [P] [US1] `src/reflections/context.py`에 현재 Interview의 Book·Reading·준비 수준과 허용된 Knowledge만 immutable payload로 구성하는 Context builder를 구현한다.
- [X] T013 [P] [US1] `src/integrations/llm/openai.py`에 Responses API structured output Adapter를 구현하고 `src/integrations/llm/factory.py`에 OpenAI provider 등록을 완성하며, prompt 지침과 untrusted payload를 분리하고 prompt·원문·credential을 로그에 남기지 않는다.
- [X] T014 [US1] `src/reflections/services.py`에 질문 후보 검증과 transaction 밖 provider 호출 후 row lock·재검증·sequence 1 멱등 저장을 수행하는 `ensure_first_question`을 구현한다.
- [X] T015 [US1] `src/reflections/urls.py`와 `src/reflections/views.py`에 owner-scoped detail GET 및 CSRF 보호 first-question POST를 추가하고 HTML/HTMX가 같은 Service 계약을 사용하게 한다.
- [X] T016 [US1] `src/templates/reflections/interview_detail.html`, `src/templates/reflections/_interview_loading.html`, `src/templates/reflections/_interview_question.html`에 무변경 GET shell, 보이는 Loading, 자동 HTMX POST와 no-JS 준비 form, 현재 질문 상태를 구현한다.

**체크포인트**: 첫 질문의 정상 경로가 준비 수준별 정책을 지키며 한 건만 저장되고 독립적으로 시연 가능하다.

---

## Phase 4: 사용자 스토리 2 - 한 질문에 집중해 답변하기 (우선순위: P1)

**목표**: Desktop·Mobile Web에서 현재 책과 질문 하나에 집중해 답변을 작성·제출할 수 있는 접근 가능한 form을 제공한다.

**독립 테스트**: 첫 질문이 있는 detail 응답의 semantic HTML을 검사해 label/help 연결, 실제 submit button, 키보드 focus, 색상 외 상태 문구와 반응형 class 계약을 확인한다.

### 사용자 스토리 2 테스트

- [X] T017 [P] [US2] `tests/reflections/test_forms.py`에 답변 form의 필수값, 공백 거부, 2,000자 경계와 원문 보존 테스트를 작성하고 실패를 확인한다.
- [X] T018 [US2] `tests/reflections/test_views.py`에 질문 heading, textarea label/help/error, 실제 submit button, 제출 중 상태, Desktop/Mobile semantic 응답과 색상 외 상태 식별 계약 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 2 구현

- [X] T019 [P] [US2] `src/reflections/forms.py`에 공백을 거부하고 최대 2,000자를 자르지 않으며 사용자가 입력한 원문을 bound data로 유지하는 answer form을 구현한다.
- [X] T020 [US2] `src/templates/reflections/_interview_question.html`에 책 식별 정보, 단일 질문, 부담을 낮추는 안내, 연결된 label/help/error와 progressive-enhancement 제출 form을 구현한다.
- [X] T021 [US2] `src/static/css/app.css`에 집중형 질문 배치, 명확한 focus 표시, 색상 외 상태 표현과 대표 Desktop/Mobile 폭에서 동작하는 반응형 스타일을 추가한다.

**체크포인트**: 질문 화면과 답변 입력·제출 조작이 마우스나 색상에 의존하지 않고 독립적으로 검증된다.

---

## Phase 5: 사용자 스토리 3 - 답변을 먼저 안전하게 보존하기 (우선순위: P1)

**목표**: 첫 답변 원문을 최초 한 번만 확정하고 실패 시 입력을 유지하며 저장 후 수정이나 다음 질문 행동을 제공하지 않는다.

**독립 테스트**: 최초 저장, 동일 답변 멱등 재제출, 다른 답변 conflict, 동시 제출, DB 실패를 재현해 원문과 Turn이 보존되고 화면 상태가 계약대로인지 확인한다.

### 사용자 스토리 3 테스트

- [ ] T022 [P] [US3] `tests/reflections/test_models.py`에 기존 schema가 nullable 미응답 상태와 2,000자 답변 원문을 migration 없이 보존하는 회귀 테스트를 추가하고 현재 동작을 확인한다.
- [ ] T023 [US3] `tests/reflections/test_services.py`에 최초 답변 저장, 동일 값 멱등 성공, 다른 값 409용 conflict, row lock 동시 제출, DB 실패 시 answer `NULL` 유지와 후속 작업 0건 테스트를 작성하고 실패를 확인한다.
- [ ] T024 [US3] `tests/reflections/test_views.py`에 익명 사용자의 answer POST 접근 차단, answer POST의 400·404·409·성공 응답, 비소유자와 미존재 대상의 동일한 404 형태, HTML redirect/HTMX saved fragment, validation·DB 실패 입력 보존 및 다음 질문 action 부재 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 3 구현

- [ ] T025 [US3] `src/reflections/models.py`에 DDL 변경 없이 Answer의 1~2,000자 application validation과 최초 확정 불변 계약을 보강한다.
- [ ] T026 [US3] `src/reflections/services.py`에 owner-scoped row lock, 최초 저장, 동일 값 멱등 처리, 다른 값 conflict와 DB 오류 변환을 수행하되 Coverage·분석·다음 질문을 호출하지 않는 `save_first_answer`를 구현한다.
- [ ] T027 [US3] `src/reflections/urls.py`와 `src/reflections/views.py`에 sequence 1 answer POST를 연결하고 validation·저장 실패에는 bound form을, 성공에는 redirect 또는 saved fragment를 반환한다.
- [ ] T028 [US3] `src/templates/reflections/_interview_answer_saved.html`에 확정 원문과 저장 완료 상태를 표시하고 수정·교체·다음 질문 action을 노출하지 않는 Saved 상태를 구현한다.

**체크포인트**: 저장 성공과 실패 모두에서 사용자의 원문이 유실되거나 덮어써지지 않는다.

---

## Phase 6: 사용자 스토리 4 - 생성 실패에서 안전하게 회복하기 (우선순위: P2)

**목표**: 질문 생성의 실패·30초 timeout·invalid output에서 데이터를 변경하지 않고 같은 화면에서 명시적으로 재시도하게 한다.

**독립 테스트**: 각 Provider 오류를 주입해 Turn 생성 0건과 Error fragment를 확인한 뒤 같은 Interview에서 재시도하여 정상 질문 한 건으로 전환되는지 검증한다.

### 사용자 스토리 4 테스트

- [ ] T029 [P] [US4] `tests/integrations/llm/test_openai.py`에 timeout, 연결/rate-limit/5xx, refusal·empty·incomplete·invalid schema가 안전한 내부 오류로 변환되고 민감 원문이 로그에 없는 테스트를 작성하고 실패를 확인한다.
- [ ] T030 [US4] `tests/reflections/test_services.py`에 provider 오류와 여러 문장·300자 초과·종결 부호 오류가 Turn을 만들지 않으며 재시도 성공 시 첫 Turn 한 건만 저장되는 테스트를 작성하고 실패를 확인한다.
- [ ] T031 [US4] `tests/reflections/test_views.py`에 질문 생성 오류의 503 Error fragment, `role="alert"`, focus target, 실제 retry button, 기존 Interview 보존과 일반 HTML 재시도 계약 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 4 구현

- [ ] T032 [US4] `src/integrations/llm/openai.py`와 `src/reflections/services.py`에 timeout·provider·rejection·configuration 오류 변환과 저장 전 결과 거부를 완성한다.
- [ ] T033 [US4] `src/templates/reflections/_interview_error.html`과 `src/reflections/views.py`에 내부 오류를 노출하지 않는 alert/focus Error 상태와 자동 재시도 없는 명시적 질문 재시도를 구현한다.

**체크포인트**: 모든 생성 실패가 동일 Interview의 데이터 무결성을 유지하며 한 번의 명확한 행동으로 회복된다.

---

## Phase 7: 마무리 및 교차 관심사

**목적**: 전체 계약과 프로젝트 품질 게이트를 함께 검증한다.

- [ ] T034 [P] `README.md`, `docs/README.md`, `CHANGELOG.md`에 첫 질문 생성·답변 저장 흐름, OpenAI Provider 설정, 새 Web 계약과 검증 결과를 기존 문서 관례에 맞춰 동기화한다.
- [ ] T035 [P] `specs/009-first-interview-turn/quickstart.md`의 Context, Provider, Service, HTML·HTMX 검증 명령을 실행하고 문서와 실제 명령이 다르면 해당 파일을 동기화한다.
- [ ] T036 `src/reflections/migrations/`에 새 migration이 생기지 않았는지 `makemigrations --check --dry-run`으로 확인하고 `tests/reflections/`, `tests/integrations/llm/`의 전체 기능 테스트를 실행한다.
- [ ] T037 `scripts/verify.py`로 Django check, migration drift, Ruff format/lint와 credential·network 없는 전체 pytest 품질 게이트를 실행한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1 설정**: 선행 단계 없이 시작한다.
- **Phase 2 기반**: Phase 1 완료에 의존하며 모든 사용자 스토리를 차단한다.
- **Phase 3 US1**: Phase 2 이후 시작하며 첫 질문과 Question 상태를 제공한다.
- **Phase 4 US2**: Phase 2 이후 form 단위 작업을 시작할 수 있지만, 질문 화면 통합 검증은 US1의 Question 상태에 의존한다.
- **Phase 5 US3**: Phase 2 이후 Service 단위 작업을 시작할 수 있지만, Web 저장 흐름은 US1의 Turn과 US2의 form에 의존한다.
- **Phase 6 US4**: Phase 2 이후 Provider 오류 단위 작업을 시작할 수 있지만, same-screen Error 통합은 US1의 생성 흐름에 의존한다.
- **Phase 7 마무리**: 제공하려는 모든 사용자 스토리가 완료된 뒤 실행한다.

### 사용자 스토리 의존성 그래프

```text
Setup → Foundation → US1 ─┬→ US2 ─→ US3 ─┐
                         └→ US4 ─────────┴→ Polish
```

- **US1**은 공유 기반 외 다른 사용자 스토리에 의존하지 않는 첫 번째 MVP 증가분이다.
- **US2**는 form validation을 독립 테스트할 수 있고, 최종 Question UI 조립에서 US1을 사용한다.
- **US3**는 Service 계약을 독립 테스트할 수 있고, Web 흐름에서 US1의 Turn과 US2 form을 사용한다.
- **US4**는 Provider 오류를 독립 테스트할 수 있고, 화면 회복 경로에서 US1을 사용한다.

### 각 사용자 스토리 내부 순서

1. 새 동작 테스트를 먼저 작성하고 의도한 계약 부재로 실패하는지 확인하며, 기존 동작 회귀 테스트는 기준선 통과를 확인한다.
2. immutable 타입과 Context/Form 같은 입력 경계를 구현한다.
3. Provider/Service 정책과 transaction 경계를 구현한다.
4. URL/View를 얇게 연결한다.
5. Template/CSS 상태를 통합하고 해당 스토리 테스트를 통과시킨다.

### 병렬 작업 기회

- T002와 T003은 서로 다른 설정/package 파일에서 병렬 진행할 수 있다.
- T005와 T006은 T004 완료 후 서로 다른 Provider 파일에서 병렬 진행할 수 있다.
- US1의 T007~T009와 구현의 T012~T013은 각각 서로 다른 파일에서 병렬 진행할 수 있다.
- US2의 T017과 선행 US1 view 작업은 서로 다른 파일에서 병렬 진행할 수 있다.
- US3의 T022는 T023~T024와 다른 테스트 파일이므로 병렬 진행할 수 있다.
- US4의 T029는 T030~T031과 다른 경계의 테스트이므로 병렬 진행할 수 있다.
- US1 정상 경로가 안정된 뒤 US2 UI와 US4 오류 경로를 서로 병렬로 진행할 수 있다.

## 병렬 실행 예시

### 사용자 스토리 1

```text
Task T007: tests/reflections/test_context.py의 Context 신뢰 경계 테스트
Task T008: tests/integrations/llm/test_fake.py의 fake provider 계약 테스트
Task T009: tests/integrations/llm/test_openai.py의 정상 Adapter 계약 테스트
```

### 사용자 스토리 3과 4

```text
Task T022: tests/reflections/test_models.py의 Answer 저장 형식 회귀 테스트
Task T029: tests/integrations/llm/test_openai.py의 Provider 오류 변환 테스트
```

## 구현 전략

### MVP 우선

1. Phase 1과 Phase 2를 완료한다.
2. Phase 3의 US1을 완료해 준비 수준에 맞는 첫 질문 한 건을 제공한다.
3. US1의 Context, Provider, Service, HTML 계약을 독립 검증하고 중지 가능한 MVP 증가분으로 확인한다.
4. 실제 답변 제출이 필요한 Bundle 06A 완성을 위해 US2와 US3를 순서대로 추가한다.
5. US4의 회복 경로를 추가한 뒤 전체 품질 게이트를 통과한다.

### 점진적 제공

1. **US1**: 첫 질문 생성·재사용과 Loading → Question 전환
2. **US2**: 집중형·접근 가능한 답변 작성 UI
3. **US3**: 최초 답변의 불변·멱등 저장과 Saved 상태
4. **US4**: 질문 생성 실패의 same-screen Error와 재시도
5. 각 증가분마다 해당 스토리 테스트를 통과시킨 뒤 다음 단계로 이동한다.

## 참고 사항

- `[P]`는 선행 작업 완료 후 파일 충돌이나 미완성 의존성이 없는 작업만 표시한다.
- Provider I/O는 DB transaction 밖에서 실행하고, 질문/답변 영속화 transaction은 짧게 유지한다.
- 실제 OpenAI 연결은 선택형 `live` smoke이며 기본 테스트와 완료 조건에 포함하지 않는다.
- 실제 브라우저 조작은 현재 승인된 완료 조건이 아니므로 작업에 포함하지 않고 결정적 HTML 응답 계약으로 Desktop/Mobile·접근성을 검증한다.
- schema는 기존 column을 재사용하므로 migration을 생성하지 않으며 drift 0건을 검증한다.
