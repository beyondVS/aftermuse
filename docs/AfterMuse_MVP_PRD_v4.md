# AfterMuse MVP PRD v4

> 상태: 구현 기준 문서 (Accepted Baseline, 2026-08-31 최신화)
> 목적: AfterMuse 토이프로젝트 MVP에서 **무엇을 만들고, 어떤 제품 규칙을 지켜야 하는지** 정의한다.
> 기술 구현 방식은 `AfterMuse_Architecture_Decisions_v4.md`를 따른다.
> 화면/인터랙션 상세는 기존 `AfterMuse_UI_UX_and_Design_Implementation_Guide_v8.md`를 따른다.
> 구현 작업 순서와 체크리스트는 `AfterMuse_MVP_Implementation_Plan_v5.md`를 따른다.
> 장기 제품 방향과 과금/확장 아이디어는 기존 `AfterMuse_Product_Planning_and_System_Design_Handoff_v9.md`를 참고하되, MVP 범위가 충돌하면 이 PRD가 우선한다.

---

## 1. 제품 개요

### 1.1 제품명

**AfterMuse**

### 1.2 한 줄 정의

AfterMuse는 사용자가 책을 읽은 뒤 AI와 인터뷰하듯 대화하면, AI가 사용자의 생각을 끌어내고 그 답변을 바탕으로 구조화된 독서노트(Reflection)를 만들어주는 서비스다.

### 1.3 핵심 가치

AfterMuse는 AI가 독후감이나 해석을 대신 작성하는 서비스가 아니다.

핵심 경험은 다음과 같다.

```text
책을 읽음
   ↓
AI가 좋은 질문을 함
   ↓
사용자가 짧게 답함
   ↓
필요한 꼬리질문으로 생각을 구체화함
   ↓
사용자가 실제로 말한 범위 안에서 Reflection을 정리함
```

핵심 원칙:

> **빈 노트에 쓰게 하지 말고, 답변하게 해서 노트를 만든다.**

> **AI가 사용자가 말하지 않은 생각을 추가하지 않는다.**

---

## 2. MVP 목표

MVP의 최우선 목표는 기능 수를 늘리는 것이 아니라 다음 제품 가설을 검증하는 것이다.

> **책에 대한 안전한 맥락과 Coverage 기반 AI 인터뷰가 사용자의 생각을 실제로 더 잘 끌어내고, 그 결과가 사용자의 기록처럼 느껴지는 Reflection으로 이어지는가?**

따라서 MVP는 Books-first로 유지한다.

게임, 영화, 드라마 등 다른 콘텐츠 Reflection은 장기 확장 가능성으로만 보존하며 MVP에서는 구현하지 않는다.

### 2.1 2주 Core MVP와 Full MVP 구분

2026-08-31 구현 전략 업데이트에 따라 MVP 구현은 두 개의 완료선을 가진다.

```text
2주 Core MVP
→ 핵심 제품 가설 검증용
→ 책 선택부터 AI Interview, Reflection 생성/수정, 실제 책 검증까지 연결

Full MVP
→ 기존 MVP 범위
→ Credit, Reader Insight, Book Knowledge 자동 Research, Backoffice, Hardening 포함
```

2주 Core MVP는 최종 제품 범위를 축소한 별도 제품 방향이 아니라, 토이프로젝트를 빠르게 검증하기 위한 첫 번째 실행 목표다.

2주 Core MVP에서 우선 검증할 질문은 다음이다.

> 사용자가 책을 선택하고 AI의 질문에 답했을 때, 혼자 빈 노트에 쓰는 것보다 자기 생각이 더 잘 드러나는 Reflection이 만들어지는가?

따라서 2주 Core MVP에서는 다음을 뒤로 미룰 수 있다.

```text
Credit Wallet/Ledger
자동 Book Knowledge Research
Reader Insight
Custom Backoffice
14일 Restart
Time Capsule / 공개 Reflection / Share Card 등 Growth 기능
```

