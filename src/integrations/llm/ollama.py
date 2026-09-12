"""Ollama Interview Provider의 API transport다."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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


class OllamaInterviewProvider(StructuredInterviewProvider):
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
