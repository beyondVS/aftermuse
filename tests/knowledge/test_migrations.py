from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_initial_migration_round_trips_and_restores_constraints() -> None:
    """초기 migration이 새 table과 모든 DB 제약을 왕복으로 보존하는지 확인한다."""
    connection = transaction.get_connection()
    migration_target = [("knowledge", "0001_initial")]

    try:
        MigrationExecutor(connection).migrate([("knowledge", None)])
        assert "knowledge_bookknowledge" not in connection.introspection.table_names()

        executor = MigrationExecutor(connection)
        executor.migrate(migration_target)
        apps = executor.loader.project_state(migration_target).apps
        Book = apps.get_model("books", "Book")
        BookKnowledge = apps.get_model("knowledge", "BookKnowledge")
        book = Book.objects.create(isbn13="9780000000021", title="Migration 테스트")
        BookKnowledge.objects.create(book=book, kind="theme", content="유효한 Claim")

        for kwargs in (
            {"book": book, "kind": "invalid", "content": "유효한 Claim"},
            {"book": book, "kind": "theme", "content": " \t "},
            {"book": book, "kind": "theme", "content": "유효한 Claim"},
            {"book_id": book.pk + 1000, "kind": "theme", "content": "고아 Claim"},
        ):
            with pytest.raises(IntegrityError), transaction.atomic():
                BookKnowledge.objects.create(**kwargs)

        MigrationExecutor(connection).migrate([("knowledge", None)])
        assert "knowledge_bookknowledge" not in connection.introspection.table_names()

        MigrationExecutor(connection).migrate(migration_target)
        assert "knowledge_bookknowledge" in connection.introspection.table_names()
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_initial_migration_sql_creates_only_the_new_knowledge_table() -> None:
    """생성 DDL이 기존 table을 변경하지 않는 additive migration인지 확인한다."""
    output = StringIO()

    call_command("sqlmigrate", "knowledge", "0001", stdout=output)

    sql = output.getvalue().upper()
    assert 'CREATE TABLE "KNOWLEDGE_BOOKKNOWLEDGE"' in sql
    assert "FOREIGN KEY" in sql
    assert "CHECK" in sql
    assert "UNIQUE" in sql
    assert 'ALTER TABLE "BOOKS_BOOK"' not in sql
    assert "DROP TABLE" not in sql
