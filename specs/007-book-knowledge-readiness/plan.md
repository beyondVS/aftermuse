# 구현 계획: 최소 Book Knowledge 및 준비 상태 판정

**브랜치**: `feature/day-05-minimal-book-knowledge-interview-preparation` | **날짜**: 2026-09-08 | **사양**: [spec.md](spec.md)

**입력**: `/specs/007-book-knowledge-readiness/spec.md`의 기능 사양

## 요약

기존 `Book`과 분리된 `knowledge` Django 앱에 Claim 단위 `BookKnowledge`를 추가한다.
Knowledge 유형과 내용은 application validation과 DB 제약으로 보호하고, Book·유형·정규화된
내용 조합의 유일성으로 일반 등록과 동시 등록의 중복을 막는다. 조회 Service는 Book별
Claim을 결정적 순서로 반환하고, Claim 존재 여부에서 `READY` 또는 `READY_LIMITED`를 매번
파생하여 상태 불일치를 원천 차단한다. 검증용 유명 도서 2권의 수동 JSON Seed 데이터는
전용 management command가 읽고, Seed Service가 모든 ISBN13과 Claim을 선검증한 뒤 단일
transaction에서 적용하여 반복 실행의 멱등성과 전체 rollback 계약을 만족시킨다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1 ORM·management command, 기존 `books.Book`

**저장소**: PostgreSQL 18; 신규 `knowledge_bookknowledge` table, Book foreign key,
허용된 유형·공백이 아닌 Claim CHECK와 Book·유형·내용 복합 UNIQUE 제약

**테스트**: pytest 9.1, pytest-django 4.14, PostgreSQL transaction test, Django
management command, migration SQL·왕복 검증, Ruff 0.16, `scripts/verify.py`

**대상 플랫폼**: Django 기반 Linux Web server와 개발·검증 CLI 환경

**프로젝트 유형**: 서버 렌더링 단일 Django Web application의 내부 도메인 기능

**성능 목표**: Book별 준비 상태 판정은 단일 존재 조회, Context용 Claim 목록은 단일
조회로 수행한다.

**제약 조건**: Seed 실행 전 모든 대상 Book 존재 필수, 외부 I/O 없음, Book 자동 생성
금지, 동일 Book·유형·내용 Claim 중복 금지, Seed 전체 transaction rollback, 준비 상태
비영속 파생, 사용자 기록의 공용 Knowledge 승격 금지, Source/Evidence/Conflict·자동
Research·UI·Interview·Credit side effect 없음

**규모/범위**: 신규 도메인 앱·table 각 1개, Knowledge 유형 5개, 수동 Seed 도서 2권,
각 도서의 소수 Claim, 등록·조회·준비 상태·Seed Service와 모델·command·migration 테스트

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| I. 사용자 생각의 충실성 | Knowledge가 없는 Book은 `READY_LIMITED`로 판정해 후속 Interview가 책 내용을 안다고 전제하지 않게 한다. | 통과 |
| II. 핵심 제품 루프와 범위 규율 | 수동 Seed 기반 최소 Knowledge와 판정만 구현하고 자동 Research, Backoffice, Interview 생성은 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 버전 관리되고 출처 대조가 승인된 수동 Seed만 공용 Knowledge로 허용한다. management command는 입력 경계만 담당하고 모든 영속 변경은 Seed Service에서 수행한다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | Architecture Decisions의 `knowledge` 도메인에 모델과 Service를 두며 내부 HTTP API, Repository, background job, 신규 의존성을 추가하지 않는다. | 통과 |
| V. 증거 기반 품질 | DB 제약, 중복·동시성, Book별 격리, 상태 판정, 반복 Seed, 누락 Book 전체 rollback과 migration 왕복을 PostgreSQL 테스트로 검증한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff를 유지한다. | 통과 |
| 데이터 무결성 | application normalization과 유형·공백 방지 DB CHECK, UNIQUE·FK를 겹치고 Seed Service가 전체 데이터를 짧은 transaction으로 적용한다. | 통과 |
| Migration 안전성 | 기존 table을 변경하지 않는 신규 빈 table의 additive 초기 migration이다. FK·CHECK·UNIQUE 생성 SQL을 `sqlmigrate`로 확인하고 왕복 migration을 검증한다. | 통과 |
| 신뢰 가능한 Seed | 도서·Claim 선택 근거를 `research.md`에 남기고 `checklists/seed-knowledge.md`에서 Claim별 출처 대조를 승인한 뒤 짧은 한국어 요약 Claim만 Seed에 포함한다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다. 관리 명령은 JSON 해석과
결과 보고만 담당하고, 기존 Book 조회·검증·저장은 Seed Service의 원자적 경계에서 수행한다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/007-book-knowledge-readiness/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── seed-knowledge.md             # Claim별 공식 출처 대조·승인 기록
├── contracts/
│   ├── seed-fixture-contract.md
│   └── service-contract.md
└── tasks.md                         # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── config/
│   └── settings.py                  # knowledge 앱 등록
└── knowledge/
    ├── apps.py
    ├── management/commands/
    │   └── seed_book_knowledge.py   # JSON 입력·결과 보고 경계
    ├── migrations/
    │   └── 0001_initial.py          # 신규 table·FK·CHECK·UNIQUE
    ├── models.py                    # Claim 구조·유형·DB invariant
    ├── seed_data/
    │   └── book_knowledge.json      # ISBN13 기반 수동 Claim 데이터
    └── services.py                  # 등록·조회·준비 상태·원자적 Seed 적용

tests/
└── knowledge/
    ├── test_seed_command.py          # 반복 적용·누락 Book·전체 rollback
    ├── test_migrations.py           # 신규 table SQL·왕복 migration
    ├── test_models.py               # 유형·내용·유일성·Book 격리
    └── test_services.py             # 등록·동시성·조회·READY 판정
```

**구조 결정**: 제품 Architecture Decisions가 `BookKnowledge`, Source, Evidence, Candidate와
Knowledge 상태를 `knowledge` 도메인으로 분리하므로 신규 `knowledge` 앱이 최소 Claim과
판정과 Seed 영속 변경을 소유한다. Seed 데이터의 ISBN13은 Service가 기존 `Book`을 일괄
조회하는 식별자이며 `books` 앱의 직렬화 계약은 변경하지 않는다. UI·URL·Template은 Bundle
05B 이후 책임이므로 생성하지 않는다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
