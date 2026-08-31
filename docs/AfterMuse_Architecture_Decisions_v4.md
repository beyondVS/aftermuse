# AfterMuse Architecture Decisions v4

> 상태: 구현 기준 아키텍처 결정 (Accepted Baseline)
> 목적: AfterMuse MVP 구현에서 **어떤 큰 기술·도메인 원칙을 따를지** 정의한다.
> 이 문서는 세부 DB Schema, API Schema, Prompt Schema를 완성하는 설계서가 아니다.
> 구체적인 구현 세부사항은 각 기능을 구현하기 직전에 필요한 만큼 결정한다.

---

## 1. 아키텍처 목표

AfterMuse의 MVP 아키텍처는 다음을 우선한다.

1. 핵심 제품 실험인 `Book Knowledge → AI Interview → Reflection`에 개발 비용을 집중한다.
2. 익숙하고 안정적인 기술을 사용해 프레임워크 자체의 실험 비용을 줄인다.
3. 데이터 관계와 상태 전이를 명확히 보존한다.
4. 가변적인 AI/문서 데이터는 필요할 때 JSONB를 사용한다.
5. LLM에게 구현을 맡기더라도 코드 구조와 책임 경계가 기능마다 흔들리지 않게 한다.
6. MVP에서 필요하지 않은 API-first, Microservice, Native App 구조를 선행하지 않는다.

---

## 2. 플랫폼 결정

### 결정

**Responsive Web Application**으로 구현한다.

### 이유

- ReadingEntry와 Interview는 모바일 사용 가능성이 높다.
- Reflection 편집과 Backoffice는 Desktop이 편리하다.
- Native App이 없어도 MVP 핵심 기능을 검증할 수 있다.
- Web + Native App 동시 구현은 제품 가설과 무관한 범위를 크게 늘린다.

### MVP 제외

- Native iOS/Android App
- 앱스토어 배포
- Native Push / Share Sheet / Camera 전용 기능

---

## 3. Backend Framework

### 결정

**Django**를 사용한다.

### 검토한 대안

- Litestar
- FastAPI

### 선택 이유

Litestar의 async-first 구조와 API 설계는 매력적이지만, MVP에서는 프레임워크 실험보다 제품 구현에 집중한다.

Django는 다음 영역에서 이미 익숙하고 충분한 기능을 제공한다.

- ORM
- Migration
- Authentication / Session
- Middleware / CSRF
- Template
- Form / Validation
- Test utilities

LLM을 활용해 구현하더라도 프레임워크/생태계 선택으로 발생하는 디버깅과 유지보수 비용은 사라지지 않으므로 MVP에서는 익숙한 Django를 선택한다.

### 비고

Django Admin을 제품의 주 관리자 UI로 의존하지 않는다. Backoffice는 서비스에 맞는 화면을 자체 구현한다.

---

## 4. API 정책

### 결정

MVP는 **API-first 아키텍처로 만들지 않는다.**

기본 사용자 인터페이스는 Django Template + HTMX endpoint를 사용한다.

JSON API가 실제로 필요해질 경우 **Django Ninja를 우선 검토**한다.

### 이유

- 현재 제품은 Responsive Web이 유일한 클라이언트다.
- 모든 기능을 미리 REST API로 분리하면 불필요한 DTO/API Client/상태 관리 비용이 생긴다.
- 서비스 계층을 HTTP 인터페이스와 분리하면 추후 API가 생겨도 비즈니스 로직을 재작성할 필요가 없다.

### 원칙

HTML/HTMX View와 향후 API는 동일한 Application Service를 호출한다.

---

## 5. Frontend

### 결정

- Django Templates
- HTMX
- Alpine.js

### 이유

AfterMuse의 주요 UI는 복잡한 SPA보다 서버 상태를 중심으로 동작한다.

예:

- Library
- Book Search
- Reading 상태 변경
- ReadingEntry 추가
- Interview 한 질문씩 진행
- Reflection 편집/완료
- Backoffice Knowledge Review

HTMX는 서버 렌더링 HTML과 부분 갱신에 사용한다.

Alpine.js는 서버 상태가 아닌 작은 브라우저 UI 상태에만 사용한다.

예:

- Modal
- Dropdown
- Tab
- Side Panel
- Confirmation
- 간단한 Loading UI

### 제외

MVP에서는 React, Vue, Svelte 기반 SPA를 도입하지 않는다.

향후 특정 화면에서 HTMX가 명확한 한계를 보일 때 필요한 부분만 재검토한다.

---

## 6. Database

### 결정

**PostgreSQL**을 Primary DBMS로 사용한다.

### 이유

AfterMuse의 핵심 데이터는 관계와 상태 전이가 강하다.

예:

- User ↔ Reading ↔ Book
- Reading ↔ Interview ↔ Reflection
- Book ↔ BookKnowledge ↔ Source
- Reflection ↔ Evaluation
- Credit 예약/소비

따라서 관계형 모델과 transaction consistency가 중요하다.

### Document 형태 데이터

Document DB를 별도로 도입하지 않는다.

대신 PostgreSQL의 `JSONB`를 사용해 관계형 데이터와 문서형 데이터를 혼합한다.

원칙:

> **정체성·관계·상태·집계가 중요한 데이터는 관계형으로 저장한다.**

> **한 Aggregate 내부에서 구조가 유동적인 데이터는 JSONB를 사용한다.**

JSONB 후보:

- Interview Coverage
- LLM 분석 metadata
- 외부 Provider raw metadata
- Reflection 가변 section 구조
- Research metadata

### 검색

Knowledge 검색은 PostgreSQL을 기반으로 시작한다.

FTS / pg_trgm / pgvector / Hybrid의 구체적 선택은 실제 검색 품질 요구가 확인된 뒤 결정한다.

별도 Vector DB를 MVP 선행 조건으로 두지 않는다.

---

## 7. Django App 경계

기본 구조:

```text
src/
├─ config/
├─ accounts/
├─ books/
├─ readings/
├─ knowledge/
├─ reflections/
├─ credits/
├─ insights/
├─ backoffice/
├─ integrations/
└─ common/
```

### accounts

- User
- 인증
- 사용자 설정

### books

- Book
- ISBN / Metadata
- Aladin Metadata 연동

### readings

- Reading
- ReadingEntry
- ReadingPreparation

### knowledge

- BookKnowledge
- Source
- Evidence
- Candidate
- Conflict
- Knowledge 상태
- Research workflow

### reflections

- Interview
- InterviewTurn
- Grounding
- Reflection
- Coverage / Interview 정책

### credits

- Credit Wallet
- Credit Ledger

### insights

- Evaluation
- Reader Insight
- 집계 데이터

### backoffice

- 자체 관리자 UI
- 비즈니스 로직을 소유하지 않음

### integrations

외부 I/O Adapter.

예:

- LLM
- Aladin
- Web Search
- Prompt Security

### common

정말 공통인 최소 코드만 둔다.

`common`, `utils`, `helpers`를 범용 쓰레기통으로 사용하지 않는다.

---

## 8. Application Code Architecture

### 결정

**Service + Selector/QuerySet + Django ORM** 구조를 사용한다.

Generic Repository Pattern은 사용하지 않는다.

### 이유

Django ORM 자체가 이미 persistence abstraction 역할을 한다.

Repository를 다시 감싸면 보일러플레이트와 일관성 문제만 늘어날 가능성이 높다.

### 책임

#### Service

상태 변경과 Business Rule을 담당한다.

예:

- Reading 완료
- Interview 시작/재시작
- Reflection 완료
- Credit 지급/예약/소비
- Knowledge Candidate 승인

#### Selector / QuerySet

반복되거나 의미 있는 읽기 Query를 담당한다.

