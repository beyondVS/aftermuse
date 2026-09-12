from datetime import date

import pytest
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

from books.models import Book
from integrations.llm.contracts import (
    ProposedNextQuestion,
    QuestionGenerationConfigurationError,
    QuestionGenerationTimeout,
)
from integrations.llm.fake import FakeNextQuestionProvider
from readings.models import Reading
from reflections.models import Interview, InterviewTurn
from reflections.services import FirstAnswerPersistenceError, InterviewPolicyError


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
    assert "준비 수준: READY_LIMITED" in start_response.content.decode()
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
    client.post(first_answer_url, {"answer": "한 장면이 남았습니다"})

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
    assert "생각이 충분히 정리되었습니다" in result.content.decode()
    assert "다음 질문 다시 준비하기" not in detail.content.decode()
    assert "생각이 충분히 정리되었습니다" in detail.content.decode()
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
