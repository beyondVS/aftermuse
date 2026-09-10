---
description: "Interview Coverage 상태 구현 작업 목록"
---

# 작업: Interview Coverage 상태

**입력**: `/specs/010-interview-coverage-state/`의 설계 문서

**사전 조건**: plan.md, spec.md, research.md, data-model.md, contracts/service-contract.md

**테스트**: 명세의 원자성·동시성·소유권 인수 조건과 프로젝트 헌법에 따라 테스트를 구현보다
먼저 작성하고 실패를 확인한다. 실제 외부 Provider나 브라우저는 사용하지 않는다.

**구성**: 공통 JSONB/migration 기반을 먼저 완성하고, 각 사용자 스토리를 독립적으로 검증 가능한
증가분으로 구현한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일을 수정하고 미완료 작업에 의존하지 않아 병렬 실행 가능
- **[Story]**: 명세의 사용자 스토리 (`US1`, `US2`, `US3`)
- 모든 작업 설명은 정확한 파일 경로를 포함한다.

## Phase 1: 설정 및 현재 상태 확인

**목적**: 기존 reflections migration과 검증 경계를 확정한다.

- [X] T001 `src/reflections/migrations/0001_initial.py`와 `tests/reflections/test_migrations.py`에서 현재 migration leaf, 기존 Interview 데이터 보존 방식과 PostgreSQL 전용 migration test 패턴을 확인하고 신규 `0002`/`0003` dependency를 확정한다.

---

## Phase 2: 기반 — canonical Coverage와 안전한 Migration

**목적**: 모든 사용자 스토리가 공유하는 Coverage 값, DB column, CHECK와 migration 호환성을
완성한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 Coverage Service 사용자 스토리를 구현하지 않는다.

### 기반 테스트

- [X] T002 [P] `tests/reflections/test_models.py`에 네 축 callable 기본값의 독립성, canonical JSON shape와 허용 상태 검증 테스트를 작성하고 구현 전 실패를 확인한다.
- [X] T003 [P] `tests/reflections/test_migrations.py`에 기존 Interview backfill, ORM/DB default insert, canonical CHECK 거부, forward/reverse 데이터 보존을 검증하는 `0001`→`0003` migration 테스트를 작성하고 구현 전 실패를 확인한다.

### 기반 구현

- [X] T004 `src/reflections/models.py`에 Core Coverage 축·상태, 매 호출마다 새 canonical dict를 반환하는 기본값, non-null `Interview.coverage` JSONField와 application shape 검증을 구현한다.
- [X] T005 `src/reflections/migrations/0002_interview_coverage.py`에 canonical `db_default`를 가진 non-null JSONB column을 추가하고 transaction-local `lock_timeout`으로 column DDL 대기를 제한하는 가역 migration을 구현한다.
- [X] T006 `src/reflections/migrations/0003_interview_coverage_constraint.py`에 canonical object CHECK를 `NOT VALID`로 추가한 뒤 별도 transaction에서 `VALIDATE CONSTRAINT`하고 Django migration state를 일치시키는 가역 migration을 구현한다.

**체크포인트**: 모든 기존·신규 Interview가 canonical Coverage를 가지며 invalid JSON은 model과
DB 경계에서 거부되고 rolling deploy 중 구버전 insert도 유효해야 한다.

---

## Phase 3: 사용자 스토리 1 — 답변으로 생각의 Coverage를 축적하기 (우선순위: P1) 🎯 MVP

**목표**: 답변이 확정된 진행 중 Interview에서 지정한 Core 축만 상승시키고 네 축의 최신
Coverage snapshot을 다시 조회한다.

**독립 테스트**: 초기, 일부 `PARTIAL`, 일부 `COVERED` 상태의 Interview에 단일·다중 축 patch를
적용해 지정된 축만 바뀌고 재조회 결과가 저장 값과 일치하며 관련 domain 상태가 불변인지 확인한다.

### 사용자 스토리 1 테스트

