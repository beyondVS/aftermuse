# 1단계 데이터 모델: 최소 Book Knowledge 및 준비 상태 판정

## 관계 개요

```text
Book 1 ─── 0..N BookKnowledge
                 │
                 └── kind + content = 단일 Claim

BookKnowledge 존재 ── yes ──> READY
                    └─ no  ──> READY_LIMITED
```

준비 상태는 별도 엔터티나 column이 아니라 현재 BookKnowledge 존재 여부에서 파생되는
application 값이다.

## Book (기존)

### 기존 필드

- `id`: 내부 `BigAutoField` primary key
- `isbn13`: ASCII 숫자 13자리, unique
- `title` 및 기존 선택 서지정보

### 규칙

- Seed Service는 입력의 ISBN13으로 이미 존재하는 Book을 일괄 조회한다.
- 조회되지 않는 ISBN13을 대신할 Book을 추측하거나 생성하지 않는다.

## BookKnowledge (신규)

### 필드

| 필드 | 형태 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | 내부 식별자 | 예 | 프로젝트 기본 `BigAutoField` |
| `book` | Book 관계 | 예 | 기존 Book 참조, Book 삭제 시 종속 Claim 삭제 |
| `kind` | 짧은 열거 문자열 | 예 | `theme`, `argument`, `concept`, `character`, `event` 중 하나 |
| `content` | Claim 문자열 | 예 | 앞뒤 공백 제거 후 1~500자 |

### 표시 이름

| 저장값 | 표시 의미 |
| --- | --- |
| `theme` | Theme |
| `argument` | Argument |
| `concept` | Concept |
| `character` | Character |
| `event` | Event |

### 관계

- 한 `Book`은 0개 이상의 `BookKnowledge` Claim을 가진다.
- 한 `BookKnowledge`는 정확히 한 `Book`에 속한다.
- 사용자, Reading, Interview, Source, Evidence, Candidate와의 관계는 이 기능에서 없다.

### 유효성 규칙

- `kind`는 정의된 5개 값 중 하나여야 한다.
- `content`는 앞뒤 공백을 제거한 뒤 비어 있지 않고 500자를 넘지 않아야 한다. 내부 공백과
  대소문자는 보존한다.
- application validation과 DB CHECK가 허용되지 않은 kind 및 빈 문자열·공백-only
  content를 거부한다.
- `(book, kind, content)` 조합은 DB에서 unique하다.
- Book, kind 또는 content 중 하나가 다르면 별도 Claim이다.

### 조회 및 순서

- Context용 Book별 Claim은 `kind`, `id` 오름차순으로 반환한다.
- Book FK index와 `(book, kind, content)` unique index가 Book 범위 조회를 지원한다.
- 별도 범용 index는 현재 규모와 쿼리 계약에 필요하지 않다.

## BookKnowledgeReadiness (파생 값)

### 값

- `READY`: 대상 Book에 유효한 BookKnowledge가 하나 이상 존재
- `READY_LIMITED`: 대상 Book에 유효한 BookKnowledge가 없음

### 전이

```text
Claim 0개 ── 첫 Claim 등록 ──> READY
READY ── 마지막 Claim 제거 ──> READY_LIMITED
```

Bundle 05A에는 Claim 삭제 Service가 없지만, 판정은 저장된 상태가 아니라 현재 존재 여부에서
계산하므로 관리 작업이나 테스트에서 마지막 Claim이 사라져도 자동으로 일치한다.

### 불변조건

- 한 Book은 한 시점에 정확히 하나의 준비 상태만 가진다.
- 다른 Book의 Claim은 판정에 영향을 주지 않는다.
- `READY_LIMITED`는 실패나 차단을 뜻하지 않고 후속 Memory 중심 Interview 정책 신호다.
- `FAILED`, `PREPARING`은 자동 준비 workflow 범위에서 도입하며 현재 값에 포함하지 않는다.

## Seed Knowledge Set

### 대상 Book

| ISBN13 | 도서 | 검증 유형 |
| --- | --- | --- |
| `9780452284234` | 1984 | fiction: Theme, Character, Event/Concept |
| `9780374275631` | Thinking, Fast and Slow | nonfiction: Argument, Concept, Theme |

### 적용 규칙

- JSON Seed 데이터에는 `Book` 레코드를 포함하지 않는다.
- 두 ISBN13의 Book이 모두 미리 존재해야 한다.
- 각 Book에 출처 대조 체크리스트에서 승인된 3~5개 Claim을 둔다.
- Seed Service는 전체 ISBN13과 Claim을 선검증한 뒤 하나의 transaction에서 저장한다.
- 하나의 Book/Claim이라도 해석·검증·저장에 실패하면 전체 실행을 rollback한다.
- 같은 Seed를 반복 적용해도 `(book, kind, 정규화된 content)` 기준으로 BookKnowledge 행
  수와 내용이 변하지 않는다.

## Migration 설계

- 신규 `knowledge` 앱의 `0001_initial` 한 개를 생성한다.
- 의존성은 현재 `books` leaf migration이다.
- 신규 빈 table과 그 FK·kind/content CHECK·UNIQUE만 만들며 기존 table을 변경하지 않는다.
- `sqlmigrate`로 실제 DDL과 lock 범위를 확인한다.
- PostgreSQL test database에서 forward/reverse/forward 왕복과 제약 복원을 검증한다.
- Seed 데이터는 schema migration에 포함하지 않는다.
