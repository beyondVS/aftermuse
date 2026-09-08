# AfterMuse MVP Implementation Plan v5

> 상태: 구현 실행 계획 (2026-09-03 최신화)
> 목적: AfterMuse를 LLM 코딩 에이전트(Codex 등)로 구현할 때, 작업을 **한 번에 맡기기 적절한 체크 가능한 단위**로 나누고, 2주 Core MVP와 이후 Full MVP Backlog를 분리한다.
>
> 이 문서는 PRD/Architecture를 반복하지 않는다. 각 항목은 구현 범위를 통제하기 위한 실행 단위다.

## 0. 기준 문서

구현 기준 문서의 우선순위는 다음과 같다.

1. `AfterMuse_MVP_PRD_v4.md`
2. `AfterMuse_Architecture_Decisions_v4.md`
3. `AfterMuse_UI_UX_and_Design_Implementation_Guide_v8.md`
4. `AfterMuse_Product_Planning_and_System_Design_Handoff_v9.md`
5. `AfterMuse_Discord_Concept_Deck_v8.pptx`

## 1. 사용 원칙

- 각 체크 항목은 LLM 에이전트에게 맡길 수 있는 작업 단위다.
- `Day`는 일정 강제가 아니라 **오늘 볼 작업 묶음**이다.
- **Day는 진행 순서와 작업량을 관리하는 단위, Bundle은 Spec Kit 의사결정·Context 단위, IMP는 실제 구현·검증 단위다.** Bundle은 하나의 논리적 기능 목표와 동일한 요구사항·설계 Context를 공유하며 specify→clarify→plan→tasks→analyze→implement→converge를 함께 진행할 수 있다. 같은 Domain 또는 기능 흐름을 공유하는 IMP를 묶되, 같은 화면 영역이나 상위 기능명이라는 이유만으로 묶지 않는다. IMP는 한 번의 호출에서 모두 구현할 필요가 없고, 서로 다른 제품·아키텍처·트랜잭션·보안 Context는 별도 Bundle로 나눈다. Day에는 여러 Bundle이 들어갈 수 있으며 Bundle이 Day와 1:1로 대응할 필요는 없다. Full MVP Day 계획은 의존성과 작업량을 기준으로 한 초안이며 Core MVP 이후 재배치할 수 있다.
- 하루 안에 끝나지 않은 항목은 다음 작업일로 이월한다.
- `IMP-xxx` 번호와 선행 관계는 유지한다.
- 한 번의 에이전트 작업에서 너무 많은 IMP를 묶지 않는다.
- 가벼운 CRUD/화면 작업은 2~4개 IMP를 묶을 수 있다.
- AI Interview, Reflection 생성, Book Knowledge 관련 작업은 가능하면 1~2개 IMP씩 작게 진행한다.
- 구현 중 세부 설계가 필요하면 필요한 만큼만 결정한다.
- 중요한 결정은 `Architecture Decisions`에 반영한다.
- 구현 완료 후 관련 테스트 또는 수동 확인을 수행한 뒤 `[x]`로 변경한다.

완료 표시:

```text
- [ ] 미완료
- [x] 완료
```

일일 진행 공유 예시:

```text
완료: IMP-021, IMP-022
완료: IMP-030, IMP-031, IMP-032, IMP-033
완료: IMP-040, IMP-041, IMP-042
다음: IMP-050
Blocker: 없음
```

---

## 2. 2-Week Core MVP Critical Path

> 2026-09-03 재기준화: 알라딘 OpenAPI 종료 대응을 Critical Path에 추가하면서 Core MVP는
> 10개에서 11개의 Day 작업 묶음으로 조정한다. `Day`는 달력상의 고정 마감이 아니며,
> Provider 교체 검증을 생략해 기존 10개 묶음에 억지로 압축하지 않는다.

2주 Core MVP의 목표는 전체 Full MVP를 끝내는 것이 아니라 다음 핵심 제품 가설을 검증하는 것이다.

> 사용자가 책을 선택하고 AI의 질문에 답했을 때, 혼자 빈 노트에 쓰는 것보다 자기 생각이 더 잘 드러나는 Reflection이 만들어지는가?

Critical Path:

```text
Foundation
  ↓
Book 검색 / 선택
  ↓
Reading 생성 / 완독
  ↓
수동 Seed 기반 최소 Book Knowledge
  ↓
Interview 시작
  ↓
답변 저장
  ↓
Coverage 갱신
  ↓
다음 질문 생성
  ↓
Soft Stop
  ↓
Reflection 초안 생성
  ↓
수정 / 확인
  ↓
실제 책 검증
```

2주 Core MVP에서는 다음을 의도적으로 뒤로 미룬다.

