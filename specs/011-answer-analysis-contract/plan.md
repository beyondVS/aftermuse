# 구현 계획: 답변 분석 계약

**브랜치**: `feature/day-07-adaptive-interview-loop` | **날짜**: 2026-09-10 | **사양**: [spec.md](spec.md)

**입력**: `/specs/011-answer-analysis-contract/spec.md`의 기능 사양

## 요약

확정된 한 Interview Turn의 질문·답변, 현재 Core Coverage와 기존 Interview Context Pack을
Provider 중립 입력으로 구성하고, LLM 또는 결정적 fake에서 답변 의미, low-information 여부와
Coverage 상승 후보를 받는다. Provider 출력은 아직 신뢰하지 않고 Application Service에서
nullable 의미, enum, strict promotion, 축 중복, 후보별 원문 근거 인용, 길이와 금지 패턴을 전체
단위로 검증한 뒤 immutable 비영속 결과로 반환한다. 소유권·Interview 관계·진행 상태·Turn 소속과
답변 확정을 Provider 생성보다 먼저 확인하며, DB transaction이나 상태 변경은 수행하지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, OpenAI Python SDK 3.10 (기존 의존성만 사용)

**저장소**: PostgreSQL 18은 입력 상태 조회에만 사용하며 분석 결과를 저장하거나 schema를 변경하지 않음

**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16, Django system check

**대상 플랫폼**: PostgreSQL에 연결되는 Django server-rendered Web 애플리케이션의 내부 application/adapter 계약

**프로젝트 유형**: 단일 Django Web 애플리케이션

**성능 목표**: 한 분석은 유효한 Interview와 대상 Turn을 bounded query로 조회하고 외부 Provider를
최대 한 번 호출한다. 호출은 기존 `OPENAI_TIMEOUT_SECONDS`와 SDK `max_retries=0` 경계를 재사용하고
DB transaction을 열어 둔 채 기다리지 않는다.

**제약 조건**: 분석 대상은 최대 2,000자의 확정 답변 한 개다. 출력은 최대 네 Core Coverage
후보만 허용하며 후보는 현재 상태보다 엄격히 높아야 한다. low-information 결과는
`meaning=None`, 빈 후보 tuple이다. 각 후보의 1~500자 근거는 답변의 양끝 공백 없는 연속 부분
문자열이어야 하고, 정상 의미는 양끝 공백을 제거한 1~1,000자로 제한한다. LLM에는 tool, DB,
검색 또는 상태 변경 권한을 주지 않으며 결과·시도는 저장하지 않는다.

**규모/범위**: 한 사용자·Interview·Turn에 대한 동기식 내부 계약 하나, 고정 Coverage 축 4개와
3단계 상태를 다룬다. Coverage 적용, Focus Coverage, 다음 질문/Feedback, low-information 누적,
Soft Stop, UI, background job과 실제 live 호출 검증은 범위 밖이다.

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며, 1단계 설계 후 동일 기준으로 다시 확인했다.*

| 원칙/게이트 | 설계 대응 | 사전 | 설계 후 |
| --- | --- | --- | --- |
| I. 사용자 생각의 충실성 | 의미는 답변 밖 내용을 추가하지 않게 지시·검증하고 Coverage 후보마다 원문과 정확히 일치하는 근거를 요구한다. low-information에는 의미를 생성하지 않는다. | 통과 | 통과 |
| II. 핵심 제품 루프와 범위 규율 | 적응형 Interview의 분석 입력만 완성하며 Coverage 적용·다음 Turn·종료 정책은 승인된 후속 Bundle에 남긴다. | 통과 | 통과 |
| III. 신뢰 경계와 데이터 통제 | 입력을 trusted 정책과 untrusted payload로 분리하고 strict Structured Output 뒤 Application이 전체 결과를 재검증한다. Provider에는 tools나 상태 변경 권한이 없다. | 통과 | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 `reflections` Service/Context와 `integrations.llm` Protocol·fake·OpenAI Adapter·factory 패턴만 확장하고 신규 앱·Repository·API를 만들지 않는다. | 통과 | 통과 |
| V. 증거 기반 품질 | fake와 SDK client double로 정상·low-information·악성/손상 출력·오류 매핑을 검증하고 실제 DB로 소유권·관계·무변경 계약을 확인한다. | 통과 | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff와 기존 전체 verify 명령을 유지하며 신규 의존성을 추가하지 않는다. | 통과 | 통과 |
| 외부 I/O와 transaction | 모든 DB 검증을 먼저 끝내고 transaction 밖에서 Provider를 1회 호출한다. timeout과 무재시도 정책을 유지한다. | 통과 | 통과 |
| 브라우저 검증 경계 | 화면 변경이 없고 사용자가 브라우저 검증을 요청하지 않았으므로 결정적 contract/service 테스트만 계획한다. | 통과 | 통과 |

헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 0단계: 조사 결과

세부 결정과 대안은 [research.md](research.md)에 기록했다. 미해결 `NEEDS CLARIFICATION`은 없다.

- 분석 결과를 기존 Turn이나 신규 모델에 저장하지 않고 immutable application 값으로 반환한다.
- Provider DTO의 문자열·nullable 값을 신뢰된 domain enum/result와 분리해 Application 재검증을 강제한다.
- 기존 Context Pack에 대상 질문·답변과 canonical Coverage snapshot을 합성하며 준비 수준별 Knowledge 정책을 보존한다.
- OpenAI Adapter는 기존 모델·timeout·credential 설정을 재사용하되 별도 분석 Protocol과 strict JSON schema를 구현한다.
- 후보별 근거는 exact contiguous substring으로 검증하고 현재 Coverage보다 엄격한 상승만 허용한다.
- low-information은 단일 답변 판정만 반환하며 누적 횟수나 종료 정책을 계산하지 않는다.

## 1단계: 설계 및 계약

- [data-model.md](data-model.md): 입력·Provider 제안·검증된 결과 값 객체와 불변조건
- [contracts/answer-analysis-contract.md](contracts/answer-analysis-contract.md): Context, Provider, Application Service, validation 및 오류 계약
- [quickstart.md](quickstart.md): 결정적 정상·경계·보안·무변경 회귀와 전체 품질 게이트 검증 절차

## 구현 단계

### 1. Provider 중립 계약

1. `integrations.llm.contracts`에 immutable `AnswerAnalysisContext`, 현재 Coverage 항목,
   Provider 제안 결과와 Coverage 후보 DTO, `AnswerAnalysisProvider` Protocol을 추가한다.
2. 질문 생성 오류와 섞이지 않는 `AnswerAnalysisError` 계층에 configuration, timeout,
   unavailable, rejected 분류를 둔다.
3. DTO에는 Provider가 반환한 값을 담되 enum 변환과 business validation은 하지 않아
   Application 경계가 알 수 없는 값·중복·모순을 검출할 수 있게 한다.

### 2. Context와 Application Service

1. `reflections.context`가 기존 질문 Context Pack과 대상 Turn 질문·답변, 네 축의 canonical 현재
   상태를 조합한다. READY는 검증된 Claim을 포함하고 READY_LIMITED는 비워 둔다.
2. `reflections.services`에 분석 진입점을 추가한다. 전달된 Interview/Turn 자체를 신뢰하지 않고
   사용자 소유, Book/Reading 관계, `IN_PROGRESS`, Turn 소속, 확정 답변과 canonical Coverage를
   DB에서 다시 확인한다.
3. 대상 검증 후에만 Provider 또는 factory를 선택하고 transaction 없이 한 번 호출한다. 잘못된
   대상이나 충돌한 `provider`/`provider_factory` 인자는 Provider 생성 전에 거부한다.
