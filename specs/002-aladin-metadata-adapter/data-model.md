# Data Model: 알라딘 Metadata Provider Adapter

이 기능은 영속 모델이나 migration을 추가하지 않는다. 아래 값과 오류는 외부 Provider
경계의 불변 애플리케이션 계약이다.

## ProviderBook

| 필드 | Python 타입 | 필수 | 검증/정규화 |
| --- | --- | --- | --- |
| `isbn13` | `str` | 예 | ASCII 숫자 13자리, 위반 시 항목 제외 |
| `title` | `str` | 예 | trim 후 비어 있지 않음, 위반 시 항목 제외 |
| `authors` | `str` | 아니요 | 문자열 trim 또는 `""` |
| `publisher` | `str` | 아니요 | 문자열 trim 또는 `""` |
| `published_date` | `date \| None` | 아니요 | ISO 날짜 또는 `None` |
| `cover_url` | `str` | 아니요 | 문자열 trim 또는 `""` |
| `description` | `str` | 아니요 | 문자열 trim 또는 `""` |
| `table_of_contents` | `str` | 아니요 | `subInfo.toc` trim 또는 `""` |
| `external_url` | `str` | 아니요 | 문자열 trim 또는 `""` |

`ProviderBook`은 `dataclass(frozen=True, slots=True)`다. 선택값을 추측하지 않으며 로컬
`books.Book`과 동일 객체가 아니고 검색만으로 영속화하지 않는다.

## BookMetadataProvider

```text
search(query: str) -> tuple[ProviderBook, ...]
```

- 유효 결과는 Provider 순서를 보존한다.
- 정상 무결과 또는 모든 개별 항목이 무효면 빈 tuple이다.
- 전체 응답을 해석할 수 없으면 부분 결과가 아니라 오류다.

## Transport

```text
transport(url: str, timeout: float) -> bytes
```

URL에는 percent-encoding된 요청 값이 있고 timeout은 양의 초 단위다. 반환 bytes는
UTF-8 JSON으로 해석하며 timeout/I/O 예외는 Provider 오류로 변환한다.

## Provider 오류 계층

```text
ProviderError
├── ProviderConfigurationError
├── ProviderTimeoutError
├── ProviderUnavailableError
└── ProviderResponseError
```

| 오류 | 발생 조건 | 외부 호출 |
| --- | --- | --- |
| `ProviderConfigurationError` | TTB key 없음 | 없음 |
| `ProviderTimeoutError` | `TimeoutError` 또는 `socket.timeout` | 시도됨 |
| `ProviderUnavailableError` | network/HTTP 실패 또는 Provider 오류 payload | 시도됨 |
| `ProviderResponseError` | JSON/최상위/item 구조 손상 | 시도됨 |

오류는 TTB key와 원본 응답 본문을 포함하지 않는다.

## 상태 흐름

```text
검색 요청
  ├─ key 누락 ─────────────────────────────> ConfigurationError
  └─ key 있음 → transport
                ├─ timeout ─────────────────> TimeoutError
                ├─ network/HTTP 실패 ───────> UnavailableError
                └─ bytes → JSON/구조 검증
                           ├─ Provider 오류 ─> UnavailableError
                           ├─ 구조 손상 ─────> ResponseError
                           └─ item 변환 ─────> tuple[ProviderBook, ...]
```

DB 관계, index, migration은 없다. IMP-022가 Provider 계약을 소비하고 IMP-024가 저장을
담당한다.
