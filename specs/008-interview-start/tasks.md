---
description: "인터뷰 시작 기능 구현을 위한 작업 목록"
---

# 작업: 인터뷰 시작

**입력**: `/specs/008-interview-start/`의 설계 문서

**사전 조건**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**테스트**: 기능 사양과 프로젝트 헌법이 model, service, view, migration, 동시성 회귀 검증을 요구하므로 빠른 pytest 기반 테스트를 포함한다. 각 스토리의 테스트를 구현보다 먼저 작성하고 실패를 확인한다. 실제 브라우저 자동화는 작성·실행하지 않으며 반응형 레이아웃, keyboard와 screen reader 접근성은 수동 검증한다.

**구성**: 각 사용자 스토리를 독립적으로 구현·검증 가능한 증가분으로 구성한다. 이번 Bundle에서는 첫 질문·답변, Coverage, Soft Stop, Reflection 데이터/화면, Credit 변경을 구현하지 않는다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 선행 작업 완료 후 서로 다른 파일에서 병렬 실행 가능
- **[Story]**: 작업이 속한 사용자 스토리
- 모든 작업 설명에 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 인프라)

**목적**: 신규 `reflections` Django 앱과 URL namespace의 최소 골격을 준비한다.

- [X] T001 `src/reflections/__init__.py`, `src/reflections/apps.py`, `src/reflections/migrations/__init__.py`에 `reflections` Django 앱 골격을 생성한다.
- [X] T002 `src/config/settings.py`에 `reflections.apps.ReflectionsConfig`를 등록하고 `src/config/urls.py`에서 `reflections.urls`를 include한다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 사용자 스토리가 공유하는 Interview/InterviewTurn 영속 모델과 additive initial migration을 구축한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 구현을 시작할 수 없다.

- [X] T003 [P] `tests/reflections/test_models.py`에 Interview의 Reading 일대일, Book 보호, status/readiness CHECK, 저장 후 Reading/Book 변경 거부·기존 관계 보존·status 변경 허용과 InterviewTurn의 정렬·sequence UNIQUE·양수·비공백 질문·nullable answer 제약 테스트를 작성하고 실패를 확인한다.
- [X] T004 [P] `tests/reflections/test_migrations.py`에 신규 두 table만 생성하는 SQL 형태, 중복 Turn FK index 부재, PostgreSQL forward → zero → forward 및 제약 복원 테스트를 작성하고 실패를 확인한다.
- [X] T005 `src/reflections/models.py`에 `Interview`와 `InterviewTurn` 모델, choices, ordering, 저장 후 Reading/Book 변경을 거부하는 application validation 및 DB 제약을 구현한다.
- [X] T006 `src/reflections/migrations/0001_initial.py`에 books/readings leaf migration을 의존하는 신규 빈 Interview/InterviewTurn table과 FK·CHECK·UNIQUE만 포함한 additive migration을 생성한다.

**체크포인트**: 저장 계층이 준비되고 새 Interview가 Turn 0개인 상태도 유효하며, 기존 table이나 data는 변경되지 않는다.

---

## Phase 3: 사용자 스토리 1 - 완독한 책으로 인터뷰 시작 (우선순위: P1) 🎯 MVP

**목표**: 로그인한 소유자가 완독 Reading의 책을 확인하고 명시적 POST로 Reading과 Book이 확정된 진행 중 Interview를 시작하며, 이후 완독 정보는 잠긴다.

**독립 테스트**: 본인 소유 완독 Reading의 확인 GET은 Interview를 만들지 않고, 확정 POST는 Interview 한 건을 생성해 Turn 0개의 상세 화면으로 이동하며 완독 취소와 완독일 변경은 거부되는지 확인한다.

### 사용자 스토리 1 테스트