```text
Credit Wallet / Ledger
자동 Book Knowledge Research Pipeline
Reader Insight
Custom Backoffice
14일 Restart
공개 Reflection / Share Card / Time Capsule 등 Growth 기능
Production-grade 운영/모니터링
```

단, 2주 Core MVP라도 다음은 유지한다.

```text
AI Interview를 고정 설문지로 대체하지 않는다.
사용자 답변을 안전하게 저장한다.
Coverage 기반으로 다음 질문과 Soft Stop을 판단한다.
Reflection은 사용자 답변의 범위 안에서만 생성한다.
Book Knowledge가 부족한 책은 READY_LIMITED 방식으로 질문한다.
```

---

# Part A. 2-Week Core MVP

### Day 01 — 프로젝트가 실행된다

#### Bundle 01A — 프로젝트 기반 구성

- [x] **IMP-001 — Django 프로젝트 Bootstrap**
  - **선행 작업:** 없음
  - Django 프로젝트를 생성하고 `src/config` 최소 project 골격을 만든다.
  - 아직 사용하지 않는 기능의 모델을 미리 만들지 않는다.
  - **완료 조건:** 로컬에서 서버 실행과 Django system check가 통과한다.

- [x] **IMP-002 — PostgreSQL 개발 환경 구성**
  - **선행 작업:** IMP-001
  - PostgreSQL 연결, 개발 환경변수, 기본 migration 흐름을 구성한다.
  - **완료 조건:** 빈 DB에서 migrate가 재현 가능하다.

- [x] **IMP-003 — 테스트 / 품질 명령 구성**
  - **선행 작업:** IMP-001
  - formatter/linter/test 명령을 확정하고 최소 smoke test를 추가한다.
  - **완료 조건:** 한 번의 명확한 명령으로 기본 검증이 가능하다.

- [x] **IMP-004 — 공통 Layout + HTMX/Alpine 토대**
  - **선행 작업:** IMP-001
  - Django Template + HTMX + Alpine.js 기반 공통 Layout을 만든다.
  - Mobile/Desktop 기본 반응형 레이아웃을 잡는다.
  - **완료 조건:** 임시 페이지에서 공통 Layout과 HTMX 기본 동작을 확인할 수 있다.

### Day 02 — 사용자가 로그인하고 책을 찾는다

#### Bundle 02A — 사용자 인증

- [x] **IMP-010 — 최소 사용자 인증 구현**
  - **선행 작업:** IMP-002, IMP-004
  - 회원가입, 로그인, 로그아웃의 MVP 흐름을 구현한다.
  - **완료 조건:** 신규 사용자가 가입 → 로그인 → 로그아웃을 수행할 수 있다.

#### Bundle 02B — 도서 검색 기반

- [x] **IMP-020 — Book 기본 모델 구현**
  - **선행 작업:** IMP-002
  - ISBN13 중심의 Book 저장/조회 모델을 구현한다.
  - 제목, 저자 표시, 출판사, 출간일, 표지, 소개, 목차를 저장할 수 있게 한다.
  - **완료 조건:** Book 저장/조회와 ISBN 중복 방지 테스트가 통과한다.

- [x] **IMP-021 — 도서 Metadata Provider Adapter 구현**
  - **선행 작업:** IMP-003
  - 알라딘 검색 Adapter를 구현하되, 외부 호출은 테스트에서 대체 가능하게 한다.
  - **완료 조건:** 정상/실패/timeout 응답을 구분할 수 있다.

- [x] **IMP-022 — 도서 검색 Service와 검색 결과 정규화**
  - **선행 작업:** IMP-020, IMP-021
  - 검색어를 Provider에 전달하고 표지/저자/출판사/출간연도 중심으로 결과를 정규화한다.
  - **완료 조건:** 정상 검색, 결과 없음, Provider 실패가 구분된다.

- [x] **IMP-023 — 도서 검색 화면 구현**
  - **선행 작업:** IMP-004, IMP-022
  - 표지 기반 도서 검색 UI를 구현한다.
  - Loading/Empty/Error 상태를 최소한으로 처리한다.
  - **완료 조건:** Desktop/Mobile에서 검색 결과를 확인할 수 있다.
  - **검증 예외:** 알라딘 신규 API key 발급 중단으로 live 검색 검증은 폐기하고, 대체 Provider 검증을 IMP-025로 이관한다.

### Day 03 — 도서 검색을 복구하고 선택한 책을 등록할 수 있다

#### Bundle 03A — 도서 검색 복구 및 선택

