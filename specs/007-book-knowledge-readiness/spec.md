# 기능 사양: 최소 Book Knowledge 및 준비 상태 판정

**기능 브랜치**: `feature/day-05-minimal-book-knowledge-interview-preparation`

**생성일**: 2026-09-08

**상태**: 초안

**입력**: 사용자 설명: "Bundle 05A — 최소 Book Knowledge 작업에 대한 명세"

## Clarifications

### Session 2026-09-08

- Q: 동일한 Book Knowledge Claim을 판별하는 기준은 무엇이어야 합니까? → A: 같은 Book + 같은 유형 + 같은 내용이면 중복
- Q: 수동 Seed Knowledge를 불러오는 도중 일부 Book이나 Claim이 실패하면 기존 성공분을 어떻게 처리해야 합니까? → A: 하나라도 실패하면 Seed 전체를 적용하지 않음
- Q: 수동 Seed Knowledge를 불러올 때 대상 Book이 아직 존재하지 않으면 어떻게 해야 합니까? → A: 대상 Book이 모두 있어야 하며 하나라도 없으면 전체 실패

## 사용자 시나리오 및 테스트 *(필수)*

### 사용자 스토리 1 - 책별 Claim Knowledge 준비 (우선순위: P1)

콘텐츠 준비 담당자는 검증 대상 Book에 대해 책의 Theme, Argument, Concept, Character,
Event 등 Interview 질문의 근거가 되는 최소 Claim을 등록하고, 해당 Book의 Knowledge로
다시 조회할 수 있다.

**우선순위가 높은 이유**: Claim 단위 Knowledge는 Interview가 책 내용을 근거 없이
추측하지 않으면서 구체적인 질문을 만들기 위한 최소 기반이다.

**독립 테스트**: 기존 Book 한 권에 서로 다른 유형의 Claim을 등록한 뒤 그 Book의
Knowledge를 조회하여, 등록한 Claim이 다른 Book의 Claim과 섞이지 않고 모두 반환되는지
확인한다.

**인수 시나리오**:

1. **Given** 등록된 Book과 유효한 Claim 정보가 있고, **When** 콘텐츠 준비 담당자가 해당
   Claim을 Book Knowledge로 등록하면, **Then** Claim은 지정한 Book에 연결되어 보존된다.
2. **Given** 한 Book에 여러 유형의 Claim이 등록되어 있고, **When** 해당 Book의 Knowledge를
   조회하면, **Then** 각 Claim의 유형과 내용이 누락 없이 반환된다.
3. **Given** 두 Book에 서로 다른 Claim이 등록되어 있고, **When** 한 Book의 Knowledge를
   조회하면, **Then** 다른 Book의 Claim은 결과에 포함되지 않는다.
4. **Given** 한 Book에 특정 유형과 내용의 Claim이 이미 있고, **When** 같은 Book에 같은
   유형과 내용의 Claim을 다시 등록하면, **Then** 별도의 중복 Claim이 생성되지 않는다.

---

### 사용자 스토리 2 - 검증용 Seed Knowledge 재현 (우선순위: P1)

제품 검증 담당자는 유명 도서 2~3권의 수동 Seed Knowledge를 일관되게 불러와, 이후
Interview Context와 질문 품질 검증에 사용할 수 있다.

**우선순위가 높은 이유**: 자동 Knowledge Research를 뒤로 미룬 Core MVP에서 실제 책을
사용한 Interview 검증을 반복하려면 작고 재현 가능한 기준 데이터가 필요하다.

**독립 테스트**: 비어 있는 검증 환경에 Seed를 불러온 뒤 대상 도서 수, 각 도서의 Claim,
책과 Claim의 연결을 확인하고, 같은 Seed를 다시 불러와도 중복 Claim이 생기지 않는지
확인한다.

**인수 시나리오**:

1. **Given** Seed 대상 Book을 식별할 수 있는 검증 환경이고, **When** 수동 Seed를 불러오면,
   **Then** 2~3권의 대상 Book마다 하나 이상의 유효한 Claim이 준비된다.
2. **Given** Seed를 한 번 불러온 환경이고, **When** 같은 Seed를 다시 불러오면, **Then**
   동일한 책과 Claim이 중복 생성되지 않고 결과가 동일하게 유지된다.
3. **Given** Seed 로드가 완료되었고, **When** 대상 Book의 Interview Context용 Knowledge를
   요청하면, **Then** 해당 Book에 속한 Seed Claim을 사용할 수 있다.