- [X] T007 [P] [US1] `tests/reflections/test_services.py`에 소유자·저장된 Reading·완독 상태/날짜, 기존 Interview와 잠근 Reading의 Book 일치 검증, IN_PROGRESS 기본 생성, Turn/Credit/Reading 무변경 및 DB 오류 rollback 테스트를 작성하고 실패를 확인한다.
- [X] T008 [P] [US1] `tests/reflections/test_views.py`에 로그인, 소유자 404, 확인 GET 무부작용, 확정 POST/CSRF/method 제한, 성공 redirect, retry 가능한 오류와 Turn 0개 상세 화면 계약 테스트를 작성하고 실패를 확인한다.
- [X] T009 [P] [US1] `tests/readings/test_services.py`와 `tests/readings/test_views.py`에 실제 Interview 존재 시 완독 취소·완독일 변경 거부와 기존 값 보존 회귀 테스트를 추가하고 실패를 확인한다.

### 사용자 스토리 1 구현

- [X] T010 [US1] `src/reflections/services.py`에 소유자 범위 Reading 잠금, 완독 재검증, Reading Book 확정 및 원자적 IN_PROGRESS Interview 생성을 수행하는 `start_interview`와 정책 오류/result 계약을 구현한다.
- [X] T011 [US1] `src/readings/services.py`의 `has_started_interview()`를 실제 Interview 존재 조회로 교체해 상태 변경과 완독일 수정 잠금 seam을 연결한다.
- [X] T012 [US1] `src/reflections/urls.py`와 `src/reflections/views.py`에 인증된 확인 GET, CSRF 보호 확정 POST, 소유자 범위 Interview detail GET과 안전한 400/404 오류 처리를 구현한다.
- [X] T013 [US1] `src/templates/reflections/interview_start.html`, `src/templates/reflections/interview_detail.html`, `src/templates/readings/_reading_panel.html`에 책 확인 form, 책 재선택 link, 명시적 시작 action, Turn 0개 시작 상태와 Reading CTA 연결을 구현한다.

**체크포인트**: 사용자 스토리 1만으로 완독 Reading → 확인 → Interview 생성 → 상세 재접근의 MVP 흐름과 Reading 잠금이 동작한다.

---

## Phase 4: 사용자 스토리 2 - 책과 시작 조건 확인 (우선순위: P1)

**목표**: 시작 전에 확보된 책 식별 정보와 변경 불가 결과, 시작·재선택 행동을 Desktop/Mobile 및 보조 기술에서 명확히 확인할 수 있게 한다.

**독립 테스트**: pytest로 선택 metadata가 있는/없는 Book의 HTML 계약을 확인하고, 실제 375px/1280px 레이아웃과 keyboard/screen reader 조작은 브라우저 자동화 없이 수동으로 확인한다.

### 사용자 스토리 2 테스트

- [X] T014 [P] [US2] `tests/reflections/test_views.py`에 Django test client로 표지·제목·저자·출판사·출간일·ISBN13 선택 렌더링, 누락값 비추측, 단일 h1, label, link/button, 변경 불가 텍스트와 `role="alert"` HTML 계약 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 2 구현

- [X] T015 [US2] `src/templates/reflections/interview_start.html`에 확보된 서지정보만 표시하는 label 기반 Book section, 변경 불가 텍스트, 실제 link/button, 오류 alert/focus와 일반 POST fallback을 구현한다.
- [X] T016 [US2] `src/static/css/app.css`에 확인·상세 화면의 visible focus, Desktop 우선 배치와 375px 무가로-scroll 반응형 스타일을 추가한다.

**체크포인트**: 확인 화면만 열어도 대상 판본과 비가역적 시작 결과를 색상에 의존하지 않고 판단하고 취소 또는 시작할 수 있다.

---

## Phase 5: 사용자 스토리 3 - 준비 수준에 맞춰 안전하게 시작 (우선순위: P1)

**목표**: `READY`와 `READY_LIMITED`를 모두 허용하고 시작 시점 readiness를 스냅샷하며 제한 상태에서만 기억 중심 안내를 제공한다.

