import json
from pathlib import Path

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


@pytest.mark.django_db
def test_prepare_validation_books_fails_on_duplicate_isbn_in_descriptor(
    tmp_path: Path,
) -> None:
    """검증 도서 descriptor에 중복 ISBN13이 있으면 DB 쓰기 전에 실패하고

    부분 변경이 남지 않는다.
    """
    dup_descriptors = [
        {
            "isbn13": "9780452284234",
            "title": "1984 Fiction",
            "authors": "George Orwell",
            "genre": "fiction",
            "expected_readiness": "READY",
        },
        {
            "isbn13": "9780452284234",  # 중복 ISBN
            "title": "1984 Nonfiction",
            "authors": "George Orwell",
            "genre": "nonfiction",
            "expected_readiness": "READY",
        },
        {
            "isbn13": "9780143111597",
            "title": "The Left Hand of Darkness",
            "authors": "Ursula K. Le Guin",
            "genre": "fiction",
            "expected_readiness": "READY_LIMITED",
        },
    ]
    desc_file = tmp_path / "dup_validation_books.json"
    desc_file.write_text(json.dumps(dup_descriptors), encoding="utf-8")

    with pytest.raises(ValidationError, match="ISBN13은 서로 달라야 합니다"):
        prepare_validation_books(descriptor_path=desc_file)

    assert Book.objects.count() == 0
    assert BookKnowledge.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("claim_count", "match_text"),
    [
        (7, "정확히 8개"),
        (9, "정확히 8개"),
    ],
)
def test_prepare_validation_books_fails_on_missing_or_extra_claims(
    tmp_path: Path, claim_count: int, match_text: str
) -> None:
    """승인 Seed Claim 수가 8개가 아니면(누락/추가) DB 쓰기 전에 실패하고

    부분 변경이 남지 않는다.
    """
    base_claims = [
        {
            "book_isbn13": "9780452284234",
            "kind": "theme",
            "content": f"테마 클레임 {i}",
        }
        for i in range(claim_count)
    ]
    for i in range(claim_count // 2):
        base_claims[i]["book_isbn13"] = "9780374275631"

    claims_file = tmp_path / f"claims_{claim_count}.json"
    claims_file.write_text(json.dumps(base_claims), encoding="utf-8")

    with pytest.raises(ValidationError, match=match_text):
        prepare_validation_books(seed_path=claims_file)

    assert Book.objects.count() == 0
    assert BookKnowledge.objects.count() == 0


@pytest.mark.django_db
def test_prepare_validation_books_fails_on_invalid_claim_target(
    tmp_path: Path,
) -> None:
    """승인 Seed Claim에 무관한 도서의 Claim이 포함되면 DB 쓰기 전에 실패한다."""
    invalid_claims = [
        {"book_isbn13": "9780452284234", "kind": "theme", "content": "1984 클레임 1"},
        {"book_isbn13": "9780452284234", "kind": "theme", "content": "1984 클레임 2"},
        {"book_isbn13": "9780452284234", "kind": "theme", "content": "1984 클레임 3"},
        {"book_isbn13": "9780452284234", "kind": "theme", "content": "1984 클레임 4"},
        {"book_isbn13": "9780374275631", "kind": "concept", "content": "생각 클레임 1"},
        {"book_isbn13": "9780374275631", "kind": "concept", "content": "생각 클레임 2"},
        {"book_isbn13": "9780374275631", "kind": "concept", "content": "생각 클레임 3"},
        # 잘못된 대상: READY_LIMITED 도서(9780143111597)에 Claim 지정
        {
            "book_isbn13": "9780143111597",
            "kind": "event",
            "content": "어둠의 왼손 클레임",
        },
    ]
    claims_file = tmp_path / "invalid_target_claims.json"
    claims_file.write_text(json.dumps(invalid_claims), encoding="utf-8")

    with pytest.raises(ValidationError, match="READY 도서가 아닌 ISBN"):
        prepare_validation_books(seed_path=claims_file)

    assert Book.objects.count() == 0
    assert BookKnowledge.objects.count() == 0


@pytest.mark.django_db
def test_prepare_validation_books_fails_when_ready_book_has_no_claims(
    tmp_path: Path,
) -> None:
    """총 8개 Claim이라도 특정 READY 도서에 매핑된 Claim이 누락되면 실패한다."""
    unmapped_claims = [
        {
            "book_isbn13": "9780452284234",
            "kind": "theme",
            "content": f"1984 독점 클레임 {i}",
        }
        for i in range(8)
    ]
    claims_file = tmp_path / "unmapped_claims.json"
    claims_file.write_text(json.dumps(unmapped_claims), encoding="utf-8")

    with pytest.raises(ValidationError, match="READY 도서의 Claim이 누락"):
        prepare_validation_books(seed_path=claims_file)

    assert Book.objects.count() == 0
    assert BookKnowledge.objects.count() == 0
