# 구현 계획: 인터뷰 시작

**브랜치**: `008-interview-start` | **날짜**: 2026-09-08 | **사양**: [spec.md](spec.md)

**입력**: `/specs/008-interview-start/spec.md`의 기능 사양

## 요약

Architecture Decisions의 도메인 경계에 맞춰 신규 `reflections` Django 앱에 `Interview`와
`InterviewTurn`을 추가한다. `Interview`는 완독 `Reading`과 일대일로 연결하고 확정된
`Book`, 시작 시점의 `READY`/`READY_LIMITED`, 진행 상태를 보존한다. 시작 Service는 소유자
범위의 Reading을 잠근 짧은 transaction에서 완독 여부를 재검증하고 멱등 생성하여 반복·동시
POST가 같은 Interview를 반환하게 한다. Reading 상세의 기존 진입점은 서버 렌더링 책 확인
화면으로 연결하며, 명시적 CSRF 보호 POST만 Interview를 생성한다. 첫 질문, Turn 생성,
Coverage, Reflection 데이터와 Credit은 후속 Bundle로 남긴다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, Django Templates, HTMX 2.0.10 및 Alpine.js CSP 3.17.1의 기존
로컬 정적 자산; 신규 package 없음

**저장소**: PostgreSQL 18; 신규 `reflections_interview`, `reflections_interviewturn` table

**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16; PostgreSQL 기반 model/service/view/
migration 테스트와 375px Mobile·1280px Desktop 수동 확인

**대상 플랫폼**: Django 서버 렌더링 Responsive Web, Desktop 우선 및 Mobile Web 지원

**프로젝트 유형**: 단일 Django Web application

**성능 목표**: 외부 I/O 없이 일반적인 단일 시작/재진입 요청을 p95 500ms 이내에 완료하고,
동일 Reading에 대한 동시 요청에서도 Interview는 한 건만 생성

현재는 성능 측정 도구가 구성되지 않았으므로 p95 목표를 이번 Bundle의 완료 게이트로
검증하지 않는다. 배포 후 tracing 도구에서 실사용 속도 문제가 관찰되면 해당 trace를
근거로 병목을 진단하고 수정한다.

**제약 조건**: Reading당 Interview 전체 수명 1개, 소유자·완독 검증, 시작 후 Reading/Book
불변, `READY_LIMITED` 시작 허용, DB transaction 안에서 외부 I/O 금지, LLM/Credit/Reflection
생성 제외, 일반 HTML form을 정본으로 유지

**규모/범위**: 신규 앱 1개, 모델 2개, additive initial migration 1개, 책 확인 화면 1개,
Interview 상태 진입 화면 1개, GET/POST 시작 경계와 상태별 재진입 resolver, Reading 잠금 seam

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| I. 사용자 생각의 충실성 | 시작 시 `READY_LIMITED`를 스냅샷하고 제한 안내를 제공하며 질문이나 사용자 생각을 이번 Bundle에서 생성하지 않는다. | 통과 |
| II. 핵심 제품 루프와 범위 규율 | Reading → Interview 진입과 Turn 영속 기반만 구현하고 첫 질문, Coverage, Soft Stop, Reflection은 후속 Bundle로 유지한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | client의 user/book/readiness를 받지 않고 소유자 범위 Reading과 서버 계산 readiness만 사용한다. 상태 변경은 Service가 수행한다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | Architecture Decisions의 `reflections` 앱, thin function view, Service, Django ORM과 server-rendered template을 사용하며 API/Repository/신규 의존성을 추가하지 않는다. | 통과 |
| V. 증거 기반 품질 | 소유권, CSRF, 상태, 동시성, rollback, readiness, 접근성, 반응형 UI와 migration SQL을 자동·수동 검증한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff와 기존 verify 명령을 유지한다. | 통과 |
| 데이터 무결성 | Reading OneToOne, Turn 순서 UNIQUE/CHECK, status/readiness/question CHECK와 짧은 transaction을 겹쳐 적용한다. | 통과 |
| Migration 안전성 | 신규 빈 table 두 개만 만드는 additive initial migration이다. 기존 table 변경이나 backfill이 없어 분할·concurrent index·`NOT VALID`가 필요하지 않으며 실제 SQL과 왕복을 검증한다. | 통과 |
| 접근성/회복 가능성 | 실제 link/button, 텍스트 안내, focus와 alert 계약, 일반 POST fallback, 실패 시 0건 생성과 재시도 안내를 유지한다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다. 상태별 재진입은 이번
Bundle에서 목적지 판정 계약을 확정하고, 아직 존재하지 않는 Reflection의 데이터·생성 UI를
미리 만들지 않는다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/008-interview-start/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── service-contract.md
│   └── web-contract.md
└── tasks.md                         # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── config/
│   ├── settings.py                 # reflections 앱 등록
│   └── urls.py                     # /reflections/ URL include
├── reflections/
│   ├── apps.py
│   ├── migrations/
│   │   └── 0001_initial.py         # 신규 빈 Interview/Turn table과 제약
│   ├── models.py                   # Interview, InterviewTurn 상태·불변조건
│   ├── services.py                 # 멱등 시작과 상태별 목적지 판정
│   ├── urls.py                     # 확인 GET, 확정 POST, Interview 진입
│   └── views.py                    # 소유자 범위 thin server-rendered views
├── readings/
│   └── services.py                 # has_started_interview 실제 조회로 교체
├── templates/
│   ├── readings/
│   │   └── _reading_panel.html     # 완독 CTA를 확인 화면 link로 전환
│   └── reflections/
│       ├── interview_start.html    # 책 최종 확인·READY_LIMITED·오류
│       └── interview_detail.html   # Turn 0개도 유효한 진행 시작 화면
└── static/css/app.css              # 확인/진입 화면 반응형·focus 스타일

tests/
├── reflections/
│   ├── test_migrations.py          # SQL 형태·forward/reverse/forward·제약
│   ├── test_models.py              # 상태/readiness/Turn 순서와 DB 불변조건
│   ├── test_services.py            # 완독·소유권·멱등·동시성·rollback·목적지
│   └── test_views.py               # GET/POST/CSRF/404/안내/redirect 계약
└── readings/
    ├── test_services.py            # 실제 Interview 기반 Reading 잠금 회귀
    └── test_views.py               # 활성 CTA와 잠금 오류 회귀
```

**구조 결정**: Architecture Decisions가 Interview, InterviewTurn, 향후 Reflection과 Coverage를
`reflections` 도메인에 배치하므로 신규 앱이 모델과 시작 Service/Web 경계를 소유한다.
`Interview.reading`은 전체 수명 유일성의 기준이고 소유자는 `Reading.user`에서 파생한다.
확정된 `book`은 시작 시점 provenance를 위해 직접 보존하되 client 입력으로 받지 않는다.
`knowledge`는 readiness 계산만 제공하며 Interview나 Turn을 생성하지 않는다. 기존
`readings.services.has_started_interview()` 확장점만 실제 조회로 교체해 Reading의 완독
정보 잠금 계약을 연결한다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
