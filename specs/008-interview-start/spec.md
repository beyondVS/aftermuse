# 기능 사양: 인터뷰 시작

**기능 브랜치**: `008-interview-start`

**생성일**: 2026-09-08

**상태**: 초안

**입력**: 사용자 설명: "구현계획 파일의 'Bundle 05B — 인터뷰 시작'을 위한 명세"

## Clarifications

### Session 2026-09-08

- Q: 하나의 Reading에는 전체 수명 동안 Interview를 몇 개까지 연결할 수 있어야 합니까? → A: Reading당 Interview 1개만 허용하며 재시작 시 기존 Interview를 재사용
- Q: 이미 Interview가 있는 Reading에서 `AI 독서노트 만들기`를 다시 선택하면 Interview 상태에 따라 어디로 이동해야 합니까? → A: 진행 중이면 Interview, Reflection 준비 완료면 Reflection 생성·확인, 완료면 완성된 Reflection으로 이동

## 사용자 시나리오 및 테스트 *(필수)*

### 사용자 스토리 1 - 완독한 책으로 인터뷰 시작 (우선순위: P1)

로그인한 사용자는 자신이 완독한 Reading에서 인터뷰 시작 전 책을 최종 확인하고,
확정한 Reading과 Book에 연결된 진행 중 Interview를 시작할 수 있다.

**우선순위가 높은 이유**: 완독한 독서 경험을 변경 불가능한 Interview Context로 확정하는
것은 Reading에서 질문·답변과 Reflection으로 이어지는 핵심 제품 루프의 시작점이다.

**독립 테스트**: 본인 소유의 완독 Reading에서 확인 화면을 열고 인터뷰 시작을 선택한 뒤,
해당 Reading과 Book에 연결된 진행 중 Interview가 하나 생성되고 다시 접근 가능한지 확인한다.

**인수 시나리오**:

1. **Given** Interview가 없는 본인 소유의 완독 Reading이고, **When** 사용자가 `AI 독서노트
   만들기`를 선택하면, **Then** 시스템은 Interview 생성 전에 대상 책의 확인 화면을 보여준다.
2. **Given** 사용자가 확인 화면에서 대상 책을 확인했고, **When** `인터뷰 시작`을 선택하면,
   **Then** 해당 Reading과 Book에 연결된 진행 중 Interview가 생성되고 Interview 진행 화면으로
   이동한다.
3. **Given** Interview가 시작된 Reading이고, **When** 사용자가 Reading의 완독 상태를
   취소하거나 완독일을 수정하려 하면, **Then** 시스템은 변경을 허용하지 않고 Interview가
   시작되어 독서 경험이 확정되었음을 알린다.
4. **Given** 인터뷰 시작 확인 화면이고, **When** 사용자가 `책 다시 선택`을 선택하면,
   **Then** Interview를 생성하지 않고 책을 다시 선택할 수 있는 이전 흐름으로 돌아간다.

---

### 사용자 스토리 2 - 책과 시작 조건 확인 (우선순위: P1)

사용자는 인터뷰를 시작하기 전에 표지와 주요 서지정보로 자신이 읽은 책이 맞는지 확인하고,
시작 후에는 다른 책으로 변경할 수 없다는 결과를 명확히 이해할 수 있다.

**우선순위가 높은 이유**: 동명 도서나 다른 판본의 오선택은 이후 질문과 답변의 의미를
왜곡하므로, 되돌리기 어려운 시작 행동 전에 명시적인 확인이 필요하다.

**독립 테스트**: 확인 화면에서 제공 가능한 책 식별 정보, 변경 불가 안내, 하나의 명확한
시작 행동과 책 재선택 행동이 Desktop 및 Mobile Web에서 구분되는지 확인한다.

**인수 시나리오**:

1. **Given** 시작 가능한 완독 Reading이고, **When** 사용자가 확인 화면을 열면, **Then**
   표지, 제목, 저자, 출판사와 제공 가능한 판본 식별 정보가 표시된다.
2. **Given** 확인 화면이 표시되었고, **When** 사용자가 시작 결정을 검토하면, **Then**
   `인터뷰를 시작하면 다른 책으로 변경할 수 없음`을 시작 행동 전에 알 수 있다.
