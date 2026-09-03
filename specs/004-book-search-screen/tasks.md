---
description: "IMP-023 도서 검색 화면 구현 작업 목록"
---

# 작업: 도서 검색 화면

**입력**: `specs/004-book-search-screen/`의 설계 문서

**사전 조건**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [ui-contract.md](contracts/ui-contract.md),
[quickstart.md](quickstart.md)

**테스트**: 기능 사양이 실제 외부 호출 없이 상태와 접근 제어를 자동 검증하도록 명시하므로
View 통합 테스트를 포함한다. 테스트 선행 작성은 이 기능의 회귀 검증 수단이며 별도의 TDD
프로세스 채택을 뜻하지 않는다.

**구성**: P1 사용자 스토리 두 개를 먼저 각각 독립적으로 완료 가능한 화면 증가분으로
구성하고, 반응형·접근성 P2를 그 위에 적용한다.

## Phase 1: 설정

**목적**: 기존 `books` 앱에 검색 입력과 주소의 최소 골격을 추가한다.

- [X] T001 `src/books/forms.py`에 양끝 공백 제거 후 1~200자만 허용하는 `BookSearchForm`을 구현한다.
- [X] T002 `src/books/urls.py`에 `books:search` GET 주소를 정의하고 `src/config/urls.py`에서 `/books/` URLconf를 include한다.

---

## Phase 2: 기반

**목적**: 모든 화면 상태가 공유할 인증, Provider 조합, HTMX 응답 선택 경계를 만든다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 구현을 시작하지 않는다.

- [X] T003 `src/books/views.py`에 로그인 필수 function View와 `get_default_provider()`·`search_books()`의 의존성 조합을 구현하고, 일반 요청과 `HX-Request`의 template 응답을 구분한다.
- [X] T004 `src/templates/books/search.html`과 `src/templates/books/_search_region.html`에 전체 페이지와 교체 가능한 검색 영역의 공통 골격을 만든다.

**체크포인트**: 인증된 사용자는 검색 전 초기 화면을, 익명 사용자는 기존 로그인 흐름을 받는다.

---

## Phase 3: 사용자 스토리 1 - 올바른 판본 찾기 (우선순위: P1) 🎯 MVP

**목표**: 유효한 검색어로 모든 Provider 결과를 순서대로 표시해 사용자가 판본을 구분한다.

**독립 테스트**: 인증된 사용자가 서로 다른 표지·저자·출판사·출간일을 가진 같은 제목의
fake 결과를 검색하고, 전체 목록의 표시 순서와 선택 Metadata의 표시 여부를 확인한다.

### 사용자 스토리 1 테스트

- [X] T005 [US1] `tests/books/test_views.py`에 인증, 유효 검색, Provider factory 대체, 실제 `search_books()` 경유, 전체 결과 순서와 선택 서지정보·출간연도 표시를 검증하는 View 테스트를 작성한다.

### 사용자 스토리 1 구현

- [X] T006 [US1] `src/books/views.py`에서 유효한 `BookSearchForm` 입력에만 Provider를 생성하고 `BookSearchStatus.SUCCESS` 결과를 template context로 전달한다.
- [X] T007 [US1] `src/templates/books/_search_region.html`에 검색어, 제목을 포함한 `alt` 텍스트와 고정 영역의 표지, 제목, 저자, 출판사, 출간연도를 제공된 값에 한해 표시하는 순서 보존 결과 목록을 구현하고, URL이 없거나 browser가 로드하지 못해도 `alt` 텍스트와 나머지 서지정보로 식별할 수 있게 한다.

**체크포인트**: 결과는 저장·선택·외부 상세 링크 없이 Provider 반환 순서대로 모두 표시된다.

---

## Phase 4: 사용자 스토리 2 - 검색 진행과 결과 상태 이해 (우선순위: P1)

**목표**: 입력 오류, Loading, Empty, Error를 서로 구별하고 실패한 검색을 같은 검색어로 재시도한다.

**독립 테스트**: 초기·빈 값·공백·201자 입력, Provider 빈 결과와 Provider 오류를 각각
재현해 Provider 호출 수, 안내 문구, 재시도 및 민감한 오류 상세 비노출을 확인한다.

### 사용자 스토리 2 테스트

- [X] T008 [US2] `tests/books/test_views.py`에 초기 화면, invalid 입력의 Provider 미호출, Empty, Error, 재시도, 일반 HTML/HTMX Fragment 분기와 오류 상세 비노출을 검증하는 View 테스트를 작성한다.

### 사용자 스토리 2 구현

- [X] T009 [US2] `src/books/views.py`와 `src/templates/books/_search_region.html`에 `BookSearchStatus.EMPTY`·`ERROR`, Form field error, 재시도 가능한 현재 검색어 및 안전한 일반 오류 context를 구현한다.
- [X] T010 [US2] `src/templates/books/_search_region.html`과 `src/static/css/app.css`에 `hx-get`, `hx-target`, `hx-push-url`, `hx-sync="this:replace"`를 구현하고, HTMX 요청 중에는 Loading live status만 표시하며 기존 결과·Empty·Error 영역을 즉시 숨기는 상태 전환을 구현한다.

**체크포인트**: Empty와 Error는 다른 텍스트 안내를 제공하며, 외부 오류·자격 증명·Provider 진단은 HTML에 나타나지 않는다.

---

## Phase 5: 사용자 스토리 3 - 기기와 입력 방식에 관계없이 검색 (우선순위: P2)

