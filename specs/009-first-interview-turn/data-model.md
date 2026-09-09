# Phase 1 데이터 모델: 첫 인터뷰 Turn

## 관계 개요

```text
User 1 ── N Reading 1 ── 1 Interview 1 ── N InterviewTurn
                     │         │                 └── answer 0..1
                     └─ Book ──┘
                           └── N BookKnowledge

Interview + Book + Reading + allowed Knowledge ──> InterviewQuestionContext (비영속)
InterviewQuestionContext ──> GeneratedQuestion (비영속) ──> InterviewTurn #1
```

소유권은 `Interview → Reading → User`로 판정한다. Provider는 비영속 Context와 질문 후보만
다루며 ORM 객체, user 식별자 또는 mutation capability를 받지 않는다.

## Interview (기존, schema 변경 없음)

| 사용 필드 | 역할 | 규칙 |
| --- | --- | --- |
| `reading` | 소유권·독서 경험 | 요청 user가 소유하고 완독 상태여야 함 |
| `book` | 확정 Book | `reading.book`과 일치해야 함 |
| `knowledge_readiness` | 질문 정책 | 시작 시점 `READY` 또는 `READY_LIMITED` |
| `status` | lifecycle | 이번 기능은 `IN_PROGRESS`만 질문/답변 허용 |

## InterviewTurn (기존, 동작 확장)

| 필드 | 저장 형태 | 이번 기능 규칙 |
| --- | --- | --- |
| `interview` | FK | 소유자 범위의 유효한 진행 중 Interview |
| `sequence` | positive integer | 첫 질문은 1, `(interview, sequence)` UNIQUE |
| `question` | `varchar(2000)` | public 생성 경계에서는 trim 후 한 문장·1~300자, 마지막은 `?` 또는 `？` |
| `answer` | nullable text | `NULL`은 미응답, trim 후 1~2,000자, 최초 성공 후 불변 |
| `created_at`/`updated_at` | timestamp | 질문 생성과 최초 답변 저장 시점 추적 |

### Answer 상태 전이

```text
NULL (미응답) ── valid submit ──> non-empty answer (확정)
     │                                  │
     ├─ invalid/DB failure ──> NULL      ├─ same submit ──> 동일 값 반환
     └─ retry 가능                       └─ different submit ──> conflict, 무변경
```

- 공백만 있는 값과 2,000자 초과 값은 저장하지 않는다.
- DB 오류 시 bound input은 응답에 남지만 DB answer는 `NULL`이다.
- Day 06에는 답변 수정·삭제 public Service가 없다.

## InterviewQuestionContext (비영속 immutable value)

| 값 | 출처 | 신뢰 분류 |
| --- | --- | --- |
| `book_title`, `authors`, `publisher` | 확정 Book | untrusted data |
| `reading_status`, `completed_on` | 확정 Reading | untrusted data |
| `knowledge_readiness` | Interview snapshot | application-controlled enum |
| `knowledge_claims` | BookKnowledge | untrusted data; `READY`일 때만 포함 |
| `policy` | application | trusted instruction |

- `READY_LIMITED`에서는 `knowledge_claims`를 빈 tuple로 만들고 기억·인상·감정에서 시작하는
  policy를 사용한다.
- 다른 user의 Reading/Interview, Credit, 관리자 데이터와 외부 검색 결과는 포함하지 않는다.
- Context payload에는 실행 가능한 tool이나 callback이 없다.

## GeneratedQuestion (비영속 immutable value)

| 값 | 규칙 |
| --- | --- |
| `question` | trim 후 1~300자, 한 줄, 하나의 의문문 |

검증은 structured output parse 이후 application layer에서 다시 수행한다. 빈 값, newline,
중간 sentence terminator, 300자 초과, 마지막 물음표 누락 또는 금지된 control text는 invalid
output이다.

## 동시성 및 transaction

### 첫 질문

```text
기존 Turn #1 조회
  ├─ 있음 → 재사용
  └─ 없음 → Context build → Provider I/O (transaction 밖)
            → output validation
            → atomic: Interview row lock → Turn #1 재조회 → create-or-reuse
```

경쟁 호출은 Provider를 둘 이상 호출할 수 있으나 저장 결과는 기존 UNIQUE로 한 Turn에 수렴한다.

### 첫 답변

```text
form validation → atomic: owner-scoped Turn #1 row lock
  ├─ answer NULL → 저장
  ├─ same answer → 멱등 성공
  └─ different answer → conflict, 기존 원문 유지
```

## Migration 설계

- 신규 migration은 만들지 않는다.
- 기존 column은 새 계약보다 넓은 저장 형식으로 호환된다.
- `makemigrations --check --dry-run reflections`로 model state drift 0건을 검증한다.
- question/answer type 축소나 새 CHECK constraint는 이번 기능에서 수행하지 않는다.
