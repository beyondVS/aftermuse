# 구현 계획: 첫 인터뷰 Turn

**브랜치**: `feature/day-06-first-question-answer-storage` | **날짜**: 2026-09-09 | **사양**: [spec.md](spec.md)

**입력**: `/specs/009-first-interview-turn/spec.md`의 기능 사양

## 요약

기존 `reflections` 앱에 첫 질문용 Context builder, Provider-neutral LLM 계약, OpenAI
Responses API Adapter와 deterministic fake를 추가한다. Interview 상세는 일반 HTML form을
정본으로 유지하면서 HTMX가 첫 질문 준비 POST를 자동 시작해 Loading → Question/Error
fragment로 전환한다. Provider I/O는 transaction 밖에서 30초·무자동재시도로 실행하고,
structured output과 application validation을 통과한 한 문장·300자 이하 질문만 짧은
transaction에서 sequence 1 Turn으로 멱등 저장한다. 답변 POST는 2,000자 이하 원문을 최초
한 번만 저장하며, 실패 시 bound form의 입력을 유지하고 성공 후에는 다음 질문을 만들지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, Django Templates, HTMX 2.0.10, Alpine.js CSP 3.17.1,
`openai~=3.10.0`; SDK와 모델을 쓰지 않는 fake provider를 기본 자동 테스트에 사용

**저장소**: PostgreSQL 18; 기존 `reflections_interview`와 `reflections_interviewturn` table을
재사용하며 schema migration 없음

**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16; context/provider/service/form/view 계약,
동시성, timeout/error, HTML·HTMX·접근성 회귀와 전체 `scripts/verify.py`

**대상 플랫폼**: Django 서버 렌더링 Responsive Web, Desktop 우선 및 Mobile Web 지원

**프로젝트 유형**: 단일 Django Web application

**성능 목표**: 첫 질문 Provider 호출은 30초에 종료하고 자동 retry를 하지 않는다. 기존 질문
조회와 답변 저장은 외부 I/O 없이 즉시 완료되어야 한다. 별도 부하 하네스가 없으므로 DB-only
p95 수치는 이번 완료 게이트로 만들지 않는다.

**제약 조건**: READY/READY_LIMITED 분리, trusted instructions와 untrusted context 구획,
tools 없음, `store=False`, Provider의 DB/웹/Credit 권한 없음, 질문 1문장·300자 이하, 답변
2,000자 이하·최초 저장 후 불변, 답변 저장 후 다음 질문 미생성, 외부 I/O를 transaction 안에
두지 않음, 일반 HTML fallback 유지, 실제 브라우저 검증은 필수 작업으로 추가하지 않음

**규모/범위**: 기존 앱 1개 확장, integration package 1개, 내부 service/context/form 계약,
HTMX fragment 4개, protected POST 2개, migration 0개

## 헌법 검사

*게이트: Phase 0 전에 통과했으며 Phase 1 설계 후 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| I. 사용자 생각의 충실성 | READY_LIMITED는 Book Knowledge를 질문 근거에서 제외하고 기억 중심 정책을 trusted instruction으로 고정한다. | 통과 |
| II. 핵심 제품 루프와 범위 규율 | 첫 질문과 최초 답변까지만 연결하며 Coverage, 다음 질문, Soft Stop, Reflection을 만들지 않는다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | Context를 typed value로 구성하고 trusted instruction과 untrusted payload를 분리하며 tools·DB mutation 권한을 Provider에 주지 않는다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 reflections app, thin views, Service, Django form/template과 Provider Adapter 경계를 사용하고 내부 HTTP API나 worker를 추가하지 않는다. | 통과 |
| V. 증거 기반 품질 | fake 기반 정상/실패/timeout/invalid output, READY 분기, 동시 저장, 입력 보존, HTML/HTMX·접근성 계약을 결정적으로 검증한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff를 유지하고 OpenAI SDK 3.10 계열만 추가한다. | 통과 |
| 데이터 무결성 | 기존 `(interview, sequence)` UNIQUE와 row lock을 재사용하고 public write Service가 질문·답변 길이와 불변성을 강제한다. | 통과 |
| Migration 안전성 | 기존 column은 요구 상한보다 넓은 호환 가능한 저장 형식이다. type 축소나 CHECK 추가를 피하고 migration drift 0건을 검증한다. | 통과 |
| 회복 가능한 UX | Loading/Error/Question/Saved 상태, 30초 timeout, 명시적 재시도, 저장 실패 시 bound answer 보존, keyboard/focus/alert 계약을 제공한다. | 통과 |

설계 후에도 헌법 위반은 없다. 실제 Provider 호출을 동기 HTMX 요청에서 수행하는 선택은 Core
MVP와 30초 명세에 맞는 최소 구조다. 운영 부하나 내구성 있는 비동기 요구가 관찰되기 전에는
worker·queue·polling 상태 모델을 도입하지 않는다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/009-first-interview-turn/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── llm-provider-contract.md
│   ├── service-contract.md
│   └── web-contract.md
└── tasks.md                         # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── config/
│   └── settings.py                 # provider/model/key/timeout 설정
├── integrations/
│   └── llm/
│       ├── contracts.py            # typed request/result와 오류 taxonomy
│       ├── fake.py                 # network 없는 결정적 provider
│       ├── factory.py              # 설정 기반 provider 선택
│       └── openai.py               # Responses API structured output adapter
├── reflections/
│   ├── context.py                  # trusted/untrusted Interview Context Pack
│   ├── forms.py                    # answer 1~2,000자 validation
│   ├── models.py                   # answer normalization/validation 보강(DDL 없음)
│   ├── services.py                 # 첫 질문 생성·멱등 저장·최초 답변 저장
│   ├── urls.py                     # 질문 준비/답변 POST
│   └── views.py                    # owner-scoped thin HTML/HTMX 경계
├── templates/reflections/
│   ├── interview_detail.html       # page shell과 no-JS fallback
│   ├── _interview_loading.html
│   ├── _interview_question.html
│   ├── _interview_error.html
│   └── _interview_answer_saved.html
└── static/css/app.css              # 집중형 질문·상태·반응형·focus 스타일

tests/
├── integrations/llm/
│   ├── test_fake.py
│   └── test_openai.py              # SDK client mock; network 없음
└── reflections/
    ├── test_context.py
    ├── test_forms.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py
```

**구조 결정**: 질문과 답변 workflow는 기존 `reflections` 도메인이 소유하고, Provider SDK와
오류 변환만 `integrations.llm`에 둔다. Context builder는 ORM 조회 결과를 immutable typed
payload로 바꾸되 HTTP나 Provider SDK에 의존하지 않는다. Views는 소유자 범위 조회, form
binding, Service 호출과 전체/fragment 응답 선택만 담당한다.

## 복잡성 추적

헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.
