# Day 08 설계 조사

## 선택 대기 상태

**Decision**: 답변 Turn마다 최대 하나의 비공개 선택 기록을 두고 종류(`SOFT_STOP`/`CAP_EXTENSION`), 미결정·종료·계속 선택과 검증된 다음 질문 후보를 보존한다. 선택 전에는 후보를 `InterviewTurn`으로 만들지 않는다.

**Rationale**: 현재 `process_next_turn`은 Coverage와 다음 Turn 또는 생략을 원자적으로 확정한다. Soft Stop에서는 Coverage 반영 후 사용자의 결정을 기다려야 한다. 후보를 보존하면 계속 선택 시 Provider를 다시 호출하지 않고 같은 질문을 확정한다. 한 Turn의 선택 유일성과 Interview 잠금으로 반복·경합 요청을 처리한다.

**Alternatives considered**: 후보 Turn을 미리 생성해 숨기면 질문 수와 현재 Turn의 의미가 흐려진다. 선택 이후 다시 분석·생성하면 실패와 비결정적 결과가 늘어난다. Interview에 여러 nullable 선택 필드를 두면 반복 선택 이력과 예외 진행 권한을 표현하기 어렵다.

## 질문 Budget과 예외 진행

**Decision**: 완료 문항 수는 답변이 확정된 Turn 수로, 절대 질문 수는 생성된 Turn sequence로 판단한다. 목표 5~6은 운영 목표이며 강제 중단 조건이 아니다. 8번째 답변에서는 Soft Stop보다 일반 상한을 먼저 판단한다. `UNCOVERED` 축을 겨냥한 검증된 후보가 있을 때만 예외 선택을 표시한다. 그 선택은 최대 2문항의 진행 허가다. 9번째 답변 후 공백·근거가 사라지면 10번째 질문을 만들지 않는다.

**Rationale**: 미답변 질문을 완료로 세거나 10번째 질문의 생성만으로 종료하면 마지막 답변을 받을 수 없다. 예외는 사용자 선택과 미충족 축을 동시에 요구하는 PRD 정책이다.

**Alternatives considered**: 8문항에서 무조건 종료하면 승인된 Exceptional Ceiling에 도달할 수 없다. `PARTIAL` 축만으로 연장하는 방식은 명세의 명시적 선택과 다르다.

## 명시적 질문 생략과 오류

**Decision**: 일반 진행에서 유효한 질문 생략은 기존 Day 07의 네 축 `COVERED` 조건을 유지한다. 과거에 생략 표식이 확정된 진행 중 Interview는 GET에서 준비 안내로 판정하고, 후속 확정 POST에서는 재분석·새 질문 없이 `REFLECTION_READY`로 멱등 전환한다. 8문항 예외 후보 평가와 허가된 9번째 답변에서는 `UNCOVERED` 축에 근거 있는 질문을 만들 수 없다는 명시적 생략 결과를 준비 상태로 처리하도록 Provider 결과와 Application 검증을 좁게 확장한다. 빈 문자열·무효 후보·timeout은 오류이며 기존 답변과 미확정 Coverage를 유지한다.

**Rationale**: `UNCOVERED` 축이 있어도 근거 없는 질문을 억지로 만들 수 없고, 실패를 종료로 간주해서도 안 된다.

**Alternatives considered**: 유효하지 않은 Provider 응답을 생략으로 취급하면 실제 장애를 완료로 오인한다. 질문이 없을 때 반복 분석·생성을 수행하면 같은 답변의 결과가 달라질 수 있다.

## Reflection 경계와 Web 목적지

**Decision**: 종료·상한·검증된 생략은 기존 `Interview.Status.REFLECTION_READY`를 사용하고 소유자에게 200 준비 안내를 제공한다. Reflection 모델, 초안 생성 및 생성 화면 전환은 Day 09~10에 둔다.

**Rationale**: `REFLECTION_READY`는 기존 시작 흐름의 목적지 판정에 정의돼 있다. 현재 이 상태를 409 unavailable로 보여주는 화면만 Day 08의 준비 안내로 교체하면 범위를 지킬 수 있다.

**Alternatives considered**: 미완성 Reflection URL로 이동하면 제공되지 않는 기능을 완료된 것처럼 보이게 한다. 새로운 Interview 종료 status는 기존 목적지 계약과 중복된다.

## Schema와 검증

**Decision**: 기존 Interview·Turn 테이블에 필수 컬럼을 추가하지 않고 선택 기록 테이블을 추가한다. FK, 유일성·상태 검증과 과거 행 호환성을 migration에서 확인한다. PostgreSQL `sqlmigrate`로 실제 DDL·잠금 범위를 검토하고 제한된 `lock_timeout`을 둔다.

**Rationale**: 기존 행의 backfill이나 테이블 재작성 없이 새 상태를 도입할 수 있다. 현재 프로젝트는 PostgreSQL만 지원하며 기존 migration에도 잠금 제한 관례가 있다.

**Alternatives considered**: 기존 Interview에 NOT NULL 결정 필드를 바로 추가하면 이전 코드와의 호환·기본값 정책이 복잡해진다.