**독립 테스트**: Claim이 있는 Book과 없는 Book의 완독 Reading에서 각각 시작해 두 경우 모두 Interview가 생성되고 정확한 readiness가 보존되며, 제한 안내는 `READY_LIMITED` 확인 화면에만 나타나는지 확인한다.

### 사용자 스토리 3 테스트

- [X] T017 [P] [US3] `tests/reflections/test_services.py`에 `get_book_knowledge_readiness()`의 READY/READY_LIMITED 결과를 시작 시 저장하고 이후 Knowledge 변화에도 Interview snapshot이 유지되는 테스트를 작성하고 실패를 확인한다.
- [X] T018 [P] [US3] `tests/reflections/test_views.py`에 READY_LIMITED에서만 기억에 남은 내용부터 정리한다는 안내가 표시되고 두 readiness 모두 시작 가능한 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 3 구현

- [X] T019 [US3] `src/reflections/services.py`에서 잠근 Reading의 Book으로 `knowledge.services.get_book_knowledge_readiness()`를 계산해 외부 I/O 없이 Interview에 저장하고 두 허용값 외 결과를 거부한다.
- [X] T020 [US3] `src/reflections/views.py`, `src/templates/reflections/interview_start.html`, `src/templates/reflections/interview_detail.html`에 readiness 표시 문맥과 READY_LIMITED 전용 기억 중심 안내를 연결한다.

**체크포인트**: Knowledge가 제한된 책도 차단되지 않으며, 화면 안내와 영속 snapshot이 동일한 시작 조건을 나타낸다.

---

## Phase 6: 사용자 스토리 4 - 진행 중 인터뷰 재진입 (우선순위: P2)

**목표**: 반복·동시 시작 요청을 Reading당 Interview 한 건으로 수렴시키고 기존 status에 맞는 목적지 계약을 반환하며 다른 사용자의 객체 존재를 숨긴다.

**독립 테스트**: 동일 Reading에 직렬·동시 요청을 보내 모든 성공 결과가 같은 Interview를 가리키고, IN_PROGRESS는 기존 상세로 재진입하며 REFLECTION_READY/COMPLETED는 후속 목적지로 판정해 상태별 409 안내를 반환하되 미구현 Reflection URL이나 가짜 화면을 만들지 않는지 확인한다.

### 사용자 스토리 4 테스트

- [X] T021 [P] [US4] `tests/reflections/test_services.py`에 반복 호출 재사용, 별도 DB connection 동시 시작 수렴, OneToOne 경쟁 `IntegrityError`의 조건부 복구, status별 destination과 잘못된 status 거부 테스트를 작성하고 실패를 확인한다.
- [X] T022 [P] [US4] `tests/reflections/test_views.py`에 기존 IN_PROGRESS 확인 GET/POST의 동일 detail redirect, 타인 Reading/Interview 동일 404, REFLECTION_READY/COMPLETED의 상태별 409 안내·무변경 및 미구현 Reflection route 미호출 테스트를 작성하고 실패를 확인한다.

### 사용자 스토리 4 구현

- [X] T023 [US4] `src/reflections/services.py`에 `get_interview_destination()`, 기존 Interview 재사용, Reading OneToOne 경쟁 후 동일 Reading Interview만 복구하는 멱등·동시성 처리를 구현한다.
- [X] T024 [US4] `src/reflections/views.py`에서 확인 GET과 확정 POST 모두 기존 Interview의 destination을 사용하고, IN_PROGRESS만 실제 detail로 redirect하며 후속 Reflection 목적지는 존재하지 않는 URL을 reverse하지 않고 내부 상태를 숨긴 상태별 409 안내로 처리한다.
- [X] T025 [US4] `tests/readings/test_views.py`에서 Interview가 없는 완독 Reading과 기존 Interview가 있는 Reading의 CTA가 동일한 `reflections:interview_start` GET 경계를 사용하고 CTA 렌더링 자체로 Interview가 생성되지 않는지 검증한다.

**체크포인트**: Reading당 전체 수명 Interview 한 건, 소유권 비노출 및 현재 단계별 재진입 계약이 보장된다.

