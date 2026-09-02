---
description: "Book 기본 모델 구현 작업 목록"
---

# 작업: Book 기본 모델

**입력**: `/specs/001-book-model/`의 설계 문서

**사전 조건**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**테스트**: 기능 사양의 완료 조건과 헌법이 실제 PostgreSQL 기반 저장·조회·ISBN 중복
방지 테스트를 요구하므로, 각 사용자 스토리의 테스트 작업을 구현보다 먼저 수행한다.

**구성**: 공통 Book 엔터티는 가장 이른 P1 스토리인 US1에 구현한다. US2와 US3는
동일 엔터티의 유일성 및 선택 Metadata 계약을 각각 독립 검증하는 증가분이다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일을 수정하며 선행 작업에 의존하지 않아 병렬 실행 가능
- **[Story]**: 사용자 스토리 작업에만 붙이는 추적 라벨
- 모든 작업은 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 인프라)

**목적**: 기존 프로젝트 구조에 `books` 도메인 앱을 안전하게 추가할 준비를 한다.

- [ ] T001 [P] `src/books/__init__.py`와 `src/books/migrations/__init__.py`에 Book 앱 및 migration 패키지 골격을 생성한다.
- [ ] T002 [P] `tests/test_settings.py`의 두 임시 프로젝트 fixture가 `src/books`도 복사하도록 갱신해 앱 등록 뒤의 관리 명령 회귀를 방지한다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 Book 사용자 스토리가 사용할 Django 앱 등록과 실제 PostgreSQL 테스트 기반을 준비한다.

**⚠️ 중요**: 이 단계가 끝나기 전에는 Book 모델 테스트를 성공시킬 수 없다.

- [ ] T003 [P] `src/books/apps.py`에 기본 `BigAutoField`와 `books` 앱 이름을 갖는 `BooksConfig`를 추가한다.
- [ ] T004 [P] `src/config/settings.py`의 `INSTALLED_APPS`에 `books.apps.BooksConfig`를 등록한다.
- [ ] T005 `tests/test_settings.py`의 격리된 `manage.py check` 테스트를 실행해 새 앱 복사 fixture가 정상 동작함을 확인한다.

**체크포인트**: `books` 앱을 포함한 실제 설정과 임시 프로젝트 설정이 모두 로드된다.

---

## Phase 3: 사용자 스토리 1 - 도서 서지정보 저장 및 조회 (우선순위: P1) 🎯 MVP

**목표**: 유효한 ISBN13과 제목을 가진 Book을 저장하고, 전체 서지정보 또는 정확한 ISBN13으로 조회할 수 있게 한다.

**독립 테스트**: 모든 지원 필드를 채운 Book 한 건과 서로 다른 ISBN13의 Book 여러 건을 저장한 뒤, 필드 왕복·정확 조회·미존재 결과·필수값 검증을 확인한다.

### 사용자 스토리 1 테스트

- [ ] T006 [US1] `tests/books/test_models.py`에 전체 Metadata 저장·조회, ISBN13 exact lookup, 미존재 결과, ASCII ISBN13 형식 및 빈 제목의 `full_clean()` 거부 테스트를 먼저 작성하고 RED를 확인한다.

### 사용자 스토리 1 구현

- [ ] T007 [US1] `src/books/models.py`에 ISBN13 ASCII 13자리 validator, 필수 제목, 7개 서지정보 필드와 제목 기반 문자열 표현을 갖는 `Book` 모델을 구현한다.
- [ ] T008 [US1] `src/books/migrations/0001_initial.py`를 `makemigrations books`로 생성해 Book 테이블, 기본 PK, 필드 nullability와 ISBN13 unique constraint를 기록한다.
- [ ] T009 [US1] `tests/books/test_models.py`의 US1 테스트와 `src/manage.py check`를 실행해 저장·조회·모델 검증이 GREEN인지 확인한다.

**체크포인트**: 완전한 서지정보의 Book을 저장·정확 조회할 수 있고, 잘못된 ISBN13 또는 빈 제목은 모델 검증에서 거부된다.

---

## Phase 4: 사용자 스토리 2 - 동일 ISBN 중복 방지 (우선순위: P1)

**목표**: 같은 ISBN13의 순차·동시 저장 시도에도 PostgreSQL이 최종 Book 한 건만 유지하게 한다.

**독립 테스트**: 최초 Book을 저장한 뒤 같은 ISBN13 저장을 다시 시도하고, PostgreSQL 동시 저장 경쟁을 재현하여 하나의 성공·하나의 무결성 오류·최종 한 건을 확인한다.

### 사용자 스토리 2 테스트

- [ ] T010 [US2] `tests/books/test_models.py`에 순차 중복 저장의 `IntegrityError`, 기존 Metadata 불변성, 트랜잭션 격리된 동시 저장 경쟁의 성공 1건·최종 행 1건 테스트를 작성한다.

### 사용자 스토리 2 구현 및 검증

- [ ] T011 [US2] `src/books/models.py`와 `src/books/migrations/0001_initial.py`의 ISBN13 database-level unique constraint가 US2 테스트의 유일성 계약을 충족하는지 확인하고, 필요한 최소 수정만 적용한다.
- [ ] T012 [US2] `tests/books/test_models.py`의 US1·US2 테스트를 실제 PostgreSQL test database에서 실행해 중복 Book 생성이 없음을 확인한다.

**체크포인트**: 중복 요청은 기존 Book을 갱신하지 못하고, 경쟁 요청 후에도 ISBN13당 Book은 정확히 한 건이다.

---

## Phase 5: 사용자 스토리 3 - 불완전한 선택 서지정보 보존 (우선순위: P2)