3. **Given** 키보드 또는 보조 기술을 사용하는 사용자이고, **When** 확인 화면을 탐색하면,
   **Then** 책 정보, 변경 불가 안내, 책 재선택과 인터뷰 시작 행동을 색상에 의존하지 않고
   식별하고 실행할 수 있다.

---

### 사용자 스토리 3 - 준비 수준에 맞춰 안전하게 시작 (우선순위: P1)

사용자는 선택한 Book의 Knowledge가 충분한 경우와 제한적인 경우 모두 Interview를 시작할
수 있으며, 정보가 제한적이면 책 내용을 아는 척하지 않고 기억에 남은 내용부터 다룬다는
안내를 받는다.

**우선순위가 높은 이유**: 비주류 책도 막지 않으면서 근거 없는 질문을 피하는 것은
AfterMuse의 신뢰성과 Core MVP 검증 범위를 함께 지키는 조건이다.

**독립 테스트**: `READY` Book과 `READY_LIMITED` Book에 연결된 완독 Reading에서 각각
확인 화면을 열고 시작하여, 둘 다 Interview가 생성되되 제한 상태에서만 기억 중심 진행
안내가 노출되는지 확인한다.

**인수 시나리오**:

1. **Given** Book 준비 상태가 `READY`인 완독 Reading이고, **When** 사용자가 인터뷰를
   시작하면, **Then** Book Knowledge를 사용할 수 있는 진행 중 Interview가 생성된다.
2. **Given** Book 준비 상태가 `READY_LIMITED`인 완독 Reading이고, **When** 사용자가 확인
   화면을 열면, **Then** 확인 가능한 정보가 제한적이어서 기억에 남은 내용부터 정리한다는
   안내와 인터뷰 시작 행동이 함께 제공된다.
3. **Given** Book 준비 상태가 `READY_LIMITED`인 완독 Reading이고, **When** 사용자가
   인터뷰를 시작하면, **Then** Knowledge 부족만으로 차단되지 않고 기억·답변 중심 진행을
   위한 준비 수준이 Interview에 보존된다.

---

### 사용자 스토리 4 - 진행 중 인터뷰 재진입 (우선순위: P2)

사용자는 같은 Reading에서 시작 행동을 반복하거나 나중에 다시 방문해도 별도 Interview를
중복 생성하지 않고 기존 Interview로 돌아갈 수 있다. 한 Reading의 Interview를 향후
재시작하더라도 새 Interview가 아니라 기존 Interview를 재사용한다.

**우선순위가 높은 이유**: 중복 Interview는 답변과 이후 Reflection의 기준을 분산시키므로,
시작 요청의 반복과 재방문에서도 하나의 독서 경험에 대한 진행 맥락을 유지해야 한다.

**독립 테스트**: 같은 완독 Reading에 대해 시작 요청을 반복하고 다시 방문하여, 진행 중
Interview가 한 건만 유지되고 매번 동일한 Interview가 열리는지 확인한다.

**인수 시나리오**:

1. **Given** 해당 Reading에 진행 중 Interview가 이미 있고, **When** 사용자가 다시
   `AI 독서노트 만들기`를 선택하면, **Then** 새 Interview를 생성하지 않고 기존 Interview로
   이동한다.
2. **Given** 동일한 Reading에 대한 인터뷰 시작 요청이 반복되거나 동시에 도착하고,
   **When** 요청 처리가 완료되면, **Then** 해당 Reading의 Interview는 최대 한 건이며 모든
   성공한 요청은 그 Interview를 연다.
3. **Given** 다른 사용자의 Reading 또는 Interview이고, **When** 사용자가 직접 접근을
   시도하면, **Then** 대상 존재 여부나 내용을 노출하지 않고 접근할 수 없다.
4. **Given** 해당 Reading의 Interview가 Reflection 생성 준비 완료 상태이고, **When** 사용자가
   다시 `AI 독서노트 만들기`를 선택하면, **Then** Reflection 생성·확인 목적지로 판정하고
   현재 단계에서는 아직 사용할 수 없다는 안내를 제공한다.