4. **Given** Seed의 Book 또는 Claim 중 하나라도 유효하지 않고, **When** 수동 Seed를
   불러오면, **Then** Seed에 포함된 Book Knowledge는 하나도 새로 적용되지 않고 실패
   대상을 확인할 수 있다.
5. **Given** Seed 대상 Book 중 하나라도 존재하지 않고, **When** 수동 Seed를 불러오면,
   **Then** 누락된 Book을 새로 생성하지 않고 Seed 전체를 적용하지 않는다.
6. **Given** 공식 출처와 대조·승인되지 않은 Claim이 있고, **When** Seed 적용을 준비하면,
   **Then** 해당 Claim을 공용 Book Knowledge로 적용하지 않고 미승인 항목을 확인할 수 있다.

---

### 사용자 스토리 3 - Book 준비 상태 구분 (우선순위: P1)

Interview 시작 흐름은 선택한 Book에 사용할 수 있는 Seed Knowledge가 있는지에 따라
`READY` 또는 `READY_LIMITED` 상태를 받아, 이후 질문 정책을 안전하게 선택할 수 있다.

**우선순위가 높은 이유**: Knowledge가 없는 책을 알고 있는 것처럼 다루지 않으면서도
사용자를 영구적으로 막지 않는 것이 AfterMuse의 핵심 신뢰 원칙이다.

**독립 테스트**: 유효한 Claim이 있는 Book과 없는 Book의 준비 상태를 각각 확인하여
전자는 `READY`, 후자는 `READY_LIMITED`로 판정되는지 검증한다.

**인수 시나리오**:

1. **Given** 한 개 이상의 유효한 Seed Claim이 연결된 Book이고, **When** 준비 상태를
   확인하면, **Then** `READY`로 판정된다.
2. **Given** 유효한 Seed Claim이 없는 Book이고, **When** 준비 상태를 확인하면, **Then**
   `READY_LIMITED`로 판정된다.
3. **Given** `READY_LIMITED`인 Book이고, **When** 후속 Interview 시작 가능 여부를
   판단하면, **Then** Knowledge 부족만으로 시작이 영구 차단되지 않고 사용자 기억 중심
   질문 정책을 선택할 수 있다.
4. **Given** Book A의 Claim만 존재하고 Book B에는 Claim이 없으며, **When** 두 Book의
   준비 상태를 각각 확인하면, **Then** Book A는 `READY`, Book B는 `READY_LIMITED`로 서로
   독립적으로 판정된다.

### 예외 상황

- 존재하지 않거나 식별할 수 없는 Book에는 Claim을 연결하지 않으며 부분적인 Knowledge를
  남기지 않는다.
- Claim 유형이 허용된 분류가 아니거나 내용이 비어 있으면 유효한 Knowledge로 등록하거나
  준비 상태 판정에 사용하지 않는다.
- 한 Book에 여러 Claim이 있어도 준비 상태는 하나의 Book 단위 결과로 반환된다.
- Seed 대상 Book이 환경에 하나라도 없을 때는 누락된 Book을 새로 만들거나 다른 Book을
  추측해 연결하지 않고, 어떤 대상이 준비되지 않았는지 확인 가능한 전체 실패 결과를
  제공한다.
- Seed 로드 중 하나의 Book 또는 Claim이라도 실패하면 해당 Seed 실행에서 추가하려던
  Knowledge 전체를 적용하지 않으며, 재시도 시 중복 없이 일관된 결과로 복구할 수 있어야
  한다.
- Knowledge가 없는 Book은 오류 상태로 간주하거나 Interview를 영구 차단하지 않고
  `READY_LIMITED`로 판정한다.
- 사용자 Reading, ReadingEntry 또는 Reflection의 내용은 이번 기능에서 공용 Book
  Knowledge로 승격하지 않는다.

## 요구사항 *(필수)*

### 기능 요구사항

- **FR-001**: 시스템은 Book Knowledge를 하나의 큰 문서가 아니라 특정 Book에 속한 개별
  Claim 단위로 관리해야 한다.
- **FR-002**: 각 Claim은 대상 Book, Knowledge 유형, 내용을 식별할 수 있어야 한다.
- **FR-003**: 시스템은 최소 Knowledge 유형으로 Theme, Argument, Concept, Character,
  Event를 구분할 수 있어야 한다.
