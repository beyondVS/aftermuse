from datetime import date

import pytest
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

from books.models import Book
from integrations.llm.contracts import QuestionGenerationTimeout
from readings.models import Reading
from reflections.models import Interview, InterviewTurn


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

    assert 'id="first-question-title"' in content
    assert "무엇이 가장 오래 남았나요?" in content
    assert 'for="id_answer"' in content
    assert 'id="id_answer"' in content
    assert 'aria-describedby="answer-help"' in content
    assert 'id="answer-help"' in content
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
    assert "다음 질문" not in fragment.content.decode()
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
