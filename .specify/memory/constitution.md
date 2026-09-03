<!--
Sync Impact Report
- 버전 변경: 미정의 scaffold → 1.0.0
- 수정된 원칙:
  - 미정의 원칙 1 → I. 사용자 생각의 충실성 (타협 불가)
  - 미정의 원칙 2 → II. 핵심 제품 루프와 범위 규율
  - 미정의 원칙 3 → III. 신뢰 경계와 데이터 통제
  - 미정의 원칙 4 → IV. 단순하고 일관된 아키텍처
  - 미정의 원칙 5 → V. 증거 기반 품질과 회복 가능한 UX
- 추가된 섹션:
  - 기술 및 보안 제약
  - 개발 워크플로 및 품질 게이트
- 제거된 섹션: 없음
- 후속 작업: 없음
-->

# AfterMuse 헌법

## 핵심 원칙

### I. 사용자 생각의 충실성 (타협 불가)

AfterMuse는 사용자의 생각을 대신 만들어내지 않고 질문을 통해 끌어내야 한다.
Reflection은 사용자가 Interview와 Reading 기록에서 실제로 표현한 생각의 범위 안에서만
구성해야 하며, AI가 새로운 신념, 해석, 평가 또는 사실을 임의로 추가해서는 안 된다.
근거가 부족한 책에 대해서는 알고 있는 척하지 않고 기억 기반 질문이나
`READY_LIMITED` 흐름을 사용해야 한다. AI가 만든 Reflection은 언제나 수정 가능한
초안이어야 하며, 사용자가 확인하고 완료해야 최종 기록으로 확정한다. 이 원칙은
결과물이 AI 독후감이 아니라 사용자의 기록으로 남게 하는 제품 신뢰의 근거다.

### II. 핵심 제품 루프와 범위 규율

구현은 Books-first 전략과 `책 선택 → Reading → Coverage 기반 AI Interview →
Reflection 생성·수정·확인` 루프를 우선해야 한다. Core MVP에서도 Interview를 고정
설문지나 일반 Chat UI로 대체해서는 안 되며, 답변 저장, Context Pack, Coverage 갱신,
답변 기반 다음 질문, Soft Stop 및 Reflection 생성 흐름을 유지해야 한다. Credit,
Reader Insight, 자동 Book Knowledge Research, Custom Backoffice, 공개 Reflection 등
연기된 기능은 승인된 범위 문서가 변경되기 전까지 핵심 루프보다 먼저 구현해서는 안
된다. 범위 추가는 기능 수가 아니라 핵심 제품 가설 검증에 기여하는지로 판단한다.

### III. 신뢰 경계와 데이터 통제

사용자 입력과 외부 콘텐츠는 모두 신뢰할 수 없는 입력으로 취급해야 한다. Trusted와
Untrusted Context를 분리하고, LLM 출력은 Structured Output으로 제한한 뒤 Application
Layer에서 enum, 길이, 참조 ID 및 금지 패턴을 검증해야 한다. Interview LLM에는 DB
직접 조회·수정, 웹 검색, 다른 사용자 데이터 접근, Credit 변경 또는 관리자 기능 권한을
부여해서는 안 된다. 외부 자료의 추출 결과는 검증 전 공용 Knowledge로 승격해서는 안
되며, 모든 영속 상태 변경은 Service Layer가 수행해야 한다. 사용자별 비공개 기록과
공유 가능한 파생 데이터는 명시적으로 분리하며 최소 권한 원칙을 적용한다.

### IV. 단순하고 일관된 아키텍처

MVP는 Django 기반 서버 렌더링 Web으로 구현하고 Django Template, HTMX 및 Alpine.js의
점진적 향상을 사용해야 한다. View는 얇게 유지하여 Service 또는 Selector를 호출하고
HTML이나 HTMX Fragment를 반환해야 하며, View가 내부 HTTP API를 호출하게 해서는 안
된다. 핵심 정책은 HTTP와 Template에 의존하지 않는 Python 로직으로 두고 LLM, 검색 및
도서 Metadata Provider는 Adapter 경계 뒤에 둔다. 실제 클라이언트 요구가 생기기 전에
API-first, Microservice, Repository 또는 과도한 Clean Architecture를 도입해서는 안
된다. 미확정 기술은 구현 직전에 필요한 범위만 결정하고 중요한 결정만 Architecture
Decisions에 동기화한다.

### V. 증거 기반 품질과 회복 가능한 UX

완료 여부는 주장이나 화면 존재가 아니라 자동 검사와 사용자 관점의 인수 조건으로
입증해야 한다. 코드 변경에는 관련 테스트를 포함하고 Django system check, Ruff format,
Ruff lint 및 pytest를 통과해야 한다. AI Interview와 Reflection 품질은 정보가 풍부한
책과 부족한 책을 모두 사용해 검증하며, 거짓 전제, 답변 밖의 내용 추가 및 과도한
인터뷰 피로를 확인해야 한다. 주요 화면은 Normal, Empty, Loading, Error 상태와
Desktop/Mobile 레이아웃을 다뤄야 하며, 네트워크 또는 LLM 오류로 사용자의 답변을
유실해서는 안 된다. Keyboard navigation, 충분한 색 대비, 명확한 focus 상태 및
색상 외 상태 표현을 보장해야 한다.

## 기술 및 보안 제약

