# Day 09 Home 및 Interview 재진입 계약

## `GET /`

- 비로그인 방문은 공개 소개와 로그인·도서 검색 진입을 제공한다. 개인 Reading·Interview 및 샘플 기록처럼 보이는 항목을 표시하지 않는다.
- 로그인 방문은 사용자의 적격 Reading과 진행 중 Interview를 [데이터 모델](../data-model.md)의 영역별로 표시한다. 기록별 실제 도서·상태·진행 단계와 행동을 제공한다.
- Reading이 없으면 `[책 찾아보기]`가 도서 검색으로 이동한다. 영역에 적격 기록이 없으면 허위 카드를 표시하지 않는다.
- 다음 GET은 현재 저장 상태를 반영하며 영속 상태를 변경하지 않는다.

## Home 행동

| 조건 | 표시 행동 | 목적지 |
|---|---|---|
| `읽고 싶음` 또는 `읽는 중` Reading | `[독서 기록 계속하기]` | 해당 Reading 상세 |
| 완독 Reading, Interview 없음 | `[AI 독서노트 만들기]` | 해당 Reading의 Interview 시작 화면 |
| 진행 중 Interview | `[인터뷰 이어하기]` | 해당 기존 Interview 상세 |

각 행동은 현재 카드의 소유 기록을 가리킨다. 완독 카드에서 도서 검색을 거치지 않으며 이어하기는 Interview 생성·재시작 요청이 아니다.

## `GET /reflections/interviews/{interview_id}/`

- 현재 사용자 소유 Interview만 연다. 타 사용자 접근은 기존 404 계약을 유지한다.
- 첫 질문 전에는 기존 준비 화면, 미답변 Turn은 해당 질문, 확정 답변 뒤에는 후속 처리·오류 복구·진행 선택 또는 준비 안내 중 현재 상태를 반환한다.
- GET을 반복해도 Interview·Turn의 수와 내용, 확정 답변, 진행 선택은 변하지 않는다.
- `REFLECTION_READY`는 기존 준비 안내로 처리하고 `COMPLETED`의 기존 목적지 정책을 유지한다. 두 상태는 Home 진행 카드에서 제외한다.

## `GET /setup-status/` + HTMX

기존 Home Template partial과 상태 확인 응답을 유지한다. 개인 허브 조회나 표시가 이 응답에 섞이지 않는다.
