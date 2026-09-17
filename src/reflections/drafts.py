"""Reflection 초안의 유효성 검증, canonical Markdown 조립 및 Service 경계다."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import markdown
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from django.utils.safestring import SafeString, mark_safe

from integrations.llm.contracts import (
    ReflectionGenerationContext,
    ReflectionProvider,
    ReflectionSourceTurn,
)
from reflections.models import Interview, InterviewTurn, Reflection

# ---------------------------------------------------------------------------
# 오류 계층
# ---------------------------------------------------------------------------


class ReflectionDraftError(Exception):
    """Reflection 초안 처리 중 발생하는 상위 오류다."""


class ReflectionPolicyError(ReflectionDraftError):
    """소유권, 관계 또는 Interview 상태가 초안 계약을 위반했다."""

    def __init__(
        self, *args: object, reason_code: str = "reflection_policy_error"
    ) -> None:
        super().__init__(*args)
        self.reason_code = reason_code


class ReflectionValidationError(ReflectionDraftError):
    """초안 구조, 인용, 형식 또는 길이가 계약을 위반했다."""

    def __init__(
        self, *args: object, reason_code: str = "reflection_invalid_output"
    ) -> None:
        super().__init__(*args)
        self.reason_code = reason_code


class ReflectionDraftConflict(ReflectionDraftError):
    """동일 Interview에 이미 다른 Reflection 초안이 저장되어 있다."""

    def __init__(
        self, *args: object, reason_code: str = "reflection_draft_conflict"
    ) -> None:
        super().__init__(*args)
        self.reason_code = reason_code


class ReflectionPersistenceError(ReflectionDraftError):
    """초안 저장 중 데이터베이스 오류가 발생했음을 나타낸다."""

    def __init__(
        self, *args: object, reason_code: str = "reflection_persistence_error"
    ) -> None:
        super().__init__(*args)
        self.reason_code = reason_code


# 식별자 별칭
ReflectionDraftPolicyError = ReflectionPolicyError
ReflectionDraftValidationError = ReflectionValidationError
ReflectionDraftConflictError = ReflectionDraftConflict
ReflectionDraftPersistenceError = ReflectionPersistenceError


# ---------------------------------------------------------------------------
# 초안 불변 결과 객체
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReflectionDraftResult:
    """검증이 완료된 비영속 Reflection 초안 결과다."""

    interview_id: int
    turns: tuple[ReflectionSourceTurn, ...]
    sections: tuple[dict[str, Any], ...]
    canonical_markdown: str

    @property
    def draft_markdown(self) -> str:
        """canonical Markdown과 동일한 초안 본문이다."""
        return self.canonical_markdown


@dataclass(frozen=True, slots=True)
class ReflectionGenerationResult:
    """생성 또는 조회된 영속 Reflection 초안과 신규 생성 여부다."""

    reflection: Reflection
    created: bool


# ---------------------------------------------------------------------------
# 검증 상수 및 정규식
# ---------------------------------------------------------------------------

_MAX_SECTIONS = 10
_MIN_SECTIONS = 1
_MAX_TITLE_LENGTH = 120
_MIN_TITLE_LENGTH = 1
_MAX_PARAGRAPHS_PER_SECTION = 10
_MIN_PARAGRAPHS_PER_SECTION = 1
_MAX_PARAGRAPH_TEXT_LENGTH = 2000
_MIN_PARAGRAPH_TEXT_LENGTH = 1
_MAX_EVIDENCE_PER_PARAGRAPH = 10
_MAX_QUOTE_LENGTH = 500
_MIN_QUOTE_LENGTH = 1
_MAX_DRAFT_MARKDOWN_LENGTH = 22000
_MIN_DRAFT_MARKDOWN_LENGTH = 1
_MAX_REVISED_MARKDOWN_LENGTH = 20000

# HTML 태그, 주석, doctype 감지 (단순 수식 <, >는 제외)
_HTML_DOCTYPE_RE = re.compile(r"<!doctype\b[^>]*>", re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")

# 링크 및 이미지 감지
_MARKDOWN_IMAGE_RE = re.compile(r"!\[.*?\]")
_MARKDOWN_INLINE_LINK_RE = re.compile(r"\[.*?\]\([^\)]*\)")
_MARKDOWN_REF_LINK_RE = re.compile(r"\[.*?\]\[.*?\]")
_MARKDOWN_REF_DEF_RE = re.compile(r"^\s*\[.*?\]:\s*\S+", re.MULTILINE)
_AUTOLINK_URL_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9+.-]*://[^>]*>")
_AUTOLINK_EMAIL_RE = re.compile(r"<[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+>")
_BARE_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)

# Markdown 구문 감지 (title 및 paragraph text 제한용)
_FENCED_CODE_RE = re.compile(r"^(?:`{3,}|~{3,})", re.MULTILINE)
_HEADING_PREFIX_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def check_no_raw_html(text: str) -> None:
    """Raw HTML(태그, 주석, doctype)이 포함되어 있으면 검증 오류를 발생시킨다."""
    if (
        _HTML_DOCTYPE_RE.search(text)
        or _HTML_COMMENT_RE.search(text)
        or _HTML_TAG_RE.search(text)
    ):
        raise ReflectionValidationError(
            "Raw HTML is prohibited",
            reason_code="prohibited_raw_html",
        )


def check_no_links_or_images(text: str) -> None:
    """Markdown/자동/bare 링크 및 이미지가 포함되어 있으면 검증 오류를 발생시킨다."""
    if _MARKDOWN_IMAGE_RE.search(text):
        raise ReflectionValidationError(
            "Images are prohibited", reason_code="prohibited_image"
        )
    if (
        _MARKDOWN_INLINE_LINK_RE.search(text)
        or _MARKDOWN_REF_LINK_RE.search(text)
        or _MARKDOWN_REF_DEF_RE.search(text)
        or _AUTOLINK_URL_RE.search(text)
        or _AUTOLINK_EMAIL_RE.search(text)
        or _BARE_URL_RE.search(text)
    ):
        raise ReflectionValidationError(
            "Links are prohibited", reason_code="prohibited_link"
        )


def validate_section_title(title: Any) -> str:
    """Section title의 타입, 길이, 단일 줄 및 금지 형식을 검증한다."""
    if not isinstance(title, str) or isinstance(title, bool):
        raise ReflectionValidationError(
            "Section title must be a string", reason_code="invalid_title_type"
        )
    if "\n" in title or "\r" in title:
        raise ReflectionValidationError(
            "Section title must be a single line", reason_code="multiline_title"
        )
    stripped = title.strip()
    if not stripped:
        raise ReflectionValidationError(
            "Section title must not be empty or whitespace only",
            reason_code="empty_title",
        )
    if len(title) > _MAX_TITLE_LENGTH or len(title) < _MIN_TITLE_LENGTH:
        raise ReflectionValidationError(
            f"Section title length must be 1–{_MAX_TITLE_LENGTH} characters",
            reason_code="invalid_title_length",
        )
    if stripped.startswith("#"):
        raise ReflectionValidationError(
            "Section title must not start with Markdown heading prefix",
            reason_code="title_heading_prefix",
        )
    if _FENCED_CODE_RE.search(title):
        raise ReflectionValidationError(
            "Section title must not contain fenced code",
            reason_code="title_fenced_code",
        )
    check_no_links_or_images(title)
    check_no_raw_html(title)
    return title


def validate_paragraph_text(text: Any) -> str:
    """Paragraph text의 타입, 길이 및 금지 형식을 검증한다."""
    if not isinstance(text, str) or isinstance(text, bool):
        raise ReflectionValidationError(
            "Paragraph text must be a string", reason_code="invalid_paragraph_type"
        )
    if not text.strip():
        raise ReflectionValidationError(
            "Paragraph text must not be empty or whitespace only",
            reason_code="empty_paragraph_text",
        )
    if len(text) > _MAX_PARAGRAPH_TEXT_LENGTH or len(text) < _MIN_PARAGRAPH_TEXT_LENGTH:
        raise ReflectionValidationError(
            f"Paragraph text length must be 1–{_MAX_PARAGRAPH_TEXT_LENGTH} characters",
            reason_code="invalid_paragraph_length",
        )
    if _HEADING_PREFIX_RE.search(text):
        raise ReflectionValidationError(
            "Paragraph text must not contain heading syntax",
            reason_code="paragraph_heading",
        )
    if _FENCED_CODE_RE.search(text):
        raise ReflectionValidationError(
            "Paragraph text must not contain fenced code",
            reason_code="paragraph_fenced_code",
        )
    check_no_links_or_images(text)
    check_no_raw_html(text)
    return text


def validate_revised_markdown(markdown: str | None) -> str | None:
    """사용자 수정본 Markdown의 길이와 비공백 및 유효한 타입을 검증한다."""
    if markdown is None:
        return None
    if not isinstance(markdown, str) or isinstance(markdown, bool):
        raise ReflectionValidationError(
            "Revised markdown must be a string or None",
            reason_code="invalid_revised_markdown_type",
        )
    if not markdown.strip():
        raise ReflectionValidationError(
            "Revised markdown must not be empty or whitespace only",
            reason_code="empty_revised_markdown",
        )
    if len(markdown) > _MAX_REVISED_MARKDOWN_LENGTH:
        raise ReflectionValidationError(
            f"Revised markdown must not exceed "
            f"{_MAX_REVISED_MARKDOWN_LENGTH} characters",
            reason_code="revised_markdown_too_long",
        )
    return markdown


def render_canonical_markdown(sections: Sequence[dict[str, Any]]) -> str:
    """검증된 sections에서 공백 줄로 연결된 canonical Markdown을 조립한다."""
    blocks: list[str] = []
    for section in sections:
        blocks.append(f"## {section['title']}")
        for p in section["paragraphs"]:
            blocks.append(p["text"])
    return "\n\n".join(blocks)


def _validate_evidence_item(
    raw_ev: Any,
    e_idx: int,
    turns_by_seq: dict[int, ReflectionSourceTurn],
    seen_evidence_keys: set[tuple[int, str]],
) -> dict[str, Any]:
    if not isinstance(raw_ev, dict):
        raise ReflectionValidationError(
            f"Evidence {e_idx} must be an object",
            reason_code="invalid_evidence_type",
        )
    if set(raw_ev.keys()) != {"sequence", "quote"}:
        raise ReflectionValidationError(
            f"Evidence {e_idx} has invalid keys",
            reason_code="invalid_evidence_keys",
        )

    seq = raw_ev["sequence"]
    if not (isinstance(seq, int) and not isinstance(seq, bool) and seq > 0):
        raise ReflectionValidationError(
            "Evidence sequence must be a positive integer",
            reason_code="invalid_evidence_sequence",
        )
    if seq not in turns_by_seq:
        raise ReflectionValidationError(
            "Evidence sequence does not match any confirmed turn in snapshot",
            reason_code="unknown_evidence_sequence",
        )

    quote = raw_ev["quote"]
    if not isinstance(quote, str) or isinstance(quote, bool):
        raise ReflectionValidationError(
            "Evidence quote must be a string",
            reason_code="invalid_quote_type",
        )
    if not quote.strip():
        raise ReflectionValidationError(
            "Evidence quote must not be empty or whitespace only",
            reason_code="empty_quote",
        )
    if len(quote) < _MIN_QUOTE_LENGTH or len(quote) > _MAX_QUOTE_LENGTH:
        raise ReflectionValidationError(
            f"Evidence quote length must be "
            f"{_MIN_QUOTE_LENGTH}–{_MAX_QUOTE_LENGTH} characters",
            reason_code="invalid_quote_length",
        )

    ev_key = (seq, quote)
    if ev_key in seen_evidence_keys:
        raise ReflectionValidationError(
            "Duplicate evidence in same paragraph",
            reason_code="duplicate_evidence",
        )
    seen_evidence_keys.add(ev_key)

    target_turn = turns_by_seq[seq]
    if quote not in target_turn.answer:
        raise ReflectionValidationError(
            f"Quote is not an exact substring of answer in turn sequence {seq}",
            reason_code="quote_not_in_answer",
        )

    return {"sequence": seq, "quote": quote}


def _validate_single_paragraph(
    raw_p: Any,
    p_idx: int,
    s_idx: int,
    turns_by_seq: dict[int, ReflectionSourceTurn],
) -> dict[str, Any]:
    if not isinstance(raw_p, dict):
        raise ReflectionValidationError(
            f"Paragraph {p_idx} in section {s_idx} must be an object",
            reason_code="invalid_paragraph_type",
        )
    if set(raw_p.keys()) != {"text", "evidence"}:
        raise ReflectionValidationError(
            f"Paragraph {p_idx} in section {s_idx} has invalid keys",
            reason_code="invalid_paragraph_keys",
        )

    p_text = validate_paragraph_text(raw_p["text"])
    raw_evidences = raw_p["evidence"]

    if not isinstance(raw_evidences, (list, tuple)) or isinstance(
        raw_evidences, (str, bytes)
    ):
        raise ReflectionValidationError(
            f"Evidence in paragraph {p_idx} must be a list",
            reason_code="invalid_evidence_type",
        )
    if len(raw_evidences) > _MAX_EVIDENCE_PER_PARAGRAPH:
        raise ReflectionValidationError(
            f"Evidence count must not exceed {_MAX_EVIDENCE_PER_PARAGRAPH}",
            reason_code="invalid_evidence_count",
        )

    seen_evidence_keys: set[tuple[int, str]] = set()
    validated_evidences = [
        _validate_evidence_item(raw_ev, e_idx, turns_by_seq, seen_evidence_keys)
        for e_idx, raw_ev in enumerate(raw_evidences)
    ]

    return {"text": p_text, "evidence": validated_evidences}


def _validate_single_section(
    raw_sec: Any,
    s_idx: int,
    turns_by_seq: dict[int, ReflectionSourceTurn],
) -> dict[str, Any]:
    if not isinstance(raw_sec, dict):
        raise ReflectionValidationError(
            f"Section {s_idx} must be an object", reason_code="invalid_section_type"
        )
    if set(raw_sec.keys()) != {"title", "paragraphs"}:
        raise ReflectionValidationError(
            f"Section {s_idx} has invalid keys",
            reason_code="invalid_section_keys",
        )

    title = validate_section_title(raw_sec["title"])
    raw_paragraphs = raw_sec["paragraphs"]

    if not isinstance(raw_paragraphs, (list, tuple)) or isinstance(
        raw_paragraphs, (str, bytes)
    ):
        raise ReflectionValidationError(
            f"Paragraphs in section {s_idx} must be a list",
            reason_code="invalid_paragraphs_type",
        )
    if (
        len(raw_paragraphs) < _MIN_PARAGRAPHS_PER_SECTION
        or len(raw_paragraphs) > _MAX_PARAGRAPHS_PER_SECTION
    ):
        raise ReflectionValidationError(
            f"Paragraphs count in section {s_idx} must be "
            f"{_MIN_PARAGRAPHS_PER_SECTION}–{_MAX_PARAGRAPHS_PER_SECTION}",
            reason_code="invalid_paragraphs_count",
        )

    validated_paragraphs = [
        _validate_single_paragraph(raw_p, p_idx, s_idx, turns_by_seq)
        for p_idx, raw_p in enumerate(raw_paragraphs)
    ]
    return {"title": title, "paragraphs": validated_paragraphs}


def validate_draft_structure(
    raw_sections: Any,
    turns_by_seq: dict[int, ReflectionSourceTurn],
) -> tuple[dict[str, Any], ...]:
    """sections 배열의 타입, 개수, 키 집합, 근거 인용 및 연결을 엄격하게 검증한다."""
    if not isinstance(raw_sections, (list, tuple)) or isinstance(
        raw_sections, (str, bytes)
    ):
        raise ReflectionValidationError(
            "Sections must be a list", reason_code="invalid_sections_type"
        )
    if len(raw_sections) < _MIN_SECTIONS or len(raw_sections) > _MAX_SECTIONS:
        raise ReflectionValidationError(
            f"Sections count must be {_MIN_SECTIONS}–{_MAX_SECTIONS}",
            reason_code="invalid_sections_count",
        )

    validated = [
        _validate_single_section(raw_sec, s_idx, turns_by_seq)
        for s_idx, raw_sec in enumerate(raw_sections)
    ]
    return tuple(validated)


def build_validated_draft_result(
    interview_id: int,
    turns: Sequence[ReflectionSourceTurn],
    raw_sections: Any,
) -> ReflectionDraftResult:
    """raw proposal sections를 검증하고 canonical Markdown 결과를 반환한다."""
    turns_tuple = tuple(turns)
    turns_by_seq = {t.sequence: t for t in turns_tuple}

    validated_sections = validate_draft_structure(raw_sections, turns_by_seq)
    canonical_md = render_canonical_markdown(validated_sections)

    if (
        len(canonical_md) < _MIN_DRAFT_MARKDOWN_LENGTH
        or len(canonical_md) > _MAX_DRAFT_MARKDOWN_LENGTH
    ):
        raise ReflectionValidationError(
            f"Draft markdown length must be "
            f"{_MIN_DRAFT_MARKDOWN_LENGTH}–{_MAX_DRAFT_MARKDOWN_LENGTH} characters, "
            f"got {len(canonical_md)}",
            reason_code="invalid_draft_markdown_length",
        )

    return ReflectionDraftResult(
        interview_id=interview_id,
        turns=turns_tuple,
        sections=validated_sections,
        canonical_markdown=canonical_md,
    )


# ---------------------------------------------------------------------------
# 서비스 경계
# ---------------------------------------------------------------------------


def get_reflection_draft(*, user: Any, interview: Interview) -> Reflection | None:
    """소유자 범위에서 Interview의 Reflection을 조회하거나 없으면 None을 반환한다."""
    scoped_interview = Interview.objects.filter(
        pk=interview.pk, reading__user=user
    ).first()
    if scoped_interview is None:
        raise ReflectionPolicyError(
            "Interview does not exist or does not belong to the user",
            reason_code="interview_not_found_or_forbidden",
        )
    return Reflection.objects.filter(interview=scoped_interview).first()


def generate_reflection_draft(
    *,
    user: Any,
    interview: Interview,
    provider: ReflectionProvider | None = None,
) -> ReflectionDraftResult:
    """소유자 범위와 상태를 검증하고 Provider를 통해 비영속 결과를 생성한다."""
    scoped_interview = (
        Interview.objects.filter(pk=interview.pk, reading__user=user)
        .select_related("reading", "book")
        .first()
    )
    if scoped_interview is None:
        raise ReflectionPolicyError(
            "Interview does not exist or does not belong to the user",
            reason_code="interview_not_found_or_forbidden",
        )

    if scoped_interview.status != Interview.Status.REFLECTION_READY:
        raise ReflectionPolicyError(
            f"Interview status must be REFLECTION_READY, got {scoped_interview.status}",
            reason_code="interview_not_reflection_ready",
        )

    if scoped_interview.book_id != scoped_interview.reading.book_id:
        raise ReflectionPolicyError(
            "Interview book does not match reading book",
            reason_code="book_relationship_mismatch",
        )

    turns = list(
        InterviewTurn.objects.filter(interview=scoped_interview).order_by("sequence")
    )
    confirmed_turns = [t for t in turns if t.answer and t.answer.strip()]

    if not confirmed_turns:
        raise ReflectionPolicyError(
            "No confirmed answers found in interview",
            reason_code="no_confirmed_answers",
        )

    if len(confirmed_turns) > 10:
        raise ReflectionPolicyError(
            f"Confirmed turns count exceeds 10: {len(confirmed_turns)}",
            reason_code="too_many_confirmed_turns",
        )

    for t in confirmed_turns:
        if len(t.answer) > 2000:
            raise ReflectionPolicyError(
                f"Turn answer exceeds 2,000 characters in sequence {t.sequence}",
                reason_code="turn_answer_too_long",
            )

    if provider is None:
        from integrations.llm.factory import get_reflection_provider

        resolved_provider: ReflectionProvider = get_reflection_provider()
    else:
        resolved_provider = provider

    source_turns = tuple(
        ReflectionSourceTurn(
            sequence=t.sequence,
            question=t.question,
            answer=t.answer,
        )
        for t in confirmed_turns
    )
    context = ReflectionGenerationContext(turns=source_turns)

    # 외부 Provider 호출 (DB transaction 및 row lock 없음)
    proposal = resolved_provider.generate_reflection(context)
    raw_sections = proposal.sections if hasattr(proposal, "sections") else proposal

    return build_validated_draft_result(
        interview_id=scoped_interview.pk,
        turns=source_turns,
        raw_sections=raw_sections,
    )


def _validate_save_scope_and_interview(
    scoped_interview: Interview | None,
    result: ReflectionDraftResult,
) -> None:
    if scoped_interview is None:
        raise ReflectionPolicyError(
            "Interview does not exist or does not belong to the user",
            reason_code="interview_not_found_or_forbidden",
        )

    if scoped_interview.status != Interview.Status.REFLECTION_READY:
        raise ReflectionPolicyError(
            f"Interview status must be REFLECTION_READY, got {scoped_interview.status}",
            reason_code="interview_not_reflection_ready",
        )

    if scoped_interview.book_id != scoped_interview.reading.book_id:
        raise ReflectionPolicyError(
            "Interview book does not match reading book",
            reason_code="book_relationship_mismatch",
        )

    if result.interview_id != scoped_interview.pk:
        raise ReflectionValidationError(
            f"Draft result interview_id ({result.interview_id}) "
            f"does not match interview ({scoped_interview.pk})",
            reason_code="draft_result_interview_mismatch",
        )


def _validate_save_turns(
    result_turns: tuple[ReflectionSourceTurn, ...],
    confirmed_turns: list[InterviewTurn],
) -> None:
    if not confirmed_turns:
        raise ReflectionPolicyError(
            "No confirmed answers found in interview",
            reason_code="no_confirmed_answers",
        )

    if len(confirmed_turns) > 10:
        raise ReflectionPolicyError(
            f"Confirmed turns count exceeds 10: {len(confirmed_turns)}",
            reason_code="too_many_confirmed_turns",
        )

    for t in confirmed_turns:
        if len(t.answer) > 2000:
            raise ReflectionPolicyError(
                f"Turn answer exceeds 2,000 characters in sequence {t.sequence}",
                reason_code="turn_answer_too_long",
            )

    if len(result_turns) != len(confirmed_turns):
        raise ReflectionValidationError(
            f"Result turn count ({len(result_turns)}) does not match "
            f"confirmed turns ({len(confirmed_turns)})",
            reason_code="turn_count_mismatch",
        )

    for r_turn, db_turn in zip(result_turns, confirmed_turns, strict=True):
        if (
            r_turn.sequence != db_turn.sequence
            or r_turn.question != db_turn.question
            or r_turn.answer != db_turn.answer
        ):
            raise ReflectionValidationError(
                f"Turn snapshot mismatch at sequence {db_turn.sequence}",
                reason_code="turn_snapshot_mismatch",
            )


def save_reflection_draft(
    *, user: Any, interview: Interview, result: ReflectionDraftResult
) -> Reflection:
    """검증된 ReflectionDraftResult를 최초 초안으로 짧은 트랜잭션에서 영속화한다."""
    scoped_interview = (
        Interview.objects.filter(pk=interview.pk, reading__user=user)
        .select_related("reading", "book")
        .first()
    )
    _validate_save_scope_and_interview(scoped_interview, result)
    assert scoped_interview is not None

    # 확정 답변 목록 조회 및 검증
    db_turns = list(
        InterviewTurn.objects.filter(interview=scoped_interview).order_by("sequence")
    )
    confirmed_turns = [t for t in db_turns if t.answer and t.answer.strip()]
    _validate_save_turns(result.turns, confirmed_turns)

    # sections 및 canonical render 재검증
    turns_by_seq = {t.sequence: t for t in result.turns}
    validated_sections = validate_draft_structure(result.sections, turns_by_seq)
    canonical_md = render_canonical_markdown(validated_sections)

    if canonical_md != result.canonical_markdown:
        raise ReflectionValidationError(
            "Canonical markdown mismatch in draft result",
            reason_code="canonical_markdown_mismatch",
        )

    if (
        len(canonical_md) < _MIN_DRAFT_MARKDOWN_LENGTH
        or len(canonical_md) > _MAX_DRAFT_MARKDOWN_LENGTH
    ):
        raise ReflectionValidationError(
            f"Draft markdown length must be "
            f"{_MIN_DRAFT_MARKDOWN_LENGTH}–{_MAX_DRAFT_MARKDOWN_LENGTH} characters",
            reason_code="invalid_draft_markdown_length",
        )

    with transaction.atomic():
        locked_interview = (
            Interview.objects.select_for_update()
            .filter(pk=scoped_interview.pk, reading__user=user)
            .select_related("reading", "book")
            .first()
        )
        if locked_interview is None:
            raise ReflectionPolicyError(
                "Interview does not exist or does not belong to the user",
                reason_code="interview_not_found_or_forbidden",
            )
        _validate_save_scope_and_interview(locked_interview, result)

        locked_db_turns = list(
            InterviewTurn.objects.filter(interview=locked_interview).order_by(
                "sequence"
            )
        )
        locked_confirmed_turns = [
            t for t in locked_db_turns if t.answer and t.answer.strip()
        ]
        _validate_save_turns(result.turns, locked_confirmed_turns)

        if Reflection.objects.filter(interview=locked_interview).exists():
            raise ReflectionDraftConflict(
                f"Reflection draft already exists for interview {locked_interview.pk}"
            )

        try:
            return Reflection.objects.create(
                interview=locked_interview,
                draft_markdown=canonical_md,
                draft_sections=list(validated_sections),
                revised_markdown=None,
                status=Reflection.Status.DRAFT,
            )
        except IntegrityError as exc:
            raise ReflectionDraftConflict(
                f"Reflection draft already exists for interview {locked_interview.pk}"
            ) from exc
        except DatabaseError as exc:
            raise ReflectionPersistenceError(
                "Failed to persist reflection draft"
            ) from exc


def generate_or_get_reflection_draft(
    *,
    user: Any,
    interview: Interview,
    provider: ReflectionProvider | None = None,
) -> ReflectionGenerationResult:
    """기존 owner Reflection이 있으면 즉시 반환하고,
    없으면 생성 후 저장하여 단일 Reflection으로 수렴한다."""
    existing = Reflection.objects.filter(
        interview_id=interview.pk,
        interview__reading__user=user,
    ).first()
    if existing is not None:
        return ReflectionGenerationResult(reflection=existing, created=False)

    # 비영속 초안 생성 (트랜잭션 밖에서 Provider 호출)
    draft_result = generate_reflection_draft(
        user=user,
        interview=interview,
        provider=provider,
    )

    try:
        saved_reflection = save_reflection_draft(
            user=user,
            interview=interview,
            result=draft_result,
        )
        return ReflectionGenerationResult(reflection=saved_reflection, created=True)
    except ReflectionDraftConflict:
        # 동시 생성 경합 시 owner scope로 재조회하여 성공 수렴
        rechecked = Reflection.objects.filter(
            interview_id=interview.pk,
            interview__reading__user=user,
        ).first()
        if rechecked is not None:
            return ReflectionGenerationResult(reflection=rechecked, created=False)
        raise


def save_reflection_revision(
    *, user: Any, reflection: Reflection, markdown: str
) -> Reflection:
    """사용자가 작성한 수정본을 검증하고 revised_markdown 및 updated_at만 갱신한다."""
    scoped_reflection = (
        Reflection.objects.filter(pk=reflection.pk, interview__reading__user=user)
        .select_related("interview__reading__user")
        .first()
    )
    if scoped_reflection is None:
        raise ReflectionPolicyError(
            "Reflection does not exist or does not belong to the user",
            reason_code="reflection_not_found_or_forbidden",
        )

    if scoped_reflection.status != Reflection.Status.DRAFT:
        raise ReflectionPolicyError(
            "Only DRAFT reflection can be revised, current status: "
            f"{scoped_reflection.status}",
            reason_code="invalid_reflection_status_for_revision",
        )

    validated_md = validate_revised_markdown(markdown)

    with transaction.atomic():
        locked_ref = (
            Reflection.objects.select_for_update()
            .filter(pk=scoped_reflection.pk, interview__reading__user=user)
            .first()
        )
        if locked_ref is None:
            raise ReflectionPolicyError(
                "Reflection does not exist or does not belong to the user",
                reason_code="reflection_not_found_or_forbidden",
            )
        if locked_ref.status != Reflection.Status.DRAFT:
            raise ReflectionPolicyError(
                "Only DRAFT reflection can be revised, current status: "
                f"{locked_ref.status}",
                reason_code="invalid_reflection_status_for_revision",
            )

        locked_ref.revised_markdown = validated_md
        try:
            locked_ref.save(update_fields=["revised_markdown", "updated_at"])
            return locked_ref
        except DatabaseError as exc:
            raise ReflectionPersistenceError(
                "Failed to persist reflection revision"
            ) from exc


def get_current_markdown(reflection: Reflection) -> str:
    """revised_markdown이 있으면 이를, 없으면 draft_markdown을 반환한다."""
    return (
        reflection.revised_markdown
        if reflection.revised_markdown is not None
        else reflection.draft_markdown
    )


def render_markdown_safely(markdown_text: str) -> SafeString:
    """사용자 입력 raw HTML을 무력화한 후 기본 Markdown 시맨틱 구조로 변환한다."""
    # 1. HTML 태그 실행 방지: 모든 '<'를 '&lt;'로 치환하여 브라우저의 raw HTML 실행 차단
    sanitized = markdown_text.replace("<", "&lt;")

    # 2. javascript: / vbscript: / data: URI 스킴 무력화
    sanitized = re.sub(
        r"\]\(\s*(javascript|vbscript|data):",
        r"](unsafe:\1:",
        sanitized,
        flags=re.IGNORECASE,
    )

    # 3. Python-Markdown 변환
    html_output = markdown.markdown(
        sanitized,
        extensions=["extra", "sane_lists"],
    )
    return mark_safe(html_output)


def complete_reflection(*, user: Any, reflection: Reflection) -> Reflection:
    """단일 트랜잭션에서 Reflection과 Interview를 원자적으로 COMPLETED로 전환한다."""
    scoped_reflection = (
        Reflection.objects.filter(pk=reflection.pk, interview__reading__user=user)
        .select_related("interview")
        .first()
    )
    if scoped_reflection is None:
        raise ReflectionPolicyError(
            "Reflection does not exist or does not belong to the user",
            reason_code="reflection_not_found_or_forbidden",
        )

    # 이미 완료된 경우 멱등하게 반환 (completed_at 불변 보존)
    if scoped_reflection.status == Reflection.Status.COMPLETED:
        return scoped_reflection

    with transaction.atomic():
        locked_ref = (
            Reflection.objects.select_for_update()
            .filter(pk=scoped_reflection.pk, interview__reading__user=user)
            .select_related("interview")
            .first()
        )
        if locked_ref is None:
            raise ReflectionPolicyError(
                "Reflection does not exist or does not belong to the user",
                reason_code="reflection_not_found_or_forbidden",
            )
        if locked_ref.status == Reflection.Status.COMPLETED:
            return locked_ref

        locked_interview = (
            Interview.objects.select_for_update()
            .filter(pk=locked_ref.interview_id)
            .first()
        )
        if locked_interview is None:
            raise ReflectionPolicyError(
                "Interview does not exist",
                reason_code="interview_not_found",
            )

        now = timezone.now()
        locked_ref.status = Reflection.Status.COMPLETED
        locked_ref.completed_at = now

        locked_interview.status = Interview.Status.COMPLETED

        try:
            locked_ref.save(update_fields=["status", "completed_at", "updated_at"])
            locked_interview.save(update_fields=["status", "updated_at"])
            return locked_ref
        except DatabaseError as exc:
            raise ReflectionPersistenceError(
                "Failed to complete reflection and interview"
            ) from exc
