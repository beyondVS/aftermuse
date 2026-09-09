# Web 계약: 첫 질문과 답변 저장

## 공통 원칙

- 모든 route는 인증이 필요하고 `Interview → Reading → request.user` 범위로 조회한다.
- 비소유와 미존재는 동일한 404로 처리한다.
- 일반 HTML form이 정본이고 HTMX는 같은 POST를 점진적으로 향상한다.
- mutation과 Provider 호출은 CSRF 보호 POST에서만 수행한다.
- HTMX 응답은 `#interview-turn-region` 전체를 교체한다.

## GET `/reflections/interviews/<interview_id>/`

**이름**: `reflections:interview_detail`

- 기존 소유자/상태/관계 검증을 유지한다.
- sequence 1이 없으면 Book 정보, Loading region과 `첫 질문 준비하기` fallback POST form을
  반환한다. HTMX는 page load 후 해당 form을 자동 제출한다.
- 미응답 Turn이 있으면 질문과 answer form을 반환한다.
- 답변된 Turn이 있으면 확정 원문과 저장 완료 상태를 반환하고 수정/다음 질문 action은 표시하지
  않는다.
- GET 자체는 Provider를 호출하거나 Turn/answer를 변경하지 않는다.

## POST `/reflections/interviews/<interview_id>/questions/first/`

**이름**: `reflections:first_question`

- 기존 first Turn은 Provider 호출 없이 재사용한다.
- 없으면 `ensure_first_question`을 호출한다.
- HTMX 성공은 200 question fragment, 일반 POST 성공은 detail redirect다.
- timeout/Provider/invalid output은 503과 같은 화면의 `role="alert"` Error fragment 및 재시도
  form을 반환한다. Interview/Turn 기존 데이터는 유지한다.
- policy/관계/status 충돌은 409, 비소유/미존재는 404, method 불일치는 405다.

## POST `/reflections/interviews/<interview_id>/turns/1/answer/`

**이름**: `reflections:first_answer`

- CSRF 보호 Answer form의 `answer`만 입력받는다.
- 공백 또는 2,000자 초과는 400과 bound textarea/error를 반환하고 저장하지 않는다.
- 최초 성공은 answer를 저장하고 HTMX에는 200 saved fragment, 일반 POST에는 detail redirect를
  반환한다. 다음 질문 준비 상태나 action을 표시하지 않는다.
- 동일 answer 재제출은 동일한 성공 상태다.
- 다른 answer 재제출은 409와 이미 확정된 원문을 반환하며 변경 action을 제공하지 않는다.
- DB 실패는 안전한 재시도 응답과 bound input을 반환하고 answer를 확정하지 않는다.

## Loading·접근성·입력 보존 계약

- Loading region은 `aria-busy="true"`와 화면에 보이는 준비 문구를 제공한다.
- Error는 `role="alert"`, focus target과 실제 retry button을 제공한다.
- question에는 heading을, textarea에는 연결된 label/help/error를 제공한다.
- 제출 중 button 중복 활성화를 막되 일반 form fallback을 유지한다.
- 저장 실패/validation 오류 fragment는 제출된 answer 값을 textarea에 그대로 유지한다.
- 실제 button/link는 keyboard로 조작 가능하고 focus style과 색상 외 상태 문구를 유지한다.
- 대표 Desktop/Mobile 응답 계약은 결정적 HTML 테스트로 검증하며 실제 브라우저 실행은 필수가 아니다.
