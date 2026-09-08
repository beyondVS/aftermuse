# 0단계 조사: 최소 Book Knowledge 및 준비 상태 판정

## 결정 1 — `knowledge` 독립 도메인 앱

**Decision**: `BookKnowledge` 모델과 준비 상태 정책을 신규 `knowledge` Django 앱에 둔다.

**Rationale**: Architecture Decisions가 `books`를 ISBN/Metadata와 Provider 연동 경계로,
`knowledge`를 BookKnowledge·Source·Evidence·Candidate·Conflict와 준비 상태의 소유자로
명시한다. Bundle 05A에서는 그 장기 경계 안에 최소 Claim만 먼저 추가하면 이후 확장 때
모델을 이동할 필요가 없다.

**Alternatives considered**:

- 기존 `books` 앱에 추가: 당장은 파일 수가 적지만 명시된 도메인 소유권과 후속
  Source/Evidence 확장 경계를 흐린다.
- `reflections` 앱에 추가: Interview 소비자와 Knowledge 소유자를 결합하므로 제외했다.

## 결정 2 — 최소 Claim 데이터 구조와 제약

**Decision**: `BookKnowledge`는 `Book` foreign key, `kind`, `content`만 가진다. `kind`는
Theme, Argument, Concept, Character, Event의 5개 값이고, `content`는 앞뒤 공백을 제거한
1~500자 문자열이다. `(book, kind, content)` DB UNIQUE, 허용된 kind CHECK와 공백이 아닌
content CHECK를 두고, application validation도 같은 계약을 적용한다.

**Rationale**: Claim 단위 저장과 사용자가 확정한 중복 기준을 가장 직접적으로 표현한다.
500자는 Interview grounding에 사용할 원자적 Claim을 충분히 담으면서 복합 B-tree UNIQUE
index의 과도한 key 크기를 피한다. DB 제약은 직접 ORM·동시 요청에도 invariant를 지키고,
Service validation은 읽기 쉬운 오류를 제공한다.

**Alternatives considered**:

- 무제한 TextField를 UNIQUE에 포함: 긴 다중 바이트 문자열은 index key 한계를 넘을 수 있고
  최소 Claim보다 큰 문서를 허용한다.
- content hash를 별도 저장: 긴 본문 중복에는 유리하지만 이 범위에는 불필요한 파생 상태와
  충돌 검증이 생긴다.
- Source, confidence, generation 필드 선반영: Bundle 05A에서 명시적으로 연기한 운영 모델을
  앞당기므로 제외했다.

## 결정 3 — 준비 상태는 파생 값

**Decision**: `READY`와 `READY_LIMITED`는 저장하지 않는다. Book에 유효한 Claim이 하나라도
존재하면 `READY`, 없으면 `READY_LIMITED`를 Service가 단일 존재 조회로 반환한다.

**Rationale**: 현재 판정 규칙은 Claim 존재 여부와 완전히 동일하므로 상태를 저장하면 Claim
추가·삭제와 상태가 어긋날 수 있다. 파생 판정은 상태 전이, 동기화 작업과 별도 table 없이
명세를 충족한다.

**Alternatives considered**:

- Book에 readiness 필드 추가: 기존 table 변경과 동기화 책임이 생긴다.
- Reading별 준비 상태 저장: 후속 `ReadingPreparation`의 관심사이며 Bundle 05A의 Book 단위
  판정을 넘어선다.
- `FAILED` 포함: 자동 준비 작업이 없는 Core MVP에서는 실행 실패 상태가 필요하지 않다.

## 결정 4 — Service 기반 멱등 Seed

**Decision**: 버전 관리된 JSON은 `book_isbn13`, `kind`, `content`만 담는 입력 데이터로
사용한다. `seed_book_knowledge` management command가 파일을 해석해 Seed Service에
전달하고, Service는 모든 ISBN13과 Claim을 쓰기 전에 검증한 뒤 단일 transaction에서
`(book, kind, 정규화된 content)` 기준으로 멱등 적용한다.

**Rationale**: 모든 영속 상태 변경을 Service Layer에서 수행한다는 헌법을 지키면서 환경별
숫자 PK 비의존, 기존 Book 필수, Book 자동 생성 금지, 반복 실행 무중복, 하나라도 실패하면
전체 rollback이라는 계약을 동시에 만족한다. command는 입력과 결과 보고만 담당한다.

