"""OpenAI Responses API의 structured Interview transport다."""

import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from integrations.llm.contracts import (
    AnswerAnalysisRejected,
    AnswerAnalysisTimeout,
    AnswerAnalysisUnavailable,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
)
from integrations.llm.interview import StructuredInterviewProvider


class OpenAIInterviewProvider(StructuredInterviewProvider):
    """세 Interview 작업을 같은 Responses API 호출로 처리한다."""

    def __init__(
        self, *, api_key: str, model: str, timeout: float, client=None
    ) -> None:
        if not api_key or not model or timeout <= 0:
            raise QuestionGenerationConfigurationError()
        self._model = model
        self._client = client or OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def _request(self, *, task, instructions, payload, schema):
        rejected = (
            AnswerAnalysisRejected if task == "analysis" else QuestionGenerationRejected
        )
        timeout_error = (
            AnswerAnalysisTimeout if task == "analysis" else QuestionGenerationTimeout
        )
        unavailable = (
            AnswerAnalysisUnavailable
            if task == "analysis"
            else QuestionGenerationUnavailable
        )
        names = {
            "first": "first_question",
            "analysis": "answer_analysis",
            "next": "next_question",
        }
        try:
            response = self._client.responses.create(
                model=self._model,
                store=False,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": names[task],
                        "strict": True,
                        "schema": schema,
                    }
                },
            )
        except APITimeoutError as error:
            raise timeout_error() from error
        except (APIConnectionError, APIStatusError) as error:
            raise unavailable() from error
        except Exception as error:
            raise unavailable() from error
        if getattr(response, "status", "completed") != "completed":
            raise rejected()
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise rejected()
        return output_text