- [x] **IMP-025 — 도서 Metadata Provider 교체 및 검색 복구**
  - **선행 작업:** IMP-003, IMP-021, IMP-022, IMP-023
  - 알라딘 OpenAPI의 신규 key 발급 및 서비스 종료에 대응해 기본 Metadata Provider를 Kakao 도서 검색 API로 교체한다.
  - Provider 중립 계약·오류·factory를 알라딘 package 밖으로 이동하고 기존 검색 Service와 화면의 계약을 유지한다.
  - **완료 조건:** Kakao 정상/빈 결과/실패/timeout과 ISBN13 정규화 테스트, 기존 검색 Service·화면 회귀 테스트 및 실제 Kakao key smoke test가 통과한다.
  - **검증 (2026-09-06):** Kakao Adapter·회귀 테스트, 기본 자동 검증과 실제 `KAKAO_REST_API_KEY`를 사용하는 명시적 `live` smoke를 통과했고, Desktop/Mobile에서 실제 검색 결과를 확인했다.

- [x] **IMP-024 — 도서 선택 및 로컬 Book 등록**
  - **선행 작업:** IMP-020, IMP-022, IMP-023, IMP-025
  - 검색 결과 선택 시 기존 Book을 재사용하거나 새 Book을 저장한다.
  - **완료 조건:** 같은 ISBN을 반복 선택해도 중복 Book이 생성되지 않는다.
  - **검증 (2026-09-06):** session 후보 ID·CSRF POST·기존 Book 재사용·동시 선택의 PostgreSQL 회귀 테스트를 통과했으며, 1280px Desktop과 375px Mobile에서 키보드만으로 검색·선택·등록 완료 흐름을 각각 2회 확인했다.

### Day 04 — Reading을 만들고 완독 상태를 관리할 수 있다

#### Bundle 04A — Reading 흐름

- [x] **IMP-030 — Reading 기본 도메인 구현**
  - **선행 작업:** IMP-010, IMP-020
  - Reading을 한 번의 독서 경험으로 구현한다.
  - 읽고 싶음 / 읽는 중 / 완독 상태를 지원한다.
  - **완료 조건:** Reading 생성과 상태 저장 테스트가 통과한다.

- [x] **IMP-031 — Book에서 Reading 생성 / 열기**
  - **선행 작업:** IMP-024, IMP-030
  - Book Detail 또는 선택 결과에서 Reading을 생성하거나 기존 활성 Reading을 열 수 있게 한다.
  - **완료 조건:** 책 선택 → Reading 생성 → Reading 화면 진입이 가능하다.

- [x] **IMP-032 — 완독 처리 UX 구현**
  - **선행 작업:** IMP-031
  - 사용자가 Reading을 완독 상태로 바꿀 수 있게 한다.
  - Interview 시작 전에는 실수로 완료한 상태를 되돌릴 수 있게 한다.
  - **완료 조건:** 완독일 기록과 상태 변경이 화면에 반영된다.

- [x] **IMP-033 — 최소 Reading Detail 화면 구현**
  - **선행 작업:** IMP-031, IMP-032
  - 책 정보, Reading 상태, 다음 행동을 표시한다.
  - **완료 조건:** 완독한 Reading에서 AI Interview 시작 CTA를 볼 수 있다.

### Day 05 — 최소 Book Knowledge와 Interview 시작 준비

#### Bundle 05A — 최소 Book Knowledge

- [x] **IMP-040 — BookKnowledge 최소 저장 구조 구현**
  - **선행 작업:** IMP-020
  - 2주 Core MVP에 필요한 최소 Claim 기반 BookKnowledge를 저장할 수 있게 한다.
  - Source/Evidence/Conflict 전체 운영 모델은 뒤로 미룬다.
  - **완료 조건:** 특정 Book에 수동 Seed Knowledge를 등록하고 조회할 수 있다.

- [x] **IMP-041 — 수동 Seed Knowledge Fixture 작성**
  - **선행 작업:** IMP-040
  - 검증용 유명 도서 2~3권에 대해 수동 BookKnowledge Seed를 작성한다.
  - **완료 조건:** Seed를 로드하면 Interview Context에 사용할 수 있다.

- [x] **IMP-042 — READY / READY_LIMITED 최소 판정 구현**
  - **선행 작업:** IMP-040, IMP-041
  - Seed Knowledge가 있으면 READY, 없으면 READY_LIMITED로 단순 판정한다.
  - 자동 Research는 구현하지 않는다.
  - **완료 조건:** Book별 준비 상태가 구분된다.

#### Bundle 05B — 인터뷰 시작

- [x] **IMP-050 — Interview / Turn 기본 모델 구현**
  - **선행 작업:** IMP-030, IMP-042
  - Interview와 질문/답변 Turn을 저장할 수 있게 한다.
  - **완료 조건:** Reading에 Interview를 생성하고 Turn을 저장할 수 있다.

