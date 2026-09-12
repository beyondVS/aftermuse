# 기능 사양: Interview Coverage 상태

**기능 브랜치**: `codex/day-07-adaptive-interview-loop`

**생성일**: 2026-09-10

**상태**: 초안

**입력**: 사용자 설명: "AfterMuse MVP Implementation Plan v5의 Bundle 07A — Coverage 상태 구현을 위한 명세"

## 사용자 시나리오 및 테스트 *(필수)*

### 사용자 스토리 1 - 답변으로 생각의 Coverage를 축적하기 (우선순위: P1)

인터뷰에서 답변을 남긴 사용자는 자신의 생각이 기억, 반응, 연결, 여운의 네 방향 중
어디까지 드러났는지 인터뷰별 상태로 축적할 수 있다. 이 상태는 이후 질문이 이미 충분히
다룬 내용을 반복하지 않고 아직 드러나지 않은 생각을 찾는 기준이 된다.

**우선순위가 높은 이유**: Coverage는 고정 설문지가 아닌 적응형 Interview를 가능하게 하는
핵심 상태다. 답변과 분리된 신뢰 가능한 상태가 없으면 다음 질문과 종료 판단이 사용자 생각을
일관되게 따라갈 수 없다.

**독립 테스트**: 답변이 확정된 진행 중 Interview에서 네 Core Coverage 축의 일부 또는 전체에
유효한 상태 변경을 적용하고, 해당 Interview를 다시 조회했을 때 변경된 축과 변경되지 않은 축이
정확히 보존되는지 확인한다.

**인수 시나리오**:

1. **Given** 답변이 확정되고 네 Core Coverage 축이 모두 `UNCOVERED`인 진행 중 Interview이고,
   **When** 유효한 Coverage 변경이 처음 적용되면, **Then** 시스템은 지정된 축을 요청된 상태로
   변경하고 나머지 축은 `UNCOVERED`로 보존한다.
2. **Given** 일부 축이 `PARTIAL` 또는 `COVERED`인 Interview이고, **When** 다른 축에 유효한
   변경이 적용되면, **Then** 시스템은 지정된 축만 변경하고 기존 축의 상태를 그대로 유지한다.
3. **Given** Coverage가 저장된 Interview이고, **When** 같은 Interview를 다시 조회하면,
   **Then** 네 축과 각 상태가 마지막으로 확정된 값과 일치한다.

---

### 사용자 스토리 2 - 유효한 Coverage 전환만 허용하기 (우선순위: P1)

사용자는 후속 분석이나 반복 요청에 오류가 있더라도 이미 축적된 Coverage가 유실되거나 더 낮은
상태로 되돌아가지 않는 일관된 인터뷰를 경험한다.

**우선순위가 높은 이유**: Coverage는 이후 질문 선택과 종료 정책의 근거가 되므로 잘못된 축,
상태 하락 또는 부분 실패가 저장되면 전체 Interview 흐름의 판단을 왜곡한다.

**독립 테스트**: 유효한 상태 상승, 같은 상태의 반복 적용, 상태 하락, 알 수 없는 축·상태와
여러 축을 포함한 실패 요청을 각각 적용하여 허용된 변경만 전체 단위로 보존되는지 확인한다.

**인수 시나리오**:

1. **Given** 특정 축이 `UNCOVERED` 또는 `PARTIAL`인 Interview이고, **When** 그보다 높은
   상태가 적용되면, **Then** 해당 축은 `UNCOVERED` → `PARTIAL` → `COVERED` 순서 안에서
   앞으로만 이동한다.
2. **Given** 특정 축에 현재와 같은 상태가 저장되어 있고, **When** 같은 변경이 반복되면,
   **Then** 시스템은 중복 Coverage를 만들거나 다른 축을 바꾸지 않고 동일한 결과를 반환한다.
3. **Given** 하나 이상의 기존 Coverage가 있는 Interview이고, **When** 상태 하락, 알 수 없는
   축 또는 알 수 없는 상태가 포함된 변경이 적용되면, **Then** 전체 변경을 거부하고 기존
   Coverage를 모두 유지한다.
4. **Given** 여러 축을 한 번에 변경하려는 요청이고, **When** 그중 하나라도 유효하지 않으면,
   **Then** 유효한 축만 부분 반영하지 않고 요청 전 상태를 유지한다.

---

### 사용자 스토리 3 - Interview 경계 안에서 Coverage를 격리하기 (우선순위: P2)

사용자의 Coverage는 해당 사용자의 해당 Interview에만 속하며, 다른 사용자나 다른 독서 경험의
Coverage와 섞이지 않는다.

**우선순위가 높은 이유**: Coverage에는 사용자의 비공개 독서 반응이 요약되므로 소유권 경계를
벗어난 조회나 변경은 개인정보와 다음 질문의 정확성을 함께 훼손한다.