- [X] T007 [US1] `tests/reflections/test_services.py`에 Coverage 조회, 최초 단일 축 상승, 다중 축 상승, 지정하지 않은 축 보존, Interview·Turn·답변 side-effect 금지와 조회당 단일 Interview query·변경당 단일 update 계약 테스트를 작성하고 구현 전 실패를 확인한다.

### 사용자 스토리 1 구현

- [X] T008 [US1] `src/reflections/services.py`에 read-only Coverage snapshot/result 값과 `get_interview_coverage`를 구현하고, 사용자 소유·Reading/Book 연결·canonical 저장 shape를 공통 검증한다. 조회는 소유자에게 진행 상태와 관계없이 허용하고, 단일·다중 축 patch는 `IN_PROGRESS`와 답변 존재까지 추가 검증한 뒤 원자적으로 적용해 T007을 통과시킨다.

**체크포인트**: 사용자 스토리 1만으로 답변 이후 Coverage를 저장·재조회할 수 있고 Answer
Analysis나 다음 질문 없이 독립 검증 가능해야 한다.

---

## Phase 4: 사용자 스토리 2 — 유효한 Coverage 전환만 허용하기 (우선순위: P1)

**목표**: Coverage가 단방향으로만 이동하고 반복·동시 요청과 mixed-validity patch가 기존
상태를 유실하거나 부분 반영하지 않게 한다.

**독립 테스트**: 동일 상태 반복, 직접 상승, 상태 하락, 알 수 없는 축·상태, 중복 축, 빈 patch,
DB 실패와 실제 PostgreSQL 경쟁 요청을 각각 재현해 최종 snapshot과 rollback 결과를 확인한다.

### 사용자 스토리 2 테스트

- [X] T009 [US2] `tests/reflections/test_services.py`에 동일 상태 no-op, 빈 patch, 직접 상승, 하락·알 수 없는 값·중복 축·mixed-validity patch 전체 거부와 DB 오류 rollback 테스트를 작성하고 구현 전 실패를 확인한다.
- [X] T010 [US2] `tests/reflections/test_services.py`에 thread별 DB connection과 barrier를 사용해 서로 다른 축, 같은 축 동일 상태, `PARTIAL`/`COVERED` 경쟁이 최고 상태로 수렴하는 PostgreSQL 동시성 테스트를 작성하고 구현 전 실패를 확인한다.

### 사용자 스토리 2 구현

- [X] T011 [US2] `src/reflections/services.py`에 순서 있는 patch 항목 전체 검증, 중복 검출, 상태 순서 비교, Interview row lock, 최신 상태 재검증, changed/no-op 결과와 원자적 오류 변환을 구현해 T009와 T010을 통과시킨다.

**체크포인트**: 모든 유효한 경쟁은 축별 최고 상태로 수렴하고 invalid 또는 실패 patch는 어떤
축도 부분 저장하지 않아야 한다.

---

## Phase 5: 사용자 스토리 3 — Interview 경계 안에서 Coverage를 격리하기 (우선순위: P2)

**목표**: Coverage 조회를 사용자 소유의 유효한 Interview에 한정하고 변경은 진행 중 Interview에만
허용하여 다른 사용자와 다른 Interview의 상태를 격리한다.

**독립 테스트**: 여러 사용자·Reading·Interview에 서로 다른 Coverage를 두고 권한 없는 조회·변경,
완료 단계의 소유자 조회, 비진행 변경, 답변 없음과 Book 연결 손상을 재현해 대상 정보 비노출과
전체 상태 불변을 확인한다.

### 사용자 스토리 3 테스트

- [X] T012 [US3] `tests/reflections/test_services.py`에 Interview별 격리, 다른 사용자와 미저장 대상의 동일 오류, 답변 없음과 Reading·Book 불일치 시 변경 거부 테스트를 작성하고 T008의 소유권·상태 경계가 이를 충족하는지 확인한다.

### 사용자 스토리 3 상태별 계약 테스트