- [x] **IMP-051 — Interview 시작 화면과 책 확정 UX 구현**
  - **선행 작업:** IMP-033, IMP-050
  - 인터뷰 시작 전 책을 확인하고 시작 후 책 변경 불가를 안내한다.
  - 2주 Core MVP에서는 Credit 예약을 하지 않는다.
  - **완료 조건:** 완독 Reading에서 Interview를 시작할 수 있다.

### Day 06 — 첫 질문과 답변 저장이 동작한다

#### Bundle 06A — 첫 인터뷰 Turn

- [ ] **IMP-060 — LLM Provider Adapter 최소 구현**
  - **선행 작업:** IMP-003
  - Interview 질문/Reflection 생성을 위한 LLM Adapter 경계를 만든다.
  - 테스트에서는 fake provider를 사용할 수 있어야 한다.
  - **완료 조건:** 실제 Provider 없이도 질문 생성 흐름을 테스트할 수 있다.

- [ ] **IMP-061 — Interview Context Pack 구성**
  - **선행 작업:** IMP-041, IMP-050
  - Book, 최소 Knowledge, Reading 상태를 LLM 입력용 Context로 구성한다.
  - READY_LIMITED에서는 책 내용을 단정하지 않게 한다.
  - **완료 조건:** READY/READY_LIMITED별 Context가 다르게 생성된다.

- [ ] **IMP-062 — 첫 질문 생성 구현**
  - **선행 작업:** IMP-060, IMP-061
  - Reading/Knowledge 상태에 따라 첫 질문을 생성한다.
  - Knowledge가 부족하면 기억 중심 질문으로 시작한다.
  - **완료 조건:** READY와 READY_LIMITED에서 각각 적절한 첫 질문이 나온다.

- [ ] **IMP-063 — Interview 질문 화면 구현**
  - **선행 작업:** IMP-051, IMP-062
  - 일반 Chat UI가 아니라 한 번에 하나의 질문에 집중하는 화면을 구현한다.
  - **완료 조건:** 첫 질문을 보고 답변을 입력할 수 있다.

- [ ] **IMP-064 — 답변 저장 구현**
  - **선행 작업:** IMP-063
  - 사용자의 답변을 먼저 안전하게 저장한다.
  - LLM 실패가 답변 유실로 이어지지 않아야 한다.
  - **완료 조건:** 정상/실패 상황에서 답변이 보존된다.

### Day 07 — 답변에 따라 다음 질문이 이어진다

#### Bundle 07A — 적응형 인터뷰 루프

- [ ] **IMP-070 — Coverage 기본 구조 구현**
  - **선행 작업:** IMP-064
  - MEMORY / REACTION / CONNECTION / AFTERTHOUGHT 중심의 Core Coverage를 저장한다.
  - 초기에는 UNCOVERED / PARTIAL / COVERED 정도로 단순화한다.
  - **완료 조건:** 답변 후 Coverage 상태를 갱신할 수 있다.

- [ ] **IMP-071 — Answer Analysis 최소 구현**
  - **선행 작업:** IMP-060, IMP-070
  - LLM 또는 fake provider를 통해 답변의 의미, low-information 여부, coverage patch를 얻는다.
  - **완료 조건:** 정상 답변과 low-information 답변이 구분된다.

- [ ] **IMP-072 — 다음 질문 생성 구현**
  - **선행 작업:** IMP-071
  - 기존 답변과 Coverage를 반영해 다음 질문을 생성한다.
  - LLM은 질문을 제안하고, Application이 상태를 갱신한다.
  - **완료 조건:** 답변 내용이 다음 질문에 반영된다.

- [ ] **IMP-073 — Interview Step 통합**
  - **선행 작업:** IMP-064, IMP-070, IMP-071, IMP-072
  - 답변 저장 → 분석 → Coverage 갱신 → 다음 질문 저장 흐름을 연결한다.
  - **완료 조건:** 최소 3턴 이상 인터뷰가 이어진다.

### Day 08 — Soft Stop과 Interview UX가 연결된다

#### Bundle 08A — 인터뷰 종료·복구

- [ ] **IMP-080 — 질문 Budget / Safety Cap 구현**
  - **선행 작업:** IMP-073
  - 질문 목표 수, 기본 상한, 안전 상한을 단순 설정값으로 둔다.
  - **완료 조건:** 상한에 도달하면 추가 질문 대신 Reflection 생성으로 유도한다.

