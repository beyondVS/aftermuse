---
description: "Day 08 질문 상한과 Soft Stop 구현 작업"
---

# 작업: 질문 상한과 Soft Stop

**입력**: `specs/013-question-budget-soft-stop/`의 spec.md, plan.md, research.md, data-model.md, contracts/interview-flow.md, quickstart.md

**사전 조건**: Day 07 답변 저장·Coverage·다음 질문·검증된 질문 생략 경로 유지

**테스트**: 사양의 독립 테스트와 헌법 품질 게이트에 필요한 PostgreSQL Service·Web·migration 회귀 테스트를 포함한다. 실제 브라우저와 외부 LLM live 호출은 필수가 아니다.

**구성**: 각 사용자 스토리가 관찰 가능한 독립 증가분이 되도록 구성한다. 기존 파일의 사용자 변경은 보존하며 Day 09~10 Reflection 초안·생성·전환은 구현하지 않는다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일에서 선행 미완료 작업 없이 병렬 가능
- **[Story]**: 명세의 사용자 스토리
- 모든 작업은 체크박스, 순차 ID, 실제 대상 파일 경로를 포함한다.

## Phase 1: 설정

**목적**: 이미 존재하는 Django 프로젝트의 Day 08 정책값만 추가한다.

- [X] T001 `src/config/settings.py`에 목표 5~6, 일반 상한 8, 절대 상한 10의 단순 설정과 `4 ≤ 목표 최소 ≤ 목표 최대 ≤ 일반 상한 < 절대 상한` 검증을 추가하고 기존 Provider timeout을 유지한다.

---

## Phase 2: 기반

**목적**: 모든 스토리가 공유하는 선택 대기 영속 상태와 정책 경계를 마련한다.

- [X] T002 `src/reflections/models.py`에 답변이 확정된 `InterviewTurn`과 일대일인 진행 선택을 추가한다. `kind`는 `SOFT_STOP`/`CAP_EXTENSION`, `selection`은 미결정/`END`/`CONTINUE`, `candidate_question`은 기존 검증을 통과한 단일 비공개 질문이며 `created_at`·`decided_at`으로 대기·확정을 구분한다. 기존 Interview·Turn 행과 필드를 변경하지 않는다.
- [X] T003 `src/reflections/migrations/0005_interview_progress_decision.py`에 신규 선택 테이블의 FK·유일성·enum/선택 제약을 추가한다. 이전 코드가 기존 Interview·Turn을 계속 읽을 수 있게 하고 `sqlmigrate`의 실제 DDL·잠금 범위에 따라 제한된 `lock_timeout`을 적용한다.
- [X] T004 `tests/reflections/test_migrations.py`와 `tests/reflections/test_models.py`에 기존 Interview·Turn을 보존하는 적용·역적용 및 한 답변 Turn당 선택 1개, 허용 enum·결정 시점 검증을 추가한다.
- [X] T005 `src/reflections/services.py`에 답변 수와 질문 sequence를 구분하는 Budget 판정, 네 축 `COVERED`·4~7개 답변의 Soft Stop 조건, 8번째 답변에서 Soft Stop보다 일반 상한을 먼저 판단하는 순서, 10문항 절대 상한과 선택 기록 재사용을 위한 공통 순수 정책 함수를 추가한다. 목표 5~6은 강제 종료 조건으로 사용하지 않는다.

**체크포인트**: 기존 Interview 흐름을 바꾸기 전에 저장·설정·정책 경계가 준비된다.

---

## Phase 3: 사용자 스토리 1 - 충분히 이야기한 뒤 마칠지 선택하기 (P1) 🎯 MVP

**목표**: 네 축 `COVERED`, 답변 4~7개, 근거 있는 다음 질문 후보가 있으면 Soft Stop을 표시하고 종료·계속을 한 번만 확정한다.

