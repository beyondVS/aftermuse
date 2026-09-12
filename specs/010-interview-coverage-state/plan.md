# 구현 계획: Interview Coverage 상태

**브랜치**: `codex/day-07-adaptive-interview-loop` | **날짜**: 2026-09-10 | **사양**: [spec.md](spec.md)

**입력**: `/specs/010-interview-coverage-state/spec.md`의 기능 사양

## 요약

진행 중 Interview에 `MEMORY`, `REACTION`, `CONNECTION`, `AFTERTHOUGHT` 네 축의
`UNCOVERED`/`PARTIAL`/`COVERED` 상태를 JSONB로 보존한다. 기존 Interview 행은 네 축이 모두
`UNCOVERED`인 canonical object로 안전하게 backfill하고, 애플리케이션과 DB 기본값을 함께 두어
rolling deploy 중 이전 코드가 만드는 행도 유효하게 한다. Service는 사용자 소유 Interview 행을
잠근 짧은 transaction에서 전체 patch를 검증하고 단방향 상태 상승만 원자적으로 저장한다.
Answer Analysis, 다음 질문, Soft Stop과 UI는 이 Bundle에 연결하지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, Psycopg 3.3

**저장소**: PostgreSQL 18의 `jsonb` (`Interview.coverage`)

**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16, Django system/migration checks

**대상 플랫폼**: PostgreSQL에 연결되는 Django server-rendered Web 애플리케이션

**프로젝트 유형**: 단일 Django Web 애플리케이션

**성능 목표**: 한 Interview의 Coverage 조회는 단일 행 조회로, 변경은 잠금 조회와 단일 행
update로 끝내며 외부 I/O를 수행하지 않는다.

**제약 조건**: PostgreSQL만 지원한다. 네 축의 상태는 하락할 수 없고, 다중 축 patch는 전부
성공하거나 전부 rollback되어야 한다. 다른 사용자 데이터와 대상 존재 여부를 노출하지 않는다.
Coverage 변경은 Interview status, Turn, 답변, 질문, Reflection, Credit과 Knowledge를 바꾸지
않는다. 실제 브라우저 검증은 요구하지 않는다.

**규모/범위**: Interview당 고정 Core 축 4개와 3단계 상태만 저장한다. Focus Coverage, 수치
score, 상태 이력, 외부 API와 사용자 편집 UI는 범위 밖이다.

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며, 1단계 설계 후 동일 기준으로 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 사전 | 설계 후 |
| --- | --- | --- | --- |
| I. 사용자 생각의 충실성 | Coverage는 사용자의 확정 답변 이후 제공된 patch만 저장하며 자체 의미 분석이나 내용을 생성하지 않는다. | 통과 | 통과 |
| II. 핵심 제품 루프와 범위 규율 | 고정 설문지 대신 다음 질문의 기준이 되는 Core Coverage 상태만 완성하고 07B·07C·08A 책임을 분리한다. | 통과 | 통과 |
| III. 신뢰 경계와 데이터 통제 | patch 전체를 enum·shape·단방향 규칙으로 검증하고, 소유자 범위의 진행 중 Interview를 Service가 잠가 변경한다. | 통과 | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 `reflections` aggregate의 JSONB 후보와 Service 패턴을 사용하며 신규 앱, API, Repository 또는 의존성을 만들지 않는다. | 통과 | 통과 |
| V. 증거 기반 품질 | 실제 PostgreSQL에서 상태, rollback, 소유권, 반복·동시 변경과 migration SQL을 결정적으로 검증한다. | 통과 | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff와 기존 verify 명령을 유지한다. | 통과 | 통과 |
| Migration 안전성 | `db_default`로 이전 코드 insert를 보호하고, `ACCESS EXCLUSIVE` DDL은 짧은 metadata 변경과 `lock_timeout`으로 제한하며 CHECK 검증은 write를 막지 않는 단계로 분리한다. | 통과 | 통과 |

헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 0단계: 조사 결과

