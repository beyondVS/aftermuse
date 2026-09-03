---
description: "도서 검색 Service와 결과 정규화 작업"
---

# 작업: 도서 검색 Service와 결과 정규화

**입력**: `/specs/003-book-search-service/`의 설계 문서

**사전 조건**: plan.md, spec.md, research.md, data-model.md,
contracts/service-contract.md, quickstart.md

**테스트**: FR-016, SC-001~SC-008 및 헌법의 증거 기반 품질 요구로 테스트 작업을
포함한다. 테스트는 각 구현 작업과 함께 작성·실행하는 완료 증거이며 test-first 또는
RED 확인을 강제하지 않는다.

**구성**: 결과 상태와 Service 공개 계약은 모든 사용자 스토리가 공유한다. 정상 검색을
MVP로 제공하고, 이후 빈 결과·Provider 실패·공백 검색어 처리를 순차적으로 확장한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일이고 미완료 작업에 의존하지 않아 병렬 수행 가능
- **[Story]**: 사용자 스토리 작업에만 붙이는 추적 레이블
- 모든 설명은 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 테스트 기반)

**목적**: 실제 외부 호출 없이 모든 검색 상태를 재현할 공통 fake Provider와 도서 fixture를
준비한다.

- [X] T001 [P] `tests/books/test_services.py`에 호출 기록, 준비된 결과·예외 주입이 가능한 fake Provider와 전체 출간일을 포함한 `ProviderBook` fixture를 추가한다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 검색 결과가 공유할 상태 enum, 불변 결과 객체와 Provider 중립 Service 공개
계약을 준비한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 검색 흐름을 시작할 수 없다.

- [X] T002 `src/books/services.py`에 `BookSearchStatus`, 불변 `BookSearchResult`, `search_books()` 공개 진입점과 Provider 계약 import를 `contracts/service-contract.md`대로 정의한다.

**체크포인트**: 검색 결과의 세 상태와 `ProviderBook` 보존 계약이 후속 구현에서 사용할 수
있게 준비된다.

---

## Phase 3: 사용자 스토리 1 - 정규화된 도서 검색 결과 제공 (우선순위: P1) 🎯 MVP

**목표**: 유효한 검색어를 한 번 전달하고, Provider가 반환한 순서와 전체 Metadata를 보존한
성공 결과를 제공한다.

**독립 테스트**: 공백이 있는 검색어와 여러 `ProviderBook`을 fake Provider에 준비해 trim,
호출 1회, `SUCCESS`, 순서·ISBN13·표지·저자·출판사·전체 출간일 보존을 확인한다.

- [X] T003 [US1] `src/books/services.py`에 양끝 공백만 제거하고 유효한 query를 Provider에 정확히 한 번 전달해 비어 있지 않은 결과를 `SUCCESS`와 원래 tuple로 반환하는 경로를 구현한다. (FR-001, FR-002, FR-004, FR-005, FR-009~FR-011)
- [X] T004 [US1] `tests/books/test_services.py`에 정상 검색의 trim, 내부 공백 보존, 호출 1회, `SUCCESS`, 도서 순서 및 전체 출간일을 포함한 Metadata 보존 테스트를 추가·실행한다. (SC-001, SC-002)

**체크포인트**: 정상 검색 결과가 Provider 세부 형식 없이 후속 검색 흐름에 전달되며 독립
검증 가능하다.

---

## Phase 4: 사용자 스토리 2 - 빈 결과와 검색 실패 구분 (우선순위: P1)

**목표**: 정상 무결과와 Provider 실패를 서로 다른 상태로 반환하고 외부 오류 상세를
격리한다.

**독립 테스트**: fake Provider가 빈 tuple 또는 각 `ProviderError` 하위 예외를 반환·발생시킬
때 각각 `EMPTY`와 빈 `books`의 `ERROR`로 구분되는지 확인한다.

- [X] T005 [US2] `src/books/services.py`에 정상 빈 Provider 결과를 `EMPTY`로, `ProviderError` 하위 예외를 빈 `books`의 `ERROR`로 변환하는 경로를 추가하고 오류 객체·메시지를 결과에 포함하지 않게 한다. (FR-006~FR-008, FR-012, FR-013)
- [X] T006 [US2] `tests/books/test_services.py`에 정상 빈 결과와 configuration, timeout, unavailable, response 오류를 각각 재현하여 상태·빈 tuple·오류 상세 비노출 계약을 검증한다. (SC-003, SC-004, SC-006, SC-007)

**체크포인트**: 빈 결과와 외부 Provider 실패가 혼동되지 않으며, 화면은 Provider별 오류에
결합하지 않는다.

---