4. 반환값 전체를 검증해 trusted `AnswerAnalysisResult`와 evidence 포함 patch tuple로 변환한다.
   low-information invariant, 의미/근거 길이, exact substring, canonical enum, 축 유일성, strict
   promotion과 금지 패턴 중 하나라도 실패하면 `AnswerAnalysisRejected`로 전체 거부한다.
5. 분석 전후 Interview, Turn, Coverage와 관련 aggregate를 저장하지 않는다. Bundle 07A의
   `apply_interview_coverage_patch`를 호출하지 않는다.

### 3. Fake와 OpenAI Adapter

1. `FakeAnswerAnalysisProvider`는 주입한 결과 또는 오류를 그대로 재현하고 받은 Context를 기록한다.
2. `OpenAIAnswerAnalysisProvider`는 기존 OpenAI client 설정을 재사용하고 `store=False`, tools
   없음, strict JSON schema, 고정 timeout과 `max_retries=0`으로 호출한다.
3. instructions에는 low-information invariant, 네 축과 두 목표 상태, strict promotion, exact
   quote와 답변 밖 의미 금지를 trusted policy로 둔다. 질문·답변·도서 metadata, Knowledge Claim과
   현재 Coverage는 별도 untrusted JSON payload로 전달한다.
4. schema/JSON/status/refusal 이상은 rejected, SDK timeout은 timeout, 연결·rate limit·HTTP 오류는
   unavailable로 변환하고 Provider 원문이나 credential을 예외 메시지에 싣지 않는다.
5. factory는 기존 `LLM_PROVIDER`, `OPENAI_MODEL`, `OPENAI_API_KEY`,
   `OPENAI_TIMEOUT_SECONDS`를 사용한다. 새 환경변수나 dependency는 추가하지 않는다.

### 4. 검증과 문서 동기화

1. contract/fake 테스트로 nullable 의미, 결과 shape, Context 기록과 결정적 오류 재현을 검증한다.
2. OpenAI Adapter 테스트로 strict schema, payload 분리, tools 부재, `store=False`, timeout,
   무재시도, JSON parsing과 안전한 오류 매핑을 검증한다.
3. Context/Service 테스트로 READY/READY_LIMITED 입력 차이, 소유권·관계·Turn·답변 선검증,
   정상/low-information, 빈 patch 정상 결과, strict promotion, 후보별 exact evidence, 중복·알 수 없는
   값·금지 패턴·길이 거부와 DB 무변경을 검증한다.
4. 기존 첫 질문, 답변 저장과 Coverage Service 회귀 후 `uv run python scripts/verify.py`를 통과한다.
5. README/CHANGELOG/Implementation Plan은 코드 완료 시 실제 동작과 체크 상태가 달라지는 범위만
   수술적으로 갱신한다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/011-answer-analysis-contract/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── answer-analysis-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md                         # $speckit-tasks가 생성
```

### 소스 코드 (저장소 루트)

```text
src/integrations/llm/
├── contracts.py                    # 분석 Context, raw 제안 DTO, Protocol, 오류
├── fake.py                         # 결정적 Answer Analysis fake
├── openai.py                       # strict Structured Output 분석 Adapter
├── factory.py                      # 분석 Provider 선택
└── __init__.py                     # public import 경계 동기화

src/reflections/
├── context.py                      # Turn + Coverage 분석 입력 구성
└── services.py                     # 대상 검증, Provider 호출, 전체 결과 검증

tests/integrations/llm/
├── test_fake.py
└── test_openai.py

tests/reflections/
├── test_context.py
└── test_services.py
```

**구조 결정**: Architecture Decisions가 Interview 의미 분석과 Coverage 정책을 `reflections`에,
외부 LLM I/O를 `integrations` Adapter에 둔다. 기존 파일과 테스트 배치를 확장하는 것으로 충분하며
신규 Django 앱, model, migration, endpoint, template, background worker 또는 dependency는 필요 없다.

## 복잡성 추적

헌법 위반이 없으므로 별도 예외는 없다.