세부 결정과 대안은 [research.md](research.md)에 기록했다. 미해결 `NEEDS CLARIFICATION`은 없다.

핵심 결정은 다음과 같다.

- Coverage는 별도 행 집합이 아니라 `Interview` aggregate 내부의 canonical JSONB object로 둔다.
- Python default와 PostgreSQL `db_default`를 같은 네 축 초기값으로 유지한다.
- Service 입력은 중복 축을 식별할 수 있는 patch 항목 sequence이며, 모든 항목을 검증한 뒤 저장한다.
- 동시 변경은 Interview 행 잠금 아래 최신 상태와 다시 비교하여 축별 최고 유효 상태로 수렴시킨다.
- JSON 검색 인덱스는 추가하지 않는다. 조회 경로가 Interview 식별자·소유권을 사용하기 때문이다.

## 1단계: 설계 및 계약

- [data-model.md](data-model.md): JSON shape, validation, 상태 전환과 migration 전략
- [contracts/service-contract.md](contracts/service-contract.md): Coverage 조회·patch application 계약
- [quickstart.md](quickstart.md): migration SQL, 상태 전환, 원자성·동시성·회귀 검증 절차

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/010-interview-coverage-state/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── service-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md                 # $speckit-tasks가 생성
```

### 소스 코드 (저장소 루트)

```text
src/reflections/
├── models.py                # Coverage 기본 shape와 Interview JSONField
├── services.py              # 소유권·상태 검증, 원자적 단방향 patch
└── migrations/
    ├── 0002_*.py            # db_default를 포함한 coverage column 추가
    └── 0003_*.py            # NOT VALID + VALIDATE CHECK와 model state 정합화

tests/reflections/
├── test_models.py           # default, shape, 상태 enum 검증
├── test_services.py         # 조회, 전환, rollback, 격리, 멱등성·동시성
└── test_migrations.py       # 기존 행 backfill, DB default·CHECK, reverse 검증
```

**구조 결정**: Architecture Decisions가 Interview, Turn, Coverage와 정책의 소유권을
`reflections`에 두므로 기존 앱을 확장한다. Coverage는 Interview의 고정 소규모 aggregate이며
별도 public Web/API 계약이 없으므로 모델과 application Service만 추가한다.

## Migration 실행 전략

1. `0002`에서 네 축이 모두 `UNCOVERED`인 immutable JSON literal을 Python default와
   PostgreSQL `db_default`로 가진 non-null JSONB column을 추가한다. PostgreSQL 18의 constant
   default 경로로 기존 행을 metadata-only 기본값으로 채우되 실제 SQL을 `sqlmigrate`로 확인한다.
2. `ALTER TABLE ... ADD COLUMN`의 짧은 `ACCESS EXCLUSIVE` 대기를 무제한 허용하지 않는다.
   구현 시 배포 정책의 값을 확인하고, 별도 값이 없으면 기본 후보 `2s`의 transaction-local
   `lock_timeout`을 DDL 직전에 둔다.
3. `0003`은 canonical object만 허용하는 CHECK를 `NOT VALID`로 추가한 뒤 별도 operation에서
   `VALIDATE CONSTRAINT`한다. `atomic = False`로 검증 transaction과 앞선 잠금을 분리하고,
   `NOT VALID` DDL의 timeout과 SQL은 같은 `RunSQL` operation에 둔다.
4. Django migration state에는 동등한 `CheckConstraint`를 `SeparateDatabaseAndState`로 기록한다.
   모든 `RunSQL`에는 reverse SQL을 제공한다.
5. 구버전 애플리케이션은 `db_default` 덕분에 coverage를 지정하지 않고도 유효한 Interview를
   만들 수 있고, 신버전은 callable Python default로 즉시 canonical dict를 얻는다.

구현 단계에서는 두 migration의 실제 SQL을 `sqlmigrate`로 확인하고, `ACCESS EXCLUSIVE` 범위,
default 유지 여부, `NOT VALID`/`VALIDATE`, reverse SQL과 migration state를 검토해야 한다.