단순한 ORM 조회까지 모두 Selector로 감싸지 않는다.

#### View / HTMX Endpoint / API / Task / Backoffice

HTTP/실행 인터페이스 역할만 한다.

비즈니스 규칙을 직접 구현하지 않는다.

### 핵심 규칙

1. Django ORM 위에 Generic Repository를 만들지 않는다.
2. 상태 변경과 Transaction Boundary는 Service가 소유한다.
3. 복잡한 Read는 Selector/QuerySet으로 분리한다.
4. 외부 I/O는 Adapter 뒤에 둔다.
5. View/Task/API/Backoffice에는 비즈니스 로직을 넣지 않는다.

---

## 9. 외부 Integration

AI, 검색, Metadata Provider는 Django 도메인 코드에 직접 종속시키지 않는다.

예:

```text
integrations/
├─ llm/
├─ aladin/
├─ search/
└─ prompt_security/
```

도메인 Service는 Adapter interface를 통해 외부 시스템을 사용한다.

이 구조의 주 목적은 Provider 교체보다 **테스트 가능성과 외부 실패 격리**다.

테스트에서는 실제 LLM, Web Search, Aladin API 호출 없이 대체 구현을 사용할 수 있어야 한다.

---

## 10. 핵심 Domain Decisions

### 10.1 Reading

`Reading`은 User-Book 연결이 아니라 **한 번의 독서 경험**이다.

같은 책의 재독은 새로운 Reading으로 생성한다.

### 10.2 Reading과 Reflection 분리

Reading은 무료 독서 기록 공간이고 Reflection은 AI Interview의 결과물이다.

### 10.3 Interview / Reflection

Interview와 Reflection은 별도 Entity로 유지한다.

Interview는 생각을 끌어내는 과정이고 Reflection은 그 결과물이다.

InterviewTurn은 개별 질문/답변의 추적성과 provenance를 위해 관계형 데이터로 보존하는 방향을 기준으로 한다.

Coverage와 AI 분석 metadata는 JSONB 사용을 허용한다.

### 10.4 Reflection Content

Reflection은 사용자 편집을 위한 Text/Markdown 표현과 가변 section 구조를 함께 보존할 수 있게 설계한다.

AI가 처음 생성한 초안과 사용자가 수정한 최종 내용을 구분해 보존하는 방향을 기본 결정으로 둔다.

세부 field 구조는 구현 시 확정한다.

---

## 11. Credit Architecture

### 결정

Credit은 **Wallet + Ledger** 구조를 사용한다.

### 이유

`Credit 1개 = DB Row 1개` 방식은 대량 지급 시 불필요한 row를 생성한다.

Wallet은 현재 상태를 빠르게 조회하고, Ledger는 변경 이력을 보존한다.

개념:

```text
CreditWallet
- available amount
- reserved amount

CreditLedger
- 지급
- 예약
- 소비
- 반환/조정
```

### 정책

- Interview 시작 시 available → reserved
- Reflection 완료 시 reserved를 소비
- Restart는 추가 Credit을 사용하지 않음
- 관리자는 Credit 지급/조정 가능

Wallet 변경과 Ledger 기록은 동일한 Transaction Boundary 안에서 일관성을 보장해야 한다.

실제 결제/Coupon/Plus가 도입될 때 더 복잡한 Credit Lot 모델을 검토할 수 있으나 MVP에서는 도입하지 않는다.

---

## 12. 상태 및 Transaction 원칙

세부 enum/schema는 구현 시 확정하되 다음 상태 경계를 유지한다.

### Reading

- 읽고 싶음
- 읽는 중
- 완독

### ReadingPreparation

- PREPARING
- READY
- READY_LIMITED
- FAILED

### Interview

- 진행 중
- Reflection 생성 준비 완료
- 완료

Coverage 충분 여부는 Interview status와 분리한다.

### Reflection

