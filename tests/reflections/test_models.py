from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from books.models import Book
from readings.models import Reading
from reflections.models import (
    CORE_COVERAGE,
    CoverageStatus,
    Interview,
    InterviewProgressDecision,
    InterviewTurn,
    Reflection,
    default_coverage,
)


def test_progress_decision_requires_answer_and_one_choice_per_turn(interview) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
    )
    pending = InterviewProgressDecision(
        turn=turn,
        kind=InterviewProgressDecision.Kind.SOFT_STOP,
        candidate_question="다음 질문은 무엇인가요?",
    )
    with pytest.raises(ValidationError):
        pending.full_clean()
    turn.answer = "남은 생각입니다."
    turn.save(update_fields=("answer", "updated_at"))
    pending.full_clean()
    pending.save()
    with pytest.raises(IntegrityError), transaction.atomic():
        InterviewProgressDecision.objects.create(
            turn=turn,
            kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
            candidate_question="다른 질문은 무엇인가요?",
        )
    pending.selection = InterviewProgressDecision.Selection.END
    with pytest.raises(ValidationError):
        pending.full_clean()


def test_progress_decision_rejects_unknown_candidate_axis(interview) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="무엇이 남았나요?",
        answer="남은 생각입니다.",
    )
    decision = InterviewProgressDecision(
        turn=turn,
        kind=InterviewProgressDecision.Kind.CAP_EXTENSION,
        candidate_question="다음 질문은 무엇인가요?",
        candidate_focus_axis="UNKNOWN",
    )
    with pytest.raises(ValidationError):
        decision.full_clean()


@pytest.fixture
def interview(django_user_model) -> Interview:
    user = django_user_model.objects.create_user(username="interview-model")
    book = Book.objects.create(isbn13="9788937834793", title="Interview 모델")
    reading = Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )
    return Interview.objects.create(
        reading=reading,
        book=book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )


def test_interview_relationships_are_immutable_but_status_can_change(interview) -> None:
    interview.status = Interview.Status.REFLECTION_READY
    interview.full_clean()
    interview.save()
    other_book = Book.objects.create(isbn13="9788937834794", title="다른 책")
    interview.book = other_book

    with pytest.raises(ValidationError):
        interview.full_clean()

    interview.refresh_from_db()
    assert interview.book_id != other_book.pk


def test_turn_orders_and_rejects_invalid_sequences_or_questions(interview) -> None:
    turn = InterviewTurn(interview=interview, sequence=1, question=" 첫 질문 ")
    turn.full_clean()
    turn.save()
    assert turn.question == "첫 질문"
    with pytest.raises(IntegrityError), transaction.atomic():
        InterviewTurn.objects.create(interview=interview, sequence=1, question="중복")
    with pytest.raises(ValidationError):
        InterviewTurn(interview=interview, sequence=0, question=" ").full_clean()


def test_interview_database_constraints_and_book_protection(interview) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        Interview.objects.filter(pk=interview.pk).update(status="INVALID")
    with pytest.raises(IntegrityError), transaction.atomic():
        Interview.objects.filter(pk=interview.pk).update(knowledge_readiness="INVALID")
    with pytest.raises(ProtectedError):
        interview.book.delete()


def test_turn_preserves_nullable_answers_and_sequence_order(interview) -> None:
    later = InterviewTurn.objects.create(
        interview=interview, sequence=2, question="두 번째 질문", answer=None
    )
    first = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="첫 번째 질문", answer="답변"
    )

    turns = list(interview.turns.all())

    assert [turn.pk for turn in turns] == [first.pk, later.pk]
    assert later.answer is None


def test_turn_answer_validation_preserves_first_confirmed_value(interview) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="첫 번째 질문", answer=None
    )
    turn.answer = "가" * 2000
    turn.full_clean()
    turn.save()
    turn.answer = "다른 답변"

    with pytest.raises(ValidationError):
        turn.full_clean()

    assert InterviewTurn.objects.get(pk=turn.pk).answer == "가" * 2000
    with pytest.raises(ValidationError):
        InterviewTurn(
            interview=interview, sequence=2, question="두 번째 질문", answer=" \n"
        ).full_clean()


