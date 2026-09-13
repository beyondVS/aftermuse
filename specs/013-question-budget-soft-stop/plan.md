# 구현 계획: 질문 상한과 Soft Stop

**브랜치**: `feature/day-08-question-budget-soft-stop` | **날짜**: 2026-09-13 | **사양**: [spec.md](spec.md)

**입력**: Day 08 IMP-080, IMP-081, IMP-084와 확정된 기능 사양

## 요약

기존 답변 분석·Coverage·다음 질문 흐름에 질문 Budget 판단을 삽입한다. 충분한 Coverage와 4~7개 답변이 있으면 검증된 다음 질문 후보를 바로 Turn으로 만들지 않고 Soft Stop 선택으로 보류한다. 8문항에서는 일반 상한을 우선하고 `UNCOVERED` 축과 유효한 질문 근거가 있을 때만 별도 예외 선택을 제공하며, 계속을 선택해도 10문항을 넘지 않는다. 종료·상한·검증된 생략은 기존 `REFLECTION_READY` 상태와 준비 안내로 연결한다. Reflection 초안과 생성 화면은 만들지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, HTMX 2.0.10, 기존 LLM Provider 계약

**저장소**: PostgreSQL 18; 기존 Interview·Turn에 선택 대기 기록 연결

**테스트**: pytest-django, Django test client, Ruff, Django system check, `scripts/verify.py`

**대상 플랫폼**: Desktop/Mobile 반응형 서버 렌더링 Web

**프로젝트 유형**: 단일 Django Web 애플리케이션

**성능 목표**: Budget·선택 판정은 로컬 정책으로 수행하고, 추가 Provider 호출은 기존 다음 질문 경로의 호출 수를 넘기지 않는다.

**제약 조건**: 답변 원문 선확정, Coverage와 선택 대기 또는 다음 Turn의 원자성, 소유권 검증, 기존 Provider timeout, 8/10문항 상한, 외부 연결 없는 기본 테스트

**규모/범위**: Interview당 최대 10개 질문과 답변, 한 답변 Turn당 최대 한 선택 기록; Day 09~10 Reflection 구현 제외

## 헌법 검사

*게이트: 설계 전·후 모두 통과. 별도 예외 없음.*

| 원칙 | 설계 적용 및 검증 |
|---|---|
| 사용자 생각의 충실성 | 후보 질문은 기존 답변·검증된 맥락에 근거하고, 종료는 새 생각이나 Reflection 내용을 생성하지 않는다. |
| 핵심 제품 루프와 범위 | Coverage 기반 질문과 Soft Stop을 유지하며 Day 09~10의 Reflection 초안·전환은 미리 구현하지 않는다. |
| 신뢰 경계와 데이터 통제 | LLM은 질문 또는 명시적 생략을 제안할 뿐 선택·상한·상태를 결정하지 않는다. 소유권과 정책은 Service에서 검증한다. |
| 단순한 아키텍처 | `reflections`의 기존 Service와 View를 확장하고 새 API 계층·작업 큐를 도입하지 않는다. |
| 회복 가능한 UX | 답변은 후속 처리 전에 확정한다. 일반 POST와 HTMX 모두 대기·오류·재시도·준비 상태를 표시하고 미확정 후보를 숨긴다. |
| 품질 게이트 | PostgreSQL 상태 전이·경합·마이그레이션과 Django 응답 계약을 검증한다. 실제 브라우저·외부 LLM live 호출은 요구하지 않는다. |

## 구현 흐름

1. 질문 Budget의 목표 5~6, 일반 상한 8, 절대 상한 10을 단순 설정으로 두고 유효한 순서를 확인한다. 확정 답변 수와 생성된 질문 수를 구분한다. 기존 Turn은 삭제하지 않는다. 8번째 답변에서는 Soft Stop보다 일반 상한을 먼저 판단한다.
2. 답변 분석 후 Service가 Coverage 예상값·답변 수·기존 예외 선택을 평가하고 필요한 경우에만 유효한 다음 질문 후보를 만든다. 10번째 답변이나 8번째 답변에서 `UNCOVERED` 축이 없으면 질문 Provider를 호출하지 않고 준비 상태로 전환한다. 8문항 예외는 `UNCOVERED` 축을 겨냥한 검증된 후보가 있을 때만 제안한다.
3. Soft Stop 또는 8문항 예외에서는 Coverage 변경과 비공개 후보 질문을 연결한 선택 기록을 한 트랜잭션에서 확정한다. 종료는 `REFLECTION_READY`로, 계속은 보류된 질문 하나의 Turn 확정으로 연결한다. 같은 Turn의 선택은 한 번만 확정하고 경합·반복 요청에서 재사용한다.
4. 상태별 HTML/HTMX 화면에 Soft Stop, 예외 선택, Reflection 준비, 답변 보존·재시도 안내를 연결한다. CSRF 보호 POST로만 상태를 바꾸며 미완성 Reflection 경로로 보내지 않는다.
5. 기존 Day 07의 질문 생략 표식이 있는 진행 중 Interview는 GET에서 준비 안내로 판정하고, 후속 확정 POST에서는 재분석·질문 생성 없이 `REFLECTION_READY`로 멱등 전환한다. 8번째 답변의 예외 평가와 허가된 9번째 답변에서는 근거 부족을 명시적으로 검증해 준비 상태로 연결한다. Provider 실패·시간 초과·무효 결과는 종료로 바꾸지 않고 답변 원문과 이전 Coverage를 유지한다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/013-question-budget-soft-stop/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/interview-flow.md
```

### 소스 코드 (저장소 루트)

```text
src/config/settings.py
src/reflections/models.py
src/reflections/services.py
src/reflections/views.py
src/reflections/urls.py
src/reflections/migrations/
src/integrations/llm/
src/templates/reflections/
tests/reflections/
tests/integrations/llm/
```

**구조 결정**: 정책·잠금·원자성은 기존 Service에 두고 View는 입력과 응답만 담당한다. 질문 후보의 신뢰 경계는 기존 LLM Adapter와 Application 검증을 재사용한다.

## 설계 후 헌법 재검사

- 새 선택 기록은 답변 원문과 구분되며, 공개되지 않은 후보 질문을 사용자에게 노출하지 않는다.
- 기존 `REFLECTION_READY` 목적지를 재사용하므로 Day 09~10의 Reflection 데이터·생성·전환을 구현할 필요가 없다.
- 새 테이블의 schema 변경은 기존 행을 재작성하지 않는 추가 방식으로 계획한다. 실제 migration 생성 단계에서 SQL·잠금 범위·적용·역적용을 확인한다.
- 권한, 오류, 반복·동시 요청은 결정적 DB·응답 검증 대상으로 남겨 둔다. 헌법 위반이나 미해결 기술 선택은 없다.
