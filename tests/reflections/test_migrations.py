import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
def test_candidate_focus_axis_migration_preserves_pending_legacy_choice() -> None:
    connection = transaction.get_connection()
    previous = [("reflections", "0005_interview_progress_decision")]
    target = [("reflections", "0006_interviewprogressdecision_candidate_focus_axis")]
    try:
        MigrationExecutor(connection).migrate(previous)
        apps = MigrationExecutor(connection).loader.project_state(previous).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        Turn = apps.get_model("reflections", "InterviewTurn")
        Decision = apps.get_model("reflections", "InterviewProgressDecision")
        user = User.objects.create(username="candidate-axis-migration-owner")
        book = Book.objects.create(isbn13="9780000000189", title="후보 축 Migration")
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-13"
        )
        interview = Interview.objects.create(
            reading=reading, book=book, knowledge_readiness="READY"
        )
        turn = Turn.objects.create(
            interview=interview, sequence=1, question="무엇인가요?", answer="답변"
        )
        choice = Decision.objects.create(
            turn=turn, kind="CAP_EXTENSION", candidate_question="다음은 무엇인가요?"
        )
        MigrationExecutor(connection).migrate(target)
        upgraded = MigrationExecutor(connection).loader.project_state(target).apps
        NewDecision = upgraded.get_model("reflections", "InterviewProgressDecision")
        assert NewDecision.objects.get(pk=choice.pk).candidate_focus_axis is None
        NewDecision.objects.filter(pk=choice.pk).update(candidate_focus_axis="MEMORY")
        MigrationExecutor(connection).migrate(previous)
        assert Decision.objects.filter(pk=choice.pk, turn_id=turn.pk).exists()
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_candidate_focus_axis_sql_is_additive_and_lock_bounded() -> None:
    output = StringIO()
    call_command("sqlmigrate", "reflections", "0006", stdout=output)
    sql = output.getvalue().upper()
    assert "SET LOCAL LOCK_TIMEOUT = '2S'" in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEWPROGRESSDECISION" ADD COLUMN' in sql
    assert "CANDIDATE_FOCUS_AXIS" in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEWTURN"' not in sql


@pytest.mark.django_db(transaction=True)
def test_progress_decision_migration_preserves_existing_turn_and_reverses() -> None:
    connection = transaction.get_connection()
    previous = [("reflections", "0004_turn_next_question_skipped_at")]
    target = [("reflections", "0005_interview_progress_decision")]
    try:
        MigrationExecutor(connection).migrate(previous)
        apps = MigrationExecutor(connection).loader.project_state(previous).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        user = User.objects.create(username="progress-migration-owner")
        book = Book.objects.create(isbn13="9780000000188", title="선택 Migration")
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-13"
        )
        interview = Interview.objects.create(
            reading=reading, book=book, knowledge_readiness="READY"
        )
        turn = InterviewTurn.objects.create(
            interview=interview, sequence=1, question="무엇인가요?", answer="답변"
        )
        MigrationExecutor(connection).migrate(target)
        apps = MigrationExecutor(connection).loader.project_state(target).apps
        Decision = apps.get_model("reflections", "InterviewProgressDecision")
        Decision.objects.create(
            turn_id=turn.pk, kind="SOFT_STOP", candidate_question="다음은 무엇인가요?"
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            Decision.objects.create(
                turn_id=turn.pk, kind="CAP_EXTENSION", candidate_question="중복인가요?"
            )
        MigrationExecutor(connection).migrate(previous)
        assert (
            "reflections_interviewprogressdecision"
            not in connection.introspection.table_names()
        )
        assert InterviewTurn.objects.filter(pk=turn.pk, answer="답변").exists()
        MigrationExecutor(connection).migrate(target)
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_progress_decision_sql_is_additive_and_bounded() -> None:
    output = StringIO()
    call_command("sqlmigrate", "reflections", "0005", stdout=output)
    sql = output.getvalue().upper()
    assert "SET LOCAL LOCK_TIMEOUT = '2S'" in sql
    assert 'CREATE TABLE "REFLECTIONS_INTERVIEWPROGRESSDECISION"' in sql
    assert "UNIQUE" in sql and "FOREIGN KEY" in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEW"' not in sql


@pytest.mark.django_db(transaction=True)
def test_next_question_skip_marker_migration_round_trip() -> None:
    """기존 Turn을 보존하며 nullable 생략 표식을 추가·제거한다."""
    connection = transaction.get_connection()
    previous = [("reflections", "0003_interview_coverage_constraint")]
    target = [("reflections", "0004_turn_next_question_skipped_at")]
    try:
        MigrationExecutor(connection).migrate(previous)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'reflections_interviewturn' "
                "AND column_name = 'next_question_skipped_at'"
            )
            assert cursor.fetchone() is None
        MigrationExecutor(connection).migrate(target)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'reflections_interviewturn' "
                "AND column_name = 'next_question_skipped_at'"
            )
            assert cursor.fetchone()[0] == "YES"
        MigrationExecutor(connection).migrate(previous)
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


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


