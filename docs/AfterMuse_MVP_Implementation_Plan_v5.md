# AfterMuse MVP Implementation Plan v5

> 상태: 구현 실행 계획 (2026-09-14 실제 작업량 기준 일정 재배치)
> 목적: AfterMuse 구현 작업을 실제 하루 작업량에 맞게 배치하고, 2주 Core MVP와 이후 보완·Full MVP Backlog를 분리한다.
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

- `Day`는 실제 하루에 함께 처리할 구현 작업 묶음이다.
- `IMP`는 독립적으로 완료 여부를 판단할 수 있는 구현·검증 단위다.
- 하나의 Day에는 작업량과 선행 관계에 따라 하나 이상의 IMP가 들어갈 수 있다.
- `IMP-xxx` 번호와 선행 관계는 일정 변경과 무관하게 유지한다.
- 하루 안에 완료하지 못한 작업은 다음 작업일로 이월한다.
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

> 알라딘 OpenAPI 종료 대응을 포함한 기존 Day 01~07 구현을 유지하고, Day 08~14를 핵심 제품 가설 검증에 필요한 작업으로 배치한다.

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
Low-information 조기 종료 고도화 / 이전 답변 보기
Mobile 핵심 흐름 별도 검증 / Demo 데이터와 실행 가이드 정리
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

- [x] **IMP-010 — 최소 사용자 인증 구현**
  - **선행 작업:** IMP-002, IMP-004
  - 회원가입, 로그인, 로그아웃의 MVP 흐름을 구현한다.
  - **완료 조건:** 신규 사용자가 가입 → 로그인 → 로그아웃을 수행할 수 있다.

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

- [x] **IMP-060 — LLM Provider Adapter 최소 구현**
  - **선행 작업:** IMP-003
  - Interview 질문/Reflection 생성을 위한 LLM Adapter 경계를 만든다.
  - 테스트에서는 fake provider를 사용할 수 있어야 한다.
  - **완료 조건:** 실제 Provider 없이도 질문 생성 흐름을 테스트할 수 있다.

- [x] **IMP-061 — Interview Context Pack 구성**
  - **선행 작업:** IMP-041, IMP-050
  - Book, 최소 Knowledge, Reading 상태를 LLM 입력용 Context로 구성한다.
  - READY_LIMITED에서는 책 내용을 단정하지 않게 한다.
  - **완료 조건:** READY/READY_LIMITED별 Context가 다르게 생성된다.

- [x] **IMP-062 — 첫 질문 생성 구현**
  - **선행 작업:** IMP-060, IMP-061
  - Reading/Knowledge 상태에 따라 첫 질문을 생성한다.
  - Knowledge가 부족하면 기억 중심 질문으로 시작한다.
  - **완료 조건:** READY와 READY_LIMITED에서 각각 적절한 첫 질문이 나온다.

- [x] **IMP-063 — Interview 질문 화면 구현**
  - **선행 작업:** IMP-051, IMP-062
  - 일반 Chat UI가 아니라 한 번에 하나의 질문에 집중하는 화면을 구현한다.
  - **완료 조건:** 첫 질문을 보고 답변을 입력할 수 있다.

- [x] **IMP-064 — 답변 저장 구현**
  - **선행 작업:** IMP-063
  - 사용자의 답변을 먼저 안전하게 저장한다.
  - LLM 실패가 답변 유실로 이어지지 않아야 한다.
  - **완료 조건:** 정상/실패 상황에서 답변이 보존된다.

### Day 07 — 답변에 따라 다음 질문이 이어진다

- [X] **IMP-070 — Coverage 기본 구조 구현**
  - **선행 작업:** IMP-064
  - MEMORY / REACTION / CONNECTION / AFTERTHOUGHT 중심의 Core Coverage를 저장한다.
  - 초기에는 UNCOVERED / PARTIAL / COVERED 정도로 단순화한다.
  - **완료 조건:** 답변 후 Coverage 상태를 갱신할 수 있다. PostgreSQL migration round-trip,
    상태 전환·소유권·동시성 회귀 테스트와 `scripts/verify.py`로 검증했다.

- [x] **IMP-071 — Answer Analysis 최소 구현**
  - **선행 작업:** IMP-060, IMP-070
  - LLM 또는 fake provider를 통해 답변의 의미, low-information 여부, coverage patch를 얻는다.
  - **완료 조건:** 정상/low-information 답변, 원문 근거, strict Coverage 상승 후보와
    Provider 오류 경계를 fake·OpenAI Adapter 및 Service 회귀 테스트와 `scripts/verify.py`로
    검증했다.

- [x] **IMP-072 — 다음 질문 생성 구현**
  - **선행 작업:** IMP-071
  - 기존 답변과 Coverage를 반영해 다음 질문을 생성한다.
  - LLM은 질문을 제안하고, Application이 상태를 갱신한다.
  - **완료 조건:** 답변·Coverage 기반 질문과 검증된 질문 생략을 fake·OpenAI Adapter,
    Service 및 `scripts/verify.py`로 검증했다.

- [x] **IMP-073 — Interview Step 통합**
  - **선행 작업:** IMP-064, IMP-070, IMP-071, IMP-072
  - 답변 저장 → 분석 → Coverage 갱신 → 다음 질문 저장 흐름을 연결한다.
  - **완료 조건:** 답변 선저장, Coverage·다음 Turn 원자성, 3답변→4번째 질문,
    생략·실패·동시성·소유권·재접속을 PostgreSQL 회귀 테스트와 `scripts/verify.py`로 검증했다.

