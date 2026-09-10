# 내부 계약: 답변 분석

## 범위

확정된 Interview Turn 하나를 읽어 Provider 중립 Context를 만들고 구조화 제안을 전체 검증해
비영속 `AnswerAnalysisResult`로 반환한다. HTTP, UI, 상태 저장, Coverage 적용과 다음 질문은 없다.

## Provider 계약

```text
AnswerAnalysisProvider.analyze_answer(context: AnswerAnalysisContext)
    -> ProposedAnswerAnalysis
```

Provider는 답변 의미 또는 null, 단일 low-information 판정, 현재 Coverage보다 높은 후보 0~4개와
각 후보의 answer exact quote만 제안한다. tools, DB, Web Search와 상태 변경 권한은 없다.

### Structured Output 예시

```json
{
  "meaning": "결말에서 허무함을 느꼈다",
  "low_information": false,
  "coverage_patch": [
    {"axis": "REACTION", "status": "PARTIAL", "evidence": "결말이 허무했어요"}
  ]
}
```

low-information은 `{"meaning": null, "low_information": true, "coverage_patch": []}`다.
모든 field는 required이고 additional properties는 금지한다. schema 통과 후에도 Application이
business invariant를 다시 검증한다.

## Application Service 계약

```text
analyze_interview_answer(
    *, user, interview, turn,
    provider=None, provider_factory=None,
) -> AnswerAnalysisResult
```

### 처리 순서

1. 저장된 Interview/Turn 객체인지 확인한다.
2. `reading__user=user`인 Interview를 DB에서 다시 조회한다.
3. Book/Reading 관계, `IN_PROGRESS`, canonical Coverage를 확인한다.
4. 같은 Interview 소속 Turn과 질문·확정 답변을 DB에서 확인한다.
5. provider/factory 충돌을 확인한 뒤에만 Provider를 준비한다.
6. Context를 구성하고 transaction 밖에서 Provider를 한 번 호출한다.
7. 제안 전체를 검증해 trusted result로 변환한다.
8. DB write 없이 반환한다.

### 결과 검증

- 정상 meaning은 trim된 1~1,000자, low-information meaning은 `None`이다.
- `low_information=True`이면 patch가 비어야 하며, `False`이면 meaning이 필수다.
- patch는 최대 4개이고 축은 유일해야 한다.
- axis/status enum과 현재 상태보다 엄격한 상승을 검사한다.
- evidence는 trim된 1~500자이며 answer에 그대로 포함되어야 한다.
- meaning/evidence의 알려진 권한 변경·시스템/비밀 정보 요구 패턴을 거부한다.
- 한 항목이라도 틀리면 전체를 거부하고 일부 후보를 제거해 수용하지 않는다.
- 결과 후보는 canonical 축 순서로 정렬한다.

## 오류 계약

| 오류 | 발생 조건 |
| --- | --- |
| `AnswerAnalysisPolicyError` | 대상, 소유권, 관계, status, Turn, 답변 또는 Coverage 위반 |
| `AnswerAnalysisConfigurationError` | provider 이름, key, model 또는 timeout 오류 |
| `AnswerAnalysisTimeout` | SDK timeout |
| `AnswerAnalysisUnavailable` | 연결, rate limit, HTTP/provider 장애 |
| `AnswerAnalysisRejected` | 미완료/refusal/JSON 해석 또는 Application validation 실패 |

모든 오류 메시지는 API key, Provider 원문, 사용자 답변과 내부 detail을 포함하지 않으며 domain
상태를 변경하지 않는다.

## Fake와 OpenAI Adapter

- fake는 주입 결과/오류 반환과 Context 기록을 network 없이 결정적으로 지원한다.
- OpenAI Adapter는 기존 고정 model/timeout, `store=False`, tools 없음, `max_retries=0`, strict
  schema와 trusted instructions/untrusted payload 분리를 사용한다.
- fake와 OpenAI 모두 같은 Provider Protocol과 오류 경계를 지키고 Application validator를
  우회하지 않는다.

## 명시적 비범위

- Coverage patch 적용과 분석 metadata 저장
- Focus Coverage, 다음 질문 또는 Feedback
- low-information 누적, Budget, Soft Stop과 종료 상태
- Reflection, Credit, Reading과 Book Knowledge 변경
- endpoint, form, template, HTMX와 브라우저 동작
