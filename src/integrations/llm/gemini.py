"""Gemini Interview Provider의 API transport다."""

import json

import httpx
from google import genai
from google.genai import errors, types

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


class GeminiInterviewProvider(StructuredInterviewProvider):
    """명시적 API key만 사용하는 Google Gen AI SDK Adapter다."""

    def __init__(self, *, api_key: str, model: str, timeout: float, client=None):
        if not api_key.strip() or not model.strip() or timeout <= 0:
            raise QuestionGenerationConfigurationError()
        self._model = model
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def _request(self, *, task, instructions, payload, schema):
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=instructions,
                    response_mime_type="application/json",
                    response_json_schema=schema,
                ),
            )
            if not isinstance(response.text, str) or not response.text.strip():
                raise (
                    AnswerAnalysisRejected
                    if task == "analysis"
                    else QuestionGenerationRejected
                )()
            return response.text
        except (AnswerAnalysisRejected, QuestionGenerationRejected):
            raise
        except (TimeoutError, httpx.TimeoutException) as error:
            raise (
                AnswerAnalysisTimeout
                if task == "analysis"
                else QuestionGenerationTimeout
            )() from error
        except errors.APIError as error:
            raise (
                AnswerAnalysisUnavailable
                if task == "analysis"
                else QuestionGenerationUnavailable
            )() from error
        except Exception as error:
            raise (
                AnswerAnalysisUnavailable
                if task == "analysis"
                else QuestionGenerationUnavailable
            )() from error
