# Contract: Book Search Screen

## 사용자 접근 계약

| 항목 | 계약 |
| --- | --- |
| 주소 | `/books/search/` |
| 이름 | `books:search` |
| 방식 | 읽기 전용 GET |
| 인증 | 로그인한 사용자만 접근 가능; 익명 사용자는 기존 로그인 흐름으로 이동 |
| 입력 | 선택적 query parameter `q` |

## 입력 계약

- `q` parameter가 없으면 검색 전 전체 화면을 제공한다.
- `q`는 양끝 공백을 제거한 뒤 1자 이상 200자 이하여야 한다.
- 빈 값, 공백만 있는 값 또는 200자 초과는 입력 오류를 표시하고 Provider factory와 검색
  Service를 호출하지 않는다.
- 유효한 `q`는 Provider factory로 만든 Provider와 함께 기존 `search_books()`에 정확히 한
  번 전달한다.
- 현재 입력 또는 정규화된 검색어는 Form에 유지한다.

## 응답 형태 계약

| 요청 | 응답 |
| --- | --- |
| 일반 browser 요청 | 공통 layout, 제목, 검색 영역을 포함한 전체 HTML 문서 |
| HTMX 요청 | Form, Loading, 입력 오류 및 현재 결과 상태를 포함한 검색 영역 Fragment |

두 응답은 같은 상태와 내용을 제공한다. HTMX 응답은 전체 문서 구조를 중복하지 않으며 검색
영역의 바깥 요소를 교체한다. Form은 현재 주소를 갱신하고, 진행 중인 동일 Form 요청을 새
요청으로 교체한다.

## 화면 상태 계약

| 조건 | 표시 상태 | 필수 내용 |
| --- | --- | --- |
| `q` 없음 | Normal/Initial | 이름 있는 검색 입력과 실행 버튼; Empty/Error 미표시 |
| Form invalid | Input Error | field error; Provider 호출 없음 |
| 유효한 요청 진행 중 | Loading | 이전 결과 숨김, 텍스트 진행 안내, live status |
| `BookSearchStatus.SUCCESS` | Success | 검색어와 전체 도서 결과 목록 |
| `BookSearchStatus.EMPTY` | Empty | 결과 없음과 검색어 변경 안내 |
| `BookSearchStatus.ERROR` | Error | 일반 실패 안내와 같은 검색 재시도 행동 |

Provider 실패 화면과 HTML에는 Provider 이름, 예외 유형, credential, 원본 응답 또는 진단
메시지를 포함하지 않는다. Empty와 Error를 서로 다른 제목과 설명으로 구분한다.

## 결과 항목 계약

- 결과는 Provider의 tuple 순서를 보존하고 전부 표시한다.
- 각 항목은 제목을 항상 표시한다.
- 표지, 저자, 출판사와 출간연도는 원본 값이 있을 때만 표시한다.
- 출간연도는 전체 출간일의 연도에서 파생하며 값이 없으면 추측하지 않는다.
- 표지 URL이 없으면 텍스트 대체 표현을 표시한다.
- 표지 image에는 도서 제목을 포함한 대체 텍스트와 layout을 유지하는 고정 영역이 있다.
- 긴 제목·저자·출판사는 다른 결과와 겹치거나 페이지 가로 scroll을 만들지 않는다.
- 도서 선택·저장, 외부 상세 링크, Reading 및 Knowledge 행동을 제공하지 않는다.

## 접근성과 반응형 계약

- 페이지는 단일 명확한 최상위 제목을 가진다.
- 검색 입력은 보이는 label과 연결되고 오류 설명을 식별할 수 있다.
- 검색, 재시도 및 navigation은 키보드로 조작 가능하고 `focus-visible` 표시가 있다.
- 상태 영역은 의미 있는 heading과 텍스트를 사용하며 색상에만 의존하지 않는다.
- Loading과 완료 상태 변경은 보조 기술이 인식할 수 있는 live region에서 제공한다.
- 375px Mobile과 1280px Desktop에서 page-level 가로 scroll 없이 정보가 표시된다.

## Side effect 계약

- 검색 결과를 local storage, session 또는 database에 저장하지 않는다.
- Book, Reading 또는 Book Knowledge를 조회·생성·변경하지 않는다.
- retry, cache, fallback 또는 여러 Provider 결과 병합을 추가하지 않는다.
- 실제 외부 호출은 View 테스트에서 Provider factory를 대체해 차단한다.