@pytest.mark.django_db(transaction=True)
def test_reflection_migration_preserves_existing_data_and_reverses() -> None:
    connection = transaction.get_connection()
    previous = [("reflections", "0006_interviewprogressdecision_candidate_focus_axis")]
    target = [("reflections", "0007_reflection")]
    try:
        MigrationExecutor(connection).migrate(previous)
        apps = MigrationExecutor(connection).loader.project_state(previous).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")
        Decision = apps.get_model("reflections", "InterviewProgressDecision")

        user = User.objects.create(username="reflection-mig-owner")
        book = Book.objects.create(
            isbn13="9780000000199", title="Reflection Migration 도서"
        )
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-15"
        )
        interview = Interview.objects.create(
            reading=reading,
            book=book,
            knowledge_readiness="READY",
            status="REFLECTION_READY",
        )
        turn = InterviewTurn.objects.create(
            interview=interview, sequence=1, question="질문", answer="답변"
        )
        decision = Decision.objects.create(
            turn=turn, kind="SOFT_STOP", candidate_question="다음 질문"
        )

        # 0007로 마이그레이션
        MigrationExecutor(connection).migrate(target)
        apps = MigrationExecutor(connection).loader.project_state(target).apps
        ReflectionModel = apps.get_model("reflections", "Reflection")

        # 기존 레코드 보존 확인
        assert Interview.objects.filter(
            pk=interview.pk, status="REFLECTION_READY"
        ).exists()
        assert InterviewTurn.objects.filter(pk=turn.pk, answer="답변").exists()
        assert Decision.objects.filter(pk=decision.pk).exists()

        # 새 Reflection 생성 및 OneToOne 검증
        TargetInterview = apps.get_model("reflections", "Interview")
        target_interview = TargetInterview.objects.get(pk=interview.pk)
        sections = [
            {
                "title": "제목",
                "paragraphs": [
                    {"text": "답변", "evidence": [{"sequence": 1, "quote": "답변"}]}
                ],
            }
        ]
        ref = ReflectionModel.objects.create(
            interview=target_interview,
            draft_markdown="초안 본문",
            draft_sections=sections,
            status="DRAFT",
        )
        assert ref.pk is not None

        # 중복 생성 시 유니크 제약
        with pytest.raises(IntegrityError), transaction.atomic():
            ReflectionModel.objects.create(
                interview=target_interview,
                draft_markdown="다른 초안",
                draft_sections=sections,
                status="DRAFT",
            )

        # 0006으로 롤백
        MigrationExecutor(connection).migrate(previous)
        with connection.cursor() as cursor:
            tables = connection.introspection.table_names(cursor)
        assert "reflections_reflection" not in tables

        # 기존 레코드 보존 확인
        assert Interview.objects.filter(pk=interview.pk).exists()
        assert InterviewTurn.objects.filter(pk=turn.pk).exists()
        assert Decision.objects.filter(pk=decision.pk).exists()
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_reflection_migration_sql_is_additive_and_lock_bounded() -> None:
    output = StringIO()
    call_command("sqlmigrate", "reflections", "0007", stdout=output)
    sql = output.getvalue().upper()
    assert "SET LOCAL LOCK_TIMEOUT = '2S'" in sql
    assert 'CREATE TABLE "REFLECTIONS_REFLECTION"' in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEW"' not in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEWTURN"' not in sql
    assert 'ALTER TABLE "REFLECTIONS_INTERVIEWPROGRESSDECISION"' not in sql


