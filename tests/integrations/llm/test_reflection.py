"""Reflection 생성 스키마, 프롬프트, wire 디코딩 및 검증 규칙에 대한 단위 테스트다."""

import json

import pytest

from integrations.llm.contracts import (
    ProposedReflectionDraft,
    ReflectionGenerationContext,
    ReflectionGenerationRejected,
    ReflectionSourceTurn,
)
from integrations.llm.reflection import (
    build_reflection_instructions,
    build_reflection_payload,
    build_reflection_schema,
    decode_reflection_payload,
)
from reflections.drafts import (
    ReflectionValidationError,
    build_validated_draft_result,
    check_no_links_or_images,
    check_no_raw_html,
    validate_paragraph_text,
    validate_revised_markdown,
    validate_section_title,
)


def test_reflection_schema_is_strict_and_hierarchical() -> None:
    """스키마는 sections, paragraphs, evidence 계층만 허용한다."""
    schema = build_reflection_schema()
    assert schema["type"] == "object"
    assert schema["required"] == ["sections"]
    assert schema["additionalProperties"] is False

    sec_schema = schema["properties"]["sections"]["items"]
    assert sec_schema["required"] == ["title", "paragraphs"]
    assert sec_schema["additionalProperties"] is False

    p_schema = sec_schema["properties"]["paragraphs"]["items"]
    assert p_schema["required"] == ["text", "evidence"]
    assert p_schema["additionalProperties"] is False

    ev_schema = p_schema["properties"]["evidence"]["items"]
    assert ev_schema["required"] == ["sequence", "quote"]
    assert ev_schema["additionalProperties"] is False


def test_build_reflection_instructions_and_payload_isolation() -> None:
    """Instructions는 신뢰된 지시사항이고 payload는 turns 데이터만을 전달한다."""
    instructions = build_reflection_instructions()
    assert "답변(answer)" in instructions
    assert "질문(question)" in instructions
    assert "새로운 사실" in instructions
    assert "유보" in instructions

    turn1 = ReflectionSourceTurn(sequence=1, question="질문 1", answer="답변 1")
    turn2 = ReflectionSourceTurn(sequence=2, question="질문 2", answer="답변 2")
    context = ReflectionGenerationContext(turns=(turn1, turn2))

    payload = build_reflection_payload(context)
    assert "turns" in payload
    assert len(payload["turns"]) == 2
    assert payload["turns"][0]["sequence"] == 1
    assert payload["turns"][0]["answer"] == "답변 1"
    # 외부 시스템 상태 변경 등 불필요한 키는 없어야 함
    assert set(payload.keys()) == {"turns"}


def test_decode_reflection_payload_success() -> None:
    """유효한 JSON 문자열 또는 dict에서 결과를 디코딩한다."""
    raw_dict = {
        "sections": [
            {
                "title": "요약 제목",
                "paragraphs": [
                    {
                        "text": "문단 본문 내용입니다.",
                        "evidence": [{"sequence": 1, "quote": "인용구"}],
                    }
                ],
            }
        ]
    }
    # dict 디코딩
    result1 = decode_reflection_payload(raw_dict)
    assert isinstance(result1, ProposedReflectionDraft)
    assert len(result1.sections) == 1

    # JSON 문자열 디코딩
    raw_json = json.dumps(raw_dict)
    result2 = decode_reflection_payload(raw_json)
    assert isinstance(result2, ProposedReflectionDraft)
    assert len(result2.sections) == 1


def test_decode_reflection_payload_rejects_malformed_json_and_types() -> None:
    """잘못된 JSON 형식 등은 ReflectionGenerationRejected를 발생시킨다."""
    with pytest.raises(ReflectionGenerationRejected):
        decode_reflection_payload("invalid json string {")

    with pytest.raises(ReflectionGenerationRejected):
        decode_reflection_payload(["not a dict"])

    with pytest.raises(ReflectionGenerationRejected):
        decode_reflection_payload({"missing_sections": []})


