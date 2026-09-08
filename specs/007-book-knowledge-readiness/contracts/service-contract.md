# 내부 Service 계약: Book Knowledge

## 범위

이 계약은 `knowledge` 도메인을 사용하는 application code의 Python 경계다. HTTP endpoint,
Template context, Interview 생성 또는 LLM prompt 형식은 정의하지 않는다.

## KnowledgeKind

지원하는 canonical 값은 다음과 같다.

```text
theme
argument
concept
character
event
```

그 밖의 값은 등록할 수 없다.

## create_book_knowledge

### 입력

- 존재하고 저장된 `Book`
- canonical `KnowledgeKind`
- Claim `content`

### 처리 계약

- content의 앞뒤 공백을 제거한다.
- 정규화된 content가 1~500자인지 검증한다.
- 같은 Book·kind·정규화된 content가 없으면 Claim을 생성한다.
- 이미 있거나 동시 요청에서 먼저 생성되면 기존 Claim을 반환한다.

### 출력

- `book_knowledge`: 생성되었거나 기존에 있던 단일 `BookKnowledge`
- `created`: 이번 호출이 새 행을 만들었는지 나타내는 boolean

### 오류

- 저장되지 않은 Book, 허용되지 않은 kind, 비어 있거나 너무 긴 content는 validation 오류
- 예상하지 못한 DB 오류는 성공 결과로 바꾸거나 숨기지 않음

### Side effect

- 최대 한 개의 BookKnowledge 행 생성
- Book, Reading, Interview, Credit 또는 사용자 데이터 변경 없음

## list_book_knowledge

### 입력

- 존재하는 `Book`

### 출력

- 해당 Book에 속한 모든 `BookKnowledge`의 읽기 전용 목록
- 순서: `kind`, `id` 오름차순
- Claim이 없으면 빈 목록

### 보장

- 다른 Book의 Claim 혼입 없음
- 단일 DB 조회로 평가 가능
- 외부 I/O와 영속 상태 변경 없음

## get_book_knowledge_readiness

### 입력

- 존재하는 `Book`

### 출력

- Claim이 하나 이상 있으면 `READY`
- Claim이 없으면 `READY_LIMITED`

### 보장

- 현재 저장된 Claim 존재 여부에서 호출 시점에 파생
- 별도 상태 저장이나 동기화 side effect 없음
- 단일 존재 조회로 평가 가능
- 다른 Book, 사용자 기록 또는 외부 서비스 상태의 영향 없음

## seed_book_knowledge

### 입력

- `book_isbn13`, canonical `kind`, `content`를 가진 전체 Seed 항목 목록

### 처리 계약

- 모든 ISBN13이 기존 Book 한 건을 식별하는지와 모든 Claim이 유효한지 쓰기 전에 검증한다.
- content는 `create_book_knowledge`와 같은 규칙으로 정규화한다.
- 검증이 끝난 전체 항목을 단일 transaction에서 `(book, kind, content)` 기준으로 멱등 적용한다.
- management command는 이 Service를 호출하며 ORM 쓰기를 직접 수행하지 않는다.

### 출력 및 오류

- 생성 수와 기존 항목 재사용 수를 반환한다.
- 누락 Book, 잘못된 항목 또는 DB 오류가 하나라도 있으면 전체 실행을 실패시키고 실행 전
  상태를 유지하며 실패 대상을 식별할 수 있게 한다.

## 후속 통합 seam

Bundle 05B는 `list_book_knowledge` 결과를 Interview Context 구성에 사용하고,
`get_book_knowledge_readiness` 결과로 Book-grounded 또는 사용자 기억 중심 질문 정책을
선택한다. 이 seam은 Interview를 생성하거나 질문을 만드는 책임을 갖지 않는다.
