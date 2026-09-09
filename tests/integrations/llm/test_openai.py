from datetime import date
from types import SimpleNamespace

import httpx2 as httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from integrations.llm.contracts import (
    InterviewQuestionContext,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
    QuestionGenerationUnavailable,
    QuestionPolicy,
)
from integrations.llm.openai import OpenAIQuestionProvider


class RecordingClient:
    """네트워크 없이 Responses request를 검증할 수 있는 client fake다."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.responses = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text='{"question":"어떤 장면이 남았나요?"}')


class FixedResponseClient(RecordingClient):
    """특정 Responses 결과를 반환하는 오류 경계 테스트용 client다."""

    def __init__(self, response) -> None:
        super().__init__()
        self._response = response

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class UnavailableClient(RecordingClient):
    """Provider 장애를 재현하는 network 없는 client다."""

    def create(self, **kwargs):
        raise RuntimeError("provider internal detail")


def test_responses_adapter_uses_strict_schema_and_policy_boundary() -> None:
    client = RecordingClient()
    context = InterviewQuestionContext(
        book_title="검증 책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=date(2026, 9, 9),
        knowledge_readiness="READY",
        knowledge_claims=("검증된 Claim",),
        policy=QuestionPolicy.KNOWLEDGE_GROUNDED,
    )

    result = OpenAIQuestionProvider(
        api_key="test-key", model="pinned-model", timeout=30, client=client
    ).generate_first_question(context)

    request = client.calls[0]
    assert result.question == "어떤 장면이 남았나요?"
    assert request["model"] == "pinned-model"
    assert request["store"] is False
    assert "tools" not in request
    assert request["text"] == {
        "format": {
            "type": "json_schema",
            "name": "first_question",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
                "additionalProperties": False,
            },
        }
    }
    assert "검증된 Claim" in request["input"]
    assert "검증된 Context Claim" in request["instructions"]


def test_limited_policy_does_not_promote_knowledge_claims_to_prompt() -> None:
    client = RecordingClient()
    context = InterviewQuestionContext(
        book_title="제한 책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )

    OpenAIQuestionProvider(
        api_key="test-key", model="pinned-model", timeout=30, client=client
    ).generate_first_question(context)

    assert "책의 사실이나 내용을 전제하지 말고" in client.calls[0]["instructions"]
    assert client.calls[0]["input"].endswith('"knowledge_claims": []}')


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(
            status="incomplete", output_text='{"question":"중단된 질문인가요?"}'
        ),
        SimpleNamespace(status="completed", output_text=""),
        SimpleNamespace(status="completed", output_text="not-json"),
    ],
)
def test_adapter_rejects_incomplete_empty_or_invalid_output(response) -> None:
    context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )

    with pytest.raises(QuestionGenerationRejected):
        OpenAIQuestionProvider(
            api_key="test-key",
            model="pinned-model",
            timeout=30,
            client=FixedResponseClient(response),
        ).generate_first_question(context)


def test_adapter_converts_unexpected_provider_failure_without_detail_leakage() -> None:
    context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )

    with pytest.raises(QuestionGenerationUnavailable) as error:
        OpenAIQuestionProvider(
            api_key="test-key",
            model="pinned-model",
            timeout=30,
            client=UnavailableClient(),
        ).generate_first_question(context)

    assert str(error.value) == ""


@pytest.mark.parametrize(
    ("provider_error", "expected_error"),
    [
        (
            APITimeoutError(
                httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            QuestionGenerationTimeout,
        ),
        (
            APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com/v1/responses")
            ),
            QuestionGenerationUnavailable,
        ),
        (
            RateLimitError(
                "sensitive provider body",
                response=httpx.Response(
                    429, request=httpx.Request("POST", "https://api.openai.com")
                ),
                body={"detail": "secret"},
            ),
            QuestionGenerationUnavailable,
        ),
        (
            APIStatusError(
                "sensitive provider body",
                response=httpx.Response(
                    500, request=httpx.Request("POST", "https://api.openai.com")
                ),
                body={"detail": "secret"},
            ),
            QuestionGenerationUnavailable,
        ),
    ],
)
def test_adapter_converts_sdk_errors_without_provider_detail(
    provider_error, expected_error
) -> None:
    context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )
    client = UnavailableClient()
    client.create = lambda **kwargs: (_ for _ in ()).throw(provider_error)

    with pytest.raises(expected_error) as error:
        OpenAIQuestionProvider(
            api_key="test-key", model="pinned-model", timeout=30, client=client
        ).generate_first_question(context)

    assert str(error.value) == ""


def test_adapter_rejects_refusal_and_uses_fixed_timeout_without_retries(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class CapturingClient(RecordingClient):
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)
            super().__init__()

    monkeypatch.setattr("integrations.llm.openai.OpenAI", CapturingClient)
    provider = OpenAIQuestionProvider(
        api_key="test-key", model="pinned-model", timeout=30
    )
    context = InterviewQuestionContext(
        book_title="책",
        authors="저자",
        publisher="출판사",
        reading_status="COMPLETED",
        completed_on=None,
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )
    provider._client = FixedResponseClient(
        SimpleNamespace(status="completed", output_text=None)
    )

    with pytest.raises(QuestionGenerationRejected):
        provider.generate_first_question(context)

    assert captured["timeout"] == 30
    assert captured["max_retries"] == 0
