"""Gemini, Ollama, OpenAI의 작업 계약을 외부 연결 없이 검증한다."""

import io
import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError

from integrations.llm.contracts import (
    AnswerAnalysisContext,
    AnswerAnalysisRejected,
    CurrentCoverageItem,
    InterviewQuestionContext,
    NextQuestionContext,
    ProposedReflectionDraft,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
    QuestionPolicy,
    ReflectionGenerationContext,
    ReflectionGenerationRejected,
    ReflectionGenerationTimeout,
    ReflectionGenerationUnavailable,
    ReflectionSourceTurn,
)
from integrations.llm.gemini import GeminiInterviewProvider
from integrations.llm.ollama import OllamaInterviewProvider
from integrations.llm.openai import OpenAIInterviewProvider
from integrations.llm.reflection import (
    build_reflection_instructions,
    build_reflection_payload,
    build_reflection_schema,
)


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


@pytest.mark.parametrize("provider_type", ["gemini", "ollama"])
def test_cap_extension_structured_skip_preserves_budget_mode(provider_type):
    output = json.dumps(
        {
            "kind": "skip",
            "question": None,
            "focus_axis": None,
            "grounding_quote": None,
            "skip_reason": "미탐색 방향에 연결할 구체적 답변 근거가 없습니다.",
        },
        ensure_ascii=False,
    )
    context = _context()
    context = NextQuestionContext(
        context.question_context,
        context.previous_turns,
        context.question,
        context.answer,
        context.meaning,
        context.low_information,
        context.coverage,
        "CAP_EXTENSION",
    )
    if provider_type == "gemini":
        client = GeminiClient(output)
        provider = GeminiInterviewProvider(
            api_key="explicit-key",
            model="exact-model",
            timeout=4,
            client=client,
        )
        result = provider.generate_next_question(context)
        payload = client.calls[0]["contents"]
    else:
        client = Transport(output)
        provider = OllamaInterviewProvider(
            base_url="http://127.0.0.1:11434",
            model="gemma4:12b-it-qat",
            timeout=4,
            transport=client,
        )
        result = provider.generate_next_question(context)
        payload = client.calls[0][0].data.decode()
    assert result.kind == "skip"
    assert "CAP_EXTENSION" in payload


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
@pytest.mark.parametrize(
    ("covered", "budget_mode", "kinds"),
    [
        (False, "NORMAL", ["question"]),
        (True, "NORMAL", ["question", "skip"]),
        (False, "CAP_EXTENSION", ["question", "skip"]),
    ],
)
def test_next_wire_contract_only_allows_policy_permitted_skip(
    provider_type, covered, budget_mode, kinds
):
    """저정보 답변도 미완료 일반 모드에서는 질문을 요구하고 허용된 생략은 유지한다."""
    context = _context()
    context = NextQuestionContext(
        context.question_context,
        (),
        context.question,
        "잘 모르겠어요",
        None,
        True,
        tuple(
            CurrentCoverageItem(item.axis, "COVERED" if covered else "UNCOVERED")
            for item in context.coverage
        ),
        budget_mode,
    )
    output = json.dumps(
        {
            "kind": "question",
            "question": "읽을 때 어떤 느낌이 들었나요?",
            "focus_axis": "REACTION",
            "grounding_quote": None,
            "skip_reason": None,
        },
        ensure_ascii=False,
    )
    if provider_type == "gemini":
        client = GeminiClient(output)
        provider = GeminiInterviewProvider(
            api_key="key", model="exact", timeout=3, client=client
        )
    else:
        client = Transport(output)
        provider = OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=3,
            transport=client,
        )
    result = provider.generate_next_question(context)
    assert result.kind == "question"
    schema = (
        client.calls[0]["config"].response_json_schema
        if provider_type == "gemini"
        else json.loads(client.calls[0][0].data)["format"]
    )
    assert schema["properties"]["kind"]["enum"] == kinds
    if kinds == ["question"]:
        assert schema["properties"]["question"]["type"] == "string"
        assert schema["properties"]["focus_axis"]["type"] == "string"
    from integrations.llm.interview import _NEXT_QUESTION_SCHEMA

    assert _NEXT_QUESTION_SCHEMA["properties"]["kind"]["enum"] == ["question", "skip"]


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
        assert request["config"].automatic_function_calling.disable is True
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


class OpenAIClient:
    def __init__(self, output_text, status="completed"):
        self.output_text = output_text
        self.status = status
        self.calls = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.output_text, Exception):
            raise self.output_text
        return SimpleNamespace(output_text=self.output_text, status=self.status)


def _reflection_context() -> ReflectionGenerationContext:
    return ReflectionGenerationContext(
        turns=(
            ReflectionSourceTurn(
                sequence=1,
                question="가장 기억에 남는 장면은 무엇이었나요?",
                answer="주인공이 바다를 바라보며 결심하던 순간이 떠올랐어요.",
            ),
            ReflectionSourceTurn(
                sequence=2,
                question="그 결심이 어떤 울림을 주었나요?",
                answer="포기하지 않는 용기가 느껴졌습니다.",
            ),
        )
    )


def _valid_reflection_output() -> str:
    return json.dumps(
        {
            "sections": [
                {
                    "title": "바다를 바라보던 결심",
                    "paragraphs": [
                        {
                            "text": (
                                "주인공이 바다를 바라보며 결심하던 순간이 떠올랐어요."
                            ),
                            "evidence": [
                                {
                                    "sequence": 1,
                                    "quote": (
                                        "주인공이 바다를 바라보며 "
                                        "결심하던 순간이 떠올랐어요."
                                    ),
                                }
                            ],
                        }
                    ],
                }
            ]
        },
        ensure_ascii=False,
    )


