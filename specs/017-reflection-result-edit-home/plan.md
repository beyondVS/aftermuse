# 구현 계획: Reflection 결과·수정과 Home 재진입

**브랜치**: `feature/day-12-reflection-result-edit-home` | **날짜**: 2026-09-17 | **사양**: [spec.md](./spec.md)

**입력**: `/specs/017-reflection-result-edit-home/spec.md`의 기능 사양

## 요약

Day 11의 임시 Reflection 성공 화면을 소유자 전용 독서 에세이 결과 화면으로 교체하고,
기존 `revised_markdown` 저장 경계를 HTTP 수정 흐름에 연결한다.
`Reflection`은 별도 저장과 명시적 완료를 지원하도록 `DRAFT → COMPLETED` 상태 전이를
단순화해 확장하고, 완료 시 연결된 `Interview`도 같은 transaction에서 `COMPLETED`로 바꾼다.
완료된 Reflection은 읽기 전용으로 유지된다.
Home은 소유자 범위에서 `updated_at`, `id` 순으로 최신 Reflection 하나만 조회하여 초안은
`작성 중`, 완료본은 `완료`로 표시한다. 검증 데이터는 기존 Seed Knowledge 소설·비문학
2권을 재사용하고 Knowledge가 없는 세 번째 책을 추가하는 멱등 management command로
독립 준비한다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, HTMX 2.0.10, Alpine.js CSP 3.17.1,
Python-Markdown 3.10.3

**저장소**: PostgreSQL 18, Psycopg 3.3

**테스트**: pytest 9.1, pytest-django 4.14, Django system check, Ruff 0.16

**대상 플랫폼**: 서버 렌더링 Responsive Web; Desktop 우선, Mobile Web 핵심 흐름 지원

**프로젝트 유형**: 단일 Django Web Application

**성능 목표**: Reflection 조회·수정·완료는 PK 기준의 bounded query로 처리하고, Home의
Reflection 추가 조회는 기록 수와 무관한 단일 query로 유지한다. 기존 Home 카드 수 증가에
따른 N+1 query를 만들지 않는다.

**제약 조건**: 사용자 입력의 raw HTML은 브라우저에서 실행되지 않아야 한다.
최초 AI 초안은 불변이며 완료본은 읽기 전용이다. 수정 저장과 완료는 분리한다.
실제 Provider 호출, 브라우저 자동화, Credit·Reader Insight, 전체 Library는 범위 밖이다.

**규모/범위**: 기존 Django app 4개 경계(`reflections`, `config`, `knowledge`, `books`) 안에서
Reflection 상태 전이 1개, 서버 렌더링 화면 3개(결과·수정·완료 확인), Home 카드 1개,
management command 1개와 검증용 책 3권을 다룬다.

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 재확인했다.*

| 원칙 | 설계 준수 근거 | 결과 |
| --- | --- | --- |
| I. 사용자 생각의 충실성 | 최초 AI 초안을 보존하고 사용자 수정본을 별도로 저장하며 명시적 확인 뒤에만 완료한다. 완료본은 자동 재생성하거나 덮어쓰지 않는다. | 통과 |
| II. 핵심 제품 루프와 범위 규율 | 결과→수정→완료→Home 재진입과 Day 13 검증 준비만 연결한다. Credit, Reader Insight, 공유, 전체 Library 및 품질 튜닝은 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 모든 조회·CUD를 소유자 범위로 제한하고, 수정 입력은 비공백·최대길이 검증 및 안전한 Markdown 렌더링을 적용한다. 상태 변경은 Service transaction에서 수행한다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 Django function view, Form, Service, ORM, Template 구조를 확장한다. 내부 HTTP API, SPA, background worker 또는 새 app을 도입하지 않는다. | 통과 |
| V. 증거 기반 품질과 회복 가능한 UX | 모델·migration·service·view·Home·command의 결정적 테스트, query-count 검사, 접근성 markup 검사와 표준 `scripts/verify.py`를 완료 게이트로 둔다. 실제 브라우저 검증은 필수화하지 않는다. | 통과 |
| PostgreSQL·Migration | 기존 컬럼을 활용해 DRAFT/COMPLETED와 completed_at의 일관성을 보장하는 표준 단일 Django migration으로 처리한다. | 통과 |

