# 데이터 모델: Interview Coverage 상태

## Interview 확장

기존 `Interview` aggregate에 Coverage 값 객체를 추가한다.

| 항목 | 계약 |
| --- | --- |
| 소유자 | `Interview.reading.user`에서 파생하며 별도 사용자 식별자를 저장하지 않는다. |
| 생명주기 | Interview와 함께 생성·삭제된다. 독립 entity 수명은 없다. |
| 초기값 | 네 Core 축 모두 `UNCOVERED` |
| 조회 가능 상태 | 소유자이고 Reading·Book 연결이 유효하면 Interview 진행 상태와 관계없이 조회 가능 |
| 변경 가능 상태 | `Interview.status == IN_PROGRESS`이고 답변이 하나 이상 확정된 경우 |
| 저장 형태 | non-null JSON object |
| 조회 단위 | Interview 전체 Coverage snapshot |

### Canonical JSON shape

```json
{
  "MEMORY": "UNCOVERED",
  "REACTION": "UNCOVERED",
  "CONNECTION": "UNCOVERED",
  "AFTERTHOUGHT": "UNCOVERED"
}
```

키와 값은 대문자 canonical token을 사용한다. 다음 조건을 모두 만족해야 한다.

- JSON 최상위 값은 object다.
- 키는 정확히 `MEMORY`, `REACTION`, `CONNECTION`, `AFTERTHOUGHT` 네 개다.
- 각 값은 `UNCOVERED`, `PARTIAL`, `COVERED` 중 하나다.
- 배열, null, 중첩 object, 누락 키와 추가 키는 허용하지 않는다.

## Core Coverage 축

| 축 | 의미 |
| --- | --- |
| `MEMORY` | 기억에 남은 내용, 주장, 장면 또는 인상 |
| `REACTION` | 동의·반대, 감정, 평가 또는 해석 |
| `CONNECTION` | 자신의 경험·생각·상황과 책의 연결 |
| `AFTERTHOUGHT` | 읽은 뒤 남은 생각, 변화, 질문 또는 여운 |

## Coverage 상태

| 상태 | 의미 | 순서 |
| --- | --- | --- |
| `UNCOVERED` | 해당 방향의 생각이 아직 드러나지 않음 | 0 |
| `PARTIAL` | 일부 의미는 있으나 후속 질문의 여지가 있음 | 1 |
| `COVERED` | Reflection 근거로 사용할 만큼 충분히 드러남 | 2 |

상태 순서는 저장 전환 검증에만 사용하며 수치 Coverage score로 노출하거나 저장하지 않는다.
`PARTIAL`과 `COVERED`의 의미 판정은 Bundle 07B의 Answer Analysis 계약이 담당한다.

## 상태 전환

```text
UNCOVERED ──> PARTIAL ──> COVERED
     └──────────────────> COVERED
```

- 동일 상태 재적용은 유효한 no-op다.
- 오른쪽으로 한 단계 또는 두 단계 상승할 수 있다.
- 왼쪽으로의 하락은 patch 전체를 거부한다.
- 한 patch의 모든 축이 유효할 때만 하나의 transaction에서 저장한다.
- 빈 patch는 아무 상태도 바꾸지 않고 현재 snapshot을 반환한다.
- Coverage 변경은 `Interview.status`를 전환하지 않는다.

## 불변조건

1. 모든 Interview는 migration 이후 canonical Coverage object를 가진다.
2. 한 Interview에는 Coverage snapshot이 하나뿐이다.
3. 다른 Interview의 Coverage와 합치거나 공유하지 않는다.
4. 답변이 없는 Interview에는 Coverage 상승을 적용하지 않는다.
5. `IN_PROGRESS`가 아니거나 `interview.book_id != interview.reading.book_id`이면 변경하지 않는다.
6. 적용된 상태는 이후 요청으로 하락하지 않는다.
7. patch 실패 시 Coverage, Interview, Turn, 답변과 다른 domain 상태가 모두 요청 전 값으로 남는다.

## 동시성 모델

Coverage 변경은 사용자 소유 Interview 행을 row lock으로 획득한 뒤 canonical shape와 상태를 다시
검증한다. 두 요청이 같은 초기 snapshot을 보더라도 실제 비교는 각 요청이 lock을 얻은 시점의
최신 값에서 수행한다.

- 서로 다른 축의 상승은 모두 보존된다.
- 같은 축의 동일 상승은 하나의 상태로 수렴한다.
- 먼저 높은 상태가 확정된 뒤 도착한 낮은 목표는 상태 하락 오류로 전체 거부된다.
- transaction에는 외부 Provider, network 또는 파일 I/O를 포함하지 않는다.

## DB 제약

DB CHECK는 다음을 함께 보장한다.

- `jsonb_typeof(coverage) = 'object'`
- 네 canonical 키를 제거한 결과가 빈 object여야 함 (추가 키 없음)
- 네 canonical 키가 모두 존재함
- 각 canonical 키의 text 값이 세 허용 상태 중 하나임

추가 JSON index는 만들지 않는다. 현재 selector와 Service는 Interview 식별자 및
`reading__user` 관계로만 대상 행을 찾는다.

## Migration 및 호환성

### Schema 단계

1. 기존 Interview 행과 구버전 insert를 위해 canonical literal `db_default`를 가진 non-null
   JSONB column을 추가한다.
2. 신버전 객체 생성에는 매번 새 dict를 반환하는 callable Python default를 사용한다.
3. canonical CHECK를 `NOT VALID`로 추가해 새 write를 즉시 제한한다.
4. 기존 행을 `VALIDATE CONSTRAINT`로 검사한다.
5. Django model state와 실제 DB constraint를 일치시킨다.

### 배포 안전성

- 구버전 코드는 새 field를 몰라도 DB default로 유효한 row를 insert할 수 있다.
- column 추가 DDL의 `ACCESS EXCLUSIVE` 대기는 transaction-local `lock_timeout`으로 제한한다.
- CHECK의 기존 행 scan은 제약 추가와 분리한다.
- 실제 SQL과 reverse 경로는 `sqlmigrate` 및 migration test로 확인한다.
- 데이터 변환 `RunPython`은 필요하지 않다.
