# 데이터 모델: Reflection 결과·수정과 Home 재진입

## 관계 개요

```text
User 1 ── N Reading N ── 1 Book
             │
             └── 0..1 Interview ── 0..1 Reflection

Book 1 ── N BookKnowledge
```

새 table이나 column은 추가하지 않는다. 이번 기능은 `Reflection`의 기존 미래 확장 필드와
기존 관계를 활성화하고 CHECK constraint를 확장한다.

## Reflection

한 Interview에서 생성된 AI 초안, 최신 사용자 수정본과 최종 완료 상태를 함께 보존한다.

| 필드 | 계약 |
| --- | --- |
| `id` | 내부 BigAutoField 식별자 |
| `interview` | 소유 Reading과 Book으로 이어지는 불변 OneToOne 관계 |
| `draft_markdown` | 1–22,000자의 최초 AI 초안; 생성 뒤 불변 |
| `draft_sections` | 최초 초안의 근거 포함 section 배열; 생성 뒤 불변 |
| `revised_markdown` | nullable, 비공백 1–20,000자 최신 사용자 수정본 |
| `status` | `DRAFT` 또는 `COMPLETED` |
| `completed_at` | DRAFT에서는 null, COMPLETED에서는 timezone-aware 완료 시각 |
| `created_at` | 최초 작성일 표시의 기준 |
| `updated_at` | 생성·수정·완료 활동 정렬 및 낙관적 충돌 token |

### 파생값

- `current_markdown`: `revised_markdown`이 null이 아니면 수정본, 아니면 `draft_markdown`.
- `display_status`: DRAFT는 `작성 중`, COMPLETED는 `완료`.
- `revision_token`: 편집 또는 완료 화면을 렌더링한 시점의 `updated_at` 정규화 문자열.

### DB 불변식

```text
status IN ('DRAFT', 'COMPLETED')

(status = 'DRAFT' AND completed_at IS NULL)
OR
(status = 'COMPLETED' AND completed_at IS NOT NULL)
```

기존 draft/revised 길이·비공백 CHECK와 `draft_sections` 배열 CHECK, Interview OneToOne는
그대로 유지한다.

### 상태 전이

```text
DRAFT
├── 수정 저장 ───────────> DRAFT (revised_markdown/updated_at 변경)
├── 완료 확인 취소 ──────> DRAFT (쓰기 없음)
└── 완료 POST ───────────> COMPLETED (completed_at/updated_at 설정)

COMPLETED
├── 결과 조회 ───────────> COMPLETED (쓰기 없음)
├── 반복 완료 POST ──────> COMPLETED (멱등, 쓰기 없음)
└── 수정/초안 복귀 ──────> 거부
```

`DRAFT → COMPLETED`와 동시에 연결된 `Interview.status`는 `REFLECTION_READY → COMPLETED`로
전이한다. 둘 중 하나만 성공하는 상태는 허용하지 않는다.

## 수정 및 완료 명령

영속 entity는 아니지만 Service와 HTTP 경계에서 다음 입력 계약을 가진다.

### ReflectionRevisionCommand

| 값 | 규칙 |
| --- | --- |
| `reflection_id` | URL의 양의 정수, owner scope로 재조회 |
| `markdown` | 원문 보존, 비공백 1–20,000자, raw HTML·링크·이미지·금지 지시 없음 |
| `expected_updated_at` | 화면 렌더 시점 token; 잠근 행의 현재 값과 같아야 함 |

### ReflectionCompletionCommand

| 값 | 규칙 |
| --- | --- |
| `reflection_id` | URL의 양의 정수, owner scope로 재조회 |
| `expected_updated_at` | 확인 화면 렌더 시점 token; DRAFT 완료 시 현재 값과 같아야 함 |

## 최근 독서노트 항목

별도 table이 아니라 owner-scoped Reflection 조회 결과다.

```text
filter: interview.reading.user = current user
order: updated_at DESC, id DESC
limit: 1
relations: interview.reading.book
```

초안과 완료본을 모두 포함하며 타인의 Reflection 또는 접근 불가능한 관계는 포함하지 않는다.

## 검증용 책 descriptor

`validation_books.json`의 비영속 입력 계약이다.

| 값 | 규칙 |
| --- | --- |
| `isbn13` | ASCII 숫자 13자리, Book 자연 식별자 |
| `title` | 누락 Book 생성에 사용할 비공백 제목 |
| `authors` | 누락 Book 생성에 사용할 저자 표시 |
| `genre` | `fiction` 또는 `nonfiction` |
| `expected_readiness` | `READY` 또는 `READY_LIMITED` |

고정 세트:

| ISBN13 | 제목 | 장르 | 기대 상태 |
| --- | --- | --- | --- |
| `9780452284234` | 1984 | fiction | READY |
| `9780374275631` | Thinking, Fast and Slow | nonfiction | READY |
| `9780143111597` | The Left Hand of Darkness | fiction | READY_LIMITED |

command는 Book을 ISBN13으로 재사용하고 기존 서지정보를 덮어쓰지 않는다. READY 두 권에는
기존 승인 Claim을 멱등 적용한다. READY_LIMITED 책에 Claim이 있으면 삭제하지 않고 전체
준비를 실패시킨다.

## Migration 전환

1. `0010_reflection_completion_constraints`: 2초 `lock_timeout`, 기존 DRAFT-only CHECK 2개
   제거, 새 status 및 status/completed_at CHECK를 `NOT VALID`로 추가, ORM state 동기화.
2. `0011_validate_reflection_completion_constraints`: `atomic = False`, 새 CHECK 2개 validate.
3. 새 application 배포: COMPLETED 쓰기 시작.

기존 Reflection은 모두 `DRAFT`, `completed_at=NULL`이므로 data migration과 backfill이 없다.
reverse는 COMPLETED 행이 존재하면 구 제약으로 복귀할 수 없으므로 구현 시 운영 reverse
정책을 명시하고, migration test에서는 완료 행이 없는 schema round-trip과 forward data
보존을 구분한다.
