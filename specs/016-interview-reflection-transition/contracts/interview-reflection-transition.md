# 내부·HTTP 계약: Interview Skip과 Reflection Transition

## HTTP endpoint

모든 endpoint는 session 인증과 CSRF를 사용한다. 대상은 `reading__user=request.user` 또는 `interview__reading__user=request.user`로 다시 조회한다. 없는 대상과 타인 대상은 동일한 404 경계로 처리한다.

| Method / path | 일반 요청 | HTMX 요청 |
| --- | --- | --- |
| `POST /reflections/interviews/{id}/turns/{sequence}/skip/` | 최신 Interview 목적지로 redirect | `#interview-turn-region`을 다음 질문·선택·준비·종결 또는 복구 오류 fragment로 교체 |
| `POST /reflections/interviews/{id}/reflection/generate/` | 성공 시 최소 결과로 redirect, 실패 시 생성 화면 503 | 성공 시 `HX-Redirect`, 실패 시 생성 region 오류/Retry fragment 503 |
| `GET /reflections/{reflection_id}/` | owner-scoped 최소 임시 결과 HTML | 동일 HTML; partial 전용 API는 두지 않음 |

POST는 추가 form field를 허용하지 않고 stale/부적합 상태를 409로 반환한다. HTMX 4xx/5xx는 기존 region retarget·focus 이벤트 관례를 따른다.

## Interview destination

| Interview 상태 / Reflection | 목적지 |
| --- | --- |
| `IN_PROGRESS` | 현재 질문·결정·Skip 복구 화면 |
| `REFLECTION_READY`, Reflection 없음 | 생성 Loading/Retry 화면 |
| `REFLECTION_READY`, Reflection 있음 | 최소 임시 결과로 redirect |
| `ENDED_NO_REFLECTION` | 답변 부족 종결 안내 |
| `COMPLETED` | 기존 완료 목적지; Day 12 전에는 안전한 unavailable 처리 유지 |

Interview 시작·직접 URL 재진입은 같은 destination 규칙으로 수렴해야 한다. Home 재진입 연계는 Day 12 범위다.

## Skip Service

```text
skip_interview_turn(
    *, user, interview, sequence,
    next_provider=None
) -> UserSkipResult
```

`UserSkipResult`는 최신 Interview, Skip된 Turn, 후속 destination과 선택적인 새 Turn을 제공한다. View는 결과를 해석해 template만 선택하고 상태를 직접 변경하지 않는다.

### Precondition

- owner의 `IN_PROGRESS` Interview이고 Reading·Book 관계와 Coverage가 유효하다.
- sequence는 현재 마지막 답변 대기 Turn이다.
- Turn은 아직 answer와 user skip이 모두 없다. 같은 user skip 재요청은 멱등 재개한다.

### Effect

- answer를 만들지 않고 `user_skipped_at`만 최초 한 번 저장한다.
- Coverage를 변경하거나 Answer analysis를 호출하지 않는다.
- budget상 다음 질문이 필요하면 skip-aware context로 Provider를 한 번 호출한다.
- 일반/절대 cap 또는 진행 선택 결과에 따라 다음 Turn, progress decision, `REFLECTION_READY` 또는 `ENDED_NO_REFLECTION` 중 하나로 전이한다.
- Provider/DB 후속 실패에도 최초 Skip은 유지되며 재요청이 같은 단계에서 이어진다.

### Error

- 타인·없는 대상: 404 경계.
- stale sequence, 이미 다른 답변, terminal Interview, 허용하지 않은 form key: 409 정책 충돌.
- 다음 질문 Provider/후속 persistence 실패: 503 복구 화면. 질문·응답 원문과 외부 exception은 노출하지 않는다.

## Skip-aware 다음 질문 계약

기존 `NextQuestionContext`에 아래 의미를 명시한다.

| 값 | Answer 경로 | 사용자 Skip 경로 |
| --- | --- | --- |
| `answer` | 비공백 확정 원문 | `None` |
| `user_skipped` | `False` | `True` |
| `skipped_questions` | 이전 사용자 Skip 질문 tuple | 현재 질문을 포함한 Skip 질문 tuple |
| `meaning` | 검증된 분석 또는 None | None |
| `low_information` | 분석 결과 | False; Skip과 혼용하지 않음 |
| `coverage` | 분석 반영 projection | 기존 snapshot 그대로 |

Prompt는 `user_skipped=true`를 답변으로 해석하지 않고 같은 질문을 압박·반복하지 않도록 지시한다. 출력 schema는 기존 question/skip 구조를 유지한다. READY_LIMITED에서는 확정 발화나 검증된 Claim에 없는 책 사실을 전제하지 않는다. 사용자 Skip 경로에서 grounding이 없으면 미충족 축의 기억·인상 중심 질문만 허용한다.

## Reflection orchestration

```text
generate_or_get_reflection_draft(
    *, user, interview, provider=None
) -> ReflectionGenerationResult
```

결과는 owner Reflection과 `created` 여부를 제공한다.

1. 기존 owner Reflection이 있으면 Provider 호출 없이 `created=False`로 반환한다.
2. 없으면 기존 `generate_reflection_draft`를 한 번 호출한다.
3. 검증 결과를 기존 `save_reflection_draft`로 저장한다.
4. concurrent `ReflectionDraftConflict` 후 owner Reflection이 확인되면 `created=False` 성공으로 반환한다. 확인되지 않으면 conflict를 유지한다.

Policy·Validation·Generation·Persistence 오류는 고정된 사용자 범주로 매핑한다. 자동 retry와 provider fallback은 없다. 로그는 작업명, Interview 내부 id, exception class 또는 안전한 reason code만 포함하며 answer·proposal·credential·exception message는 기록하지 않는다.

## Template 상태 계약

### Reflection 생성

- Loading: `aria-busy=true`, `role=status`, `aria-live=polite`, submit disabled, `hx-sync=drop`.
- Error: `role=alert`, focus 가능한 오류 제목, 답변 보존 안내, 명시적 Retry button.
- Success: HTMX와 일반 요청 모두 최소 임시 결과 URL로 이동.
- Minimal result: 책 제목, “독서노트 초안 생성 완료”, 저장된 Reflection 존재만 표시. 본문·수정·완료·Home CTA는 Day 12.

### 사용자 Skip

- 현재 질문 form에 답변 submit과 구분되는 POST button을 제공한다.
- button label은 “건너뛰기”이고 답변을 저장하지 않는다는 설명을 연결한다.
- 처리 중 색상 외 status와 disabled 상태를 제공한다.
- 실패 후 재진입은 Skip 완료 사실과 “다음 질문 다시 준비” 행동을 제공하며 이전 질문 답변 form으로 되돌리지 않는다.

### Knowledge 안내

- `READY`, `READY_LIMITED`, `Knowledge readiness`, `RAG`, “준비 수준” 문자열을 사용자 HTML에 출력하지 않는다.
- READY는 별도 준비 상태 문구 없이 정상 Interview 안내만 표시한다.
- READY_LIMITED는 시작·질문 화면에서 확인 가능한 정보가 많지 않으며 기억과 감상부터 이야기한다는 non-alert 안내를 표시한다.

## 접근성·반응형 계약

- 주요 상태는 색상만으로 구분하지 않는다.
- POST 오류 후 focus는 `role=alert` region으로 이동한다.
- 모든 form control과 button은 keyboard로 접근 가능하고 명확한 accessible name을 가진다.
- Django test client로 Desktop/Mobile 공통 markup 구조와 overflow를 유발하는 고정 폭 부재를 검증한다. 실제 브라우저 실행은 필수 완료 조건이 아니다.