- [x] **IMP-074 — Gemini / Local Ollama Provider Adapter**
  - **선행 작업:** IMP-073
  - 기존 세 Interview capability 계약을 유지하며 Gemini와 로컬 Ollama를 명시적으로 선택한다.
  - Provider별 credential, 모델, timeout을 환경변수로 지정하고 외부 결과는 Application 검증 경계를 통과한다.
  - 기본 자동 테스트는 외부 연결 없이 실행하며 실제 Provider의 세 작업 smoke는 명시적으로만 실행한다.
  - **완료 조건:** factory 선택·설정 오류, 세 작업의 구조화 요청·오류 매핑을 단위 테스트로 확인한다.

### Day 08 — 질문 상한과 Soft Stop을 연결한다

- [x] **IMP-080 — 질문 Budget / Safety Cap 구현**
  - **선행 작업:** IMP-073
  - 질문 목표 수, 기본 상한, 안전 상한을 단순 설정값으로 둔다.
  - **완료 조건:** 일반 8문항에서 멈추고, 미탐색 축에 근거 있는 질문과 명시적 선택이 있을 때만 최대 10문항까지 이어진 뒤 독서노트 준비 안내를 표시한다.

- [x] **IMP-081 — Soft Stop 구현**
  - **선행 작업:** IMP-070, IMP-080
  - Coverage가 충분하면 독서노트 만들기 / 조금 더 이야기하기 선택지를 보여준다.
  - **완료 조건:** Soft Stop에서 사용자가 종료 또는 계속을 선택할 수 있다.

- [x] **IMP-084 — Interview 오류/재시도 UX 구현**
  - **선행 작업:** IMP-073
  - LLM 실패, timeout, 잘못된 응답에서 답변이 보존되며 재시도할 수 있게 한다.
  - **완료 조건:** 다음 질문 생성 실패 후에도 사용자가 복구할 수 있다.
  - **현재 구현 확인:** next_turn 실패 시 저장된 답변을 보존하고 오류 화면에서 동일 endpoint로 재시도한다. 관련 view 테스트에 답변 보존·재시도 표시 검증이 있다.

### Day 09 — Core Home 사용자 상태 연결과 인터뷰 재진입 UI

Core MVP의 최소 Navigation Hub를 구축하여 현재 사용자의 실제 독서/인터뷰 상태를 연결하고, 진행 중인 인터뷰로 안전하게 복귀하는 재진입 UI를 구현한다.

- [ ] **IMP-085 — Core Home / 사용자 상태 연결**
  - **선행 작업:** IMP-033, IMP-050, IMP-073, IMP-084
  - Home을 Full Library로 만드는 것이 아니라, Core MVP에서 사용자가 현재 상태와 다음 행동을 찾을 수 있는 최소 Navigation Hub로 만든다.
  - 하드코딩된 샘플 데이터를 걷어내고 현재 사용자의 실제 데이터(Reading 및 진행 중 Interview)를 바탕으로 Home UI를 렌더링한다. (아직 생성되지 않은 Reflection 연계는 Day 12 IMP-094에서 담당한다.)
  - **상태별 동작 및 UI:**
    - **Reading 없음:** `[책 찾아보기]` 버튼으로 도서 검색 화면으로 유도한다.
    - **읽고 싶음 / 읽는 중 Reading:** '지금 읽고 있는 책' 섹션에 도서 정보와 독서 상태를 표시하고, `[독서 기록 계속하기]` 버튼으로 해당 Reading 상세 화면으로 이동한다.
    - **완독 Reading + Interview 없음:** '사색을 기다리는 책' 섹션에 도서 정보와 완독 상태를 표시하고, `[AI 독서노트 만들기]` 버튼을 제공한다. 이 버튼은 도서 검색으로 이동하지 않고 해당 Reading의 Interview 시작 화면으로 직접 이동한다.
    - **진행 중 Interview:** '진행 중인 인터뷰' 섹션에 진행 상황을 표시하고 `[인터뷰 이어하기]` 버튼을 제공한다. 새 Interview를 생성하지 않고 기존 Interview를 연다.
  - **완료 조건:**
    - Home의 도서/상태가 하드코딩된 샘플이 아니며 실제 사용자 데이터를 반영한다.
    - 실제 Reading 상태(읽고 싶음/읽는 중/완독)가 Home에 즉시 반영된다.
    - 완독 후 다시 책을 검색하지 않고 Home에서 바로 Interview를 시작할 수 있다.
    - 진행 중 Interview에 Home에서 다시 접근할 수 있다.

- [ ] **IMP-086 — Core Interview 재진입 UI**
  - **선행 작업:** IMP-073, IMP-085
  - Core MVP에서 필요한 최소 Resume(재진입) 경로를 구현한다. 사용자가 인터뷰 진행 중 브라우저를 닫거나 이탈한 후에도 Home을 통해 직전 진행 상태로 복귀할 수 있게 한다.
  - **재진입 흐름:** `Interview 진행 → 페이지 이탈 → Home → [인터뷰 이어하기] → 기존 미완료 Turn 화면`
  - **완료 조건:**
    - 재진입 시 새 Interview가 중복 생성되지 않는다.
    - 기존 질문/답변 상태가 유실 없이 유지된다.
    - 현재 미완료 Turn으로 정확하게 돌아갈 수 있다.
  - **명시적 제외 사항 (Full MVP 이관):** Restart, 14일 재시작 제한 정책, 기존 답변 삭제 정책 안내, Restart Confirm UX 등은 여기에서 구현하지 않고 기존 Full MVP Resume 작업(IMP-160, IMP-161)에서 처리한다.

