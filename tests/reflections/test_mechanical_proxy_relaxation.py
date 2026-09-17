"""AfterMuse Interview / Reflection Mechanical Proxy 완화 회귀 테스트 모음.

시나리오 A: 후속 질문의 lexical grounding 완화 (조사·어미 변화/의역 허용, quote 검증)
시나리오 B: 정상적인 blacklist 표현(데이터베이스, 웹 검색, 관리자 권한 등) 허용
시나리오 C: READY_LIMITED 상태에서 열린 인물/사건/결말 질문 허용
"""

from datetime import date
from typing import Any

import pytest

from books.models import Book
from integrations.llm.contracts import (
    GeneratedQuestion,
    ProposedAnswerAnalysis,
    ProposedCoverageChange,
    ProposedNextQuestion,
    ProposedReflectionDraft,
    QuestionGenerationRejected,
)
from integrations.llm.fake import (
    FakeAnswerAnalysisProvider,
    FakeNextQuestionProvider,
    FakeQuestionProvider,
    FakeReflectionProvider,
)
from readings.models import Reading
from reflections.drafts import (
    generate_reflection_draft,
    validate_paragraph_text,
    validate_section_title,
)
from reflections.models import Interview, InterviewTurn
from reflections.services import (
    analyze_interview_answer,
    ensure_first_question,
    process_next_turn,
    start_interview,
)


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
# 시나리오 A: 후속 질문 semantic grounding
# ===========================================================================


def test_scenario_a_follow_up_question_semantic_grounding_allows_paraphrase(
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


def test_scenario_a_follow_up_question_rejects_unconfirmed_grounding_quote(
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
# 시나리오 B: 정상적인 blacklist 표현 허용
# ===========================================================================


@pytest.mark.parametrize(
    "question_text",
    [
        "이 책을 읽으면서 데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈나요?",
        "시스템 프롬프트가 결과에 미치는 영향에 대해 어떻게 생각하시나요?",
        "관련 내용을 웹 검색으로 다시 찾아보고 싶으셨나요?",
        "관리자 권한에 대한 비유가 인상 깊었나요?",
    ],
)
def test_scenario_b_questions_allow_general_and_technical_terms(
    relaxed_test_setup, question_text
) -> None:
    """첫 질문 및 후속 질문에 일반 기술/지시어 어휘가 포함되어도 정상 허용된다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]

    turn = ensure_first_question(
        user=user,
        interview=interview,
        provider=FakeQuestionProvider(result=GeneratedQuestion(question=question_text)),
    )
    assert turn.sequence == 1
    assert turn.question == question_text


def test_scenario_b_answer_analysis_allows_general_and_technical_terms(
    relaxed_test_setup,
) -> None:
    """답변 분석의 meaning과 evidence에 데이터베이스, 웹 검색 등이
    포함되어도 정상 허용된다."""
    user = relaxed_test_setup["user"]
    interview = relaxed_test_setup["interview"]

    answer = "이 책을 읽으면서 데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈다."
    turn = InterviewTurn.objects.create(
        interview=interview,
        sequence=1,
        question="어떤 점을 느끼셨나요?",
        answer=answer,
    )

    meaning = "데이터베이스 구조와 인간 기억의 유사성을 고찰함"
    evidence = "데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈다"
    analysis_result = ProposedAnswerAnalysis(
        meaning=meaning,
        low_information=False,
        coverage_patch=(ProposedCoverageChange("CONNECTION", "COVERED", evidence),),
    )

    result = analyze_interview_answer(
        user=user,
        interview=interview,
        turn=turn,
        provider=FakeAnswerAnalysisProvider(result=analysis_result),
    )
    assert result.meaning == meaning
    assert len(result.coverage_patch) == 1
    assert result.coverage_patch[0].evidence == evidence


def test_scenario_b_reflection_draft_allows_general_and_technical_terms(
    relaxed_test_setup,
) -> None:
    """Reflection의 section title 및 paragraph text에
    일반 기술/지시어 어휘가 허용된다."""
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
    assert validate_section_title(title) == title

    paragraph_text = (
        "이 책을 읽으면서 데이터베이스 구조와 인간의 기억이 비슷하다고 느꼈다. "
        "시스템 프롬프트가 결과에 미치는 영향이 인상적이었고, "
        "관련 내용을 웹 검색으로 다시 찾아보고 싶었다."
    )
    assert validate_paragraph_text(paragraph_text) == paragraph_text

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


# ===========================================================================
# 시나리오 C: READY_LIMITED 열린 질문 허용
# ===========================================================================


@pytest.mark.parametrize(
    "question_text",
    [
        "기억나는 등장인물이 있었나요?",
        "특별히 떠오르는 사건이나 장면이 있었나요?",
        "결말에 대해 기억나는 점이 있다면 이야기해 주시겠어요?",
    ],
)
def test_scenario_c_ready_limited_allows_open_cue_questions(
    relaxed_test_setup, question_text
) -> None:
    """READY_LIMITED 상태에서 등장인물, 사건, 결말 같은 일반 cue 단어가
    단순 문자열 포함으로 인해 reject되지 않는다."""
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
                question=question_text,
                focus_axis="MEMORY",
                grounding_quote="많은 질문을 던지는 책",
                skip_reason=None,
            )
        ),
    )

    assert not result.skipped
    assert result.turn.sequence == 2
    assert result.turn.question == question_text