- **FR-004**: 시스템은 특정 Book에 연결된 유효한 Claim 목록을 다른 Book의 Claim과 섞지
  않고 조회할 수 있어야 한다.
- **FR-005**: 시스템은 존재하지 않는 Book, 허용되지 않은 Knowledge 유형 또는 비어 있는
  내용의 Claim을 유효한 Book Knowledge로 받아들여서는 안 된다.
- **FR-005A**: 시스템은 Claim 내용의 앞뒤 공백을 제거한 값을 기준으로 같은 Book에
  Knowledge 유형과 내용이 모두 같은 Claim을 두 개 이상 등록해서는 안 된다. 내부 공백과
  대소문자는 변경하지 않으며, Book, Knowledge 유형 또는 정규화된 내용 중 하나라도 다르면
  서로 다른 Claim으로 취급해야 한다.
- **FR-006**: 시스템은 검증용 유명 도서 2~3권에 대한 수동 Seed Knowledge를 재현 가능하게
  제공해야 한다.
- **FR-006A**: 각 Seed Claim은 적용 전에 공식 출처 URL과 의미를 대조하고, 출처가 Claim을
  뒷받침한다는 수동 승인 기록이 있어야 한다. 승인되지 않은 Claim은 공용 Book Knowledge로
  적용해서는 안 된다.
- **FR-007**: 각 Seed 대상 Book에는 Interview Context에서 사용할 수 있는 유효한 Claim이
  하나 이상 포함되어야 한다.
- **FR-008**: 동일한 Seed를 반복해서 불러와도 같은 Book 또는 Claim의 중복이 증가하지
  않아야 하며, 같은 Knowledge 결과를 제공해야 한다.
- **FR-009**: Seed 대상 Book을 안전하게 식별할 수 없으면 임의의 Book에 Knowledge를
  연결해서는 안 되며, 실패 대상을 확인할 수 있어야 한다.
- **FR-009B**: 모든 Seed 대상 Book은 Seed 실행 전에 존재해야 한다. 대상 Book이 하나라도
  없으면 시스템은 Book을 생성하지 않고 Seed 전체를 실패시켜야 한다.
- **FR-009A**: Seed의 Book 또는 Claim 중 하나라도 유효하지 않으면 해당 Seed 실행의
  변경 전체를 적용해서는 안 되며, 실행 전 상태를 유지해야 한다.
- **FR-010**: 시스템은 Book에 유효한 Claim이 하나 이상 있으면 해당 Book의 준비 상태를
  `READY`로 판정해야 한다.
- **FR-011**: 시스템은 Book에 유효한 Claim이 없으면 해당 Book의 준비 상태를
  `READY_LIMITED`로 판정해야 한다.
- **FR-012**: 준비 상태는 Book별로 독립적으로 판정되어야 하며 다른 Book의 Knowledge가
  판정에 영향을 주어서는 안 된다.
- **FR-013**: `READY_LIMITED`는 Knowledge가 부족함을 나타내되 후속 Interview 시작을
  영구적으로 차단해서는 안 되며, 사용자 기억과 답변 중심의 질문 정책을 선택할 수 있는
  신호를 제공해야 한다.
- **FR-014**: 이번 기능은 자동 Book Knowledge Research, 외부 자료 수집, Knowledge
  Candidate 승인, Source/Evidence/Conflict 운영, Claim 수정 이력 및 자동 보강을 수행하지
  않아야 한다.
- **FR-015**: 이번 기능은 Interview 생성·진행, 질문 생성, Reading 준비 화면, 사용자 안내
  UI 또는 Credit 처리를 포함하지 않아야 한다.
- **FR-016**: 이번 기능은 사용자 Reading, ReadingEntry, Interview 답변 또는 Reflection의
  내용을 검증 없이 공용 Book Knowledge로 저장해서는 안 된다.

### 핵심 엔터티 *(기능에 데이터가 포함되는 경우 작성)*

- **Book**: Book Knowledge가 설명하는 출판 도서이다. 각 Book의 Knowledge와 준비 상태는
  다른 Book과 독립적으로 관리된다.
- **Book Knowledge Claim**: 한 Book에 관한 개별 지식 진술이다. 대상 Book, Theme·Argument·
  Concept·Character·Event 중 하나인 Knowledge 유형, 비어 있지 않은 내용을 가진다. 같은
  Book 안에서 Knowledge 유형과 내용이 모두 같은 Claim은 하나만 존재한다.