def test_coverage_defaults_are_independent_and_canonical(interview) -> None:
    other = Interview(
        reading=interview.reading,
        book=interview.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )

    assert default_coverage() == dict.fromkeys(CORE_COVERAGE, CoverageStatus.UNCOVERED)
    assert interview.coverage == other.coverage
    assert interview.coverage is not other.coverage
    assert set(interview.coverage) == set(CORE_COVERAGE)


@pytest.mark.parametrize(
    "coverage",
    [
        [],
        {"MEMORY": "UNCOVERED"},
        dict.fromkeys((*CORE_COVERAGE, "EXTRA"), "UNCOVERED"),
        dict.fromkeys(CORE_COVERAGE, "INVALID"),
    ],
)
def test_interview_rejects_noncanonical_coverage(coverage, interview) -> None:
    interview.coverage = coverage

    with pytest.raises(ValidationError):
        interview.full_clean()


def test_reflection_model_creation_and_one_to_one_constraint(interview) -> None:
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {"text": "내용", "evidence": [{"sequence": 1, "quote": "내용"}]}
            ],
        }
    ]
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=valid_sections,
        revised_markdown=None,
    )
    reflection.full_clean()
    assert reflection.status == Reflection.Status.DRAFT
    assert reflection.completed_at is None
    assert reflection.revised_markdown is None
    assert interview.reflection == reflection

    with pytest.raises(IntegrityError), transaction.atomic():
        Reflection.objects.create(
            interview=interview,
            draft_markdown="다른 초안 본문입니다.",
            draft_sections=valid_sections,
        )


def test_reflection_draft_markdown_boundaries_and_rejection(interview) -> None:
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {"text": "내용", "evidence": [{"sequence": 1, "quote": "내용"}]}
            ],
        }
    ]

    # 22,000자 허용 경계
    ref_22k = Reflection(
        interview=interview,
        draft_markdown="가" * 22000,
        draft_sections=valid_sections,
    )
    ref_22k.full_clean()

    # 22,001자 거부 경계
    ref_22001 = Reflection(
        interview=interview,
        draft_markdown="가" * 22001,
        draft_sections=valid_sections,
    )
    with pytest.raises(ValidationError):
        ref_22001.full_clean()

    # 빈 문자열 및 공백 거부
    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="   \n\t  ",
            draft_sections=valid_sections,
        ).full_clean()


def test_reflection_revised_markdown_boundaries_and_rejection(interview) -> None:
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {"text": "내용", "evidence": [{"sequence": 1, "quote": "내용"}]}
            ],
        }
    ]

    # None 허용
    ref_none = Reflection(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=valid_sections,
        revised_markdown=None,
    )
    ref_none.full_clean()

    # 20,000자 허용 경계
    ref_20k = Reflection(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=valid_sections,
        revised_markdown="나" * 20000,
    )
    ref_20k.full_clean()

    # 20,001자 거부 경계
    ref_20001 = Reflection(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=valid_sections,
        revised_markdown="나" * 20001,
    )
    with pytest.raises(ValidationError):
        ref_20001.full_clean()

    # 공백만 있는 수정본 거부
    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="초안 본문입니다.",
            draft_sections=valid_sections,
            revised_markdown="   \n  ",
        ).full_clean()


def test_reflection_draft_sections_json_array_shape(interview) -> None:
    # list 허용
    Reflection(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=[{"title": "제목", "paragraphs": []}],
    ).full_clean()

    # dict(객체) 거부
    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="초안 본문입니다.",
            draft_sections={"sections": []},
        ).full_clean()

    # 원시값(string, int) 거부
    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="초안 본문입니다.",
            draft_sections="invalid string",
        ).full_clean()


def test_reflection_draft_only_and_completed_at_none(interview) -> None:
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {"text": "내용", "evidence": [{"sequence": 1, "quote": "내용"}]}
            ],
        }
    ]

    # status != DRAFT 거부
    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="초안 본문입니다.",
            draft_sections=valid_sections,
            status="COMPLETED",
        ).full_clean()

    # completed_at != None 거부
    from django.utils import timezone

    with pytest.raises(ValidationError):
        Reflection(
            interview=interview,
            draft_markdown="초안 본문입니다.",
            draft_sections=valid_sections,
            completed_at=timezone.now(),
        ).full_clean()


