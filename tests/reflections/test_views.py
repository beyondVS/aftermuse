from datetime import date
from urllib.error import HTTPError

import pytest
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from books.models import Book
from integrations.llm.contracts import (
    AnswerAnalysisRejected,
    ProposedNextQuestion,
    QuestionGenerationConfigurationError,
    QuestionGenerationRejected,
    QuestionGenerationTimeout,
)
from integrations.llm.fake import FakeNextQuestionProvider
from readings.models import Reading
from reflections.models import Interview, InterviewProgressDecision, InterviewTurn
from reflections.services import (
    FirstAnswerPersistenceError,
    InterviewPolicyError,
    NextTurnPersistenceError,
    NextTurnStaleError,
)


@pytest.fixture(autouse=True)
def default_fake_llm_provider(settings) -> None:
    settings.LLM_PROVIDER = "fake"


@pytest.mark.parametrize(
    "error_type",
    [
        AnswerAnalysisRejected,
        QuestionGenerationRejected,
        NextTurnPersistenceError,
        NextTurnStaleError,
    ],
)
def test_next_failure_logs_types_without_sensitive_messages(
    client, reading, monkeypatch, caplog, error_type
):
    """503 진단 로그는 원문 대신 chain 타입을 제공하고 답변을 보존한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="보존할 답변",
    )
    secret = "credential-and-provider-answer-must-stay-private"

    def fail(**kwargs):
        try:
            raise ValueError(secret)
        except ValueError as cause:
            raise error_type(secret) from cause

    monkeypatch.setattr("reflections.views.process_next_turn", fail)
    client.force_login(reading.user)
    response = client.post(
        reverse("reflections:next_turn", args=[interview.pk, 1]), HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 503
    assert "실패 사유:" in response.content.decode()
    assert "다음 질문 다시 준비하기" in response.content.decode()
    assert error_type.__name__ in caplog.text and "ValueError" in caplog.text
    assert f"interview_id={interview.pk} sequence=1" in caplog.text
    assert "stage=next" in caplog.text
    assert secret not in caplog.text and secret not in response.content.decode()
    assert turn.answer not in caplog.text
    turn.refresh_from_db()
    assert turn.answer == "보존할 답변"


@pytest.mark.parametrize("htmx", [True, False])
def test_analysis_validation_reason_is_visible_and_logged(
    client, reading, monkeypatch, caplog, htmx
):
    """동일 상태 제안의 안전한 진단은 fragment와 전체 화면 모두 제공한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=3,
        question="무엇이 남았나요?",
        answer="저장된 답변",
    )

    def fail(**kwargs):
        raise AnswerAnalysisRejected(
            "private provider response", reason_code="analysis_non_increasing_coverage"
        )

    monkeypatch.setattr("reflections.views.process_next_turn", fail)
    client.force_login(reading.user)
    response = client.post(
        reverse("reflections:next_turn", args=[interview.pk, 3]),
        **({"HTTP_HX_REQUEST": "true"} if htmx else {}),
    )
    body = response.content.decode()
    assert response.status_code == 503
    assert "이미 반영된 상태와 같거나 낮은" in body
    assert "analysis_non_increasing_coverage" in body and "질문 3" in body
    assert "reason=analysis_non_increasing_coverage" in caplog.text
    assert "private provider response" not in body + caplog.text
    turn.refresh_from_db()
    assert turn.answer == "저장된 답변"


def test_first_failure_logs_safe_exception_chain(client, reading, monkeypatch, caplog):
    """첫 질문 실패도 후속 질문과 동일한 비노출 진단 계약을 따른다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )

    def fail(**kwargs):
        raise QuestionGenerationTimeout("private provider details")

    monkeypatch.setattr("reflections.views.ensure_first_question", fail)
    client.force_login(reading.user)
    response = client.post(
        reverse("reflections:first_question", args=[interview.pk]),
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 503
    assert "stage=first" in caplog.text and "QuestionGenerationTimeout" in caplog.text
    assert "private provider details" not in caplog.text
    assert "private provider details" not in response.content.decode()


def test_pipeline_log_preserves_http_status_without_response_body(caplog):
    """HTTP 오류의 상태만 추적하며 Provider 메시지와 header는 기록하지 않는다."""
    from reflections.views import _log_pipeline_failure

    error = HTTPError("http://private-provider", 500, "private error", {}, None)
    _log_pipeline_failure("first", 12, 1, error)
    assert "HTTPError[status=500]" in caplog.text
    assert "private-provider" not in caplog.text and "private error" not in caplog.text


def test_fake_first_answer_analysis_next_and_idempotent_retry(client, reading):
    """세 LLM 작업과 실제 ORM 상태 전이를 연결하고 재제출 시 Turn을 재사용한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    client.force_login(reading.user)
    first = client.post(
        reverse("reflections:first_question", args=[interview.pk]),
        HTTP_HX_REQUEST="true",
    )
    assert first.status_code == 200
    saved = client.post(
        reverse("reflections:turn_answer", args=[interview.pk, 1]),
        {"answer": "푸른 표지가 기억에 남았어요. 차분한 느낌이 들었어요."},
        HTTP_HX_REQUEST="true",
    )
    assert saved.status_code == 200
    url = reverse("reflections:next_turn", args=[interview.pk, 1])
    next_response = client.post(url, HTTP_HX_REQUEST="true")
    repeated = client.post(url, HTTP_HX_REQUEST="true")
    assert next_response.status_code == repeated.status_code == 200
    assert interview.turns.count() == 2
    first_turn = interview.turns.get(sequence=1)
    assert first_turn.answer == "푸른 표지가 기억에 남았어요. 차분한 느낌이 들었어요."
    assert interview.turns.get(sequence=2).answer is None


def test_pending_soft_stop_hides_candidate_and_continue_uses_it(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    for sequence in range(1, 4):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=sequence,
            question=f"{sequence}번째 질문은 무엇인가요?",
            answer=f"{sequence}번째 답변입니다.",
        )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="기억에 남는 것은 무엇인가요?",
        answer="장면이 기억에 남습니다.",
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="비공개로 보류한 질문은 무엇인가요?",
    )
    client.force_login(reading.user)
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))
    assert detail.status_code == 200
    assert "조금 더 이야기하기" in detail.content.decode()
    assert "비공개로 보류한" not in detail.content.decode()
    url = reverse("reflections:interview_decision", args=[interview.pk, 4])
    continued = client.post(url, {"decision": "continue"}, HTTP_HX_REQUEST="true")
    assert continued.status_code == 200
    assert "비공개로 보류한" in continued.content.decode()
    assert InterviewTurn.objects.filter(interview=interview).count() == 5


def test_cap_choice_rejects_stale_continue_but_allows_end(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        coverage={
            "MEMORY": "COVERED",
            "REACTION": "COVERED",
            "CONNECTION": "COVERED",
            "AFTERTHOUGHT": "UNCOVERED",
        },
    )
    for sequence in range(1, 9):
        turn = InterviewTurn.objects.create(
            interview=interview,
            sequence=sequence,
            question=f"{sequence}번째 질문은 무엇인가요?",
            answer=f"{sequence}번째 답변입니다.",
        )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
        candidate_question="다음 질문은 무엇인가요?",
        candidate_focus_axis="AFTERTHOUGHT",
    )
    Interview.objects.filter(pk=interview.pk).update(
        coverage=dict.fromkeys(interview.coverage, "COVERED")
    )
    client.force_login(reading.user)
    url = reverse("reflections:interview_decision", args=[interview.pk, 8])
    denied = client.post(url, {"decision": "continue"}, HTTP_HX_REQUEST="true")
    assert denied.status_code == 409
    assert "다음 질문은 무엇인가요?" not in denied.content.decode()
    ended = client.post(url, {"decision": "end"})
    assert ended.status_code == 302
    interview.refresh_from_db()
    assert interview.status == Interview.Status.REFLECTION_READY


def test_decision_end_ready_and_owner_boundary(
    client, reading, django_user_model
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="무엇인가요?",
        answer="생각입니다.",
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="다음 질문은 무엇인가요?",
    )
    url = reverse("reflections:interview_decision", args=[interview.pk, 4])
    other = django_user_model.objects.create_user(username="day08-other")
    client.force_login(other)
    assert client.post(url, {"decision": "end"}).status_code == 404
    client.force_login(reading.user)
    ended = client.post(url, {"decision": "end"})
    assert ended.status_code == 302
    ready = client.get(ended.url)
    assert ready.status_code == 200
    assert "독서노트를 준비할 수 있어요" in ready.content.decode()
    assert client.post(url, {"decision": "end"}).status_code == 302
    assert client.post(url, {"decision": "continue"}).status_code == 409


