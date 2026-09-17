"""IMP-097: Interview / Reflection LLM Validation Hardening 회귀 테스트다.

- check_grounding_connection 제거 및 자연스러운 의역 허용 검증
- paragraph별 evidence optional 허용 및 exact substring 불변식 유지 검증
- 소량 답변 (1개, 2개, 3개) + Skip 조합에서의 Reflection 초안 생성 검증
- 답변과 Skip 혼합, 짧은 답변 반복 시나리오 검증
- 질문 문장 부호 완화(공감 문장, 마침표) 검증
- 503 파이프라인 에러 분류 및 메시지 개선 검증
"""

from datetime import date

import pytest
from django.urls import reverse

from books.models import Book
from integrations.llm.contracts import (
    GeneratedQuestion,
    ProposedNextQuestion,
    ReflectionSourceTurn,
)
from integrations.llm.fake import (
    FakeAnswerAnalysisProvider,
    FakeNextQuestionProvider,
    FakeQuestionProvider,
)
from readings.models import Reading
from reflections.drafts import (
    ReflectionValidationError,
    build_validated_draft_result,
)
from reflections.models import Interview, InterviewTurn, Reflection
from reflections.services import (
    ensure_first_question,
    process_next_turn,
)
from reflections.views import _pipeline_failure_details


@pytest.fixture(autouse=True)
def default_fake_llm_provider(settings) -> None:
    settings.LLM_PROVIDER = "fake"


@pytest.fixture
def completed_reading(django_user_model) -> Reading:
    user = django_user_model.objects.create_user(username="hardening-user")
    book = Book.objects.create(isbn13="9788937834799", title="Hardening Test Book")
    return Reading.objects.create(
        user=user, book=book, status=Reading.Status.COMPLETED, completed_on=date.today()
    )


@pytest.fixture
def reading(completed_reading) -> Reading:
    return completed_reading


# ---------------------------------------------------------------------------
# 1. Reflection Validation: 의역 허용 및 Hard Validation 유지
# ---------------------------------------------------------------------------


def test_reflection_validation_allows_natural_paraphrase_without_lexical_overlap() -> (
    None
):
    """답변의 quote가 존재하면 어휘 일치가 없어도 의역을 허용한다."""
    turns = [
        ReflectionSourceTurn(
            sequence=1,
            question="결말에 대해 어떻게 생각하시나요?",
            answer="주인공이 마지막에 포기한 게 좀 아쉬웠어요.",
        )
    ]
    sections = [
        {
            "title": "결말에 대한 감상",
            "paragraphs": [
                {
                    "text": "마지막 선택은 독자에게 깊은 아쉬움으로 남았다.",
                    "evidence": [{"sequence": 1, "quote": "포기한 게 좀 아쉬웠어요"}],
                }
            ],
        }
    ]
    result = build_validated_draft_result(
        interview_id=1, turns=turns, raw_sections=sections
    )
    assert len(result.sections) == 1
    assert "마지막 선택은 독자에게 깊은 아쉬움으로 남았다." in result.canonical_markdown


def test_reflection_validation_rejects_fabricated_quote_not_in_answer() -> None:
    """사용자가 말하지 않은 허위 인용구는 여전히 엄격히 거부한다 (Hard Validation)."""
    turns = [
        ReflectionSourceTurn(
            sequence=1,
            question="결말에 대해 어떻게 생각하시나요?",
            answer="주인공이 마지막에 포기한 게 좀 아쉬웠어요.",
        )
    ]
    sections = [
        {
            "title": "결말에 대한 감상",
            "paragraphs": [
                {
                    "text": "주인공의 선택이 훌륭했다고 느꼈다.",
                    "evidence": [
                        {
                            "sequence": 1,
                            "quote": "주인공의 선택이 정말 훌륭했다고 생각했다.",
                        }
                    ],
                }
            ],
        }
    ]
    with pytest.raises(ReflectionValidationError) as exc:
        build_validated_draft_result(interview_id=1, turns=turns, raw_sections=sections)
    assert exc.value.reason_code == "quote_not_in_answer"


def test_reflection_validation_allows_paragraph_without_evidence() -> None:
    """서론이나 종합 문단처럼 인용구가 필요 없는 문단은 evidence: []를 허용한다."""
    turns = [
        ReflectionSourceTurn(
            sequence=1,
            question="어떤 인상을 받았나요?",
            answer="가족의 의미를 다시금 돌아보게 되었습니다.",
        )
    ]
    sections = [
        {
            "title": "도입과 마무리",
            "paragraphs": [
                {
                    "text": "이 책은 많은 생각을 남기게 하는 작품이다.",
                    "evidence": [],  # 서론 문단: 인용 없음
                },
                {
                    "text": "가족 관계의 소중함에 대한 깊은 성찰을 이끌어낸다.",
                    "evidence": [
                        {
                            "sequence": 1,
                            "quote": "가족의 의미를 다시금 돌아보게 되었습니다.",
                        }
                    ],
                },
            ],
        }
    ]
    result = build_validated_draft_result(
        interview_id=1, turns=turns, raw_sections=sections
    )
    assert len(result.sections[0]["paragraphs"]) == 2
    assert result.sections[0]["paragraphs"][0]["evidence"] == []


# ---------------------------------------------------------------------------
# 2. 질문 문장부호 검증 완화 (Soft Validation)
# ---------------------------------------------------------------------------