- [ ] **IMP-081 — Soft Stop 구현**
  - **선행 작업:** IMP-070, IMP-080
  - Coverage가 충분하면 독서노트 만들기 / 조금 더 이야기하기 선택지를 보여준다.
  - **완료 조건:** Soft Stop에서 사용자가 종료 또는 계속을 선택할 수 있다.

- [ ] **IMP-082 — Low-information 조기 종료 처리**
  - **선행 작업:** IMP-071, IMP-080
  - low-information 답변이 반복되면 무리한 꼬리질문을 중단한다.
  - **완료 조건:** 연속 low-information 답변 후 짧은 Reflection 생성 흐름으로 이동한다.

- [ ] **IMP-083 — 이전 답변 보기 최소 구현**
  - **선행 작업:** IMP-073
  - 사용자가 이전 질문/답변을 확인할 수 있게 한다.
  - 수정 기능은 Full MVP 이후로 미룰 수 있다.
  - **완료 조건:** Interview 화면에서 이전 Turn을 확인할 수 있다.

- [ ] **IMP-084 — Interview 오류/재시도 UX 구현**
  - **선행 작업:** IMP-073
  - LLM 실패, timeout, 잘못된 응답에서 답변이 보존되며 재시도할 수 있게 한다.
  - **완료 조건:** 다음 질문 생성 실패 후에도 사용자가 복구할 수 있다.

### Day 09 — Reflection 초안이 생성되고 수정된다

#### Bundle 09A — Reflection 생성·수정

- [ ] **IMP-090 — Reflection 기본 모델 구현**
  - **선행 작업:** IMP-050
  - Interview 결과를 바탕으로 Reflection 초안과 사용자 수정본을 저장할 수 있게 한다.
  - **완료 조건:** Reflection Draft를 저장/조회할 수 있다.

- [ ] **IMP-091 — Reflection 생성 Prompt / Adapter 구현**
  - **선행 작업:** IMP-060, IMP-073, IMP-090
  - Interview 답변만을 근거로 Reflection 초안을 생성한다.
  - 사용자가 말하지 않은 생각을 추가하지 않는 규칙을 포함한다.
  - **완료 조건:** fake provider 및 실제 provider에서 Markdown 초안을 생성할 수 있다.

- [ ] **IMP-092 — Reflection 생성 Transition 구현**
  - **선행 작업:** IMP-080, IMP-081, IMP-082, IMP-091
  - Soft Stop, 질문 budget/safety cap 도달, 또는 low-information 조기 종료 후 Reflection 생성 화면으로 이동한다.
  - **완료 조건:** Interview 완료 → Reflection Draft 생성 흐름이 연결된다.

- [ ] **IMP-093 — Reflection 결과 화면 구현**
  - **선행 작업:** IMP-090, IMP-092
  - AI보다 독서노트 자체가 중심이 되는 결과 화면을 구현한다.
  - **완료 조건:** 긴 글을 읽기 편하고 책/날짜/본문이 표시된다.

- [ ] **IMP-094 — Reflection 수정 구현**
  - **선행 작업:** IMP-093
  - 사용자가 생성된 Reflection을 직접 수정할 수 있게 한다.
  - **완료 조건:** 수정한 내용이 저장되고 다시 열어도 유지된다.

### Day 10 — 실제 책으로 품질을 검증한다

#### Bundle 10A — Core MVP 품질 검증

실제 책과 전체 사용자 흐름으로 Core MVP의 핵심 제품 가설을 검증한다.

- [ ] **IMP-100 — 2주 검증용 책 세트 구성**
  - **선행 작업:** IMP-041, IMP-094
  - Seed Knowledge가 있는 책과 READY_LIMITED 책을 포함한 최소 검증 세트를 준비한다.
  - **완료 조건:** 최소 3권 이상으로 테스트할 수 있다.

- [ ] **IMP-101 — End-to-End 수동 시나리오 검증**
  - **선행 작업:** IMP-094, IMP-100
  - 가입 → 책 검색 → Reading → Interview → Reflection 수정까지 실제로 수행한다.
  - **완료 조건:** 팀원이 전체 흐름을 끊김 없이 완료할 수 있다.

- [ ] **IMP-102 — Interview 품질 1차 조정**
  - **선행 작업:** IMP-101
  - 질문이 너무 일반적이거나 사용자의 답변을 반영하지 않는 문제를 수정한다.
  - **완료 조건:** 최소 3권에서 질문이 사용자의 답변과 책 맥락을 반영한다.
  - **Acceptance Rubric (수동):** 직전 답변을 무시하지 않는다. 이미 충분히 다룬 내용은 불필요하게 반복하지 않는다. Book Knowledge가 사용자 경험보다 우위에 서지 않는다. 검증되지 않은 READY_LIMITED 자료를 사실로 단정하지 않는다.

