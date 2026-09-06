---
description: "도서 검색 복구 및 선택 구현 작업"
---

# 작업: 도서 검색 복구 및 선택

**입력**: `specs/005-book-search-selection/`의 plan.md, spec.md, research.md,
data-model.md, contracts/, quickstart.md

**테스트**: 기능 사양의 완료 조건에 따라 fake/mock 기반 자동 테스트와 명시 실행 `live`
smoke test를 포함한다. 기본 pytest는 외부 연결을 수행하지 않는다.

**구성**: Provider 공통 경계를 먼저 정리한 뒤, P1 검색 복구와 P1 선택 등록을 각각
검증 가능한 증가분으로 완료하고, P2 중복·동시성 보장을 추가한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일이며 완료 전제조건이 없는 병렬 작업
- **[Story]**: 해당 사용자 스토리 (`US1`, `US2`, `US3`)

## Phase 1: 설정

**목적**: Kakao 기본 Provider의 안전한 설정과 live-test 실행 경계를 준비한다.

- [X] T001 [P] `src/config/settings.py`에 조건부 `KAKAO_REST_API_KEY` 환경 설정을 추가하고 `ALADIN_TTB_KEY` legacy 설정을 유지한다.
- [X] T002 [P] `.env.example`과 `README.md`에 실제값 없는 Kakao key 예시와 명시적 `-m live` 실행법을 추가한다.
- [X] T003 [P] `tests/test_repository_contract.py`에 `live` marker 등록과 기본 `not live` 선택식이 유지되는지 검증하는 테스트를 추가한다.

---

## Phase 2: 기반 — Provider 중립 계약

**목적**: 모든 검색·선택 작업이 사용할 Provider 중립 계약을 Aladin package 밖에 둔다.

**⚠️ 중요**: 이 단계가 완료될 때까지 US1 검색 복구와 이후 스토리를 시작하지 않는다.

- [X] T004 `src/integrations/book_metadata/contracts.py`와 `src/integrations/book_metadata/exceptions.py`에 `ProviderBook`, `BookMetadataProvider`, Provider 오류 계층의 정본을 이동한다.
- [X] T005 `src/integrations/aladin/contracts.py`, `src/integrations/aladin/exceptions.py`, `src/integrations/aladin/client.py`, `src/books/services.py`, `tests/integrations/aladin/test_client.py`, `tests/books/test_services.py`, `tests/books/test_views.py`의 import를 정본 또는 호환 re-export로 전환해 legacy Aladin 회귀를 보존한다.
- [X] T006 `src/integrations/book_metadata/__init__.py`에서 중립 계약과 예외의 canonical import 경계를 공개하고 `tests/integrations/aladin/test_client.py`에서 legacy re-export 호환성을 검증한다.

**체크포인트**: 구체 Provider 이름과 무관한 검색 Service 계약 및 기존 Aladin 자동 테스트가 통과한다.

---

## Phase 3: 사용자 스토리 1 - 신뢰할 수 있는 도서 검색 복구 (우선순위: P1) 🎯 MVP

**목표**: 로그인 사용자가 Kakao 기반 검색으로 정상·빈·실패·timeout 상태와 판본 식별 정보를 확인한다.

**독립 테스트**: fake transport로 Kakao의 정상/빈/실패/timeout과 ISBN10+ISBN13 정규화를 검증하고, 기존 검색 View에서 같은 상태가 표시되는지 확인한다.

### 사용자 스토리 1 테스트

- [X] T007 [P] [US1] `tests/integrations/kakao/test_client.py`에 endpoint, Authorization header, 3초 timeout, 정상/빈 documents, HTTP·network·timeout·손상 응답 오류 매핑 테스트를 작성한다.
- [X] T008 [P] [US1] `tests/integrations/kakao/test_client.py`에 ISBN10/ISBN13 token 선택, 무효 항목 제외, authors·datetime·선택 Metadata 정규화와 key 비노출 테스트를 작성한다.
- [X] T009 [P] [US1] `tests/books/test_views.py`에 Kakao 기본 factory를 fake로 대체한 정상·빈·오류 검색 회귀 테스트를 추가한다.