### Day 10 — Reflection 기본 모델과 생성 Prompt / Adapter

Interview 결과를 저장할 Reflection 모델을 구현하고, 사용자 답변에만 근거하여 에세이 초안을 생성하는 LLM Prompt 및 Provider Adapter 경계를 완성한다.

- [ ] **IMP-090 — Reflection 기본 모델 구현**
  - **선행 작업:** IMP-050
  - Interview 결과를 바탕으로 Reflection 초안과 사용자 수정본을 저장할 수 있게 한다.
  - **완료 조건:** Reflection Draft를 저장/조회할 수 있다.

- [ ] **IMP-091 — Reflection 생성 Prompt / Adapter 구현**
  - **선행 작업:** IMP-060, IMP-073, IMP-090
  - Interview 답변만을 근거로 Reflection 초안을 생성한다.
  - 사용자가 말하지 않은 생각을 추가하지 않는 규칙을 포함한다.
  - **완료 조건:** fake provider 및 실제 provider에서 Markdown 초안을 생성할 수 있다.

### Day 11 — Interview 상호작용 완결과 Reflection 생성 Transition

Interview 도중 질문을 건너뛸 수 있는 액션을 추가하고, 내부 도서 지식 안내 표현을 친화적으로 정리하며, 인터뷰 종료 후 Reflection 생성 중 로딩 및 재시도/멱등성 전이 흐름을 완성한다.

- [ ] **IMP-092 — Reflection 생성 Transition 구현**
  - **선행 작업:** IMP-080, IMP-081, IMP-091
  - Soft Stop에서 종료를 선택하거나 질문 budget/safety cap에 도달했을 때 Reflection 생성 화면으로 이동하며, LLM 생성 과정의 UI 상태(생성 중, 성공, 실패, 재시도)를 처리한다.
  - **정상 흐름:** `Interview 종료 → Reflection 생성 중 (Loading UI) → 성공 → Reflection 결과 화면`
  - **실패 및 재시도 흐름:** `Reflection 생성 실패 → 기존 Interview 답변 보존 → 오류 안내 → 다시 시도 (Retry CTA)`
  - **완료 조건:**
    - 생성 중(Loading) 상태가 사용자에게 명확히 표시되고 중복 호출을 방지한다.
    - 생성 실패 상태가 사용자에게 친절하게 표시된다.
    - Retry가 가능하며, 재시도 시 기존 Interview 답변이 절대 유실되지 않는다.
    - Retry로 인해 동일 Interview에 중복 Reflection이 만들어지지 않는다 (멱등성 보장).
    - 생성 완료 시 Reflection 결과 화면으로 자동 전환된다.

- [ ] **IMP-095 — Book Knowledge 사용자용 상태 표현 정리**
  - **선행 작업:** IMP-042, IMP-051, IMP-063
  - 기존 `READY / READY_LIMITED` 도메인 상태는 유지하되, 사용자에게 보이는 표현 계층만 친화적으로 정리한다.
  - **원칙:**
    - 사용자에게 `READY`, `READY_LIMITED`, `Knowledge readiness`, `RAG 상태` 등 내부 enum이나 기술 용어를 직접 노출하지 않는다.
    - `READY_LIMITED` 상태는 시스템 결함처럼 표시하지 않고, 사용자 친화적인 안내 문구(예: *"이 책에 대해 확인할 수 있는 정보가 많지 않아, 기억에 남은 내용부터 함께 이야기해볼게요."*)를 사용한다.
    - Knowledge가 부족한 상태에서 AI가 책 내용을 아는 척하거나 사실을 단정하지 않고, 사용자의 주도적인 기억과 감상을 묻는다.
  - **완료 조건:**
    - Interview 시작 화면, 질문 화면 등 사용자 접점 UI에 내부 Knowledge enum이 직접 나타나지 않는다.
    - `READY_LIMITED` 상태에서도 자연스럽게 Interview를 시작하고 진행할 수 있다.
    - Knowledge가 부족한 상태에서 AI가 책 내용을 아는 척하지 않는다.

- [ ] **IMP-096 — Interview 질문 건너뛰기 구현**
  - **선행 작업:** IMP-073, IMP-080
  - 사용자가 현재 질문에 답하기 어렵거나 답하고 싶지 않을 경우 명시적으로 건너뛸 수 있는 기능을 추가한다.
  - **Skip 구분 원칙:**
    - Skip은 빈 답변(`""`), low-information 답변(예: "모르겠어요"), 실제 사용자 답변과 엄격히 구분하여 처리한다.
    - 빈 문자열 Answer 레코드 저장으로 우회하지 않고, Skip된 상태를 명시적으로 구분하여 처리한다.
    - Skip된 Turn은 Coverage를 무리하게 올리지 않으며, 다음 질문 생성 또는 질문 Budget/Safety Cap에 따른 종료 판단으로 정상 진행된다.
  - **완료 조건:**
    - Interview 화면에서 질문을 건너뛸 수 있는 `[건너뛰기]` 액션이 제공된다.
    - 빈 문자열 Answer 저장으로 구현하지 않는다.
    - Skip된 Turn과 실제 Answer를 구분할 수 있다.
    - Skip 후 다음 질문 생성 또는 Interview 종료 판단이 정상 진행된다.