- [ ] **IMP-103 — Reflection 충실도 1차 조정**
  - **선행 작업:** IMP-101
  - 사용자가 말하지 않은 내용이 추가되는지, 노트가 사용자 기록처럼 느껴지는지 확인한다.
  - **완료 조건:** Reflection이 사용자 답변 기반이라는 기준을 통과한다.
  - **Acceptance Rubric (수동):** 사용자가 말하지 않은 생각·주장을 추가하지 않는다. AI의 질문 문구를 사용자의 생각으로 재구성하지 않는다. 주요 반응·연결·후속 생각을 보존한다.

- [ ] **IMP-104 — Mobile 핵심 흐름 확인**
  - **선행 작업:** IMP-101
  - 모바일 웹에서 책 검색, 인터뷰, Reflection 확인/수정이 가능한지 확인한다.
  - **완료 조건:** 모바일에서 핵심 루프를 수행할 수 있다.

### Day 11 — Demo 가능한 Core MVP로 정리한다

#### Bundle 11A — Demo / Release 준비

- [ ] **IMP-110 — 핵심 오류 정리 및 Smoke Test 보강**
  - **선행 작업:** IMP-101, IMP-102, IMP-103
  - 시연을 막는 오류와 가장 중요한 회귀 테스트를 정리한다.
  - **완료 조건:** 핵심 E2E 흐름이 smoke test 또는 명확한 수동 절차로 검증된다.

- [ ] **IMP-111 — Demo 데이터와 시연 흐름 정리**
  - **선행 작업:** IMP-100, IMP-110
  - 팀 공유용 시연 책, 계정, 진행 순서를 정리한다.
  - **완료 조건:** 누가 시연해도 같은 흐름으로 데모 가능하다.

- [ ] **IMP-112 — 2주 Core MVP 배포 또는 로컬 실행 가이드 정리**
  - **선행 작업:** IMP-110
  - 배포까지 가능하면 배포하고, 어렵다면 재현 가능한 로컬 실행 가이드를 완성한다.
  - **완료 조건:** 다른 팀원이 새 환경에서 실행할 수 있다.

#### Bundle 11B — Core MVP Go / No-Go

이는 구현 작업이 아니라 제품 진행 여부를 결정하는 판단이다.

- [ ] **IMP-113 — 2주 회고 및 Full MVP 진행 여부 판단**
  - **선행 작업:** IMP-101, IMP-102, IMP-103
  - 핵심 제품 가설이 충분히 흥미로운지 팀이 판단한다.
  - **완료 조건:** 계속 진행 / 방향 수정 / 중단 중 하나를 결정한다.

---

## ★ 2-WEEK CORE MVP COMPLETE

2주 Core MVP 완료 기준:

```text
사용자가 책을 선택한다.
Reading을 완독 처리한다.
AI Interview를 시작한다.
사용자 답변에 따라 질문이 이어진다.
Coverage가 충분하면 Soft Stop이 나온다.
Reflection 초안이 생성된다.
사용자가 Reflection을 수정할 수 있다.
실제 책 몇 권으로 품질을 검증했다.
```

---

# Part B. Post-MVP / Full MVP Backlog

아래 항목은 삭제된 것이 아니라 2주 Core MVP 이후 구현할 Full MVP 항목이다.
Day 계획은 의존성과 작업량을 기준으로 한 초안이며 Core MVP 이후 재배치할 수 있다.

### Day 12 — 독서 Context와 개인 Library를 확장한다

#### Bundle 12A — Reading Context 확장

- [ ] **IMP-120 — Reading Intention 입력/수정 고도화**
  - **선행 작업:** IMP-033
  - 읽기 전 기대를 Interview Context에 자연스럽게 반영한다.
  - **완료 조건:** Intention이 첫 질문 또는 후속 질문에 활용된다.

- [ ] **IMP-121 — ReadingEntry 작성/수정/삭제 구현**
  - **선행 작업:** IMP-031
  - 읽는 중 짧은 메모를 여러 개 저장하고 수정/삭제할 수 있게 한다.
  - **완료 조건:** Entry가 Interview Context에 활용 가능하다.

#### Bundle 12B — 개인 Library

- [ ] **IMP-122 — Library / Home 기본 화면 고도화**
  - **선행 작업:** IMP-030, IMP-093
  - 읽는 중 / 완독 / Reflection 존재 여부를 책 중심으로 보여준다.
  - **완료 조건:** 사용자가 자신의 Reading과 Reflection을 다시 찾을 수 있다.

### Day 13 — Credit 흐름을 완성한다

#### Bundle 13A — Credit Lifecycle