def test_cap_choice_and_legacy_skip_get_is_read_only(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=8,
        question="무엇인가요?",
        answer="생각입니다.",
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
        candidate_question="보류된 다음 질문은 무엇인가요?",
    )
    client.force_login(reading.user)
    detail_url = reverse("reflections:interview_detail", args=[interview.pk])
    pending = client.get(detail_url)
    assert "최대 두 문항 더 이야기하기" in pending.content.decode()
    assert "보류된 다음 질문" not in pending.content.decode()
    InterviewProgressDecision.objects.filter(turn=turn).delete()
    turn.next_question_skipped_at = timezone.now()
    turn.save(update_fields=("next_question_skipped_at", "updated_at"))
    ready = client.get(detail_url)
    interview.refresh_from_db()
    assert ready.status_code == 200
    assert "독서노트를 준비할 수 있어요" in ready.content.decode()
    assert interview.status == Interview.Status.IN_PROGRESS


def test_decision_failure_keeps_answer_and_retryable_htmx_region(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="무엇인가요?",
        answer="보존된 답변",
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="보류 질문은 무엇인가요?",
    )
    client.force_login(reading.user)
    monkeypatch.setattr(
        "reflections.views.decide_interview_progress",
        lambda **kwargs: (_ for _ in ()).throw(NextTurnPersistenceError()),
    )
    response = client.post(
        reverse("reflections:interview_decision", args=[interview.pk, 4]),
        {"decision": "continue"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 503
    assert "작성한 답변은 저장되어 있습니다" in response.content.decode()
    assert response.headers["HX-Retarget"] == "#interview-turn-region"
    assert InterviewTurn.objects.get(pk=turn.pk).answer == "보존된 답변"


@pytest.fixture
def reading(django_user_model) -> Reading:
    user = django_user_model.objects.create_user(username="interview-view")
    book = Book.objects.create(isbn13="9788937834796", title="Interview 화면")
    return Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )


def test_confirmation_get_is_side_effect_free_and_post_starts_interview(
    client, reading
) -> None:
    client.force_login(reading.user)
    start_url = reverse("reflections:interview_start", args=[reading.pk])

    response = client.get(start_url)
    created = client.post(reverse("reflections:interview_create", args=[reading.pk]))

    assert response.status_code == 200
    assert (
        "인터뷰를 시작하면 다른 책으로 변경할 수 없습니다." in response.content.decode()
    )
    assert Interview.objects.count() == 1
    assert created.status_code == 302
    assert created.url == reverse(
        "reflections:interview_detail", args=[Interview.objects.get().pk]
    )


def test_owner_and_csrf_boundaries_and_existing_status(
    client, reading, django_user_model
) -> None:
    other = django_user_model.objects.create_user(username="interview-other")
    client.force_login(other)
    assert (
        client.get(
            reverse("reflections:interview_start", args=[reading.pk])
        ).status_code
        == 404
    )
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(reading.user)
    assert (
        csrf_client.post(
            reverse("reflections:interview_create", args=[reading.pk])
        ).status_code
        == 403
    )
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        status=Interview.Status.COMPLETED,
    )
    client.force_login(reading.user)
    unavailable = client.get(reverse("reflections:interview_start", args=[reading.pk]))
    assert unavailable.status_code == 409
    assert interview.pk == Interview.objects.get(reading=reading).pk


def test_non_completed_reading_has_no_start_action_or_created_interview(
    client, reading
) -> None:
    reading.status = Reading.Status.READING
    reading.completed_on = None
    reading.save()
    client.force_login(reading.user)
    start_url = reverse("reflections:interview_start", args=[reading.pk])

    response = client.get(start_url)
    created = client.post(reverse("reflections:interview_create", args=[reading.pk]))

    assert response.status_code == 400
    assert "인터뷰 시작</button>" not in response.content.decode()
    assert created.status_code == 400
    assert Interview.objects.filter(reading=reading).count() == 0


def test_start_page_renders_only_available_metadata_and_accessible_actions(
    client, reading
) -> None:
    reading.book.authors = "저자"
    reading.book.publisher = "출판사"
    reading.book.save()
    client.force_login(reading.user)

    content = client.get(
        reverse("reflections:interview_start", args=[reading.pk])
    ).content.decode()

    assert content.count("<h1") == 1
    assert "<dt>제목</dt>" in content
    assert "<dt>저자</dt>" in content
    assert "<dt>출판사</dt>" in content
    assert "<dt>출간일</dt>" not in content
    assert "<dt>ISBN13</dt>" in content
    assert 'href="/books/search/"' in content
    assert "인터뷰 시작</button>" in content


def test_limited_guidance_and_retry_error_are_exposed_safely(
    client, reading, monkeypatch
) -> None:
    client.force_login(reading.user)
    start_url = reverse("reflections:interview_start", args=[reading.pk])
    assert "기억에 남은 내용부터 정리" in client.get(start_url).content.decode()
    monkeypatch.setattr(
        "reflections.views.start_interview",
        lambda **kwargs: (_ for _ in ()).throw(DatabaseError()),
    )

    response = client.post(reverse("reflections:interview_create", args=[reading.pk]))

    assert response.status_code == 400
    assert 'role="alert"' in response.content.decode()
    assert 'tabindex="-1" autofocus' in response.content.decode()
    assert "잠시 후 다시 시도해 주세요." in response.content.decode()


@pytest.mark.parametrize(
    "status",
    [Interview.Status.REFLECTION_READY, Interview.Status.COMPLETED],
)
def test_existing_non_interview_status_is_a_safe_unavailable_response(
    client, reading, status
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=status,
    )
    client.force_login(reading.user)

    response = client.get(reverse("reflections:interview_detail", args=[interview.pk]))

    if status == Interview.Status.REFLECTION_READY:
        assert response.status_code == 200
        assert "독서노트를 준비할 수 있어요" in response.content.decode()
    else:
        assert response.status_code == 409
        assert "아직 사용할 수 없습니다" in response.content.decode()


def test_corrupted_interview_relationship_is_not_routed(client, reading) -> None:
    other_book = Book.objects.create(isbn13="9788937834797", title="손상된 연결")
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    Interview.objects.filter(pk=interview.pk).update(book=other_book)
    client.force_login(reading.user)

    response = client.get(reverse("reflections:interview_detail", args=[interview.pk]))

    assert response.status_code == 400
    assert "인터뷰 정보" in response.content.decode()


def test_corrupted_interview_cannot_be_reentered_or_changed(client, reading) -> None:
    other_book = Book.objects.create(isbn13="9788937834798", title="손상된 시작 연결")
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    Interview.objects.filter(pk=interview.pk).update(book=other_book)
    client.force_login(reading.user)

    start_url = reverse("reflections:interview_start", args=[reading.pk])
    get_response = client.get(start_url)
    post_response = client.post(
        reverse("reflections:interview_create", args=[reading.pk])
    )
    detail_response = client.get(
        reverse("reflections:interview_detail", args=[interview.pk])
    )

    assert [
        response.status_code
        for response in (get_response, post_response, detail_response)
    ] == [400, 400, 400]
    assert Interview.objects.filter(reading=reading).count() == 1
    assert Interview.objects.get(pk=interview.pk).book_id == other_book.pk


def test_start_and_detail_method_and_html_contracts(client, reading) -> None:
    client.force_login(reading.user)
    start_url = reverse("reflections:interview_start", args=[reading.pk])
    create_url = reverse("reflections:interview_create", args=[reading.pk])

    start_response = client.get(start_url)
    created = client.post(create_url)
    detail_response = client.get(created.url)

    assert client.post(start_url).status_code == 405
    assert client.get(create_url).status_code == 405
    assert "기억에 남은 내용부터 정리해 볼게요" in start_response.content.decode()
    assert "준비 수준" not in start_response.content.decode()
    assert "READY_LIMITED" not in start_response.content.decode()
    assert 'role="alert"' not in start_response.content.decode()
    assert created.status_code == 302
    assert "첫 질문을 준비하고 있어요." in detail_response.content.decode()
    assert Interview.objects.get(reading=reading).turns.count() == 0