다만 Full MVP에서는 기존 정책을 유지한다. 즉 Credit, Reader Insight, Knowledge Research, Backoffice는 삭제된 것이 아니라 2주 Core MVP 이후 구현할 항목이다.

---

## 3. 대상 플랫폼

MVP는 **Responsive Web Application**으로 제공한다.

지원 우선순위:

1. Desktop Web
2. Mobile Web

Native App과 PWA 전용 기능은 MVP 범위에 포함하지 않는다.

특히 다음 사용자 행동은 모바일 웹에서도 문제없이 가능해야 한다.

- Reading 상태 변경
- 읽는 중 짧은 메모 작성
- AI Interview 진행
- Reflection 확인/수정

---

## 4. MVP 사용자 흐름

```text
회원가입 / 로그인
   ↓
도서 검색
   ↓
도서 선택
   ↓
Reading 생성 또는 기존 Reading 열기
   ↓
읽기 전 기대 / 읽는 중 메모 (선택)
   ↓
완독 처리
   ↓
AI 독서노트 만들기
   ↓
Book Knowledge 준비 확인
   ├─ 충분함 → 인터뷰 시작 가능
   ├─ 제한적 → READY_LIMITED 안내 후 시작 가능
   └─ 부족함 → 준비 후 시작
   ↓
책 최종 확인
   ↓
Credit 예약
   ↓
Coverage 기반 AI Interview
   ↓
Reflection 초안 생성
   ↓
사용자 확인 / 수정
   ↓
Reflection 완료
   ↓
Credit 소비 + 파생 데이터 반영
   ↓
Reader Insight 확인
```

---

## 5. 핵심 도메인 개념

### 5.1 Book

도서 자체를 나타낸다.

MVP에서는 ISBN13을 기준으로 도서를 구분한다.

도서 검색/선택 단계에서 가능한 범위에서 다음 서지정보를 확보한다.

- ISBN
- 제목
- 저자
- 출판사
- 출간일
- 표지
- 책 소개
- 목차

Core MVP의 한국 도서 Metadata Provider는 Kakao 도서 검색 API를 사용한다. 알라딘
OpenAPI는 신규 key 발급과 서비스 종료가 공지되어 운영 후보에서 제외한다.

Work / Edition 모델의 본격적인 분리는 MVP 이후로 미룬다.

### 5.2 Reading

`Reading`은 단순한 User-Book 연결이 아니라 **사용자의 한 번의 독서 경험**을 나타낸다.

같은 사용자가 같은 책을 다시 읽으면 새로운 Reading을 생성할 수 있다.

Reading에는 다음이 포함된다.

- 독서 상태
- 읽기 전 기대 (선택)
- 읽는 중 짧은 메모 (선택)
- 시작일 / 완료일 등 독서 경험 정보

Reading 생성과 기록은 Credit을 사용하지 않는다.

### 5.3 Reflection

Reflection은 완독 후 AI Interview를 통해 만들어지는 독서노트다.

UI에서는 `독서노트`라는 표현을 사용할 수 있지만, 내부 제품 개념은 향후 다른 콘텐츠 확장을 고려해 Reflection으로 유지할 수 있다.

---

## 6. Reading 요구사항

### 6.1 독서 상태

기본 상태:

- 읽고 싶음
- 읽는 중
- 완독

사용자는 이미 읽은 책을 처음 등록할 수도 있으므로 반드시 순차적으로 상태를 거칠 필요는 없다.

### 6.2 읽기 전 기대

선택 기능이다.

예:

> 이 책에서 조직 운영에 적용할 수 있는 아이디어를 얻고 싶다.

강제 입력하지 않는다.

### 6.3 읽는 중 메모

사용자는 Reading에 짧은 메모를 여러 개 남길 수 있다.

예:

- KPI 부분이 회사 상황과 비슷했다.
- 사례는 흥미롭지만 현실성이 떨어지는 것 같다.
- 이 주장은 나중에 다시 생각해보고 싶다.

MVP에서는 메모 타입을 사용자에게 세분화해 요구하지 않는다.

메모는 이후 AI Interview Context에 활용할 수 있다.