- [ ] **IMP-130 — Credit Wallet / Ledger 구현**
  - **선행 작업:** IMP-010
  - available/reserved 수량과 Ledger 이력을 구현한다.
  - **완료 조건:** 관리자 지급, 예약, 소비, 해제가 테스트된다.

- [ ] **IMP-131 — Interview 시작 시 Credit 예약 적용**
  - **선행 작업:** IMP-051, IMP-130
  - Full MVP에서는 Interview 시작 시 Credit을 RESERVED 처리한다.
  - **완료 조건:** Credit 부족/성공/실패 시나리오가 검증된다.

- [ ] **IMP-132 — Reflection 완료 시 Credit 소비 적용**
  - **선행 작업:** IMP-094, IMP-131
  - Reflection 최종 완료 시 Credit을 CONSUMED 처리한다.
  - **완료 조건:** 소비와 파생 데이터 commit 경계가 일치한다.

### Day 14 — Book Knowledge 모델을 확장한다

#### Bundle 14A — Book Knowledge 확장

- [ ] **IMP-140 — Source / Evidence / Candidate 모델 확장**
  - **선행 작업:** IMP-040
  - Claim, Source, Evidence, Candidate 구조를 Full MVP 기준으로 확장한다.
  - **완료 조건:** Source 기반 Candidate와 Evidence를 저장할 수 있다.

- [ ] **IMP-141 — Knowledge State / Generation 구현**
  - **선행 작업:** IMP-140
  - EMPTY / PARTIAL / GROUNDED / VERIFIED와 generation을 관리한다.
  - **완료 조건:** 의미 있는 Knowledge 변화에 generation이 증가한다.

- [ ] **IMP-142 — Candidate 검토 / 승격 / 중복 처리 구현**
  - **선행 작업:** IMP-140, IMP-141
  - Candidate를 기존 Knowledge와 비교해 Evidence 추가, 신규 Claim, Conflict로 처리한다.
  - **완료 조건:** 세 가지 결과가 테스트된다.

### Day 15 — Knowledge Research 수집 흐름을 만든다

#### Bundle 15A — Knowledge Research Pipeline

- [ ] **IMP-150 — KnowledgeResearchJob 구현**
  - **선행 작업:** IMP-141
  - Book 단위 Research Job을 기록하고 중복 실행을 방지한다.
  - **완료 조건:** 같은 Book에 동시 PREPARING 요청이 하나의 Job으로 병합된다.

- [ ] **IMP-151 — Search / Fetch / Extraction Pipeline 구현**
  - **선행 작업:** IMP-150
  - 제한된 query/source budget으로 외부 자료를 수집한다.
  - **완료 조건:** Source 수집과 실패 처리가 검증된다.

### Day 16 — 안전한 Knowledge 추출 경계를 만든다

#### Bundle 16A — Safe Knowledge Extraction

- [ ] **IMP-152 — Prompt Injection Guard 삽입 지점 구현**
  - **선행 작업:** IMP-151
  - 외부 문서를 Untrusted Input으로 검사하고 위험한 문서를 차단/보류한다.
  - **완료 조건:** 악성 지시문 포함 문서가 Knowledge로 바로 승격되지 않는다.

- [ ] **IMP-153 — Knowledge Extractor LLM 구현**
  - **선행 작업:** IMP-152
  - Tool 권한 없이 Structured Candidate만 생성한다.
  - **완료 조건:** Source에서 Candidate가 생성되고 Application Validation을 통과한다.

### Day 17 — 인터뷰 연속성과 Grounding을 보강한다

#### Bundle 17A — 인터뷰 재개·초기화

- [ ] **IMP-160 — Interview Resume 구현**
  - **선행 작업:** IMP-073
  - 사용자가 중단한 인터뷰를 이어서 진행할 수 있게 한다.
  - **완료 조건:** 브라우저를 닫아도 진행 상태가 유지된다.

- [ ] **IMP-161 — 14일 Restart 정책 구현**
  - **선행 작업:** IMP-160
  - IN_PROGRESS Interview를 14일 이후 같은 책에 한해 초기화할 수 있게 한다.
  - **완료 조건:** 정책 조건과 기존 답변 삭제 안내가 검증된다.

#### Bundle 17B — Interview Grounding

- [ ] **IMP-162 — Grounding 관계 저장 및 검증**
  - **선행 작업:** IMP-073, IMP-140
  - BookKnowledge 기반 질문의 grounding을 저장하고 잘못된 grounding_id를 검증한다.
  - **완료 조건:** 질문에 사용된 Knowledge를 추적할 수 있다.

### Day 18 — Reflection 완료 처리를 구현한다

#### Bundle 18A — Reflection 완료 처리

