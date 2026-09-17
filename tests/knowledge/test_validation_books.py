import pytest
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command

from accounts.models import User
from books.models import Book
from knowledge.models import BookKnowledge
from knowledge.services import (
    BookKnowledgeReadiness,
    get_book_knowledge_readiness,
    prepare_validation_books,
)
from readings.models import Reading
from reflections.models import Interview, Reflection

VALIDATION_BOOKS_DESCRIPTOR = (
    ("9780452284234", "1984", "fiction", BookKnowledgeReadiness.READY, 4),
    (
        "9780374275631",
        "Thinking, Fast and Slow",
        "nonfiction",
        BookKnowledgeReadiness.READY,
        4,
    ),
    (
        "9780143111597",
        "The Left Hand of Darkness",
        "fiction",
        BookKnowledgeReadiness.READY_LIMITED,
        0,
    ),
)


@pytest.mark.django_db
def test_prepare_validation_books_service_from_empty_db() -> None:
    """빈 DB에서 서비스 실행 시 정확히 3권 생성 및 8개 Claim이 준비된다."""
    assert Book.objects.count() == 0
    assert BookKnowledge.objects.count() == 0

    result = prepare_validation_books()

    assert result.books_created == 3
    assert result.books_reused == 0
    assert result.claims_created == 8
    assert result.claims_reused == 0

    assert Book.objects.count() == 3
    assert BookKnowledge.objects.count() == 8

    for (
        isbn13,
        _title,
        _genre,
        expected_readiness,
        expected_claim_count,
    ) in VALIDATION_BOOKS_DESCRIPTOR:
        book = Book.objects.get(isbn13=isbn13)
        assert expected_claim_count == BookKnowledge.objects.filter(book=book).count()
        assert get_book_knowledge_readiness(book) == expected_readiness


@pytest.mark.django_db
def test_prepare_validation_books_is_idempotent() -> None:
    """연속 2회 실행 시 두 번째 실행에서는 신규 생성 0건 및 동일 상태로 수렴한다."""
    first_res = prepare_validation_books()
    assert first_res.books_created == 3
    assert first_res.claims_created == 8

    second_res = prepare_validation_books()
    assert second_res.books_created == 0
    assert second_res.books_reused == 3
    assert second_res.claims_created == 0
    assert second_res.claims_reused == 8

    assert Book.objects.count() == 3
    assert BookKnowledge.objects.count() == 8


@pytest.mark.django_db
def test_prepare_validation_books_preserves_existing_book_metadata() -> None:
    """이미 등록된 Book이 존재하면 서지정보를 덮어쓰지 않고 재사용한다."""
    custom_title = "조지 오웰 1984 커스텀 제목"
    custom_authors = "조지 오웰 / 박진 번역"
    Book.objects.create(
        isbn13="9780452284234",
        title=custom_title,
        authors=custom_authors,
    )

    result = prepare_validation_books()
    assert result.books_created == 2
    assert result.books_reused == 1

    book_1984 = Book.objects.get(isbn13="9780452284234")
    assert book_1984.title == custom_title
    assert book_1984.authors == custom_authors
    assert BookKnowledge.objects.filter(book=book_1984).count() == 4


@pytest.mark.django_db
def test_prepare_validation_books_aborts_if_limited_has_claims() -> None:
    """READY_LIMITED 대상 도서에 기존 Claim이 있으면 중단하고 전체 rollback한다."""
    # LIMITED 대상 책 생성 및 기존 Claim 등록
    limited_book = Book.objects.create(
        isbn13="9780143111597",
        title="The Left Hand of Darkness",
    )
    existing_claim = BookKnowledge.objects.create(
        book=limited_book,
        kind="theme",
        content="사전 등록된 불일치 클레임",
    )

    with pytest.raises((ValidationError, CommandError)):
        prepare_validation_books()

    # 기존 Claim은 삭제되지 않고 보존됨
    assert BookKnowledge.objects.filter(pk=existing_claim.pk).exists()
    # 롤백으로 인해 다른 2권의 Book 및 Claim은 생성되지 않음
    assert Book.objects.filter(isbn13="9780452284234").count() == 0
    assert Book.objects.filter(isbn13="9780374275631").count() == 0


@pytest.mark.django_db
def test_prepare_validation_books_does_not_modify_user_data() -> None:
    """사용자 Reading, Interview, Reflection 데이터는 일체 변경되지 않는다."""
    user = User.objects.create_user(username="validation-test-user")
    user_book = Book.objects.create(isbn13="9788932917999", title="사용자 개인 도서")
    reading = Reading.objects.create(
        user=user, book=user_book, status=Reading.Status.READING
    )
    interview = Interview.objects.create(
        reading=reading,
        book=user_book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="# 초안 내용",
        draft_sections=[],
        status=Reflection.Status.DRAFT,
    )

    prepare_validation_books()

    # 사용자 관련 데이터 무변경 확인
    reading.refresh_from_db()
    interview.refresh_from_db()
    reflection.refresh_from_db()
    assert reading.status == Reading.Status.READING
    assert interview.status == Interview.Status.REFLECTION_READY
    assert reflection.status == Reflection.Status.DRAFT
    assert reading.book_id == user_book.pk


@pytest.mark.django_db
def test_prepare_validation_books_management_command(capsys) -> None:
    """management command로 실행 시 정상 완료 메시지를 출력한다."""
    call_command("prepare_validation_books")

    captured = capsys.readouterr()
    assert (
        "검증 도서 준비 완료" in captured.out
        or "Validation Books 준비 완료" in captured.out
    )
    assert Book.objects.count() == 3
    assert BookKnowledge.objects.count() == 8
