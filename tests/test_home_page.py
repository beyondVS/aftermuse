from datetime import date

import pytest
from django.urls import reverse

from books.models import Book
from readings.models import Reading
from reflections.models import Interview, InterviewTurn


@pytest.mark.django_db
def test_home_page_contains_progressive_enhancement_assets(client) -> None:
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<main id="main-content"' in content
    assert "static/vendor/htmx.min.js" in content
    assert "static/vendor/alpine.min.js" in content
    assert 'hx-get="/setup-status/"' in content
    assert "x-data" in content


@pytest.mark.django_db
def test_htmx_request_returns_only_setup_partial(client) -> None:
    response = client.get(reverse("setup-status"), headers={"HX-Request": "true"})
    content = response.content.decode()

    assert response.status_code == 200
    assert '<section id="setup-status"' in content
    assert "<html" not in content
    assert "<main" not in content


@pytest.mark.django_db
def test_home_page_enforces_same_origin_csp(client) -> None:
    response = client.get(reverse("home"))
    policy = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy
    assert "img-src 'self' data: https:" in policy
    assert "'unsafe-eval'" not in policy


@pytest.mark.django_db
def test_authenticated_home_with_no_readings_shows_empty_state_and_search_link(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="empty-reader")
    client.force_login(user)

    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    # FR-001, SC-001: Sample mockups are removed
    assert "대니얼 카너먼" not in content
    assert "생각에 관한 생각" not in content
    assert "68% 완독 중" not in content
    assert "공리주의가 다수의 행복을 계산할 때" not in content

    # FR-002: Empty state with search link
    assert reverse("books:search") in content
    assert "책 찾아보기" in content


@pytest.mark.django_db
def test_authenticated_home_shows_currently_reading_and_ready_for_reflection_cards(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="active-reader")
    client.force_login(user)

    book_reading = Book.objects.create(
        isbn13="9788932917245",
        title="읽는 중인 도서",
        authors="작가 일번",
    )
    book_want = Book.objects.create(
        isbn13="9788932917246",
        title="읽고 싶은 도서",
        authors="작가 이번",
    )
    book_completed = Book.objects.create(
        isbn13="9788932917247",
        title="완독한 도서",
        authors="작가 삼번",
    )

    reading_active = Reading.objects.create(
        user=user, book=book_reading, status=Reading.Status.READING
    )
    reading_want = Reading.objects.create(
        user=user, book=book_want, status=Reading.Status.WANT_TO_READ
    )
    reading_completed = Reading.objects.create(
        user=user,
        book=book_completed,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )

    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200

    # Section 1: 지금 읽고 있는 책
    assert "지금 읽고 있는 책" in content
    assert "읽는 중인 도서" in content
    assert "읽고 싶은 도서" in content
    assert "읽는 중" in content
    assert "읽고 싶음" in content
    assert reverse("readings:detail", args=[reading_active.pk]) in content
    assert reverse("readings:detail", args=[reading_want.pk]) in content
    assert "독서 기록 계속하기" in content

    # Section 2: 사색을 기다리는 책
    assert "사색을 기다리는 책" in content
    assert "완독한 도서" in content
    assert "완독" in content
    # FR-004, SC-002: Directly links to reflections:interview_start, NOT books:search
    assert (
        reverse("reflections:interview_start", args=[reading_completed.pk]) in content
    )
    assert "AI 독서노트 만들기" in content


@pytest.mark.django_db
def test_home_page_reflects_reading_status_change(client, django_user_model) -> None:
    user = django_user_model.objects.create_user(username="changing-reader")
    client.force_login(user)

    book = Book.objects.create(
        isbn13="9788932917248",
        title="상태가 바뀌는 도서",
        authors="작가 사번",
    )
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.READING
    )

    # Initially READING
    response1 = client.get(reverse("home"))
    content1 = response1.content.decode()
    assert reverse("readings:detail", args=[reading.pk]) in content1
    assert reverse("reflections:interview_start", args=[reading.pk]) not in content1

    # Transition to COMPLETED
    reading.status = Reading.Status.COMPLETED
    reading.completed_on = date.today()
    reading.save()

    # Re-visit Home: Now COMPLETED without interview -> reflections:interview_start
    response2 = client.get(reverse("home"))
    content2 = response2.content.decode()
    assert reverse("reflections:interview_start", args=[reading.pk]) in content2
    assert "AI 독서노트 만들기" in content2