### 사용자 스토리 1 구현

- [X] T010 [US1] `src/integrations/kakao/client.py`에 주입 가능한 `urllib` transport와 Kakao request·응답 검증·`ProviderBook` 정규화를 구현한다.
- [X] T011 [US1] `src/integrations/book_metadata/factory.py`에서 Kakao Adapter를 기본 Provider로 선택하고 `src/books/views.py`의 factory import를 중립 경계로 전환한다.
- [X] T012 [US1] `src/config/settings.py`, `src/templates/books/_search_region.html`, `src/static/css/app.css`에서 Kakao 전환 후에도 기존 Normal/Loading/Empty/Error와 표지·저자·출판사·출간연도 검색 계약을 유지한다.
- [X] T013 [US1] `tests/integrations/kakao/test_live_smoke.py`에서 실제 key가 있을 때 대표 한국 도서 검색의 유효 ISBN13·제목을 확인하고, key·header·원본 응답을 출력하지 않게 한다.

**체크포인트**: fake 기반 전체 검색 회귀 테스트가 통과하고, `-m live`에서만 실제 Kakao smoke를 실행할 수 있다.

---

## Phase 4: 사용자 스토리 2 - 검색 결과에서 책 선택 및 등록 (우선순위: P1)

**목표**: 사용자가 서버가 보관한 검색 후보 ID만으로 유효한 새 Book을 선택·등록하고 완료 상태를 확인한다.

**독립 테스트**: 성공 검색 결과를 현재 사용자 session에 저장한 뒤 화면이 보낸 Metadata를 무시하고 후보 ID로 새 Book 한 건만 만드는지 검증한다.

### 사용자 스토리 2 테스트

- [X] T014 [P] [US2] `tests/books/test_selection_candidates.py`에 JSON 후보 최대 20건, 15분 TTL, 새 검색/Empty/Error의 batch 제거, 임의·만료·다른 사용자 ID 거부 테스트를 작성한다.
- [X] T015 [P] [US2] `tests/books/test_services.py`에 후보 기반 신규 Book 생성, 누락 선택 Metadata 보존, 선택 실패 rollback과 `BookSelectionResult` 테스트를 작성한다.
- [X] T016 [P] [US2] `tests/books/test_views.py`에 인증·POST·CSRF, 후보 ID만 가진 선택 Form, HTMX/전체 HTML 성공·만료 응답, client ISBN/Metadata 변조 무시 테스트를 작성한다.

### 사용자 스토리 2 구현

- [X] T017 [US2] `src/books/selection_candidates.py`에 JSON 직렬화, 임의 후보 ID, owner PK 검증, 15분 TTL 및 최신 batch 삭제·조회 helper를 구현한다.
- [X] T018 [US2] `src/books/services.py`에 검증된 후보를 새 `Book`으로 생성하거나 기존 Book을 반환하는 `BookSelectionResult`와 선택 Service를 구현한다.
- [X] T019 [US2] `src/books/forms.py`, `src/books/urls.py`, `src/books/views.py`에 `candidate_id`만 받는 CSRF 보호 `books:select` POST와 안전한 후보 오류 처리를 구현한다.
- [X] T020 [US2] `src/books/views.py`와 `src/templates/books/_search_region.html`에 성공 검색 시 후보를 저장하고 각 결과에 접근 가능한 선택 Form을 표시하도록 연결한다.
- [X] T021 [US2] `src/templates/books/_selection_result.html`, `src/templates/books/search.html`, `src/static/css/app.css`에 신규/기존 선택 완료와 재검색 안내를 Desktop·Mobile·보조 기술 계약에 맞게 구현한다.

**체크포인트**: 새 ISBN13 후보 선택은 Book 한 건을 등록하며 변조·만료·다른 사용자 후보는 Book을 만들지 않는다.

---