---

## Phase 7: 마무리 및 교차 관심사

**목적**: 변경 기록과 전체 기능 검증을 완료한다.

- [X] T026 [P] `CHANGELOG.md`의 `[Unreleased]`에 Interview/Turn 기반, 확인·시작·멱등 재진입 및 Reading 잠금 기능을 기록한다.
- [X] T027 `specs/008-interview-start/quickstart.md`의 정적 검사와 `tests/reflections`, `tests/readings` 명령을 실행해 schema drift, migration SQL/왕복 및 자동 인수 계약을 검증한다.
- [X] T028 브라우저 자동화 도구나 자동화 코드를 추가하지 않고 `specs/008-interview-start/quickstart.md`의 Desktop 1280px, Mobile 375px, keyboard/screen reader, metadata 누락, READY/READY_LIMITED 시나리오를 수동 실행해 결과를 확인한다.
- [X] T029 `scripts/verify.py`를 실행해 Django check, migration drift, Ruff format/lint와 전체 기본 pytest 품질 게이트를 통과시킨다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **설정 (Phase 1)**: 의존성 없음. T001 이후 T002를 수행한다.
- **기반 (Phase 2)**: Phase 1 완료에 의존하며 모든 사용자 스토리를 차단한다. T003/T004 작성 후 T005 → T006 순서로 구현한다.
- **사용자 스토리 1 (Phase 3)**: Phase 2 완료 후 시작하며 최초 end-to-end 흐름을 제공한다.
- **사용자 스토리 2 (Phase 4)**: Phase 3의 확인 화면 경계에 의존하고 표시·접근성 계약을 완성한다.
- **사용자 스토리 3 (Phase 5)**: Phase 3의 시작 Service/화면 경계에 의존하며 US2와 독립적으로 개발할 수 있다.
- **사용자 스토리 4 (Phase 6)**: Phase 3의 시작 Service/화면 경계에 의존하며 US2/US3와 독립적으로 개발할 수 있다.
- **마무리 (Phase 7)**: 제공할 모든 사용자 스토리 완료에 의존한다.

### 사용자 스토리 의존성 그래프

```text
Setup → Foundation → US1 (MVP) ─┬→ US2
                                ├→ US3
                                └→ US4
US2 + US3 + US4 → Polish
```

### 각 사용자 스토리 내부

- 테스트를 먼저 작성하고 대상 구현 전 실패를 확인한다.
- 모델과 migration은 Service보다 먼저 완료한다.
- Service 정책은 View/Template 연결보다 먼저 완료한다.
- 같은 파일을 수정하는 작업은 Task ID 순서로 수행한다.
- 각 체크포인트에서 해당 스토리의 독립 테스트 기준을 검증한다.

### 병렬 작업 기회

- T003과 T004는 서로 다른 테스트 파일에서 병렬 작성 가능하다.
- Phase 3에서 T007, T008, T009는 서로 다른 테스트 경계를 대상으로 병렬 작성 가능하다.
- US1 완료 후 US2, US3, US4는 서로 다른 책임을 중심으로 병렬 진행할 수 있으나 공유 파일 merge는 Task ID 순서로 조정한다.
- T017/T018 및 T021/T022는 각 스토리 안에서 서로 다른 service/view 테스트 파일을 대상으로 병렬 작성 가능하다.
- T026은 기능 코드와 검증 작업이 완료되는 동안 독립적으로 작성 가능하다.

---

## 병렬 실행 예시

### 사용자 스토리 1

```text
Task T007: tests/reflections/test_services.py에 시작 Service 실패 테스트 작성
Task T008: tests/reflections/test_views.py에 Web 경계 실패 테스트 작성
Task T009: tests/readings/test_services.py와 tests/readings/test_views.py에 잠금 회귀 테스트 작성
```

### 사용자 스토리 2

```text
Task T014 완료 후 T015를 구현한다.
T016은 T015의 class/구조 계약이 확정된 뒤 수행한다.
```

