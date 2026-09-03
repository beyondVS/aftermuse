# Contract: Book Metadata Provider

## 공개 Python 계약

```python
class BookMetadataProvider(Protocol):
    def search(self, query: str) -> tuple[ProviderBook, ...]: ...
```

- 정상 무결과는 `()`다.
- 반환 순서는 Provider 순서를 유지한다.
- 각 항목은 ASCII 13자리 ISBN13과 비어 있지 않은 제목을 가진다.
- 선택값은 제공된 사실만 보존하고 누락/해석 불가는 빈 문자열 또는 `None`이다.

| 공개 예외 | 의미 |
| --- | --- |
| `ProviderConfigurationError` | 설정 없음, transport 호출 전 발생 |
| `ProviderTimeoutError` | 제한시간 초과, 일반 통신 실패와 별도 타입 |
| `ProviderUnavailableError` | network/HTTP/Provider 오류 |
| `ProviderResponseError` | 응답 형식 또는 구조 해석 실패 |

모두 `ProviderError`를 상속하며 credential과 원본 응답 본문을 노출하지 않는다.

## Aladin ItemSearch outbound 계약

**Method**: `GET`
**Endpoint**: `https://www.aladin.co.kr/ttb/api/ItemSearch.aspx`
**응답**: JSON bytes

| Query parameter | 값/출처 |
| --- | --- |
| `ttbkey` | 생성 시 주입된 TTB key |
| `Query` | `search()` 검색어 |
| `QueryType` | `Keyword` |
| `MaxResults` | `20` |
| `start` | `1` |
| `SearchTarget` | `Book` |
| `output` | `js` |
| `Version` | `20131101` |

모든 값은 `urlencode`로 encoding하고 구성한 timeout을 transport에 전달한다.

## 응답 매핑

| Aladin JSON | ProviderBook |
| --- | --- |
| `item[].isbn13` | `isbn13` |
| `item[].title` | `title` |
| `item[].author` | `authors` |
| `item[].publisher` | `publisher` |
| `item[].pubDate` | `published_date` |
| `item[].cover` | `cover_url` |
| `item[].description` | `description` |
| `item[].subInfo.toc` | `table_of_contents` |
| `item[].link` | `external_url` |

최상위 `errorCode`는 `ProviderUnavailableError`, JSON object가 아니거나 `item`이 list가
아니면 `ProviderResponseError`다. item이 object가 아니면 전체 구조 오류이며, object의
ISBN13/제목만 무효면 해당 item만 제외한다.

## 기본 factory와 자동 검증

`get_default_provider()`는 `settings.ALADIN_TTB_KEY`로 기본 Provider를 만든다. key가
비어 있으면 생성은 가능하지만 `search()`가 호출 전에 설정 오류를 낸다.

테스트는 fake transport로 URL/timeout을 기록하고 bytes 또는 예외를 제공한다. 기본
transport, 실제 알라딘 endpoint 및 `books.Book` 저장을 호출하지 않는다.
