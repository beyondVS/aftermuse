"""OpenAI Responses API를 첫 질문 Provider 계약으로 제한하는 Adapter다."""

import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from integrations.llm.contracts import (
    GeneratedQuestion,
    InterviewQuestionContext,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
)

_QUESTION_SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
    "additionalProperties": False,
}


class OpenAIQuestionProvider:
    """도구 없이 strict JSON 질문 하나만 요청하는 OpenAI Adapter다."""

    def __init__(
        self, *, api_key: str, model: str, timeout: float, client=None
    ) -> None:
        if not api_key or not model or timeout <= 0:
            raise QuestionGenerationConfigurationError()
        self._model = model
        self._client = client or OpenAI(
            api_key=api_key, timeout=timeout, max_retries=0
        )

    def generate_first_question(
        self, context: InterviewQuestionContext
    ) -> GeneratedQuestion:
        """신뢰 정책과 별도 payload로 질문 후보를 요청한다."""
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=_instructions_for(context),
                input=json.dumps(_untrusted_payload(context), ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "first_question",
                        "strict": True,
                        "schema": _QUESTION_SCHEMA,
                    }
                },
            )
        except APITimeoutError as error:
            raise QuestionGenerationTimeout() from error
        except (APIConnectionError, APIStatusError) as error:
            raise QuestionGenerationUnavailable() from error
        except Exception as error:
            raise QuestionGenerationUnavailable() from error
        try:
            payload = json.loads(response.output_text)
            question = payload["question"]
        except (AttributeError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise QuestionGenerationRejected() from error
        if not isinstance(question, str):
            raise QuestionGenerationRejected()
        return GeneratedQuestion(question=question)


def _instructions_for(context: InterviewQuestionContext) -> str:
    """비신뢰 payload와 분리된 최소 질문 정책을 제공한다."""
    if context.policy.value == "knowledge_grounded":
        policy = "검증된 Context Claim만 사실 전제로 사용할 수 있습니다."
    else:
        policy = "책의 사실이나 내용을 전제하지 말고 기억, 인상, 감정을 묻습니다."
    return (
        "사용자의 생각을 끌어내는 한국어 질문 한 문장만 만드세요. "
        f"{policy} 출력은 question 문자열 하나를 가진 JSON schema를 지켜야 합니다."
    )


def _untrusted_payload(context: InterviewQuestionContext) -> dict[str, object]:
    """외부 문자열을 명시적으로 data payload로만 직렬화한다."""
    return {
        "book": {
            "title": context.book_title,
            "authors": context.authors,
            "publisher": context.publisher,
        },
        "reading": {
            "status": context.reading_status,
            "completed_on": context.completed_on.isoformat()
            if context.completed_on is not None
            else None,
        },
        "knowledge_claims": list(context.knowledge_claims),
    }
