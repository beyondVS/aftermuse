# Contract: Book Metadata Provider와 Kakao Adapter

## 중립 계약

```python
class BookMetadataProvider(Protocol):
    def search(self, query: str) -> tuple[ProviderBook, ...]: ...
```

- 정본은 `integrations.book_metadata.contracts`, legacy Aladin 경로는 re-export다.
- 정상 무결과는 `()`, 순서는 Provider 순서를 유지한다.
- 각 항목은 ASCII 13자리 ISBN13과 비어 있지 않은 제목을 가진다.
- `ProviderConfigurationError`, `ProviderTimeoutError`, `ProviderUnavailableError`,
  `ProviderResponseError`는 공통 `ProviderError`를 상속하고 secret·원본 본문을 노출하지 않는다.

## Kakao outbound 계약

| 항목 | 값 |
| --- | --- |
| Method/Endpoint | `GET https://dapi.kakao.com/v3/search/book` |
| Header | `Authorization: KakaoAK {KAKAO_REST_API_KEY}` |
| Parameters | `query`, `sort=accuracy`, `page=1`, `size=20` |
| Timeout | 3초 |

key는 URL·HTML·일반 로그에 포함하지 않는다. 빈 key는 transport 전에 설정 오류다.

## 응답 매핑

| Kakao | ProviderBook | 규칙 |
| --- | --- | --- |
| `isbn` | `isbn13` | 공백 token 중 ASCII 13자리 |
| `title` | `title` | trim, 필수 |
| `authors` | `authors` | 문자열 배열을 `, `로 연결 |
| `publisher` | `publisher` | trim |
| `datetime` | `published_date` | ISO date, 오류는 `None` |
| `thumbnail` | `cover_url` | trim |
| `contents` | `description` | trim |
| 미제공 | `table_of_contents` | 빈 문자열 |
| `url` | `external_url` | trim |

최상위 object와 `documents` list가 아니면 응답 오류다. document 구조 오류는 전체 실패,
필수값만 무효면 해당 항목만 제외한다. timeout은 별도 오류, network/HTTP/quota는 unavailable
오류로 변환하며 예상하지 못한 프로그래밍 오류는 숨기지 않는다.