5. **Given** 해당 Reading의 Interview와 Reflection이 완료 상태이고, **When** 사용자가 다시
   `AI 독서노트 만들기`를 선택하면, **Then** 새 Interview를 시작하지 않고 완성된 Reflection
   목적지로 판정하며 현재 단계에서는 아직 사용할 수 없다는 안내를 제공한다.

### 예외 상황

- 로그인하지 않은 사용자는 확인 화면, Interview 생성 또는 기존 Interview에 접근할 수 없다.
- 본인 소유가 아니거나 존재하지 않는 Reading은 시작 대상으로 사용할 수 없다.
- `읽고 싶음` 또는 `읽는 중` Reading에서는 Interview를 시작할 수 없으며, 완독이 필요함을
  안내한다.
- 저장되지 않은 Reading으로 시작을 요청하거나 기존 Interview의 Book과 잠근 Reading의 Book이
  일치하지 않으면 Interview를 생성·변경하지 않고 기존 데이터를 유지한다.
- 시작 요청 처리 중 오류가 발생하면 부분적으로 생성되거나 Reading·Book 연결이 누락된
  Interview를 남기지 않으며, 사용자는 안전하게 다시 시도할 수 있다.
- 표지나 일부 선택 서지정보가 없더라도 제목과 저자 등 확보된 정보로 확인할 수 있게 하며,
  없는 정보를 추측해 표시하지 않는다.
- 이미 시작된 Interview의 대상 Book이나 Reading을 다른 대상으로 바꾸려는 요청은 거부하고
  기존 연결을 보존한다.

## 요구사항 *(필수)*

### 기능 요구사항

- **FR-001**: 시스템은 Interview를 특정 사용자 소유의 한 Reading과 그 Reading의 한 Book에
  연결된 생각 정리 과정으로 관리해야 한다.
- **FR-002**: 시스템은 Interview와 개별 질문·답변 Turn을 서로 구분해 보존할 수 있어야 한다.
- **FR-003**: 각 Interview Turn은 소속 Interview, Interview 안에서의 순서, 질문 내용과
  선택적으로 입력되는 답변 내용을 식별할 수 있어야 한다.
- **FR-004**: 시스템은 한 Interview 안에서 서로 다른 Turn이 동일한 순서를 갖도록 허용해서는
  안 되며, Turn 조회 시 정해진 순서가 유지되어야 한다.
- **FR-005**: 로그인한 사용자는 자신이 소유한 `완독` Reading에서만 Interview 시작 흐름에
  진입할 수 있어야 한다.
- **FR-006**: 시스템은 Interview 생성 전에 대상 Book 확인 화면을 제공해야 한다.
- **FR-007**: 확인 화면은 Book의 표지, 제목, 저자, 출판사와 ISBN·출간 정보 등 제공 가능한
  판본 식별 정보를 표시하되, 확보되지 않은 정보를 추측해 표시해서는 안 된다.
- **FR-008**: 확인 화면은 Interview 시작 후 다른 Book으로 변경할 수 없음을 시작 행동 전에
  명확히 고지해야 한다.
- **FR-009**: 사용자는 확인 화면에서 Interview를 생성하지 않고 책 선택 흐름으로 돌아가거나,
  명시적으로 `인터뷰 시작`을 선택할 수 있어야 한다.
- **FR-010**: 시스템은 명시적인 시작 선택이 성공했을 때 Reading과 Book이 확정된 진행 중
  Interview를 생성해야 한다.
- **FR-010A**: 시스템은 Interview의 현재 단계를 진행 중, Reflection 생성 준비 완료, 완료로
  구분할 수 있어야 한다.
- **FR-011**: Interview가 시작된 뒤에는 해당 Interview의 Reading 또는 Book을 다른 대상으로
  변경할 수 없어야 하며 변경 시도 시 기존 관계를 보존해야 한다.
- **FR-012**: Interview가 시작된 Reading의 완독 상태 취소와 완독일 변경을 허용해서는 안
  되며 기존 값을 보존해야 한다.
- **FR-013**: 시스템은 Book의 시작 시점 준비 수준을 `READY` 또는 `READY_LIMITED`로 확인해
  Interview에 보존해야 한다.
