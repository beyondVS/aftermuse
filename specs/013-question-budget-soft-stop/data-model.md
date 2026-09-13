# 데이터 모델: 질문 상한과 Soft Stop

## 기존 엔터티

### Interview

- `reading`, `book`, `knowledge_readiness`, `coverage`는 기존 계약을 유지한다.
- `status`: `IN_PROGRESS`에서 종료 선택·상한·검증된 생략 시 `REFLECTION_READY`로 전환한다. Day 07에 이미 생략 표식이 기록된 행은 읽기만으로 상태를 바꾸지 않고 준비 안내를 표시하며, 후속 확정 요청에서 멱등 전환한다. 이번 단계는 `COMPLETED` 또는 Reflection 데이터를 만들지 않는다.
- 선택 기록은 답변 Turn을 통해 연결된다. 한 Interview에 여러 Soft Stop 선택 이력이 생길 수 있지만 현재 유효한 기록은 마지막 답변 Turn의 기록뿐이다.

### InterviewTurn

- `sequence`: 질문 순서다. 새로 생성되는 질문은 최대 10개이며 기존 Turn을 삭제하거나 재번호 매기지 않는다.
- `answer`: 최대 2,000자의 한 번 확정된 원문이다. 완료 문항 수는 `answer IS NOT NULL`인 Turn 수로 계산한다.
- `next_question_skipped_at`: 검증된 질문 생략과 Provider 실패를 구분하는 기존 표식이다. 새 선택 기록과 같은 답변 Turn에 동시에 확정되지 않는다.

## 신규 엔터티: Interview 진행 선택

한 답변 Turn에 최대 하나의 선택 기록이 속한다. 선택 전에 생성된 질문 후보는 비공개이며, 사용자가 계속을 확정한 뒤에만 새 `InterviewTurn`이 된다.

| 속성 | 의미와 제약 |
|---|---|
| `turn` | 답변이 확정된 InterviewTurn과 일대일 연결. 유일하며 다른 Interview의 선택으로 재사용할 수 없다. |
| `kind` | `SOFT_STOP` 또는 `CAP_EXTENSION`. 생성 뒤 변경하지 않는다. |
| `selection` | 미결정, `END`, `CONTINUE` 중 하나. 최초 확정 이후 다른 값으로 바꾸지 않는다. |
| `candidate_question` | 기존 검증 경계를 통과한 단일 질문 후보. 선택 전 사용자에게 노출하지 않는다. |
| `created_at`, `decided_at` | 재접속과 반복 요청에서 대기·확정 상태를 구분한다. |

검증 규칙: `turn.answer`가 확정돼야 하고, 선택 생성 시 해당 Turn이 마지막 답변 Turn이어야 한다. `CAP_EXTENSION`은 8번째 답변과 `UNCOVERED` 목표 축의 근거 있는 후보에서만 허용한다. `CONTINUE`는 허용 상한 이내의 다음 Turn 하나와 같은 트랜잭션에서 확정한다. `END`는 Interview의 `REFLECTION_READY`와 함께 확정한다. `CAP_EXTENSION`의 `CONTINUE` 이력은 9번째 답변 후 10번째 질문 허용의 근거가 된다.

## 상태 전이

| 현재 상태 | 사건 | 결과 |
|---|---|---|
| 답변 확정, 후속 미처리 | 분석·질문 검증 성공, Soft Stop 해당 | Coverage + `SOFT_STOP` 미결정 기록 확정, 새 Turn 없음 |
| 답변 확정, 후속 미처리 | 8번째 답변, `UNCOVERED` 목표 후보 유효 | Coverage + `CAP_EXTENSION` 미결정 기록 확정, 9번째 Turn 없음 |
| 미결정 선택 | `END` | 선택 확정 + `REFLECTION_READY`, 새 Turn 없음 |
| 미결정 선택 | `CONTINUE` | 선택 확정 + 보류된 다음 Turn 하나; 같은 선택 재시도는 기존 결과 재사용 |
| 8번째 답변, 예외 불가 | 정책 판정 | Coverage + `REFLECTION_READY`, 새 Turn 없음 |
| 8번째 답변, 네 축 `COVERED` | 일반 상한 우선 판정 | Soft Stop 재노출 없이 Coverage + `REFLECTION_READY`, 새 Turn 없음 |
| 9번째 답변, 예외 허가 | `UNCOVERED`·근거 유지 또는 소멸 | 유지 시 검증된 10번째 Turn 하나; 공백 소멸 시 Coverage + `REFLECTION_READY`; 근거 부족의 유효한 생략이면 Coverage + 생략 표식 + `REFLECTION_READY` |
| 10번째 답변 | 후속 처리 | Coverage + `REFLECTION_READY`, 11번째 Turn 없음 |
| 답변 뒤 유효한 생략 | 정책 판정 | Coverage + 생략 표식 + `REFLECTION_READY`, 새 Turn 없음 |
| Day 07 생략 표식이 있는 진행 중 Interview | GET·후속 확정 POST | GET은 읽기 전용 준비 안내, POST는 재분석 없이 `REFLECTION_READY` 멱등 전환 |
| 분석·생성·저장 실패 | 재시도 | 답변만 유지하고 그 답변의 Coverage·선택·다음 Turn은 미확정 |

모든 전이에서 Interview 소유권과 Reading·Book 연결을 확인한다. 선택 확정과 질문 생성에는 Interview 행 잠금을 공통 직렬화 경계로 사용한다.
