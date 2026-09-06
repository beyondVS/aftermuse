"""검색 결과를 선택 전에 session에 짧게 보관하는 정책이다."""

from collections.abc import MutableMapping
from dataclasses import dataclass
from datetime import date
from time import time
from typing import Any
from uuid import uuid4

from integrations.book_metadata.contracts import ProviderBook

CANDIDATES_SESSION_KEY = "book_selection_candidates"
MAX_CANDIDATES = 20
TTL_SECONDS = 15 * 60


class SelectionCandidateError(Exception):
    """선택할 수 없는 session 후보를 나타낸다."""


@dataclass(frozen=True, slots=True)
class BookSelectionCandidate:
    """서버가 저장한 단일 선택 후보다."""

    candidate_id: str
    owner_user_id: str
    created_at: float
    book: ProviderBook


def clear_candidates(session: MutableMapping[str, Any]) -> None:
    """새 검색 시작·빈 결과·오류 시 기존 후보 batch를 제거한다."""
    session.pop(CANDIDATES_SESSION_KEY, None)
    if hasattr(session, "modified"):
        session.modified = True


def store_candidates(
    session: MutableMapping[str, Any],
    owner_user_id: str,
    books: tuple[ProviderBook, ...],
    *,
    now: float | None = None,
) -> tuple[BookSelectionCandidate, ...]:
    """유효 검색 결과를 JSON 기본형 session batch로 저장한다."""
    created_at = time() if now is None else now
    candidates = tuple(
        BookSelectionCandidate(str(uuid4()), str(owner_user_id), created_at, book)
        for book in books[:MAX_CANDIDATES]
    )
    session[CANDIDATES_SESSION_KEY] = {
        "owner_user_id": str(owner_user_id),
        "created_at": created_at,
        "candidates": [_serialize_candidate(candidate) for candidate in candidates],
    }
    if hasattr(session, "modified"):
        session.modified = True
    return candidates


def get_candidate(
    session: MutableMapping[str, Any],
    owner_user_id: str,
    candidate_id: str,
    *,
    now: float | None = None,
) -> BookSelectionCandidate:
    """현재 사용자와 TTL을 검증한 뒤 보관된 후보를 반환한다."""
    batch = session.get(CANDIDATES_SESSION_KEY)
    if not isinstance(batch, dict):
        raise SelectionCandidateError

    created_at = batch.get("created_at")
    stored_owner_id = batch.get("owner_user_id")
    current_time = time() if now is None else now
    if (
        not isinstance(created_at, (int, float))
        or current_time - created_at > TTL_SECONDS
        or stored_owner_id != str(owner_user_id)
    ):
        raise SelectionCandidateError

    candidates = batch.get("candidates")
    if not isinstance(candidates, list):
        raise SelectionCandidateError
    for raw_candidate in candidates:
        candidate = _deserialize_candidate(raw_candidate)
        if candidate is not None and candidate.candidate_id == candidate_id:
            if candidate.owner_user_id == str(owner_user_id):
                return candidate
    raise SelectionCandidateError


def _serialize_candidate(candidate: BookSelectionCandidate) -> dict[str, object]:
    book = candidate.book
    return {
        "candidate_id": candidate.candidate_id,
        "owner_user_id": candidate.owner_user_id,
        "created_at": candidate.created_at,
        "isbn13": book.isbn13,
        "title": book.title,
        "authors": book.authors,
        "publisher": book.publisher,
        "published_date": book.published_date.isoformat()
        if book.published_date is not None
        else None,
        "cover_url": book.cover_url,
        "description": book.description,
        "table_of_contents": book.table_of_contents,
        "external_url": book.external_url,
    }


def _deserialize_candidate(raw_candidate: object) -> BookSelectionCandidate | None:
    if not isinstance(raw_candidate, dict):
        return None
    required = ("candidate_id", "owner_user_id", "isbn13", "title")
    if any(not isinstance(raw_candidate.get(field), str) for field in required):
        return None
    created_at = raw_candidate.get("created_at")
    if not isinstance(created_at, (int, float)):
        return None
    isbn13 = raw_candidate["isbn13"]
    title = raw_candidate["title"].strip()
    if not _is_valid_isbn13(isbn13) or not title:
        return None
    return BookSelectionCandidate(
        candidate_id=raw_candidate["candidate_id"],
        owner_user_id=raw_candidate["owner_user_id"],
        created_at=float(created_at),
        book=ProviderBook(
            isbn13=isbn13,
            title=title,
            authors=_optional_text(raw_candidate.get("authors")),
            publisher=_optional_text(raw_candidate.get("publisher")),
            published_date=_parse_date(raw_candidate.get("published_date")),
            cover_url=_optional_text(raw_candidate.get("cover_url")),
            description=_optional_text(raw_candidate.get("description")),
            table_of_contents=_optional_text(raw_candidate.get("table_of_contents")),
            external_url=_optional_text(raw_candidate.get("external_url")),
        ),
    )


def _is_valid_isbn13(value: str) -> bool:
    return len(value) == 13 and value.isascii() and value.isdecimal()


def _optional_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