### Day 12 — Reflection 결과/수정과 Home 재진입 및 검증 준비

AI 결과물이 아닌 독서 에세이 형태의 Reflection 결과 화면과 직접 수정 UX를 구현하고, Home '최근 독서노트' 재진입을 완성하며, 2주 E2E 검증용 책 세트(Seed 및 READY_LIMITED)를 준비한다.

- [ ] **IMP-093 — Reflection 결과 화면 구현**
  - **선행 작업:** IMP-090, IMP-092
  - AI 생성 결과 화면보다는 사용자의 독서 기록처럼 보이는 에세이 결과 화면을 구현한다.
  - **UX 기준:**
    - 책 제목, 저자, 작성일, Reflection 본문을 명확하게 구분한다.
    - 긴 Reflection을 몰입해서 읽기 편한 타이포그래피와 레이아웃을 적용한다.
    - 결과 화면에서 `[수정]` 및 `[Home으로]` 명확한 이동 진입점을 제공한다.
  - **완료 조건:**
    - 긴 글을 읽기 편하고 책 제목/저자/작성일/본문이 명확히 구분되어 표시된다.
    - AI 도구 결과물보다 사용자의 독서 기록 에세이로 자연스럽게 느껴진다.
    - `[수정]` 및 `[Home으로]` 진입점이 정상 동작한다.

- [ ] **IMP-094 — Reflection 수정 구현 및 Home 재진입 연계**
  - **선행 작업:** IMP-085, IMP-093
  - 사용자가 생성된 Reflection을 직접 수정하고 보완할 수 있는 흐름을 구현하고, Reflection 생성/저장 후 Home에서 다시 접근할 수 있는 최소 재진입 경로를 완성한다.
  - **편집 및 이동 흐름:** `Reflection 수정 → 저장 → 저장 완료 피드백 (인라인/토스트) → 결과 화면`
  - **Home 연계 (최소 재진입 경로 완성):**
    - Reflection이 생성/저장된 이후에는 IMP-085에서 구축한 Core Home에 '최근 독서노트' 섹션을 활성화하고 `[독서노트 보기]` 버튼을 제공하여 해당 Reflection 결과 화면으로 다시 접근할 수 있게 한다.
    - 다수의 Reflection 아카이브나 서재 필터링 등 전체 Library 기능은 Full MVP(IMP-122)로 분리하고, 여기서는 방금 또는 최근 완성된 Reflection으로의 최소 재진입만 연결한다.
  - **완료 조건:**
    - 수정한 내용이 DB에 안전하게 저장된다.
    - 저장 완료 즉시 사용자 피드백이 제공되고 결과 화면으로 복귀한다.
    - Reflection 저장 후 Home의 '최근 독서노트'에서 실제 저장된 Reflection을 다시 열 수 있고 수정된 내용이 유지된다.
    - IMP-085에서 만든 Core Home 구조를 확장하되, 기존 Reading / Interview 기본 동작을 깨뜨리지 않는다.

- [ ] **IMP-100 — 2주 검증용 책 세트 구성**
  - **선행 작업:** IMP-041, IMP-094
  - Seed Knowledge가 있는 책과 READY_LIMITED 책을 포함한 최소 검증 세트를 준비한다.
  - **완료 조건:** 최소 3권 이상으로 테스트할 수 있다.

### Day 13 — 전체 Core Loop E2E 검증 및 핵심 품질 1차 조정

Desktop 및 Mobile 환경에서 실제 검증용 책들로 전체 Core Loop 수동 E2E를 완주하고, 발견된 핵심 제품 가설 저해 문제에 대해 인터뷰 질문 품질과 Reflection 충실도를 1차 조정한다.
새로운 기능이나 디자인 polish를 추가하는 날로 바꾸지 않고, Day 13 E2E에서 발견된 문제 중 **Core Loop를 막는 문제만** 처리한다.

