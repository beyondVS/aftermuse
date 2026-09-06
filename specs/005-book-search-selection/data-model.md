# Data Model: 도서 검색 복구 및 선택

새 도메인 table이나 migration은 추가하지 않는다. 기존 `Book`과 Django session을 사용한다.

## ProviderBook

정본은 `integrations.book_metadata`에 둔다.

| 필드 | 타입 | 규칙 |
| --- | --- | --- |
| `isbn13` | `str` | 필수, ASCII 숫자 13자리 |
| `title` | `str` | 필수, trim 후 비어 있지 않음 |
| `authors` | `str` | 저자 배열의 유효 항목을 `, `로 연결 |
| `publisher` | `str` | 누락 시 빈 문자열 |
| `published_date` | `date \| None` | ISO datetime의 날짜, 해석 불가 시 `None` |
| `cover_url` | `str` | `thumbnail`, 누락 시 빈 문자열 |
| `description` | `str` | `contents`, 누락 시 빈 문자열 |
| `table_of_contents` | `str` | Kakao 미제공이므로 빈 문자열 |
| `external_url` | `str` | Kakao 상세 URL |

필수값이 무효인 document만 제외하고 유효 결과 순서는 보존한다.

## BookSelectionCandidate

최신 성공 검색 결과를 session에 일시 보관하는 JSON 값이다.

| 필드 | 저장 형태 | 규칙 |
| --- | --- | --- |
| `candidate_id` | 문자열 | 예측하기 어려운 batch 내 unique ID |
| `owner_user_id` | 문자열 | 검색 당시 사용자 PK |
| `created_at` | 숫자 | UTC Unix timestamp |
| `isbn13`, `title` | 문자열 | 필수 Book 값 |
| 선택 Metadata | 문자열 또는 null | ProviderBook 값을 JSON 형태로 보존 |

- 최신 batch 최대 20건, TTL 15분이다.
- 새 유효 검색 시작 시 기존 batch를 제거하며 Empty/Error도 후보를 남기지 않는다.
- 조회 시 후보 ID, 현재 사용자 PK와 TTL을 검증한다.
- client가 보낸 ISBN13이나 Metadata는 병합하지 않는다.

## Book과 선택 결과

기존 `books.Book` schema와 ISBN13 unique/CHECK 제약을 유지한다. 새 ISBN13이면 candidate의
서지정보로 생성하고, 기존 ISBN13이면 어떤 필드도 갱신하지 않고 기존 instance를 반환한다.

`BookSelectionResult`는 `book: Book`과 `created: bool`을 갖는 불변 결과다. 후보 없음·만료·
소유자 불일치는 후보 조회 오류이며 Book 변경 전에 끝난다.

## 상태 전이

```text
유효 검색 시작 → 기존 후보 제거
  ├─ SUCCESS → 최대 20개 ACTIVE 후보
  ├─ EMPTY ──> 후보 없음
  └─ ERROR ──> 후보 없음

ACTIVE 후보
  ├─ 15분 경과/다른 사용자 → 선택 거부, Book 변경 없음
  └─ 현재 사용자 POST
       ├─ ISBN13 존재 → 기존 Book (`created=false`)
       └─ ISBN13 없음 → 새 Book (`created=true`)
```

성공 후보는 TTL까지 유지해 반복 POST가 같은 Book을 반환한다. Reading과 Book Knowledge는
생성하지 않는다.
