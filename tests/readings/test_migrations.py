import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_initial_migration_defines_reading_constraints() -> None:
    """초기 migration이 빈 Reading table에 필요한 제약을 선언하는지 확인한다."""
    migration = MigrationExecutor(connection).loader.get_migration(
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
