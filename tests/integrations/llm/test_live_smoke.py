"""명시적으로 선택한 경우에만 실제 LLM 연결을 확인한다."""

import os
from datetime import date

import pytest
from django.urls import reverse

from books.models import Book
from integrations.llm.contracts import (
    AnswerAnalysisContext,
    CurrentCoverageItem,
    InterviewQuestionContext,
    NextQuestionContext,
    QuestionPolicy,
)
from integrations.llm.gemini import GeminiInterviewProvider
from integrations.llm.ollama import OllamaInterviewProvider
from readings.models import Reading
from reflections.models import Interview
from reflections.services import (
    _validate_answer_analysis,
    _validate_first_question,
    _validate_next_question,
)

pytestmark = pytest.mark.live


def _context():
    return InterviewQuestionContext(
        "테스트 책",
        "",
        "",
        "COMPLETED",
        None,
        "READY_LIMITED",
        (),
        QuestionPolicy.MEMORY_CENTERED,
    )


def _smoke_three_tasks(provider):
    """실제 모델에서 중첩 배열과 nullable 후속 질문까지 확인한다."""
    context = _context()
    first = provider.generate_first_question(context)
    question = _validate_first_question(first.question)
    coverage = tuple(
        CurrentCoverageItem(axis, "UNCOVERED")
        for axis in ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT")
    )
    answer = "푸른 표지가 기억에 남았어요. 차분한 느낌이 들었어요."
    analysis = provider.analyze_answer(
        AnswerAnalysisContext(context, question, answer, coverage)
    )
    validated = _validate_answer_analysis(
        analysis, answer, {item.axis: item.status for item in coverage}
    )
    projected = {item.axis: item.status for item in coverage}
    for change in validated.coverage_patch:
        projected[change.axis.value] = change.status.value
    next_context = NextQuestionContext(
        context,
        (),
        question,
        answer,
        validated.meaning,
        validated.low_information,
        tuple(CurrentCoverageItem(axis, status) for axis, status in projected.items()),
    )
    next_question = provider.generate_next_question(next_context)
    _validate_next_question(next_question, next_context)
    assert next_question.kind == "question"
    assert isinstance(next_question.question, str) and next_question.question.strip()


def test_gemini_live():
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "")
    if not key or not model:
        pytest.skip("GEMINI_API_KEY or GEMINI_MODEL is not configured")
    provider = GeminiInterviewProvider(
        api_key=key,
        model=model,
        timeout=30,
    )
    _smoke_three_tasks(provider)
    context = _context()
    next_context = NextQuestionContext(
        context,
        (),
        "어떤 장면이 기억에 남았나요?",
        "잘 모르겠어요",
        None,
        True,
        tuple(
            CurrentCoverageItem(axis, "UNCOVERED")
            for axis in ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT")
        ),
    )
    proposal = provider.generate_next_question(next_context)
    assert proposal.kind == "question"
    _validate_next_question(proposal, next_context)


@pytest.mark.django_db
def test_gemini_interview_http_flow_live(client, settings, django_user_model):
    """실제 Provider를 HTTP view·Application 검증·테스트 DB 저장까지 연결한다."""
    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        pytest.skip("Gemini is not configured")
    settings.LLM_PROVIDER = "gemini"
    user = django_user_model.objects.create_user(username="live-interview")
    book = Book.objects.create(isbn13="9788937834796", title="테스트 책")
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    interview = Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    client.force_login(user)
    first = client.post(
        reverse("reflections:first_question", args=[interview.pk]),
        HTTP_HX_REQUEST="true",
    )
    assert first.status_code == 200
    answer = "푸른 표지가 기억에 남았어요. 차분한 느낌이 들었어요."
    saved = client.post(
        reverse("reflections:turn_answer", args=[interview.pk, 1]),
        {"answer": answer},
        HTTP_HX_REQUEST="true",
    )
    assert saved.status_code == 200
    next_url = reverse("reflections:next_turn", args=[interview.pk, 1])
    generated = client.post(next_url, HTTP_HX_REQUEST="true")
    assert generated.status_code == 200
    assert interview.turns.get(sequence=1).answer == answer
    assert interview.turns.get(sequence=2).answer is None
    repeated = client.post(next_url, HTTP_HX_REQUEST="true")
    assert repeated.status_code == 200
    assert interview.turns.count() == 2


def test_ollama_live():
    model = os.environ.get("OLLAMA_MODEL", "")
    if os.environ.get("OLLAMA_LIVE_TEST") != "1" or not model:
        pytest.skip("OLLAMA_LIVE_TEST or OLLAMA_MODEL is not configured")
    provider = OllamaInterviewProvider(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        model=model,
        timeout=120,
    )
    _smoke_three_tasks(provider)