메모를 남기지 않아도 Interview는 정상적으로 진행되어야 한다.

### 6.4 재독

같은 책을 다시 읽는 경우 기존 Reading을 덮어쓰지 않고 새로운 Reading을 만든다.

이유는 AfterMuse가 `이 책을 읽었는가`보다 **그 시점에 어떻게 읽고 생각했는가**를 보존하는 서비스이기 때문이다.

---

## 7. Book Knowledge 요구사항

### 7.1 목적

질문의 품질과 사실성을 높이기 위해 단순 서지정보와 별도로 Book Knowledge를 관리한다.

목차 제목만으로 책의 주장이나 내용을 추론하지 않는다.

### 7.2 Knowledge 예시

- Theme
- Argument
- Concept
- Character
- Event
- Chapter Summary
- Context

각 Knowledge는 가능하면 근거 Source와 연결되어야 한다.

### 7.3 Knowledge 준비 상태

사용자가 Reflection 생성을 요청했을 때 Knowledge가 충분하지 않으면 준비 절차를 수행한다.

사용자에게 노출되는 준비 결과는 다음과 같다.

- `READY`: Book-grounded 질문을 안전하게 사용할 수 있음
- `READY_LIMITED`: 공개 정보가 부족하여 사용자 기억/답변 중심으로 Interview 가능
- `FAILED`: 준비 과정 실패

Book Knowledge가 부족하더라도 사용자를 영구적으로 막지 않는다.

### 7.4 READY_LIMITED 원칙

READY_LIMITED에서는 책의 내용을 AI가 알고 있다고 전제하는 질문을 피한다.

예:

> 가장 기억에 남는 주장이나 장면부터 하나 이야기해주세요.

처럼 사용자의 기억을 먼저 확보한다.

### 7.5 Knowledge 수집 원칙

모든 책의 지식을 미리 구축하지 않는다.

사용자가 실제 Reflection 생성을 요청한 책을 우선 준비하는 Lazy / Demand-driven 방식을 사용한다.

Research는 무제한 Agent 방식이 아니라 제한된 Pipeline으로 수행한다.

웹 자료와 사용자 입력은 모두 신뢰되지 않은 입력(Untrusted Input)으로 취급한다.

사용자 Reading/Reflection에서 발견된 새로운 내용은 공용 Knowledge로 즉시 반영하지 않고 검증 후보로 취급한다.

---

## 8. AI Interview 요구사항

### 8.1 핵심 원칙

Interview는 고정된 질문 목록을 소비하는 방식이 아니다.

> **질문 수는 안전장치이고, 종료 판단의 핵심은 생각의 Coverage다.**

### 8.2 질문 종류

#### Book-grounded Question

근거 있는 Book Knowledge가 충분할 때 사용한다.

#### User Memory Question

Knowledge가 부족하거나 사용자의 기억을 먼저 확보해야 할 때 사용한다.

#### Reflection Question

사용자가 실제로 한 답변의 의미를 더 구체화한다.

### 8.3 Context

질문 생성에는 가능한 범위에서 다음을 사용한다.

- Book Knowledge
- Reading의 읽기 전 기대
- ReadingEntry
- 현재까지의 Interview 답변
- 향후에는 사용자 Reading Profile을 추가할 수 있음

ReadingEntry가 충분하면 질문 수가 늘어나는 것이 아니라 **더 짧고 정확한 Interview**로 보상되어야 한다.

### 8.4 Coverage

Coverage는 크게 다음 두 종류로 본다.

#### Core Coverage

대부분의 Reflection에서 기본적으로 필요한 축.

- 기억에 남은 내용
- 반응 / 평가
- 자신의 경험·생각과의 연결
- 읽은 뒤 남은 생각 / 변화 / 여운

책의 성격에 따라 질문 표현은 달라질 수 있다.

#### Focus Coverage

사용자 답변, ReadingEntry, Book Knowledge에서 발견된 특정 주제다.

예:

- KPI와 회사 경험
- 공리주의에 대한 반대
- 특정 인물의 마지막 선택
- 결말에서 느낀 허무함