- Draft
- Finalizing
- Completed

### 중요한 Commit Boundary

#### Interview 시작

- 책/Reading 확정
- Credit 예약
- Interview 생성

이 세 작업은 일관되게 처리되어야 한다.

#### Reflection 완료

- Reflection 완료
- Credit 소비
- Evaluation / Reader Insight / Knowledge Candidate 등 파생 데이터 Commit

이 경계를 유지한다.

### LLM과 Transaction

느리고 실패 가능한 LLM / Web I/O를 장시간 DB transaction 내부에서 실행하지 않는다.

먼저 외부 작업을 수행하고, 저장할 결과가 준비된 뒤 짧은 DB transaction으로 Commit하는 것을 기본 원칙으로 한다.

---

## 13. Book Knowledge Architecture

### 13.1 BookKnowledge

Book Knowledge는 큰 문서 하나가 아니라 **Claim 단위의 지식**으로 관리한다.

예:

- Theme
- Argument
- Concept
- Character
- Event

### 13.2 Source / Evidence

Knowledge와 Source를 분리한다.

한 Source가 여러 Knowledge를 뒷받침할 수 있고, 한 Knowledge가 여러 Source에 의해 뒷받침될 수 있으므로 Evidence 관계를 둔다.

### 13.3 Candidate

외부 웹 자료나 사용자 Reading/Reflection에서 발견된 새로운 정보는 공용 Knowledge로 바로 저장하지 않는다.

Candidate → 기존 Knowledge 비교 → 승인/병합/Conflict 처리 과정을 거친다.

### 13.4 수정 이력

Knowledge의 의미가 바뀌는 경우 과거 Claim을 overwrite하기보다 대체/폐기 관계를 보존하는 방향을 사용한다.

이는 향후 Echo/Revisit 및 과거 Interview Grounding 추적을 가능하게 한다.

### 13.5 Generation

Book 단위 Knowledge generation/version은 **Interview에 제공되는 Knowledge 의미가 실제로 바뀌었을 때** 증가시키는 방향을 사용한다.

단순 Source 추가나 미미한 confidence 변화마다 generation을 증가시키지 않는다.

세부 규칙은 Knowledge 구현 시 확정한다.

---

## 14. Knowledge Research Architecture

### 결정

Research는 무제한 Agent가 아니라 **제한된 Pipeline**으로 수행한다.

개념:

```text
Knowledge 상태 확인
↓
Gap 확인
↓
검색 Query 생성
↓
정해진 Budget 내 Search
↓
Source 수집 / Dedup
↓
Content Extraction
↓
Prompt Injection 검사
↓
Tool 없는 Extractor LLM
↓
Structured Candidate
↓
Application Validation
↓
Candidate / Evidence / Conflict 처리
↓
Knowledge 상태 재계산
```

### 원칙

- 일반 도서 탐색만으로 비싼 Research를 자동 실행하지 않는다.
- 실제 Reflection 생성 수요가 있는 책을 우선한다.
- 동일 Book에 대한 동시 준비 요청은 가능한 한 하나의 Research 작업으로 병합한다.
- Research Budget을 둔다.
- LLM에게 무제한 검색 권한을 주지 않는다.

Background Job 기술 자체는 별도 결정사항으로 남긴다.

---

## 15. Interview Engine Architecture

### 책임 분리

#### Application / Python

- Context Retrieval
- Interview 상태
- Coverage 저장
- 질문 Budget
- Soft Stop 정책
- Low-information 카운트
- Safety Cap
- Grounding validation
- Workflow 상태 전이

#### LLM

- 사용자 답변 의미 분석
- Coverage 변화 후보
- 새로운 의미 있는 Focus 발견
- 다음 질문 문장 생성

핵심 원칙:

> **LLM은 다음 질문과 의미 분석을 제안하지만 Workflow 자체를 자율적으로 통제하지 않는다.**

### Coverage

