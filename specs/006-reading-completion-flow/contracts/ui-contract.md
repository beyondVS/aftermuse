# UI Contract: Reading 진입 및 상세

## 주소와 Method

| 이름 | Method | 목적 | 성공 결과 |
| --- | --- | --- | --- |
| `readings:book_entry` | GET | Book의 현재 사용자 Reading 상태 확인 | 상태 선택, 활성 상세 또는 최근 완독 상세 |
| `readings:create` | POST | 이력 없는 Book의 첫 Reading 생성 | Reading 상세로 redirect |
| `readings:detail` | GET | 소유 Reading의 최소 상세 표시 | 전체 HTML |
| `readings:reread` | POST | 완독 Reading에서 명시적 재독 생성 | 새/기존 활성 Reading 상세로 redirect |
| `readings:change_state` | POST | 상태 또는 완독일 변경 | 갱신 panel 또는 전체 상세 |

구체적인 path는 명명된 URL로만 참조하며 Template과 View에서 하드코딩하지 않는다.

## Book 선택 연결

- `books:select` 성공은 `readings:book_entry`로 이동한다.
- 일반 POST는 HTTP redirect를 반환한다.
- HTMX POST는 같은 전체 페이지 URL을 `HX-Redirect`로 제공한다.
- 선택 실패·후보 만료는 기존 Book 검색 오류 계약을 유지한다.

## Book-entry 상태

| 서버 상태 | 표시 | 허용 행동 | 영속 변화 |
| --- | --- | --- | --- |
| Reading 이력 없음 | Book 정보, 세 초기 상태, 완독일 입력 | 상태 선택 후 생성 | 명시적 POST에서만 1건 생성 |
| 활성 Reading 있음 | 현재 상태와 `계속 보기` | 기존 상세 열기 | 없음 |
| 완독 Reading만 있음 | 가장 최근 완독 정보, `다시 읽기` | 재독 상태 선택 후 생성 | 명시적 POST에서만 새 1건 |
| Book 없음 | 안전한 찾을 수 없음 안내 | 검색으로 돌아가기 | 없음 |

초기 또는 재독 상태로 `완독`을 선택하면 오늘을 기본값으로 한 완독일 입력이 필수다.
일반 Form POST를 서버 동작의 정본으로 유지하고 HTMX와 Alpine.js는 응답 교체와 필드 표시를
점진적으로 향상한다. JavaScript 비활성 브라우저를 별도의 제품 지원·인수시험 대상으로
규정하지 않는다.

## Reading 상세

항상 표시:

- 제목, 제공되는 경우 표지·저자·출판사·출간 정보
- 현재 독서 상태
- 상태 변경 Form
- 검색으로 돌아가기

완독 상태에서 추가 표시:

- 완독일과 Interview 시작 전 수정 Form
- `AI 독서노트 만들기` CTA
- `다시 읽기`와 재독 초기 상태 선택

Day 04의 CTA는 설명과 함께 비활성이다. 링크처럼 동작하지 않으며 `disabled` 또는
`aria-disabled=true`로 보조 기술에도 상태를 전달한다. Day 05가 같은 위치를 실제 시작
주소에 연결한다.

## 상태 변경 결과

| 결과 | HTTP/화면 계약 |
| --- | --- |
| 성공 | 현재 상태, 완독일과 다음 행동이 갱신됨 |
| 유효하지 않은 상태/날짜 | 400 계열 Form 오류, 입력 보존, 영속 변화 없음 |
| 다른 활성 Reading과 충돌 | 기존 값 유지, 활성 Reading으로 이동 가능한 안내 |
| Interview 잠금 | 기존 값 유지, 변경 불가 이유 안내 |
| 다른 사용자/없는 Reading | 동일한 404 응답으로 존재 여부 비노출 |
| 예상하지 못한 DB 실패 | 내부 상세 없는 오류와 재시도, 이전 값 보존 |

일반 요청은 전체 상세를, HTMX 요청은 동일 정보를 담은 `_reading_panel.html` Fragment를
반환한다. 오류 의미와 Form 값은 두 응답 방식에서 동일하다.

## 보안 및 접근성

- 모든 화면은 로그인 필수이며 Reading 조회는 `user=request.user` 범위에서 수행한다.
- 생성·재독·상태 변경은 POST와 CSRF를 요구한다.
- client가 보낸 user ID, 소유권 또는 Book metadata를 신뢰하지 않는다.
- Django Template auto-escape를 유지하고 외부 Book 문자열에 `safe`를 사용하지 않는다.
- 상태 Form은 `fieldset`/`legend`, 각 입력의 label, 날짜 오류 연결을 제공한다.
- 성공은 `aria-live=polite`, 입력 오류는 해당 field와 연결된 `role=alert`로 전달한다.
- 현재 상태, 비활성 CTA와 오류는 색상만이 아니라 텍스트·속성으로 구분한다.
- 375px와 1280px에서 가로 scroll 없이 Tab/Shift+Tab/Enter/Space로 흐름을 완료한다.
- 상태 변경 후 focus는 갱신 panel의 제목 또는 결과 메시지로 이동한다.