def test_decode_reflection_payload_rejects_extra_root_keys_safely() -> None:
    """Wire dict 또는 JSON의 최상위에 sections 외의 추가 키가 있으면 거부된다."""
    valid_sections = [
        {
            "title": "제목",
            "paragraphs": [
                {
                    "text": "문단 본문",
                    "evidence": [{"sequence": 1, "quote": "인용구"}],
                }
            ],
        }
    ]

    # dict에 extra key (markdown 등 별도 본문) 포함
    dict_with_extra = {
        "sections": valid_sections,
        "markdown": "## 별도 본문이 포함됨",
    }
    with pytest.raises(ReflectionGenerationRejected) as exc:
        decode_reflection_payload(dict_with_extra)
    assert exc.value.reason_code == "invalid_wire_root_keys"

    # JSON 문자열에 extra key 및 synthetic secret 포함 시 오류 문자열에 secret 비노출
    secret_key = "SYNTHETIC_API_SECRET_KEY_9999"
    secret_val = "SUPER_SECRET_PAYLOAD_VALUE_8888"
    json_with_secret = json.dumps(
        {
            "sections": valid_sections,
            secret_key: secret_val,
        }
    )
    with pytest.raises(ReflectionGenerationRejected) as exc:
        decode_reflection_payload(json_with_secret)
    assert exc.value.reason_code == "invalid_wire_root_keys"
    assert secret_key not in str(exc.value)
    assert secret_val not in str(exc.value)


def test_decode_reflection_payload_malformed_json_isolates_error_chain() -> None:
    """JSON 파싱 실패 시 원문 시크릿이 오류 문자열이나 __cause__에 누출되지 않는다."""
    secret_token = "MALFORMED_SECRET_TOKEN_XYZ_123"
    malformed_json = f'{{ {secret_token}: "invalid json'

    with pytest.raises(ReflectionGenerationRejected) as exc:
        decode_reflection_payload(malformed_json)
    assert exc.value.reason_code == "invalid_json_wire_format"
    assert secret_token not in str(exc.value)
    assert exc.value.__cause__ is None


def test_validation_rejects_bool_sequence_and_missing_keys() -> None:
    """sequence가 bool이거나 키가 누락/초과된 제안은 거부된다."""
    turns = [
        ReflectionSourceTurn(sequence=1, question="질문", answer="원문 답변입니다.")
    ]

    # bool sequence 거부 (Python에서 True는 int의 서브클래스이므로 엄격히 차단해야 함)
    bad_bool_seq = [
        {
            "title": "제목",
            "paragraphs": [
                {
                    "text": "원문 답변입니다.",
                    "evidence": [{"sequence": True, "quote": "원문 답변입니다."}],
                }
            ],
        }
    ]
    with pytest.raises(ReflectionValidationError) as exc:
        build_validated_draft_result(
            interview_id=1, turns=turns, raw_sections=bad_bool_seq
        )
    assert exc.value.reason_code == "invalid_evidence_sequence"

    # extra key in section 거부
    extra_key_sec = [
        {
            "title": "제목",
            "paragraphs": [],
            "extra": "value",
        }
    ]
    with pytest.raises(ReflectionValidationError) as exc:
        build_validated_draft_result(
            interview_id=1, turns=turns, raw_sections=extra_key_sec
        )
    assert exc.value.reason_code == "invalid_section_keys"


def test_validation_rejects_quote_copied_from_question_instead_of_answer() -> None:
    """답변이 아닌 질문에서 복사한 인용구는 거부된다."""
    turns = [
        ReflectionSourceTurn(
            sequence=1,
            question="어떤 점이 가장 인상 깊었나요?",
            answer="주인공의 결단력이 마음에 들었습니다.",
        )
    ]
    question_quote = [
        {
            "title": "제목",
            "paragraphs": [
                {
                    "text": "어떤 점이 가장 인상 깊었는지 보았다.",
                    "evidence": [
                        {
                            "sequence": 1,
                            "quote": "인상 깊었나요?",  # 질문에만 있는 어구
                        }
                    ],
                }
            ],
        }
    ]
    with pytest.raises(ReflectionValidationError) as exc:
        build_validated_draft_result(
            interview_id=1, turns=turns, raw_sections=question_quote
        )
    assert exc.value.reason_code == "quote_not_in_answer"


