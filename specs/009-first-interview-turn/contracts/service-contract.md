# 내부 Service 계약: 첫 질문과 답변

## build_interview_question_context

- 입력: 소유권과 상태를 검증할 대상 `Interview`
- 출력: immutable `InterviewQuestionContext`
- Interview/Reading/Book 관계가 일치하고 status가 `IN_PROGRESS`여야 한다.
- `READY`는 해당 Book의 최소 Knowledge Claim을 안정된 순서로 포함한다.
- `READY_LIMITED`는 Knowledge Claim을 포함하지 않는다.
- 외부 I/O와 영속 변경이 없다.

## ensure_first_question

### 입력/출력

- 입력: 인증 user, interview, `QuestionProvider`
- 출력: sequence 1의 기존 또는 신규 `InterviewTurn`

### 처리 계약

1. user 소유, 관계 일치, `IN_PROGRESS` 상태를 검증한다.
2. sequence 1 Turn이 있으면 Provider를 호출하지 않고 반환한다.
3. Context를 만들고 transaction 밖에서 Provider를 호출한다.
4. 한 문장·300자 이하 질문을 application validation한다.
5. 짧은 transaction에서 Interview를 잠그고 상태·관계와 기존 Turn을 재검증한다.
6. 기존 Turn이 없을 때만 sequence 1을 생성한다.

Provider/validation 실패는 Turn을 만들지 않는다. 경쟁 생성은 기존 Turn을 반환해 DB 상태를
한 건으로 수렴시킨다.

## save_first_answer

### 입력/출력

- 입력: 인증 user, interview, sequence 1 Turn, validated answer
- 출력: 확정된 `InterviewTurn`과 신규 저장/멱등 재사용 구분

### 처리 계약

1. trim 후 1~2,000자인지 검증한다.
2. 소유자 범위의 진행 중 Interview와 sequence 1 Turn을 짧은 transaction에서 잠근다.
3. answer가 `NULL`이면 원문을 저장한다.
4. 저장된 값과 동일한 재제출은 멱등 성공으로 반환한다.
5. 다른 값의 재제출은 conflict이며 기존 answer를 유지한다.
6. Coverage, 분석, 다음 질문, status와 Credit은 변경하지 않는다.

DB 실패는 성공으로 표시하지 않으며 caller가 bound form 입력과 재시도 행동을 렌더링할 수 있는
오류로 변환한다. 내부 DB/Provider 원문 오류는 사용자에게 노출하지 않는다.
