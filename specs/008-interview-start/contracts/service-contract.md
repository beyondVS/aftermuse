# 내부 Service 계약: Interview 시작

## 범위

Reading에서 Interview를 시작하거나 기존 Interview의 목적지를 판정하는 application 경계다. HTTP, Template, LLM 질문, Turn 생성, Coverage, Reflection 데이터와 Credit 변경을 수행하지 않는다.

## start_interview

### 입력

- 인증된 `user`
- 시작 대상 `reading`

Book, 소유자, readiness 또는 status를 client 입력으로 받지 않는다.

### 처리 계약

1. transaction 안에서 Reading을 `pk`와 `user`로 다시 조회하고 잠근다.
2. 비소유/미존재는 외부에 존재 여부를 구분하지 않는 오류로 처리한다.
3. `완독` 상태와 유효한 완독일을 검증한다.
4. 기존 Interview가 있으면 새 행을 만들지 않고 status의 destination과 함께 반환한다.
5. 없으면 Reading Book의 readiness를 계산해 `IN_PROGRESS` Interview를 만든다.
6. Interview Book은 잠근 Reading Book과 같고 readiness는 호출 시점 값이다.

### 출력

- `interview`: 신규 또는 기존 Interview
- `created`: 신규 생성 여부
- `destination`: `INTERVIEW`, `REFLECTION_READY`, `REFLECTION_COMPLETED`

### 오류와 Side effect

- 미저장 Reading, 비소유/미존재, 미완독 또는 상태·날짜 불일치는 정책/validation 오류다.
- 기존 Interview의 Book과 잠근 Reading의 Book이 일치하지 않으면 손상된 연결을 재사용하거나
  변경하지 않고 정책 오류로 처리한다.
- 예상하지 못한 DB 오류는 성공으로 바꾸거나 내부 내용을 사용자에게 노출하지 않는다.
- UNIQUE 경쟁은 같은 Reading의 기존 Interview를 확인할 때만 재사용으로 복구한다.
- 신규 경로에서 Interview 최대 한 건만 생성하며 Reading, Book, Knowledge, Turn, Credit, 질문, Coverage와 Reflection은 변경하지 않는다.

## get_interview_destination

| status | destination |
| --- | --- |
| `IN_PROGRESS` | `INTERVIEW` |
| `REFLECTION_READY` | `REFLECTION_READY` |
| `COMPLETED` | `REFLECTION_COMPLETED` |

허용되지 않는 status는 기본 화면으로 보내지 않고 오류로 처리한다. Bundle 05B는 `INTERVIEW`를 실제 화면에 연결한다. 후속 Reflection Bundle이 나머지 두 목적지를 named URL에 연결하며, 그 전에는 존재하지 않는 URL을 reverse하거나 가짜 Reflection 화면을 만들지 않는다.

## has_started_interview

- 입력: 저장된 Reading
- 출력: 해당 Reading에 Interview가 존재하면 `True`, 아니면 `False`
- `readings.services.change_reading_state()`와 `update_completion_date()`가 이 결과로 완독 취소와 완독일 수정을 거부한다.
- 외부 I/O나 영속 변경은 없다.

## Turn 저장 계약

- Interview마다 sequence는 1부터 시작하고 중복될 수 없다.
- question은 앞뒤 공백 제거 후 1~2,000자다.
- answer의 `NULL`은 미응답이다.
- 이번 Bundle에는 public Turn 생성·답변 Service가 없으며 Bundle 06A가 입력·저장 계약을 추가한다.