@pytest.mark.django_db
def test_multiple_readings_maintain_correct_links_and_order(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="multi-reader")
    client.force_login(user)

    book1 = Book.objects.create(isbn13="9788932917251", title="도서 하나")
    book2 = Book.objects.create(isbn13="9788932917252", title="도서 둘")

    reading1 = Reading.objects.create(
        user=user, book=book1, status=Reading.Status.READING
    )
    reading2 = Reading.objects.create(
        user=user, book=book2, status=Reading.Status.READING
    )

    response = client.get(reverse("home"))
    content = response.content.decode()

    # Both books are present with their own distinct detail links
    assert reverse("readings:detail", args=[reading1.pk]) in content
    assert reverse("readings:detail", args=[reading2.pk]) in content

    # Newest updated appears first (reading2 was created after reading1)
    pos1 = content.find(reverse("readings:detail", args=[reading1.pk]))
    pos2 = content.find(reverse("readings:detail", args=[reading2.pk]))
    assert pos2 < pos1


@pytest.mark.django_db
def test_home_cards_accessibility_and_state_presentation(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="a11y-reader")
    client.force_login(user)

    book = Book.objects.create(
        isbn13="9788932917253",
        title="접근성 테스트 도서",
        authors="접근성 작가",
    )
    Reading.objects.create(user=user, book=book, status=Reading.Status.READING)

    response = client.get(reverse("home"))
    content = response.content.decode()

    # Accessible link text / aria-label
    assert f'aria-label="《{book.title}》 독서 기록 계속하기"' in content or (
        "독서 기록 계속하기" in content and "접근성 테스트 도서" in content
    )
    # Color-independent textual status indication
    assert "읽는 중" in content


@pytest.mark.django_db
def test_home_page_shows_in_progress_interview_with_stage_and_resume_link(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="interview-reader")
    client.force_login(user)

    book = Book.objects.create(
        isbn13="9788932917254",
        title="진행 중인 도서",
        authors="인터뷰 작가",
    )
    reading = Reading.objects.create(
        user=user,
        book=book,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    interview = Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="첫 번째 질문입니다?",
    )

    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    # FR-005: In-progress interview card with book and stage
    assert "진행 중인 인터뷰" in content
    assert "진행 중인 도서" in content
    assert "1번째 질문 답변 대기" in content
    assert reverse("reflections:interview_detail", args=[interview.pk]) in content
    assert "인터뷰 이어하기" in content

    # FR-007: Same reading does NOT show a duplicate start card under 사색을 기다리는 책
    assert reverse("reflections:interview_start", args=[reading.pk]) not in content


