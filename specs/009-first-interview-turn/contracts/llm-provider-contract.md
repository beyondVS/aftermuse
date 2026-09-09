# LLM Provider 계약: 첫 질문 생성

## 내부 경계

```text
generate_first_question(context: InterviewQuestionContext) -> GeneratedQuestion
```

Provider는 질문 후보만 반환하며 Interview/Turn/Book/Reading/Credit을 조회·저장하거나 tool을
호출하지 않는다.

## 입력 계약

- trusted instructions: 한 질문, 사용자 생각 우선, READY_LIMITED 거짓 전제 금지, schema 준수
- untrusted payload: Book/Reading/Knowledge의 문자열·날짜·enum 값
- `READY`만 검증된 최소 Knowledge Claim을 포함한다.
- `READY_LIMITED`는 Claim을 포함하지 않고 기억·인상·감정 중심 질문 정책을 사용한다.
- 다른 사용자 정보, ORM 식별자, credential과 관리자/Credit 데이터는 포함하지 않는다.

## 출력 계약

```json
{
  "question": "이 책에서 가장 오래 남은 장면이나 생각은 무엇인가요?"
}
```

- strict structured output을 사용한다.
- application validation: trim 후 한 줄, 한 문장, 1~300자, 마지막 `?`/`？`.
- validation 전 결과는 저장하거나 Template에 전달하지 않는다.

## OpenAI Adapter

- Responses API, model setting의 pinned snapshot, `store=False`.
- tools를 전달하지 않으며 previous response/conversation state를 사용하지 않는다.
- 전체 timeout 30초, SDK automatic retry 0회.
- Provider request id는 진단용으로 기록할 수 있지만 prompt, Knowledge 원문, 사용자 답변,
  credential과 원본 오류 body는 로그에 남기지 않는다.

## 오류 taxonomy

| 내부 오류 | 원인 | 사용자 계약 |
| --- | --- | --- |
| `QuestionGenerationTimeout` | 30초 초과 | 같은 화면 Error + 명시적 재시도 |
| `QuestionGenerationUnavailable` | 연결/rate limit/5xx/provider 실패 | 같은 화면 Error + 명시적 재시도 |
| `QuestionGenerationRejected` | refusal/empty/incomplete/invalid schema/content | 저장 0건 + 명시적 재시도 |
| `QuestionGenerationConfigurationError` | key/model/provider 설정 누락 | 안전한 일반 오류; secret 비노출 |

기본 자동 테스트는 fake 또는 주입된 SDK client로 모든 오류를 재현하며 network와 실제 credential을
사용하지 않는다. 실제 연결 검증을 추가할 경우 별도 `live` marker의 opt-in 테스트로 격리한다.