새로운 Focus가 생겼다고 모두 따라가지 않는다.

최종 Reflection 품질에 의미 있는 주제만 추가 질문 후보가 된다.

### 8.5 질문 수 정책

초기 운영 기준:

- 일반 목표: 5~6문항
- Coverage가 충분한 경우 4~5문항 이후 Soft Stop 가능
- 일반 상한: 8문항
- 절대 안전장치: 10문항

10문항은 목표가 아니라 사용자가 더 이야기하기를 선택했고 중요한 Gap이 남아 있는 경우의 예외적 상한이다.

### 8.6 Soft Stop

Coverage가 충분하면 다음과 같이 사용자가 선택할 수 있어야 한다.

```text
생각이 충분히 정리됐어요.
지금까지의 답변으로 독서노트를 만들 수 있습니다.

[독서노트 만들기]
[조금 더 이야기하기]
```

### 8.7 Low-information 답변

사용자가 연속적으로 다음과 같은 답변을 하면 무리하게 깊게 파고들지 않는다.

- 잘 모르겠어요.
- 딱히 없어요.
- 그냥 괜찮았어요.

초기 정책은 연속 2회의 Low-information 답변을 기준으로 추가 Follow-up을 줄이고, 필요한 핵심 질문만 확인한 뒤 짧은 Reflection으로 종료하는 방향을 사용한다.

정확한 임계값은 실제 사용자 테스트 후 조정할 수 있다.

### 8.8 Interview Resume / Restart

Interview는 자동 저장하며 브라우저를 닫거나 이탈해도 이어서 진행할 수 있어야 한다.

같은 책의 진행 중 Interview는 시작 또는 재시작 후 14일이 지나면 처음부터 다시 시작할 수 있다.

Restart 시:

- 기존 진행 중 질문/답변은 삭제
- 같은 책으로 다시 시작
- 추가 Credit 사용 없음
- 책 변경 불가
- 재시작 가능 시점은 다시 14일 후로 갱신

완료된 Reflection은 Restart 대상이 아니다.

---

## 9. Reflection 요구사항

### 9.1 생성 원칙

Reflection은 사용자가 Interview에서 실제로 말한 생각의 범위 안에서만 작성한다.

AI가 새로운 신념, 해석, 평가를 임의로 추가하지 않는다.

### 9.2 가변 구조

모든 책에 동일한 템플릿을 강제하지 않는다.

비문학 예:

- 기억하고 싶은 주장
- 동의한 부분
- 의문이 남은 부분
- 내 경험과 연결된 생각

소설 예:

- 기억에 남은 장면
- 인물에 대한 생각
- 결말에 대한 해석
- 읽고 난 뒤의 감정

Section의 종류와 개수는 Interview 내용에 따라 달라질 수 있다.

### 9.3 AI 초안과 사용자 기록

AI가 생성한 결과는 최종본이 아니라 초안이다.

사용자는 반드시 직접 수정할 수 있어야 한다.

### 9.4 완료 시점

AI 초안이 생성되었다고 Reflection이 최종 완료된 것으로 보지 않는다.

사용자가 내용을 확인하고 완료한 시점에 최종 Reflection으로 확정한다.

이 시점에만 Reader Insight 등 공용 파생 데이터에 반영한다.

---

## 10. Credit 정책

### 10.1 목적

MVP에서는 실제 결제 기능을 구현하지 않는다.

Credit은 과금보다는 AI Reflection 사용량과 세션 상태를 제어하기 위한 제품 규칙으로 구현한다.

### 10.2 기본 정책

- Reading 생성/수정에는 Credit 사용 없음
- AI Interview 시작 시 Credit 1개 예약
- Reflection 완료 시 예약된 Credit 소비
- Interview 진행 중에는 예약 상태 유지
- 같은 Interview Restart에는 추가 Credit 사용 없음

### 10.3 관리자 지급

원활한 테스트를 위해 관리자는 사용자에게 Credit을 임의로 지급/조정할 수 있어야 한다.