설계 후 재검사에서도 헌법 위반과 정당화가 필요한 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/017-reflection-result-edit-home/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── reflection-result-edit-home.md
│   └── validation-book-set.md
├── checklists/
│   └── requirements.md
└── tasks.md                         # $speckit-tasks 출력
```

### 소스 코드 (저장소 루트)

```text
src/
├── config/
│   └── views.py                     # Home group에 최신 Reflection 추가
├── knowledge/
│   ├── management/commands/
│   │   └── prepare_validation_books.py
│   ├── seed_data/
│   │   └── validation_books.json
│   └── services.py                  # 검증 세트 멱등 준비 경계
├── reflections/
│   ├── migrations/
│   │   └── 0010_reflection_completed_status.py
│   ├── drafts.py                    # 수정 저장·완료 Service 및 Markdown 안전 렌더링
│   ├── forms.py                     # DRAFT 수정 Form (비공백, 최대 길이 검증)
│   ├── models.py                    # COMPLETED와 status/completed_at 불변식
│   ├── urls.py
│   └── views.py
├── static/css/app.css
└── templates/
    ├── pages/home.html
    └── reflections/
        ├── reflection_detail.html
        ├── reflection_edit.html
        └── reflection_complete_confirm.html

tests/
├── knowledge/test_validation_books.py
├── reflections/
│   ├── test_drafts.py
│   ├── test_migrations.py
│   ├── test_models.py
│   └── test_views.py
└── test_home_page.py
```

**구조 결정**: 새 app이나 API 계층을 만들지 않는다. Reflection의 데이터·상태 변경은
`reflections`, Home 조합은 기존 `config.views`, 지식 준비 조건을 포함한 검증 세트는 기존
`knowledge` app이 소유한다. 결과 페이지는 `draft_sections`를 직접 신뢰하지 않고 현재
유효 본문(`revised_markdown` 우선)을 하나의 안전 렌더 경계로 통과시킨다.

## 단계별 구현 전략

### 1. 상태와 Migration 계약

- `Reflection.Status`에 `COMPLETED`를 추가하고 `(DRAFT, completed_at IS NULL)` 또는
  `(COMPLETED, completed_at IS NOT NULL)`만 허용한다.
- 기존 draft-only CHECK 제약을 새 제약으로 교체하는 표준 단일 migration
  `0010_reflection_completed_status.py`를 작성한다.
- migration 적용 후 기존 DRAFT 보존, COMPLETED 제약 일관성 및 migration 회귀를 검증한다.

### 2. 수정·완료 Service

- `current_markdown`은 `revised_markdown`이 있으면 이를, 아니면 `draft_markdown`을 반환하는
  단일 읽기 규칙으로 둔다.
- 수정 Form은 비공백 및 최대 20,000자 검증을 수행한다.
- `save_reflection_revision()`은 owner scope와 DRAFT 상태를 검증한 뒤 `revised_markdown`을
  저장한다. 이미 COMPLETED된 Reflection의 수정 요청은 거부한다.
- `complete_reflection()`은 소유자 검증 후 Reflection status/completed_at과 Interview status를
  하나의 짧은 transaction 안에서 일관되게 COMPLETED로 갱신한다. 이미 COMPLETED된 요청은
  추가 쓰기 없이 기존 완료 결과로 안전하게 수렴한다 (단순 guard).
- persistence 실패 시 transaction을 rollback하고 기존 데이터를 안전하게 보존한다.

### 3. 안전한 결과·수정·완료 화면

- 결과 GET은 owner-scoped `select_related("interview__reading__book")`로 책과 Reflection을
  조회해 제목, 선택적 저자, 최초 작성일, 현재 본문, 상태(`작성 중` 또는 `완료`) 및 행동을 렌더링한다.
- Python-Markdown 3.10.3 등 최소 parser를 사용해 독서노트의 기본 Markdown 표현(heading,
  paragraph, list, blockquote, emphasis)을 렌더링하되, 사용자 작성 raw HTML이 브라우저에서
  실행되지 않도록 안전하게 처리한다.
- 수정 화면은 GET으로 현재 본문 textarea를 제공하고, POST 성공 시 결과 화면으로 redirect하는
  PRG 패턴을 사용한다. validation 실패는 form error를 유지하며, 이미 COMPLETED인 경우 수정을 거부한다.
- 완료는 별도 GET 확인 페이지와 POST action으로 분리한다. 취소는 결과 화면 링크이며 GET은
  side effect가 없다. 완료 POST 성공 및 이미 완료된 재요청은 결과 화면으로 redirect한다.
- 완료된 결과에서는 수정·완료 action을 숨기고 읽기 전용 상태를 텍스트로 표시한다.

### 4. Home 최신 Reflection 재진입

- `get_home_reading_groups()`에 현재 사용자의 Reflection을 `updated_at DESC, id DESC`로
  정렬한 단일 owner-scoped query를 추가하고 `select_related("interview__reading__book")`한다.
- Home context의 `recent_reflection`은 최대 하나다. UI 섹션 명칭은 `최근 독서노트`로 하고,
  DRAFT는 `작성 중`, COMPLETED는 `완료`를 텍스트로 표시하며 결과 URL과 책 정보를 제공한다.
- Reflection이 없거나 접근할 수 없으면 최근 카드만 생략한다. 기존 Reading, 진행 중
  Interview, 사색 대기 카드와 빈 상태는 그대로 유지한다.
- Home query-count 테스트를 새 bounded query 수에 맞게 갱신하고 기록 수 증가에도 고정됨을
  검증한다.

### 5. 검증용 책 세트

- 기존 승인 Seed를 가진 소설 《1984》(`9780452284234`)와 비문학
  《Thinking, Fast and Slow》(`9780374275631`)을 그대로 사용한다.
- 세 번째 책은 Knowledge를 넣지 않는 《The Left Hand of Darkness》
  (`9780143111597`)로 고정해 `READY_LIMITED`를 만든다. 검증 JSON은 ISBN13, 제목, 저자,
  `fiction|nonfiction`, `READY|READY_LIMITED` 기대값만 포함하고 사용자 기록은 포함하지 않는다.
- `prepare_validation_books` command는 명시적으로 실행할 때만 세 Book을 ISBN13 기준으로
  `get_or_create`하고 기존 서지정보를 덮어쓰지 않는다. 그 뒤 기존 승인 Knowledge Seed를
  READY 두 권에 적용하며 LIMITED 책에 Claim이 있으면 삭제하지 않고 안전하게 실패한다.
- command 전체를 하나의 Service transaction으로 감싸 누락·형식 오류·상태 불일치 시
  부분 세트를 남기지 않는다. 동일 상태에서 반복 실행하면 생성 0건·재사용 3권으로 수렴한다.

### 6. 문서와 검증

- 모델·migration·service·view·Home·command의 좁은 테스트를 먼저 실행하고,
  `makemigrations --check --dry-run` 및 migration `0010`의 `sqlmigrate`를 확인한다.
- 제품 동작과 구현 계획이 안정되면 README, `docs/README.md`, 구현 계획 Day 12 체크 상태,
  CHANGELOG를 실제 완료 범위에 맞춰 수술적으로 동기화한다.
- 최종 게이트는 `uv run python scripts/verify.py`다. 실제 브라우저 및 live Provider는 이번
  계획의 필수 검증에 포함하지 않는다.
