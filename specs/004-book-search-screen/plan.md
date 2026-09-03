# 구현 계획: 도서 검색 화면

**브랜치**: `feature/day-02-auth-book-search` | **날짜**: 2026-09-03 | **사양**: [spec.md](spec.md)

**입력**: `/specs/004-book-search-screen/spec.md`의 기능 사양

## 요약

로그인한 사용자가 1~200자의 검색어로 기존 도서 검색 Service를 호출하고, 검색 전·진행
중·정상 결과·빈 결과·오류를 구분하는 반응형 화면을 `books` 도메인에 추가한다. 단일 GET
주소가 일반 요청에는 전체 문서를, HTMX 요청에는 검색 영역 Fragment를 반환한다. 입력은
Django Form이 검증하고 View는 Provider factory와 기존 `search_books()`를 조합하는 얇은
경계만 담당한다. 새 검색은 이전 요청을 교체하고 이전 결과를 즉시 숨기며, 결과 전체를
Pagination 없이 표시한다.

## 기술적 맥락

**언어/버전**: Python 3.14, HTML5, CSS, 최소 JavaScript

**주요 의존성**: Django 6.1 Templates·Forms·Session Authentication, HTMX 2.0.10,
Alpine.js CSP 3.17.1 공통 자산, 기존 `BookSearchResult`와 Provider factory

**저장소**: N/A — 검색 화면은 Book, Reading 또는 Book Knowledge를 조회·변경하지 않음

**테스트**: pytest 9.1, pytest-django 4.14, Django test client, Ruff 0.16,
`scripts/verify.py`, Desktop/Mobile 수동 브라우저 검증

**대상 플랫폼**: Django 기반 Linux Web server와 최신 Desktop/Mobile Web browser

**프로젝트 유형**: 서버 렌더링 Django Web application

**성능 목표**: 준비된 검색 응답을 1초 이내에 화면 상태로 반영하고, 유효한 검색당 Provider
호출 1회, 무효 입력당 0회

**제약 조건**: 로그인 필수, 검색어 1~200자, Provider 반환 결과 전체를 단일 목록으로 표시,
새 검색 중 이전 결과 숨김, 외부 오류 상세 비노출, CDN·신규 runtime 의존성·Pagination·
저장·도서 선택·Reading 생성·Book Knowledge 준비 없음

**규모/범위**: 검색 주소 1개, Form 1개, 얇은 View 1개, 전체 페이지 1개와 검색 영역
Fragment 1개, 검색 화면 CSS, View 통합 테스트 1개

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 재확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| II. 핵심 제품 루프와 범위 규율 | Books-first 흐름의 검색과 판본 구분까지만 구현하고 선택·Reading 생성은 IMP-024에 남긴다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | Form이 검색어를 검증하고 Template autoescape를 유지하며 Provider 오류 상세를 전달하지 않는다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 얇은 서버 렌더링 View가 기존 Service와 Adapter factory를 직접 조합하고 내부 HTTP API를 만들지 않는다. | 통과 |
| V. 증거 기반 품질과 회복 가능한 UX | Normal·Loading·Empty·Error·Success, Keyboard, focus, Desktop/Mobile을 자동·수동 인수 조건으로 검증한다. | 통과 |
| UI 기술 제약 | 저장소의 Django Template, HTMX와 공통 로컬 자산을 재사용하며 CDN과 SPA를 추가하지 않는다. | 통과 |
| 영속성 경계 | 검색 화면은 Book·Reading·Knowledge ORM을 사용하거나 상태를 저장하지 않는다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/004-book-search-screen/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-contract.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── books/
│   ├── forms.py             # 1~200자 검색어 검증
│   ├── urls.py              # books:search 주소
│   ├── views.py             # 인증·Form·Service·응답 조합
│   └── services.py          # 기존 IMP-022 검색 계약, 변경 최소화
├── config/
│   └── urls.py              # books URL include
├── templates/
│   ├── base.html            # 인증 사용자용 도서 검색 navigation
│   └── books/
│       ├── search.html      # 전체 페이지
│       └── _search_region.html  # Form·Loading·결과 상태 Fragment
└── static/
    └── css/
        └── app.css          # 검색 목록·상태·반응형·focus 스타일

tests/
└── books/
    └── test_views.py        # 인증·입력·상태·Fragment 계약 테스트

docs/AfterMuse_MVP_Implementation_Plan_v5.md  # 전체 검증 후 IMP-023 완료 표시
CHANGELOG.md                                  # Unreleased 기능 기록
```

**구조 결정**: 검색 UI를 기존 `books` 앱 안에 두고 별도 API나 frontend application을 만들지
않는다. Form은 입력 경계를, 기존 Service는 검색 정책을, View는 의존성 조합과 Template
선택을, Template/CSS는 표시 상태를 담당한다. 외부 I/O 테스트는 Provider factory만 fake로
대체하고 실제 Service 상태 변환은 그대로 실행한다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