Credit 변경 이력은 추적할 수 있어야 한다.

### 10.4 MVP에서 구현하지 않는 것

- 실제 결제
- Coupon
- Plus 구독
- Free / Paid 기능 구분
- 가격/상품 구매 UX

향후 상용화 기획은 기존 Product Planning 문서에만 유지한다.

---

## 11. Reader Insight

### 11.1 목적

Reflection에서 추출된 구조화된 평가 신호를 익명·집계해 다른 독자의 반응을 보여준다.

개별 사용자의 원문 Reflection을 공용 Insight로 직접 노출하지 않는다.

### 11.2 MVP 정책

MVP에는 Free / Plus Paywall을 구현하지 않는다.

Reflection을 완료한 사용자는 해당 책의 Reader Insight를 확인할 수 있어야 한다.

MVP에서는 `상세 Reader Insight를 읽기 전에 미리 보여주는 Plus 기능`, Personal Fit, Cross-book Insight 등 상용화 후보 기능은 필수 구현 범위에서 제외한다.

### 11.3 표현 원칙

표본 수가 적으면 데이터가 부족하다는 사실을 표시한다.

점수를 객관적 사실처럼 표현하지 않는다.

예:

> 독서노트에서 '내용이 깊다'는 평가 신호가 많이 나타났습니다.

---

## 12. 관리자 기능

MVP의 Backoffice에서는 최소한 다음 업무를 수행할 수 있어야 한다.

### 사용자 / Credit

- 사용자 조회
- Credit 지급
- Credit 조정
- Credit 변경 이력 확인

### Book

- Book 조회
- Metadata 확인/수정

### Book Knowledge

- Book Knowledge 상태 확인
- Knowledge 조회
- Source 조회
- Candidate 검토
- 신규 Knowledge 승인
- 기존 Knowledge에 근거 추가
- Knowledge 폐기/대체
- Conflict 확인/처리
- Research 재실행

관리자 UX는 단순 CRUD뿐 아니라 Candidate 검토와 Knowledge 승인/병합 같은 업무 흐름을 지원해야 한다.

---

## 13. 주요 예외/실패 처리

### 13.1 도서 Metadata 확보 실패

사용자에게 오류를 명확히 표시하고 재시도할 수 있어야 한다.

잘못된 Metadata를 LLM이 추측해 채우지 않는다.

### 13.2 Book Knowledge 준비 실패

사용자에게 다음 선택지를 제공할 수 있다.

- 다시 시도
- 제한된 정보로 Interview 시작

제한된 정보로 시작하면 READY_LIMITED 정책을 적용한다.

### 13.3 Interview 질문 생성 실패

- 사용자가 작성한 답변은 보존
- 현재 Interview 상태 보존
- 재시도 가능

### 13.4 Reflection 생성 실패

Interview 답변과 상태를 보존하고 재시도할 수 있어야 한다.

실패 때문에 Credit을 소비하지 않는다.

### 13.5 Credit 부족

Interview 시작 전에 부족 상태를 명확히 알린다.

MVP에서는 관리자가 테스트 Credit을 지급할 수 있다.

### 13.6 장기간 방치된 Interview

자동 폐기하지 않는다.

사용자는 기존 Interview를 이어서 진행하거나, 정책상 재시작 가능 시점 이후 같은 책으로 Restart할 수 있다.

### 13.7 완독 상태 실수

Interview가 아직 시작되지 않았다면 Reading 상태를 수정할 수 있다.

Interview 시작 이후에는 Interview가 특정 Reading/Book Context를 기준으로 진행되므로 임의로 책이나 독서 경험의 정체성을 바꾸지 않는다.

---

## 14. 보안 / 신뢰 원칙

사용자 답변과 외부 웹 콘텐츠를 모두 Untrusted Input으로 취급한다.

필수 원칙:

- Trusted / Untrusted Context 분리
- LLM Tool 권한 최소화
- Prompt Injection 검사 삽입 지점 확보
- Structured Output 사용
- Application Validation
- DB 상태 변경은 애플리케이션 코드가 수행
- 외부 자료에서 추출된 내용은 검증 전 공용 Knowledge로 확정하지 않음

