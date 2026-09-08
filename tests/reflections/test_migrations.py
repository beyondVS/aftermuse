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