Coverage는 `Core + Focus` 구조를 기준으로 한다.

Core 예:

- Memory
- Reaction
- Connection
- Afterthought

Focus는 Book/ReadingEntry/User Answer에서 동적으로 발견되는 특정 주제다.

MVP에서 Coverage를 과도하게 정밀한 실수 점수로 만들지 않고, 이해 가능한 상태 기반 표현을 우선한다.

### 질문 Budget

- 목표 5~6
- Coverage가 충분하면 4~5 이후 Soft Stop 가능
- 일반 상한 8
- 절대 안전장치 10

정확한 정책 값은 사용자 테스트에 따라 조정 가능해야 한다.

---

## 16. Backoffice

### 결정

서비스 업무에 맞는 **자체 Backoffice UI**를 Django Template + HTMX로 구현한다.

Django Admin에 제품 운영 UX를 의존하지 않는다.

### 이유

Knowledge Candidate 검토, 기존 Knowledge 비교, Merge/Approve/Reject, Conflict 처리 등은 단순 CRUD보다 업무 흐름 중심 UI가 필요하다.

### 원칙

Backoffice는 Interface Layer다.

Knowledge 승인, Credit 지급 등의 비즈니스 로직은 각 도메인 Service를 호출한다.

---

## 17. Security Architecture

사용자 입력과 외부 웹 콘텐츠는 모두 Untrusted Input이다.

Defense in Depth 원칙:

- Trusted / Untrusted Context 분리
- LLM Tool 권한 최소화
- Prompt Injection 검사
- Structured Output
- Application Validation
- 상태 변경은 Service Layer에서 수행
- 외부 콘텐츠 추출 결과를 검증 없이 공용 Knowledge로 확정하지 않음

Interview용 LLM에는 DB 변경, Credit 변경, 관리자 기능, 다른 사용자 데이터 접근 권한을 주지 않는다.

Knowledge Extractor LLM에는 Web/Search Tool을 직접 주지 않는다.

Prompt Injection 방어 솔루션의 구체 제품/라이브러리는 구현 시점에 결정한다.

---

## 18. Background Jobs

Book Knowledge Research, 느린 AI 분석 등은 요청-응답 lifecycle에서 분리할 수 있어야 한다.

다만 **Background Job 기술 선택은 아직 확정하지 않는다.**

구현 직전에 다음을 비교해 결정한다.

- Django 생태계 Task 방식
- Celery
- 기타 적합한 Worker/Queue

선택 기준:

- retry
- idempotency
- 운영 복잡도
- Redis 등 추가 인프라 필요성
- Django 통합
- 토이프로젝트 규모 적합성

Task 자체에는 비즈니스 로직을 넣지 않고 Service를 호출한다.

---

## 19. 아직 확정하지 않는 구현 상세

다음은 지금 미리 고정하지 않고 해당 기능 구현 직전에 결정한다.

- 실제 LLM Provider / 모델
- Search Provider
- Prompt Injection 솔루션
- Background Worker 제품
- FTS / Vector / Hybrid Retrieval
- pgvector 사용 여부
- API endpoint/schema
- Django model field 전체 목록
- JSONB 내부 schema 전체
- Prompt / Structured Output schema
- Evaluation scoring 세부 공식
- Authentication 상세 UX
- Deployment Provider
- Observability / APM 제품

이는 결정 누락이 아니라 **Just-in-time Technical Design 대상**이다.

---

## 20. 구현 시 아키텍처 우선순위

기능 구현 중 선택지가 충돌하면 다음을 우선한다.

1. 제품 PRD의 동작/정책을 보존한다.
2. 기존 프로젝트의 확정된 아키텍처와 일관성을 유지한다.
3. 가장 단순한 구현으로 목적을 만족한다.
4. LLM/외부 I/O와 핵심 Business State를 분리한다.
5. 미래 확장 가능성을 이유로 현재 MVP를 과도하게 추상화하지 않는다.

