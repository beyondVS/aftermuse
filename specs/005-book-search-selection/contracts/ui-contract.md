# Contract: 도서 검색 및 선택 화면

| 이름 | 방식 | 주소 | 역할 |
| --- | --- | --- | --- |
| `books:search` | GET | `/books/search/` | 기존 검색과 session 후보 생성 |
| `books:select` | POST | `/books/select/` | 후보 ID로 Book 선택·등록 |

두 주소는 로그인 필수이고 선택 Form은 CSRF 보호를 유지한다.

## 검색 결과

기존 Initial/Input Error/Loading/Success/Empty/Error와 전체/HTMX Fragment 계약을 유지한다.
각 성공 결과는 기존 판본 정보, 책을 구분하는 접근 가능한 선택 버튼, CSRF token과 hidden
`candidate_id`만 제공한다. ISBN13과 Metadata hidden field는 제공하지 않는다. 새 유효 검색은
이전 표시와 후보를 모두 무효화한다.

## 선택 결과

| 조건 | 표시 | Book 변경 |
| --- | --- | --- |
| 신규 후보 | 선택·신규 등록 완료, Book 정보, 다른 책 선택 | 1건 생성 |
| 기존 ISBN13 | 선택 완료, Book 정보, 다른 책 선택 | 기존 1건 재사용 |
| 없음·만료·소유자 불일치/Form 오류 | 재검색 안내 | 없음 |
| DB/예상 실패 | 안전한 실패와 재시도/재검색 | 부분 변경 없음 |

HTMX는 검색 영역을 대체하는 Fragment, 일반 POST는 같은 결과를 포함한 전체 HTML을 반환한다.
Reading, Interview, Knowledge 상태와 외부 상세 링크는 제공하지 않는다. JavaScript 없이
동작하고 375px/1280px에서 가로 scroll 없이 키보드와 보조 기술로 상태를 구분할 수 있어야 한다.