## Phase 5: 사용자 스토리 3 - 같은 판본의 중복 등록 방지 (우선순위: P2)

**목표**: 같은 ISBN13을 반복 또는 동시에 선택해도 기존 Book을 재사용하고 서지정보를 변경하지 않는다.

**독립 테스트**: 동일 후보·ISBN13을 순차와 실제 transaction 동시 요청으로 선택해 한 건만 남고 모든 성공 결과가 같은 Book을 가리키는지 확인한다.

### 사용자 스토리 3 테스트

- [X] T022 [P] [US3] `tests/books/test_services.py`에 기존 ISBN13 재사용, 기존 Metadata 무변경, 같은 후보 반복 선택의 멱등성 테스트를 추가한다.
- [X] T023 [P] [US3] `tests/books/test_services.py`에 PostgreSQL transaction을 사용하는 동시 동일 ISBN13 선택이 최종 Book 한 건만 남기는 회귀 테스트를 추가한다.
- [X] T024 [P] [US3] `tests/books/test_views.py`에 선택 재전송이 동일 Book을 반환하고 추가 Provider 호출이나 Book 이외의 영속 변경을 발생시키지 않는 통합 테스트를 추가한다.

### 사용자 스토리 3 구현

- [X] T025 [US3] `src/books/services.py`의 선택 Service에 기존 `Book.isbn13` unique 제약을 이용한 짧은 atomic `get_or_create` 경계와 IntegrityError 회복을 구현한다.
- [X] T026 [US3] `src/books/selection_candidates.py`와 `src/books/views.py`에서 성공 후보를 TTL까지 유지해 이중 클릭·재전송이 같은 Book으로 귀결되게 한다.

**체크포인트**: 순차·동시·재전송 선택에서 중복 Book은 0건이며 기존 Metadata가 변하지 않는다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: 전체 검증, 실제 운영 후보 확인 및 변경 문서화를 완료한다.

- [X] T027 [P] `pyproject.toml`과 `tests/integrations/kakao/test_live_smoke.py`에서 기본 pytest의 `live` 제외와 명시적 `-m live` 선택을 검증한다.
- [X] T028 [P] `CHANGELOG.md`와 `docs/AfterMuse_MVP_Implementation_Plan_v5.md`에 Kakao 전환 결과와 IMP-024/IMP-025 완료 상태를 동기화한다.
- [X] T029 자동 검증·수동 Desktop/Mobile·live smoke 시나리오를 실행하고 결과를 `specs/005-book-search-selection/quickstart.md`에 대조
- [X] T030 `src/`, `tests/`, `scripts/verify.py`에 대해 `uv run python scripts/verify.py`를 실행하고, key가 있는 환경에서는 `uv run pytest -m live tests/integrations/kakao/test_live_smoke.py -v`를 실행한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- Phase 1은 즉시 시작할 수 있다.
- Phase 2는 T001 완료 후 진행하며 US1·US2·US3을 차단한다.
- US1은 T004–T006 완료 후 진행한다.
- US2는 US1의 Kakao `ProviderBook` 결과 계약(T010–T012) 완료 후 진행한다.
- US3은 US2 선택 Service(T017–T021) 완료 후 진행한다.
- Phase 6은 필요한 사용자 스토리와 자동 검증이 모두 끝난 뒤 진행한다.

### 사용자 스토리 의존성

```text
Provider 중립 기반
  └─ US1: Kakao 검색 복구 (MVP)
       └─ US2: 서버 보관 후보 선택·Book 등록
            └─ US3: 반복·동시 선택 중복 방지
                 └─ 마무리·live smoke·전체 검증
```

### 병렬 실행 기회

- T001–T003은 서로 다른 파일에서 병렬로 진행할 수 있다.
- US1의 T007–T009는 구현 전 병렬 테스트 작업이다.
- US2의 T014–T016과 US3의 T022–T024는 각 스토리 내 병렬 테스트 작업이다.
- T027과 T028은 전체 구현 완료 후 서로 다른 검증·문서 파일에서 병렬로 진행할 수 있다.

