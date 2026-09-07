# 구현 계획: Reading 생성 및 완독 관리

**브랜치**: `feature/day-04-reading-completion` | **날짜**: 2026-09-07 | **사양**: [spec.md](spec.md)

**입력**: `/specs/006-reading-completion-flow/spec.md`의 기능 사양

## 요약

새 `readings` Django 앱에 사용자·Book별 한 번의 독서 경험을 나타내는 `Reading`을
추가한다. 세 상태와 완독일의 일관성은 모델 제약과 Service에서 함께 보장하고, 사용자
행을 잠그는 짧은 transaction과 활성 Reading 조건부 유일성으로 동시 생성을 제어한다.
도서 선택 성공은 Reading 진입 화면으로 연결하며, 첫 Reading과 재독은 사용자가 상태를
명시적으로 선택할 때만 생성한다. 최소 상세 화면은 상태·완독일 변경, 소유권 보호와
완독 후 비활성 `AI 독서노트 만들기` CTA까지 제공한다.

## 기술적 맥락

**언어/버전**: Python 3.14, HTML5, CSS

**주요 의존성**: Django 6.1 Templates·Forms·Session Authentication, HTMX 2.0.10,
Alpine.js CSP 3.17.1, 기존 `accounts.User`와 `books.Book`

**저장소**: PostgreSQL 18; 신규 `readings_reading` table, CHECK 제약과 활성 Reading
조건부 unique index

**테스트**: pytest 9.1, pytest-django 4.14, Django test client, PostgreSQL transaction
test, migration round-trip, Ruff 0.16, `scripts/verify.py`

**대상 플랫폼**: Django 기반 Linux Web server와 최신 Desktop/Mobile Web browser

**프로젝트 유형**: 서버 렌더링 단일 Django Web application

**성능 목표**: 외부 호출 없이 상태 변경 후 1초 이내 화면 피드백, 사용자·Book별 Reading
진입 조회는 고정된 수의 query로 수행

**제약 조건**: 로그인·CSRF 필수, 소유자 범위 조회, 상태와 완독일 원자적 변경, 사용자·
Book별 활성 Reading 최대 1건, 미래 완독일 거부, Interview 시작 후 완독 상태·날짜 잠금
계약, Credit/Knowledge/Interview side effect 없음, 일반 Form POST를 정본으로 유지하면서
HTMX와 Alpine.js로 상호작용을 점진적으로 향상

**규모/범위**: 신규 도메인 앱·table 각 1개, Book 진입·Reading 상세 화면, 생성/재독·상태
변경 Service와 Form, 기존 Book 선택 성공 연결, 관련 모델·Service·View·migration 테스트

**Interview 잠금 연결**: `readings.services.has_started_interview(reading) -> bool`을 Day 05
통합 seam으로 둔다. Bundle 04A에서는 Interview 모델이 없으므로 기본적으로 `False`를
반환하며, Service 테스트에서는 이 seam을 `True`로 대체해 잠금 시 상태와 완독일이 보존되는
계약을 검증한다. Day 05는 호출부를 유지하고 실제 Interview 존재 조회로 구현을 교체한다.

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| II. 핵심 제품 루프와 범위 규율 | Book 선택 다음에 Reading 생성·완독·상세까지만 연결하고 Intention, Entry, Knowledge와 Interview 생성은 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 모든 변경은 로그인·CSRF 보호 Form을 거쳐 Service가 수행하며 Reading 조회는 현재 소유자로 제한한다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 문서에 정의된 `readings` 도메인 앱, Django Template/HTMX와 Service 패턴을 사용하고 내부 API·Repository·신규 의존성을 추가하지 않는다. | 통과 |
| V. 증거 기반 품질 | 상태/날짜 제약, 동시 생성, 소유권, rollback, 전체/HTMX 응답과 Desktop/Mobile 키보드 흐름을 검증한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff를 유지한다. | 통과 |
| 데이터 무결성 | DB CHECK·조건부 unique index와 짧은 transaction을 겹쳐 상태/날짜와 활성 Reading invariant를 보장한다. | 통과 |
| Migration 안전성 | 신규 빈 table의 additive 초기 migration 한 개로 구성하고 실제 SQL·왕복 migration을 검증한다. 기존 table 변경이나 data migration은 없다. | 통과 |
| 회복 가능한 UX | 실패 시 이전 상태를 보존하고 재시도 안내를 제공하며, 상태·오류·focus를 색상 외 정보로 전달한다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다. Day 05에서 Interview
모델을 연결할 때는 동일 상태 변경 Service에 시작 여부 검사를 추가하여 잠금 계약을
완성한다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/006-reading-completion-flow/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── service-contract.md
│   └── ui-contract.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── books/
│   └── views.py                         # 선택 성공을 Reading 진입 화면으로 연결
├── config/
│   ├── settings.py                      # readings 앱 등록
│   └── urls.py                          # readings URL include
├── readings/
│   ├── apps.py
│   ├── forms.py                         # 초기/재독 상태와 완독일, 상태 변경 검증
│   ├── migrations/0001_initial.py       # 신규 table·제약·조건부 unique index
│   ├── models.py                        # Reading 구조와 DB invariant
│   ├── services.py                      # 생성·재독·상태 전이 transaction
│   ├── urls.py
│   └── views.py                         # 얇은 GET/POST 요청 조합과 소유자 조회
├── static/css/app.css                   # Reading 진입·상세 responsive 상태 UI
└── templates/readings/
    ├── _reading_panel.html              # HTMX/전체 화면 공용 핵심 영역
    ├── book_entry.html                  # Reading 없음/활성/최근 완독 진입 상태
    └── detail.html                      # 최소 Reading 상세 화면

tests/
├── books/test_views.py                  # 선택 성공 연결 회귀
└── readings/
    ├── test_forms.py
    ├── test_migrations.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

**구조 결정**: `Reading`은 문서에서 확정한 독립 도메인이므로 `books`에 넣지 않고
`readings` 앱이 소유한다. 상태 변경과 transaction은 Service, 입력 검증은 Form, 소유자
범위 조회와 HTML 응답 조합은 View가 담당한다. Book 선택 View는 성공 후 명명된 Reading
진입 URL로 넘기는 것 외에 Reading 정책을 알지 않는다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
