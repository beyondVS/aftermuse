---
description: "최소 Book Knowledge 및 준비 상태 판정 구현 작업"
---

# 작업: 최소 Book Knowledge 및 준비 상태 판정

**입력**: `/specs/007-book-knowledge-readiness/`의 설계 문서

**사전 조건**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**테스트**: 명세·헌법·계획에서 요구한 pytest, PostgreSQL migration 검증, Django check,
Ruff, `scripts/verify.py`를 포함한다.

**구성**: Claim 등록·조회, 수동 Seed, 준비 상태 판정을 각 사용자 스토리 단위로 검증한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일에서 의존성 없이 병렬 실행 가능
- **[Story]**: 작업이 속한 사용자 스토리 (`US1`, `US2`, `US3`)
- 모든 작업은 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 인프라)

**목적**: 새 Knowledge 도메인을 Django 프로젝트에 인식시킬 최소 구조를 준비한다.

- [ ] T001 `src/knowledge/__init__.py`, `src/knowledge/apps.py`, `src/knowledge/migrations/__init__.py`를 만들고 `src/config/settings.py`의 `INSTALLED_APPS`에 `knowledge.apps.KnowledgeConfig`를 등록한다.

---

## Phase 2: 기반 (모든 사용자 스토리의 차단 전제조건)

**목적**: 테스트와 management command의 Python package 경계를 준비한다.

- [ ] T002 `tests/knowledge/__init__.py`를 만들어 Knowledge 도메인 테스트 package를 준비한다.
- [ ] T003 `src/knowledge/management/__init__.py`, `src/knowledge/management/commands/__init__.py`를 만들어 전용 Seed command package를 준비한다.

**체크포인트**: Knowledge 테스트와 command 구현을 추가할 package 경계가 준비된다.

---

## Phase 3: 사용자 스토리 1 - 책별 Claim Knowledge 준비 (우선순위: P1) 🎯 MVP

**목표**: 콘텐츠 준비 담당자가 특정 Book에 Claim을 멱등 등록하고, 다른 Book과 섞이지 않은
결정적 목록으로 조회할 수 있다.

**독립 테스트**: 두 Book에 각기 다른 Claim을 등록하고 한 Book의 목록을 조회해 유형·내용,
격리, 순서와 중복 방지를 확인한다.

### 사용자 스토리 1 테스트

- [ ] T004 [P] [US1] `tests/knowledge/test_models.py`에 `BookKnowledge`의 5개 kind, Book FK, content 길이·공백 검증, 동일 Book·kind·content UNIQUE, Book 간 동일 Claim 허용을 검증하는 모델·DB 제약 테스트를 작성한다.
- [ ] T005 [P] [US1] `tests/knowledge/test_services.py`에 `create_book_knowledge()`의 trim·validation·멱등 결과·동시 중복 방지와 `list_book_knowledge()`의 Book 격리·`kind`, `id` 정렬·단일 query 계약을 검증하는 Service 테스트를 작성한다.
- [ ] T006 [P] [US1] `tests/knowledge/test_migrations.py`에 `knowledge.0001_initial`의 forward/reverse/forward 왕복, FK·kind/content CHECK·UNIQUE 복원과 `sqlmigrate` DDL이 기존 table 변경 없이 새 table만 생성함을 검증하는 migration 테스트를 작성한다.

### 사용자 스토리 1 구현

- [ ] T007 [US1] `src/knowledge/models.py`에 `KnowledgeKind`, 앞뒤 공백 제거 후 1~500자 Claim validation, Book FK, kind/non-whitespace CHECK와 `(book, kind, content)` UNIQUE를 구현하되 내부 공백과 대소문자는 보존한다.
- [ ] T008 [US1] `src/knowledge/migrations/0001_initial.py`를 생성해 `books` leaf migration에 의존하는 신규 빈 `knowledge_bookknowledge` table, FK, CHECK, UNIQUE를 추가한다.
- [ ] T009 [US1] `src/knowledge/services.py`에 `create_book_knowledge()`와 결과 객체, `list_book_knowledge()`를 구현해 정규화·검증·짧은 transaction·동시 `IntegrityError` 복구·결정적 조회를 보장한다.
- [ ] T010 [US1] `tests/knowledge/test_models.py`, `tests/knowledge/test_services.py`, `tests/knowledge/test_migrations.py`의 US1 시나리오를 실행하고 실패 원인을 구현 계약에 맞춰 수정한다.

