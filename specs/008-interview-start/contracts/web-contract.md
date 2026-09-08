# Web 계약: 인터뷰 시작과 재진입

## 공통 원칙

- 모든 경로는 인증이 필요하고 객체는 `request.user` 소유 범위에서 조회한다.
- 미존재와 비소유는 동일한 404로 처리해 metadata와 존재 여부를 노출하지 않는다.
- 일반 HTML GET/POST가 정본이며 JavaScript 없이 완료할 수 있다.
- 상태 변경은 CSRF 보호 POST에서만 수행한다.

## GET `/reflections/readings/<reading_id>/start/`

**이름**: `reflections:interview_start`

### 신규 Interview가 없는 완독 Reading

- 200과 책 최종 확인 화면을 반환한다.
- 표지, 제목, 저자, 출판사, 출간일, ISBN13 중 확보된 정보만 표시한다.
- `인터뷰를 시작하면 다른 책으로 변경할 수 없습니다.`를 시작 전에 텍스트로 표시한다.
- `READY_LIMITED`에서만 기억에 남은 내용부터 정리한다는 안내를 표시한다.
- `책 다시 선택`은 `books:search` link이고, `인터뷰 시작`은 confirm POST form의 유일한 primary action이다.

### 기존 Interview 또는 거부 상태

- 기존 `IN_PROGRESS` Interview는 확인 화면 없이 `reflections:interview_detail`로 redirect한다.
- `REFLECTION_READY`/`COMPLETED`는 Service destination 계약으로 목적지를 판정하되, 실제
  Reflection route가 없는 동안 409와 현재 단계를 아직 사용할 수 없다는 상태별 안내를
  반환한다. 새 Interview를 만들거나 존재하지 않는 URL을 reverse하지 않는다.
- 미인증은 로그인 redirect, 비소유/미존재는 404다.
- 미완독은 Interview 0건을 유지하고 Reading 상세에서 완독 필요를 안내한다.

## POST `/reflections/readings/<reading_id>/start/confirm/`

**이름**: `reflections:interview_create`

- CSRF token과 URL reading_id만 경계 입력으로 사용하고 POST에서 소유권·완독을 재검증한다.
- 성공하면 신규/기존 `IN_PROGRESS` Interview의 detail로 redirect한다.
- 기존 Interview가 `REFLECTION_READY`/`COMPLETED`이면 새 Interview 없이 상태별 409 안내를
  반환하며 실제 Reflection route 연결은 후속 Bundle에서 완성한다.
- 반복·동시 POST는 같은 Interview로 수렴하고 신규 Interview는 Turn 0개이며 Credit 변경은 없다.
- CSRF 없음은 403, 비소유/미존재는 404다.
- 정책 충돌은 400 확인 화면 또는 Reading 상세 안내를 반환한다.
- DB 실패는 내부 오류를 숨긴 재시도 안내를 제공하며 부분 Interview 0건과 Reading 불변을 보장한다.

## GET `/reflections/interviews/<interview_id>/`

**이름**: `reflections:interview_detail`

- 소유자 범위 Interview만 조회한다.
- `IN_PROGRESS`에서 Book, readiness와 첫 질문이 아직 없을 수 있는 유효한 시작 상태를 표시한다.
- 첫 질문/답변 form, Coverage, Soft Stop과 Reflection 내용은 만들지 않는다.
- 다른 status는 destination resolver를 거쳐 후속 named route가 연결된 뒤 해당 단계로 redirect한다.
- 후속 named route가 연결되기 전 `REFLECTION_READY`/`COMPLETED` 접근은 상태별 409 안내를
  반환하며 내부 status나 구현 세부정보를 노출하지 않는다.

## 접근성 및 반응형 계약

- 페이지당 하나의 `<h1>`과 label이 있는 Book 정보 section을 사용한다.
- 변경 불가, 제한과 오류를 색상만이 아닌 텍스트로 제공한다.
- 실제 `<a>`/`<button>`, visible focus, 오류의 `role="alert"`와 focus 이동을 사용한다.
- 제출 상태는 `aria-busy`로 표현할 수 있으나 일반 POST를 대체하지 않는다.
- 375px와 1280px에서 가로 scroll 없이 책 정보, 안내와 행동을 사용할 수 있어야 한다.
