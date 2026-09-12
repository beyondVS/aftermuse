"""Gemini SDK와 로컬 Ollama의 세 Interview 작업용 제한된 Adapter다."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import httpx
from google import genai
from google.genai import errors, types

from integrations.llm.contracts import (
    AnswerAnalysisRejected,
    AnswerAnalysisTimeout,
    AnswerAnalysisUnavailable,
    GeneratedQuestion,
    ProposedAnswerAnalysis,
    ProposedCoverageChange,
    ProposedNextQuestion,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
)
from integrations.llm.openai import (
    _ANSWER_ANALYSIS_SCHEMA,
    _NEXT_QUESTION_SCHEMA,
    _QUESTION_SCHEMA,
    _answer_analysis_instructions,
    _answer_analysis_payload,
    _instructions_for,
    _next_question_instructions,
    _next_question_payload,
    _untrusted_payload,
)


def _decode(payload: object, task: str):
    """SDK의 구조화 출력도 필수 키와 타입을 로컬에서 다시 확인한다."""
    rejected = (
        AnswerAnalysisRejected if task == "analysis" else QuestionGenerationRejected
    )
    try:
        value = json.loads(payload)
        if not isinstance(value, dict):
            raise ValueError
        if task == "first":
            if not isinstance(value["question"], str):
                raise ValueError
            return GeneratedQuestion(value["question"])
        if task == "analysis":
            if not isinstance(value["low_information"], bool):
                raise ValueError
            if value["meaning"] is not None and not isinstance(value["meaning"], str):
                raise ValueError
            patch = value["coverage_patch"]
            if not isinstance(patch, list):
                raise ValueError
            changes = tuple(
                ProposedCoverageChange(item["axis"], item["status"], item["evidence"])
                for item in patch
            )
            return ProposedAnswerAnalysis(
                value["meaning"], value["low_information"], changes
            )
        return ProposedNextQuestion(
            value["kind"],
            value["question"],
            value["focus_axis"],
            value["grounding_quote"],
            value["skip_reason"],
        )
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise rejected() from error


class _InterviewAdapter:
    """하나의 요청을 세 작업의 공통 입력·오류 계약으로 변환한다."""

    def _request(self, *, task, instructions, payload, schema):
        raise NotImplementedError

    def generate_first_question(self, context):
        return _decode(
            self._request(
                task="first",
                instructions=_instructions_for(context),
                payload=_untrusted_payload(context),
                schema=_QUESTION_SCHEMA,
            ),
            "first",
        )

    def analyze_answer(self, context):
        return _decode(
            self._request(
                task="analysis",
                instructions=_answer_analysis_instructions(),
                payload=_answer_analysis_payload(context),
                schema=_ANSWER_ANALYSIS_SCHEMA,
            ),
            "analysis",
        )

    def generate_next_question(self, context):
        return _decode(
            self._request(
                task="next",
                instructions=_next_question_instructions(context.question_context),
                payload=_next_question_payload(context),
                schema=_NEXT_QUESTION_SCHEMA,
            ),
            "next",
        )


class GeminiInterviewProvider(_InterviewAdapter):
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
        except AnswerAnalysisRejected, QuestionGenerationRejected:
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


class OllamaInterviewProvider(_InterviewAdapter):
    """명시한 loopback Ollama API로만 한 번 POST한다."""

    def __init__(self, *, base_url: str, model: str, timeout: float, transport=None):
        try:
            parsed = urlparse(base_url)
            port = parsed.port
        except ValueError as error:
            raise QuestionGenerationConfigurationError() from error
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or port is None
            or not model.strip()
            or timeout <= 0
        ):
            raise QuestionGenerationConfigurationError()
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout = timeout
        self._transport = transport or urlopen

    def _request(self, *, task, instructions, payload, schema):
        body = {
            "model": self._model,
            "stream": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        }
        request = Request(
            self._url,
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._transport(request, timeout=self._timeout) as response:
                output = json.load(response)
            if output.get("done") is not True:
                raise ValueError
            content = output["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError
            return content
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise (
                AnswerAnalysisRejected
                if task == "analysis"
                else QuestionGenerationRejected
            )() from error
        except TimeoutError as error:
            raise (
                AnswerAnalysisTimeout
                if task == "analysis"
                else QuestionGenerationTimeout
            )() from error
        except (HTTPError, URLError, OSError) as error:
            raise (
                AnswerAnalysisUnavailable
                if task == "analysis"
                else QuestionGenerationUnavailable
            )() from error