**독립 테스트**: 4번째 답변 뒤 두 선택지를 확인하고 `end`는 기존 답변을 유지한 `REFLECTION_READY`, `continue`는 보류된 질문 하나로 이어짐을 확인한다. 계속 뒤 다음 답변에도 조건이 유지되면 선택지가 다시 나타난다.

### 테스트

- [X] T006 [P] [US1] `tests/reflections/test_services.py`에 Coverage와 답변 수 경계(3/4문항), 후보 질문의 비공개 대기, Coverage·선택의 원자적 확정, 종료·계속의 Turn 수와 선택 재사용 사례를 추가한다.
- [X] T007 [P] [US1] `tests/reflections/test_views.py`에 일반 POST·HTMX의 Soft Stop 두 버튼, 종료 후 200 준비 안내, 계속 후 질문 하나, 재방문·재노출과 후보 질문 비노출 사례를 추가한다.

### 구현

- [X] T008 [US1] `src/reflections/services.py`의 `process_next_turn`과 commit 경계에 검증된 후보를 Turn으로 확정하기 전 Soft Stop 판정을 추가하고, projected Coverage + `SOFT_STOP` 미결정 기록을 한 트랜잭션으로 저장한다. 기존 답변 선확정과 stale 재검증을 유지한다.
- [X] T009 [US1] `src/reflections/services.py`에 `end|continue` 선택 서비스를 추가한다. Interview 행 잠금과 소유권·현재 Turn 확인 후 `END`는 `REFLECTION_READY`, `CONTINUE`는 후보 질문의 다음 Turn 하나와 같은 트랜잭션에서 확정하고 같은 선택 반복은 기존 결과를 반환한다.
- [X] T010 [US1] `src/reflections/urls.py`와 `src/reflections/views.py`에 CSRF 보호 `reflections:interview_decision` POST를 추가하고 `decision=end|continue` 외 후보·Coverage 입력은 무시 또는 거부한다. 비소유 404, stale·경합 409, 일반 redirect·HTMX fragment 계약을 따른다.
- [X] T011 [US1] `src/templates/reflections/interview_detail.html`, `src/templates/reflections/_interview_soft_stop.html`, `src/templates/reflections/interview_reflection_ready.html`에 답변 보존 안내·두 선택·준비 안내를 연결하고 비공개 후보 질문을 렌더링하지 않는다. 준비 상태는 Reflection 초안·생성 URL 없이 소유자에게 200으로 표시한다.

**체크포인트**: 상한에 미달한 Interview에서 Soft Stop 종료·계속이 독립적으로 동작한다.

---

## Phase 4: 사용자 스토리 2 - 질문 수가 길어지기 전에 멈추기 (P1)

**목표**: 일반 8문항에서 멈추고 `UNCOVERED` 축의 검증된 질문 근거와 사용자 선택이 있을 때만 최대 10문항까지 예외 진행한다.

**독립 테스트**: 8번째 답변에서 예외 불가면 준비 안내, 예외 가능이면 별도 선택 화면을 확인한다. 계속 선택 후 9·10번째 질문과 열 번째 답변 뒤 질문 0개를 확인한다.

### 테스트

- [X] T012 [P] [US2] `tests/reflections/test_services.py`에 8번째 답변의 `UNCOVERED`/`PARTIAL`/전부 `COVERED` 판정과 Soft Stop 우선순위, 명시적 연장 선택, 9번째 답변 뒤 근거 소멸 시 10번째 질문 생략, 10번째 답변·11번째 질문 금지와 오래된 후보 경합 사례를 추가한다.
- [X] T013 [P] [US2] `tests/reflections/test_views.py`에 8번째 답변에서 네 축 `COVERED`이면 Soft Stop 재노출 없이 준비 안내, `UNCOVERED`이면 별도 상한 선택 화면의 두 행동, 10문항 준비 안내 및 일반 POST·HTMX 상태를 추가한다.
- [X] T014 [P] [US2] `tests/integrations/llm/test_fake.py`와 `tests/integrations/llm/test_structured_providers.py`에 8번째 답변의 예외 평가와 허가된 9번째 답변에서 명시적 근거 부족 생략, 무효·빈 결과·timeout 거부 계약을 추가한다.