@pytest.mark.django_db(transaction=True)
def test_interview_turn_user_skip_migration_round_trip() -> None:
    connection = transaction.get_connection()
    previous = [("reflections", "0007_reflection")]
    target = [("reflections", "0009_validate_interview_turn_user_skip")]

    try:
        # 1. 0007_reflection 상태에서 기존 데이터 생성
        MigrationExecutor(connection).migrate(previous)
        apps = MigrationExecutor(connection).loader.project_state(previous).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        InterviewTurn = apps.get_model("reflections", "InterviewTurn")

        user = User.objects.create(username="skip-mig-owner")
        book = Book.objects.create(isbn13="9780000000201", title="Skip Migration 도서")
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-16"
        )
        interview = Interview.objects.create(
            reading=reading,
            book=book,
            knowledge_readiness="READY",
            status="IN_PROGRESS",
        )
        turn = InterviewTurn.objects.create(
            interview=interview,
            sequence=1,
            question="기존 질문",
            answer="기존 확정 답변",
        )

        # 2. 0008, 0009로 forward 마이그레이션
        MigrationExecutor(connection).migrate(target)
        upgraded_apps = MigrationExecutor(connection).loader.project_state(target).apps
        UpgradedInterview = upgraded_apps.get_model("reflections", "Interview")
        UpgradedTurn = upgraded_apps.get_model("reflections", "InterviewTurn")

        # 3. 기존 answer 데이터 보존 및 user_skipped_at IS NULL 확인
        migrated_turn = UpgradedTurn.objects.get(pk=turn.pk)
        assert migrated_turn.answer == "기존 확정 답변"
        assert migrated_turn.user_skipped_at is None

        # 4. 신규 status ENDED_NO_REFLECTION 허용 확인
        upgraded_interview = UpgradedInterview.objects.get(pk=interview.pk)
        upgraded_interview.status = "ENDED_NO_REFLECTION"
        upgraded_interview.save()
        assert (
            UpgradedInterview.objects.get(pk=interview.pk).status
            == "ENDED_NO_REFLECTION"
        )

        # 5. answer와 user_skipped_at 동시 설정 시 DB 제약 위반 확인
        now = timezone.now()
        with pytest.raises(IntegrityError), transaction.atomic():
            UpgradedTurn.objects.create(
                interview=upgraded_interview,
                sequence=2,
                question="상호 배타 테스트",
                answer="답변 있음",
                user_skipped_at=now,
            )

        # 정상적인 skip 생성 확인
        valid_skip_turn = UpgradedTurn.objects.create(
            interview=upgraded_interview,
            sequence=3,
            question="건너뛴 질문",
            answer=None,
            user_skipped_at=now,
        )
        assert valid_skip_turn.pk is not None

        # 6. 0007_reflection으로 reverse 마이그레이션
        # 롤백 전 신규 status와 user_skipped_at을 사용하는 행 정리
        # (운영 reverse가 아닌 마이그레이션 롤백 테스트 격리)
        valid_skip_turn.delete()
        upgraded_interview.status = "IN_PROGRESS"
        upgraded_interview.save()

        MigrationExecutor(connection).migrate(previous)
        rolled_back_apps = (
            MigrationExecutor(connection).loader.project_state(previous).apps
        )
        RolledBackTurn = rolled_back_apps.get_model("reflections", "InterviewTurn")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'reflections_interviewturn' "
                "AND column_name = 'user_skipped_at'"
            )
            assert cursor.fetchone() is None

        assert RolledBackTurn.objects.filter(
            pk=turn.pk, answer="기존 확정 답변"
        ).exists()

    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_interview_turn_user_skip_sql_is_additive_and_lock_bounded() -> None:
    output_0008 = StringIO()
    call_command("sqlmigrate", "reflections", "0008", stdout=output_0008)
    sql_0008 = output_0008.getvalue().upper()
    assert "SET LOCAL LOCK_TIMEOUT = '2S'" in sql_0008
    assert (
        'ALTER TABLE "REFLECTIONS_INTERVIEWTURN" ADD COLUMN "USER_SKIPPED_AT"'
        in sql_0008
    )
    assert "NOT VALID" in sql_0008

    output_0009 = StringIO()
    call_command("sqlmigrate", "reflections", "0009", stdout=output_0009)
    sql_0009 = output_0009.getvalue().upper()
    assert "VALIDATE CONSTRAINT" in sql_0009


