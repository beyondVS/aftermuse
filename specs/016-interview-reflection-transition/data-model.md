# 데이터 모델: Interview Skip과 Reflection Transition

## Interview 변경

| 항목 | 표현 | 계약 |
| --- | --- | --- |
| `Status.ENDED_NO_REFLECTION` | 기존 `status` CharField의 새 terminal choice | 확정 답변 없이 질문 흐름을 종결했으며 Reflection 없음 |
| status DB CHECK | `IN_PROGRESS`, `REFLECTION_READY`, `COMPLETED`, `ENDED_NO_REFLECTION` | 알 수 없는 상태 저장 거부 |

`COMPLETED`는 후속 Day 12의 Reflection 최종 완료 의미로 보존한다. `ENDED_NO_REFLECTION`은 생성 실패가 아니며 Retry 대상도 아니다. Reading·Book·user 관계와 Coverage는 종결 시 변경하지 않는다.

### Interview 상태 전이

```text
IN_PROGRESS
├─ 종료 조건 + confirmed answer >= 1 ──> REFLECTION_READY
├─ 종료 조건 + confirmed answer == 0 ─> ENDED_NO_REFLECTION
└─ 답변/Skip 후 질문 계속 ───────────> IN_PROGRESS

REFLECTION_READY
├─ 생성 실패 ───────────────────────> REFLECTION_READY
├─ 생성 성공(DRAFT 생성) ───────────> REFLECTION_READY
└─ Day 12 최종 확인 ─────────────────> COMPLETED (이번 범위 밖)
```

Reflection DRAFT 생성만으로 Interview를 `COMPLETED`로 바꾸지 않는다. `ENDED_NO_REFLECTION`에서 Reflection 생성·답변·Skip은 모두 거부한다.

## InterviewTurn 변경

| 필드 | 표현 | 계약 |
| --- | --- | --- |
| `user_skipped_at` | nullable DateTimeField | 사용자가 현재 질문을 명시적으로 건너뛴 시각; 기존 행은 NULL |
| `answer` | 기존 nullable TextField | 실제 확정 답변; `user_skipped_at`과 동시 non-NULL 불가 |
| `next_question_skipped_at` | 기존 nullable DateTimeField | 답변 뒤 Provider가 다음 질문을 만들지 않은 상태; 사용자 Skip과 별개 |

### Turn 결과 불변

- 답변 대기: `answer IS NULL AND user_skipped_at IS NULL`.
- 답변 확정: `answer IS NOT NULL AND user_skipped_at IS NULL`.
- 사용자 Skip: `answer IS NULL AND user_skipped_at IS NOT NULL`.
- `answer IS NOT NULL AND user_skipped_at IS NOT NULL`은 DB CHECK와 model validation에서 거부한다.
- 이미 답변 또는 Skip으로 확정된 Turn은 다른 결과로 바꿀 수 없다.
- `next_question_skipped_at`은 answer가 있는 Turn에만 허용하는 기존 계약을 유지한다.

## InterviewBudget

| 값 | 계산 |
| --- | --- |
| `question_count` | InterviewTurn 전체 수 |
| `answered_count` | answer가 있는 Turn 수 |
| `user_skipped_count` | user_skipped_at이 있는 Turn 수 |
| `resolved_count` | answered_count + user_skipped_count |

후속 전이 직전에는 `resolved_count == question_count`이고 마지막 처리 Turn의 sequence도 `question_count`와 같아야 한다. 일반/절대 질문 상한은 `resolved_count`로 계산한다. Coverage는 Answer analysis 결과로만 상승하며 Skip 자체는 변경하지 않는다.

## Reflection과 생성 결과

Reflection schema는 Day 10을 그대로 유지한다. Interview OneToOne이 최종 중복 방어다.

| 상태 | Reflection 수 | 사용자 목적지 |
| --- | --- | --- |
| `REFLECTION_READY`, 생성 전/실패 | 0 | 생성 또는 Retry 화면 |
| `REFLECTION_READY`, 생성 성공 | 1 | 최소 임시 결과 화면 |
| `ENDED_NO_REFLECTION` | 0 | 답변 부족 종결 안내 |
| `COMPLETED` | 후속 정책 | Day 12 완료 목적지 |

생성 실패 상태를 DB에 별도 저장하지 않는다. GET 재진입 시 Reflection 부재와 `REFLECTION_READY`로 생성 가능 상태를 복원한다. 오류 상세는 요청 범위에서만 안전한 reason category로 표시·기록한다.

## Transaction과 동시성

### 사용자 Skip

1. 짧은 atomic에서 owner-scoped Interview와 현재 Turn을 잠근다.
2. 이미 같은 Skip이면 기존 상태를 재사용하고, answer가 있으면 conflict로 거부한다.
3. `user_skipped_at`을 저장하고 최신 budget을 계산한다.
4. 즉시 종결/선택 상태면 같은 transaction에서 Interview 상태 또는 decision을 확정한다.
5. 다음 질문이 필요하면 commit 후 Provider를 호출한다.
6. 두 번째 atomic에서 Interview/Turn/budget이 그대로인지 재검증하고 다음 Turn을 하나만 삽입한다.

답변 저장도 잠근 Turn의 `user_skipped_at IS NULL`을 확인한다. 답변과 Skip 경합은 먼저 잠금을 획득해 확정한 요청만 성공하며 DB CHECK가 마지막 방어다.

### Reflection 생성

1. owner scope에서 기존 Reflection을 조회해 있으면 즉시 재사용한다.
2. 없으면 transaction 밖에서 Day 10 생성 결과를 만든다.
3. Day 10 저장 Service가 Interview lock·현재 answer snapshot·OneToOne을 재검증한다.
4. concurrent conflict면 owner scope로 기존 Reflection을 다시 조회해 같은 성공 결과로 수렴한다.

Provider 실패는 Interview·Turn·Coverage·기존 Reflection을 변경하지 않는다.

## Migration

현재 leaf `0007_reflection` 뒤를 기준으로 계획하며 구현 직전 graph를 다시 확인한다.

### Schema migration

- `SET LOCAL lock_timeout = '2s'` 후 nullable `user_skipped_at` 추가.
- 기존 Interview status CHECK를 짧게 제거하고 네 상태 CHECK를 `NOT VALID`로 추가.
- Turn answer/Skip 상호 배타 CHECK를 `NOT VALID`로 추가.
- `SeparateDatabaseAndState`로 Django state에는 새 choice와 두 CHECK가 최종 형태로 보이게 한다.
- backfill·RunPython 없음. 기존 행은 `user_skipped_at=NULL`이라 새 Turn CHECK를 만족한다.

### Validation migration

- `atomic = False`.
- Interview status CHECK와 Turn 결과 CHECK를 각각 `VALIDATE CONSTRAINT`.
- validation에는 `lock_timeout`을 적용하지 않는다.

구현 시 `sqlmigrate`로 nullable ADD COLUMN, constraint drop/add/validate, reverse SQL을 확인한다. 새 terminal 데이터 생성 후 운영 reverse는 금지하고 additive schema를 보존한 코드 rollback을 우선한다.