### 구현

- [X] T015 [US2] `src/reflections/services.py`에 8번째 답변의 일반 상한을 Soft Stop보다 먼저 판단하고 `UNCOVERED` 목표 후보만 `CAP_EXTENSION` 미결정으로 저장한다. 해당 선택의 `CONTINUE` 이력과 현재 Coverage로 9번째 답변 뒤 10번째 질문 가능성을 재평가하고 10번째 답변 후 `REFLECTION_READY`로 확정한다. 8번째 답변에서 `UNCOVERED`가 없거나 10번째 답변이면 질문 Provider를 호출하지 않으며 모든 새 Turn insert 직전에 10문항 상한을 잠금 안에서 재검증한다.
- [X] T016 [US2] `src/integrations/llm/contracts.py`, `src/integrations/llm/fake.py`, `src/integrations/llm/interview.py`, `src/reflections/services.py`에 8번째 답변의 예외 평가와 허가된 9번째 답변에서 근거 있는 `UNCOVERED` 질문이 없다는 명시적 생략을 검증해 준비 상태로 연결한다. 공유 Interview Provider 계약을 사용하는 fake·OpenAI·Gemini·Ollama에서 일반 Day 07의 네 축 `COVERED` 생략 규칙은 보존하고 빈·무효·timeout은 오류로 둔다.
- [X] T017 [US2] `src/templates/reflections/_interview_cap_extension.html`, `src/templates/reflections/interview_detail.html`, `src/reflections/views.py`에 8문항 전용 독서노트 준비/최대 2문항 더 이야기하기 선택과 상한 도달 준비 화면을 연결한다. 네 축이 모두 `COVERED`이면 Soft Stop을 재노출하지 않고, `PARTIAL`만 남거나 질문 근거가 없으면 계속 버튼을 표시하지 않는다.

**체크포인트**: 일반 8문항과 예외 10문항 경계가 독립적으로 검증된다.

---

## Phase 5: 사용자 스토리 3 - 실패 후 답변을 잃지 않고 이어가기 (P2)

**목표**: 분석·생성·저장 실패 및 중단·반복 요청에서 답변을 보존하고 같은 결정·질문으로 수렴한다.

**독립 테스트**: 선택 화면 재방문, 종료·계속 경합, Provider timeout·무효 응답·DB 실패 후 답변과 Coverage·선택·Turn을 확인하고 같은 답변으로 재시도한다.

### 테스트

- [X] T018 [P] [US3] `tests/reflections/test_services.py`에 두 선택의 동시 요청, 같은 선택 반복, 선택·Turn 저장 실패 rollback, 답변 보존과 Provider 재호출 방지, Day 07의 기존 질문 생략 표식에 대한 후속 확정 POST의 멱등 `REFLECTION_READY` 전환 사례를 추가한다.
- [X] T019 [P] [US3] `tests/reflections/test_views.py`에 분석·생성 timeout·무효 결과의 503 재시도, 404/409 비노출, 선택 POST 실패 후 일반/HTMX 복구 및 접근성 상태를 추가한다. Day 07의 기존 질문 생략 표식이 있는 진행 중 Interview의 GET은 DB 변경·재분석 없이 준비 안내를 보여주는지 검증한다.

### 구현