- **FR-014**: `READY`와 `READY_LIMITED`는 모두 Interview 시작을 허용해야 한다.
- **FR-015**: `READY_LIMITED` 확인 화면은 책에 대해 확인할 수 있는 정보가 제한적이며 사용자
  기억에 남은 내용부터 정리한다는 안내를 제공해야 한다.
- **FR-016**: 같은 Reading에 Interview가 이미 있으면 시스템은 중복 생성하지 않아야 하며,
  진행 중이면 기존 Interview로 이동하고, Reflection 생성 준비 완료 또는 완료 상태이면 각각
  후속 Reflection 흐름의 목적지를 판정해야 한다. 실제 Reflection 화면 연결은 후속 기능에서
  수행하며, 그전에는 현재 단계를 아직 사용할 수 없다는 안내를 제공해야 한다.
- **FR-017**: 동일한 Reading에 대한 반복 또는 동시 시작 요청에서도 전체 수명 동안
  Interview는 최대 한 건만 존재해야 한다.
- **FR-017A**: 향후 진행 중 Interview를 재시작할 때는 새 Interview를 생성하지 않고 기존
  Interview의 상태와 Turn을 보존한 채 같은 Interview로 재진입해야 한다.
- **FR-018**: Interview 생성과 Reading·Book·준비 수준 확정은 일부만 반영되는 결과 없이
  함께 성공하거나 함께 실패해야 한다.
- **FR-019**: 시스템은 사용자에게 자신이 소유한 Interview만 조회하거나 사용할 수 있게 하고,
  다른 사용자의 Reading·Interview 내용과 존재 여부를 노출해서는 안 된다.
- **FR-020**: 확인 화면과 시작 결과는 Desktop 및 Mobile Web에서 동작해야 하며, 키보드와
  보조 기술 사용자가 정보, 안내, 행동 및 오류를 색상 외의 정보로 구분할 수 있어야 한다.
- **FR-021**: 시작 실패 시 시스템은 불완전한 Interview를 남기거나 Reading의 확정 상태를
  잘못 변경해서는 안 되며, 사용자가 다시 시도할 수 있는 안내를 제공해야 한다.
- **FR-022**: Core MVP의 이번 기능은 Interview 시작 또는 완료 시 Credit·Coupon을 예약,
  소비 또는 변경해서는 안 되며 비용이 발생한다는 안내를 표시해서도 안 된다.
- **FR-023**: 이번 기능은 첫 질문 생성, 질문에 대한 답변 제출, Coverage 갱신, Soft Stop,
  Reflection 생성·완료, 14일 재시작 및 판본 정정 절차를 수행하지 않아야 한다.
- **FR-024**: 이번 기능은 시작 시 전체 질문 목록을 미리 생성하거나 고정 설문지를 만들어서는
  안 된다.

### 핵심 엔터티 *(기능에 데이터가 포함되는 경우 작성)*

- **Interview**: 한 사용자의 특정 완독 Reading과 확정된 Book을 바탕으로 생각을 끌어내는
  과정이다. 소유 사용자, Reading, Book, 시작 시점의 Knowledge 준비 수준, 진행 상태와 시작
  시점을 가지며 한 Reading에는 전체 수명 동안 최대 하나만 연결된다. 진행 상태는 재진입 시
  Interview, Reflection 생성·확인 또는 완성된 Reflection 중 현재 단계로 안내하는 기준이다.
- **Interview Turn**: Interview 안의 개별 질문과 그에 대한 선택적 답변을 나타낸다. 소속
  Interview와 순서를 통해 대화 흐름 및 질문·답변의 출처를 추적할 수 있다.
- **Reading**: Interview의 대상이 되는 한 사용자의 한 번의 독서 경험이다. 완독 상태이며
  Interview가 시작되면 완독 상태와 완독일을 변경할 수 없다.
- **Book**: Reading과 Interview가 다루는 확정된 출판 도서이다. 확인 화면에서 사용자가
  표지와 제공 가능한 서지정보로 대상을 검증한다.
- **Knowledge 준비 수준**: Interview 시작 시 질문 정책이 사용할 Book Context 수준이다.
  `READY`는 Book-grounded 질문을 사용할 수 있음을, `READY_LIMITED`는 사용자 기억과 답변을
  우선해야 함을 나타낸다.

## 성공 기준 *(필수)*

### 측정 가능한 결과