**목표**: Desktop·Mobile과 키보드·보조 기술 환경에서 검색과 상태 확인이 가능하다.

**독립 테스트**: 1280px와 375px에서 긴 결과와 표지 없는 결과를 확인하고, Tab으로 검색·재시도에 도달하며 상태 변화가 텍스트와 live region으로 전달되는지 확인한다.

### 사용자 스토리 3 구현

- [X] T011 [US3] `src/static/css/app.css`에 검색 Form, 결과 카드, 고정 표지 영역, 긴 텍스트 줄바꿈, 375px/1280px 반응형 레이아웃 및 `focus-visible` 스타일을 추가한다.
- [X] T012 [US3] `src/templates/base.html`에 인증 사용자가 도서 검색 화면으로 이동할 수 있는 navigation을 추가하고 `src/templates/books/_search_region.html`의 label·오류 연결·heading·live region을 접근성 계약에 맞춘다.

**체크포인트**: 모든 상태는 색상 외 텍스트·구조로 구분되고 page-level 가로 scroll 없이 조작 가능하다.

---

## Phase 6: 마무리 및 교차 관심사

**목적**: 자동 검증, 수동 인수 검증, 완료 문서를 동기화한다.

- [X] T013 `tests/books/test_views.py`와 `src/books/views.py`를 검토해 검색 흐름이 Book·Reading·Book Knowledge ORM 또는 저장 동작을 호출하지 않는지 회귀 검증을 보강한다.
- [X] T014 [P] `docs/AfterMuse_MVP_Implementation_Plan_v5.md`에서 검증 완료 후 IMP-023 상태를 완료로 갱신한다.
- [X] T015 [P] `CHANGELOG.md`의 `[Unreleased]`에 사용자용 도서 검색 화면을 기록한다.
- [X] T016 `specs/004-book-search-screen/quickstart.md`의 자동 품질 명령 통과를 기록한다. 알라딘 신규 API key 발급 중단으로 live 검색을 포함한 최종 browser 검증은 더 이상 유효한 완료 조건이 아니므로 Day 03 `IMP-023A`의 Kakao live smoke와 Desktop/Mobile 수동 검증으로 대체 이관한다.

> **검증 예외 (2026-09-03)**: 자동 품질 게이트는 `80 passed, 1 skipped`로 통과했다. 알라딘 live 검색 검증은 신규 API key를 발급받을 수 없어 미실행으로 남기지 않고 Provider 종료에 따른 범위 변경으로 종결했으며, 대체 Provider의 실제 연동 검증은 IMP-023A에서 수행한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1**: 의존성 없음.
- **Phase 2**: Phase 1의 Form과 URL 구성이 필요하다.
- **US1 (Phase 3)**: Phase 2 이후 시작한다.
- **US2 (Phase 4)**: Phase 2 이후 시작할 수 있으나 US1의 동일 View/Fragment 변경과 충돌하므로 US1 완료 뒤 순차 적용한다.
- **US3 (Phase 5)**: US1·US2의 확정 Template 구조 이후 적용한다.
- **Phase 6**: 세 사용자 스토리 완료 후 실행한다.

### 사용자 스토리 의존성

- **US1 (P1)**: 검색 결과 식별이라는 MVP를 독립적으로 제공한다.
- **US2 (P1)**: 같은 주소와 Fragment를 확장하지만, 완료하면 각 상태를 독립적으로 검증할 수 있다.
- **US3 (P2)**: 앞선 화면의 반응형·접근성 품질을 완성한다.

### 병렬 작업 기회

- T001과 T002는 서로 다른 파일이므로 병렬로 진행할 수 있다.
- T011은 확정된 Template class/구조를 받은 뒤 T012와 다른 파일 위주로 병렬 진행할 수 있다.
- T014와 T015의 문서 갱신은 구현 및 검증 완료 후 병렬로 진행할 수 있다.

## 병렬 예시: 설정과 마무리

```text
Task: "src/books/forms.py에 BookSearchForm 구현"
Task: "src/books/urls.py 및 src/config/urls.py에 books:search 라우팅 연결"

Task: "docs/AfterMuse_MVP_Implementation_Plan_v5.md에 IMP-023 완료 표시"
Task: "CHANGELOG.md의 [Unreleased]에 도서 검색 화면 기록"
```

## 구현 전략

### MVP 우선 (US1)

1. Phase 1에서 입력 경계와 URL을 준비한다.
2. Phase 2에서 인증 View와 Fragment 골격을 만든다.
3. US1의 자동 검증과 결과 목록을 완성한다.
4. 인증된 사용자의 정상 검색과 판본 구분을 독립 검증한다.

### 점진적 제공

1. US1: 결과 목록과 판본 구분을 제공한다.
2. US2: 입력 오류와 Loading·Empty·Error 회복 상태를 추가한다.
3. US3: 반응형·키보드·보조 기술 품질을 적용한다.
4. 마무리 단계에서 전체 품질 게이트와 완료 문서를 동기화한다.

## 참고 사항

- 모든 작업은 체크박스, 순차 Task ID, 필요한 Story label, 정확한 파일 경로를 갖는다.
- `[P]`는 다른 미완료 작업과 파일 충돌 없이 병렬 수행 가능한 작업만 표시한다.
- 외부 I/O는 `get_default_provider()` 대체로만 차단하고 `search_books()`의 실제 상태 변환을 검증한다.
- migration, 신규 runtime dependency, JSON API, pagination, 결과 저장·선택은 작업 범위에 없다.