def test_validation_allows_natural_paraphrase_and_optional_evidence() -> None:
    """lexical token 일치 없이도 의역을 허용하고, evidence 빈 배열을 허용한다."""
    turns = [
        ReflectionSourceTurn(sequence=1, question="추천하나요?", answer="네"),
        ReflectionSourceTurn(
            sequence=2, question="이유는?", answer="좋은 통찰이 가득한 책이었습니다."
        ),
    ]

    # 1. 자연스러운 의역 (문단 본문에 quote 어휘가 없어도 substring이면 허용)
    paraphrased_sections = [
        {
            "title": "추천과 이유",
            "paragraphs": [
                {
                    "text": "전반적으로 동의하며 주변에 권하고 싶다는 인상을 받았다.",
                    "evidence": [{"sequence": 1, "quote": "네"}],
                },
                {
                    "text": "삶의 지혜와 깊은 깨달음을 주는 문장들이 큰 울림을 주었다.",
                    "evidence": [
                        {"sequence": 2, "quote": "좋은 통찰이 가득한 책이었습니다."}
                    ],
                },
            ],
        }
    ]
    res = build_validated_draft_result(
        interview_id=1, turns=turns, raw_sections=paraphrased_sections
    )
    assert len(res.sections) == 1
    assert len(res.sections[0]["paragraphs"]) == 2

    # 2. evidence가 빈 배열인 문단 허용 (서론/종합/결론 등 인용이 불필요한 문단)
    empty_evidence_sections = [
        {
            "title": "종합 감상",
            "paragraphs": [
                {
                    "text": "이 책은 결국 선택의 무게에 대해 다시 생각하게 했다.",
                    "evidence": [],
                }
            ],
        }
    ]
    res_empty = build_validated_draft_result(
        interview_id=1, turns=turns, raw_sections=empty_evidence_sections
    )
    assert len(res_empty.sections[0]["paragraphs"][0]["evidence"]) == 0

    # 3. 반면 실제 answer에 없는 허위 quote는 여전히 엄격히 거부 (Hard Validation 유지)
    invalid_quote_sections = [
        {
            "title": "추천",
            "paragraphs": [
                {
                    "text": "전혀 추천하지 않는다고 생각한다.",
                    "evidence": [{"sequence": 1, "quote": "아니요 전혀요"}],
                }
            ],
        }
    ]
    with pytest.raises(ReflectionValidationError) as exc:
        build_validated_draft_result(
            interview_id=1, turns=turns, raw_sections=invalid_quote_sections
        )
    assert exc.value.reason_code == "quote_not_in_answer"


def test_prohibited_formats_in_generated_content() -> None:
    """생성 title 및 text에서 금지된 형식(HTML, 링크 등)을 검증한다."""
    # title에 Markdown heading prefix(#) 거부
    with pytest.raises(ReflectionValidationError) as exc:
        validate_section_title("# 제목입니다")
    assert exc.value.reason_code == "title_heading_prefix"

    # title에 개행 거부
    with pytest.raises(ReflectionValidationError) as exc:
        validate_section_title("제목 1줄\n제목 2줄")
    assert exc.value.reason_code == "multiline_title"

    # paragraph text에 heading 거부
    with pytest.raises(ReflectionValidationError) as exc:
        validate_paragraph_text("문단 내용 시작\n### 소제목\n문단 내용 끝")
    assert exc.value.reason_code == "paragraph_heading"

    # paragraph text에 fenced code 거부
    with pytest.raises(ReflectionValidationError) as exc:
        validate_paragraph_text("코드 예시:\n```python\nprint(1)\n```")
    assert exc.value.reason_code == "paragraph_fenced_code"

    # HTML 태그 거부
    with pytest.raises(ReflectionValidationError):
        check_no_raw_html("여기에 <script>alert(1)</script> 포함")
    with pytest.raises(ReflectionValidationError):
        check_no_raw_html("HTML 주석 <!-- 주석 --> 포함")
    with pytest.raises(ReflectionValidationError):
        check_no_raw_html("<!DOCTYPE html> 태그 포함")

    # 수학 비교 기호 <, >는 허용
    check_no_raw_html("a < b 이고 x > y 이다.")

    # 링크 및 이미지 거부
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images("인라인 링크 [구글](https://google.com)")
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images(
            "참조 링크 [문서][ref] 포함\n\n[ref]: https://google.com"
        )
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images("자동 링크 <https://aftermuse.org>")
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images("자동 이메일 <user@example.com>")
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images("bare URL https://aftermuse.org/doc")
    with pytest.raises(ReflectionValidationError):
        check_no_links_or_images("이미지 ![책 표지](cover.png)")


def test_reflection_title_and_paragraph_allow_general_words() -> None:
    """섹션 제목과 본문 문단에서 일반 기술/지시어 어휘가 허용됨을 검증한다."""
    title = validate_section_title("데이터베이스 및 시스템 상태 정리")
    assert title == "데이터베이스 및 시스템 상태 정리"

    text = validate_paragraph_text(
        "이 책을 읽으면서 데이터베이스 구조와 웹 검색 최적화, "
        "그리고 시스템 프롬프트의 영향을 배웠다."
    )
    assert "데이터베이스" in text


