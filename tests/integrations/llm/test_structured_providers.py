"""Gemini와 Ollama의 세 작업 계약을 외부 연결 없이 검증한다."""

import io
import json
from datetime import date
from types import SimpleNamespace

import pytest

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    AnswerAnalysisRejected,
    CurrentCoverageItem,
    InterviewQuestionContext,
    NextQuestionContext,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
    QuestionPolicy,
)
from integrations.llm.gemini import GeminiInterviewProvider
from integrations.llm.ollama import OllamaInterviewProvider


def _context():
    question_context = InterviewQuestionContext(
        "책",
        "저자",
        "출판사",
        "COMPLETED",
        date(2026, 9, 12),
        "READY_LIMITED",
        (),
        QuestionPolicy.MEMORY_CENTERED,
    )
    return NextQuestionContext(
        question_context,
        (),
        "무엇이 남았나요?",
        "푸른 표지가 남았어요",
        "푸른 표지",
        False,
        tuple(
            CurrentCoverageItem(axis, "UNCOVERED")
            for axis in ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT")
        ),
    )


class GeminiClient:
    def __init__(self, text):
        self.text = text
        self.calls = []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.text, Exception):
            raise self.text
        return SimpleNamespace(text=self.text)


class Transport:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def __call__(self, request, *, timeout):
        self.calls.append((request, timeout))
        if isinstance(self.content, Exception):
            raise self.content
        return io.BytesIO(
            json.dumps({"done": True, "message": {"content": self.content}}).encode()
        )


@pytest.mark.parametrize("provider_type", ["gemini", "ollama"])
def test_three_tasks_use_structured_output_without_network(provider_type):
    output = json.dumps(
        {
            "kind": "question",
            "question": "푸른 표지가 왜 남았나요?",
            "focus_axis": "MEMORY",
            "grounding_quote": "푸른 표지",
            "skip_reason": None,
        },
        ensure_ascii=False,
    )
    if provider_type == "gemini":
        client = GeminiClient(output)
        provider = GeminiInterviewProvider(
            api_key="explicit-key", model="exact-model", timeout=4, client=client
        )
    else:
        client = Transport(output)
        provider = OllamaInterviewProvider(
            base_url="http://127.0.0.1:11434",
            model="gemma4:12b-it-qat",
            timeout=4,
            transport=client,
        )
    result = provider.generate_next_question(_context())
    assert result.question == "푸른 표지가 왜 남았나요?"
    if provider_type == "gemini":
        request = client.calls[0]
        assert request["model"] == "exact-model"
        assert request["config"].response_mime_type == "application/json"
        assert request["config"].response_json_schema["required"] == [
            "kind",
            "question",
            "focus_axis",
            "grounding_quote",
            "skip_reason",
        ]
        assert "푸른 표지가 남았어요" in request["contents"]
        assert "푸른 표지가 남았어요" not in request["config"].system_instruction
    else:
        request, timeout = client.calls[0]
        body = json.loads(request.data)
        assert request.full_url == "http://127.0.0.1:11434/api/chat"
        assert body["model"] == "gemma4:12b-it-qat"
        assert body["stream"] is False and body["format"]["type"] == "object"
        assert timeout == 4
    assert len(client.calls) == 1


@pytest.mark.parametrize("provider_type", ["gemini", "ollama"])
def test_first_question_and_analysis_contracts(provider_type):
    def make_provider(output):
        if provider_type == "gemini":
            client = GeminiClient(output)
            return GeminiInterviewProvider(
                api_key="key", model="exact", timeout=3, client=client
            ), client
        client = Transport(output)
        return OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=3,
            transport=client,
        ), client

    provider, client = make_provider('{"question":"어떤 생각이 남았나요?"}')
    assert (
        provider.generate_first_question(_context().question_context).question
        == "어떤 생각이 남았나요?"
    )
    assert len(client.calls) == 1
    provider, client = make_provider(
        '{"meaning":"표지가 남음","low_information":false,"coverage_patch":[]}'
    )
    result = provider.analyze_answer(
        AnswerAnalysisContext(
            _context().question_context,
            "무엇이 남았나요?",
            "푸른 표지",
            _context().coverage,
        )
    )
    assert result.meaning == "표지가 남음" and result.coverage_patch == ()
    assert len(client.calls) == 1


@pytest.mark.parametrize("provider_type", ["gemini", "ollama"])
def test_invalid_result_and_timeout_are_safe(provider_type):
    def provider(content):
        if provider_type == "gemini":
            return GeminiInterviewProvider(
                api_key="key", model="exact", timeout=2, client=GeminiClient(content)
            )
        return OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=2,
            transport=Transport(content),
        )

    with pytest.raises(QuestionGenerationRejected):
        provider("not json").generate_next_question(_context())
    with pytest.raises(AnswerAnalysisRejected):
        provider("{}").analyze_answer(
            SimpleNamespace(
                question_context=_context().question_context,
                question="질문",
                answer="답변",
                current_coverage=(),
            )
        )
    with pytest.raises(QuestionGenerationTimeout):
        provider(TimeoutError()).generate_first_question(_context().question_context)


def test_ollama_rejects_nonlocal_url_and_connection_failure():
    with pytest.raises(QuestionGenerationConfigurationError):
        OllamaInterviewProvider(
            base_url="http://remote.example:11434", model="exact", timeout=2
        )
    with pytest.raises(QuestionGenerationUnavailable):
        OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=2,
            transport=Transport(ConnectionError()),
        ).generate_first_question(_context().question_context)


def test_gemini_requires_explicit_key():
    with pytest.raises(QuestionGenerationConfigurationError):
        GeminiInterviewProvider(api_key="", model="exact", timeout=2)
