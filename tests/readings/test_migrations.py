import pytest
from django.db import IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_initial_migration_defines_reading_constraints() -> None:
    """초기 migration이 빈 Reading table에 필요한 제약을 선언하는지 확인한다."""
    migration = MigrationExecutor(transaction.get_connection()).loader.get_migration(
        "readings", "0001_initial"
    )
    reading_operation = migration.operations[0]
    constraint_names = {
        constraint.name for constraint in reading_operation.options["constraints"]
    }

    assert reading_operation.name == "Reading"
    assert constraint_names == {
        "readings_completion_date_state",
        "readings_active_user_book_uniq",
    }


@pytest.mark.django_db(transaction=True)
def test_initial_migration_round_trip_enforces_database_constraints() -> None:
    """pytest 전용 DB에서 초기 migration과 실제 제약의 왕복을 검증한다."""
    database_connection = transaction.get_connection()
    migrate_from = [("readings", None)]
    migrate_to = [("readings", "0001_initial")]

    try:
        MigrationExecutor(database_connection).migrate(migrate_from)
        assert "readings_reading" not in database_connection.introspection.table_names()

        executor = MigrationExecutor(database_connection)
        executor.migrate(migrate_to)
        apps = executor.loader.project_state(migrate_to).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        user = User.objects.create(username="migration-owner")
        book = Book.objects.create(isbn13="9788937834799", title="Migration 테스트")

        with pytest.raises(IntegrityError), transaction.atomic():
            Reading.objects.create(
                user=user, book=book, status="completed", completed_on=None
            )

        Reading.objects.create(user=user, book=book, status="reading")
        with pytest.raises(IntegrityError), transaction.atomic():
            Reading.objects.create(user=user, book=book, status="want_to_read")

        with pytest.raises(IntegrityError), transaction.atomic():
            Reading.objects.create(user_id=user.pk + 1000, book=book, status="reading")
        with pytest.raises(IntegrityError), transaction.atomic():
            Reading.objects.create(user=user, book_id=book.pk + 1000, status="reading")

        MigrationExecutor(database_connection).migrate(migrate_from)
        assert "readings_reading" not in database_connection.introspection.table_names()

        MigrationExecutor(database_connection).migrate(migrate_to)
        assert "readings_reading" in database_connection.introspection.table_names()
        assert apps.get_model("readings", "Reading").objects.count() == 0
    finally:
        executor = MigrationExecutor(database_connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
