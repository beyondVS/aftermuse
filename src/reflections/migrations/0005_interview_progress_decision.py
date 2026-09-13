import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [("reflections", "0004_turn_next_question_skipped_at")]

    operations = [
        migrations.RunSQL(
            "SET LOCAL lock_timeout = '2s';",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="InterviewProgressDecision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("SOFT_STOP", "조기 마무리 선택"),
                            ("CAP_EXTENSION", "질문 상한 연장 선택"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "selection",
                    models.CharField(
                        blank=True,
                        choices=[("END", "마치기"), ("CONTINUE", "계속하기")],
                        max_length=8,
                        null=True,
                    ),
                ),
                ("candidate_question", models.CharField(max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("decided_at", models.DateTimeField(blank=True, null=True)),
                (
                    "turn",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progress_decision",
                        to="reflections.interviewturn",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.CheckConstraint(
                        condition=Q(kind__in=("SOFT_STOP", "CAP_EXTENSION")),
                        name="reflections_progress_kind_valid",
                    ),
                    models.CheckConstraint(
                        condition=Q(selection__isnull=True)
                        | Q(selection__in=("END", "CONTINUE")),
                        name="reflections_progress_selection_valid",
                    ),
                    models.CheckConstraint(
                        condition=(
                            Q(selection__isnull=True) & Q(decided_at__isnull=True)
                        )
                        | (Q(selection__isnull=False) & Q(decided_at__isnull=False)),
                        name="reflections_progress_decided_consistent",
                    ),
                ],
            },
        ),
    ]
