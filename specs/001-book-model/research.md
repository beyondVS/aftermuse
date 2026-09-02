# Phase 0 조사: Book 기본 모델

## 결정 1 — ISBN13을 MVP Book 식별자로 사용

**Decision**: Book은 MVP에서 ASCII 숫자 13자리 ISBN13으로 출판 판본을 구분하고,
ISBN13마다 하나의 행만 허용한다.

**Rationale**: PRD와 승인된 Day 02 설계가 ISBN13 중심 모델을 확정했으며, 이후 Reading과
Book Knowledge가 안정적으로 동일 Book을 참조하려면 단일 식별 규칙이 필요하다.

**Alternatives considered**:

- Work와 Edition을 즉시 분리: Core MVP에 필요하지 않은 관계와 병합 정책을 선행하므로 제외.
- Provider별 ID를 식별자로 사용: Provider 교체와 다중 공급자 통합을 어렵게 하므로 제외.
- 내부 PK만으로 중복을 허용: 같은 ISBN의 Reading과 Knowledge가 분산되므로 제외.

## 결정 2 — 모델 검증과 데이터베이스 제약을 분담

**Decision**: ISBN13의 ASCII 숫자 13자리 형식은 `\A[0-9]{13}\Z` 패턴으로, 필수 필드는
모델 검증으로 확인하고, ISBN13 유일성은 데이터베이스 unique constraint로 강제한다.
ISBN 체크 디지트는 이번 범위에서 검증하지 않는다.

**Rationale**: ASCII 범위를 명시하면 Unicode 숫자를 잘못 허용하지 않는다. 모델 검증은
사용 가능한 오류를 제공하고, 데이터베이스 제약은 우회 저장과 동시 요청에서도 최종 Book
한 건을 보장한다. Django의 일반 저장 호출은 `full_clean()`을 자동 실행하지 않으므로 형식
검증 테스트는 명시적으로 모델 검증 경로를 사용하고, 후속 저장 Service도 영속화 전에 같은
검증을 호출해야 한다.

**Alternatives considered**:

- Service 검사만 사용: 동시 요청과 우회 쓰기에서 중복이 생길 수 있어 제외.
- `\d{13}` 사용: Unicode 숫자도 허용하고 검색 기반 validator의 경계를 덜 명확하게
  표현하므로 제외.
- ISBN 형식까지 database check constraint로 강제: 현재 승인 설계와 완료 조건보다 범위를
  넓히므로 제외.
- `save()`를 재정의해 항상 `full_clean()` 호출: bulk 작업과 Django 관례를 바꾸는 전역
  side effect가 생기므로 제외.

## 결정 3 — 서지정보의 최소 타입과 누락 표현

**Decision**: 제목과 저자 표시는 최대 500자, 출판사는 최대 255자, 표지 위치는 최대
1000자의 URL로 보존한다. 소개와 목차는 길이 제한 없는 텍스트로 둔다. 누락된 선택
문자열은 빈 문자열, 미상 출간일은 `NULL`로 보존한다.

**Rationale**: 승인된 Day 02 설계와 기존 구현 계획의 필드 계약을 재사용한다. 문자열과
날짜의 누락 표현을 구분하면 불필요한 nullable 문자열을 피하면서 미상 날짜를 정확히
표현할 수 있다. 표지 원격 자원의 존재 여부는 모델이 확인하지 않는다.

**Alternatives considered**:

- 모든 선택 필드를 `NULL`로 저장: 빈 문자열과 `NULL`의 이중 상태가 생기므로 제외.
- 저자를 별도 엔터티로 분리: Provider 표시 문자열 정규화와 동명이인 정책이 필요해 제외.
- 원본 Metadata를 JSON으로 보존: 현재 저장·조회 완료 조건에 필요하지 않아 제외.

## 결정 4 — 별도 Service와 외부 계약을 만들지 않음

**Decision**: IMP-020에서는 `books` 앱, Book 모델, 초기 migration과 모델 테스트만 만든다.
HTTP/API/UI/CLI 또는 Provider contract 산출물은 생성하지 않는다.