**독립 테스트**: 같은 사용자와 다른 사용자의 여러 Interview에 서로 다른 Coverage를 저장한 뒤,
각 Interview의 조회·변경 결과가 독립적이며 권한 없는 요청이 아무 상태도 노출하거나 변경하지
않는지 확인한다.

**인수 시나리오**:

1. **Given** 서로 다른 Reading에 연결된 두 Interview가 있고, **When** 한 Interview의
   Coverage를 변경하면, **Then** 다른 Interview의 Coverage는 변하지 않는다.
2. **Given** 다른 사용자가 소유한 Interview이고, **When** 사용자가 그 Coverage를 조회하거나
   변경하려 하면, **Then** 시스템은 Coverage와 대상 존재 여부를 노출하지 않고 아무 상태도
   변경하지 않는다.
3. **Given** 진행 중이 아니거나 Reading·Book 연결이 손상된 Interview이고, **When** Coverage
   변경이 요청되면, **Then** 시스템은 요청을 거부하고 기존 Coverage를 유지한다.
4. **Given** 사용자가 소유하고 Reading·Book 연결이 유효한 완료 단계의 Interview이고,
   **When** 사용자가 Coverage를 조회하면, **Then** 시스템은 저장된 snapshot을 보여주되 변경은
   허용하지 않는다.

### 예외 상황

- Coverage 변경 대상 Interview에 아직 확정된 답변이 없으면 상태를 만들거나 변경하지 않는다.
- 한 변경 요청에 같은 축이 여러 번 포함되면 모호한 결과를 선택하지 않고 전체 요청을 거부한다.
- 빈 변경은 성공한 상태 변경으로 기록하지 않으며 기존 Coverage를 그대로 반환할 수 있다.
- Coverage 저장 중 오류가 발생하면 일부 축만 반영하지 않고 요청 전 상태를 유지한다.
- 이미 저장된 Coverage에 현재 지원하지 않는 축이나 상태가 발견되면 임의로 고치거나 무시하지
  않고 변경을 중단한다.
- 반복 또는 동시에 도착한 상태 변경은 유효한 최고 상태로 수렴해야 하며 이미 확정된 상위 상태를
  하위 상태로 덮어쓰지 않는다.

## 요구사항 *(필수)*

### 기능 요구사항

- **FR-001**: 시스템은 각 Interview에 `MEMORY`, `REACTION`, `CONNECTION`, `AFTERTHOUGHT`의
  네 Core Coverage 축을 구분해 보존해야 한다.
- **FR-002**: 각 Core Coverage 축은 `UNCOVERED`, `PARTIAL`, `COVERED` 중 하나의 상태를
  가져야 한다.
- **FR-003**: Coverage가 처음 확정될 때 변경 대상으로 지정되지 않은 Core Coverage 축은
  `UNCOVERED`로 취급되고 이후에도 명시적으로 조회 가능해야 한다.
- **FR-004**: Coverage 변경은 답변이 하나 이상 확정된 진행 중 Interview에만 적용해야 한다.
- **FR-005**: 시스템은 하나의 변경에서 한 개 이상의 Core Coverage 축을 지정할 수 있어야 하며,
  지정되지 않은 축의 기존 상태를 변경해서는 안 된다.
- **FR-006**: 각 축은 `UNCOVERED` → `PARTIAL` → `COVERED` 방향으로만 전환할 수 있고,
  현재보다 낮은 상태로 되돌아가서는 안 된다.
- **FR-007**: 현재와 동일한 상태를 반복 적용하면 중복 기록이나 추가 상태 변경 없이 같은
  Coverage 결과를 반환해야 한다.
- **FR-008**: 시스템은 알 수 없는 축, 알 수 없는 상태, 같은 축의 중복 지정 또는 상태 하락이
  포함된 변경 요청 전체를 거부해야 한다.
- **FR-009**: 여러 축의 변경은 하나의 단위로 확정되어야 하며, 어느 한 축이라도 유효하지 않거나
  저장에 실패하면 어떤 축도 부분 반영해서는 안 된다.
- **FR-010**: 동시에 처리된 유효한 변경은 각 축의 가장 높은 유효 상태로 수렴해야 하며 이미
  확정된 상태를 유실하거나 하락시켜서는 안 된다.
- **FR-011**: Coverage는 해당 Interview에만 속해야 하며 다른 Reading 또는 Interview의 상태와
  공유되거나 합쳐져서는 안 된다.
- **FR-012**: 시스템은 현재 사용자가 소유하고 Reading·Book 연결이 유효한 Interview의 Coverage를
  진행 상태와 관계없이 조회할 수 있게 해야 한다. 다른 사용자의 Coverage와 대상 존재 여부는
  노출해서는 안 된다.