def test_detail_loading_and_first_question_post_contract(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    client.force_login(reading.user)
    detail_url = reverse("reflections:interview_detail", args=[interview.pk])
    question_url = reverse("reflections:first_question", args=[interview.pk])

    loading = client.get(detail_url)
    fragment = client.post(question_url, HTTP_HX_REQUEST="true")
    repeated = client.post(question_url)

    assert loading.status_code == 200
    assert 'id="interview-turn-region"' in loading.content.decode()
    assert 'aria-busy="true"' in loading.content.decode()
    assert 'hx-trigger="load delay:100ms, submit"' in loading.content.decode()
    assert 'hx-sync="this:drop"' in loading.content.decode()
    assert "hx-disabled-elt=\"find button[type='submit']\"" in loading.content.decode()
    assert fragment.status_code == 200
    assert "가장 오래 남은 장면" in fragment.content.decode()
    assert repeated.status_code == 302
    assert repeated.url == detail_url
    assert InterviewTurn.objects.filter(interview=interview, sequence=1).count() == 1


def test_first_question_reuse_and_policy_conflict_ignore_provider_configuration(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 가장 오래 남았나요?"
    )
    client.force_login(reading.user)
    question_url = reverse("reflections:first_question", args=[interview.pk])
    monkeypatch.setattr(
        "reflections.views.get_question_provider",
        lambda: (_ for _ in ()).throw(QuestionGenerationConfigurationError()),
    )

    reused = client.post(question_url, HTTP_HX_REQUEST="true")
    interview.status = Interview.Status.COMPLETED
    interview.save(update_fields=("status", "updated_at"))
    conflict = client.post(question_url, HTTP_HX_REQUEST="true")

    assert reused.status_code == 200
    assert "무엇이 가장 오래 남았나요?" in reused.content.decode()
    assert conflict.status_code == 409
    assert conflict.headers["HX-Retarget"] == "#interview-turn-region"


def test_question_state_exposes_accessible_answer_form(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 가장 오래 남았나요?"
    )
    client.force_login(reading.user)

    content = client.get(
        reverse("reflections:interview_detail", args=[interview.pk])
    ).content.decode()

    assert 'id="current-question-title"' in content
    assert "무엇이 가장 오래 남았나요?" in content
    assert 'for="id_answer"' in content
    assert 'id="id_answer"' in content
    assert 'aria-describedby="answer-help"' in content
    assert 'id="answer-help"' in content
    assert content.count('id="interview-turn-region"') == 1
    assert 'hx-post="/reflections/interviews/' in content
    assert 'hx-target="#interview-turn-region"' in content
    assert 'type="submit"' in content
    assert "data-answer-submission" in content


def test_first_answer_post_returns_saved_fragment_or_detail_redirect(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 가장 오래 남았나요?"
    )
    client.force_login(reading.user)
    answer_url = reverse("reflections:first_answer", args=[interview.pk])
    detail_url = reverse("reflections:interview_detail", args=[interview.pk])

    fragment = client.post(
        answer_url, {"answer": "처음 적은 답변"}, HTTP_HX_REQUEST="true"
    )
    redirected = client.post(answer_url, {"answer": "처음 적은 답변"})

    assert fragment.status_code == 200
    assert "답변을 저장했습니다" in fragment.content.decode()
    assert "다음 질문을 준비하고 있어요" in fragment.content.decode()
    assert redirected.status_code == 302
    assert redirected.url == detail_url


def test_question_generation_error_returns_retryable_alert(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    client.force_login(reading.user)
    monkeypatch.setattr(
        "reflections.views.get_question_provider",
        lambda: (_ for _ in ()).throw(QuestionGenerationTimeout()),
    )

    response = client.post(
        reverse("reflections:first_question", args=[interview.pk]),
        HTTP_HX_REQUEST="true",
    )

    content = response.content.decode()
    assert response.status_code == 503
    assert 'role="alert"' in content
    assert 'tabindex="-1"' in content
    assert "첫 질문 다시 준비하기" in content
    assert InterviewTurn.objects.filter(interview=interview).count() == 0
    assert response.headers["HX-Retarget"] == "#interview-turn-region"
    assert response.headers["HX-Reswap"] == "outerHTML"
    assert response.headers["HX-Trigger-After-Settle"] == "interviewTurnSettled"


def test_interview_routes_hide_non_owned_or_missing_resources(
    client, reading, django_user_model
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?"
    )
    other = django_user_model.objects.create_user(username="interview-route-other")
    client.force_login(other)

    for name in ("interview_detail", "first_question", "first_answer"):
        url = reverse(f"reflections:{name}", args=[interview.pk])
        response = client.get(url) if name == "interview_detail" else client.post(url)
        missing_url = reverse(f"reflections:{name}", args=[999999])
        missing = (
            client.get(missing_url)
            if name == "interview_detail"
            else client.post(missing_url)
        )
        assert response.status_code == missing.status_code == 404


def test_answer_errors_swap_bound_form_and_preserve_input(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?"
    )
    client.force_login(reading.user)
    answer_url = reverse("reflections:first_answer", args=[interview.pk])

    invalid = client.post(answer_url, {"answer": "   "}, HTTP_HX_REQUEST="true")
    invalid_content = invalid.content.decode()
    assert invalid.status_code == 400
    assert invalid.headers["HX-Retarget"] == "#interview-turn-region"
    assert invalid.headers["HX-Reswap"] == "outerHTML"
    assert 'aria-describedby="answer-help id_answer-error"' in invalid_content
    assert 'data-interview-focus="true"' in invalid_content

    monkeypatch.setattr(
        "reflections.views.save_first_answer",
        lambda **kwargs: (_ for _ in ()).throw(FirstAnswerPersistenceError()),
    )
    failed = client.post(
        answer_url, {"answer": "다시 제출할 원문"}, HTTP_HX_REQUEST="true"
    )
    failed_content = failed.content.decode()
    assert failed.status_code == 503
    assert "다시 제출할 원문" in failed_content
    assert 'id="answer-form-error"' in failed_content
    assert failed.headers["HX-Trigger-After-Settle"] == "interviewTurnSettled"


def test_answer_conflict_and_csrf_keep_the_safe_contract(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="확정된 원문",
    )
    answer_url = reverse("reflections:first_answer", args=[interview.pk])
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(reading.user)
    assert csrf_client.post(answer_url, {"answer": "새 원문"}).status_code == 403

    client.force_login(reading.user)
    conflict = client.post(answer_url, {"answer": "새 원문"}, HTTP_HX_REQUEST="true")
    assert conflict.status_code == 409
    assert conflict.headers["HX-Retarget"] == "#interview-turn-region"
    assert "확정된 원문" in conflict.content.decode()


def test_anonymous_interview_routes_redirect_to_login(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    for name in ("interview_detail", "first_question", "first_answer"):
        url = reverse(f"reflections:{name}", args=[interview.pk])
        response = client.get(url) if name == "interview_detail" else client.post(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url


def test_question_post_rejects_csrf_and_unavailable_status(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        status=Interview.Status.COMPLETED,
    )
    question_url = reverse("reflections:first_question", args=[interview.pk])
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(reading.user)
    assert csrf_client.post(question_url).status_code == 403

    client.force_login(reading.user)
    assert client.post(question_url).status_code == 409


def test_policy_conflicts_replace_htmx_interview_region_safely(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question=" multiline-policy-secret "
    )
    client.force_login(reading.user)
    question_url = reverse("reflections:first_question", args=[interview.pk])
    answer_url = reverse("reflections:first_answer", args=[interview.pk])

    def reject_policy(**kwargs):
        raise InterviewPolicyError("internal-policy-detail")

    monkeypatch.setattr("reflections.views.ensure_first_question", reject_policy)
    question = client.post(question_url, HTTP_HX_REQUEST="true")
    question_page = client.post(question_url)
    monkeypatch.setattr("reflections.views.save_first_answer", reject_policy)
    answer = client.post(
        answer_url, {"answer": "보존 대상이 아닌 입력"}, HTTP_HX_REQUEST="true"
    )
    answer_page = client.post(answer_url, {"answer": "보존 대상이 아닌 입력"})

    for response in (question, answer):
        content = response.content.decode()
        assert response.status_code == 409
        assert response.headers["HX-Retarget"] == "#interview-turn-region"
        assert response.headers["HX-Reswap"] == "outerHTML"
        assert response.headers["HX-Trigger-After-Settle"] == "interviewTurnSettled"
        assert content.count('id="interview-turn-region"') == 1
        assert 'role="alert"' in content
        assert "현재 단계를 사용할 수 없습니다" in content
        assert "internal-policy-detail" not in content
        assert "보존 대상이 아닌 입력" not in content

    for response in (question_page, answer_page):
        content = response.content.decode()
        assert response.status_code == 409
        assert "현재 단계를 아직 사용할 수 없습니다" in content
        assert "internal-policy-detail" not in content
        assert "보존 대상이 아닌 입력" not in content


def test_answer_next_question_and_second_answer_flow(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?"
    )
    client.force_login(reading.user)
    first_answer_url = reverse("reflections:first_answer", args=[interview.pk])
    saved_fragment = client.post(
        first_answer_url, {"answer": "한 장면이 남았습니다"}, HTTP_HX_REQUEST="true"
    )
    assert 'hx-trigger="load delay:100ms, submit"' in saved_fragment.content.decode()
    assert 'hx-sync="this:drop"' in saved_fragment.content.decode()
    assert (
        "hx-disabled-elt=\"find button[type='submit']\""
        in saved_fragment.content.decode()
    )

    next_url = reverse("reflections:next_turn", args=[interview.pk, 1])
    fragment = client.post(next_url, HTTP_HX_REQUEST="true")
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))

    assert fragment.status_code == 200
    assert "2번째 질문" in fragment.content.decode()
    assert "2번째 질문" in detail.content.decode()
    assert "한 장면이 남았습니다" in detail.content.decode()
    assert (
        "<blockquote>한 장면이 남았습니다</blockquote>" not in detail.content.decode()
    )
    second_answer_url = reverse("reflections:turn_answer", args=[interview.pk, 2])
    saved = client.post(second_answer_url, {"answer": "그 장면이 저를 떠올리게 했어요"})
    assert saved.status_code == 302
    assert InterviewTurn.objects.get(interview=interview, sequence=2).answer == (
        "그 장면이 저를 떠올리게 했어요"
    )


def test_skipped_next_question_is_distinct_from_retryable_error(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="생각이 남았어요",
    )
    client.force_login(reading.user)
    next_url = reverse("reflections:next_turn", args=[interview.pk, 1])

    def unavailable(**kwargs):
        raise QuestionGenerationTimeout()

    monkeypatch.setattr("reflections.views.process_next_turn", unavailable)
    failed = client.post(next_url, HTTP_HX_REQUEST="true")
    assert failed.status_code == 503
    assert "작성한 답변은 저장되어 있습니다" in failed.content.decode()
    assert "다음 질문 다시 준비하기" in failed.content.decode()
    turn.refresh_from_db()
    assert turn.answer == "생각이 남았어요"
    assert turn.next_question_skipped_at is None


def test_skipped_question_reentry_shows_waiting_without_retry(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        coverage=dict.fromkeys(
            ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT"), "COVERED"
        ),
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="생각이 남았지만 더 할 말이 없어요",
    )
    client.force_login(reading.user)
    monkeypatch.setattr(
        "integrations.llm.factory.get_next_question_provider",
        lambda: FakeNextQuestionProvider(
            result=ProposedNextQuestion(
                "skip",
                None,
                None,
                None,
                "네 방향은 다뤘고 지금 답변에서 더 탐색할 근거가 없습니다.",
            )
        ),
    )
    next_url = reverse("reflections:next_turn", args=[interview.pk, 1])

    result = client.post(next_url, HTTP_HX_REQUEST="true")
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))
    repeated = client.post(next_url, HTTP_HX_REQUEST="true")

    assert result.status_code == 200
    assert "독서노트를 준비할 수 있어요" in result.content.decode()
    assert "다음 질문 다시 준비하기" not in detail.content.decode()
    assert "독서노트를 준비할 수 있어요" in detail.content.decode()
    assert repeated.status_code == 200
    turn.refresh_from_db()
    assert turn.next_question_skipped_at is not None
    assert interview.turns.count() == 1