Interview LLM은 다음 권한을 갖지 않는다.

- 다른 사용자 데이터 접근
- DB 직접 수정
- Credit 변경
- 관리자 기능 호출
- 임의의 웹 검색/도구 실행

---

## 15. MVP 범위

### 포함

- 회원가입 / 로그인
- 도서 검색 / 선택
- Book Metadata 확보
- Reading 생성 및 상태 관리
- 읽기 전 기대
- 읽는 중 짧은 메모
- 완독 처리
- Book Knowledge 준비
- READY / READY_LIMITED
- Coverage 기반 AI Interview
- Resume / 14일 Restart
- Reflection 생성 / 수정 / 완료
- Evaluation Signal 추출
- Reflection 완료 후 Reader Insight
- Credit 예약/소비
- 관리자 Credit 지급/조정
- Knowledge/Source/Candidate 관리 Backoffice
- Prompt Injection 방어 삽입 구조

### 제외

- 실제 결제
- Coupon
- Plus
- Free/Paid Paywall
- 독서 타이머
- OCR
- Kindle/밀리/리디 등 외부 하이라이트 연동
- Streak / Badge
- 복잡한 목표 관리
- 친구 / 팔로우 / 댓글 / 소셜 피드
- 자체 블로그 플랫폼
- Native App
- 게임/영화/드라마 지원
- Collaborative Filtering
- 고급 추천 알고리즘
- Personal Fit / Cross-book Insight의 상용 기능화
- Time-driven Echo 완전 구현

---

## 16. MVP 성공 기준

### 16.1 핵심 실험 세트

최소 다음 두 그룹을 대상으로 실제 Interview를 수행한다.

- Book Knowledge가 비교적 풍부한 유명 책 5권
- 공개 정보가 적은 신간/비주류 책 5권

### 16.2 평가 질문

각 책에서 다음을 평가한다.

1. 질문이 실제 책/사용자 Context와 관련 있는가?
2. 책 내용을 알고 있는 척하며 틀린 사실을 전제하지 않는가?
3. 질문이 너무 일반적이지 않은가?
4. 꼬리질문이 사용자의 생각을 실제로 더 구체화하는가?
5. ReadingEntry가 있으면 질문 품질이 실제로 좋아지는가?
6. READY_LIMITED에서도 Interview가 성립하는가?
7. Reflection에 사용자가 말하지 않은 생각이 추가되지 않는가?
8. 결과물이 AI 독후감보다 `내가 남긴 기록`처럼 느껴지는가?
9. 인터뷰 길이가 지나치게 피곤하지 않은가?

### 16.3 MVP의 핵심 합격 조건

정량 KPI를 억지로 고정하기보다 다음 제품 가설이 사용자 테스트에서 반복적으로 확인되어야 한다.

> **좋은 질문이 사용자의 생각을 더 쉽게 꺼내게 한다.**

> **완성된 Reflection이 사용자가 실제로 말한 생각을 충실하게 보존한다.**

> **Book Knowledge가 부족한 책에서도 서비스가 거짓 전제를 만들지 않고 유용하게 동작한다.**

이 핵심 가설이 성립하지 않으면 부가 기능 확장보다 Interview/Knowledge 설계를 먼저 재검토한다.

---

## 17. 향후 확장 방향 (MVP 비범위)

장기적으로 다음을 검토할 수 있다.

- Echo / Revisit
- Knowledge-driven Follow-up Reflection
- Time-driven Reflection
- 개인 Reading Profile
- 다음 책 추천
- Personal Fit
- Cross-book Insight
- Plus / Credit 판매 / Coupon
- B2B Reader Insight
- 게임 / 영화 / 드라마 등 다른 콘텐츠 Reflection

이 항목들은 현재 MVP 구현 범위를 넓히는 근거로 사용하지 않는다.

---

## 18. 문서 우선순위

MVP 구현 중 문서 간 충돌이 있으면 다음 우선순위를 사용한다.

