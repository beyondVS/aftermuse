# Data Model: Reading 생성 및 완독 관리

## Reading

사용자와 Book을 연결하는 단순 join이 아니라 한 번의 독서 경험이다. 같은 Book의 완독
Reading은 보존하며 명시적 재독마다 별도 행을 만든다.

| 필드 | 타입 | 필수/기본값 | 규칙 |
| --- | --- | --- | --- |
| `id` | `BigAutoField` | 자동 | 내부 PK; 별도 외부 ID는 도입하지 않음 |
| `user` | `ForeignKey(accounts.User)` | 필수 | 소유자, 삭제 시 개인 Reading 함께 삭제 |
| `book` | `ForeignKey(books.Book)` | 필수 | 대상 판본, Reading이 있으면 Book 삭제 보호 |
| `status` | `CharField` | 필수 | `want_to_read`, `reading`, `completed` 중 하나 |
| `completed_on` | `DateField` | 선택, `NULL` | 완독 상태에서 필수; 오늘 또는 과거 날짜 |
| `created_at` | `DateTimeField` | 자동 | 독서 경험 생성 시점 |
| `updated_at` | `DateTimeField` | 자동 | 최근 상태/완독일 변경 시점 |

### 관계

```text
accounts.User 1 ─── N Reading N ─── 1 books.Book
                              │
                              └── Day 05 이후 Interview 0..N
```

- 같은 사용자와 Book에 완독 Reading은 여러 건 존재할 수 있다.
- 같은 사용자와 Book에 활성 Reading(`want_to_read`, `reading`)은 최대 한 건이다.
- Day 05의 Interview가 시작되면 해당 완독 Reading의 상태와 완독일은 잠긴다. 이번
  migration에는 아직 존재하지 않는 Interview FK나 잠금 중복 필드를 추가하지 않는다.

### DB 제약

1. `readings_completion_date_state`
   - `status = completed`이면 `completed_on IS NOT NULL`
   - `status != completed`이면 `completed_on IS NULL`
2. `readings_active_user_book_uniq`
   - `status IN (want_to_read, reading)`인 행에만 `(user_id, book_id)` unique
3. FK
   - `user`는 계정 삭제 시 함께 삭제한다.
   - `book`은 Reading 이력 보존을 위해 보호한다.

미래 완독일은 현재 날짜에 의존하므로 DB CHECK가 아닌 Form과 Service가 쓰기 시점에
검증한다. Model validation도 같은 규칙을 표현해 관리/테스트 경로의 오류를 조기에 찾는다.

## 상태 정의

| 내부 값 | 사용자 표시 | 활성 여부 | `completed_on` |
| --- | --- | --- | --- |
| `want_to_read` | 읽고 싶음 | 활성 | `NULL` |
| `reading` | 읽는 중 | 활성 | `NULL` |
| `completed` | 완독 | 비활성 | 필수 |

## 상태 전이

상태는 순차 진행을 강제하지 않는다.

```text
Reading 없음
  └─ 사용자 상태 선택 ──> WANT_TO_READ | READING | COMPLETED(+완독일)

WANT_TO_READ <──────────> READING
      │                      │
      └──────> COMPLETED <───┘
                 │
                 ├─ Interview 없음 ──> WANT_TO_READ | READING (완독일 제거)
                 ├─ 다른 활성 Reading 존재 ──> 변경 거부, 활성 Reading 안내
                 └─ Interview 시작됨 ──> 상태·완독일 변경 거부
```

- 현재 상태를 다시 제출하면 저장값과 완독일을 바꾸지 않는 멱등 처리다.
- 완독 전이는 오늘을 날짜 기본값으로 제공하되 사용자가 고른 유효한 날짜를 저장한다.
- 완독일만 수정할 때도 오늘 이후 날짜를 거부한다.
- 상태와 완독일은 한 Service transaction에서 함께 저장한다.

## 생성 및 재독 규칙

### 최초 Reading

1. Book 조회/선택만으로는 생성하지 않는다.
2. 이력이 없는 Book에서 사용자가 초기 상태를 선택할 때 생성한다.
3. 경쟁 요청은 사용자 행 잠금 뒤 이력을 재확인하여 첫 성공 결과를 재사용한다.

### 기존 활성 Reading

같은 사용자·Book의 활성 Reading이 있으면 새 행을 만들지 않고 해당 상세를 연다.

### 완독 이력과 재독

1. 활성 Reading 없이 완독 이력만 있으면 `completed_on`, `created_at`, `id` 순으로 가장
   최근인 완독 Reading을 먼저 연다.
2. Book 재선택만으로는 재독을 만들지 않는다.
3. 사용자가 최근 완독 Reading에서 `다시 읽기`를 선택하고 초기 상태를 고르면 새 Reading을
   만든다.
4. 초기 상태가 완독이면 유효한 완독일도 함께 저장한다.

## Service 결과와 오류

생성 Service는 `reading`과 `created`를 가진 불변 결과를 반환한다. 예상 가능한 정책 오류는
Form/View가 안전한 사용자 메시지로 매핑할 수 있는 도메인 오류로 구분한다.

- `ReadingHistoryExistsError`: 최초 생성 대상에 이미 이력이 있음
- `ActiveReadingExistsError`: 새 생성 또는 완독 취소 시 다른 활성 Reading이 있음
- `InvalidReadingTransitionError`: 상태/완독일 조합 또는 미래 날짜가 유효하지 않음
- `ReadingLockedError`: Interview 시작 후 상태 또는 완독일 변경 시도

DB 오류나 예상하지 못한 예외의 상세는 사용자 응답에 노출하지 않는다.