- Runtime은 Python 3.14, Backend는 Django 6.1, Database는 PostgreSQL 18과 Psycopg 3을
  기준으로 한다. 변경하려면 Architecture Decisions에 대안과 전환 비용을 기록하고
  헌법 준수 검토를 받아야 한다.
- UI는 Django Templates, HTMX 2.0.10, Alpine.js CSP 3.17.1을 사용한다. HTMX와
  Alpine.js 자산은 CDN이 아니라 저장소의 로컬 정적 자산으로 제공해야 한다.
- 의존성과 실행 환경은 `uv` 및 `uv.lock`으로 재현해야 한다. 개발 검증은 `pytest`,
  `pytest-django`, Ruff를 기준으로 한다.
- PostgreSQL이 유일한 지원 Database이며 SQLite fallback을 추가해서는 안 된다. 내부
  PK는 기본 `BigAutoField`를 사용하고, 외부 식별자가 실제로 필요한 모델에만 별도의
  `public_id`를 도입한다.
- 필수 환경변수가 없으면 애플리케이션은 시작 단계에서 명시적으로 실패해야 한다.
  비밀값은 저장소에 커밋하지 않고 `.env.example`에는 실제 credential이 아닌 안전한
  예시만 유지한다.
- Prompt Injection 방어는 단일 제품에 의존하지 않고 Context 분리, 최소 권한,
  검사, Structured Output, Application Validation을 겹쳐 적용해야 한다. 구체적인
  Provider나 방어 라이브러리는 구현 시점의 공식 문서와 유지보수 상태를 확인해 정한다.
- Responsive Web은 Desktop을 우선하되 Reading 기록, Interview 및 Reflection 확인·수정
  핵심 흐름이 Mobile Web에서도 동작해야 한다. Native App과 PWA 전용 기능은 MVP
  범위에 포함하지 않는다.

## 개발 워크플로 및 품질 게이트

1. 기능 동작과 정책은 `docs/README.md`에 정의된 문서 우선순위를 따른다. 충돌 시
   PRD, Architecture Decisions, UI/UX Guide, Handoff 순서로 해석하고 구현 계획은
   실행 순서와 완료 상태의 기준으로 사용한다.
2. 기능 작업 전에는 Spec Kit의 spec, plan, tasks 산출물로 목표, 비목표, 상태 전이,
   보안 경계 및 독립 검증 방법을 확정한다. Day 표기는 마감이 아니라 작업 묶음이며,
   실제 완료는 검증된 task 또는 IMP 체크박스로 관리한다.
3. 변경은 독립적으로 검증 가능한 작은 단위로 진행한다. AI Interview, Reflection 및
   Book Knowledge처럼 위험과 불확실성이 큰 작업은 한 번에 1~2개 구현 단위로 제한하는
   것을 기본으로 한다.
4. 테스트는 내부 구현을 과도하게 mocking하지 않고 실제 비즈니스 상태와 전이를
   검증해야 한다. Migration, 인증·인가, LLM 경계 또는 공개 계약 변경에는 해당 위험을
   재현하는 회귀 테스트가 필요하다.
5. 완료 전 `uv run python scripts/verify.py`를 실행해야 한다. 전체 검증이 환경 제약으로
   불가능하면 실행한 개별 검사, 실패 원인 및 잔여 위험을 변경 보고에 기록해야 한다.
6. 제품 정책, 공개 계약, 기술 스택 또는 운영 절차가 바뀌면 같은 변경에서 README,
   관련 `docs/`, CHANGELOG 및 코드 내 계약 문서를 수술적으로 동기화해야 한다.
7. 헌법 원칙을 벗어나는 복잡성이나 예외는 plan의 Complexity Tracking에 필요성,
   검토한 단순한 대안 및 제거 조건을 기록하고 승인받아야 한다.

## 거버넌스

이 헌법은 AfterMuse의 구현과 기술적 의사결정에 적용되는 최상위 프로젝트 거버넌스다.
제품의 구체적인 동작은 승인된 PRD와 관련 설계 문서가 정의하지만, 그 구현은 이 헌법의
신뢰성, 보안, 단순성 및 검증 원칙을 위반할 수 없다.

개정은 변경 이유, 영향을 받는 원칙과 문서, 호환성 또는 Migration 계획 및 검증 증거를
포함해야 한다. 모든 개정은 파일 상단의 Sync Impact Report와 관련 문서를 함께
갱신하고 다음 Semantic Versioning 규칙을 적용한다.

- MAJOR: 기존 원칙을 제거하거나 호환되지 않게 재정의하고 준수 방식의 Migration이
  필요한 변경
- MINOR: 새 원칙 또는 섹션을 추가하거나 기존 의무를 실질적으로 확장하는 변경
- PATCH: 의미를 바꾸지 않는 명확화, 오탈자 수정 또는 표현 개선

모든 plan과 코드 검토는 관련 헌법 원칙 준수 여부를 확인해야 한다. 자동 검증만으로
판단할 수 없는 AI 품질, UX 및 보안 경계는 인수 기준이나 수동 검토 증거를 남겨야 한다.
위반을 발견하면 기능 확장보다 수정 또는 명시적인 헌법 개정을 우선한다.

**버전**: 1.0.0 | **비준일**: 2026-09-02 | **최근 개정일**: 2026-09-02
