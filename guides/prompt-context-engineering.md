# Prompt, Context, and Agent Engineering Guide

## Purpose

이 문서는 AI 에이전트에게 줄 규칙, 프롬프트, Task Contract, 실행 하네스를 설계·검토하는 사람이 선택적으로 참고하는 범용 가이드다.
특정 도구, 모델, 조직의 작업 방식에 종속되지 않는다.
설명과 예시는 판단을 돕기 위한 것이며, 현재 작업에 자동 적용되는 규칙이 아니다.

좋은 설계의 목표는 에이전트가 충분한 근거와 적절한 권한 안에서 결과를 만들고, 성공·실패·추가 판단 필요 상태를 외부에서 확인할 수 있게 하는 것이다.

## Prompt, Context, and Agent Engineering

세 영역은 분리된 기법이라기보다 하나의 작업 흐름을 이루는 관점이다.

| 영역 | 핵심 질문 | 설계 대상 |
| --- | --- | --- |
| Prompt engineering | 에이전트가 무엇을 해야 하는가? | 목표, 결과 형태, 요구사항, 판단 기준 |
| Context engineering | 올바르게 판단하려면 무엇을 알아야 하는가? | 관련성 있고 권위 있으며 최신인 정보 |
| Agent engineering | 성공과 실패를 어떻게 관찰·통제하는가? | scope, 권한, acceptance, validation, escalation |

```text
Context
  ↓
Prompt / Task Contract
  ↓
Decision rules
  ↓
Authority and constraints
  ↓
Verification
  ↓
Terminal state
```

프롬프트가 원하는 결과를 분명히 해도 필요한 context가 빠지면 판단이 흔들린다.
context와 지시가 충분해도 권한·검증 경계가 없으면 작업이 과도하게 확대되거나 검증되지 않은 완료로 끝날 수 있다.

## Core Design Principles

### Define the desired result before restrictions

금지 목록을 늘리기 전에 원하는 결과의 구조를 정의한다. 특히 출력 형태가 문제라면 다음 순서가 유용하다.

```text
Desired result → Required structure → Constraints → Prohibitions
```

제한은 중요한 안전 경계를 보호하지만, 원하는 산출물의 모양을 대신 설명하지는 못한다.

### Choose a format that preserves relationships

표현 형식은 독자가 비교 기준, 조건과 동작의 관계, 적용 순서를 정확히 파악할 수 있도록 선택한다.
동일한 기준의 비교나 조건과 동작의 대응에는 표가 도움이 될 수 있다. 표 사용 자체가 목적이나 의무는 아니다.
형식을 바꾸더라도 조건·예외·우선순위·문장 강도와 항목 간 관계를 보존한다.
표만 읽으면 의미가 달라지는 조건이나 예외는 해당 내용과 함께 제시한다.

### Prefer observable conditions

`필요하면`, `적절히`, `상황에 따라`, `충분히`, `합리적으로`, `의미 있는`, `실질적으로`, `대규모`, `고위험`, `복잡한` 같은 단어가 언제나 잘못된 것은 아니다.
다만 문맥상 여러 합리적 해석이 가능하여 실행 결과가 달라질 때는 다음 구조로 바꿀 수 있다.

```text
기본 동작
+ 관찰 가능한 조건
+ 조건이 성립했을 때의 동작
```

근거 없는 수치 대리 지표로 모호성을 숨기지 않는다.

```text
Bad: 복잡한 작업이면 계획을 작성한다.

Better: 공개 API·schema·protocol 계약을 변경하거나,
되돌리기 어려운 선택 또는 결과를 바꾸는 미해결 대안이 있으면
실행 전에 목표·제약·검증 계획을 정렬한다.
```

### Make exceptions independent conditions

`A를 수행한다. 단, 필요하면 생략할 수 있다.`는 기본 동작을 협상 가능하게 만든다. 실제 예외가 있다면 독립적인 조건과 동작으로 표현한다.

```text
기본: A
조건 X가 확인되면: B
```

