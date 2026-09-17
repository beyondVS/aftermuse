"""AfterMuse Interview / Reflection Mechanical Proxy 완화 핵심 회귀 테스트.

유지 대상 핵심 회귀:
A. 자연스러운 한국어 semantic grounding 허용 (조사/어미 변화, 의역)
B. 확인되지 않은 grounding quote 거부 (source invariant 유지)
C. Semantic blacklist 표현이 실제 Reflection pipeline을 정상 통과
D. READY_LIMITED 상태에서 열린 cue 질문 허용
"""

from datetime import date
from typing import Any

import pytest

from books.models import Book
from integrations.llm.contracts import (
    ProposedNextQuestion,
    ProposedReflectionDraft,
    QuestionGenerationRejected,
)
from integrations.llm.fake import (
    FakeAnswerAnalysisProvider,
    FakeNextQuestionProvider,
    FakeReflectionProvider,
)
from readings.models import Reading
from reflections.drafts import generate_reflection_draft
from reflections.models import Interview, InterviewTurn
from reflections.services import process_next_turn, start_interview


@pytest.fixture
def relaxed_test_setup(db, django_user_model) -> dict[str, Any]:
    """테스트용 완독 Reading 및 IN_PROGRESS Interview를 준비한다."""
    user = django_user_model.objects.create_user(username="relaxed-tester")
    book = Book.objects.create(isbn13="9788937834999", title="기술과 인간")
    reading = Reading.objects.create(
        user=user,
        book=book,
        status=Reading.Status.COMPLETED,
        completed_on=date(2026, 9, 18),
    )
    started = start_interview(user=user, reading=reading)
    return {"user": user, "reading": reading, "interview": started.interview}


# ===========================================================================
# A. 자연스러운 한국어 semantic grounding 허용
# ===========================================================================


def test_follow_up_question_allows_semantic_grounding_without_lexical_overlap(
    relaxed_test_setup,
) -> None:
    """사용자 답변과 질문 사이에 lexical exact overlap이 없어도
    grounding_quote가 확정 답변의 substring이면 정상 허용된다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]

    turn1 = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="어떤 부분이 가장 인상 깊었나요?",
        answer="그 장면이 무서웠어요.",
    )

    # grounding_quote는 답변 원문의 정확한 substring
    # 질문 문장은 '어떤 장면을 특히 무섭게 느꼈나요?'
    # (조사/어미 변화: 장면이!=장면을, 무서웠어요!=무섭게)
    result = process_next_turn(
        user=user,
        interview=interview,
        turn=turn1,
        analysis_provider=FakeAnswerAnalysisProvider(),
        next_provider=FakeNextQuestionProvider(
            result=ProposedNextQuestion(
                kind="question",
                question="어떤 장면을 특히 무섭게 느꼈나요?",
                focus_axis="REACTION",
                grounding_quote="그 장면이 무서웠어요",
                skip_reason=None,
            )
        ),
    )

    assert not result.skipped
    assert result.turn.sequence == 2
    assert result.turn.question == "어떤 장면을 특히 무섭게 느꼈나요?"


# ===========================================================================
# B. 확인되지 않은 grounding quote는 계속 거부
# ===========================================================================


def test_follow_up_question_rejects_unconfirmed_grounding_quote(
    relaxed_test_setup,
) -> None:
    """grounding_quote가 실제 확정 답변에 없는 임의 문자열인 경우는 거부된다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]

    turn1 = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="어떤 부분이 가장 인상 깊었나요?",
        answer="그 장면이 무서웠어요.",
    )

    with pytest.raises(QuestionGenerationRejected):
        process_next_turn(
            user=user,
            interview=interview,
            turn=turn1,
            analysis_provider=FakeAnswerAnalysisProvider(),
            next_provider=FakeNextQuestionProvider(
                result=ProposedNextQuestion(
                    kind="question",
                    question="어떤 장면을 특히 무섭게 느꼈나요?",
                    focus_axis="REACTION",
                    grounding_quote="존재하지 않는 사용자 발화 인용",
                    skip_reason=None,
                )
            ),
        )


# ===========================================================================
# C. Semantic blacklist 표현이 실제 Reflection pipeline을 통과
# ===========================================================================


def test_reflection_draft_pipeline_allows_general_technical_terms(
    relaxed_test_setup,
) -> None:
    """Reflection 파이프라인에서 데이터베이스, 시스템 프롬프트, 웹 검색,
    관리자 권한 등 일반 기술 표현이 포함되어도 거부되지 않고 정상 생성된다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]

    answer = (
        "이 책을 읽으면서 데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈다. "
        "시스템 프롬프트가 결과에 미치는 영향이 인상적이었고, "
        "웹 검색으로 관련 내용을 더 찾아보고 싶었다. "
        "관리자 권한의 역할도 다시 생각해보게 되었다."
    )
    InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="어떤 점을 느끼셨나요?",
        answer=answer,
    )

    title = "데이터베이스 및 시스템 프롬프트 고찰"
    paragraph_text = (
        "이 책을 읽으면서 데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈다. "
        "시스템 프롬프트가 결과에 미치는 영향이 인상적이었고, "
        "관련 내용을 웹 검색으로 다시 찾아보고 싶었다. "
        "관리자 권한 역시 신중하게 다루어야 함을 배웠다."
    )

    draft_proposal = ProposedReflectionDraft(
        sections=[
            {
                "title": title,
                "paragraphs": [
                    {
                        "text": paragraph_text,
                        "evidence": [
                            {
                                "sequence": 1,
                                "quote": (
                                    "데이터베이스 구조와 인간의 기억이 "
                                    "비슷하다고 느꼈다"
                                ),
                            }
                        ],
                    }
                ],
            }
        ]
    )

    interview.status = Interview.Status.REFLECTION_READY
    interview.save(update_fields=["status"])

    provider = FakeReflectionProvider(result=draft_proposal)
    draft_result = generate_reflection_draft(
        user=user, interview=interview, provider=provider
    )
    assert draft_result is not None
    assert draft_result.sections[0]["title"] == title
    assert "데이터베이스" in draft_result.sections[0]["paragraphs"][0]["text"]
    assert "시스템 프롬프트" in draft_result.sections[0]["paragraphs"][0]["text"]
    assert "웹 검색" in draft_result.sections[0]["paragraphs"][0]["text"]
    assert "관리자 권한" in draft_result.sections[0]["paragraphs"][0]["text"]


# ===========================================================================
# D. READY_LIMITED 열린 cue 질문 허용
# ===========================================================================


def test_ready_limited_allows_open_cue_question(
    relaxed_test_setup,
) -> None:
    """READY_LIMITED 상태에서 등장인물이나 사건 같은 일반 cue 단어가 포함되어도
    단순 문자열 매칭으로 reject되지 않는다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]
    assert interview.knowledge_readiness == Interview.KnowledgeReadiness.READY_LIMITED

    turn1 = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="책을 읽고 어떤 생각이 먼저 떠올랐나요?",
        answer="생각보다 많은 질문을 던지는 책이었습니다.",
    )

    result = process_next_turn(
        user=user,
        interview=interview,
        turn=turn1,
        analysis_provider=FakeAnswerAnalysisProvider(),
        next_provider=FakeNextQuestionProvider(
            result=ProposedNextQuestion(
                kind="question",
                question="기억나는 등장인물이나 사건이 있었나요?",
                focus_axis="MEMORY",
                grounding_quote="많은 질문을 던지는 책",
                skip_reason=None,
            )
        ),
    )

    assert not result.skipped
    assert result.turn.sequence == 2
    assert result.turn.question == "기억나는 등장인물이나 사건이 있었나요?"