---

## 21. 구현 문서 전략

전체 시스템의 세부 Technical Spec을 선행 작성하지 않는다.

다음 방식으로 진행한다.

```text
PRD
+ Architecture Decisions
+ UI/UX Guide
        ↓
기능 구현 시작
        ↓
해당 기능에 필요한 상세 설계만 결정
        ↓
구현 / Test
        ↓
다음 기능
```

이미 이 문서에서 확정한 중요한 결정은 유지하되, 아직 구현하지 않은 미래 기능의 세부 구조까지 미리 고정하지 않는다.

---

## 22. 문서 우선순위

1. `AfterMuse_MVP_PRD_v4.md`
2. `AfterMuse_Architecture_Decisions_v3.md`
3. `AfterMuse_UI_UX_and_Design_Implementation_Guide_v8.md`
4. `AfterMuse_MVP_Implementation_Plan_v4.md`
5. `AfterMuse_Product_Planning_and_System_Design_Handoff_v9.md`
6. `AfterMuse_Discord_Concept_Deck_v8.pptx`

Architecture는 PRD의 제품 정책을 변경하지 않는다. 제품 동작에 대한 충돌이 있으면 PRD가 우선한다.
Implementation Plan은 구현 순서와 작업 단위를 정리하는 문서이며, 제품 범위나 아키텍처 원칙을 변경하지 않는다.


---

## 23. 2026-08-26 문서 최신화 내역

- MVP 구현 작업 단위 문서 `AfterMuse_MVP_Implementation_Plan_v4.md`를 기준 문서 목록에 추가했다.
- UI/UX Guide `v6`, Product Planning Handoff `v7`, Concept Deck `v6`와 문서명을 맞췄다.
- 기존 아키텍처 결정은 유지한다.
- 아직 확정하지 않는 구현 상세는 계속 Just-in-time Technical Design 대상으로 둔다.


---

## 24. Interface Architecture 업데이트: API-ready, not API-first

MVP는 계속 Django Template + HTMX + Alpine.js 기반으로 구현한다.

API는 미래 가능성을 이유로 선행 구축하지 않는다.

### 결정

```text
MVP
- Server-rendered Web
- Django Template + HTMX
- 별도 JSON API 선행 구현 없음

Future
- 별도 프론트엔드 / 모바일 앱 / 외부 클라이언트가 실제로 필요해질 때 API 도입을 재평가
```

### 이유

AfterMuse의 MVP 검증 대상은 API 구조가 아니라 다음 제품 루프다.

```text
Reading
→ AI Interview
→ Reflection
→ Reader Insight
```

따라서 현재 단계에서 API-first 구조를 만들면 Request/Response Schema, API Auth, Error Format, Versioning, 클라이언트 상태 관리 등 구현 부담이 늘어난다.

### 구현 원칙

```text
Thin View
→ Service / Selector 호출
→ HTML 또는 HTMX Fragment 반환
```

향후 JSON API가 필요해져도 동일한 Service / Selector를 재사용한다.

중요:

```text
HTMX View가 내부 HTTP API를 호출하는 구조로 만들지 않는다.
View와 API는 모두 Application Service를 호출하는 별도 Interface다.
```

### API Framework는 고정하지 않는다

이전 문서에서는 필요 시 Django Ninja를 우선 검토하는 방향을 언급했지만, 이번 결정으로 특정 API Framework를 미래 선택으로 고정하지 않는다.

미래에 API가 실제로 필요해지는 시점에 다음 후보를 당시 생태계와 프로젝트 상황에 맞춰 다시 비교한다.

```text
Django Bolt
Django Ninja
DRF
기타 Django API 도구
Litestar 기반 Backend 분리
```

Litestar는 Django 프로젝트에 추가하는 보조 API 레이어가 아니라, 프론트 분리와 Backend 재구성이 실제로 필요해질 때 검토할 수 있는 별도 Backend 선택지로 본다.