**목표**: ISBN13과 제목만 있는 Book도 저장하고, 누락된 선택 Metadata를 추측 없이 일관된 값으로 조회한다.

**독립 테스트**: ISBN13과 제목만 가진 Book, 목차가 없는 Book, 서로 다른 ISBN13 100건을 저장·조회하여 빈 문자열/미상 날짜와 식별자별 분리를 확인한다.

### 사용자 스토리 3 테스트

- [ ] T013 [US3] `tests/books/test_models.py`에 선택 문자열의 빈 문자열, 미상 출간일의 `None`, 누락 목차의 비추론, 서로 다른 ISBN13 100건의 정확 조회 및 단건 조회 시간 표본 테스트를 작성한다.

### 사용자 스토리 3 구현 및 검증

- [ ] T014 [US3] `src/books/models.py`의 선택 필드 기본값, `blank`/`null` 설정과 표지 URL 검증이 US3 테스트 계약을 충족하는지 확인하고 필요한 최소 수정만 적용한다.
- [ ] T015 [US3] `tests/books/test_models.py` 전체를 실행해 누락 Metadata 보존과 100건 조회 계약이 통과하는지 확인한다.

**체크포인트**: 누락된 선택 Metadata 때문에 저장이 실패하지 않으며, 시스템은 누락 값을 임의로 생성하지 않는다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: 실제 migration SQL, rollback 경계, 전체 품질 게이트와 구현 문서를 완료한다.

- [ ] T016 `src/books/migrations/0001_initial.py`의 forward·backward SQL을 `sqlmigrate books 0001`과 `sqlmigrate books 0001 --backwards`로 검토해 신규 테이블·ISBN13 유일성·새 테이블용 보조 index·reverse의 테이블 삭제를 확인한다.
- [ ] T017 `src/books/migrations/0001_initial.py`을 데이터가 없는 격리 개발 또는 test database에서 forward → `books zero` reverse → forward로 왕복 적용하고, reverse가 운영 rollback 절차가 아님을 확인한다.
- [ ] T018 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-020 완료 상태와 `CHANGELOG.md`의 `[Unreleased]`를 구현·검증 결과에 맞게 갱신한다.
- [ ] T019 `scripts/verify.py`를 실행하고 Django check, Ruff format, Ruff lint, 전체 pytest가 모두 통과하는지 확인한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1**: 즉시 시작 가능하다.
- **Phase 2**: T001 및 T002 이후 시작한다. 완료 전에는 Book 모델 테스트를 실행하지 않는다.
- **US1 (Phase 3)**: Phase 2 이후 시작하며 공통 Book 엔터티와 initial migration을 제공한다.
- **US2 (Phase 4)**: US1의 Book 모델과 initial migration 이후 시작한다.
- **US3 (Phase 5)**: US1의 Book 모델과 initial migration 이후 시작한다. US2와는 병렬 가능하지만 같은 `tests/books/test_models.py`를 수정하므로 한 작업 트리에서는 순차 실행한다.
- **Phase 6**: US1·US2·US3 완료 후 수행한다.

### 사용자 스토리 완료 순서

```text
설정 → 기반 → US1 (저장·조회) → US2 (중복 방지) → US3 (선택 Metadata) → 마무리
```

US2와 US3은 구현된 Book 모델에 의존하지만, 각각 고유한 데이터 무결성 및 누락값 인수
기준을 독립적으로 검증한다.

### 병렬 작업 기회

- T001과 T002는 서로 다른 파일을 수정하므로 병렬 실행할 수 있다.
- T003과 T004는 서로 다른 파일을 수정할 수 있지만, T005의 설정 검증은 둘 다 완료된 뒤
  실행한다.
- US2와 US3의 실행 자체는 US1 이후 병렬화할 수 있으나 둘 다 `tests/books/test_models.py`를
  수정하므로 동일 작업 트리에서는 병렬화하지 않는다.

## 병렬 예시

```text
Task: "src/books/__init__.py와 src/books/migrations/__init__.py에 패키지 골격 생성"
Task: "tests/test_settings.py의 임시 프로젝트 fixture에 src/books 복사 추가"
```

## 구현 전략

### MVP 우선

1. Phase 1과 Phase 2로 앱 등록 및 설정 회귀 보호를 완료한다.
2. US1에서 Book 모델·migration·저장/조회 검증을 완료한다.
3. US1 테스트가 통과하면 최소 Book 저장 기반을 시연할 수 있다.
4. US2의 database-level unique 검증과 US3의 누락 Metadata 검증을 순서대로 추가한다.
5. 마지막으로 생성 SQL, migration 왕복, 문서, 전체 품질 게이트를 확인한다.

### 증분 제공

- **MVP**: US1 — ISBN13 중심 Book 저장과 정확 조회
- **데이터 일관성 강화**: US2 — 순차·동시 중복 방지
- **외부 Metadata 내성 강화**: US3 — 누락 선택값 보존

## 참고 사항

- `objects.create()`는 모델 validator를 자동 실행하지 않으므로 형식·필수값 테스트는
  `full_clean()` 경로를 명시적으로 검증한다.
- ISBN13 unique constraint는 application-level 사전 검사만으로 대체하지 않는다.
- initial migration은 새 빈 테이블만 만들므로 concurrent index, `NOT VALID`/`VALIDATE`,
  `lock_timeout` 또는 migration 분할이 필요하지 않다.
- `books zero`는 Book 데이터를 삭제하므로 격리된 빈 database에서만 실행한다.
- Provider 연동, 검색 UI, Book 저장 Service, Work/Edition 분리는 이 작업 목록에 포함하지
  않는다.