def test_next_turn_rejects_invalid_answer_without_server_error(client, reading) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?", answer="원문"
    )
    InterviewTurn.objects.filter(pk=turn.pk).update(answer="")
    client.force_login(reading.user)

    response = client.post(
        reverse("reflections:next_turn", args=[interview.pk, 1]),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 409
    assert "현재 단계를 사용할 수 없습니다" in response.content.decode()


def test_new_turn_routes_hide_other_users_interview(
    client, reading, django_user_model
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="무엇이 남았나요?", answer="내 답변"
    )
    other = django_user_model.objects.create_user(username="other-interview-user")
    answer_url = reverse("reflections:turn_answer", args=[interview.pk, 1])
    next_url = reverse("reflections:next_turn", args=[interview.pk, 1])

    for url in (answer_url, next_url):
        assert client.post(url).status_code == 302
    client.force_login(other)
    for url in (answer_url, next_url):
        response = client.post(url, {"answer": "훔친 답변"})
        assert response.status_code == 404
        assert "내 답변" not in response.content.decode()


def test_interview_detail_resume_pre_first_question_preserves_state(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    client.force_login(reading.user)

    for _ in range(2):
        response = client.get(
            reverse("reflections:interview_detail", args=[interview.pk])
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "첫 질문을 준비하고 있어요." in content
        assert "첫 질문 준비하기" in content

    assert Interview.objects.count() == 1
    assert InterviewTurn.objects.filter(interview=interview).count() == 0


def test_interview_detail_resume_unanswered_turn_preserves_question(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="처음 읽을 때 인상 깊었던 장면은 무엇인가요?",
    )
    client.force_login(reading.user)

    for _ in range(2):
        response = client.get(
            reverse("reflections:interview_detail", args=[interview.pk])
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "1번째 질문" in content
        assert "처음 읽을 때 인상 깊었던 장면은 무엇인가요?" in content
        assert "답변 저장하기" in content

    turn.refresh_from_db()
    assert turn.answer is None
    assert InterviewTurn.objects.filter(interview=interview).count() == 1


def test_interview_detail_resume_answered_turn_preserves_answer_without_reentry(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="처음 읽을 때 인상 깊었던 장면은 무엇인가요?",
        answer="주인공이 결심하는 장면이 인상적이었습니다.",
    )
    client.force_login(reading.user)

    for _ in range(2):
        response = client.get(
            reverse("reflections:interview_detail", args=[interview.pk])
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "답변을 저장했습니다" in content
        assert "주인공이 결심하는 장면이 인상적이었습니다." in content
        assert "다음 질문 준비하기" in content
        assert "답변 저장하기" not in content

    turn.refresh_from_db()
    assert turn.answer == "주인공이 결심하는 장면이 인상적이었습니다."
    assert InterviewTurn.objects.filter(interview=interview).count() == 1


def test_interview_detail_resume_pending_decision_preserves_choices(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="네 번째 질문입니다?",
        answer="네 번째 답변입니다.",
    )
    decision = InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="다섯 번째 보류 질문입니다?",
    )
    client.force_login(reading.user)

    for _ in range(2):
        response = client.get(
            reverse("reflections:interview_detail", args=[interview.pk])
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert "조금 더 이야기하기" in content
        assert "독서노트 준비하기" in content
        assert "다섯 번째 보류 질문입니다?" not in content

    decision.refresh_from_db()
    assert decision.selection is None
    assert InterviewTurn.objects.filter(interview=interview).count() == 1


def test_interview_detail_resume_after_error_preserves_answer_and_retries(
    client, reading, monkeypatch
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="첫 번째 질문입니다?",
        answer="소중한 첫 답변입니다.",
    )
    client.force_login(reading.user)

    def failing_analyze(*args, **kwargs):
        raise QuestionGenerationTimeout()

    monkeypatch.setattr(
        "reflections.views.process_next_turn",
        failing_analyze,
    )

    error_response = client.post(
        reverse("reflections:next_turn", args=[interview.pk, 1]),
        HTTP_HX_REQUEST="true",
    )
    assert error_response.status_code == 503
    assert "다음 질문을 준비하지 못했습니다" in error_response.content.decode()

    resume_response = client.get(
        reverse("reflections:interview_detail", args=[interview.pk])
    )
    assert resume_response.status_code == 200
    content = resume_response.content.decode()
    assert "소중한 첫 답변입니다." in content
    assert "답변을 저장했습니다" in content
    assert "다음 질문 준비하기" in content

    turn.refresh_from_db()
    assert turn.answer == "소중한 첫 답변입니다."
    assert InterviewTurn.objects.filter(interview=interview).count() == 1


def test_interview_detail_resume_multiple_turns_preserves_previous_answers(
    client, reading
) -> None:
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    turn1 = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="첫 번째 질문: 책의 핵심 메시지는 무엇인가요?",
        answer="주인공의 용기가 가장 큰 울림을 주었습니다.",
    )
    turn2 = InterviewTurn.objects.create(
        interview=interview,
        sequence=2,
        question="두 번째 질문: 어떤 장면에서 그 용기를 가장 크게 느꼈나요?",
    )
    client.force_login(reading.user)

    for _ in range(2):
        response = client.get(
            reverse("reflections:interview_detail", args=[interview.pk])
        )
        assert response.status_code == 200
        content = response.content.decode()

        # Previous turn question and confirmed answer are displayed
        assert "1번째 질문" in content
        assert "첫 번째 질문: 책의 핵심 메시지는 무엇인가요?" in content
        assert "주인공의 용기가 가장 큰 울림을 주었습니다." in content

        # Current uncompleted turn question and answer form are displayed
        assert "2번째 질문" in content
        assert "두 번째 질문: 어떤 장면에서 그 용기를 가장 크게 느꼈나요?" in content
        assert "답변 저장하기" in content

    # State invariants: no duplicate creation, no data mutation
    assert Interview.objects.count() == 1
    assert InterviewTurn.objects.filter(interview=interview).count() == 2
    turn1.refresh_from_db()
    turn2.refresh_from_db()
    assert turn1.answer == "주인공의 용기가 가장 큰 울림을 주었습니다."
    assert turn2.answer is None


# ---------------------------------------------------------------------------
# User Story 1 View Tests
# ---------------------------------------------------------------------------


def test_reflection_generate_auth_and_ownership(
    client, reading, django_user_model
) -> None:
    """인증되지 않은 사용자는 로그인으로 redirect되고, 타인은 404를 받는다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문", answer="답변"
    )
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    # 1. Anonymous -> 302 login
    anon_res = client.post(url)
    assert anon_res.status_code == 302
    assert "/accounts/login/" in anon_res.url

    # 2. Other user -> 404
    other_user = django_user_model.objects.create_user(username="other-ref-gen-user")
    client.force_login(other_user)
    other_res = client.post(url)
    assert other_res.status_code == 404


def test_reflection_detail_auth_and_ownership(
    client, reading, django_user_model
) -> None:
    """최소 결과 화면은 소유자만 볼 수 있고 타인 및 익명은 접근할 수 없다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문", answer="답변"
    )
    from reflections.models import Reflection

    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="## 초안 본문",
        draft_sections=[
            {"title": "초안", "paragraphs": [{"text": "답변", "evidence": []}]}
        ],
        status=Reflection.Status.DRAFT,
    )
    url = reverse("reflections:reflection_detail", args=[reflection.pk])

    # 1. Anonymous -> 302 login
    anon_res = client.get(url)
    assert anon_res.status_code == 302

    # 2. Other user -> 404
    other_user = django_user_model.objects.create_user(username="other-ref-detail-user")
    client.force_login(other_user)
    other_res = client.get(url)
    assert other_res.status_code == 404

    # 3. Owner -> 200
    client.force_login(reading.user)
    owner_res = client.get(url)
    assert owner_res.status_code == 200


def test_reflection_generate_stale_or_invalid_status_returns_409(
    client, reading
) -> None:
    """REFLECTION_READY 상태가 아닌 Interview의 생성 요청은 409를 반환한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문", answer="답변"
    )
    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    res = client.post(url)
    assert res.status_code == 409


def test_reflection_generate_provider_failure_returns_503_and_retry_ui(
    client, reading, monkeypatch
) -> None:
    """Provider 실패 시 503과 재시도 UI를 제공하며 원본 답변을 보존한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문", answer="보존되어야 할 답변"
    )

    def mock_fail(**kwargs):
        from integrations.llm.contracts import ReflectionGenerationUnavailable

        raise ReflectionGenerationUnavailable("Provider is down")

    monkeypatch.setattr("reflections.drafts.generate_reflection_draft", mock_fail)

    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    # 1. Normal POST -> 503 with retry button
    res_normal = client.post(url)
    assert res_normal.status_code == 503
    content_normal = res_normal.content.decode()
    assert "다시 시도" in content_normal or "재시도" in content_normal
    assert "답변은 안전하게 보존" in content_normal or "보존" in content_normal

    # 2. HTMX POST -> 503 fragment with role="alert"
    res_htmx = client.post(url, HTTP_HX_REQUEST="true")
    assert res_htmx.status_code == 503
    content_htmx = res_htmx.content.decode()
    assert 'role="alert"' in content_htmx
    assert "다시 시도" in content_htmx or "재시도" in content_htmx

    turn.refresh_from_db()
    assert turn.answer == "보존되어야 할 답변"


def test_reflection_generate_success_redirects_and_creates_draft(
    client, reading
) -> None:
    """생성 성공 시 일반 요청은 302,
    HTMX 요청은 HX-Redirect로 최소 결과 URL로 이동한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문", answer="생성 근거가 될 답변"
    )
    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    # 1. Normal POST
    res = client.post(url)
    assert res.status_code == 302
    from reflections.models import Reflection

    reflection = Reflection.objects.get(interview=interview)
    expected_url = reverse("reflections:reflection_detail", args=[reflection.pk])
    assert res.url == expected_url

    # 2. HTMX POST with existing reflection -> HX-Redirect
    res_htmx = client.post(url, HTTP_HX_REQUEST="true")
    assert res_htmx.status_code == 200
    assert res_htmx.headers.get("HX-Redirect") == expected_url


def test_reflection_detail_screen_scope(client, reading) -> None:
    """Day 12 결과 화면은 책 제목, 본문 에세이 및 수정/완료 액션을 제공하고,
    수정용 textarea는 상세 화면에 노출하지 않는다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    from reflections.models import Reflection

    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown=("## 독서노트 본문\n\n이 본문은 결과 화면에 정상 노출된다."),
        draft_sections=[{"title": "초안", "paragraphs": []}],
        status=Reflection.Status.DRAFT,
    )
    client.force_login(reading.user)
    url = reverse("reflections:reflection_detail", args=[reflection.pk])

    res = client.get(url)
    assert res.status_code == 200
    content = res.content.decode()

    # 표시되어야 할 항목: 도서명, 본문, 작성 중 상태
    assert reading.book.title in content
    assert "독서노트 본문" in content
    assert "작성 중" in content

    # 수정 textarea는 상세가 아닌 edit 화면에 위치해야 함
    assert "<textarea" not in content


