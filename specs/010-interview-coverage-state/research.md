# 조사: Interview Coverage 상태

## 결정 1: Coverage는 Interview의 JSONB 값 객체로 저장한다

**Decision**: `Interview`에 네 Core 축을 모두 키로 가지는 non-null JSONB `coverage`를 추가한다.

**Rationale**: Architecture Decisions는 Coverage를 Interview aggregate 안의 JSONB 후보로 두고
있다. 현재 범위는 항상 함께 읽고 잠그는 고정 축 4개뿐이므로 별도 행 모델보다 단일 값 객체가
조회·원자적 patch·rollback을 단순하게 만든다. 향후 Focus Coverage가 추가되어도 aggregate 내부
shape를 명시적으로 확장할 수 있다.

**Alternatives considered**:

- 축별 `InterviewCoverage` 행: DB enum/unique 제약은 직관적이지만 Interview마다 4행 생성,
  다중 행 잠금 순서, 동시 초기화와 부분 생성 복구가 필요해 현재 범위보다 복잡하다.
- `Interview`의 축별 4개 column: DB 제약은 강하지만 Focus Coverage 확장과 aggregate snapshot
  전달에 불리하고 승인된 JSONB 방향과 어긋난다.
- Coverage 이력 event: 현재 요구사항은 최신 상태뿐이며 감사 이력은 범위에 없다.

## 결정 2: canonical shape는 네 키를 항상 포함한다

**Decision**: 기본값은 모든 축이 `UNCOVERED`인 object이고, 저장된 값은 정확히 네 키와 허용된
세 상태만 포함해야 한다. 알 수 없는 키, 누락 키, 비-object 또는 허용되지 않은 값은 변경 전에
정책 오류로 처리한다.

**Rationale**: 누락을 암묵적 `UNCOVERED`로 해석하면 저장 shape가 호출 경로마다 달라지고 후속
Answer Analysis와 Stop Policy가 방어 로직을 반복하게 된다. canonical shape는 반환 계약과 DB
검증을 결정적으로 만든다.

**Alternatives considered**:

- sparse object: 쓰기는 작지만 키 부재 의미와 migration/backfill 처리가 계속 전파된다.
- 수치 score: Core MVP가 이해 가능한 상태 표현을 우선한다는 문서와 범위를 위반한다.

## 결정 3: Python default와 DB default를 함께 유지한다

**Decision**: callable Python default는 새 객체마다 독립 dict를 만들고, 같은 JSON literal을
PostgreSQL `db_default`로 유지한다.

**Rationale**: Python default는 application에서 저장 전에도 정상 값을 제공한다. DB default는
schema-first rolling deploy에서 coverage를 모르는 이전 애플리케이션의 insert와 migration 당시
기존 행을 보호한다. Django 공식 문서는 두 default를 함께 지정하면 Python 생성에는 `default`,
DB insert와 새 field migration에는 `db_default`가 사용된다고 설명한다.

**Alternatives considered**:

- Python default만 사용: 구버전 process가 새 non-null column을 생략하는 rolling deploy에
  안전하지 않다.
- nullable column 후 backfill과 `SET NOT NULL`: 여러 배포 단계와 full-table validation이 필요하며
  canonical default를 계속 보장하지 못한다.
- DB default만 사용: 저장 전 model instance가 실제 dict 대신 DB default 표현을 가질 수 있어
  application validation이 불편하다.

## 결정 4: 상태 patch는 Interview 행 잠금 아래 단방향으로 적용한다

**Decision**: patch 항목 전체를 먼저 형식 검증하고, transaction에서 소유자 범위 Interview를
잠근 뒤 최신 canonical Coverage와 비교한다. 동일 상태는 no-op, 상승은 저장, 하락은 전체 거부한다.
빈 patch는 성공한 변경으로 세지 않고 현재 canonical 상태를 `changed=False`로 반환한다.

**Rationale**: Interview 하나가 aggregate lock이므로 축별 별도 잠금 순서 없이 lost update를
막을 수 있다. 경쟁 요청은 직렬화된 최신 상태에서 다시 단방향 규칙을 평가하므로 더 높은 상태가
낮아지지 않는다. 외부 호출 없이 짧은 transaction만 유지한다.

**Alternatives considered**:

- 잠금 없는 read-modify-write: 서로 다른 축 변경도 마지막 write가 앞선 변경을 덮을 수 있다.
- 비교 조건을 포함한 축별 SQL JSON update: query는 줄지만 다중 축 validation, 오류 계약과
  canonical shape 확인이 복잡해진다.
- 상태 하락을 조용히 무시: 손상된 분석 결과를 성공으로 오인하므로 명세의 전체 거부 계약과
  맞지 않는다.

## 결정 5: patch 입력은 순서 있는 항목 집합으로 받는다

**Decision**: application 계약은 `(axis, target_status)` 항목 sequence를 받아 중복 축을 검출한 뒤
내부 canonical mapping으로 변환한다.

**Rationale**: mapping만 받으면 같은 축이 중복된 upstream Structured Output을 변환 과정에서
조용히 덮어쓸 수 있다. 항목 sequence는 명세가 요구하는 중복 거부를 persistence 경계에서 보장한다.

**Alternatives considered**:

- mapping 입력: 편리하지만 중복 정보가 이미 소실된다.
- raw provider payload: 07A가 07B의 LLM 계약과 parsing 책임을 떠안는다.

## 결정 6: DB CHECK는 안전한 두 단계로 추가하고 JSON index는 만들지 않는다

**Decision**: column 추가 뒤 JSON object type, 정확히 4개 키, 네 필수 키 존재와 각 값의 enum을
검사하는 CHECK를 `NOT VALID`로 추가하고 별도로 validate한다. Coverage JSON 내용으로 검색하거나
정렬하지 않으므로 index를 추가하지 않는다.

**Rationale**: PostgreSQL에서 다수의 `ALTER TABLE`은 강한 lock을 요구하므로 DDL 대기는
`lock_timeout`으로 제한한다. `NOT VALID`는 새 write부터 제약을 적용하면서 기존 행 scan을 짧은
제약 추가와 분리하고, `VALIDATE CONSTRAINT`는 읽기·쓰기를 막지 않는 lock으로 기존 행을 확인한다.
현재 접근 경로는 Interview PK와 `reading__user`이며 JSON GIN/B-tree index가 사용될 query가 없다.

**Alternatives considered**:

- 제약 없는 JSONB: ORM을 우회한 write가 후속 정책 전체를 손상할 수 있다.
- 일반 `AddConstraint`: 기존 행 scan 동안 강한 lock을 유지할 수 있다.
- JSON index: 측정된 query가 없고 쓰기·저장 비용만 늘어난다.

