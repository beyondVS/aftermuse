"""Reflection 초안 생성을 위한 공통 스키마, 지침, payload 빌더 및 wire 디코더다."""

import json
from typing import Any

from integrations.llm.contracts import (
    ProposedReflectionDraft,
    ReflectionGenerationContext,
    ReflectionGenerationRejected,
)


def build_reflection_schema() -> dict[str, Any]:
    """Provider가 반환할 Reflection 초안의 엄격한 구조화 JSON 스키마를 제공한다."""
    return {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "paragraphs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "evidence": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "sequence": {"type": "integer"},
                                                "quote": {"type": "string"},
                                            },
                                            "required": ["sequence", "quote"],
                                            "additionalProperties": False,
                                        },
                                    },
                                },
                                "required": ["text", "evidence"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["title", "paragraphs"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["sections"],
        "additionalProperties": False,
    }


def build_reflection_instructions() -> str:
    """답변만을 근거로 삼아 왜곡 없이 초안을 작성하도록 지시하는 시스템 프롬프트다."""
    return (
        "당신은 독자가 인터뷰에서 스스로 표현한 생각을 바탕으로 "
        "개인 독서노트 초안을 작성하는 도우미입니다.\n\n"
        "다음 원칙을 엄격히 준수하십시오:\n"
        "1. [근거의 유일성]: 사용자가 '답변(answer)'에서 실제로 언급하고 표현한 "
        "내용만을 모든 서술의 유일한 근거로 삼으십시오. '질문(question)'은 대화의 "
        "문맥을 이해하기 위한 참고용일 뿐이며, 질문에 포함된 개념이나 전제를 "
        "독자가 동의하거나 표현한 생각인 것처럼 서술의 근거로 삼아서는 안 됩니다.\n"
        "2. [임의 추가 금지]: AI가 책의 일반적인 줄거리, 새로운 사실, 지어낸 신념, "
        "독자가 말하지 않은 해석이나 평가를 임의로 추가하지 마십시오.\n"
        "3. [태도와 감정의 보존]: 독자의 유보적 태도, 회의, 의문, 비판, 반대 의견 및 "
        "감정의 강도를 임의로 긍정이나 확신으로 미화하거나 왜곡하지 말고 "
        "원문 그대로 보존하십시오.\n"
        "4. [가변적 구조]: 사용자의 답변 분량과 생각의 흐름에 맞추어 유연하고 "
        "자연스러운 섹션(section)과 문단(paragraph)으로 구성하십시오. "
        "답변이 짧으면 초안도 간결해야 합니다.\n"
        "5. [문단별 근거 인용]: 모든 문단(paragraph)은 해당 서술의 근거가 된 독자의 "
        "확정 답변 순번(sequence)과 답변 원문의 정확한 연속 부분 문자열 "
        "인용구(quote)를 근거(evidence) 목록에 반드시 포함해야 합니다.\n"
        "6. [형식 제약]: 제목(title)은 단일 줄의 평문이어야 하며 마크다운 제목(#), "
        "링크, HTML을 포함할 수 없습니다. 본문 문단(text)에는 마크다운 링크, "
        "자동 링크, 이미지, fenced code, HTML을 포함해서는 안 됩니다. "
        "별도의 마크다운 전체 본문이나 서두/결미 인사말 없이 제공된 JSON 스키마 "
        "규격으로만 응답하십시오."
    )


def build_reflection_payload(context: ReflectionGenerationContext) -> dict[str, Any]:
    """초안 생성에 허용된 확정 인터뷰 턴 snapshot만을 JSON 호환 dict로 직렬화한다."""
    return {
        "turns": [
            {
                "sequence": turn.sequence,
                "question": turn.question,
                "answer": turn.answer,
            }
            for turn in context.turns
        ]
    }


def decode_reflection_payload(raw_data: Any) -> ProposedReflectionDraft:
    """Wire 출력을 검증하여 ProposedReflectionDraft로 변환한다."""
    if isinstance(raw_data, (str, bytes)):
        try:
            parsed = json.loads(raw_data)
        except ValueError, TypeError:
            raise ReflectionGenerationRejected(
                "Wire output is not a valid JSON string",
                reason_code="invalid_json_wire_format",
            ) from None
    elif isinstance(raw_data, dict):
        parsed = raw_data
    else:
        raise ReflectionGenerationRejected(
            f"Wire output must be string or dict, got {type(raw_data).__name__}",
            reason_code="invalid_wire_payload_type",
        )

    if not isinstance(parsed, dict):
        raise ReflectionGenerationRejected(
            "Parsed wire data is not a dictionary",
            reason_code="invalid_wire_root_type",
        )

    if set(parsed.keys()) != {"sections"}:
        if "sections" not in parsed:
            raise ReflectionGenerationRejected(
                "Wire data missing required 'sections' key",
                reason_code="missing_sections_key",
            )
        raise ReflectionGenerationRejected(
            "Wire data contains invalid root keys",
            reason_code="invalid_wire_root_keys",
        )

    raw_sections = parsed["sections"]
    if not isinstance(raw_sections, list):
        raise ReflectionGenerationRejected(
            "'sections' must be a list",
            reason_code="sections_not_a_list",
        )

    return ProposedReflectionDraft(sections=raw_sections)