**체크포인트**: US1이 Claim 등록과 Book별 조회를 단독으로 제공하며, DB와 Service 양쪽에서
중복·잘못된 입력을 막는다.

---

## Phase 4: 사용자 스토리 2 - 검증용 Seed Knowledge 재현 (우선순위: P1)

**목표**: 기존 Book 2권에 대한 수동 Claim Seed를 반복 적용해도 동일한 Context 입력을
재현하고, 누락·잘못된 입력은 전체 rollback한다.

**독립 테스트**: 두 대상 Book을 준비한 test database에서 Seed command를 세 번 적용하여 Claim 수와
내용이 불변인지 확인하고, 대상 Book 하나가 누락된 경우 새 Claim·Book이 생기지 않는지
검증한다.

### 사용자 스토리 2 테스트

- [ ] T011 [P] [US2] `tests/knowledge/test_seed_command.py`에 `seed_book_knowledge` command의 2권·각 3~5 Claim 적용, 세 번 반복 실행 멱등성, ISBN13 연결, Service 호출 경계, 누락 Book·invalid kind·invalid content 시 전체 rollback과 Book 자동 생성 0건을 검증하는 테스트를 작성한다.

### 사용자 스토리 2 구현

- [ ] T012 [P] [US2] `specs/007-book-knowledge-readiness/checklists/seed-knowledge.md`에 Claim별 ISBN13·kind·최종 content·공식 출처 URL·지지 여부를 기록하고 모두 승인한 뒤, 승인된 도서별 3~5개 Claim을 `src/knowledge/seed_data/book_knowledge.json`에 작성한다.
- [ ] T013 [US2] `src/knowledge/services.py`에 전체 Book·Claim 선검증과 단일 transaction 멱등 저장을 수행하는 `seed_book_knowledge()`를 구현하고 `src/knowledge/management/commands/seed_book_knowledge.py`에는 JSON 해석·Service 호출·결과 보고만 구현한 뒤 `tests/knowledge/test_seed_command.py`를 통과시킨다.

**체크포인트**: US2가 Book을 만들지 않으면서도 두 existing Book의 Context용 Claim을
일관되게 재현하고, 실패 시 부분 데이터를 남기지 않는다.

---

## Phase 5: 사용자 스토리 3 - Book 준비 상태 구분 (우선순위: P1)

**목표**: 후속 Interview가 Book별 Claim 유무에 따라 `READY` 또는 `READY_LIMITED`를
안전하게 선택할 수 있다.

**독립 테스트**: Claim이 하나 이상 있는 Book과 없는 Book을 함께 준비해 각 상태가 정확하고,
다른 Book의 Claim이 판정에 영향을 주지 않으며 상태 저장 side effect가 없음을 확인한다.

### 사용자 스토리 3 테스트

- [ ] T014 [P] [US3] `tests/knowledge/test_services.py`에 `get_book_knowledge_readiness()`의 Claim 존재/부재 `READY`·`READY_LIMITED`, Book별 독립성, 단일 존재 query, 영속 상태 변경 없음 테스트를 추가한다.

### 사용자 스토리 3 구현

- [ ] T015 [P] [US3] `src/knowledge/services.py`에 `BookKnowledgeReadiness` enum과 Claim 존재 여부만으로 값을 파생하는 `get_book_knowledge_readiness()`를 구현한다.
- [ ] T016 [US3] `tests/knowledge/test_services.py`의 US3 시나리오를 실행해 `READY_LIMITED`가 오류·차단 상태를 만들지 않는지 검증한다.

**체크포인트**: US3은 별도 status table·column 없이 Book 단위의 안전한 후속 Interview
정책 신호를 제공한다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: 실제 schema, quickstart와 전체 품질 게이트가 계획·명세와 일치하는지 확인한다.

