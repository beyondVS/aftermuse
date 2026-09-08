# 1단계 데이터 모델: 인터뷰 시작

## 관계 개요

```text
User 1 ── 0..N Reading 1 ── 0..1 Interview 1 ── 0..N InterviewTurn
                       │              │
                       └── 1 Book ────┘
                                      └── readiness snapshot
```

소유권은 `Interview → Reading → User`로 판정한다. Interview의 Book은 시작 시 잠근 Reading의 Book만 허용하며 시작 이후 두 관계를 변경하는 public Service를 두지 않는다.

## Interview (신규)

| 필드 | 형태 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | 내부 식별자 | 예 | 프로젝트 기본 `BigAutoField` |
| `reading` | Reading 일대일 관계 | 예 | 전체 수명 동안 Reading당 최대 하나, 삭제 시 함께 삭제 |
| `book` | Book 관계 | 예 | 시작 시 Reading의 Book에서 파생, Book 삭제는 보호 |
| `knowledge_readiness` | 짧은 열거 문자열 | 예 | 시작 시점의 `READY` 또는 `READY_LIMITED` |
| `status` | 짧은 열거 문자열 | 예 | 기본 `IN_PROGRESS`; 허용 lifecycle 값만 저장 |
| `started_at` | 시각 | 예 | 최초 생성 시각 |
| `updated_at` | 시각 | 예 | 후속 상태 변경 추적 시각 |

### 상태와 재진입

| canonical 값 | 의미 | 목적지 |
| --- | --- | --- |
| `IN_PROGRESS` | 질문·답변 Working Data | Interview 진행 화면 |
| `REFLECTION_READY` | Reflection으로 넘어갈 준비 완료 | 후속 Reflection 생성·확인 경계 |
| `COMPLETED` | Reflection 사용자 확인 완료 | 후속 완성 Reflection 경계 |

```text
생성 ──> IN_PROGRESS ──> REFLECTION_READY ──> COMPLETED
```

- 이번 Bundle은 생성 → `IN_PROGRESS`만 수행한다.
- Coverage 충분 여부는 status와 분리한다.
- `COMPLETED`는 재시작하지 않는다. 향후 진행 중 재시작은 같은 Interview를 재사용한다.
- reading은 DB UNIQUE이고, book·reading은 nullable이 아니다.
- Service만 `book_id == reading.book_id`를 생성하며 소유자는 `reading.user`에서 파생한다.
- 저장된 Interview의 `reading_id` 또는 `book_id` 변경은 application validation에서 거부하고
  기존 관계를 보존한다. 정상적인 status 변경은 허용한다.
- readiness/status는 DB CHECK와 application choices로 허용값을 제한한다.
- Reading 삭제 시 Interview/Turn은 cascade하되 제품 UI는 시작 후 Reading 삭제를 제공하지 않는다. Book 삭제는 보호한다.

## InterviewTurn (신규)

| 필드 | 형태 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `id` | 내부 식별자 | 예 | 프로젝트 기본 `BigAutoField` |
| `interview` | Interview 관계 | 예 | Interview 삭제 시 함께 삭제 |
| `sequence` | 양의 정수 | 예 | 1부터 시작, Interview 안에서 중복 불가 |
| `question` | 문자열 | 예 | 앞뒤 공백 제거 후 1~2,000자 |
| `answer` | nullable 문자열 | 아니요 | `NULL`은 아직 답하지 않음을 의미 |
| `created_at` | 시각 | 예 | 생성 시각 |
| `updated_at` | 시각 | 예 | 답변/metadata 변경 추적 시각 |

- 새 Interview는 Turn 0개여도 유효하다.
- `(interview, sequence)` DB UNIQUE, `sequence >= 1`과 whitespace-only question 금지 CHECK를 적용한다.
- 기본 조회는 sequence, id 오름차순이다.
- 복합 UNIQUE가 Interview별 조회를 지원하므로 Interview FK standalone index는 만들지 않는다.
- 이 Bundle에는 Turn 생성·답변 변경 Service가 없다.

## InterviewStartResult (비영속)

| 값 | 의미 |
| --- | --- |
| `interview` | 새로 만들었거나 기존 Interview |
| `created` | 이번 호출의 신규 생성 여부 |
| `destination` | `INTERVIEW`, `REFLECTION_READY`, `REFLECTION_COMPLETED` |

## 동시성 및 transaction

```text
POST → 소유자 Reading select_for_update → 완독 재검증
     → 기존 Interview 있음: 상태별 destination 반환
     → 없음: readiness 계산 → Interview 생성
```

- transaction에는 DB 작업만 포함한다.
- Reading 행 잠금은 시작과 완독 정보 변경을 직렬화하고 OneToOne UNIQUE가 최종 방어한다.
- 경쟁 `IntegrityError`는 같은 Reading의 기존 Interview가 확인될 때만 복구한다.
- 생성 실패 시 부분 Interview와 Reading/Credit 변경은 0건이다.

## Migration 설계

- `reflections/0001_initial` 한 개가 books/readings leaf migration에 의존한다.
- 신규 빈 table과 FK·CHECK·UNIQUE만 만들고 기존 table이나 data를 변경하지 않는다.
- Turn Interview FK는 `db_index=False`로 두고 복합 UNIQUE로 조회와 유일성을 함께 지원한다.
- `sqlmigrate` forward/backward와 PostgreSQL forward → zero → forward를 검증한다.