## Phase 5: 사용자 스토리 3 - 의미 없는 검색 방지 (우선순위: P2)

**목표**: 빈 문자열 또는 공백 검색어가 외부 검색을 시작하지 않도록 한다.

**독립 테스트**: 빈 문자열과 공백 문자열을 각각 전달해 fake Provider 호출 0회,
`EMPTY`, 빈 `books`가 반환되는지 확인한다.

- [X] T007 [US3] `src/books/services.py`에 정규화 후 빈 query를 Provider 호출 없이 `EMPTY`와 빈 tuple로 반환하는 short-circuit 경로를 추가한다. (FR-003, FR-008)
- [X] T008 [US3] `tests/books/test_services.py`에 빈 문자열과 공백 검색어의 호출 0회 및 `EMPTY` 결과 테스트를 추가·실행한다. (SC-005, SC-006)

**체크포인트**: 의미 없는 검색어가 외부 호출, cache 또는 오류 상태를 만들지 않는다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: 안전한 오류 경계, 비영속성, 전체 품질 게이트 및 완료 문서를 확인한다.

- [X] T009 `tests/books/test_services.py`에 `ProviderError`가 아닌 예외가 숨겨지지 않는지와 Service가 `books.models.Book`·ORM을 import하거나 변경하지 않는지 검증하는 회귀 테스트를 추가한다. (FR-014~FR-016, quickstart)
- [X] T010 `specs/003-book-search-service/quickstart.md`의 집중 Service 테스트 명령을 실행하고 정상·빈·오류·공백 검색어 계약이 실제 외부 호출 없이 통과하는지 확인한다.
- [X] T011 `scripts/verify.py`를 실행해 Django check, Ruff format, Ruff lint 및 전체 pytest 품질 게이트를 통과하는지 확인한다.
- [X] T012 `CHANGELOG.md`와 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`에 IMP-022 구현·검증 완료 사실과 완료 상태를 전체 검증 후 동기화한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1**: 의존성 없음. T001은 T002와 다른 파일이므로 병렬 수행할 수 있다.
- **Phase 2**: Service 공개 타입을 정의하며 모든 사용자 스토리를 차단한다.
- **US1 (Phase 3)**: Phase 2 완료 후 정상 검색 MVP를 제공한다.
- **US2 (Phase 4)**: US1의 Provider 호출 흐름에 빈 결과와 오류 분류를 추가한다.
- **US3 (Phase 5)**: 같은 Service 진입점에 short-circuit 정책을 추가하므로 US1·US2 뒤에 수행한다.
- **Phase 6**: 모든 사용자 스토리 완료 후 검증과 문서 동기화를 수행한다.

### 사용자 스토리 의존성

```text
공통 테스트 기반 → 상태·결과 계약 → US1 (MVP) → US2 → US3 → 품질 게이트·문서화
```

세 사용자 스토리는 하나의 `search_books()` 상태 기계를 점진적으로 완성하므로 같은 파일
충돌과 상태 불변조건 누락을 피하기 위해 순차 수행한다. 각 단계는 해당 상태를 독립적으로
fake Provider로 검증할 수 있다.

### 병렬 작업 기회

- T001과 T002는 서로 다른 파일이므로 병렬 수행할 수 있다.
- 구현과 테스트는 같은 파일을 수정하므로 같은 스토리 안에서는 순차 수행한다.
- Phase 6의 T009는 사용자 스토리 완료 뒤 `tests/books/test_services.py`를 수정하므로
  T010~T012보다 먼저 수행한다.

## 구현 전략

### MVP 우선

1. Phase 1~2로 fake Provider와 공개 결과 계약을 준비한다.
2. US1에서 trim, Provider 호출 1회, Metadata 보존 및 `SUCCESS`를 구현·검증한다.
3. US1 테스트가 통과하면 정상 도서 검색 Service MVP를 시연할 수 있다.

### 점진적 제공

1. US2로 정상 빈 결과와 Provider 실패를 분리한다.
2. US3로 공백 검색어의 호출 0회 정책을 추가한다.
3. Phase 6에서 예상 밖 예외의 전파, 비영속성, 집중·전체 검증 및 문서 상태 동기화를
   완료한다.

## 참고 사항

- 테스트 작업은 명세의 자동 검증 요구를 증명하지만 TDD 절차를 강제하지 않는다.
- `[P]` 작업은 서로 다른 파일이며 선행 작업에 의존하지 않을 때만 표시했다.
- 사용자 스토리 레이블은 모든 스토리 작업에 포함했다.
- 이 작업은 검색 화면(IMP-023), 도서 저장·재사용(IMP-024), retry, cache, fallback,
  실제 credential 호출 및 Provider 병합을 포함하지 않는다.