def test_skip_turn_auth_and_ownership(client, reading, other_reflection_user) -> None:
    """인증되지 않은 사용자는 로그인으로 이동하고,
    타인의 인터뷰 skip 요청은 404를 반환한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(interview=interview, sequence=1, question="질문 1")
    url = reverse("reflections:turn_skip", args=[interview.pk, 1])

    # 1. Anonymous user
    res_anon = client.post(url)
    assert res_anon.status_code == 302
    assert "/accounts/login/" in res_anon.url

    # 2. Non-owner user
    client.force_login(other_reflection_user)
    res_non_owner = client.post(url)
    assert res_non_owner.status_code == 404


def test_skip_turn_stale_or_invalid_sequence_returns_409(client, reading) -> None:
    """이미 완료/답변된 turn, 또는 terminal 인터뷰 skip 요청은 409를 반환한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문 1", answer="이미 답변 완료"
    )
    InterviewTurn.objects.create(interview=interview, sequence=2, question="질문 2")
    client.force_login(reading.user)

    # 1. 이미 답변된 1번 turn에 skip 요청 -> 409
    url_stale = reverse("reflections:turn_skip", args=[interview.pk, 1])
    res1 = client.post(url_stale)
    assert res1.status_code == 409

    # 2. terminal 인터뷰 skip 요청 -> 409
    interview.status = Interview.Status.REFLECTION_READY
    interview.save(update_fields=("status", "updated_at"))
    url_terminal = reverse("reflections:turn_skip", args=[interview.pk, 2])
    res2 = client.post(url_terminal)
    assert res2.status_code == 409

    # 3. 존재하지 않는 turn은 404
    url_nonexistent = reverse("reflections:turn_skip", args=[interview.pk, 99])
    res3 = client.post(url_nonexistent)
    assert res3.status_code == 404