- [X] T020 [US3] `src/reflections/services.py`에 모든 결정 경로의 잠금 후 최신 Interview·Turn·Coverage·선택·Budget 재검증과 DatabaseError rollback을 정리한다. Day 07의 기존 질문 생략 표식이 있는 진행 중 Interview는 후속 확정 POST에서 재분석·질문 생성 없이 `REFLECTION_READY`로 멱등 전환한다. 답변 원문을 재저장하지 않고 기존 선택·다음 Turn·준비 상태를 재사용한다.
- [X] T021 [US3] `src/reflections/views.py`, `src/templates/reflections/_interview_next_error.html`, `src/templates/reflections/_interview_answer_saved.html`, `src/templates/reflections/interview_detail.html`에 Day 07의 기존 질문 생략 표식에 대한 읽기 전용 준비 안내, 답변 보존 사실, 같은 답변으로 재시도, 오류 focus와 HTMX 오류 영역 교체를 확인·보완한다. 실패를 Soft Stop 또는 완료로 표시하지 않는다.

**체크포인트**: 실패·재방문·경합 후에도 답변과 결정이 일관되게 유지된다.

---

## Phase 6: 마무리 및 교차 관심사

- [X] T022 `tests/reflections/test_migrations.py` 및 `src/reflections/migrations/0005_interview_progress_decision.py`에서 PostgreSQL migration 적용·역적용, `sqlmigrate` 결과, FK·유일성·잠금 제한을 확인하고 기존 데이터 재작성·삭제가 없음을 기록한다.
- [X] T023 `specs/013-question-budget-soft-stop/quickstart.md`의 대표 4/8/10문항·생략·오류 시나리오를 관련 pytest와 Django test client로 실행한 뒤 `uv run python scripts/verify.py`를 수행한다.
- [X] T024 `README.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`, `CHANGELOG.md`를 실제 통과한 IMP-080/081/084 상태와 Day 08 동작에 맞춰 수술적으로 동기화한다. 현재 사용자 변경을 덮어쓰지 않는다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **설정**: T001.
- **기반**: T002→T003→T004와 T005. 기반 완료 전 Story의 상태 변경을 시작하지 않는다.
- **US1**: 기반 이후 T006·T007을 병렬로 작성할 수 있다. T008→T009→T010→T011 순서로 구현·검증한다.
- **US2**: US1의 선택 흐름 뒤 T012·T013·T014를 병렬로 작성할 수 있다. T015→T016→T017 순서로 상한 흐름을 연결한다.
- **US3**: US1·US2의 실패 경계가 존재한 뒤 T018·T019를 병렬로 작성할 수 있다. T020→T021로 복구 경로를 확정한다.
- **마무리**: Story 완료 후 T022→T023→T024. 검증 결과 없이 완료 체크박스를 바꾸지 않는다.

### 사용자 스토리 의존성

- **US1 (P1)**: 기반 이후 독립 동작. 이번 기능의 첫 MVP 증가분이다.
- **US2 (P1)**: 같은 선택 모델·POST 계약을 재사용하므로 US1에 의존하지만 8/10문항 수용 기준은 별도 테스트한다.
- **US3 (P2)**: US1·US2의 상태 전이를 대상으로 실패·재시도·경합을 별도 검증한다.

### 병렬 작업 예시

- **US1**: T006 서비스 상태 테스트와 T007 Web 응답 테스트는 서로 다른 파일에서 함께 진행 가능하다.
- **US2**: T012 서비스 상한 테스트, T013 Web 상한 테스트, T014 Provider 생략 계약 테스트는 서로 다른 파일에서 함께 진행 가능하다.
- **US3**: T018 서비스 경합 테스트와 T019 Web 복구 테스트는 서로 다른 파일에서 함께 진행 가능하다.

## 구현 전략

1. 설정·기반을 완료하고 US1을 독립적으로 검증해 Soft Stop 선택을 제공한다.
2. US2에서 일반·예외 상한을 연결하고 8/10문항 경계를 검증한다.
3. US3에서 오류·재시도·경합을 수렴시킨 뒤 PostgreSQL·전체 품질 게이트와 문서를 갱신한다.

Day 09~10 Reflection 초안 생성·저장·화면 전환, 반복 low-information 종료, Focus Coverage, 이전 Turn 열람 및 Credit은 수행하지 않는다.