def test_first_question_allows_period_and_multiple_sentences(completed_reading) -> None:
    """첫 질문에 공감 문장이나 마침표가 포함되어도 거부되지 않는다."""
    interview = Interview.objects.create(
        reading=completed_reading,
        book=completed_reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    turn = ensure_first_question(
        user=completed_reading.user,
        interview=interview,
        provider=FakeQuestionProvider(
            result=GeneratedQuestion(
                question="책을 완독하셨군요. 가장 인상 깊었던 장면은 무엇인가요?"
            )
        ),
    )
    assert turn.sequence == 1
    assert "책을 완독하셨군요. 가장 인상 깊었던 장면은 무엇인가요?" == turn.question


def test_next_question_allows_period_and_exclamation(completed_reading) -> None:
    """후속 질문에서도 공감 문장이나 마침표/느낌표가 포함된 복문이 허용된다."""
    interview = Interview.objects.create(
        reading=completed_reading,
        book=completed_reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.IN_PROGRESS,
    )
    turn1 = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="첫 인상은 어떠셨나요?",
        answer="주인공의 결단이 놀라웠습니다.",
    )
    result = process_next_turn(
        user=completed_reading.user,
        interview=interview,
        turn=turn1,
        analysis_provider=FakeAnswerAnalysisProvider(),
        next_provider=FakeNextQuestionProvider(
            result=ProposedNextQuestion(
                kind="question",
                question="주인공의 결단이 놀라웠죠! 어떤 기분이 드셨나요?",
                focus_axis="REACTION",
                grounding_quote=turn1.answer,
                skip_reason=None,
            )
        ),
    )
    assert not result.skipped
    assert result.turn.sequence == 2
    assert "주인공의 결단이 놀라웠죠!" in result.turn.question


# ---------------------------------------------------------------------------
# 3. 소량 답변 + Skip 조합에서의 Reflection 초안 생성 회귀 검증
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("answered_count", [1, 2, 3])
def test_reflection_generation_succeeds_with_few_answers_and_skips(
    client, reading, answered_count: int
) -> None:
    """소량 답변(1~3개)과 Skip 조합에서도 Reflection 생성이 503 없이 성공한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )

    sample_answers = [
        "처음 주인공의 고독에 깊이 공감했어요.",
        "중반부 갈등 장면에서는 답답함이 컸습니다.",
        "결말의 선택은 아쉬움과 여운을 동시에 남겼어요.",
    ]

    # answered_count 만큼 답변 턴 생성
    for seq in range(1, answered_count + 1):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=seq,
            question=f"질문 {seq}번입니다?",
            answer=sample_answers[seq - 1],
        )

    # 나머지 턴들은 건너뛴 상태로 생성
    for seq in range(answered_count + 1, 11):
        InterviewTurn.objects.create(
            interview=interview,
            sequence=seq,
            question=f"건너뛴 질문 {seq}번입니다?",
            answer=None,
        )

    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    # Reflection 생성 요청 (일반 POST -> 302 redirect)
    response = client.post(url)
    assert response.status_code == 302, (
        f"Expected 302 redirect but got {response.status_code}"
    )

    # DB에 단일 Reflection이 안전하게 생성되었는지 확인
    reflection = Reflection.objects.filter(interview=interview).first()
    assert reflection is not None
    assert reflection.status == Reflection.Status.DRAFT
    assert len(reflection.draft_markdown) > 0


def test_mixed_answer_and_skip_sequence_generates_reflection(client, reading) -> None:
    """답변과 건너뛰기가 중간중간 섞여 있어도 Reflection 생성이 정상 작동한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    # Turn 1: Answer
    InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="질문 1?",
        answer="첫 번째 답변입니다.",
    )
    # Turn 2: Skip
    InterviewTurn.objects.create(
        interview=interview, sequence=2, question="질문 2?", answer=None
    )
    # Turn 3: Answer
    InterviewTurn.objects.create(
        interview=interview,
        sequence=3,
        question="질문 3?",
        answer="세 번째 답변입니다.",
    )
    # Turn 4: Skip
    InterviewTurn.objects.create(
        interview=interview, sequence=4, question="질문 4?", answer=None
    )

    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    response = client.post(url)
    assert response.status_code == 302
    assert Reflection.objects.filter(interview=interview).exists()


def test_repeated_short_answers_generates_reflection(client, reading) -> None:
    """'네', '그냥 그랬어요' 등 매우 짧은 단답형이 반복되어도 성공한다."""
    interview = Interview.objects.create(
        reading=reading,
        book=reading.book,
        knowledge_readiness=Interview.KnowledgeReadiness.READY,
        status=Interview.Status.REFLECTION_READY,
    )
    short_answers = ["네", "그냥 그랬어요", "잘 모르겠어요"]
    for i, ans in enumerate(short_answers, 1):
        InterviewTurn.objects.create(
            interview=interview, sequence=i, question=f"질문 {i}?", answer=ans
        )

    client.force_login(reading.user)
    url = reverse("reflections:reflection_generate", args=[interview.pk])

    response = client.post(url)
    assert response.status_code == 302
    reflection = Reflection.objects.get(interview=interview)
    assert reflection.status == Reflection.Status.DRAFT


# ---------------------------------------------------------------------------
# 4. Error Classification & Failure Policy 검증
# ---------------------------------------------------------------------------


def test_pipeline_failure_details_classifies_reflection_errors() -> None:
    """Reflection 관련 에러가 친절한 에러 문구로 분류된다."""
    err_validation = ReflectionValidationError("테스트 오류")
    details_val = _pipeline_failure_details(err_validation)
    assert details_val["pipeline_error_code"] == "ReflectionValidationError"
    assert (
        "독서노트 초안을 구성하는 중 일시적인 문제가 발생했습니다"
        in details_val["pipeline_error_reason"]
    )

    from integrations.llm.contracts import ReflectionGenerationRejected

    err_rejected = ReflectionGenerationRejected("테스트 거부")
    details_rej = _pipeline_failure_details(err_rejected)
    assert (
        "독서노트 초안을 구성하는 중 일시적인 문제가 발생했습니다"
        in details_rej["pipeline_error_reason"]
    )