### Calibrate statement strength

문장의 강도가 오해될 수 있다면 Hard Rule, Default, Conditional Rule, Guideline의 차이를 드러낸다.
모든 문서에 이 레이블을 붙이는 것이 목적은 아니다.
반드시 지켜야 할 경계, 기본값, 관찰 가능한 조건의 분기, 참고 조언을 혼동하지 않게 하는 것이 목적이다.

### Define outcomes before implementation

공용 rule이나 prompt는 가능한 경우 구현 수단보다 원하는 결과를 먼저 정의한다.

```text
condition → desired outcome → implementation choice
```

예를 들어 `1:N 관계에는 항상 prefetch_related()를 사용한다`보다, 관계 접근이 반복 query를 만들면 프로젝트 ORM과 기존 패턴에 맞는 eager-loading으로 N+1을 제거하고 query 동작을 확인하라고 표현하는 편이 이식성과 의도를 보존한다.

### State precedence and fallback

기술 선택과 스타일 기본값은 가능한 경우 결정 순서를 갖는다.

```text
사용자 명시 지시
→ 프로젝트 설정
→ 기존 프로젝트의 일관된 관례
→ framework/language guide
→ template default
```

따라서 `line length는 80 또는 88` 대신 formatter 또는 linter 설정을 따르고, 설정과 관례가 없는 신규 프로젝트에서만 88을 기본값으로 둔다고 쓸 수 있다.

## Designing Rules and Conditions

규칙은 실제 실패를 관찰한 뒤 최소한으로 강화하는 편이 좋다.

```text
baseline → 실제 실패 또는 오해 관찰 → 그 실패를 막는 최소 규칙 추가 → 재검증
```

가상의 허점마다 금지 조항을 더하면 읽기 비용과 상충 가능성만 커질 수 있다.
같은 프롬프트를 여러 모델에서 사용하거나 반복 실행했을 때 서로 다른 합리적 해석이 반복된다면,
문구가 해석의 범위를 충분히 제한하지 못한다는 신호일 수 있다.

## Scope and Authority

### Syntactic scope and semantic scope

두 극단을 피한다. 한 위치만 고쳐 같은 근본 원인의 반복 문제를 남기는 일과, 한 문제를 이유로 저장소 전체 리팩터링으로 확대하는 일이다. 기본적으로 사용자가 지정한 scope를 보호한다.

다만 사용자가 특정 위치가 아니라 문제 유형을 고치도록 요청했고, 정의된 search scope 안에서 같은 근본 원인의 같은 유형 문제가 확인된다면 그 match를 함께 다루는 것이 의미적 scope에 맞을 수 있다.
사용자가 정확한 위치만 지시했다면 그 경계를 우선한다.

### Decisions and authority boundaries

`Decisions already made`는 이미 확정되어 다시 판단하면 안 되는 것을 기록한다. `Must not decide`는 현재 작업에서 에이전트에게 권한이 없는 선택을 기록한다.

```text
Decisions already made:
- 기존 API response schema 유지
- PostgreSQL 사용 유지

Must not decide:
- 새로운 API version 생성
- DB 교체
- 인증 정책 변경
```

이 구분은 더 나은 방법처럼 보이는 선택을 발견하더라도 scope나 architecture를 임의로 확대하지 않게 한다.

### Apply semantics patterns

적용 범위와 구현 재량은 별도의 판단 축이다.
`Apply`는 scope 모호성을 줄이기 위한 재사용 가능한 패턴이며, `Delegated authority`는 고정된 외부 계약 안에서 에이전트가 선택할 수 있는 구현 범위를 설명한다.
모든 Task Contract에 강제되는 표준은 아니다.

| 적용 범위 패턴 | 의미 |
| --- | --- |
| `Exact` | 지정한 target만 수정한다. |
| `All matches within scope` | 정의한 search scope에서 같은 rule에 해당하는 모든 match를 검사하고 처리한다. |