@pytest.mark.django_db(transaction=True)
def test_reflection_completed_status_migration_round_trip() -> None:
    connection = transaction.get_connection()
    previous = [("reflections", "0009_validate_interview_turn_user_skip")]
    target = [("reflections", "0010_reflection_completed_status")]

    try:
        # 1. 0009 상태에서 기존 DRAFT 데이터 생성
        MigrationExecutor(connection).migrate(previous)
        apps = MigrationExecutor(connection).loader.project_state(previous).apps
        User = apps.get_model("accounts", "User")
        Book = apps.get_model("books", "Book")
        Reading = apps.get_model("readings", "Reading")
        Interview = apps.get_model("reflections", "Interview")
        Reflection = apps.get_model("reflections", "Reflection")

        user = User.objects.create(username="reflection-mig-owner")
        book = Book.objects.create(
            isbn13="9780000000210", title="Reflection Migration 도서"
        )
        reading = Reading.objects.create(
            user=user, book=book, status="completed", completed_on="2026-09-17"
        )
        interview = Interview.objects.create(
            reading=reading,
            book=book,
            knowledge_readiness="READY",
            status="REFLECTION_READY",
        )
        reflection = Reflection.objects.create(
            interview=interview,
            draft_markdown="마이그레이션 전 초안 본문입니다.",
            draft_sections=[{"title": "섹션", "paragraphs": []}],
            status="DRAFT",
            completed_at=None,
        )

        # 2. 0010 forward 마이그레이션
        MigrationExecutor(connection).migrate(target)
        upgraded_apps = MigrationExecutor(connection).loader.project_state(target).apps
        UpgradedReflection = upgraded_apps.get_model("reflections", "Reflection")

        # 3. 기존 DRAFT 데이터 보존 확인
        migrated_ref = UpgradedReflection.objects.get(pk=reflection.pk)
        assert migrated_ref.status == "DRAFT"
        assert migrated_ref.completed_at is None
        assert migrated_ref.draft_markdown == "마이그레이션 전 초안 본문입니다."

        # 4. COMPLETED 및 completed_at 설정 허용 확인
        now = timezone.now()
        migrated_ref.status = "COMPLETED"
        migrated_ref.completed_at = now
        migrated_ref.save()

        ref_reloaded = UpgradedReflection.objects.get(pk=reflection.pk)
        assert ref_reloaded.status == "COMPLETED"
        assert ref_reloaded.completed_at is not None

        # 5. 불일치 상태 DB 제약 위반 확인 (COMPLETED인데 completed_at IS NULL)
        with pytest.raises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE reflections_reflection "
                    "SET completed_at = NULL WHERE id = %s",
                    [reflection.pk],
                )

        # 6. 불일치 상태 DB 제약 위반 확인 (DRAFT인데 completed_at IS NOT NULL)
        with pytest.raises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE reflections_reflection SET status = 'DRAFT' WHERE id = %s",
                    [reflection.pk],
                )

        # 7. 0009로 reverse 마이그레이션
        # 롤백 전 DRAFT 상태로 복구하여 0009 제약 만족
        migrated_ref.status = "DRAFT"
        migrated_ref.completed_at = None
        migrated_ref.save()

        MigrationExecutor(connection).migrate(previous)
        rolled_back_apps = (
            MigrationExecutor(connection).loader.project_state(previous).apps
        )
        RolledBackReflection = rolled_back_apps.get_model("reflections", "Reflection")

        rolled_back_ref = RolledBackReflection.objects.get(pk=reflection.pk)
        assert rolled_back_ref.status == "DRAFT"
        assert rolled_back_ref.completed_at is None

    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@pytest.mark.django_db(transaction=True)
def test_reflection_completed_status_sql_is_lock_bounded() -> None:
    output_0010 = StringIO()
    call_command("sqlmigrate", "reflections", "0010", stdout=output_0010)
    sql_0010 = output_0010.getvalue().upper()
    assert "SET LOCAL LOCK_TIMEOUT = '2S'" in sql_0010
    assert "DROP CONSTRAINT" in sql_0010
    assert "ADD CONSTRAINT" in sql_0010