- [ ] **IMP-101 — End-to-End 수동 시나리오 검증**
  - **선행 작업:** IMP-085, IMP-086, IMP-094, IMP-095, IMP-096, IMP-100
  - 화면 단위의 고립된 검증을 넘어, 실제 사용자 Navigation과 상태 전이를 포함하여 Desktop 및 Mobile에서 전체 Core Loop를 직접 수행한다.
  - **Desktop 전체 Core Loop 검증 시나리오:**
    ```text
    회원가입 / 로그인
      ↓
    Home (초기 빈 상태 확인)
      ↓
    책 검색 ([책 찾아보기] 클릭)
      ↓
    책 선택 및 등록
      ↓
    Reading 생성 (읽는 중 / 완독)
      ↓
    Home에서 Reading 상태 반영 확인
      ↓
    완독 처리
      ↓
    Home ('사색을 기다리는 책' 카드 확인)
      ↓
    [AI 독서노트 만들기] (도서 검색으로 돌아가지 않고 바로 이동)
      ↓
    Interview 시작 (책 확인 및 내부 Knowledge enum 미노출 확인)
      ↓
    몇 개 질문에 답변 및 질문 [건너뛰기] 확인
      ↓
    Interview 중간 이탈 (브라우저 닫기/다른 페이지 이동)
      ↓
    Home ('진행 중인 인터뷰' 카드 확인)
      ↓
    [인터뷰 이어하기] (새 인터뷰 미생성, 기존 미완료 Turn 복귀)
      ↓
    남은 질문 완료 및 Interview 종료
      ↓
    Reflection 생성 Transition (생성 중 Loading 및 실패 시 Retry 확인)
      ↓
    Reflection 결과 확인 (가독성 레이아웃, 독서 기록 감성)
      ↓
    [수정] 클릭 → Reflection 수정 및 저장 (저장 완료 피드백 확인)
      ↓
    Home ([Home으로] 이동)
      ↓
    Reflection 다시 열기 ('최근 독서노트'에서 확인 및 재진입)
    ```
  - **Desktop 검증 기준:** 사용자가 이전 상태를 다시 찾거나 다음 행동으로 나아가기 위해 책 검색부터 불필요하게 반복해야 하는 구간이 없어야 한다.
  - **Mobile 실사용 검증:**
    - 단순한 "화면이 깨지지 않는다" 수준을 넘어, Mobile Viewport 환경에서 실제로 다음 흐름을 끝까지 수행한다:
      `책 검색 → Reading 진입 및 상태 변경 → Interview 질문 확인 → 답변 입력 및 건너뛰기 → Reflection 확인 → Reflection 수정 및 저장`
    - (단, Day 16의 Mobile Hardening 세부 보강 작업은 별도로 유지한다.)
  - **완료 조건:**
    - Desktop에서 팀원이 위 전체 E2E 시나리오를 막힘 없이 완료할 수 있다.
    - Mobile Viewport에서도 전체 핵심 루프를 실제로 조작하여 완주할 수 있음을 검증한다.

- [ ] **IMP-102 — Interview 품질 1차 조정**
  - **선행 작업:** IMP-101
  - 핵심 제품 가설을 깨는 질문 오류만 수정한다. 말투와 취향 수준의 개선은 이후로 미룬다.
  - **완료 조건:** 최소 3권에서 질문이 사용자의 답변과 책 맥락을 반영한다.
  - **Acceptance Rubric (수동):** 직전 답변을 무시하지 않는다. 이미 충분히 다룬 내용은 불필요하게 반복하지 않는다. Book Knowledge가 사용자 경험보다 우위에 서지 않는다. 검증되지 않은 READY_LIMITED 자료를 사실로 단정하지 않는다.

- [ ] **IMP-103 — Reflection 충실도 1차 조정**
  - **선행 작업:** IMP-101
  - 사용자가 말하지 않은 내용이 추가되는 등 핵심 제품 가설을 깨는 충실도 오류만 수정한다.
  - **완료 조건:** Reflection이 사용자 답변 기반이라는 기준을 통과한다.
  - **Acceptance Rubric (수동):** 사용자가 말하지 않은 생각·주장을 추가하지 않는다. AI의 질문 문구를 사용자의 생각으로 재구성하지 않는다. 주요 반응·연결·후속 생각을 보존한다.

### Day 14 — 핵심 오류를 정리하고 진행 여부를 판단한다

회고에서는 계속 진행 / 방향 수정 / 중단 중 하나를 판단한다.

- [ ] **IMP-110 — 핵심 오류 정리 및 Smoke Test 보강**
  - **선행 작업:** IMP-101, IMP-102, IMP-103
  - 핵심 흐름을 막는 오류와 가장 중요한 회귀 테스트를 정리한다.
  - 회귀/Smoke 대상에는 핵심 기능뿐만 아니라 다음 주요 사용자 Navigation 경로를 반드시 포함한다:
    - `Home → Reading`
    - `Home → Interview 시작`
    - `Home → 진행 중 Interview 재진입`
    - `Home → Reflection 재진입`
  - **완료 조건:** 핵심 E2E 흐름 및 4대 사용자 이동 경로가 smoke test 또는 명확한 수동 절차로 검증된다.

- [ ] **IMP-113 — 2주 회고 및 Full MVP 진행 여부 판단**
  - **선행 작업:** IMP-101, IMP-102, IMP-103
  - 핵심 제품 가설이 충분히 흥미로운지 팀이 판단한다.
  - **완료 조건:** 계속 진행 / 방향 수정 / 중단 중 하나를 결정한다.

---

## ★ 2-WEEK CORE MVP COMPLETE

2주 Core MVP 완료 기준:

```text
사용자가 Home에서 책 검색을 시작할 수 있다.
책을 선택하고 Reading을 생성할 수 있다.
Reading 상태가 Home에 실제 데이터로 반영된다.
완독한 Reading에서 책을 다시 검색하지 않고 AI Interview를 시작할 수 있다.
진행 중 Interview에서 나갔다가 다시 이어갈 수 있다.
사용자 답변을 기반으로 질문이 이어진다.
필요한 경우 질문을 건너뛸 수 있다.
Coverage 또는 질문 Budget에 따라 Interview를 종료할 수 있다.
Reflection 생성 중 / 실패 / 재시도 상태가 처리된다.
Interview 답변을 기반으로 Reflection이 생성된다.
Reflection을 직접 수정하고 저장할 수 있다.
저장한 Reflection을 Home에서 다시 찾을 수 있다.
Desktop에서 전체 Core Loop를 수행할 수 있다.
Mobile에서도 핵심 흐름을 수행할 수 있다.
실제 책으로 전체 흐름과 생성 품질을 검증한다.
```