- [ ] T017 `specs/007-book-knowledge-readiness/quickstart.md`의 명령대로 `uv run python src/manage.py check`, `uv run python src/manage.py makemigrations --check --dry-run`, `uv run python src/manage.py sqlmigrate knowledge 0001`, Seed command 반복 실행·상태 확인을 실행하고 실제 결과와 어긋나는 검증 안내만 수술적으로 갱신한다.
- [ ] T018 `scripts/verify.py`와 관련 `tests/knowledge/`를 실행해 Django check, Ruff format/lint, PostgreSQL pytest를 통과시키고 실패를 수정한다.
- [ ] T019 T017과 T018이 통과한 뒤 `CHANGELOG.md`의 `[Unreleased]`에 Bundle 05A를 기록하고 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-040~IMP-042를 완료 처리한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1**: 의존성 없음.
- **Phase 2**: Phase 1 이후 실행하며 테스트와 Seed command package 전제조건이다.
- **US1 (Phase 3)**: Phase 2 이후 실행한다. Claim schema와 Service가 US2·US3의 공통 기반이다.
- **US2 (Phase 4)**: US1의 BookKnowledge model·Service·migration 이후 실행한다.
- **US3 (Phase 5)**: US1의 Claim schema 이후 실행한다. `services.py` 충돌을 피하기 위해 US1의 Service 작업 완료 후 실행한다.
- **Phase 6**: US1·US2·US3 모두 완료한 뒤 실행한다.

### 사용자 스토리 의존성

- **US1 (P1)**: Phase 2 이후 독립적으로 완료·검증 가능하며 MVP 기준선이다.
- **US2 (P1)**: US1의 Claim schema를 사용하지만 UI·Interview 없이 Seed 재현 계약만 독립 검증한다.
- **US3 (P1)**: US1의 Claim schema를 사용하지만 Seed 없이 Claim 유무만으로 독립 검증한다.

### 병렬 작업 기회

- T004, T005, T006은 서로 다른 테스트 파일이므로 T003 이후 병렬로 작성할 수 있다.
- US1 구현 완료 후 T011(US2 Seed command test)과 T014(US3 readiness test)는 서로 다른 파일에서
  병렬로 작성할 수 있다.
- T012(Seed 검수·데이터)와 T015(readiness Service)는 서로 다른 파일이지만 각각 T011·T014의
  기대 동작이 확정된 뒤 병렬로 구현할 수 있다.

---

## 병렬 예시: Claim schema 완료 후

```text
Task: "tests/knowledge/test_seed_command.py에 Seed 반복 적용·전체 rollback 테스트 작성"
Task: "tests/knowledge/test_services.py에 READY/READY_LIMITED 판정 테스트 추가"
```

두 작업은 각각 Seed command와 readiness 계약을 검증하며 서로 다른 파일을 편집한다.

## 구현 전략

### MVP 우선 (US1만)

1. Phase 1과 Phase 2로 `knowledge` 앱과 테스트·command package를 준비한다.
2. Phase 3에서 Claim schema·migration·등록·조회 Service와 PostgreSQL 테스트를 완료한다.
3. US1 테스트를 단독 실행해 Claim 등록, 격리, 중복 방지가 성립하는지 검증한다.
4. 이 시점에는 Seed·Interview 상태 UI를 추가하지 않는다.

### 점진적 제공

1. US1 완료: 수동 Claim을 안전하게 저장·조회할 수 있다.
2. US2 완료: 검증용 2권의 Context 입력을 반복 재현할 수 있다.
3. US3 완료: 후속 Interview가 Book별 `READY`/`READY_LIMITED` 정책을 선택할 수 있다.
4. Phase 6 완료: schema SQL, quickstart, 전체 품질 게이트를 확인한다.

### 범위 보호

이 작업 목록은 Source/Evidence/Conflict, 자동 Research, Candidate 승인, Backoffice,
ReadingPreparation, Interview/Turn, 질문 생성, UI/URL/Template, Credit과 사용자 기록의
공용 Knowledge 승격을 구현하지 않는다.
