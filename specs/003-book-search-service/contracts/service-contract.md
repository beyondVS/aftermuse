# Contract: Book Search Service

## 공개 Python 계약

```python
class BookSearchStatus(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BookSearchResult:
    status: BookSearchStatus
    books: tuple[ProviderBook, ...]


def search_books(
    query: str,
    provider: BookMetadataProvider,
) -> BookSearchResult: ...
```

`BookMetadataProvider`와 `ProviderBook`은 IMP-021의 Provider 중립 계약을 재사용한다.

## 입력 계약

- `query`의 양끝 공백을 제거한 문자열을 Provider에 전달한다.
- query 내부의 문자와 공백은 변경하지 않는다.
- 정규화 후 빈 query는 Provider를 호출하지 않는다.
- 유효한 query는 Provider의 `search()`에 정확히 한 번 전달한다.

검색어 길이와 허용 문자 검증은 IMP-023 입력 경계의 책임이며 이 Service는 추가 변환하지
않는다.

## 반환 계약

| 조건 | `status` | `books` |
| --- | --- | --- |
| Provider가 1건 이상 반환 | `SUCCESS` | 반환된 tuple을 순서대로 보존 |
| Provider가 정상 빈 tuple 반환 | `EMPTY` | `()` |
| query가 정규화 후 빈 문자열 | `EMPTY` | `()` |
| Provider가 `ProviderError` 발생 | `ERROR` | `()` |

- `SUCCESS`와 빈 `books`의 조합은 허용하지 않는다.
- `EMPTY` 또는 `ERROR`와 비어 있지 않은 `books`의 조합은 허용하지 않는다.
- 전체 출간일을 포함한 모든 `ProviderBook` 필드는 변경하지 않는다.
- 결과에는 자격 증명, 원본 오류 본문, 예외 객체 또는 내부 진단 메시지를 포함하지 않는다.

## 오류 경계

다음 기존 예외는 모두 안전한 `ERROR` 결과로 변환한다.

- `ProviderConfigurationError`
- `ProviderTimeoutError`
- `ProviderUnavailableError`
- `ProviderResponseError`

이 예외들의 공통 기반인 `ProviderError`를 경계로 사용한다. `ProviderError`가 아닌 예외는
프로그래밍 결함을 숨기지 않도록 포착하지 않는다.

## Side effect 계약

- `Book`을 조회, 생성 또는 변경하지 않는다.
- 검색 결과를 cache하지 않는다.
- Provider retry나 fallback 호출을 수행하지 않는다.
- 유효한 검색 한 번당 Provider 호출은 한 번을 초과하지 않는다.
- Service는 HTTP 요청·응답 및 화면 표현에 의존하지 않는다.