- **FR-013**: 진행 중이 아니거나 확정된 Book과 Reading의 연결이 유효하지 않은 Interview에는
  Coverage 변경을 적용해서는 안 된다.
- **FR-014**: Coverage 상태는 Interview 진행 상태와 독립적으로 관리해야 하며 Coverage 변경만으로
  Interview를 종료 준비 또는 완료 상태로 전환해서는 안 된다.
- **FR-015**: 이번 기능은 답변의 의미를 판정하거나 Coverage 변경안을 생성하지 않아야 한다.
  검증할 변경안이 제공되었을 때 상태를 안전하게 적용하는 범위만 담당한다.
- **FR-016**: 이번 기능은 Focus Coverage 추가, 다음 질문 생성, 질문 Budget, Soft Stop,
  Low-information 판단, Reflection 생성, Credit 또는 Book Knowledge 변경을 수행해서는 안 된다.

### 핵심 엔터티 *(기능에 데이터가 포함되는 경우 작성)*

- **Interview Coverage**: 한 Interview에서 사용자의 생각이 어떤 방향까지 드러났는지를 나타내는
  영속 상태다. Interview에 종속되며 네 Core Coverage 축별 현재 상태를 보존한다.
- **Core Coverage 축**: 대부분의 Reflection에 필요한 생각의 방향이다. 기억에 남은 내용
  (`MEMORY`), 반응·평가(`REACTION`), 자신의 경험·생각과의 연결(`CONNECTION`), 읽은 뒤 남은
  생각·변화·여운(`AFTERTHOUGHT`)으로 구성된다.
- **Coverage 상태**: 한 축이 아직 드러나지 않은 `UNCOVERED`, 일부 드러난 `PARTIAL`,
  Reflection 근거로 충분히 드러난 `COVERED` 중 어디에 있는지를 나타낸다.
- **Coverage 변경**: 하나 이상의 축에 적용할 목표 상태 묶음이다. 전부 유효할 때만 하나의
  단위로 확정되며 자체적으로 답변을 분석하거나 Interview 진행 상태를 바꾸지 않는다.

## 성공 기준 *(필수)*

### 측정 가능한 결과

- **SC-001**: 네 Core Coverage 축 각각에 대해 `UNCOVERED`, `PARTIAL`, `COVERED` 상태를
  저장하고 다시 조회하는 대표 검증 사례의 100%에서 마지막으로 확정된 상태가 일치한다.
- **SC-002**: 유효한 단일·다중 축 상태 상승과 동일 상태 반복 적용 사례의 100%에서 지정된 축만
  기대한 상태로 바뀌고 중복 Coverage가 생성되지 않는다.
- **SC-003**: 상태 하락, 알 수 없는 축·상태, 중복 축 및 일부 저장 실패 사례의 100%에서
  변경 전 Coverage 전체가 그대로 유지된다.
- **SC-004**: 같은 Interview에 동시에 적용되는 대표 변경 사례의 100%에서 각 축은 유효한 최고
  상태로 수렴하며 확정된 상위 상태가 하락하거나 유실되지 않는다.
- **SC-005**: 서로 다른 사용자와 Interview를 사용한 격리 검증 사례의 100%에서 한 Interview의
  변경이 다른 Interview에 영향을 주지 않고 권한 없는 사용자는 Coverage나 대상 존재 여부를
  확인할 수 없다.
- **SC-006**: Coverage 변경 검증 사례의 100%에서 Interview 진행 상태, 답변 원문, Turn 순서,
  다음 질문, Reflection, Credit과 Book Knowledge는 변경되지 않는다.

## 가정

- Bundle 06A에서 사용자 소유의 진행 중 Interview와 하나 이상의 확정된 답변이 이미 존재한다.
- Bundle 07A는 Core Coverage의 영속 상태와 안전한 변경 경계만 제공하며, 답변에서 변경안을
  도출하는 Answer Analysis는 Bundle 07B가 담당한다.
- Core MVP에서는 이해 가능한 세 단계 상태만 사용하고 수치 점수나 가중치를 도입하지 않는다.
- Focus Coverage는 답변 분석 및 다음 질문 정책과 함께 후속 Bundle에서 다루며 이번 상태 구조에
  미리 포함하지 않는다.
- Coverage가 Reflection을 만들기에 충분한지 판단하는 기준과 Interview 종료 선택은 Bundle 08A의
  종료 정책에서 다룬다.
- 이번 기능은 사용자에게 별도의 Coverage 편집 화면을 제공하지 않는다. Coverage는 이후 적응형
  질문 흐름을 위한 내부 진행 상태이며, 사용자에게 진행감을 표시하는 UI는 후속 범위다.
