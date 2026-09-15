# 구현 계획: Reflection 기본 모델과 생성 Prompt / Adapter

**브랜치**: `feature/day-10-reflection-model-prompt-adapter` | **날짜**: 2026-09-15 | **사양**: [spec.md](spec.md)

**입력**: `specs/015-reflection-draft-generation/spec.md`

## 요약

IMP-090은 Interview당 하나의 Reflection에 최초 AI 초안과 사용자 수정본을 구분해 저장한다. IMP-091은 확정 답변만 사용하는 읽기 전용 생성 capability를 기존 fake·OpenAI·Gemini·Ollama에 추가한다. 구조화 section·문단·원문 인용을 검증한 뒤 서버가 Markdown을 조립한다. 생성과 저장은 별도 Service로 둔다. HTTP endpoint, Template, 생성 화면 전이, 편집·완료 UI는 후속 작업이다.

## 기술적 맥락

**언어/버전**: Python 3.14, Django 6.1; 루트 pyproject 및 lockfile 기준.

**주요 의존성**: 기존 Psycopg 3.3, OpenAI SDK 3.10, google-genai 2.23, httpx 0.28. 새 패키지 없음.

**저장소**: PostgreSQL 18, 새 Reflection 테이블 하나.

**테스트**: pytest·pytest-django, 실제 PostgreSQL ORM/transaction, 외부 transport mock/fake, Django check·Ruff.

**대상 플랫폼**: 기존 Django Web의 내부 Service 및 LLM integration. Windows 호스트 개발 및 PostgreSQL 컨테이너.

**프로젝트 유형**: 단일 서버 렌더링 Web; 이번 작업은 데이터·생성 기반.

**성능 목표**: 생성 요청당 외부 호출 1회와 기존 Provider timeout 준수. 외부 호출 중 DB transaction·row lock 없음. 추가 지연 SLA 없음.

**제약 조건**: 최대 10개 확정 답변, 각 원문 최대 2,000자. section 최대 10개, section당 문단 최대 10개, 제목 최대 120자, 문단 최대 2,000자, 완성 초안 Markdown 최대 22,000자·사용자 수정본 최대 20,000자. 초안은 최대 입력 원문 20,000자와 제목·구분자 공간을 확보한다. 상한은 안전 경계이며 목표 분량이 아니다. 금지 형식·패턴·정규화는 생성 계약의 명시적 기준을 따른다.

**규모/범위**: IMP-090·091의 두 구현 단위. Day 11/12 UI·Retry·완료, Credit·공개·Echo 제외.

## 헌법 검사

*헌법 1.1.0 기준 조사 전·설계 후 모두 통과.*

| 원칙 | 설계 증거 | 판정 |
| --- | --- | --- |
| I. 생각 충실성 | 확정 답변만 근거, 문단별 원문 인용, 유보 표현 보존, 대표 자료 의미 대조 | 통과 |
| II. 범위 규율 | Day 10의 두 IMP, 후속 UI·전이 제외 | 통과 |
| III. 신뢰 경계 | trusted instruction/untrusted payload 분리, 구조·인용 재검증, owner scope, Service만 변경 | 통과 |
| IV. 단순성 | 기존 앱·transport 재사용, 테이블 하나, HTTP API·Celery·Repository 없음 | 통과 |
| V. 증거 기반 | ORM·migration·소유자·거부 회귀, opt-in live, 표준 verify | 통과 |

구현 완료 전 독립된 검토 관점에서 소유자 경계, 초안 불변, 실패 보존을 diff·검사 결과와 대조하고 근거를 기록한다. 인용 일치는 의미적 충실성 증명이 아니므로 품질 평가를 분리한다. 실제 브라우저 검증을 필수 작업으로 추가하지 않는다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/015-reflection-draft-generation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/reflection-generation.md
```

`tasks.md`는 다음 `$speckit-tasks` 단계의 산출물이다.

### 소스 코드 (저장소 루트)

| 경로 | 변경 책임 |
| --- | --- |
| `src/reflections/models.py` | Reflection·불변 검증 |
| `src/reflections/migrations/0007_reflection.py` | additive 새 테이블; 구현 시 leaf 재확인 |
| `src/reflections/drafts.py` | owner-scoped 조회·생성·검증·저장·수정본 Service |
| `src/integrations/llm/contracts.py` | context·proposal·Protocol·작업별 오류 |
| `src/integrations/llm/reflection.py` | 공통 schema·prompt·payload·decode |
| `src/integrations/llm/interview.py` | 공통 Provider의 reflection capability |
| `src/integrations/llm/fake.py`, `factory.py` | fake 및 reflection factory |
| `src/integrations/llm/openai.py`, `gemini.py`, `ollama.py` | reflection task format·오류 매핑 |
| `tests/reflections/test_drafts.py` | 생성·저장·수정·정책 결과 |
| `tests/reflections/test_models.py`, `test_migrations.py` | DB·불변·migration 보존/역방향 |
| `tests/integrations/llm/test_reflection.py` | wire·검증·fake |
| `tests/integrations/llm/test_structured_providers.py`, `test_factory.py` | routing 및 기존 세 작업 회귀 |
| `tests/integrations/llm/test_live_smoke.py` | opt-in Reflection smoke |

**구조 결정**: 약 1,100줄인 기존 Interview Service에서 관련 없는 코드를 이동하지 않고 Reflection만 `drafts.py`로 추가한다. 기존 Provider 클래스명도 유지한다.

## 실행 및 검증 순서

1. IMP-090: 모델·migration·owner-scoped 저장·조회·수정본 보존을 준비된 초안으로 독립 검증한다.
2. IMP-091: snapshot·생성 계약·fake·실제 transport capability를 구현한다. 생성은 비영속 결과, 저장은 명시적 별도 호출이다.
3. [quickstart.md](quickstart.md)의 좁은 회귀 후 표준 verify를 실행한다. 실제 외부 호출은 별도 opt-in으로만 실행한다.
4. 구현 후 README·CHANGELOG·구현 계획의 실제 완료 상태를 동기화한다. 계획 작성만으로 IMP를 완료 표시하지 않는다.

## 복잡성 추적

헌법 위반·예외 없음. section은 JSON으로 보존하며 별도 section 테이블·추가 의미 판정 LLM·검색 엔진을 도입하지 않는다.