### 사용자 스토리 3

```text
Task T017: tests/reflections/test_services.py에 readiness snapshot 테스트 작성
Task T018: tests/reflections/test_views.py에 조건부 안내 테스트 작성
```

### 사용자 스토리 4

```text
Task T021: tests/reflections/test_services.py에 멱등·동시성·resolver 테스트 작성
Task T022: tests/reflections/test_views.py에 재진입·소유권 테스트 작성
```

## 구현 전략

### MVP 우선

1. Phase 1 설정을 완료한다.
2. Phase 2 모델과 migration 기반을 완료한다.
3. Phase 3 사용자 스토리 1을 완료한다.
4. 중지하고 US1 독립 테스트 기준과 관련 migration/Reading 회귀를 검증한다.
5. 책 확인 → 시작 → Turn 0개 Interview 상세 → Reading 잠금 흐름을 시연한다.

### 점진적 제공

1. Setup + Foundation → 영속 기반 준비
2. US1 → 시작 MVP 제공
3. US2 → 판본 확인과 접근성/반응형 완성
4. US3 → READY_LIMITED 신뢰 흐름 완성
5. US4 → 반복·동시 요청 및 lifecycle 재진입 완성
6. Polish → 변경 기록, quickstart, 전체 품질 게이트 완료

### 범위 보호

- 첫 질문 또는 Turn 생성/답변 Service를 추가하지 않는다.
- Coverage, Soft Stop, Reflection model/template/named URL을 추가하지 않는다.
- Credit/Coupon을 조회·예약·소비·변경하거나 비용 안내를 표시하지 않는다.
- GET에서 Interview를 생성하거나 client가 user/book/readiness/status를 지정하게 하지 않는다.
- 신규 package, API, Repository layer 또는 외부 I/O를 추가하지 않는다.

## 참고 사항

- `[P]`는 선행 의존성이 끝났고 수정 파일이 충돌하지 않을 때만 병렬 실행한다.
- 각 Story label은 `spec.md`의 사용자 스토리와 직접 대응한다.
- 동시성 검증은 PostgreSQL과 별도 DB connection을 사용한다.
- Selenium, Playwright 등 실제 브라우저 자동 테스트는 추가하지 않고 UI/접근성 확인은 T028의 수동 검증으로 수행한다.
- p95 500ms 목표는 현재 성능 측정 도구가 없어 이번 완료 게이트에서 측정하지 않으며, 배포 후 tracing에서 실사용 속도 문제가 관찰될 때 별도 최적화 작업으로 다룬다.
- migration은 신규 빈 table만 다루며 기존 table 변경·backfill·drop을 포함하지 않는다.
- 각 작업 또는 논리적 그룹 후 커밋할 수 있지만, 커밋은 별도 사용자 요청이 있을 때만 수행한다.

## Phase 8: Convergence

