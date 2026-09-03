from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from time import perf_counter

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.db.migrations.executor import MigrationExecutor

from books.models import Book


@pytest.mark.django_db
def test_book_persists_complete_bibliographic_metadata() -> None:
    book = Book.objects.create(
        isbn13="9788937834790",
        title="정의란 무엇인가",
        authors="마이클 샌델",
        publisher="와이즈베리",
        published_date=date(2014, 11, 20),
        cover_url="https://images.example.test/books/justice.jpg",
        description="정의에 관한 질문을 다룬 책",
        table_of_contents="1장 정의란 무엇인가",
    )

    saved_book = Book.objects.get(pk=book.pk)

    assert saved_book.isbn13 == "9788937834790"
    assert saved_book.title == "정의란 무엇인가"
    assert saved_book.authors == "마이클 샌델"
    assert saved_book.publisher == "와이즈베리"
    assert saved_book.published_date == date(2014, 11, 20)
    assert saved_book.cover_url == "https://images.example.test/books/justice.jpg"
    assert saved_book.description == "정의에 관한 질문을 다룬 책"
    assert saved_book.table_of_contents == "1장 정의란 무엇인가"
    assert str(saved_book) == "정의란 무엇인가"


@pytest.mark.django_db
def test_book_is_retrieved_by_exact_isbn13() -> None:
    target_book = Book.objects.create(isbn13="9788937834790", title="정의란 무엇인가")
    Book.objects.create(isbn13="9788966262281", title="사피엔스")

    found_book = Book.objects.get(isbn13="9788937834790")

    assert found_book.pk == target_book.pk


@pytest.mark.django_db
def test_missing_isbn13_returns_no_book() -> None:
    assert Book.objects.filter(isbn13="9780000000000").first() is None


@pytest.mark.parametrize(
    "isbn13",
    [
        "978893783479",
        "97889378347900",
        "978893783479X",
        "１２３４５６７８９０１２３",
    ],
)
@pytest.mark.django_db
def test_book_full_clean_rejects_invalid_isbn13(isbn13: str) -> None:
    with pytest.raises(ValidationError):
        Book(isbn13=isbn13, title="유효한 제목").full_clean()


@pytest.mark.django_db
def test_book_full_clean_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        Book(isbn13="9788937834790", title="").full_clean()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "isbn13,title",
    [
        ("978893783479", "유효한 제목"),
        ("978893783479X", "유효한 제목"),
        ("9788937834790", ""),
    ],
)
def test_book_database_constraints_reject_invalid_raw_orm_values(
    isbn13: str,
    title: str,
) -> None:
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Book.objects.create(isbn13=isbn13, title=title)


@pytest.mark.django_db(transaction=True)
def test_duplicate_isbn13_does_not_change_existing_book_metadata() -> None:
    original_book = Book.objects.create(
        isbn13="9788937834790",
        title="정의란 무엇인가",
        authors="마이클 샌델",
    )

    with pytest.raises(IntegrityError):
        Book.objects.create(
            isbn13="9788937834790",
            title="변경되면 안 되는 제목",
            authors="다른 저자",
        )

    saved_book = Book.objects.get(isbn13="9788937834790")

    assert saved_book.pk == original_book.pk
    assert saved_book.title == "정의란 무엇인가"
    assert saved_book.authors == "마이클 샌델"


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_isbn13_creation_leaves_one_book() -> None:
    isbn13 = "9788937834790"
    barrier = Barrier(2)

    def create_book(title: str) -> str:
        close_old_connections()
        try:
            barrier.wait()
            Book.objects.create(isbn13=isbn13, title=title)
        except IntegrityError:
            return "duplicate"
        finally:
            close_old_connections()
        return "created"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_book, ("첫 번째 요청", "두 번째 요청")))

    assert results.count("created") == 1
    assert results.count("duplicate") == 1
    assert Book.objects.filter(isbn13=isbn13).count() == 1


@pytest.mark.django_db
def test_book_preserves_missing_optional_metadata() -> None:
    book = Book.objects.create(isbn13="9788937834790", title="정의란 무엇인가")

    saved_book = Book.objects.get(pk=book.pk)

    assert saved_book.authors == ""
    assert saved_book.publisher == ""
    assert saved_book.published_date is None
    assert saved_book.cover_url == ""
    assert saved_book.description == ""
    assert saved_book.table_of_contents == ""


@pytest.mark.django_db
def test_exact_isbn13_lookups_use_one_query_and_meet_p95_target(
    django_assert_num_queries,
) -> None:
    books = [
        Book(isbn13=f"978000000{number:04d}", title=f"도서 {number}")
        for number in range(100)
    ]
    Book.objects.bulk_create(books)
    durations = []

    for book in books:
        started_at = perf_counter()
        with django_assert_num_queries(1):
            found_book = Book.objects.filter(isbn13=book.isbn13).first()
        durations.append(perf_counter() - started_at)
        assert found_book is not None
        assert found_book.isbn13 == book.isbn13

    for number in range(100):
        started_at = perf_counter()
        with django_assert_num_queries(1):
            missing_book = Book.objects.filter(isbn13=f"979000000{number:04d}").first()
        durations.append(perf_counter() - started_at)
        assert missing_book is None

    p95_index = int(len(durations) * 0.95) - 1
    assert sorted(durations)[p95_index] < 1


@pytest.mark.django_db(transaction=True)
def test_initial_book_migration_round_trips_on_an_empty_database() -> None:
    executor = MigrationExecutor(transaction.get_connection())
    executor.migrate([("books", None)])

    assert "books_book" not in transaction.get_connection().introspection.table_names()

    executor = MigrationExecutor(transaction.get_connection())
    executor.migrate([("books", "0001_initial")])

    assert "books_book" in transaction.get_connection().introspection.table_names()
    assert Book.objects.count() == 0