@pytest.mark.parametrize("provider_type", ["openai", "gemini", "ollama"])
def test_reflection_task_uses_structured_output_without_network(provider_type):
    output = _valid_reflection_output()
    context = _reflection_context()
    expected_schema = build_reflection_schema()
    expected_instructions = build_reflection_instructions()
    expected_payload = build_reflection_payload(context)

    if provider_type == "openai":
        client = OpenAIClient(output)
        provider = OpenAIInterviewProvider(
            api_key="explicit-key", model="exact-model", timeout=4, client=client
        )
        result = provider.generate_reflection(context)
        assert len(client.calls) == 1
        request = client.calls[0]
        assert request["model"] == "exact-model"
        assert request["store"] is False
        assert "tools" not in request
        assert request["instructions"] == expected_instructions
        assert json.loads(request["input"]) == expected_payload
        format_spec = request["text"]["format"]
        assert format_spec["type"] == "json_schema"
        assert format_spec["name"] == "reflection_draft"
        assert format_spec["strict"] is True
        assert format_spec["schema"] == expected_schema
    elif provider_type == "gemini":
        client = GeminiClient(output)
        provider = GeminiInterviewProvider(
            api_key="explicit-key", model="exact-model", timeout=4, client=client
        )
        result = provider.generate_reflection(context)
        assert len(client.calls) == 1
        request = client.calls[0]
        assert request["model"] == "exact-model"
        assert request["config"].response_mime_type == "application/json"
        assert request["config"].automatic_function_calling.disable is True
        assert request["config"].response_json_schema == expected_schema
        assert request["config"].system_instruction == expected_instructions
        assert json.loads(request["contents"]) == expected_payload
    else:
        client = Transport(output)
        provider = OllamaInterviewProvider(
            base_url="http://127.0.0.1:11434",
            model="gemma4:12b-it-qat",
            timeout=4,
            transport=client,
        )
        result = provider.generate_reflection(context)
        assert len(client.calls) == 1
        request, timeout = client.calls[0]
        body = json.loads(request.data)
        assert request.full_url == "http://127.0.0.1:11434/api/chat"
        assert body["model"] == "gemma4:12b-it-qat"
        assert body["stream"] is False
        assert body["format"] == expected_schema
        assert body["messages"][0]["content"] == expected_instructions
        assert json.loads(body["messages"][1]["content"]) == expected_payload
        assert timeout == 4

    assert isinstance(result, ProposedReflectionDraft)
    assert len(result.sections) == 1
    assert result.sections[0]["title"] == "바다를 바라보던 결심"
    assert result.sections[0]["paragraphs"][0]["evidence"][0]["sequence"] == 1


@pytest.mark.parametrize("provider_type", ["openai", "gemini", "ollama"])
def test_reflection_task_error_mapping_safe(provider_type):
    context = _reflection_context()

    def get_provider(content_or_error):
        if provider_type == "openai":
            return OpenAIInterviewProvider(
                api_key="key",
                model="exact",
                timeout=2,
                client=OpenAIClient(content_or_error),
            )
        if provider_type == "gemini":
            return GeminiInterviewProvider(
                api_key="key",
                model="exact",
                timeout=2,
                client=GeminiClient(content_or_error),
            )
        return OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=2,
            transport=Transport(content_or_error),
        )

    # 1. Timeout error
    if provider_type == "openai":
        timeout_exc = APITimeoutError(
            httpx.Request("POST", "https://api.openai.com/v1/responses")
        )
    else:
        timeout_exc = TimeoutError("timeout")
    with pytest.raises(ReflectionGenerationTimeout):
        get_provider(timeout_exc).generate_reflection(context)

    # 2. Unavailable error
    if provider_type == "openai":
        unavail_exc = APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com/v1/responses")
        )
    elif provider_type == "gemini":
        unavail_exc = RuntimeError("gemini connection failure")
    else:
        unavail_exc = ConnectionError("ollama down")
    with pytest.raises(ReflectionGenerationUnavailable):
        get_provider(unavail_exc).generate_reflection(context)

    # 3. Rejected error (malformed json, incomplete status)
    with pytest.raises(ReflectionGenerationRejected):
        get_provider("not valid json").generate_reflection(context)

    with pytest.raises(ReflectionGenerationRejected):
        get_provider("{}").generate_reflection(context)


@pytest.mark.parametrize("provider_type", ["openai", "gemini", "ollama"])
def test_reflection_task_rejects_extra_root_keys_before_application(provider_type):
    """Wire의 sections 외 추가 키는 Application 검증 전 거부된다."""
    context = _reflection_context()
    valid_base = json.loads(_valid_reflection_output())
    valid_base["markdown"] = "## 별도 마크다운 본문"
    valid_base["summary"] = "추가 요약"
    tampered_output = json.dumps(valid_base, ensure_ascii=False)

    if provider_type == "openai":
        provider = OpenAIInterviewProvider(
            api_key="key",
            model="exact",
            timeout=2,
            client=OpenAIClient(tampered_output),
        )
    elif provider_type == "gemini":
        provider = GeminiInterviewProvider(
            api_key="key",
            model="exact",
            timeout=2,
            client=GeminiClient(tampered_output),
        )
    else:
        provider = OllamaInterviewProvider(
            base_url="http://localhost:11434",
            model="exact",
            timeout=2,
            transport=Transport(tampered_output),
        )

    with pytest.raises(ReflectionGenerationRejected) as exc:
        provider.generate_reflection(context)
    assert exc.value.reason_code == "invalid_wire_root_keys"