### Migration 대비 원칙

Litestar 전환 가능성을 이유로 MVP에 과도한 Repository / Clean Architecture를 도입하지 않는다.

대신 다음을 지킨다.

```text
Service가 HttpRequest / Template / HTMX에 의존하지 않게 한다.
Coverage / Stop Policy / Knowledge readiness 등 핵심 정책은 순수 Python 로직으로 분리한다.
LLM / Search / Metadata Provider는 Adapter 뒤에 둔다.
Django ORM 추상화는 과도하게 만들지 않는다.
```

즉, 핵심 제품 규칙은 재사용 가능하게 두되 Persistence와 Web Interface 코드는 나중에 교체 대상이 될 수 있음을 받아들인다.

---

## 25. Growth / Retention 기능의 아키텍처 위치

2026-08-30에 검토한 공유 카드, 공개 Reflection, Time Capsule, 개인 지식 그래프, 월간 무료 Pass 등은 MVP Architecture에 즉시 반영하지 않는다.

다만 장기적으로 다음 확장 지점을 고려한다.

```text
Reflection
→ 공개 / 공유 카드 / Collection

Reflection History
→ Time Capsule / Echo

Evaluation / User Profile
→ 심층 취향 리포트 / 개인 지식 그래프

Credit / Usage Policy
→ Monthly Free Pass / 제한적 리워드
```

이 확장은 MVP 검증 이후 별도 설계에서 다룬다.

---

## 26. 2026-08-30 문서 최신화 내역

- API 전략을 `Django Ninja 우선 검토`에서 `API-ready, not API-first`로 수정했다.
- 특정 API Framework를 미래 선택으로 고정하지 않는다.
- Post-MVP Growth / Retention 후보의 아키텍처 위치를 기록했다.
- 문서 기준 버전을 PRD v3, UI/UX v7, Product Planning v8, Implementation Plan v4, Concept Deck v8로 갱신했다.

---

## 25. 2주 Core MVP 실행 전략 반영

2026-08-31 결정에 따라 Implementation Plan은 2주 Core MVP와 이후 Full MVP Backlog를 구분한다. 이 결정은 Architecture 자체를 변경하지 않는다.

원칙:

```text
Architecture는 Full MVP까지 유지 가능한 구조를 기준으로 한다.
2주 Core MVP에서는 일부 컴포넌트를 구현하지 않거나 수동 Seed로 대체할 수 있다.
나중에 구현할 기능을 위해 현재 코드에 미사용 추상화를 과도하게 추가하지 않는다.
```

2주 Core MVP에서 지연 가능한 항목:

```text
Credit Wallet/Ledger
자동 Book Knowledge Research Pipeline
Reader Insight / Evaluation 집계
Custom Backoffice
14일 Restart
Production-grade Background Worker / Retry / Monitoring
```

대체 전략:

```text
Book Knowledge 자동 Research
→ 검증용 책 몇 권에 대해 수동 Seed 데이터를 사용한다.

Credit
→ Core MVP에서는 인터뷰 시작/완료 흐름을 무료로 진행한다.

Reader Insight
→ Reflection 품질 검증 이후 Full MVP 구간에서 구현한다.
```

중요한 제약:

```text
2주 Core MVP라도 AI Interview는 고정 설문지로 대체하지 않는다.
답변 저장, Context Pack, Coverage 갱신, 다음 질문, Soft Stop, Reflection 생성 흐름은 반드시 살아 있어야 한다.
```

따라서 2주 Core MVP의 목적은 구조 전체 구현이 아니라 AfterMuse의 가장 중요한 제품 루프를 실제로 검증하는 것이다.

### 변경 이력

- Implementation Plan v5의 2주 Core MVP / Post-MVP 구조를 반영했다.
- API-ready, not API-first 원칙은 유지한다.
- 특정 API Framework를 미래 선택으로 고정하지 않는다.
