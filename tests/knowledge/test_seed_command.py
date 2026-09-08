import pytest
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command

from books.models import Book
from knowledge.models import BookKnowledge
from knowledge.services import BookKnowledgeSeedResult, seed_book_knowledge

TARGET_BOOKS = (
    ("9780452284234", "1984"),
    ("9780374275631", "Thinking, Fast and Slow"),
)


def create_target_books() -> None:
    """승인된 Seed가 참조하는 기존 Book 두 권을 준비한다."""
    for isbn13, title in TARGET_BOOKS:
        Book.objects.create(isbn13=isbn13, title=title)


@pytest.mark.django_db
def test_seed_command_applies_approved_claims_idempotently() -> None:
    create_target_books()

    call_command("seed_book_knowledge")
    first_claims = list(
        BookKnowledge.objects.order_by("book__isbn13", "kind", "content").values_list(
            "book__isbn13", "kind", "content"
        )
    )
    call_command("seed_book_knowledge")
    call_command("seed_book_knowledge")

    assert len(first_claims) == 8
    assert BookKnowledge.objects.count() == 8
    assert first_claims == list(
        BookKnowledge.objects.order_by("book__isbn13", "kind", "content").values_list(
            "book__isbn13", "kind", "content"
        )
    )
    assert {
        isbn13: BookKnowledge.objects.filter(book__isbn13=isbn13).count()
        for isbn13, _title in TARGET_BOOKS
    } == {"9780452284234": 4, "9780374275631": 4}


@pytest.mark.django_db
def test_seed_command_delegates_persistence_to_service(monkeypatch) -> None:
    create_target_books()
    from knowledge.management.commands import seed_book_knowledge as command_module

    received_entries = []

    def fake_seed(entries):
        received_entries.extend(entries)
        return BookKnowledgeSeedResult(created=3, reused=5)

    monkeypatch.setattr(command_module, "seed_book_knowledge", fake_seed)

    call_command("seed_book_knowledge")

    assert len(received_entries) == 8
    assert BookKnowledge.objects.count() == 0


@pytest.mark.django_db
def test_seed_command_missing_book_rolls_back_everything() -> None:
    Book.objects.create(isbn13=TARGET_BOOKS[0][0], title=TARGET_BOOKS[0][1])

    with pytest.raises(CommandError, match="대상 Book이 없습니다"):
        call_command("seed_book_knowledge")

    assert BookKnowledge.objects.count() == 0
    assert Book.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "entry",
    [
        {"book_isbn13": "9780452284234", "kind": "invalid", "content": "유효한 Claim"},
        {"book_isbn13": "9780452284234", "kind": "theme", "content": " \t "},
    ],
)
def test_seed_service_validates_every_entry_before_writing(entry) -> None:
    create_target_books()
    valid_entry = {
        "book_isbn13": "9780374275631",
        "kind": "theme",
        "content": "유효한 Claim",
    }

    with pytest.raises(ValidationError):
        seed_book_knowledge([valid_entry, entry])

    assert BookKnowledge.objects.count() == 0


@pytest.mark.django_db
def test_seed_command_rejects_invalid_json_without_writing(monkeypatch) -> None:
    create_target_books()
    from knowledge.management.commands import seed_book_knowledge as command_module

    def invalid_json(_file):
        raise command_module.JSONDecodeError("잘못된 JSON", "{", 0)

    monkeypatch.setattr(command_module.json, "load", invalid_json)

    with pytest.raises(CommandError, match="JSON"):
        call_command("seed_book_knowledge")

    assert BookKnowledge.objects.count() == 0