def test_reflection_initial_fields_are_immutable_but_revision_can_change(
    interview, django_user_model
) -> None:
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {"text": "내용", "evidence": [{"sequence": 1, "quote": "내용"}]}
            ],
        }
    ]
    reflection = Reflection.objects.create(
        interview=interview,
        draft_markdown="초안 본문입니다.",
        draft_sections=valid_sections,
        revised_markdown=None,
    )
    initial_updated_at = reflection.updated_at

    # revised_markdown 변경 허용
    reflection.revised_markdown = "수정된 본문입니다."
    reflection.full_clean()
    reflection.save()
    assert reflection.revised_markdown == "수정된 본문입니다."
    assert reflection.updated_at >= initial_updated_at

    # interview 변경 거부
    other_user = django_user_model.objects.create_user(
        username="other-ref-interview-user"
    )
    other_book = Book.objects.create(isbn13="9788937834799", title="다른 책")
    other_reading = Reading.objects.create(
        user=other_user,
        book=other_book,
        status=Reading.Status.COMPLETED,
        completed_on=date.today(),
    )
    other_interview = Interview.objects.create(
        reading=other_reading,
        book=other_book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
    )
    reflection.interview = other_interview
    with pytest.raises(ValidationError):
        reflection.full_clean()
    reflection.interview = interview

    # draft_markdown 변경 거부
    reflection.draft_markdown = "변경된 초안 본문"
    with pytest.raises(ValidationError):
        reflection.full_clean()
    reflection.draft_markdown = "초안 본문입니다."

    # draft_sections 변경 거부
    reflection.draft_sections = [{"title": "새 제목", "paragraphs": []}]
    with pytest.raises(ValidationError):
        reflection.full_clean()


def test_interview_status_ended_no_reflection(interview) -> None:
    interview.status = Interview.Status.ENDED_NO_REFLECTION
    interview.full_clean()
    interview.save()
    assert interview.status == "ENDED_NO_REFLECTION"
    interview.refresh_from_db()
    assert interview.status == Interview.Status.ENDED_NO_REFLECTION


def test_turn_user_skipped_at_and_answer_mutual_exclusivity(interview) -> None:
    now = timezone.now()
    # 1. 초기 상태 (답변 대기): answer is None, user_skipped_at is None
    turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="첫 번째 질문"
    )
    assert turn.user_skipped_at is None
    assert turn.answer is None

    # 2. user_skipped_at 설정: 정상
    turn.user_skipped_at = now
    turn.full_clean()
    turn.save()
    assert turn.user_skipped_at == now

    # 3. answer와 user_skipped_at 동시 설정: ValidationError
    turn.answer = "답변 시도"
    with pytest.raises(ValidationError):
        turn.full_clean()


def test_turn_user_skipped_at_rejects_next_question_skipped_at(interview) -> None:
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="첫 번째 질문",
        user_skipped_at=timezone.now(),
    )
    turn.next_question_skipped_at = timezone.now()
    with pytest.raises(ValidationError):
        turn.full_clean()


def test_turn_immutability_for_answer_and_user_skipped_at(interview) -> None:
    now = timezone.now()

    # 1. answer가 확정된 턴은 user_skipped_at 설정 불가
    answered_turn = InterviewTurn.objects.create(
        interview=interview, sequence=1, question="질문 1", answer="확정 답변"
    )
    answered_turn.user_skipped_at = now
    with pytest.raises(ValidationError):
        answered_turn.full_clean()

    # 2. user_skipped_at이 확정된 턴은 answer 설정 불가 및 user_skipped_at 변경 불가
    skipped_turn = InterviewTurn.objects.create(
        interview=interview, sequence=2, question="질문 2", user_skipped_at=now
    )
    skipped_turn.answer = "뒤늦은 답변"
    with pytest.raises(ValidationError):
        skipped_turn.full_clean()

    skipped_turn.answer = None
    skipped_turn.user_skipped_at = timezone.now() + timezone.timedelta(seconds=10)
    with pytest.raises(ValidationError):
        skipped_turn.full_clean()
