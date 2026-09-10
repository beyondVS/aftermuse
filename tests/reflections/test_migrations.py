import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_initial_migration_is_additive_and_has_no_turn_fk_index() -> None:
    """Interview 초기 DDL이 신규 table·제약만 생성하는지 확인한다."""
    output = StringIO()
    call_command("sqlmigrate", "reflections", "0001", stdout=output)

    sql = output.getvalue().upper()
    assert 'CREATE TABLE "REFLECTIONS_INTERVIEW"' in sql
    assert 'CREATE TABLE "REFLECTIONS_INTERVIEWTURN"' in sql
    assert "CHECK" in sql
    assert "UNIQUE" in sql
    assert "REFLECTIONS_INTERVIEW_READINESS_VALID" in sql
    assert "REFLECTIONS_INTERVIEW_STATUS_VALID" in sql
    assert "REFLECTIONS_TURN_SEQUENCE_POSITIVE" in sql
    assert "REFLECTIONS_TURN_INTERVIEW_SEQUENCE_UNIQ" in sql
    assert 'ALTER TABLE "BOOKS_BOOK"' not in sql
    assert 'ALTER TABLE "READINGS_READING"' not in sql
    assert 'CREATE INDEX "REFLECTIONS_INTERVIEWTURN_INTERVIEW_ID' not in sql


@pytest.mark.django_db(transaction=True)
def test_initial_migration_round_trip_restores_constraints() -> None:
    """PostgreSQL에서 신규 두 table과 관계 제약이 왕복으로 복원되는지 확인한다."""
    connection = transaction.get_connection()
    target = [("reflections", "0001_initial")]
    try:
        MigrationExecutor(connection).migrate([("reflections", None)])
        tables = connection.introspection.table_names()
        assert "reflections_interview" not in tables
        assert "reflections_interviewturn" not in tables

        executor = MigrationExecutor(connection)
        executor.migrate(target)
        apps = executor.loader.project_state(target).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        user = User.objects.create(username="reflection-migration-owner")
        book = Book.objects.create(isbn13="9780000000081", title="Migration 테스트")
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-08"
        )
        interview = Interview.objects.create(
            reading=reading,
            book=book,
            knowledge_readiness="READY",
            status="IN_PROGRESS",
        )
        InterviewTurn.objects.create(interview=interview, sequence=1, question="질문")
        for kwargs in (
            {"interview": interview, "sequence": 1, "question": "중복"},
            {"interview": interview, "sequence": 0, "question": "0"},
            {"interview": interview, "sequence": 2, "question": "  "},
        ):
            with pytest.raises(IntegrityError), transaction.atomic():
                InterviewTurn.objects.create(**kwargs)

        MigrationExecutor(connection).migrate([("reflections", None)])
        assert "reflections_interview" not in connection.introspection.table_names()
        MigrationExecutor(connection).migrate(target)
        assert "reflections_interview" in connection.introspection.table_names()
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_coverage_migrations_backfill_defaults_constraints_and_reverse_data() -> None:
    """Coverage schema가 기존 Interview를 보존하고 DB default와 CHECK를 제공한다."""
    connection = transaction.get_connection()
    initial = [("reflections", "0001_initial")]
    target = [("reflections", "0003_interview_coverage_constraint")]
    try:
        MigrationExecutor(connection).migrate(initial)
        apps = MigrationExecutor(connection).loader.project_state(initial).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        user = User.objects.create(username="coverage-migration-owner")
        book = Book.objects.create(isbn13="9780000000098", title="Coverage Migration")
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-10"
        )
        default_reading = Reading.objects.create(
            user=User.objects.create(username="coverage-default-owner"),
            book=book,
            status="completed",
            completed_on="2026-09-10",
        )
        interview = Interview.objects.create(
            reading=reading,
            book=book,
            knowledge_readiness="READY",
            status="IN_PROGRESS",
        )
        InterviewTurn.objects.create(interview=interview, sequence=1, question="질문")

        MigrationExecutor(connection).migrate(target)
        apps = MigrationExecutor(connection).loader.project_state(target).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        book = Book.objects.get(pk=book.pk)
        upgraded = Interview.objects.get(pk=interview.pk)
        assert upgraded.coverage == {
            "MEMORY": "UNCOVERED",
            "REACTION": "UNCOVERED",
            "CONNECTION": "UNCOVERED",
            "AFTERTHOUGHT": "UNCOVERED",
        }
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO reflections_interview "
                "(reading_id, book_id, knowledge_readiness, status, "
                "started_at, updated_at) VALUES (%s, %s, 'READY', "
                "'IN_PROGRESS', NOW(), NOW()) RETURNING coverage",
                [default_reading.pk, book.pk],
            )
            assert json.loads(cursor.fetchone()[0]) == upgraded.coverage
        orm_reading = Reading.objects.create(
            user=User.objects.create(username="coverage-orm-default-owner"),
            book=book,
            status="completed",
            completed_on="2026-09-10",
        )
        orm_default = Interview.objects.create(
            reading=orm_reading,
            book=book,
            knowledge_readiness="READY",
            status="IN_PROGRESS",
        )
        assert orm_default.coverage == upgraded.coverage
        invalid_coverages = (
            [],
            {"MEMORY": "UNCOVERED"},
            {**upgraded.coverage, "EXTRA": "UNCOVERED"},
            {**upgraded.coverage, "MEMORY": "INVALID"},
        )
        for invalid_coverage in invalid_coverages:
            with pytest.raises(IntegrityError), transaction.atomic():
                Interview.objects.filter(pk=upgraded.pk).update(
                    coverage=invalid_coverage
                )
        assert InterviewTurn.objects.filter(interview_id=upgraded.pk).count() == 1

        MigrationExecutor(connection).migrate(initial)
        apps = MigrationExecutor(connection).loader.project_state(initial).apps
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        assert Interview.objects.filter(pk=interview.pk).exists()
        assert InterviewTurn.objects.filter(interview_id=interview.pk).count() == 1
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