**Alternatives considered**:

- 표준 `loaddata`와 natural key 사용: 영속 변경이 Service Layer를 우회한다.
- 데이터에 고정 숫자 PK 사용: 기존 데이터와 충돌할 수 있고 환경 독립성이 없다.
- Book까지 Seed에 포함: 사용자가 확정한 기존 Book 필수 계약을 위반한다.
- migration data seed: 환경별 검증 데이터를 schema history에 영구 결합한다.

## 결정 5 — 검증용 Seed 도서와 Claim 출처

**Decision**: 서로 다른 질문 유형을 검증할 수 있도록 소설 《1984》
(`9780452284234`)와 논픽션 《Thinking, Fast and Slow》(`9780374275631`) 두 권을 사용한다.
각 책에는 공식 출판사 소개를 한국어로 짧게 재서술한 4개 Theme, Argument, Concept,
Character 또는 Event Claim을 둔다. 원문 문장이나 장문 요약은 복제하지 않으며, 최종
ISBN13·kind·content와 Claim별 출처 대조·승인 기록은
`checklists/seed-knowledge.md`를 기준 원본으로 사용한다.

**Rationale**: 두 권 모두 공식 출판사 페이지에서 ISBN과 핵심 내용을 검증할 수 있는 유명
도서이며, fiction의 Character/Event grounding과 nonfiction의 Argument/Concept grounding을
작은 Seed로 함께 시험할 수 있다.

**Sources**:

- Penguin Random House, 《1984》: https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/
- Macmillan, 《Thinking, Fast and Slow》: https://us.macmillan.com/books/9780374275631/thinkingfastandslow/

**Alternatives considered**:

- 한 장르의 도서 두 권: 최소 유형 분기를 넓게 검증하기 어렵다.
- 프로젝트 테스트의 임의 제목/ISBN 조합 재사용: bibliographic 사실성을 보장하지 못한다.
- 3권 Seed: 명세상 가능하지만 Core MVP의 최소 검증에는 두 장르 두 권이면 충분하다.

## 결정 6 — Service와 조회 계약

**Decision**: Service는 정규화·검증·멱등 등록 결과, Book별 결정적 Claim 목록, Book 단위
준비 상태를 제공한다. Context 목록은 `kind`, `pk` 순으로 고정하고 준비 상태는 `.exists()`
상당의 독립 조회로 계산한다. 외부 HTTP/API 계약은 만들지 않는다.

**Rationale**: View나 Interview 구현 없이도 Bundle 05B가 재사용할 안정된 application
경계를 제공한다. 결정적 순서는 prompt/context snapshot과 테스트의 재현성을 높인다.

**Alternatives considered**:

- Model method에 등록과 판정 정책 배치: 영속 변경과 application 정책을 Model에 집중시킨다.
- 별도 Repository 계층: 단순 ORM 조회에 불필요한 추상화다.
- HTTP endpoint 선구현: 실제 UI 소비자가 없는 현재 범위를 넘어선다.

## 결정 7 — additive 초기 migration

**Decision**: `knowledge`의 `0001_initial`은 기존 table/column을 수정하지 않고 빈
`knowledge_bookknowledge` table, Book FK, CHECK, UNIQUE만 생성한다. 생성 SQL과 migration
왕복을 PostgreSQL에서 검증한다.

**Rationale**: 새 빈 table의 index와 제약 생성은 기존 대용량 table scan을 요구하지 않는다.
Book FK가 참조하는 기존 table에는 짧은 제약 생성 lock만 발생하며 기존 column 변경,
backfill 또는 destructive DDL이 없다. Seed를 위한 `Book` schema·직렬화 변경도 필요 없다.

**Alternatives considered**:

- 기존 `books_book`에 JSON/상태 column 추가: rolling deploy 호환성과 상태 drift 위험이
  생기고 Claim 관계를 표현하기 어렵다.
- FK `NOT VALID`/후속 validate 분리: 신규 빈 child table에는 검증할 기존 행이 없어 추가
  migration 복잡성만 만든다. 실제 `sqlmigrate`가 예상과 다르면 구현 단계에서 재평가한다.

## 미해결 조사 항목

없음.
