# 조사: Reflection 결과·수정과 Home 재진입

## 1. Reflection 완료 상태와 표준 CHECK 교체

**Decision**: 새 컬럼 없이 기존 `status`에 `COMPLETED`를 추가하고 `completed_at`과의
일관성을 CHECK로 강제한다. Core MVP에서는 과도한 2단계 배포 하드닝을 피하고 표준 단일
Django migration(`0010_reflection_completed_status.py`)으로 처리한다.

**Rationale**: 기존 모델이 이미 미래 완료를 위해 nullable `completed_at`과 20자 status를
보유하므로 새 컬럼이나 backfill이 필요 없다. 기존 DRAFT 행은 새 제약을 만족하며,
Core MVP의 단일 애플리케이션 환경에서는 표준적인 Django migration으로 충분하다.

**Alternatives considered**: `Finalizing` 상태까지 강제하는 방식은 실제 비동기/다단계
완료 처리가 없는 Core MVP에 불필요한 복잡성을 더하므로 제외한다. 2단계 `NOT VALID` +
`VALIDATE CONSTRAINT` 배포 분리는 대규모 실운영 트래픽 하드닝이므로 Core MVP에서는 선행하지 않는다.

## 2. 저장·완료 트랜잭션과 소유권 격리

**Decision**: 낙관적 동시성 토큰(`expected_updated_at`)이나 복잡한 행 잠금(`select_for_update`)을
도입하지 않고, 소유자 검증(owner scope), DRAFT 상태 검증 및 Service 단위의 짧은 DB 트랜잭션으로
완결한다. 완료 시 Reflection과 Interview를 같은 트랜잭션 안에서 일관되게 COMPLETED로 전환한다.

**Rationale**: Core MVP의 실제 사용자 핵심 흐름 검증에서는 기본적인 소유자/상태 검사와
트랜잭션 원자성으로 충분하다. 여러 브라우저 탭에서의 극단적인 동시 수정 충돌을 이번 단계에서
미리 과잉 설계하지 않는다. 이미 완료된 Reflection에 대한 수정 요청은 단호하게 거부하며,
완료 요청이 중복 전송된 경우 추가 쓰기 없이 완료 상태를 유지하는 단순 가드로 충분하다.

**Alternatives considered**: revision token과 409 Conflict 프로토콜은 Core MVP에 불필요한
상태 관리와 클라이언트 복구 프로토콜 비용을 발생시킨다.

## 3. Markdown 렌더링과 사용자 입력 안전성

**Decision**: Python-Markdown 등 최소 parser를 사용해 headings, 문단, 목록, 인용, 강조 등
독서노트의 기본 Markdown 구조를 지원하되, 사용자 작성 raw HTML이 브라우저에서 실행되지
않도록 안전하게 처리한다. 사용자 수정 Form 검증에서는 비공백과 최대 길이(20,000자)를
적용하며, Prompt injection 키워드 블랙리스트는 적용하지 않는다.

**Rationale**: 사용자가 직접 작성하는 독서 에세이에 '관리자 권한', '시스템 상태' 등 일반적인
단어를 금지하는 것은 LLM I/O 경계의 방어를 사용자 입력에 잘못 투영한 과잉 검증이다.
사용자 입력의 진짜 보안 불변식은 "작성한 raw HTML이 실행되지 않는다"이므로, 렌더링 시
안전하게 처리하는 것으로 보안을 보장한다.

**Alternatives considered**: 링크/이미지 문법을 차단하기 위해 복잡한 거대 정규식 검증기를
새로 작성하는 것은 또 다른 취약점과 과잉 설계를 유발하므로, Core MVP에서는 기본적인
마크다운 표현 렌더링에 집중한다.

## 4. 서버 렌더링 Interaction 계약

**Decision**: 결과는 GET, 수정은 GET/POST, 완료는 별도 GET 확인/POST로 제공한다. POST
성공은 결과 화면으로 redirect하는 PRG 패턴을 사용한다. Form validation 실패 및 COMPLETED 상태에서의
수정 시도는 400으로 처리하고, 타인 또는 존재하지 않는 기록은 404로 통일한다. 일반 DB 실패는
트랜잭션 롤백과 프레임워크 기본 오류 처리에 위임한다.

**Rationale**: 완료 confirmation GET의 side effect를 막고 새로고침 재전송을 피한다.
기존 Django function view와 Form 관례를 유지하며 불필요한 409 stale conflict나 503
persistence 프로토콜을 제거해 HTTP 의미 구조를 단순하고 명확하게 유지한다.

**Alternatives considered**: 일반 persistence 실패에 대해 별도 503 HTTP 프로토콜을
규정하는 것은 외부 서비스(LLM) 장애와 일반 DB 에러를 혼동한 과잉 설계이므로 배제한다.

## 5. Home 최신 기록 조회

**Decision**: `Reflection.objects.filter(interview__reading__user=user)`를
`updated_at DESC, id DESC`로 정렬해 하나만 가져오고 책까지 `select_related`한다. DRAFT와
COMPLETED를 모두 포함하며 사용자 상태 label을 각각 `작성 중`, `완료`로 표현한다.

**Rationale**: clarification에서 생성·수정·완료 중 마지막 활동을 최근 기준으로 확정했다.
동률에서 PK 역순은 결정론을 제공한다. 기존 Home Reading loop에 reflection prefetch를 섞는
것보다 단일 bounded query가 선택 규칙과 query count를 명확히 한다.

**Alternatives considered**: 최초 생성일 기준은 방금 수정한 오래된 기록으로의 복귀를 막는다.
완료본만 표시하면 초안 재진입 요구를 위반한다. 모든 Reflection을 가져와 Python에서 정렬하면
사용자 기록 수에 비례해 메모리와 query payload가 늘어난다.

## 6. 검증용 책 세트의 재사용과 READY_LIMITED 보장

**Decision**: 기존 승인 Seed의 《1984》와 《Thinking, Fast and Slow》을 각각 fiction READY,
nonfiction READY로 재사용한다. 제한 책은 공식 출판사 ISBN이 확인된
《The Left Hand of Darkness》(`9780143111597`)를 생성하되 Knowledge Claim을 추가하지 않는다.
새 command는 세 Book 준비와 기존 Seed 적용을 orchestrate하고 LIMITED 대상에 Knowledge가
있으면 삭제 대신 실패한다.

**Rationale**: 승인된 8개 Claim과 멱등 Service를 중복하지 않으면서 사용자 합의인
소설 READY 1권·비문학 READY 1권·READY_LIMITED 1권을 정확히 만든다. LIMITED 보장을 위해
기존 데이터를 삭제하면 외부 영향을 확대하므로, 불일치를 명시적으로 보고하는 것이 안전하다.

**Alternatives considered**: 테스트용 가상 책은 실제 Day 13 제품 검증의 현실성을 낮춘다.
기존 seed command가 Book까지 생성하게 바꾸면 “Seed는 Book을 만들지 않는다”는 승인 계약을
깨뜨린다. LIMITED 책의 Knowledge를 자동 삭제하면 복구하기 어려운 데이터 변경이 된다.

**Source**: [Penguin Random House — The Left Hand of Darkness, ISBN 9780143111597](https://www.penguinrandomhouse.com/books/538943/the-left-hand-of-darkness-by-ursula-k-le-guin/)