- [X] T013 [US3] `tests/reflections/test_services.py`에 소유자의 `REFLECTION_READY`·`COMPLETED` Coverage 조회 허용, 비진행 Interview 변경 거부와 다른 사용자 대상 정보 비노출 회귀 테스트를 추가해 T008의 조회·변경 경계가 상태별 계약을 충족하는지 확인한다.

**체크포인트**: 다른 사용자와 invalid Interview는 대상 존재 여부나 Coverage를 확인할 수 없고,
어떤 거부 경로도 기존 상태를 변경하지 않아야 한다.

---

## Phase 6: 마무리 및 교차 검증

**목적**: migration SQL, 전체 회귀와 구현 계획 상태를 증거에 맞춰 동기화한다.

- [X] T014 `specs/010-interview-coverage-state/quickstart.md`의 `makemigrations --check --dry-run`, `sqlmigrate` 0002/0003, migration/model/service 테스트를 실행하고 `lock_timeout`, `db_default`, `NOT VALID`/`VALIDATE`, reverse SQL과 migration state가 설계 계약과 일치하는지 확인한다.
- [X] T015 `uv run python scripts/verify.py`로 Django system check, Ruff format/lint, 전체 pytest와 migration drift를 검증하고 Bundle 06A 첫 질문·답변 회귀가 유지되는지 확인한다.
- [X] T016 T014와 T015가 성공한 뒤 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-070 완료 상태·검증 근거와 `CHANGELOG.md`의 Unreleased 변경 내역을 실제 구현 결과에 맞춰 수술적으로 갱신한다.

---

## 의존성 및 실행 순서

### 단계 의존성

```text
Phase 1 현재 상태 확인
  ↓
Phase 2 canonical 모델·migration 기반
  ↓
Phase 3 US1 Coverage 축적
  ├─→ Phase 4 US2 전환 무결성
  └─→ Phase 5 US3 소유권 격리
          ↓
Phase 6 migration·전체 회귀·문서 동기화
```

- **Phase 1**: 의존성 없이 시작한다.
- **Phase 2**: T001 이후 시작한다. T002와 T003은 병렬 작성 가능하며 T004~T006은 두 테스트가
  실패함을 확인한 뒤 순서대로 진행한다.
- **US1 (Phase 3)**: Phase 2 완료 후 시작하며 다른 사용자 스토리에 의존하지 않는다.
- **US2 (Phase 4)**: US1의 기본 patch Service에 의존한다.
- **US3 (Phase 5)**: US1에서 완성한 안전한 조회·patch Service에 의존한다. US2와 제품 계약상 독립이지만
  같은 `src/reflections/services.py`와 `tests/reflections/test_services.py`를 수정하므로 기본 실행은
  순차 진행한다.
- **Phase 6**: US1~US3 완료 후 진행한다. T016은 T014와 T015의 실제 성공 증거에 의존한다.

### 사용자 스토리별 독립 완료 기준

- **US1**: 네 축의 canonical snapshot을 조회하고 답변 이후 지정한 축만 상승·보존한다.
- **US2**: 반복·invalid·실패·동시 patch가 단방향·원자성·최고 상태 수렴 계약을 지킨다.
- **US3**: 소유권·Interview 상태·답변·Book 연결 경계를 벗어난 접근이 정보와 상태를 노출하지 않는다.

### 병렬 작업 기회

- T002 model 테스트와 T003 migration 테스트는 서로 다른 파일이므로 병렬 가능하다.
- 구현 파일 충돌을 피하기 위해 US2와 US3는 기본적으로 순차 실행한다.
- T016 문서 편집은 코드 변경이 끝난 뒤 수행하며, T014/T015 검증과 동시에 시작하지 않는다.

## 병렬 예시: 기반 단계

```text
Task: "tests/reflections/test_models.py에 canonical Coverage 모델 테스트 작성"
Task: "tests/reflections/test_migrations.py에 backfill·DB default·CHECK·reverse migration 테스트 작성"
```

## 구현 전략

### MVP 우선

