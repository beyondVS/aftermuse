# 내부 Service 계약: Interview Coverage 상태

## 범위

사용자 소유 Interview의 canonical Core Coverage snapshot을 조회하고, 검증된 상태 patch를 짧은
transaction에서 원자적으로 적용하는 application 경계다. HTTP, Template, LLM 분석, 다음 질문,
Stop Policy, Reflection, Credit과 Knowledge 변경을 수행하지 않는다.

## 공통 값

### CoreCoverageAxis

```text
MEMORY
REACTION
CONNECTION
AFTERTHOUGHT
```

### CoverageStatus

```text
UNCOVERED
PARTIAL
COVERED
```

### CoveragePatchItem

한 축과 목표 상태의 pair다. patch는 이 항목의 순서 있는 collection으로 전달하여 같은 축의
중복을 persistence 경계에서 검출할 수 있게 한다.

### CoverageSnapshot

네 canonical 축과 현재 상태를 모두 포함하는 read-only 결과다. 내부 mutable 저장 object를
caller와 공유하지 않는다.

## get_interview_coverage

### 입력

- 인증된 사용자
- 저장된 Interview 식별 대상

### 성공

- 사용자가 소유하고 Reading·Book 연결이 유효한 Interview의 canonical `CoverageSnapshot`을
  진행 상태와 관계없이 반환한다.
- 조회는 Interview, Turn 또는 Coverage를 변경하지 않는다.

### 실패

- 미저장 대상, 다른 사용자 소유, 손상된 Reading·Book 연결 또는 canonical이 아닌 저장 값은
  안전한 정책 오류로 반환한다.
- 다른 사용자 대상과 존재하지 않는 대상은 호출자가 구별할 수 없게 한다.
- `IN_PROGRESS`가 아닌 소유자 Interview도 연결과 canonical shape가 유효하면 조회할 수 있다.

## apply_interview_coverage_patch

### 입력

- 인증된 사용자
- 저장된 Interview 식별 대상
- 0개 이상의 `CoveragePatchItem`

### 선행조건

1. 사용자가 Interview를 소유한다.
2. Interview가 `IN_PROGRESS`다.
3. Interview와 Reading의 Book 연결이 일치한다.
4. Interview에 답변이 확정된 Turn이 하나 이상 있다.
5. 저장된 Coverage가 canonical shape다.

### 처리 계약

1. patch collection의 각 항목이 허용된 축과 상태인지 확인한다.
2. 같은 축이 두 번 이상 나타나면 전체 patch를 거부한다.
3. 빈 patch는 DB write 없이 현재 snapshot과 `changed=False`를 반환한다.
4. 사용자 소유 Interview 행을 transaction 안에서 잠그고 모든 선행조건과 최신 Coverage를 다시
   확인한다.
5. 각 목표가 현재와 같으면 no-op, 현재보다 높으면 상승, 낮으면 전체 patch를 거부한다.
6. 하나라도 유효하지 않으면 어떤 축도 저장하지 않는다.
7. 변경이 있으면 canonical object 전체를 한 번 저장하고 `changed=True`를 반환한다.
8. 변경이 없으면 저장하지 않고 `changed=False`를 반환한다.

### 성공 결과

- 최신 read-only `CoverageSnapshot`
- 실제 DB 변경 여부 `changed`

### 실패 결과

| 분류 | 조건 | 상태 보장 |
| --- | --- | --- |
| 입력 오류 | 알 수 없는 축·상태, 중복 축 또는 잘못된 항목 shape | DB 접근 전 또는 write 전에 전체 거부 |
| 정책 오류 | 소유권, Interview 상태, 답변 존재 또는 Book 연결 위반 | Coverage와 관련 domain 상태 불변 |
| 저장 상태 오류 | 기존 Coverage가 canonical이 아님 | 임의 복구 없이 전체 거부 |
| 상태 하락 오류 | 목표 상태가 최신 저장 상태보다 낮음 | 전체 patch rollback |
| 영속 오류 | DB read, lock 또는 write 실패 | 성공으로 변환하지 않고 전체 rollback |

내부 DB 오류, 저장된 비정상 payload와 다른 사용자 대상의 상세정보는 사용자에게 노출하지 않는다.

## 동시성 및 멱등성

- 같은 patch의 반복 적용은 첫 요청 이후 `changed=False`인 같은 snapshot으로 수렴한다.
- 서로 다른 축의 동시 상승은 두 변경을 모두 포함하는 snapshot으로 수렴한다.
- 같은 축의 동시 상승에서 높은 상태가 확정된 뒤 낮은 요청이 lock을 얻으면 낮은 요청은 상태
  하락으로 거부되고 높은 상태가 유지된다.
- transaction 밖에서 읽은 stale Coverage를 그대로 덮어쓰지 않는다.

## Side-effect 금지

Coverage 조회와 patch 적용은 다음을 수행하지 않는다.

- Interview status 변경
- InterviewTurn 생성, 순서 변경 또는 답변 수정
- Answer Analysis 또는 Provider 호출
- 다음 질문, 질문 Budget, Soft Stop 또는 Low-information 판단
- Reflection, Credit, Book Knowledge 또는 Reading 변경