- **SC-001**: 본인 소유의 완독 Reading을 사용한 모든 시작 인수 사례에서 Reading, Book,
  사용자와 준비 수준이 올바르게 연결된 진행 중 Interview 생성 성공률이 100%이다.
- **SC-002**: 모든 시작 확인 인수 사례에서 대상 책의 확보된 식별 정보, 시작 후 변경 불가
  안내, 시작 행동과 재선택 행동이 시작 전에 함께 표시되는 비율은 100%이다.
- **SC-003**: `READY`와 `READY_LIMITED`를 포함한 모든 시작 인수 사례에서 Knowledge 부족만으로
  차단되는 경우는 0건이며, 제한 상태 안내 노출 정확도는 100%이다.
- **SC-004**: 같은 Reading에 대한 반복 및 동시 시작 인수 사례에서 Interview 중복은 0건이고
  기존 Interview 재진입 성공률은 100%이다.
- **SC-004A**: 진행 중, Reflection 생성 준비 완료, 완료 상태별 재진입 인수 사례에서 현재
  단계와 다른 목적지로 판정되거나 새 Interview가 생성되는 경우는 0건이다. 이번 기능에서는
  진행 중 상태만 실제 화면 이동까지 제공한다.
- **SC-005**: 미인증 사용자, 다른 사용자 소유 Reading, 미완독 Reading을 사용한 모든 접근
  인수 사례에서 허용되지 않은 Interview 생성 또는 정보 노출은 0건이다.
- **SC-006**: 시작 실패와 유효하지 않은 연결을 포함한 모든 인수 사례에서 부분 Interview,
  잘못 확정된 Reading·Book 또는 변경된 Credit은 0건이다.
- **SC-007**: 확인 화면의 Desktop 및 Mobile Web 접근성 검증에서 책 정보, 변경 불가 안내,
  시작·재선택 행동과 오류를 키보드 및 보조 기술로 식별하고 실행하는 핵심 과업 성공률이
  100%이다.
- **SC-008**: 저장된 Turn 순서 및 질문·답변 보존 인수 사례에서 누락, 순서 충돌과 다른
  Interview의 Turn 혼입은 각각 0건이다.

## 가정

- Bundle 04A의 Reading 흐름이 완료되어 사용자는 본인 소유 Reading의 완독 여부와 완독일을
  확인할 수 있고, `AI 독서노트 만들기` 진입점이 제공되어 있다.
- Bundle 05A는 Book별 `READY` 또는 `READY_LIMITED` 준비 수준을 제공한다. Core MVP에서는
  자동 준비 작업과 `FAILED` 상태를 시작 흐름에서 다루지 않는다.
- 한 Reading은 전체 수명 동안 하나의 Interview만 가진다. 완료된 Interview는 재시작 대상이
  아니며, 향후 허용되는 진행 중 Interview 재시작은 새 Interview를 만들지 않고 기존
  Interview를 재사용한다. 구체적인 재시작 절차는 후속 범위에서 다룬다.
- Interview는 생성 직후 진행 중 상태가 되지만, 첫 질문은 Bundle 06A에서 생성된다. 따라서
  시작 직후 Turn이 아직 없어도 유효한 Interview다.
- 이번 Bundle은 기존 Interview의 상태에 맞는 후속 흐름을 식별하지만, Reflection 생성·확인
  및 완성된 Reflection 화면 자체는 해당 후속 Bundle의 책임으로 유지한다.
- 사용자의 95% 이상이 30초 이내에 책 확인과 시작 또는 재선택을 완료하는지는 별도 사용성
  평가 환경이 마련된 뒤 측정하며 이번 기능의 완료 게이트로 사용하지 않는다.
- Turn의 답변은 질문보다 나중에 채워질 수 있으며, 답변 저장·수정 규칙은 Bundle 06A 이후에
  구체화한다.
- Core MVP는 무료 검증 흐름이므로 Full MVP 문서의 Interview 시작 시 Credit 예약 계약을
  의도적으로 적용하지 않는다.
- 동일한 책의 판본 정정은 제품 정책상 예외가 될 수 있으나 Work/Edition 분리와 운영 절차가
  확정되지 않았으므로 이번 Bundle에서는 수행하지 않는다.
