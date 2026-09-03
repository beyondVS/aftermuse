# 구현 계획: Book 기본 모델

**브랜치**: `feature/day-02-auth-book-search` (Spec Kit 기능: `001-book-model`) | **날짜**: 2026-09-02 | **사양**: [spec.md](spec.md)

**입력**: `/specs/001-book-model/spec.md`의 기능 사양

## 요약

ISBN13으로 출판 판본을 구분하는 `books.Book` 도메인 모델과 초기 migration을 추가한다.
Book은 제목과 ISBN13을 필수로, 저자 표시·출판사·출간일·표지 위치·소개·목차를
선택값으로 저장한다. ISBN 형식과 빈 제목은 모델 검증 및 PostgreSQL CHECK 제약으로,
ISBN 유일성은 PostgreSQL unique constraint로 보장한다. 실제 Provider 연동, 검색 UI,
저장 Service 및 Work/Edition 분리는
후속 IMP 항목으로 남긴다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, Psycopg 3.3; 신규 의존성 없음

**저장소**: PostgreSQL 18.6 단일 지원

**테스트**: pytest 9.1, pytest-django 4.14, Django system check, Ruff 0.16

**대상 플랫폼**: PostgreSQL에 연결되는 Django 서버 애플리케이션

**프로젝트 유형**: 단일 저장소의 서버 렌더링 Django Web 애플리케이션

**성능 목표**: ISBN13 단건 조회의 95% 이상이 1초 이내에 성공 또는 미존재 결과를 반환

**제약 조건**: ASCII 숫자 13자리 ISBN13, 데이터베이스 수준 유일성, 선택 문자열은 빈
문자열, 미상 출간일은 `NULL`, SQLite fallback 금지, 새 테이블 초기 migration은
backfill 없음

**규모/범위**: 신규 Django 앱 1개, Book 모델 1개, 초기 migration 1개, 서로 다른
ISBN13 100건의 저장·조회 및 순차/동시 중복 검증

## 헌법 검사

*게이트: 0단계 조사 전에 통과해야 합니다. 1단계 설계 후 다시 확인합니다.*

### 설계 전 게이트

- **Books-first 및 범위 규율 — 통과**: Book 저장 기반은 핵심 제품 루프의 선행 조건이다.
  Provider, UI, Reading, Knowledge 및 API를 함께 구현하지 않는다.
- **신뢰 경계와 데이터 통제 — 통과**: 외부 Metadata가 들어올 수 있는 ISBN 형식과 빈
  제목은 모델 검증 및 데이터베이스 CHECK 제약으로 제한하고, 유일성은 database-level
  unique constraint로 보장한다. 이번 범위에는
  운영 쓰기 진입점이 없으며, 후속 IMP-024의 저장 Service가 영속화 전 검증을 담당한다.
- **단순한 아키텍처 — 통과**: `books` 도메인 앱과 모델만 추가한다. 아직 필요하지 않은
  Repository, Selector, Service, API 또는 Provider 추상화를 만들지 않는다.
- **기술 제약 — 통과**: Python 3.14, Django 6.1, PostgreSQL 18.6, Psycopg 3과 기본
  `BigAutoField`를 유지하며 신규 패키지를 추가하지 않는다.
- **증거 기반 품질 — 통과**: PostgreSQL 기반 모델 테스트, 생성 SQL, forward/reverse
  migration, Django check, Ruff, 전체 pytest로 완료를 입증한다.
- **Migration 안전성 — 통과**: 기존 테이블을 변경하지 않고 비어 있는 신규 Book 테이블을
  생성한다. table rewrite나 backfill이 없고 unique, CHECK 및 LIKE 조회용 index도 새 빈
  테이블에 만들어지므로 concurrent index 분할이나 `lock_timeout`이 필요하지 않다. 실제 SQL은
  `sqlmigrate`로 확인한다.

### 설계 후 재검사

- `data-model.md`는 하나의 Book 엔터티와 데이터베이스 유일성만 정의하며 범위를 넓히지
  않는다.
- 외부 HTTP/API/UI 계약이 없으므로 `contracts/`는 만들지 않는다. 후속 IMP-021부터
  Provider 및 사용자 인터페이스 계약을 별도로 정의한다.
- `quickstart.md`는 실제 PostgreSQL에서 모델 검증, 동시 중복 방지, migration 왕복 및
  전체 품질 게이트를 재현하도록 구성한다.
- 헌법 위반과 정당화가 필요한 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/001-book-model/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── spec.md
└── checklists/
    └── requirements.md
```

외부에 노출되는 API, CLI, UI 또는 Provider interface가 없으므로 `contracts/` 산출물은
생성하지 않는다. `tasks.md`는 후속 `$speckit-tasks` 단계에서 생성한다.

### 소스 코드 (저장소 루트)

```text
src/
├── books/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
└── config/
    └── settings.py

tests/
├── books/
│   └── test_models.py
└── test_settings.py
```

**구조 결정**: 기존 `accounts` 앱과 같은 도메인 앱 구조를 사용한다. `books.Book`은
데이터 구조, 기본 표시 및 모델 검증만 담당한다. `books` 앱 등록 후에도 임시 프로젝트
검증이 동작하도록 `tests/test_settings.py`의 복사 fixture에 새 앱을 포함한다. 운영 저장
흐름과 조회 전용 Selector는 실제 사용 사례가 생기는 후속 IMP-024 이후에 추가한다.

## 복잡성 추적

헌법 위반이나 추가 계층 도입이 없어 기록할 항목이 없다.