def test_revised_markdown_allows_links_images_html_and_general_words() -> None:
    """사용자 수정본은 링크, 이미지, HTML, 일반 지시어 어휘를 허용한다."""
    valid_revised = (
        "## 내 최종 생각\n\n"
        "책을 읽고 다음 점들을 배웠다:\n"
        "- 첫 번째 배움\n"
        "- 두 번째 배움\n\n"
        "> 인용구 블록도 가능하다.\n\n"
        "수학식: a < b and c > d"
    )
    assert validate_revised_markdown(valid_revised) == valid_revised

    # 링크 포함 시 허용
    link_md = "내 생각과 [참고자료](https://example.com)"
    assert validate_revised_markdown(link_md) == link_md

    # HTML 포함 시 허용 (렌더링 경계에서 안전하게 이스케이프됨)
    html_md = "내 생각 <span style='color:red;'>강조</span>"
    assert validate_revised_markdown(html_md) == html_md

    # 이미지 포함 시 허용
    img_md = "내 생각 ![사진](photo.jpg)"
    assert validate_revised_markdown(img_md) == img_md

    # 일반 어휘 및 지시 패턴 단어 포함 시 허용
    word_md = "내 생각: 데이터베이스를 갱신하라."
    assert validate_revised_markdown(word_md) == word_md


def test_ready_limited_allows_open_recall_and_rejects_unconfirmed_grounding() -> None:
    """READY_LIMITED 프롬프트 정책을 확인하고 열린 회상 질문을 허용하며
    미확인 grounding quote를 거부한다."""
    from datetime import date

    from integrations.llm.contracts import (
        CurrentCoverageItem,
        InterviewQuestionContext,
        NextQuestionContext,
        ProposedNextQuestion,
        QuestionGenerationRejected,
        QuestionPolicy,
    )
    from integrations.llm.interview import _next_question_instructions
    from reflections.services import _validate_next_question

    question_context = InterviewQuestionContext(
        book_title="페스트",
        authors="알베르 카뮈",
        publisher="민음사",
        reading_status="COMPLETED",
        completed_on=date(2026, 9, 12),
        knowledge_readiness="READY_LIMITED",
        knowledge_claims=(),
        policy=QuestionPolicy.MEMORY_CENTERED,
    )
    context = NextQuestionContext(
        question_context=question_context,
        previous_turns=(),
        question="어떤 사건이 기억에 남나요?",
        answer=None,
        meaning=None,
        low_information=False,
        coverage=tuple(
            CurrentCoverageItem(axis, "UNCOVERED")
            for axis in ("MEMORY", "REACTION", "CONNECTION", "AFTERTHOUGHT")
        ),
        budget_mode="NORMAL",
        user_skipped=True,
        skipped_questions=("어떤 사건이 기억에 남나요?",),
    )

    # 1. Prompt 지시문 검증
    instructions = _next_question_instructions(context)
    assert (
        "책의 사건, 인물, 주장 등 확인되지 않은 구체적 사실을 전제하지 말고, "
        "사용자의 기억, 인상, 감정 또는 열린 회상을 묻습니다." in instructions
    )
    assert "사용자가 직전 질문을 건너뛰었습니다(user_skipped=true)." in instructions
    assert (
        "아직 충족되지 않은 축에서 부담 없이 답할 수 있는 "
        "기억이나 인상 중심의 새로운 질문을 제안하세요." in instructions
    )

    # 2. 열린 인물/사건/결말 질문 허용 (기계적 cue로 거부하지 않음)
    proposal_with_open_cue = ProposedNextQuestion(
        kind="question",
        question="기억나는 등장인물이 있었나요?",
        focus_axis="MEMORY",
        grounding_quote=None,
        skip_reason=None,
    )
    validated_open = _validate_next_question(proposal_with_open_cue, context)
    assert validated_open == "기억나는 등장인물이 있었나요?"

    # 3. 미확인 quote를 기반으로 한 grounding 질문 거부
    proposal_with_unconfirmed_quote = ProposedNextQuestion(
        kind="question",
        question="카뮈가 묘사한 페스트의 전개에 대해 어떻게 보셨나요?",
        focus_axis="MEMORY",
        grounding_quote="카뮈가 묘사한 페스트의 전개",
        skip_reason=None,
    )
    with pytest.raises(QuestionGenerationRejected):
        _validate_next_question(proposal_with_unconfirmed_quote, context)

    # 4. 사용자 skip 후 ungrounded 기억/감정 질문 정상 허용
    valid_feeling_proposal = ProposedNextQuestion(
        kind="question",
        question="책을 읽으며 마음속에 떠오른 감정이나 생각은 무엇이었나요?",
        focus_axis="MEMORY",
        grounding_quote=None,
        skip_reason=None,
    )
    validated = _validate_next_question(valid_feeling_proposal, context)
    assert validated == "책을 읽으며 마음속에 떠오른 감정이나 생각은 무엇이었나요?"