- **Seed Knowledge Set**: Core MVP의 Interview 품질 검증을 위해 선정한 유명 도서 2~3권과
  각 도서의 수동 Claim 모음이다. 반복해서 불러와도 동일한 결과를 제공한다.
- **Book 준비 상태**: 후속 Interview가 사용할 Knowledge 수준을 나타내는 Book 단위
  결과이다. 유효한 Claim이 있으면 `READY`, 없으면 `READY_LIMITED`이다.

## 성공 기준 *(필수)*

### 측정 가능한 결과

- **SC-001**: Claim 등록 및 Book별 조회 인수 시나리오에서 등록한 유효한 Claim의 조회율이
  100%이고 다른 Book의 Claim 혼입은 0건이다.
- **SC-002**: 비어 있는 검증 환경에서 Seed를 불러올 때 2~3권의 대상 Book 모두에 하나
  이상의 유효한 Claim이 준비되며 누락된 대상 Book은 0권이다.
- **SC-002A**: 적용되는 Seed Claim의 공식 출처 대조 및 승인 기록 보유율은 100%이고,
  미승인 Claim의 적용 건수는 0건이다.
- **SC-003**: 동일한 Seed를 연속 3회 불러온 뒤에도 Book별 Claim 수와 내용이 첫 로드 결과와
  100% 동일하고 중복 Claim 증가는 0건이다.
- **SC-003A**: 유효하지 않은 Book 또는 Claim을 포함한 Seed 로드 인수 사례에서 새로
  적용된 부분 데이터는 0건이고 실행 전 Knowledge 상태 보존율은 100%이다.
- **SC-004**: 유효한 Claim이 있는 Book과 없는 Book을 포함한 준비 상태 판정 인수 사례에서
  `READY`와 `READY_LIMITED` 판정 정확도가 100%이다.
- **SC-005**: Knowledge가 없는 모든 인수 사례에서 `READY_LIMITED`가 반환되고 Knowledge
  부족만으로 후속 Interview가 영구 차단되는 사례는 0건이다.
- **SC-006**: 유효하지 않은 Claim과 식별 불가능한 Seed 대상 Book을 사용한 모든 인수
  사례에서 잘못 연결되거나 준비 상태 판정에 포함된 Knowledge는 0건이다.
- **SC-007**: Seed 대상 모든 Book의 Knowledge가 Interview Context용 조회에서 누락 없이
  제공되어, 후속 Interview 기능의 검증 입력으로 100% 사용할 수 있다.

## 가정

- IMP-020의 Book 기본 도메인과 Day 03의 도서 선택·로컬 Book 등록 흐름이 완료되어 있으며,
  이번 기능은 Seed 실행 전에 등록된 기존 Book만 Knowledge의 대상으로 사용한다. Seed는
  누락된 Book을 생성하지 않는다.
- Core MVP의 수동 Seed 대상은 제품 검증에 사용할 유명 도서 2~3권이며, 정확한 도서와 Claim
  문구는 계획 단계에서 저작권과 검증 용이성을 고려해 선택한다.
- 이번 최소 판정에서 "유효한 Claim이 있음"은 대상 Book에 연결되고, 허용된 유형과 비어
  있지 않은 내용을 가진 Claim이 하나 이상 존재함을 뜻한다. Claim 수나 유형별 최소 개수,
  신뢰도 점수는 요구하지 않는다.
- `READY`는 Book-grounded 질문에 사용할 최소 Seed가 있음을 뜻하고, `READY_LIMITED`는
  책 내용을 안다고 전제하지 않는 사용자 기억 중심 Interview가 필요함을 뜻한다.
- Core MVP에서는 자동 준비 절차가 없으므로 Knowledge 부재 자체에 `FAILED` 상태를 사용하지
  않는다. 실제 준비 작업의 실행 실패 상태는 자동 Research 도입 시 후속 범위에서 다룬다.
- Book Knowledge는 사용자 개인 기록이 아니라 공용 Book 단위 데이터로 취급한다. 사용자
  기록에서 발견된 내용을 Candidate 검증 없이 공용 Knowledge로 승격하는 흐름은 후속 범위다.
- Source/Evidence 연결은 제품 전체 방향에는 포함되지만 Bundle 05A에서는 최소 Claim 저장과
  상태 판정을 우선하기 위해 제외한다.
