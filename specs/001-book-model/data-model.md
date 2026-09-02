# 데이터 모델: Book 기본 모델

## 엔터티 개요

### Book

MVP에서 하나의 ISBN13으로 구분되는 출판 판본이다. 내부 관계를 위한 기본 PK와
서지정보를 가지며, 사용자·Reading·Book Knowledge와의 관계는 이번 기능에서 만들지
않는다.

## 필드 정의

| 필드 | 저장 형태 | 필수 | 기본/누락 값 | 검증 및 의미 |
| --- | --- | --- | --- | --- |
| `id` | 64-bit 자동 증가 정수 | 예 | 자동 생성 | 내부 PK이며 외부 도서 식별자로 사용하지 않음 |
| `isbn13` | 최대 13자 문자열 | 예 | 없음 | ASCII 숫자 13자리, Book 전체에서 유일, 체크 디지트 검증 제외 |
| `title` | 최대 500자 문자열 | 예 | 없음 | 빈 제목은 모델 검증에서 거부 |
| `authors` | 최대 500자 문자열 | 아니요 | 빈 문자열 | Provider가 제공한 저자 표시를 분해하지 않고 보존 |
| `publisher` | 최대 255자 문자열 | 아니요 | 빈 문자열 | 출판사 표시 문자열 |
| `published_date` | 날짜 | 아니요 | `NULL` | 출간일 미상과 실제 날짜를 구분 |
| `cover_url` | 최대 1000자 URL 문자열 | 아니요 | 빈 문자열 | URL 형식만 검증하며 원격 자원 존재는 확인하지 않음 |
| `description` | 텍스트 | 아니요 | 빈 문자열 | 책 소개를 추측하거나 생성하지 않음 |
| `table_of_contents` | 텍스트 | 아니요 | 빈 문자열 | 목차를 추측하거나 책 내용으로 확장하지 않음 |

문자열 최대 길이는 승인된 Day 02 설계와 구현 계획을 따른다. 누락된 문자열에 `NULL`을
사용하지 않아 빈 값 표현을 하나로 유지하고, 의미상 미상 상태가 필요한 출간일에만
`NULL`을 사용한다.

## 무결성 규칙

1. `isbn13`은 모델 검증 시 ASCII 숫자 13자리여야 한다.
2. `isbn13`의 ISBN 체크 디지트 유효성은 검사하지 않는다.
3. `isbn13`에는 데이터베이스 unique constraint가 있어야 한다.
4. 데이터베이스 CHECK 제약은 ISBN13이 ASCII 숫자 13자리인지와 `title`이 빈 문자열이 아닌지를 보장해야 한다.
5. 같은 ISBN13 저장이 순차 또는 동시에 시도되어도 최종 Book은 한 건만 남아야 한다.
6. 중복 저장 실패는 기존 Book의 서지정보를 변경하지 않아야 한다.
7. `title`은 모델 검증에서 필수이며 빈 문자열을 허용하지 않는다.
8. 선택 문자열이 누락되면 빈 문자열을 유지하고 임의 값을 채우지 않는다.
9. 출간일이 누락되면 `NULL`을 유지하고 임의 날짜를 만들지 않는다.

## 검증 경계

- ISBN 형식은 `\A[0-9]{13}\Z` 패턴으로 검증해 Unicode 숫자를 허용하지 않는다.
- ISBN 형식, 필수 제목, URL 형식과 필드 길이는 Django 모델 검증 계약이다.
- 일반 `save()`와 `objects.create()`는 모델 검증을 자동 호출하지 않으므로, 형식 오류를
  확인하는 테스트와 후속 운영 저장 Service는 영속화 전에 `full_clean()`을 호출한다.
- PostgreSQL CHECK 제약은 raw ORM 저장에서도 ISBN 형식과 빈 제목을 거부한다. ISBN
  유일성은 모델 검증 결과와 별개로 unique constraint가 최종 보장하며, 경쟁 상황의 패배
  요청은 무결성 오류로 종료되어야 한다.
- 문자열 trim, Provider 응답 정규화 및 기존 Book 갱신·병합은 후속 기능의 책임이다.

## 조회 계약

- ISBN13 exact lookup은 Book 한 건 또는 미존재 결과만 반환한다.
- 내부 PK 조회도 가능하지만 도서 중복 판단에는 ISBN13을 사용한다.
- 기본 문자열 표현은 제목을 반환해 관리 및 디버깅 시 Book을 식별할 수 있게 한다.
- 목록, 검색어, 저자 또는 출판사 기반 조회 계약은 이번 범위에 포함하지 않는다.

## 관계

현재 관계는 없다. 후속 기능에서 다음 관계가 필요해질 수 있지만 이번 migration에는
포함하지 않는다.

- `Reading` → `Book`: 사용자의 독서 경험이 하나의 Book을 참조
- `BookKnowledge` → `Book`: 검증된 도서 지식이 하나의 Book을 참조

## 상태와 생명주기

Book 자체의 상태 enum이나 전이는 없다.

```text
검증 가능한 입력 → 저장된 Book → ISBN13 exact lookup
                         ↘ 중복 시도는 거부되고 기존 Book 유지
```

삭제, Metadata 갱신, merge, Edition 분리 및 보존 정책은 이번 기능에서 정의하지 않는다.

## Migration 설계

- `books` 앱의 `0001_initial` 한 파일로 Book 테이블을 생성한다.
- 기존 Book 테이블과 행이 없으므로 data migration, backfill 및 상태 분리가 필요 없다.
- ISBN13 유일성, ISBN13·제목 CHECK 제약과 Django가 생성하는 LIKE 조회용 보조 index는 새 빈 테이블에 만든다.
- 생성 SQL에서 PK, 각 필드의 nullability, ISBN13 유일성, CHECK 제약과 보조 index를 확인한다.
- forward migration 후 모델 테스트를 실행하고, 격리된 개발/test database에서 reverse 후
  다시 forward하여 migration 왕복을 검증한다.
- 신규 빈 테이블에 대한 초기 생성이므로 concurrent index와 `lock_timeout`은 필요하지
  않다. 향후 기존 Book 테이블을 변경할 때는 별도 migration 안전성 검토를 수행한다.
- reverse SQL은 Book 테이블을 삭제하므로 운영 롤백 수단으로 사용하지 않고 데이터가 없는
  격리 환경에서만 검증한다.

## 제외 범위

- Work/Edition 별도 엔터티
- Author 또는 Publisher 엔터티
- Provider 원본 JSON 및 Provider별 외부 ID
- Metadata 갱신, 병합, 충돌 해결과 이력
- 공개 ID
- API, Form, Template 및 관리자 화면