def test_skip_turn_provider_failure_returns_503_recovery_fragment(
    client, reading, monkeypatch
) -> None:
    """Provider 오류 시 503과 함께 재시도 가능한 복구 fragment를 반환하며,
    skip 사실은 보존된다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(interview=interview, sequence=1, question="질문 1")
    client.force_login(reading.user)
    url = reverse("reflections:turn_skip", args=[interview.pk, 1])

    from integrations.llm.contracts import QuestionGenerationUnavailable

    def fail_skip(**kwargs):
        raise QuestionGenerationUnavailable()

    monkeypatch.setattr("reflections.views.skip_interview_turn", fail_skip)

    res = client.post(url, HTTP_HX_REQUEST="true")
    assert res.status_code == 503
    content = res.content.decode()
    assert "다시 준비" in content or "다시 시도" in content or "재시도" in content


def test_skip_turn_htmx_and_normal_success_flow(client, reading) -> None:
    """정상 skip 시 일반 요청은 redirect되고,
    HTMX 요청은 다음 질문 fragment를 반환한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(interview=interview, sequence=1, question="질문 1")
    client.force_login(reading.user)
    url = reverse("reflections:turn_skip", args=[interview.pk, 1])

    # HTMX skip
    res = client.post(url, HTTP_HX_REQUEST="true")
    assert res.status_code == 200
    content = res.content.decode()
    assert (
        'id="interview-turn-region"' in content or 'data-turn-sequence="2"' in content
    )


def test_interview_detail_ended_no_reflection_screen(client, reading) -> None:
    """ENDED_NO_REFLECTION 상태의 인터뷰는
    reflection 없이 종료된 안내 화면을 렌더링한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.ENDED_NO_REFLECTION,
    )
    client.force_login(reading.user)
    url = reverse("reflections:interview_detail", args=[interview.pk])

    res = client.get(url)
    assert res.status_code == 200
    content = res.content.decode()
    assert "독서노트" in content
    assert "답변" in content


def test_interview_start_and_detail_hide_internal_enums_and_show_friendly_notice(
    client, reading
) -> None:
    """READY 및 READY_LIMITED 상태에서 내부 enum, RAG, Knowledge readiness,
    준비 수준이 노출되지 않고, 제한 상태에서는 친화적인 비오류 문구를 제공한다."""
    from knowledge.models import BookKnowledge, KnowledgeKind

    forbidden_strings = [
        "READY_LIMITED",
        "READY",
        "Knowledge readiness",
        "knowledge_readiness",
        "준비 수준",
        "RAG",
    ]

    # 1. READY_LIMITED: start view
    client.force_login(reading.user)
    start_url = reverse("reflections:interview_start", args=[reading.pk])
    res_start_limited = client.get(start_url)
    assert res_start_limited.status_code == 200
    start_limited_content = res_start_limited.content.decode()

    for forbidden in forbidden_strings:
        assert forbidden not in start_limited_content, (
            f"Found '{forbidden}' in start (READY_LIMITED)"
        )

    # 비오류 안내 문구 포함 확인 & alert 없음 확인
    assert "기억에 남은" in start_limited_content
    assert 'role="alert"' not in start_limited_content

    # 2. READY_LIMITED: detail view
    interview_limited = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        status=Interview.Status.IN_PROGRESS,
    )
    detail_url = reverse("reflections:interview_detail", args=[interview_limited.pk])
    res_detail_limited = client.get(detail_url)
    assert res_detail_limited.status_code == 200
    detail_limited_content = res_detail_limited.content.decode()

    for forbidden in forbidden_strings:
        assert forbidden not in detail_limited_content, (
            f"Found '{forbidden}' in detail (READY_LIMITED)"
        )

    assert "기억에 남은" in detail_limited_content
    assert 'role="alert"' not in detail_limited_content

    # 3. READY: start view
    BookKnowledge.objects.create(
        book=reading.book, kind=KnowledgeKind.THEME, content="검증된 지식 클레임"
    )
    other_reading = Reading.objects.create(
        user=reading.user,
        book=reading.book,
        status=Reading.Status.COMPLETED,
        completed_on=date(2026, 9, 15),
    )
    start_url_ready = reverse("reflections:interview_start", args=[other_reading.pk])
    res_start_ready = client.get(start_url_ready)
    assert res_start_ready.status_code == 200
    start_ready_content = res_start_ready.content.decode()

    for forbidden in forbidden_strings:
        assert forbidden not in start_ready_content, (
            f"Found '{forbidden}' in start (READY)"
        )
    assert 'role="alert"' not in start_ready_content

    # 4. READY: detail view
    interview_ready = Interview.objects.create(
        reading=other_reading,
        book=other_reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    detail_url_ready = reverse(
        "reflections:interview_detail", args=[interview_ready.pk]
    )
    res_detail_ready = client.get(detail_url_ready)
    assert res_detail_ready.status_code == 200
    detail_ready_content = res_detail_ready.content.decode()

    for forbidden in forbidden_strings:
        assert forbidden not in detail_ready_content, (
            f"Found '{forbidden}' in detail (READY)"
        )
    assert 'role="alert"' not in detail_ready_content


def test_cross_story_full_lifecycle_and_security_boundaries(
    client, reading, other_reflection_user
) -> None:
    """답변과 skip이 혼합된 인터뷰의 Reflection 생성, 중복 방지,
    all-skip 종결, 소유권 경계를 교차 검증한다."""
    from reflections.models import Reflection

    # 1. 혼합 상호작용 후 REFLECTION_READY 전이
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(
        interview=interview, sequence=1, question="1번 질문", answer="1번 답변"
    )
    turn2 = InterviewTurn.objects.create(
        interview=interview, sequence=2, question="2번 질문"
    )

    # 1-1. 비소유자 접근 차단 (404)
    client.force_login(other_reflection_user)
    skip_url = reverse("reflections:turn_skip", args=[interview.pk, 2])
    assert client.post(skip_url).status_code == 404

    # 1-2. 소유자 skip 실행
    client.force_login(reading.user)
    skip_res = client.post(skip_url)
    assert skip_res.status_code == 302
    turn2.refresh_from_db()
    assert turn2.user_skipped_at is not None
    assert turn2.answer is None

    # 1-3. 이미 skip된 turn에 답변 시도 (409)
    answer_url = reverse("reflections:turn_answer", args=[interview.pk, 2])
    conflict_answer = client.post(answer_url, {"answer": "뒤늦은 답변"})
    assert conflict_answer.status_code == 409

    # 1-4. REFLECTION_READY 상태로 전환
    interview.status = Interview.Status.REFLECTION_READY
    interview.save()

    # 2. Reflection 생성 흐름
    gen_url = reverse("reflections:reflection_generate", args=[interview.pk])

    # 2-1. 비소유자 생성 시도 차단 (404)
    client.force_login(other_reflection_user)
    assert client.post(gen_url).status_code == 404

    # 2-2. 소유자 생성 성공 및 단일 Reflection 확인
    client.force_login(reading.user)
    gen_res = client.post(gen_url)
    assert gen_res.status_code == 302
    assert Reflection.objects.filter(interview=interview).count() == 1
    reflection = Reflection.objects.get(interview=interview)
    assert gen_res.url == reverse("reflections:reflection_detail", args=[reflection.pk])

    # 2-3. 중복 생성 시도 시 기존 Reflection으로 수렴 (idempotent, 1개 유지)
    repeat_gen_res = client.post(gen_url)
    assert repeat_gen_res.status_code == 302
    assert repeat_gen_res.url == reverse(
        "reflections:reflection_detail", args=[reflection.pk]
    )
    assert Reflection.objects.filter(interview=interview).count() == 1

    # 2-4. Reflection 상세 화면 소유권 검증
    detail_url = reverse("reflections:reflection_detail", args=[reflection.pk])
    owner_view_res = client.get(detail_url)
    assert owner_view_res.status_code == 200
    assert "작성 중" in owner_view_res.content.decode()
    assert reading.book.title in owner_view_res.content.decode()

    client.force_login(other_reflection_user)
    assert client.get(detail_url).status_code == 404

    # 3. All-skip 종결 인터뷰의 Reflection 생성 거부 (409)
    all_skip_reading = Reading.objects.create(
        user=reading.user,
        book=reading.book,
        status=Reading.Status.COMPLETED,
        completed_on=date(2026, 9, 15),
    )
    all_skip_interview = Interview.objects.create(
        reading=all_skip_reading,
        book=all_skip_reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
        status=Interview.Status.ENDED_NO_REFLECTION,
    )
    client.force_login(reading.user)
    all_skip_gen_url = reverse(
        "reflections:reflection_generate", args=[all_skip_interview.pk]
    )
    assert client.post(all_skip_gen_url).status_code == 409
    assert Reflection.objects.filter(interview=all_skip_interview).count() == 0


def test_reflection_generate_with_unexpected_form_field_returns_409(
    client, reading
) -> None:
    """reflection_generate는 허용되지 않은 추가 form field가 포함된 POST에
    409를 반환한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])
    response = client.post(url, {"unexpected_field": "disallowed"})
    assert response.status_code == 409