---

# Part B. Core MVP Hardening

Core MVP 직후 보완할 작업이며 Full MVP 기능 구현에 앞서 진행한다.

### Day 15 — Low-information 조기 종료와 이전 답변 확인

반복적인 low-information 답변 시 무리한 질문을 멈추고 조기 종료하는 로직을 처리하며, Interview 화면에서 이전 질문과 답변 내역을 확인할 수 있는 최소 뷰를 구현한다.

- [ ] **IMP-082 — Low-information 조기 종료 처리**
  - **선행 작업:** IMP-071, IMP-080
  - low-information 답변이 반복되면 무리한 꼬리질문을 중단한다.
  - **완료 조건:** 연속 low-information 답변 후 짧은 Reflection 생성 흐름으로 이동한다.

- [ ] **IMP-083 — 이전 답변 보기 최소 구현**
  - **선행 작업:** IMP-073
  - 사용자가 이전 질문/답변을 확인할 수 있게 한다.
  - 수정 기능은 Full MVP 이후로 미룰 수 있다.
  - **완료 조건:** Interview 화면에서 이전 Turn을 확인할 수 있다.

### Day 16 — Mobile UX Hardening 및 반응형 검증

Day 13의 최소 Mobile E2E를 바탕으로, 모바일 실사용 시의 세부 반응형 UX 결함을 보강하고 검증한다.

- [ ] **IMP-104 — Mobile UX Hardening 및 반응형 검증**
  - **선행 작업:** IMP-101
  - Day 13의 최소 Mobile E2E를 바탕으로, 모바일 실사용 시의 세부 반응형 UX 결함을 보강하고 검증한다.
  - 긴 책 제목/저자 줄바꿈, 긴 질문 및 답변 스크롤 처리, 모바일 가상 키보드 활성 시 textarea 및 CTA 가림 방지, 터치 영역(최소 44x44px), Loading/Error 상태 표시, 소형 Viewport(375px/320px) 레이아웃 무결성을 집중 점검한다.
  - **완료 조건:** 다양한 모바일 화면과 가상 키보드 입력 상황에서도 폼 입력과 버튼 조작이 가려지지 않고 핵심 루프를 쾌적하게 수행할 수 있다.

### Day 17 — Demo와 실행 재현성을 정리한다

팀 공유용 시연 책, 계정, 진행 순서를 정리하고, 새 환경에서 Full MVP 재현 실행이 가능하도록 배포 및 로컬 실행 가이드를 완성한다.

- [ ] **IMP-111 — Demo 데이터와 시연 흐름 정리**
  - **선행 작업:** IMP-100, IMP-110
  - 팀 공유용 시연 책, 계정, 진행 순서를 정리한다.
  - **완료 조건:** 누가 시연해도 같은 흐름으로 데모 가능하다.

- [ ] **IMP-112 — 2주 Core MVP 배포 또는 로컬 실행 가이드 정리**
  - **선행 작업:** IMP-110
  - 배포까지 가능하면 배포하고, 어렵다면 재현 가능한 로컬 실행 가이드를 완성한다.
  - **완료 조건:** 다른 팀원이 새 환경에서 실행할 수 있다.

# Part C. Full MVP Backlog

기존 Full MVP 기능을 이어서 구현한다. Day 계획은 Core MVP 이후 작업량에 맞게 다시 조정할 수 있다.

### Day 18 — 독서 Context와 개인 Library를 확장한다

읽기 전 의도와 읽는 중 메모 모델/CRUD를 구축하여 Interview Context에 연계하고, 개인 서재 관점의 Full Library 화면 고도화를 구현한다. (과밀 주의: 모델 및 화면 동시 변경)

- [ ] **IMP-120 — Reading Intention 입력/수정 고도화**
  - **선행 작업:** IMP-033
  - 읽기 전 기대를 Interview Context에 자연스럽게 반영한다.
  - **완료 조건:** Intention이 첫 질문 또는 후속 질문에 활용된다.

- [ ] **IMP-121 — ReadingEntry 작성/수정/삭제 구현**
  - **선행 작업:** IMP-031
  - 읽는 중 짧은 메모를 여러 개 저장하고 수정/삭제할 수 있게 한다.
  - **완료 조건:** Entry가 Interview Context에 활용 가능하다.

- [ ] **IMP-122 — Library / Home 기본 화면 고도화**
  - **선행 작업:** IMP-085, IMP-093
  - Core MVP의 최소 Navigation Hub(IMP-085)와 역할을 명확히 구분하여, 개인 서재 관점의 Full Library/Home으로 고도화한다.
    - `IMP-085`: Core MVP용 최소 Home Navigation Hub (현재 상태 및 다음 행동 최소 연결)
    - `IMP-122`: Full MVP용 개인 Library / Home 고도화 (전체 서재 아카이브, 분류 및 탐색)
  - 다수의 Reading 탐색, 과거 독서 이력 아카이브, 상태별(읽고 싶음/읽는 중/완독) 필터링 및 분류 정렬, 여러 Reflection 탐색, 최근 활동 피드, 서재 정보 구조(IA)를 체계화한다.
  - **완료 조건:** 다수의 Reading과 Reflection을 상태별로 정렬·필터링하여 체계적으로 탐색하고 관리할 수 있다.