예를 들어 한 docstring만 바꾼다면 `Modify: foo.py::target_function`, `Apply: Exact`라고 쓸 수 있다.
package 안의 문서화 언어 정책 위반 docstring 전체를 다룬다면 Python source를 search scope로 정하고 `All matches within scope`를 사용할 수 있다.

적용 범위(`Apply`)와 위임된 구현 재량(`Delegated authority`)은 함께 지정할 수 있다.
예를 들어 `Apply: All matches within scope`와 `Delegated authority: 기존 패턴과 최소 구현 원칙 안에서 내부 구현 선택 가능`은 같은 문제의 모든 match를 처리하면서 각 위치의 구현 수단은 기존 코드에 맞게 고를 수 있음을 뜻한다.

### Completion sets for multi-output work

여러 파일, 문서, 산출물 또는 독립 요구사항이 하나의 작업에 포함될 때는 완료 대상을 하나의 **completion set**(완료 여부를 확인할 대상들의 집합)으로 관리한다.
이는 작성자가 이미 알고 있는 필수 대상을 일부 빠뜨리는 일과, 작업 중 발견되는 추가 영향을 놓치는 일을 함께 줄이기 위한 패턴이며 모든 작업에 강제되는 절차는 아니다.

초기 completion set에는 사용자 요구사항, 프로젝트 계약, 현재 context에서 이미 알려진 완료 대상(`Known targets`)을 명시한다.
사전에 모든 영향 대상을 알 수 없다면 파일 목록을 추측해서 고정하지 않는다.
대신 재현 가능한 탐색 범위(`search scope`)와 검색 결과의 관련성을 판정할 기준(`match rule`)을 정의해 추가 대상(`Discovered targets`)을 찾는다.
이처럼 정해진 범위 안에서 수행하는 탐색을 bounded search라고 하며, 새로 발견한 관련 대상은 completion set에 추가한다.

```text
Known targets
  + Discovered targets from bounded search
  → Final completion set
  → Resolve every item
  → Re-run discovery check when practical
```

completion set의 각 항목은 작업 완료 전에 수정함(`modified`) 또는 근거가 있는 수정하지 않음(`not modified`)으로 처리 결과를 확정한다.
이 문서에서 항목을 닫는다는 것은 이처럼 처리 결과를 확정한다는 뜻이다.
발견한 항목을 모두 처리했다는 사실만으로 discovery가 충분했다고 가정하지 않는다.
가능하면 수정 후 같은 search scope와 match rule, 또는 동등한 검색을 다시 수행해 의도하지 않은 잔여 match와 누락 가능성을 확인한다.

이 패턴은 두 층의 completeness를 구분한다.

- **Discovery completeness**: 정의한 탐색으로 관련 대상을 충분히 발견했는가?
- **Execution completeness**: 지정·발견한 각 대상을 모두 처리하거나 근거와 함께 처리하지 않기로 닫았는가?

`Exact`는 Known targets가 곧 completion set의 경계인 경우에 적합하다.
`All matches within scope`는 bounded search로 Discovered targets를 completion set에 추가하고 처리해야 하는 경우에 적합하다.
두 패턴 모두 completion set의 모든 항목을 닫아야 완료로 판단한다.

예를 들어 설명을 변경하는 작업은 다음처럼 표현할 수 있다. 이는 고정 문법이 아니라 개념을 보이는 예시다.

```text
Known targets:
- SKILL.md
- README.md

Search:
- 저장소 전체에서 변경되는 동작명, 옵션명 또는 기존 설명을 참조하는 위치

Completion:
- known targets와 검색으로 발견된 관련 대상 모두 처리
- 각 항목은 modified 또는 not modified: <reason>
- 재검색 결과 의도하지 않은 잔여 match 없음
```

## Context Selection

더 많은 context가 항상 더 좋은 것은 아니다.
좋은 context는 작업과 관련성이 있고, 권위 있는 출처에 근거하며, 최신이어야 한다.
보통 다음과 같이 점진적으로 구성한다.