def test_turn_skip_htmx_all_skip_returns_fragment_without_full_page(
    client, reading
) -> None:
    """all-skip 종결 시 HTMX skip 요청은 base.html이 포함되지 않은
    fragment를 반환한다."""
    from django.conf import settings

    normal_cap = settings.INTERVIEW_QUESTION_NORMAL_CAP

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    for seq in range(1, normal_cap):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=seq,
            question=f"질문 {seq}",
            user_skipped_at=timezone.now(),
        )
    last_turn = InterviewTurn.objects.create(
        interview=interview, sequence=normal_cap, question=f"질문 {normal_cap}"
    )
    client.force_login(reading.user)
    skip_url = reverse("reflections:turn_skip", args=[interview.pk, last_turn.sequence])

    res = client.post(skip_url, HTTP_HX_REQUEST="true")
    assert res.status_code == 200
    content = res.content.decode()

    # fragment 검증: turn-region 포함, 전체 HTML 뼈대(DOCTYPE/html) 없음
    assert 'id="interview-turn-region"' in content
    assert "<!DOCTYPE html>" not in content
    assert "<html" not in content
    assert "독서노트를 생성하지 않고 인터뷰를 종료했습니다" in content


def test_turn_skip_repeated_post_on_ended_no_reflection_converges_idempotently(
    client, reading
) -> None:
    """이미 ENDED_NO_REFLECTION 상태인 인터뷰의 마지막 건너뛴 turn에 대한 반복 POST는
    409 오류 없이 200 fragment(HTMX) 또는 redirect(일반)로 멱등 수렴한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.ENDED_NO_REFLECTION,
    )
    for seq in range(1, 8):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=seq,
            question=f"질문 {seq}",
            user_skipped_at=timezone.now(),
        )
    last_turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=8,
        question="질문 8",
        user_skipped_at=timezone.now(),
    )
    client.force_login(reading.user)
    skip_url = reverse("reflections:turn_skip", args=[interview.pk, last_turn.sequence])

    # HTMX 요청: 409가 아니라 200과 함께 종료 안내 fragment 반환
    res_htmx = client.post(skip_url, HTTP_HX_REQUEST="true")
    assert res_htmx.status_code == 200
    content = res_htmx.content.decode()
    assert 'id="interview-turn-region"' in content
    assert "독서노트를 생성하지 않고 인터뷰를 종료했습니다" in content

    # 일반 POST 요청: 409가 아니라 302 redirect
    res_normal = client.post(skip_url)
    assert res_normal.status_code == 302
    assert res_normal.url == reverse(
        "reflections:interview_detail", args=[interview.pk]
    )


def test_turn_skip_repeated_post_on_reflection_ready_converges_idempotently(
    client, reading
) -> None:
    """이미 REFLECTION_READY 상태인 인터뷰의 마지막 건너뛴 turn에 대한 반복 POST는
    409 오류 없이 200 fragment(HTMX) 또는 redirect(일반)로 멱등 수렴한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="질문 1",
        answer="답변 완료",
    )
    for seq in range(2, 8):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=seq,
            question=f"질문 {seq}",
            user_skipped_at=timezone.now(),
        )
    last_turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=8,
        question="질문 8",
        user_skipped_at=timezone.now(),
    )
    client.force_login(reading.user)
    skip_url = reverse("reflections:turn_skip", args=[interview.pk, last_turn.sequence])

    # HTMX 요청: 409가 아니라 200과 함께 reflection_ready fragment 반환
    res_htmx = client.post(skip_url, HTTP_HX_REQUEST="true")
    assert res_htmx.status_code == 200
    content = res_htmx.content.decode()
    assert 'id="interview-turn-region"' in content
    assert "독서노트를 준비할 수 있어요" in content

    # 일반 POST 요청: 409가 아니라 302 redirect
    res_normal = client.post(skip_url)
    assert res_normal.status_code == 302
    assert res_normal.url == reverse(
        "reflections:interview_detail", args=[interview.pk]
    )


def test_interview_decision_soft_stop_end_htmx_renders_reflection_generate_button(
    client, reading
) -> None:
    """HTMX Soft Stop END 선택 시 fragment에
    초안 생성 버튼과 올바른 form action이 포함된다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="기억에 남는 것은 무엇인가요?",
        answer="장면이 기억에 남습니다.",
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="보류된 질문은 무엇인가요?",
    )
    client.force_login(reading.user)
    url = reverse("reflections:interview_decision", args=[interview.pk, 4])
    response = client.post(url, {"decision": "end"}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    content = response.content.decode()
    assert 'id="interview-turn-region"' in content
    assert "독서노트를 준비할 수 있어요" in content
    assert "독서노트 초안 생성하기" in content
    expected_generate_url = reverse(
        "reflections:reflection_generate", args=[interview.pk]
    )
    assert f'action="{expected_generate_url}"' in content
    assert f'hx-post="{expected_generate_url}"' in content


def test_interview_detail_renders_soft_stop_on_skipped_turn_with_pending_decision(
    client, reading
) -> None:
    """Skip된 Turn에 pending SOFT_STOP이 있으면
    Soft Stop 선택 UI가 우선 표시된다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=4,
        question="건너뛴 질문입니다.",
        user_skipped_at=timezone.now(),
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="보류된 후보 질문입니다.",
    )
    client.force_login(reading.user)
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))
    assert detail.status_code == 200
    content = detail.content.decode()
    assert "생각이 충분히 모였어요" in content
    assert "독서노트 준비하기" in content
    assert "조금 더 이야기하기" in content
    assert "질문 건너뛰기 후 다음 단계를 준비하지 못했습니다" not in content


def test_interview_detail_renders_cap_extension_on_skipped_turn_with_pending_decision(
    client, reading
) -> None:
    """Skip된 Turn에 pending CAP_EXTENSION이 있으면
    CAP 선택 UI가 우선 표시된다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=8,
        question="건너뛴 8번째 질문입니다.",
        user_skipped_at=timezone.now(),
    )
    InterviewProgressDecision.objects.create(
        turn=turn,
        kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
        candidate_question="보류된 후보 질문입니다.",
    )
    client.force_login(reading.user)
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))
    assert detail.status_code == 200
    content = detail.content.decode()
    assert "여덟 개의 질문을 마쳤어요" in content
    assert "독서노트 준비하기" in content
    assert "최대 두 문항 더 이야기하기" in content
    assert "질문 건너뛰기 후 다음 단계를 준비하지 못했습니다" not in content


def test_interview_detail_renders_retry_ui_on_skipped_turn_without_decision(
    client, reading
) -> None:
    """Skip 저장 후 Provider 실패 상태(재진입)에서는
    기존 Retry UI가 유지된다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY_LIMITED,
    )
    InterviewTurn.objects.create(
        interview=interview,
        sequence=2,
        question="건너뛴 질문입니다.",
        user_skipped_at=timezone.now(),
    )
    client.force_login(reading.user)
    detail = client.get(reverse("reflections:interview_detail", args=[interview.pk]))
    assert detail.status_code == 200
    content = detail.content.decode()
    assert "질문 건너뛰기 후 다음 단계를 준비하지 못했습니다" in content
    assert "다음 질문 다시 준비하기" in content