1. `AfterMuse_MVP_PRD_v3.md`
2. `AfterMuse_Architecture_Decisions_v4.md`
3. `AfterMuse_UI_UX_and_Design_Implementation_Guide_v8.md`
4. `AfterMuse_Product_Planning_and_System_Design_Handoff_v9.md`
5. `AfterMuse_Discord_Concept_Deck_v8.pptx`

PRD가 MVP의 제품 범위를 결정하고, Architecture는 구현 원칙을 결정하며, UI/UX Guide는 화면과 인터랙션의 상세 기준을 제공한다.


---

## 19. 2026-08-26 문서 최신화 내역

이 버전은 MVP 구현 문서 묶음의 기준을 맞추기 위해 다음 사항을 반영한다.

- Architecture 문서를 `v2`로 갱신하여 문서 우선순위와 구현 계획 문서명을 맞춘다.
- UI/UX Guide를 `v6`, Product Planning Handoff를 `v7` 기준으로 참조한다.
- `AfterMuse_MVP_Implementation_Plan_v5.md`를 MVP 구현 작업 체크리스트로 추가한다.
- MVP 범위는 기존 결정대로 유지한다.
  - 실제 결제 구현 없음
  - Coupon / Plus / Free-Paid 기능 제한 없음
  - Credit은 테스트와 AI Reflection 사용량 제어를 위한 도메인 기능으로 구현
  - 기능 구현은 PRD 범위를 우선한다.


---

## 20. 2026-08-30 Growth 아이디어 반영 기준

이번 버전은 공유 카드, 공개 Reflection, Time Capsule, 개인 지식 그래프, 월간 무료 Pass 등 Post-MVP 성장 아이디어를 검토한 결과를 반영한다.

중요한 결론:

```text
MVP 구현 범위는 변경하지 않는다.
```

### 20.1 MVP에 추가하지 않는 항목

다음은 좋은 후보지만 MVP 구현 범위에는 포함하지 않는다.

```text
1장 인사이트 카드 자동 생성
공개 Reflection / 공유 링크
공개 노트 리워드
Monthly Free Pass
악마의 대변인 Interview Mode
Time Capsule / Time-driven Echo
개인 지식 그래프
심층 취향 리포트
Reflection Collection / 블로그형 큐레이션
신작 서평단 Quest
```

### 20.2 PRD 관점의 해석

이 아이디어들은 AfterMuse의 장기 제품 루프를 강화한다.

```text
Reflection 생성
→ 공유 가능한 산출물
→ 외부 유입

Reflection 축적
→ 개인 지식 그래프 / 취향 리포트
→ 서비스에 계속 기록할 이유

시간 경과
→ Time Capsule / Echo
→ 재방문 이유
```

다만 MVP의 핵심 검증은 여전히 다음이다.

```text
좋은 질문이 사용자의 생각을 더 잘 끌어내는가?
완성된 Reflection이 사용자의 실제 생각처럼 느껴지는가?
Book Knowledge가 부족한 책에서도 거짓 전제를 만들지 않는가?
```

따라서 Growth 기능은 MVP 검증 이후 별도 Post-MVP PRD에서 다룬다.

### 20.3 무료 사용권 정책

기존 장기 기획의 분기 Coupon 1장 정책은 Post-MVP에서 재검토한다.

후보 정책:

```text
Monthly Free Pass
- 매월 1개까지 보충
- 최대 보유량 1개
- 이월 누적 없음
- 구매 Credit과 분리
```

MVP에서는 여전히 실제 Coupon / Plus / 결제 구현을 하지 않는다.
Credit은 관리자 지급과 AI Reflection 사용량 제어를 위한 도메인 기능으로만 구현한다.

---

## 21. 문서 최신화 내역

- Product Planning Handoff `v8`의 Growth / Retention 업데이트를 참조한다.
- Architecture Decisions `v3`, UI/UX Guide `v7`, Implementation Plan `v4`, Concept Deck `v8`을 최신 기준으로 참조한다.
- MVP 범위는 기존 v2와 동일하게 유지한다.