```text
Global invariant
→ 현재 작업에 해당하는 conditional rules
→ 현재 Task Contract
→ validation evidence
```

작업과 무관한 framework rule, 오래된 결정, 모든 설계 guide를 항상 주입하지 않는다.
필요한 파일, 설정, 계약, 기존 관례만 선택하면 지시 충돌과 주의 분산을 줄일 수 있다.
이것이 Minimum Sufficient Context다.

## Completion and Verification

모델의 자기평가 대신 외부 증거를 사용한다.
여러 산출물이 있는 작업이라면 먼저 [completion set](#completion-sets-for-multi-output-work)으로 discovery와 execution의 완료 범위를 닫고,
Acceptance criteria는 무엇이 참이어야 하는지, Validation은 그것을 어떤 명령이나 관찰 가능한 검사로 확인하는지 각각 설명한다.

```text
Acceptance:
- 응답의 필수 필드와 HTTP 상태 코드 유지
- 변경한 endpoint의 정상·오류 동작 유지

Validation:
- pytest tests/api/test_orders.py -k create_order
- ruff check app/orders/
```

위 경로와 명령은 설명용이다.
실제 contract를 가장 직접적으로 확인하는 프로젝트의 테스트·검사 명령을 선택한다.
예를 들어 API response schema를 보존해야 한다면 해당 필드와 상태 코드를 검증하는 contract test가 acceptance의 증거가 된다.

검증을 실행하지 못했거나 실패했다면 성공했다고 주장하지 않는다. 그 상태와 제한 요인을 명확히 반환한다.

작업이 끝났거나 더 진행할 수 없을 때의 상태(terminal state)는 적어도 다음을 구분할 수 있으면 유용하다.
정확히 네 상태를 모든 시스템에 강제할 필요는 없다.

| 상태 | 의미 |
| --- | --- |
| Completed | Acceptance와 Validation을 만족했다. |
| Failed | 허용된 범위와 권한 안에서 작업·합리적인 복구를 마쳤지만 acceptance 또는 validation을 충족하지 못했다. |
| Needs Decision | architecture, public contract, product policy, compatibility, security처럼 위임되지 않은 판단이 실행을 막는다. |
| Needs External Action | push, deploy, credential, approval처럼 외부 권한 또는 side effect가 실행을 막는다. |

위임되지 않은 판단이나 외부 조치가 필요한 경우에는 `Failed`보다 각각 `Needs Decision`, `Needs External Action`을 반환한다.
이 구분은 애매한 상태를 알아서 결정하거나 검증 실패를 완료로 포장하는 일을 막는다.

반환 형식도 terminal state에 맞춰 최소한의 증거를 담으면 검토와 재개가 쉬워진다.

- `Completed`에는 수정 대상, 실행한 validation과 결과, 충족한 acceptance를 기록한다.
- `Failed`에는 실패한 검사, 시도한 범위, 남은 blocker와 현재 변경 상태를 기록한다.
- `Needs Decision`에는 미해결 판단과 그것이 위임 범위를 넘는 이유를 기록한다.
- `Needs External Action`에는 필요한 외부 작업과 그 전까지 완료한 로컬 작업을 기록한다.

형식은 작업 환경에 맞게 줄일 수 있다.

## Harness and Delegation ROI

planning, TDD, auditor, subagent, skill, 반복 review를 모든 작업에 일률적으로 추가할 필요는 없다. 다음 요소에 비례해 하네스 강도를 높인다.

- 비가역성 또는 rollback 난이도
- external side effect
- 보안·권한 경계
- 공개 계약과 데이터 무결성
- 미해결 trade-off
- 검증 난이도

단순하고 가역적이며 기계적으로 검증 가능한 작업에는 최소 충분한 하네스가 적합하다.
delegation도 독립적인 결과물, 명확한 authority, 확인 가능한 return state가 있을 때 특히 유용하다.
협업 조율 비용이 작업 자체보다 크면 직접 처리하거나 더 작은 작업 계약을 쓰는 편이 낫다.

## Task Contract Template

Task Contract는 복잡도·위험·모호성이 있는 작업에서 목표, scope, authority, 검증을 정렬하는 재사용 가능한 형식이다.
절차적 의무가 아니다.
단순한 작업에는 Goal, Scope, Acceptance, Validation만으로 충분할 수 있으며, contract 작성 비용이 직접 처리 비용보다 크다면 상세 형식은 과도한 하네스일 수 있다.

```text
TASK CONTRACT

Goal:
[완성해야 하는 단일한 결과]

Scope:
- Search:
- Modify:

Intent / Context:
[결과 판단에 필요한 경우에만]

Decisions already made:
- [이미 확정된 요구사항]
- [고정된 public/API/compatibility contract]

Delegated authority:
[현재 작업 안에서 스스로 선택할 수 있는 것]

Must not decide:
- [architecture / public contract / product policy / security policy 등]

Apply:
[Exact | All matches within scope]

Completion set:
[optional; Known targets, bounded search의 scope와 match rule, 각 항목의 close 상태]

Examples:
[optional; exhaustive인지 illustrative인지 명시]

Preserve / Do not touch:
- [...]

Acceptance criteria:
- [ ] ...

Validation:
- [command / observable check]

Failure / escalation:
[자의적으로 결정하지 않고 중단 또는 상위 판단을 요청할 조건]
```

필드를 기계적으로 채우지 않는다.
결과를 바꾸는 context, 이미 고정된 결정, 위임 범위가 없으면 생략한다.
반대로 public contract, 보안 정책, 외부 side effect처럼 의사결정 권한이 중요한 경우에는 명시하는 편이 안전하다.

## Review Checklist

- 조건이 외부에서 관찰 가능한가?
- 에이전트가 `필요하면`을 스스로 정의해야 하는가?
- desired result가 implementation보다 먼저 정의되어 있는가?
- hard rule, default, 조건부 동작이 혼동되지 않는가?
- 예외가 기본 동작을 무력화하지 않는가?
- 프로젝트 설정과 기존 convention의 우선순위가 분명한가?
- 수정 scope와 semantic scope가 구분되는가?
- 여러 산출물이 있으면 Known targets와 bounded search 결과를 completion set으로 닫는가?
- 이미 결정된 것과 에이전트가 결정할 수 있는 것이 구분되는가?
- acceptance와 validation이 분리되어 있는가?
- 검증 실패 시 완료를 주장할 여지가 없는가?
- 작업 복잡도에 비해 harness가 과도하지 않은가?
- 불필요한 context가 항상 로드되고 있지 않은가?

## Examples

### Ambiguous change condition

```text
Bad: 필요하면 리팩터링한다.

Better: 현재 요구사항을 충족하는 데 기존 구조가 직접적인 장애가 되는 경우에만
해당 범위의 구조를 변경한다. 관련 없는 정리나 리팩터링으로 확대하지 않는다.
```

### Avoiding an over-prescribed implementation

```text
Bad: 1:N 관계에는 prefetch_related를 반드시 사용한다.

Better: 관계 접근 때문에 반복 query가 발생하는 경우 프로젝트 ORM과 기존 패턴에 맞는
방법으로 N+1을 제거한다.
```

### Replacing self-assessed completion

```text
Bad: 문제가 없는지 확인한다.

Better:
Acceptance:
- 응답의 필수 필드와 HTTP 상태 코드 유지
- 변경한 endpoint의 정상·오류 동작 유지

Validation:
- pytest tests/api/test_orders.py -k create_order
- ruff check app/orders/
```

## Related Material

- [Superpowers `writing-skills`](https://github.com/obra/superpowers)
- [codex-downshift task capsule template](https://github.com/callorange/codex-downshift/blob/main/skills/codex-downshift/references/task-capsule-template.md)
- agent-rules-template의 Core 및 rule-validator 설계

이 문서가 이 주제에 대한 `agent-rules-template`의 독립적인 SSOT다. 외부 자료와 자동 동기화하지 않는다.