- [X] T030 **CRITICAL** `src/reflections/views.py`와 `src/templates/reflections/interview_start.html`에서 미완독 Reading의 확인 GET이 시작 form 또는 활성 시작 action을 제공하지 않도록 하고, POST 재검증과 무생성 회귀 테스트를 `tests/reflections/test_views.py`에 추가한다. per FR-005, US1/AC1 (contradicts)
- [X] T031 [P] `tests/reflections/test_models.py`와 신규 `tests/reflections/test_migrations.py`에 Book 보호, status/readiness CHECK, Reading/Book 저장 변경 거부와 기존 관계 보존, Turn ordering·nullable answer·모든 DB 제약, 신규 두 table만 생성하는 SQL, 중복 FK index 부재 및 PostgreSQL forward → zero → forward 복원을 검증한다. per FR-002–004, SC-008 (partial)
- [X] T032 [P] `tests/reflections/test_services.py`, `tests/readings/test_services.py`, `tests/readings/test_views.py`에 미저장·비소유·미완독 Reading, 유효하지 않은 완독일, 손상된 Book 연결, 예상하지 못한 DB 오류 rollback, Turn/Credit/Reading 무변경과 실제 Interview 기반 완독 취소·완독일 변경 거부를 검증한다. per FR-005, FR-018, FR-021 (partial)
- [X] T033 `src/reflections/services.py`의 OneToOne 경쟁 복구를 동일 Reading의 실제 unique 경쟁에만 제한하고 `tests/reflections/test_services.py`에 별도 PostgreSQL connection 동시 시작 수렴, 조건부 `IntegrityError` 복구, status별 destination 및 잘못된 status 거부 테스트를 추가한다. per FR-017, SC-004 (partial)
- [X] T034 `src/reflections/views.py`의 확인 GET·확정 POST·detail GET 모두에서 기존 Interview의 Reading–Book 일치를 검증하고 손상된 연결이나 잘못된 status를 내부 정보 노출 없이 400 또는 409로 처리하는 회귀 테스트를 `tests/reflections/test_views.py`에 추가한다. per FR-011, SC-006 (partial)
- [X] T035 [P] `src/reflections/views.py`, `src/templates/reflections/interview_start.html`, `src/templates/reflections/interview_detail.html`과 `tests/reflections/test_views.py`에 READY/READY_LIMITED 표시 문맥, 확보된 metadata만의 label 렌더링, 누락값 비추측, 단일 h1, 실제 link/button, method 제한, retry 오류 focus/alert와 Turn 0개 상세 계약을 완성한다. per FR-007, FR-015, T014–T020 (partial)
- [X] T036 `specs/008-interview-start/quickstart.md`의 1280px Desktop, 375px Mobile, keyboard/screen reader, metadata 누락, READY/READY_LIMITED 시나리오를 브라우저 자동화 없이 수동 실행하고 결과를 확인한다. per FR-020, SC-007 (partial)

## Phase 9: Convergence

- [X] T037 [P] `tests/reflections/test_models.py`와 `tests/reflections/test_migrations.py`에 Book 삭제 보호, Interview status/readiness DB CHECK, Turn nullable answer와 다중 Turn 정렬을 각각 관찰 가능한 assertion으로 검증하는 회귀 테스트를 추가한다. per FR-002–004, SC-008 (partial)
- [X] T038 [P] `tests/reflections/test_services.py`에 Interview 저장 중 예상하지 못한 DB 오류가 발생할 때 Interview·Turn이 남지 않고 Reading·Book·Credit 관련 상태가 변경되지 않으며 재시도 가능한지 검증하는 원자성 회귀 테스트를 추가한다. per FR-018, FR-021–022, SC-006 (partial)
- [X] T039 `src/reflections/services.py`의 `IntegrityError` 복구를 동일 Reading의 실제 OneToOne 경쟁으로 생성된 Interview에만 제한하고, 관련 없는 무결성 오류는 재발생시키는 조건부 복구 테스트를 `tests/reflections/test_services.py`에 추가한다. per FR-017, SC-004 (partial)
- [X] T040 [P] `tests/reflections/test_views.py`에서 Reading–Book 연결이 손상된 기존 Interview에 대한 확인 GET, 확정 POST와 detail GET이 모두 새 Interview나 변경을 남기지 않고 안전한 오류를 반환하는지 검증한다. per FR-011, SC-006 (partial)
- [X] T041 [P] `tests/reflections/test_views.py`에 시작 URL의 GET/POST method 제한, READY 표시 문맥, retry 오류의 alert·focus, Turn 0개 상세 화면 계약을 검증하는 자동 Web 회귀 테스트를 추가한다. per FR-020, SC-007 (partial)

## Phase 10: Convergence

- [X] T042 **CRITICAL** `tests/test_settings.py`의 격리 프로젝트 fixture에 현재 `INSTALLED_APPS`가 요구하는 `src/knowledge`와 `src/reflections`를 포함하고 `uv run python scripts/verify.py` 전체 품질 게이트를 재통과시킨다. per Constitution V, T029 (partial)