## 병렬 예시: 사용자 스토리 2

```text
Task: "tests/books/test_selection_candidates.py에 session 후보 TTL·소유권 테스트 작성"
Task: "tests/books/test_services.py에 신규 Book 선택·rollback 테스트 작성"
Task: "tests/books/test_views.py에 CSRF·변조 방지 선택 흐름 테스트 작성"
```

## 구현 전략

### MVP 우선

1. Phase 1과 Phase 2를 완료한다.
2. US1을 구현·검증해 실제 검색 복구를 먼저 시연한다.
3. US2를 구현·검증해 안전한 Book 선택과 등록을 연결한다.
4. US3로 동시성·멱등성 보장을 추가한다.
5. 마지막으로 기본 전체 검증과 명시적 live smoke를 분리해 실행한다.

### 점진적 제공

- US1은 정상·빈·오류 검색 상태와 Kakao 전환만으로 독립 가치가 있다.
- US2는 서버 보관 후보를 이용해 변조 없는 새 Book 등록을 추가한다.
- US3는 반복·동시 선택에서 Book 데이터 일관성을 보장한다.

## 참고 사항

- 모든 작업은 정확한 경로, 완료 조건 및 의존성을 포함한다.
- 외부 I/O는 fake/mock으로 격리하고, 실제 외부 연결 검증은 `live` marker에만 둔다.
- 코드·문서 변경 뒤에는 해당 테스트와 최종 `scripts/verify.py` 증거를 남긴다.

## Phase 7: Convergence

- [X] T031 `src/integrations/kakao/client.py`에서 ISBN 후보 내부의 하이픈을 제거한 뒤 ASCII 13자리 ISBN13을 판별하고 `tests/integrations/kakao/test_client.py`에 공백·하이픈·ISBN10/ISBN13 혼합 표기 회귀 테스트를 추가한다. per FR-005, SC-003 (partial)
- [X] T032 `tests/integrations/kakao/test_client.py`에 빈 `documents`가 정상 빈 결과가 되는 테스트와 HTTP·network·timeout·손상 응답 오류에서 REST API key와 원본 진단이 노출되지 않는 assertion을 추가한다. per SC-002, FR-014 (partial)

## Phase 8: Convergence

- [X] T033 `src/books/views.py`와 `src/templates/books/_search_region.html`에서 검색 결과와 session 후보를 생성 순서대로 1:1 결합하고, 동일 ISBN13 결과가 둘 이상이어도 각 판본 카드가 화면에 표시된 서지정보의 후보 ID 하나만 제출하는 회귀 테스트를 `tests/books/test_views.py`에 추가한다. per FR-007B, FR-008, US2/AC1 (partial)
- [X] T034 `src/books/views.py`와 `src/templates/books/_selection_result.html`에서 Book 저장 단계의 예상 가능한 DB 실패를 rollback 후 내부 진단 없는 선택 실패·재검색 안내로 변환하고, 불완전한 Book이 남지 않으며 재시도 가능한지 `tests/books/test_views.py`에 검증한다. per FR-014, FR-015, UI contract: DB/예상 실패 (partial)

## Phase 9: Convergence

- [X] T035 `src/books/views.py`와 `src/templates/books/_search_region.html`에서 Book 저장 실패 시 같은 `candidate_id`를 다시 제출할 수 있는 CSRF 보호 재시도 Form을 제공하고, `tests/books/test_views.py`에서 첫 DB 실패 뒤 같은 후보 재시도가 성공하며 Book 한 건만 남는지 검증한다. per FR-015, UI contract: DB/예상 실패 (partial)
- [X] T036 1280px Desktop과 375px Mobile에서 키보드만으로 검색 시작부터 판본 선택 완료까지를 각각 2회 연속 회당 2분 이내에 수행하고, 환경·반복 횟수·소요 시간·결과를 `specs/005-book-search-selection/quickstart.md`에 기록한다. per SC-008 (partial)