**Rationale**: 이 기능은 내부 데이터 기반만 제공한다. 운영 저장 흐름은 IMP-024,
Provider 계약은 IMP-021, 검색 UI는 IMP-023에서 처음 필요해진다. 지금 외부 계약이나
Service를 만들면 사용 사례 없이 내부 구현을 고착시킨다.

**Alternatives considered**:

- 빈 `contracts/README.md` 생성: 의미 없는 산출물이므로 제외.
- Book 생성 Service 선행: 저장 정책과 Provider 결과 병합 정책이 IMP-024 전에는 확정되지
  않아 제외.
- REST API 추가: 프로젝트의 API-first 금지 원칙과 현재 범위에 어긋나므로 제외.

## 결정 5 — 초기 migration은 단일 CreateModel로 생성

**Decision**: Django가 생성하는 단일 `0001_initial` migration으로 빈 Book 테이블과
ISBN13 unique constraint를 함께 만든다. concurrent index 분할과 `lock_timeout`은
추가하지 않는다.

**Rationale**: 기존 데이터나 Book 테이블이 없어 backfill과 table rewrite가 없다. Django의
PostgreSQL backend가 unique 문자열의 LIKE 조회를 위해 별도 `varchar_pattern_ops` index를
생성하더라도 새 빈 테이블 대상이므로 기존 쓰기를 차단하지 않는다. 실제 migration 생성 후
`sqlmigrate`로 테이블, unique constraint, 보조 index와 reverse SQL을 확인한다.

**Alternatives considered**:

- unique index를 별도 concurrent migration으로 생성: 비어 있는 신규 테이블에는 복잡성만
  추가하므로 제외.
- `SeparateDatabaseAndState` 사용: 상태와 데이터베이스 작업을 분리할 이유가 없어 제외.
- `lock_timeout` 추가: 기존 관계에 `ACCESS EXCLUSIVE`를 요청하는 변경이 없어 제외.

## 결정 6 — 실제 PostgreSQL 기반으로 검증

**Decision**: 모델 테스트는 SQLite fallback이나 내부 ORM mocking 없이 프로젝트의
PostgreSQL test database에서 실행한다. 저장 왕복, 선택값, 모델 검증, 정확 조회,
미존재, 순차·동시 중복, 100건 구분을 검증한다.

**Rationale**: 유일성 경쟁과 migration SQL은 실제 지원 저장소에서 확인해야 신뢰할 수
있다. 프로젝트 헌법도 PostgreSQL 단일 지원과 실제 상태 기반 테스트를 요구한다.

**Alternatives considered**:

- SQLite 단위 테스트: 지원하지 않는 저장소이며 PostgreSQL 동시성 의미를 대변하지 못해
  제외.
- ORM mock: database constraint와 query 결과를 검증하지 못해 제외.
- 순차 중복 테스트만 수행: 기본 회귀에는 유용하지만 명세의 동시 중복 조건을 단독으로
  입증하지 못하므로 동시성 검증을 함께 둔다.

## 결정 7 — 설정 격리 회귀 테스트를 함께 갱신

**Decision**: `books` 앱을 `INSTALLED_APPS`에 추가할 때 `tests/test_settings.py`의 임시
프로젝트 fixture도 `src/books`를 복사하도록 갱신한다.

**Rationale**: 현재 두 설정 테스트는 `src/config`와 `src/accounts`만 임시 프로젝트로
복사한 뒤 관리 명령을 실행한다. 설정이 `books.apps.BooksConfig`를 참조하면 앱을 복사하지
않은 격리 환경에서 `ModuleNotFoundError`가 발생한다.

**Alternatives considered**:

- 설정 테스트에서 `books` 앱을 제거한 별도 설정 사용: 실제 프로젝트 설정을 검증하지
  못하므로 제외.
- 해당 테스트를 삭제 또는 완화: 환경변수 로딩 회귀 보호를 잃으므로 제외.

## 조사 결론

모든 기술적 결정이 프로젝트 문서, 현재 저장소 설정과 로컬 Django 6.1 동작으로
해소되었다. 남은 `NEEDS CLARIFICATION` 항목은 없으며 Phase 1 설계로 진행할 수 있다.
