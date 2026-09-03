# Data Model: 도서 검색 Service와 결과 정규화

이 기능은 database entity나 migration을 추가하지 않는다. 아래 타입은 검색 요청 한 번의
수명 동안만 존재하는 불변 애플리케이션 계약이다.

## BookSearchStatus

| 값 | 의미 | 도서 목록 |
| --- | --- | --- |
| `SUCCESS` | 한 건 이상의 유효한 도서가 반환됨 | 1건 이상 |
| `EMPTY` | 공백 검색어이거나 정상 검색 결과가 없음 | 빈 tuple |
| `ERROR` | Provider가 검색을 완료하지 못함 | 빈 tuple |

세 값은 상호 배타적이다. Provider의 configuration, timeout, unavailable, response 오류는
외부 소비자에게 모두 `ERROR`로 보이며 구체 오류나 메시지를 상태에 포함하지 않는다.

## BookSearchResult

| 필드 | 타입 | 필수 | 불변조건 |
| --- | --- | --- | --- |
| `status` | `BookSearchStatus` | 예 | 허용된 세 상태 중 정확히 하나 |
| `books` | `tuple[ProviderBook, ...]` | 예 | `SUCCESS`이면 1건 이상, 그 외에는 빈 tuple |

결과 객체는 불변이며 검색 간 공유 상태를 가지지 않는다. `books`는 Provider가 반환한 순서와
객체를 보존한다.

## ProviderBook 참조

IMP-021에서 정의한 기존 불변 값 객체를 그대로 사용한다.

| 필드 | 타입 | Service 처리 |
| --- | --- | --- |
| `isbn13` | `str` | 그대로 보존 |
| `title` | `str` | 그대로 보존 |
| `authors` | `str` | 그대로 보존 |
| `publisher` | `str` | 그대로 보존 |
| `published_date` | `date \| None` | 전체 날짜를 보존; 연도는 후속 화면에서 파생 |
| `cover_url` | `str` | 그대로 보존 |
| `description` | `str` | 그대로 보존 |
| `table_of_contents` | `str` | 그대로 보존 |
| `external_url` | `str` | 그대로 보존 |

Service는 필수값을 다시 검증하거나 선택값을 추측하지 않는다. 이 검증과 정규화는 Provider
Adapter 계약의 책임이다.

## 검색 요청과 상태 전이

별도 요청 객체를 만들지 않고 입력 문자열을 호출 범위에서 정규화한다.

```text
원본 검색어
  └─ 양끝 공백 제거
      ├─ 빈 문자열 ─────────────────────────> EMPTY + ()
      └─ 유효 문자열 → Provider 1회 호출
                        ├─ 1건 이상 ─────────> SUCCESS + ProviderBook tuple
                        ├─ 정상 0건 ─────────> EMPTY + ()
                        └─ ProviderError ─────> ERROR + ()
```

DB 관계, key, index, lifecycle persistence 및 migration은 없다. 검색 결과를 `Book`으로
저장하거나 재사용하는 작업은 IMP-024의 책임이다.