### Day 19 — Credit 지갑과 인터뷰 시작 예약 적용

Credit Wallet과 원자적 Ledger 이력을 구현하고, Full MVP 인터뷰 시작 시 Credit을 RESERVED 처리하는 예약 트랜잭션을 연결한다.

- [ ] **IMP-130 — Credit Wallet / Ledger 구현**
  - **선행 작업:** IMP-010
  - available/reserved 수량과 Ledger 이력을 구현한다.
  - **완료 조건:** 관리자 지급, 예약, 소비, 해제가 테스트된다.

- [ ] **IMP-131 — Interview 시작 시 Credit 예약 적용**
  - **선행 작업:** IMP-051, IMP-130
  - Full MVP에서는 Interview 시작 시 Credit을 RESERVED 처리한다.
  - **완료 조건:** Credit 부족/성공/실패 시나리오가 검증된다.

### Day 20 — Book Knowledge 모델을 확장한다

Claim, Source, Evidence, Candidate 구조로 다중 지식 모델을 확장하고, 지식 준비 상태(State)와 세대(Generation) 버전 관리 및 Candidate 검토/승격 도메인 로직을 구현한다. (과밀 주의: 신규 스키마 및 비즈니스 로직 집중)

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

### Day 21 — Knowledge Research 수집 흐름을 만든다

도서 단위 비동기 Research Job을 기록하여 중복 실행을 방지하고, 외부 검색·수집·추출을 위한 Search/Fetch 파이프라인을 구축한다.

- [ ] **IMP-150 — KnowledgeResearchJob 구현**
  - **선행 작업:** IMP-141
  - Book 단위 Research Job을 기록하고 중복 실행을 방지한다.
  - **완료 조건:** 같은 Book에 동시 PREPARING 요청이 하나의 Job으로 병합된다.

- [ ] **IMP-151 — Search / Fetch / Extraction Pipeline 구현**
  - **선행 작업:** IMP-150
  - 제한된 query/source budget으로 외부 자료를 수집한다.
  - **완료 조건:** Source 수집과 실패 처리가 검증된다.

### Day 22 — 안전한 Knowledge 추출 경계를 만든다

외부 수집 문서를 Untrusted Input으로 검사하여 Prompt Injection을 방어하고, 도구 권한 없이 안전하게 Structured Candidate만 생성하는 Extractor LLM을 구현한다.

- [ ] **IMP-152 — Prompt Injection Guard 삽입 지점 구현**
  - **선행 작업:** IMP-151
  - 외부 문서를 Untrusted Input으로 검사하고 위험한 문서를 차단/보류한다.
  - **완료 조건:** 악성 지시문 포함 문서가 Knowledge로 바로 승격되지 않는다.

- [ ] **IMP-153 — Knowledge Extractor LLM 구현**
  - **선행 작업:** IMP-152
  - Tool 권한 없이 Structured Candidate만 생성한다.
  - **완료 조건:** Source에서 Candidate가 생성되고 Application Validation을 통과한다.

### Day 23 — 인터뷰 연속성과 Grounding을 보강한다

기기/브라우저 변경 시 복구 안내를 거쳐 진행 중 인터뷰로 안전하게 복귀할 수 있게 하고, 14일 경과 Restart 정책과 Confirm UX를 처리하며, 질문에 사용된 지식의 Grounding 관계를 저장·검증한다.

- [ ] **IMP-160 — Interview Resume 고도화**
  - **선행 작업:** IMP-086
  - Core MVP의 IMP-086은 동일 세션/브라우저 흐름에서 Home을 통해 기존 Interview로 다시 들어가는 최소 기능만 제공한다.
  - IMP-160은 이를 확장하여 브라우저 변경, 기기 변경, 세션 만료 후 재로그인 등 환경이 바뀌어도 진행 중 Interview를 안전하게 발견하고 복구 안내를 거쳐 현재 미완료 Turn으로 이어갈 수 있게 한다.
  - 기존 Interview 및 Turn 상태 동기화를 처리하되, 인터뷰 초기화(Restart) 정책은 IMP-161로 분리한다.
  - **완료 조건:** 브라우저 또는 기기가 변경되거나 세션이 갱신된 후에도 기존 진행 중 Interview를 안전하게 식별하고 현재 미완료 Turn부터 이어갈 수 있다.

- [ ] **IMP-161 — 14일 Restart 정책 및 Confirm UX 구현**
  - **선행 작업:** IMP-160
  - IN_PROGRESS Interview에 대해 14일 경과 여부에 따른 재시작(Restart) 정책 및 사용자 확인 UX를 전담한다.
  - 마지막 시작/재시작 시점 기준 14일 제한 및 Restart eligibility 판정, 재시작 가능 날짜 계산 및 표시를 구현한다.
  - 같은 책에 대한 Restart 시 기존 질문/답변이 영구 삭제된다는 사전 안내 및 Confirm 모달/UX를 제공한다.
  - 사용자가 명시적으로 승인한 경우에만 안전하게 기존 Interview 상태를 초기화하고 동일한 책으로 새 Interview 흐름을 시작한다.
  - **완료 조건:**
    - 사용자가 14일 정책 조건을 충족했을 때만 Restart할 수 있다.
    - Restart 전 기존 질문/답변이 삭제된다는 점을 명확히 안내한다.
    - 사용자가 명시적으로 Confirm한 경우에만 기존 상태를 초기화한다.
    - Restart 후 동일한 책으로 새 Interview 흐름을 정상 시작할 수 있다.

