# Phase 0 Research: Reading 생성 및 완독 관리

## 1. 도메인 앱 경계

**Decision**: `Reading`을 신규 `readings` Django 앱이 소유하고 기존 `books.Book`과
`accounts.User`를 참조한다.

**Rationale**: 프로젝트 Architecture Decisions가 `readings`를 `Reading`,
`ReadingEntry`, `ReadingPreparation`의 도메인 경계로 정의한다. 이번 Bundle은 첫 엔터티만
구현하되 후속 Reading Context와 Interview가 같은 경계를 확장할 수 있다.

**Alternatives considered**:

- `books` 앱에 추가: 초기 파일 수는 줄지만 Book 서지정보와 사용자 독서 경험의 소유권이
  섞여 문서의 도메인 결정을 위반한다.
- 범용 `journal` 앱: 현재 범위에 없는 추상화를 미리 도입한다.

## 2. 상태와 완독일 invariant

**Decision**: `status`는 `want_to_read`, `reading`, `completed` 세 값만 허용한다.
`completed`이면 `completed_on`이 필수이고, 다른 상태에서는 `completed_on`이 `NULL`이어야
한다. 오늘 이후 날짜는 Form과 Service에서 거부한다.

**Rationale**: 상태와 날짜를 한 transaction에서 바꾸고 DB CHECK로 구조적 불일치를
막는다. 현재 날짜는 시간이 흐르는 값이므로 DB CHECK predicate에 넣지 않고 요청 시점의
application validation으로 검증한다. Django `CheckConstraint`는 `Q` 조건을 DB 제약으로
표현한다. [Django constraints](https://docs.djangoproject.com/en/6.1/ref/models/constraints/)

**Alternatives considered**:

- 완독 여부를 별도 boolean으로 중복 저장: `status`, boolean, 날짜 사이에 추가 불일치가
  생긴다.
- 미래 날짜까지 DB CHECK로 제한: 현재 날짜 의존 제약은 시간이 지나며 의미가 변하고
  index/check 표현의 안정성을 해친다.
- `completed_at` datetime: 제품 계약은 사용자가 선택하는 달력 날짜이며 시각 정밀도가
  필요하지 않다.

## 3. 활성 Reading 유일성과 동시 생성

**Decision**: `want_to_read`와 `reading`을 활성 상태로 정의하고 `(user, book)`에 조건부
`UniqueConstraint`를 둔다. 생성/재독 Service는 짧은 `transaction.atomic()` 안에서 현재
사용자 행을 `select_for_update()`로 잠근 뒤 기존 Reading을 다시 확인한다.

**Rationale**: Reading 행이 아직 없을 때는 행 잠금만으로 경쟁 요청을 직렬화할 수 없다.
사용자 행 잠금은 서로 다른 사용자를 막지 않으면서 같은 사용자의 첫 생성 경쟁을 정렬하고,
조건부 unique index는 Service 밖 쓰기에도 최종 invariant를 지킨다. Django의 조건부
`UniqueConstraint`는 PostgreSQL unique partial index로 구현되며, PostgreSQL은 `WHERE`
predicate가 있는 unique index로 일부 행에만 유일성을 강제한다.
[Django UniqueConstraint](https://docs.djangoproject.com/en/6.1/ref/models/constraints/#uniqueconstraint),
[PostgreSQL partial unique indexes](https://www.postgresql.org/docs/18/sql-createindex.html)

완독 Reading을 활성 상태로 되돌릴 때 다른 활성 Reading이 있으면 변경을 거부하고 그 활성
Reading으로 이동할 수 있게 한다. 이는 “활성 Reading 최대 한 건”과 “과거 완독 기록 보존”을
동시에 유지하기 위한 필연적인 충돌 처리다.

**Alternatives considered**:

- application의 사전 `exists()` 검사만 사용: 동시 요청 사이 race condition을 막지 못한다.
- Book 행 잠금: 같은 Book을 선택한 서로 다른 사용자까지 불필요하게 직렬화한다.
- advisory lock 또는 별도 idempotency table: 현재 규모와 계약에 비해 복잡하다.
- 모든 `(user, book)` 조합 unique: 같은 책 재독을 별도 Reading으로 보존할 수 없다.

## 4. 생성·재독 Service 분리

**Decision**: 최초 생성과 재독 시작은 별도 Service entry point로 구분하되 공통 내부 생성
정책을 공유한다. 최초 생성은 Reading 이력이 없을 때만, 재독은 소유자의 완독 Reading에서
`다시 읽기`를 명시하고 활성 Reading이 없을 때만 허용한다.

**Rationale**: client flag 하나로 두 의도를 구분하면 조작되거나 중복 제출됐을 때 자동
재독이 생기기 쉽다. 출발 엔터티와 서버 상태를 함께 검증하는 두 command가 제품 계약을
직접 표현한다.

**Alternatives considered**:

- 범용 `get_or_create_reading()` 하나: 최초/재독의 서로 다른 사전 조건과 오류가 숨겨진다.
- Book 선택 즉시 생성: 명시적 상태 선택 전에는 Reading을 만들지 않는 확정 UX와 충돌한다.

## 5. Book 선택 이후 Web 흐름

**Decision**: Book 선택 성공 후 명명된 Reading Book-entry GET으로 이동한다. 일반 요청은
redirect, HTMX 요청은 `HX-Redirect`를 사용해 동일한 전체 페이지로 전환한다. Entry 화면은
활성 Reading이 있으면 상세로 안내하고, 이력이 없으면 초기 상태 선택, 완독 이력만 있으면
최근 완독 상세와 명시적 재독 선택을 제공한다.

**Rationale**: 기존 검색/선택 Fragment 안에 Reading 정책을 넣지 않고, JavaScript 유무와
관계없이 동일 URL이 다음 흐름의 정본이 된다. View는 Form 검증과 Service 호출만 조합한다.

**Alternatives considered**:

- 선택 결과 Fragment에 모든 Reading UI 삽입: `books` 화면과 View가 Reading 상태 정책을
  소유하게 된다.
- JSON API/SPA: 헌법의 서버 렌더링 단일 Web 구조보다 복잡하다.

## 6. Day 04의 Interview CTA 경계

**Decision**: 완독 상세에 `AI 독서노트 만들기` CTA와 다음 단계 설명을 표시하되 Day 04에는
비활성 상태로 렌더링한다. Interview endpoint, Knowledge 준비, Credit 변경은 만들지 않고
Day 05에서 같은 위치를 실제 시작 GET에 연결한다.

**Rationale**: IMP-033의 “CTA를 볼 수 있다”를 충족하면서 존재하지 않는 기능으로 보내는
깨진 링크나 조기 side effect를 피한다. UI는 `disabled` 또는 `aria-disabled`와 텍스트를
함께 제공해 색상에만 의존하지 않는다.

**Alternatives considered**:

- 임시 Interview endpoint: Day 05 책임과 placeholder 화면을 미리 구현한다.
- 동작하지 않는 링크: 키보드와 보조 기술 사용자에게 잘못된 affordance를 준다.
- CTA 미표시: IMP-033 완료 조건을 충족하지 못한다.

## 7. Migration 전략

**Decision**: 신규 앱의 단일 `0001_initial` migration에서 빈 Reading table, FK, CHECK와
조건부 unique index를 함께 생성한다. 적용 전 `sqlmigrate`, 적용/역방향 round-trip과
`makemigrations --check --dry-run`을 검증한다.

**Rationale**: 기존 table이나 행을 변경하지 않는 additive schema이고 old code는 새 table을
참조하지 않으므로 rolling deploy 호환성이 있다. 조건부 unique index도 빈 신규 table에서
생성되어 기존 대형 table에 inline index를 추가하는 위험이 없다. 생성 SQL에 기존 table을
장시간 잠그는 예상 밖 DDL이 보이면 구현 단계에서 migration을 분리한다.

**Alternatives considered**:

- `AddIndexConcurrently`를 위한 별도 migration: 빈 신규 table에서는 추가 복잡성만 생긴다.
- FK `NOT VALID`/후속 VALIDATE 분리: child table이 새로 생성되어 기존 row scan이 없다.
- 기존 `books` migration 수정: 적용된 migration 이력을 훼손한다.

## 8. 검증 전략

**Decision**: 빠른 모델/Form/View 테스트와 PostgreSQL 실제 제약·transaction 테스트를
분리한다. 동시 생성은 `transaction=True`, thread별 DB connection과 barrier로 검증하고,
migration은 빈 DB 기준 정방향·역방향을 검증한다. 외부 Provider는 호출하지 않는다.

**Rationale**: 핵심 위험은 Django 코드 모양이 아니라 DB invariant, race condition,
소유권과 화면 결과다. 기존 프로젝트가 같은 PostgreSQL 동시성·migration test 패턴을
사용한다.

**Alternatives considered**:

- Service 전체를 mock한 View test: 내부 상태 전이와 rollback 결함을 가린다.
- SQLite 단위 테스트: 조건부 index와 PostgreSQL transaction 동작을 대표하지 못한다.
- browser 검증만 수행: 동시성과 DB 제약을 재현하기 어렵다.

## 조사 결론

모든 기술적 결정이 기존 코드·프로젝트 헌법과 공식 문서로 해소되었으며 미해결 항목은
없다.
