# Service Contract: Reading lifecycle

HTTP나 Template에 의존하지 않는 `readings` Service의 구현 계약이다.

## `create_initial_reading`

**입력**

- 인증된 `user`
- 존재하는 `book`
- 세 값 중 하나인 `status`
- `status=completed`일 때 오늘 또는 과거인 `completed_on`

**동작**

1. 짧은 transaction에서 사용자 행을 잠근다.
2. 같은 사용자·Book의 Reading 이력을 재확인한다.
3. 활성 Reading이 있으면 생성하지 않고 해당 Reading을 반환한다.
4. 완독 이력만 이미 있으면 자동 재독을 만들지 않고 정책 오류와 최근 완독 Reading을
   제공한다.
5. 이력이 없으면 선택 상태로 한 건을 생성한다.

**출력**: `ReadingCreationResult(reading, created)`

## `create_rereading`

**입력**

- 인증된 `user`
- 현재 사용자가 소유한 완독 `source_reading`
- 새 Reading의 초기 `status`
- 초기 상태가 완독이면 유효한 `completed_on`

**동작**

1. 사용자 행을 잠그고 source 소유권·완독 상태를 다시 검증한다.
2. 같은 Book의 활성 Reading이 있으면 새로 만들지 않고 해당 Reading을 반환한다.
3. 활성 Reading이 없으면 source를 변경하지 않고 선택 상태의 별도 Reading을 생성한다.

**출력**: `ReadingCreationResult(reading, created)`

## `change_reading_state`

**입력**

- 인증된 `user`
- 현재 사용자가 소유한 `reading`
- 목표 `status`
- 목표가 완독이면 오늘 또는 과거의 `completed_on`

**동작**

1. Reading을 소유자 범위에서 잠가 최신 상태를 사용한다.
2. 같은 상태 재제출은 기존 완독일을 암묵적으로 바꾸지 않는다. 명시적인 날짜 수정은
   별도 Form 의도로 구분한다.
3. 완독으로 바꾸면 선택한 완독일을 저장한다.
4. Interview 시작 전 완독을 활성 상태로 바꾸면 완독일을 제거한다.
5. 다른 활성 Reading과 충돌하면 아무 값도 바꾸지 않고 그 Reading을 반환한다.
6. Interview 시작 후에는 완독 상태와 완독일 변경을 모두 거부한다.

**출력**: 저장된 `Reading`

## `has_started_interview`

**입력**: 잠금 여부를 확인할 `reading`

**출력**: Interview가 시작되었으면 `True`, 아니면 `False`

Bundle 04A에는 Interview 모델이 없으므로 기본 구현은 `False`를 반환한다.
`change_reading_state`는 이 함수만 통해 Interview 잠금을 판별하며, Service 테스트는 함수를
`True`로 대체해 잠금 시 상태와 완독일이 보존되는 계약을 검증한다. Day 05는 호출부를
변경하지 않고 실제 Interview 존재 조회로 구현을 교체한다.

## Transaction 및 무결성

- 사용자 잠금, 사전 조건 재확인, Reading 생성/변경은 한 `transaction.atomic()` 경계다.
- transaction 안에서 외부 I/O, Template rendering 또는 느린 작업을 수행하지 않는다.
- 조건부 unique 또는 CHECK 위반은 부분 상태를 남기지 않는다.
- 예상 가능한 동시 충돌은 rollback 뒤 기존 활성 Reading을 조회해 회복 가능한 결과로
  바꾸며, 임의의 `IntegrityError`를 모두 중복으로 오인하지 않는다.

## Day 05 연결 계약

Bundle 04A에는 Interview 모델이 없다. Day 05는 Interview 생성과 같은 transaction에서
Reading을 확정하고, `has_started_interview`를 실제 Interview 존재 조회로 교체한다. 그
전까지 Bundle 04A에서 생성한 Reading은 Interview가 없으므로 완독 상태와 날짜를 수정할 수
있다.