- [ ] **IMP-162 — Grounding 관계 저장 및 검증**
  - **선행 작업:** IMP-073, IMP-140
  - BookKnowledge 기반 질문의 grounding을 저장하고 잘못된 grounding_id를 검증한다.
  - **완료 조건:** 질문에 사용된 Knowledge를 추적할 수 있다.

### Day 24 — Reflection 완료 처리와 Credit 최종 소비

Reflection의 최종 완료 상태 전이(DRAFT → FINALIZING → COMPLETED)와 commit boundary를 구현하고, 완료 시점에 일치하여 Credit을 소비(CONSUMED) 처리하는 원자적 트랜잭션을 연결한다.

- [ ] **IMP-170 — Reflection 완료 상태와 Commit Boundary 구현**
  - **선행 작업:** IMP-094, IMP-132
  - DRAFT → FINALIZING → COMPLETED 흐름을 구현한다.
  - **완료 조건:** 완료 시점에만 파생 데이터가 반영된다.

- [ ] **IMP-132 — Reflection 완료 시 Credit 소비 적용**
  - **선행 작업:** IMP-094, IMP-131
  - Reflection 최종 완료 시 Credit을 CONSUMED 처리한다.
  - **완료 조건:** 소비와 파생 데이터 commit 경계가 일치한다.

### Day 25 — Reader Insight 평가 신호 추출 및 집계

완성된 Reflection에서 구조화된 다차원 평가 신호(Dimension/Score)를 추출하고, 도서별로 독자 인사이트를 집계하여 표본 수와 신뢰도를 함께 제공하는 Reader Insight 통계 화면을 구현한다.

- [ ] **IMP-171 — Evaluation Dimension / Score 추출 구현**
  - **선행 작업:** IMP-170
  - Reflection에서 구조화된 Evaluation Signal을 추출한다.
  - **완료 조건:** 언급된 항목만 sparse하게 저장된다.

- [ ] **IMP-172 — Reader Insight Aggregate 구현**
  - **선행 작업:** IMP-171
  - 책별 평가 신호를 집계하고 표본 수와 신뢰도를 함께 보여준다.
  - **완료 조건:** 사용자가 완성한 책의 Reader Insight를 볼 수 있다.

### Day 26 — Backoffice 운영 화면을 완성한다

Staff 전용 Layout과 접근 제어 Shell을 구축하고, 관리자가 테스트/보정 목적으로 Credit을 지급·조정하는 화면 및 LLM이 생성한 지식 Candidate를 승인·거절·수정하는 검토 화면을 완성한다.

- [ ] **IMP-180 — Backoffice 기본 Shell 구현**
  - **선행 작업:** IMP-004, IMP-010
  - Staff 전용 Layout과 접근 제어를 구현한다.
  - **완료 조건:** 비관리자는 접근할 수 없다.

- [ ] **IMP-181 — 관리자 Credit 지급 화면 구현**
  - **선행 작업:** IMP-130, IMP-180
  - 관리자가 테스트 목적으로 Credit을 지급/조정할 수 있게 한다.
  - **완료 조건:** Wallet과 Ledger가 함께 반영된다.

- [ ] **IMP-182 — Knowledge Candidate 검토 화면 구현**
  - **선행 작업:** IMP-142, IMP-180
  - Candidate를 승인/거절/병합할 수 있게 한다.
  - **완료 조건:** 관리자가 LLM 결과를 확정 전 수정할 수 있다.

### Day 27 — Full MVP 품질을 평가한다

- [ ] **IMP-190 — 유명 책 5권 / 비주류 책 5권 평가 세트 구축**
  - **선행 작업:** IMP-153, IMP-172
  - 질문 품질, 사실 오류, 꼬리질문, Reflection 충실도를 평가할 책 세트를 만든다.
  - **완료 조건:** 평가 결과를 반복 비교할 수 있다.

- [ ] **IMP-191 — AI Interview 품질 평가 및 튜닝**
  - **선행 작업:** IMP-190
  - 실제 인터뷰 결과를 바탕으로 질문 정책과 prompt를 조정한다.
  - **완료 조건:** 질문이 책과 사용자 답변을 안정적으로 반영한다.
  - **Acceptance Rubric (수동):** 직전 답변을 무시하지 않는다. 이미 충분히 다룬 내용은 불필요하게 반복하지 않는다. Book Knowledge가 사용자 경험보다 우위에 서지 않는다. 검증되지 않은 READY_LIMITED 자료를 사실로 단정하지 않는다.

### Day 28 — Release 회귀를 검증한다

- [ ] **IMP-192 — Full MVP E2E / Regression Test 정리**
  - **선행 작업:** IMP-172, IMP-182, IMP-191
  - 핵심 사용자 흐름과 주요 실패 시나리오를 테스트한다.
  - **완료 조건:** 배포 전 회귀 테스트가 통과한다.

### Day 29 — Production Readiness를 정리한다

- [ ] **IMP-193 — 배포 / 운영 최소 설정**
  - **선행 작업:** IMP-192
  - 환경변수, secret, DB migration, static files, 로그 확인 흐름을 정리한다.
  - **완료 조건:** 새 환경에서 Full MVP를 배포하거나 재현 가능하게 실행할 수 있다.

---

# Part D. Post-MVP Growth / Retention Backlog

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
