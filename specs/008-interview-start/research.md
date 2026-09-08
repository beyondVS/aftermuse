# 0단계 조사: 인터뷰 시작

## 결정 1: `reflections` 앱이 Interview 도메인을 소유한다

**Decision**: 신규 `reflections` Django 앱에 `Interview`, `InterviewTurn`, 시작 Service와 Web 경계를 둔다.

**Rationale**: Architecture Decisions가 reflections 도메인에 Interview, Turn, Reflection과 Coverage를 배치한다. Reading은 독서 경험 lifecycle을, knowledge는 공용 Book Knowledge를 이미 소유한다.

**Alternatives considered**: `readings` 앱은 lifecycle과 Interview Engine 책임을 결합하고, `knowledge` 앱은 사용자별 Working Data의 소유자가 아니며, 별도 `interviews` 앱은 향후 Reflection까지 같은 경계에 둔 승인 architecture와 어긋난다.

## 결정 2: Reading OneToOne과 확정 Book 스냅샷을 함께 저장한다

**Decision**: `Interview.reading`을 OneToOne으로 두고 `book`을 별도 FK로 보존한다. 소유자는 중복 저장하지 않고 `reading.user`에서 파생한다. client는 이 값을 지정하지 않는다.

**Rationale**: OneToOne UNIQUE가 Reading당 전체 수명 Interview 한 개를 DB에서 보장한다. Book FK는 시작 당시 대상의 provenance를 명시하고, user 중복 저장을 피하면 교차 관계 불변조건을 줄인다.

**Alternatives considered**: Reading만 저장하면 확정 Book 추적이 간접적이고, user까지 저장하면 불일치 가능성이 늘며, DB trigger는 현 ORM 관례와 규모에 과도하다.

## 결정 3: readiness와 Interview 상태는 시작 시점 값으로 보존한다

**Decision**: `knowledge_readiness`는 시작 시점의 `READY`/`READY_LIMITED`를 저장하고, status는 `IN_PROGRESS`, `REFLECTION_READY`, `COMPLETED`를 지원한다.

**Rationale**: 이후 Knowledge가 바뀌어도 Interview가 실제 사용한 출발 조건을 재현해야 한다. 상태는 Architecture Decisions와 명확화된 재진입 목적지의 최소 lifecycle이다.

**Alternatives considered**: readiness 재계산은 과거 질문 정책의 재현성을 없애고, 별도 Preparation 모델은 자동 Research가 없는 Core MVP에 불필요하며, Coverage와 status 결합은 승인된 분리 원칙을 위반한다.

## 결정 4: Reading 행 잠금과 DB UNIQUE로 시작 멱등성을 보장한다

**Decision**: `start_interview(user, reading)`은 짧은 transaction에서 소유자 범위 Reading을 잠그고 완독 여부를 재검증한다. 기존 Interview면 재사용하고, 없으면 readiness를 계산해 생성한다.

**Rationale**: 같은 Reading의 시작과 완독 정보 변경이 하나의 직렬화 기준을 공유한다. OneToOne UNIQUE가 최종 방어이며, 경쟁 `IntegrityError`는 동일 Reading의 기존 Interview가 확인될 때만 복구한다.

**Alternatives considered**: 사전 `exists()`만으로는 race를 막지 못하고, user 행 잠금은 서로 다른 Reading까지 직렬화하며, application lock/cache는 불필요한 운영 의존성이다.

## 결정 5: Turn은 관계형 순서와 미응답 상태를 명시한다

**Decision**: Turn은 Interview FK, 1부터 시작하는 sequence, 1~2,000자의 question, nullable answer와 시점을 가진다. `(interview, sequence)` UNIQUE와 양수/비공백 CHECK를 적용한다. 이 Bundle은 Turn을 생성하지 않는다.

**Rationale**: 개별 질문·답변 provenance와 안정된 순서를 보존하고 미제출 답변을 구분한다. 복합 UNIQUE의 선행 Interview column이 조회를 지원하므로 중복 FK index는 만들지 않는다.

**Alternatives considered**: JSON 배열은 개별 제약과 grounding 추적이 약하고, 빈 문자열 미응답은 상태가 모호하며, 전체 질문 사전 생성은 고정 설문지 금지와 충돌한다.

## 결정 6: 확인 GET과 확정 POST를 분리한다

**Decision**: Reading CTA는 책 확인 GET으로 연결하고 별도 CSRF POST만 Service를 호출한다. 확인 화면은 확보된 서지정보, 변경 불가 안내와 조건부 `READY_LIMITED` 안내를 표시한다.

**Rationale**: GET을 무부작용으로 유지하고 명시적 확정만 상태를 바꾼다. 기존 function view, method decorator, server-rendered template 관례를 재사용하며 전체 페이지 확인은 HTMX 계약을 넓히지 않는다.

**Alternatives considered**: Modal은 focus/history/no-JS 복잡성이 크고, GET 생성은 HTTP semantics를 위반하며, JSON API는 API-first 금지와 맞지 않는다.

## 결정 7: 상태별 재진입은 목적지 계약을 먼저 고정한다

**Decision**: `IN_PROGRESS`는 Interview 화면, `REFLECTION_READY`는 후속 Reflection 생성·확인 경계, `COMPLETED`는 후속 완성 Reflection 경계로 해석하는 resolver를 둔다. 이번 Bundle은 실제 생성 가능한 `IN_PROGRESS` 화면만 완성한다.

**Rationale**: 명확화된 재진입 정책을 보존하면서 아직 구현 순서가 오지 않은 Reflection 데이터나 가짜 화면을 선구현하지 않는다.

**Alternatives considered**: 모든 상태를 Interview 화면으로 보내면 계약을 위반하고, 존재하지 않는 URL을 미리 reverse하면 현재 release가 실패하며, 가짜 Reflection 데이터는 범위를 넘는다.

## 결정 8: 신규 빈 테이블의 단일 additive migration을 사용한다

**Decision**: `reflections/migrations/0001_initial.py` 하나에서 두 신규 table과 FK, CHECK, UNIQUE를 생성하며 data migration이나 기존 table 변경은 하지 않는다.

**Rationale**: 빈 table의 inline 제약은 기존 대형 child table을 검사하지 않는다. concurrent index, `NOT VALID`/`VALIDATE`, migration 분할과 `lock_timeout`은 이 schema에 이점이 없다. 실제 SQL과 PostgreSQL 왕복으로 검증한다.

**Alternatives considered**: 모든 제약을 두 단계로 추가하면 복잡성만 늘고, Turn FK standalone index는 복합 UNIQUE와 중복되며, Seed migration은 사용자 행동 생성 원칙을 위반한다.