1. Phase 1과 Phase 2를 완료해 모든 Interview가 canonical Coverage를 가지게 한다.
2. Phase 3의 US1을 완료해 소유권·상태 경계를 포함한 Coverage 저장·재조회를 독립 검증한다.
3. Phase 4의 US2를 완료해 단방향·원자성·동시성 계약까지 갖춘 최소 MVP를 확인한다.
4. Phase 5의 US3 격리·완료 상태 조회 회귀를 추가해 Bundle 전체 보안 경계를 검증한다.
5. 전체 품질 게이트와 문서 동기화로 IMP-070을 완료한다.

### 범위 통제

- Bundle 07B의 Answer Analysis 또는 LLM Provider 계약을 추가하지 않는다.
- Bundle 07C의 다음 질문 생성·Turn 통합을 추가하지 않는다.
- Bundle 08A의 질문 Budget, Soft Stop과 Low-information 정책을 추가하지 않는다.
- Focus Coverage, 수치 score, Coverage history, 사용자 편집 UI와 JSON 검색 index를 추가하지 않는다.
- 실제 브라우저, 외부 network 또는 credential 기반 검증을 실행하지 않는다.

## 참고 사항

- 모든 migration SQL은 operation 이름이 아니라 `sqlmigrate` 실제 출력으로 안전성을 판정한다.
- `ACCESS EXCLUSIVE` DDL의 `lock_timeout` 값은 migration 작성 시 프로젝트 배포 정책과 확인한다.
- test double은 DB 자체가 아닌 영속 실패 같은 현재 테스트 대상 밖의 경계에만 사용한다.
- 각 사용자 스토리는 해당 체크포인트에서 독립 검증한 뒤 다음 단계로 진행한다.

## Phase 7: Convergence

- [X] T017 `tests/reflections/test_services.py`에 동일 상태 재적용과 빈 patch가 같은 snapshot, `changed=False`, Coverage 무-write로 끝나는 회귀 테스트를 추가한다 per FR-007 및 예외 상황 (partial)
- [X] T018 `tests/reflections/test_services.py`에 알 수 없는 상태, 유효·무효 축이 섞인 patch와 Coverage update 실패가 전체 rollback되고 기존 snapshot을 보존하는 테스트를 추가한다 per FR-008, FR-009, SC-003 (partial)
- [X] T019 `tests/reflections/test_services.py`에 thread별 DB connection과 barrier로 같은 축의 동일 상태 경쟁 및 `PARTIAL`/`COVERED` 경쟁이 상위 상태를 보존하는 테스트를 추가한다 per FR-010, SC-004 (partial)
- [X] T020 `tests/reflections/test_services.py`에 서로 다른 Interview 격리, 미저장 대상과 다른 사용자 대상의 동일 오류, Reading·Book 연결 손상, `REFLECTION_READY` 조회 허용·변경 거부를 검증한다 per FR-011, FR-012, FR-013, SC-005 (partial)
- [X] T021 `src/reflections/services.py`의 Coverage patch 입력을 중복 순서를 보존하는 일반 `Sequence[CoveragePatchItem]` 계약으로 확장하고 tuple과 list 입력 및 문자열·mapping 오용 거부 테스트를 추가한다 per plan: ordered sequence input (contradicts)
- [X] T022 `tests/reflections/test_services.py`에 Coverage 조회가 단일 Interview query이고 실제 변경이 잠금 조회 뒤 단일 Interview update만 수행하며 no-op은 update하지 않는 query 계수 테스트를 추가한다 per plan: 성능 목표 및 T007 (partial)
- [X] T023 `tests/reflections/test_migrations.py`에 ORM default 생성과 DB CHECK의 비-object·누락 키·추가 키·허용되지 않은 상태 거부를 각각 검증하는 migration 회귀 테스트를 추가한다 per plan: migration strategy 및 T003 (partial)

## Phase 8: Convergence

- [X] T024 `tests/reflections/test_services.py`에 답변이 확정된 Interview의 Coverage patch를 다른 사용자가 요청할 때 미저장 대상과 동일한 `CoveragePolicyError`로 거부되고 Coverage 및 관련 domain 상태가 불변임을 검증한다 per US3/AC2, FR-012, SC-005 (partial)