@pytest.mark.django_db
def test_home_page_excludes_ready_and_completed_interviews_from_resume(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="completed-interview-reader")
    client.force_login(user)

    book_ready = Book.objects.create(
        isbn13="9788932917255",
        title="준비 완료 도서",
        authors="작가 오번",
    )
    reading_ready = Reading.objects.create(
        user=user,
        book=book_ready,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    Interview.objects.create(
        reading=reading_ready,
        book=book_ready,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )

    book_done = Book.objects.create(
        isbn13="9788932917256",
        title="완료된 도서",
        authors="작가 육번",
    )
    reading_done = Reading.objects.create(
        user=user,
        book=book_done,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    Interview.objects.create(
        reading=reading_done,
        book=book_done,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.COMPLETED,
    )

    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    # Neither should appear in '진행 중인 인터뷰'
    assert "진행 중인 인터뷰" not in content
    assert "인터뷰 이어하기" not in content
    # Neither should appear in '사색을 기다리는 책' (since interview exists)
    assert (
        reverse("reflections:interview_start", args=[reading_ready.pk]) not in content
    )
    assert reverse("reflections:interview_start", args=[reading_done.pk]) not in content


@pytest.mark.django_db
def test_anonymous_home_does_not_expose_any_user_reading_or_interview(
    client, django_user_model
) -> None:
    user = django_user_model.objects.create_user(username="private-reader")
    book = Book.objects.create(isbn13="9788932917257", title="비공개 독서 도서")
    reading = Reading.objects.create(
        user=user,
        book=book,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    interview = Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )

    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "비공개 독서 도서" not in content
    assert reverse("readings:detail", args=[reading.pk]) not in content
    assert reverse("reflections:interview_start", args=[reading.pk]) not in content
    assert reverse("reflections:interview_detail", args=[interview.pk]) not in content
    assert "독서 기록 계속하기" not in content
    assert "인터뷰 이어하기" not in content
    assert "AI 독서노트 만들기" not in content


@pytest.mark.django_db
def test_user_isolation_between_different_accounts(client, django_user_model) -> None:
    user_a = django_user_model.objects.create_user(username="user-a")
    user_b = django_user_model.objects.create_user(username="user-b")

    book_a = Book.objects.create(isbn13="9788932917258", title="사용자 A의 독서")
    book_b = Book.objects.create(isbn13="9788932917259", title="사용자 B의 독서")

    reading_a = Reading.objects.create(
        user=user_a, book=book_a, status=Reading.Status.READING
    )
    reading_b = Reading.objects.create(
        user=user_b,
        book=book_b,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    interview_b = Interview.objects.create(
        reading=reading_b,
        book=book_b,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )

    # User A login
    client.force_login(user_a)
    response_a = client.get(reverse("home"))
    content_a = response_a.content.decode()

    assert "사용자 A의 독서" in content_a
    assert reverse("readings:detail", args=[reading_a.pk]) in content_a
    assert "사용자 B의 독서" not in content_a
    assert reverse("readings:detail", args=[reading_b.pk]) not in content_a
    assert (
        reverse("reflections:interview_detail", args=[interview_b.pk]) not in content_a
    )

    # User B login
    client.force_login(user_b)
    response_b = client.get(reverse("home"))
    content_b = response_b.content.decode()

    assert "사용자 B의 독서" in content_b
    assert reverse("reflections:interview_detail", args=[interview_b.pk]) in content_b
    assert "사용자 A의 독서" not in content_b
    assert reverse("readings:detail", args=[reading_a.pk]) not in content_b


@pytest.mark.django_db
def test_home_page_queries_do_not_scale_with_card_count(
    client, django_user_model, django_assert_num_queries
) -> None:
    user = django_user_model.objects.create_user(username="perf-reader")
    client.force_login(user)

    # 1. Create 1 book, 1 reading, and 1 interview
    book1 = Book.objects.create(isbn13="9788932917260", title="성능 도서 1")
    r1 = Reading.objects.create(
        user=user,
        book=book1,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    interview1 = Interview.objects.create(
        reading=r1,
        book=book1,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    InterviewTurn.objects.create(
        interview=interview1, sequence=1, question="질문 1입니다?"
    )

    # Measure baseline query count
    # (session + user + reading/book + turns + decisions = 5)
    with django_assert_num_queries(5):
        client.get(reverse("home"))

    # 2. Add multiple readings and interviews
    for i in range(2, 7):
        book = Book.objects.create(isbn13=f"978893291726{i}", title=f"성능 도서 {i}")
        status = Reading.Status.READING if i % 2 == 0 else Reading.Status.COMPLETED
        r = Reading.objects.create(
            user=user,
            book=book,
            status=status,
            completed_on=date.today() if status == Reading.Status.COMPLETED else None,
        )
        if i % 2 == 1:
            inv = Interview.objects.create(
                reading=r,
                book=book,
                knowledge_readiness=Interview.KnowledgeReadiness.READY,
                status=Interview.Status.IN_PROGRESS,
            )
            InterviewTurn.objects.create(
                interview=inv, sequence=1, question=f"질문 {i}입니다?"
            )

    # Even with many more readings and interviews,
    # the query count must remain exactly 5 (no N+1)!
    with django_assert_num_queries(5):
        client.get(reverse("home"))