def test_reflection_detail_owner_view_success_and_metadata(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown=(
            "# 초안 제목\n\n초안으로 작성된 본문 에세이입니다.\n\n- 첫 번째 생각"
        ),
        draft_sections=[{"title": "초안 제목", "paragraphs": []}],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    response = client.get(
        reverse("reflections:reflection_detail", args=[reflection.pk])
    )

    assert response.status_code == 200
    content = response.content.decode()

    # 1. 책 메타데이터 및 작성일
    assert reading.book.title in content
    if reading.book.authors:
        assert reading.book.authors in content
    assert "작성일" in content or reflection.created_at.strftime("%Y") in content

    # 2. Markdown 시맨틱 구조 렌더링
    assert "<h1>초안 제목</h1>" in content
    assert "<p>초안으로 작성된 본문 에세이입니다.</p>" in content
    assert "<li>첫 번째 생각</li>" in content

    # 3. DRAFT 상태 텍스트 및 행동 버튼
    assert "작성 중" in content
    assert reverse("reflections:reflection_edit", args=[reflection.pk]) in content
    assert (
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
        in content
    )
    assert reverse("home") in content

    # 4. AI 작성자/Chat transcript 비노출
    assert "AI 작성" not in content
    assert "Transcript" not in content
    assert "프롬프트" not in content


def test_reflection_detail_prefers_revised_markdown_when_available(
    client, reading
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 원래 AI 초안\n\n원래 초안 내용입니다.",
        revised_markdown="# 사용자가 수정한 제목\n\n직접 수정한 본문 내용입니다.",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    response = client.get(
        reverse("reflections:reflection_detail", args=[reflection.pk])
    )

    assert response.status_code == 200
    content = response.content.decode()

    # 수정본 내용 렌더링 확인
    assert "<h1>사용자가 수정한 제목</h1>" in content
    assert "<p>직접 수정한 본문 내용입니다.</p>" in content

    # 원본 초안은 렌더링되지 않음
    assert "원래 AI 초안" not in content
    assert "원래 초안 내용입니다." not in content


def test_reflection_detail_neutralizes_user_raw_html(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown=(
            "# 보안 테스트\n\n"
            "<script>alert('xss')</script>\n\n"
            '<img src="x" onerror="alert(1)">\n'
        ),
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    response = client.get(
        reverse("reflections:reflection_detail", args=[reflection.pk])
    )

    assert response.status_code == 200
    content = response.content.decode()

    # 실행 가능한 raw HTML 태그는 없어야 하고 entity escape 되어야 함
    assert "<script>" not in content
    assert "&lt;script&gt;" in content
    assert '<img src="x" onerror="alert(1)">' not in content
    assert "&lt;img" in content


def test_reflection_detail_completed_status_shows_label_and_hides_actions(
    client, reading
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.COMPLETED,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 완료된 독서노트\n\n완료된 본문입니다.",
        draft_sections=[],
        status=Reflection.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    client.force_login(reading.user)
    response = client.get(
        reverse("reflections:reflection_detail", args=[reflection.pk])
    )

    assert response.status_code == 200
    content = response.content.decode()

    # 1. 완료 상태 텍스트
    assert "완료" in content
    assert "작성 중" not in content

    # 2. 수정 및 완료 버튼 비노출
    assert reverse("reflections:reflection_edit", args=[reflection.pk]) not in content
    assert (
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
        not in content
    )

    # 3. Home 링크 존재
    assert reverse("home") in content


def test_reflection_detail_other_user_or_not_found_returns_404(
    client, reading, django_user_model
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 소유자 초안",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    # 타인 로그인 시 404
    other_user = django_user_model.objects.create_user(username="other-ref-viewer")
    client.force_login(other_user)
    response = client.get(
        reverse("reflections:reflection_detail", args=[reflection.pk])
    )
    assert response.status_code == 404

    # 존재하지 않는 ID 시 404
    response_404 = client.get(reverse("reflections:reflection_detail", args=[999999]))
    assert response_404.status_code == 404


def test_reflection_detail_query_count_is_bounded(
    client, reading, django_assert_num_queries
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 독서노트",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    # session (1) + auth user (1) + single select_related (1) = 3 queries
    with django_assert_num_queries(3):
        response = client.get(
            reverse("reflections:reflection_detail", args=[reflection.pk])
        )
        assert response.status_code == 200


def test_reflection_edit_get_draft_success(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 초안 내용입니다.",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    res = client.get(reverse("reflections:reflection_edit", args=[reflection.pk]))
    assert res.status_code == 200
    content = res.content.decode()

    # textarea에 초안 내용 포함 확인
    assert "<textarea" in content
    assert "# 초안 내용입니다." in content
    # 취소 링크 및 저장 버튼 확인
    assert reverse("reflections:reflection_detail", args=[reflection.pk]) in content
    assert "수정 저장" in content


def test_reflection_edit_get_completed_redirects_to_detail(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.COMPLETED,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 완료된 내용입니다.",
        draft_sections=[],
        status=Reflection.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    client.force_login(reading.user)
    res = client.get(reverse("reflections:reflection_edit", args=[reflection.pk]))
    assert res.status_code == 302
    assert res.url == reverse("reflections:reflection_detail", args=[reflection.pk])


def test_reflection_edit_post_valid_revision_redirects_and_saves(
    client, reading
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 원본 초안",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)
    new_text = "## 사용자가 직접 수정한 독서노트 내용입니다."
    res = client.post(
        reverse("reflections:reflection_edit", args=[reflection.pk]),
        {"markdown": new_text},
    )

    assert res.status_code == 302
    assert res.url == reverse("reflections:reflection_detail", args=[reflection.pk])

    reflection.refresh_from_db()
    assert reflection.revised_markdown == new_text
    assert reflection.draft_markdown == "# 원본 초안"
    assert reflection.status == Reflection.Status.DRAFT


def test_reflection_edit_post_validation_error_returns_400(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 원본 초안",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)

    # 1. 공백만 있는 본문 제출 시 400
    res_blank = client.post(
        reverse("reflections:reflection_edit", args=[reflection.pk]),
        {"markdown": "   \n\t  "},
    )
    assert res_blank.status_code == 400
    assert "본문은 공백만으로 구성될 수 없습니다." in res_blank.content.decode()

    # 2. 20,000자 초과 본문 제출 시 400
    res_overflow = client.post(
        reverse("reflections:reflection_edit", args=[reflection.pk]),
        {"markdown": "가" * 20001},
    )
    assert res_overflow.status_code == 400
    assert "20,000자를 초과할 수 없습니다." in res_overflow.content.decode()

    # DB는 여전히 수정되지 않음 확인
    reflection.refresh_from_db()
    assert reflection.revised_markdown is None


def test_reflection_edit_post_completed_rejected(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.COMPLETED,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 완료된 초안",
        draft_sections=[],
        status=Reflection.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    client.force_login(reading.user)
    res = client.post(
        reverse("reflections:reflection_edit", args=[reflection.pk]),
        {"markdown": "완료 후 수정 시도"},
    )
    # 완료본 수정 시도는 거부 (302 상세 이동 또는 400)
    assert res.status_code in (302, 400)
    reflection.refresh_from_db()
    assert reflection.revised_markdown is None


def test_reflection_complete_confirm_get_and_post(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 완료할 초안 내용",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    client.force_login(reading.user)

    # 1. GET 확인 화면
    res_get = client.get(
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
    )
    assert res_get.status_code == 200
    content_get = res_get.content.decode()
    assert "최종 완료" in content_get or "완료 확인" in content_get
    assert reverse("reflections:reflection_detail", args=[reflection.pk]) in content_get

    # 2. POST 완료 실행
    res_post = client.post(
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
    )
    assert res_post.status_code == 302
    assert res_post.url == reverse(
        "reflections:reflection_detail", args=[reflection.pk]
    )

    # Reflection과 Interview 모두 원자적으로 COMPLETED 전이 확인
    reflection.refresh_from_db()
    assert reflection.status == Reflection.Status.COMPLETED
    assert reflection.completed_at is not None

    interview.refresh_from_db()
    assert interview.status == Interview.Status.COMPLETED

    # 3. 중복 POST 멱등 확인
    res_repeat = client.post(
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
    )
    assert res_repeat.status_code == 302
    assert res_repeat.url == reverse(
        "reflections:reflection_detail", args=[reflection.pk]
    )


def test_reflection_complete_confirm_get_completed_redirects(client, reading) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.COMPLETED,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 완료된 내용",
        draft_sections=[],
        status=Reflection.Status.COMPLETED,
        completed_at=timezone.now(),
    )

    client.force_login(reading.user)
    res = client.get(
        reverse("reflections:reflection_complete_confirm", args=[reflection.pk])
    )
    assert res.status_code == 302
    assert res.url == reverse("reflections:reflection_detail", args=[reflection.pk])


def test_reflection_edit_and_complete_other_user_returns_404(
    client, reading, django_user_model
) -> None:
    from reflections.models import Reflection

    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 초안 내용",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    other_user = django_user_model.objects.create_user(username="other-editor")
    client.force_login(other_user)

    edit_url = reverse("reflections:reflection_edit", args=[reflection.pk])
    assert client.get(edit_url).status_code == 404
    assert client.post(edit_url, {"markdown": "해킹"}).status_code == 404

    complete_url = reverse(
        "reflections:reflection_complete_confirm", args=[reflection.pk]
    )
    assert client.get(complete_url).status_code == 404
    assert client.post(complete_url).status_code == 404
