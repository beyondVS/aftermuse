# Web·Service 계약: Day 08 Interview 진행

## 공통 경계

- 인증된 소유자의 Interview와 마지막 답변 Turn만 처리한다. 미존재와 비소유는 동일한 404, 유효하지 않은 상태·오래된 Turn은 내용 비노출 409다.
- 일반 HTML GET/POST가 정본이고 HTMX는 동일 상태의 `#interview-turn-region` fragment를 교체한다. 상태 변경은 CSRF 보호 POST로만 한다.
- 소유권, Budget, 선택 유일성 및 현재 상태의 최종 판정은 Service가 수행한다. View의 사전 조회나 Provider 제안만으로 결정하지 않는다.

## POST 기존 `/reflections/interviews/<interview_id>/turns/<sequence>/next/`

답변은 이미 확정돼 있어야 한다. 기존 질문 생략 표식이 있으면 Provider를 다시 호출하지 않고 준비 상태로 확정한다. 그 밖에는 분석 후 Budget을 먼저 판단하고 필요한 경우에만 후속 질문 후보를 검증한다. 8번째 답변에서는 Soft Stop보다 일반 상한이 우선한다.

| 결과 | 일반 POST | HTMX | 영속 결과 |
|---|---|---|---|
| 다음 질문 | detail redirect | 현재 질문 fragment 200 | Coverage + 새 Turn 하나 |
| Soft Stop | detail redirect | 선택 fragment 200 | Coverage + 미결정 선택, 새 Turn 없음 |
| 8문항 예외 선택 | detail redirect | 별도 상한 선택 fragment 200 | Coverage + 미결정 선택, 새 Turn 없음 |
| 준비 완료 | 소유자용 준비 안내로 redirect | 준비 fragment 200 | Coverage + `REFLECTION_READY`; 유효한 생략이면 기존 표식도 기록 |
| 분석·생성·저장 오류 | 보존된 답변의 오류 화면 503 | 교체 가능한 오류 fragment 503 | 해당 답변의 후속 상태 미확정, 같은 답변으로 재시도 |

검증된 생략은 오류가 아니다. 이미 확정된 선택·다음 Turn·준비 상태는 Provider 재호출 없이 재사용한다. Day 07의 기존 생략 표식은 상태 확정 POST에서 재분석 없이 `REFLECTION_READY`로 멱등 전환한다. 8번째 답변의 예외 평가와 예외 진행을 허가받은 9번째 답변의 근거 부족은 적용 문맥에 맞는 유효한 생략 제안이어야 한다. 10번째 답변이나 8번째 답변에서 `UNCOVERED` 축이 없으면 질문 Provider를 호출하지 않는다.

## POST 신규 `/reflections/interviews/<interview_id>/turns/<sequence>/decision/`

**이름**: `reflections:interview_decision`

**입력**: `decision=end|continue`. URL의 sequence는 선택 기록의 답변 Turn과 일치해야 한다. 후보 질문 본문·Coverage·상한 값은 클라이언트 입력으로 받지 않는다.

- `end`: 후보를 Turn으로 만들지 않고 선택과 Interview의 `REFLECTION_READY`를 함께 확정한다. 일반 POST는 준비 안내로 redirect하고 HTMX는 준비 fragment 200을 반환한다.
- `continue`: 유효한 보류 후보를 새 Turn 하나로 확정한다. `CAP_EXTENSION`에서는 8번째 답변의 선택으로 최대 2문항 예외 진행을 허가한다. 일반 POST는 detail로 redirect하고 HTMX는 현재 질문 fragment 200을 반환한다.
- 같은 선택의 반복은 확정 결과를 재사용한다. 다른 선택과의 경합은 먼저 확정된 상태를 유지하며, 후속 GET에서 실제 상태를 확인할 수 있게 한다. stale·위조 요청은 409, 비소유·미존재는 404다.
- DB 실패 시 선택과 Turn 또는 상태 전환은 모두 취소한다. 보류된 후보와 답변을 유지하고 안전한 재시도 안내를 제공한다.

## GET 기존 `/reflections/interviews/<interview_id>/`

- `IN_PROGRESS`에서 질문·답변 저장·선택 대기·후속 실패 중 실제 확정 상태를 표시한다. 후보 질문은 선택 전에 HTML이나 응답 헤더에 포함하지 않는다.
- Day 07의 기존 질문 생략 표식이 마지막 답변 Turn에 있으면 GET에서 DB 상태를 바꾸지 않고 200 준비 안내를 표시한다. 반복 방문도 재분석·질문 생성을 시작하지 않는다.
- `REFLECTION_READY`는 Day 08의 200 독서노트 준비 안내를 제공한다. Reflection 초안, 생성 화면, 완료 URL은 아직 제공하지 않는다.
- Soft Stop은 4~7번째 답변에서 두 선택을, 8문항 예외는 독서노트 준비와 최대 2문항 더 이야기하기를 구분된 문구로 보여준다. 8번째 답변에서 네 축이 모두 `COVERED`면 Soft Stop을 다시 보여주지 않는다. 첫 계속 선택 후 다음 답변에서 조건과 일반 상한 이내의 질문 여지가 유지되면 다시 Soft Stop을 보여준다.
- 오류 화면은 답변 보존 사실, 같은 답변의 재시도 행동과 실패 상태를 표시한다. 키보드 focus, 텍스트 상태 및 Desktop/Mobile 레이아웃 계약을 유지한다.