- [ ] **IMP-170 — Reflection 완료 상태와 Commit Boundary 구현**
  - **선행 작업:** IMP-094, IMP-132
  - DRAFT → FINALIZING → COMPLETED 흐름을 구현한다.
  - **완료 조건:** 완료 시점에만 파생 데이터가 반영된다.

### Day 19 — Reader Insight와 Backoffice 기반을 준비한다

#### Bundle 19A — Reader Insight

- [ ] **IMP-171 — Evaluation Dimension / Score 추출 구현**
  - **선행 작업:** IMP-170
  - Reflection에서 구조화된 Evaluation Signal을 추출한다.
  - **완료 조건:** 언급된 항목만 sparse하게 저장된다.

- [ ] **IMP-172 — Reader Insight Aggregate 구현**
  - **선행 작업:** IMP-171
  - 책별 평가 신호를 집계하고 표본 수와 신뢰도를 함께 보여준다.
  - **완료 조건:** 사용자가 완성한 책의 Reader Insight를 볼 수 있다.

#### Bundle 19B — Backoffice 기반

- [ ] **IMP-180 — Backoffice 기본 Shell 구현**
  - **선행 작업:** IMP-004, IMP-010
  - Staff 전용 Layout과 접근 제어를 구현한다.
  - **완료 조건:** 비관리자는 접근할 수 없다.

### Day 20 — Backoffice 운영 화면을 완성한다

#### Bundle 20A — Backoffice 운영 화면

- [ ] **IMP-181 — 관리자 Credit 지급 화면 구현**
  - **선행 작업:** IMP-130, IMP-180
  - 관리자가 테스트 목적으로 Credit을 지급/조정할 수 있게 한다.
  - **완료 조건:** Wallet과 Ledger가 함께 반영된다.

- [ ] **IMP-182 — Knowledge Candidate 검토 화면 구현**
  - **선행 작업:** IMP-142, IMP-180
  - Candidate를 승인/거절/병합할 수 있게 한다.
  - **완료 조건:** 관리자가 LLM 결과를 확정 전 수정할 수 있다.

### Day 21 — Full MVP 품질을 평가한다

#### Bundle 21A — Full MVP 품질 평가

- [ ] **IMP-190 — 유명 책 5권 / 비주류 책 5권 평가 세트 구축**
  - **선행 작업:** IMP-153, IMP-172
  - 질문 품질, 사실 오류, 꼬리질문, Reflection 충실도를 평가할 책 세트를 만든다.
  - **완료 조건:** 평가 결과를 반복 비교할 수 있다.

- [ ] **IMP-191 — AI Interview 품질 평가 및 튜닝**
  - **선행 작업:** IMP-190
  - 실제 인터뷰 결과를 바탕으로 질문 정책과 prompt를 조정한다.
  - **완료 조건:** 질문이 책과 사용자 답변을 안정적으로 반영한다.
  - **Acceptance Rubric (수동):** 직전 답변을 무시하지 않는다. 이미 충분히 다룬 내용은 불필요하게 반복하지 않는다. Book Knowledge가 사용자 경험보다 우위에 서지 않는다. 검증되지 않은 READY_LIMITED 자료를 사실로 단정하지 않는다.

### Day 22 — Release 회귀를 검증한다

#### Bundle 22A — Release Verification

- [ ] **IMP-192 — Full MVP E2E / Regression Test 정리**
  - **선행 작업:** IMP-172, IMP-182, IMP-191
  - 핵심 사용자 흐름과 주요 실패 시나리오를 테스트한다.
  - **완료 조건:** 배포 전 회귀 테스트가 통과한다.

### Day 23 — Production Readiness를 정리한다

#### Bundle 23A — Production Readiness

- [ ] **IMP-193 — 배포 / 운영 최소 설정**
  - **선행 작업:** IMP-192
  - 환경변수, secret, DB migration, static files, 로그 확인 흐름을 정리한다.
  - **완료 조건:** 새 환경에서 Full MVP를 배포하거나 재현 가능하게 실행할 수 있다.

---

# Part C. Post-MVP Growth / Retention Backlog

아래는 Product Planning에 반영된 장기 아이디어이며 Full MVP 이후 별도 계획에서 다룬다.

- [ ] 공개 Reflection / 공유 링크
- [ ] SNS 공유용 1장 Insight Card
- [ ] Monthly Free Pass
- [ ] 공개 전환 리워드 실험
- [ ] 선택형 악마의 대변인 Interview Mode
- [ ] Time Capsule / Echo
- [ ] 개인 지식 그래프
- [ ] 심층 취향 리포트
- [ ] Reflection Collection / 큐레이션 글
- [ ] 신작 서평단 Quest
