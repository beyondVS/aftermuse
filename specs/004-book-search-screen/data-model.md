# Data Model: 도서 검색 화면

이 기능은 database entity나 migration을 추가하지 않는다. 아래 항목은 요청 및 화면 표시
동안만 존재하며 검색 결과를 영속화하지 않는다.

## BookSearchForm 입력

| 항목 | 원본 | 유효 조건 | 정규화·오류 |
| --- | --- | --- | --- |
| `q` | query parameter 문자열 | trim 후 1~200자 | 양끝 공백 제거; 빈 값과 200자 초과는 입력 오류 |

query parameter 자체가 없으면 Form은 검색 전 상태다. parameter가 있지만 검증에 실패하면
Provider를 만들거나 검색하지 않고 입력값과 field error를 표시한다. 허용 문자 종류는
제한하지 않으며 Template 출력 시 기본 escaping을 유지한다.

## SearchScreen 렌더링 상태

| 상태 | 발생 조건 | 표시 데이터 | 가능한 다음 행동 |
| --- | --- | --- | --- |
| `INITIAL` | `q` parameter 없음 | 빈 Form | 검색어 입력·검색 |
| `INPUT_ERROR` | Form이 빈 값·공백 또는 200자 초과를 거부 | 입력값과 field error | 입력 수정·검색 |
| `LOADING` | 유효한 검색 요청 진행 중 | 정규화 전 현재 입력과 진행 텍스트 | 최신 요청 완료 대기 |
| `SUCCESS` | Service가 1건 이상 반환 | 정규화된 검색어와 전체 도서 tuple | 결과 비교·새 검색 |
| `EMPTY` | Service가 정상 무결과 반환 | 정규화된 검색어와 Empty 안내 | 검색어 변경·검색 |
| `ERROR` | Service가 Provider 실패를 격리 | 정규화된 검색어와 일반 오류 안내 | 같은 검색 재시도·검색어 변경 |

`LOADING`은 browser의 일시 상태이며 새 검색 시작 시 이전 결과를 즉시 숨긴다. 완료 응답이
검색 영역 전체를 교체하며 진행 중인 이전 요청은 최신 요청으로 대체된다.

## 표시용 도서 결과

별도 DTO를 만들지 않고 IMP-021의 기존 `ProviderBook`을 읽기 전용으로 사용한다.

| 원본 필드 | 화면 표시 | 규칙 |
| --- | --- | --- |
| `isbn13` | 결과 식별용 값 | 표시·테스트 식별에 사용하며 변경하지 않음 |
| `title` | 제목 | 항상 표시 |
| `authors` | 저자 | 값이 있을 때만 표시 |
| `publisher` | 출판사 | 값이 있을 때만 표시 |
| `published_date` | 출간연도 | 값이 있을 때 `.year`만 파생 표시 |
| `cover_url` | 표지 | 값이 있으면 image, 없으면 텍스트 대체 표현 |
| 나머지 Metadata | 표시하지 않음 | 객체에는 보존되며 이번 목록 화면에서 추측·변형하지 않음 |

모든 결과는 Provider 순서를 유지해 한 목록에 표시한다. Pagination, 더 보기, 선택 상태,
Book 저장 key, Reading 관계와 Book Knowledge 상태는 없다.

## 상태 전이

```text
GET (q 없음) ───────────────────────────────> INITIAL

검색 실행
  ├─ trim 후 빈 값 또는 200자 초과 ────────> INPUT_ERROR
  └─ 유효한 q ─────────────────────────────> LOADING
       ├─ 1건 이상 ────────────────────────> SUCCESS
       ├─ 정상 0건 ────────────────────────> EMPTY
       └─ Provider 실패 ───────────────────> ERROR

SUCCESS / EMPTY / ERROR / INPUT_ERROR
  └─ 새 유효 검색 ── 이전 표시 숨김 ───────> LOADING
```

어떤 전이도 Book, Reading, Knowledge 또는 cache를 생성·조회·변경하지 않는다.
