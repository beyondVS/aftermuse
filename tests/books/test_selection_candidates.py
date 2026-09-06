from datetime import date

import pytest

from books.selection_candidates import (
    CANDIDATES_SESSION_KEY,
    TTL_SECONDS,
    SelectionCandidateError,
    clear_candidates,
    get_candidate,
    store_candidates,
)
from integrations.book_metadata.contracts import ProviderBook


@pytest.fixture
def book() -> ProviderBook:
    return ProviderBook(
        isbn13="9788937834790",
        title="정의란 무엇인가",
        authors="마이클 샌델",
        publisher="와이즈베리",
        published_date=date(2014, 11, 20),
        cover_url="",
        description="",
        table_of_contents="",
        external_url="",
    )


def test_store_and_get_candidate_uses_json_session_data(book: ProviderBook) -> None:
    session: dict[str, object] = {}

    candidates = store_candidates(session, "10", (book,), now=1000)
    result = get_candidate(session, "10", candidates[0].candidate_id, now=1001)

    assert result.book == book
    assert (
        session[CANDIDATES_SESSION_KEY]["candidates"][0]["published_date"]
        == "2014-11-20"
    )


def test_store_limits_batch_and_clear_removes_it(book: ProviderBook) -> None:
    session: dict[str, object] = {}

    candidates = store_candidates(session, "10", (book,) * 21, now=1000)
    clear_candidates(session)

    assert len(candidates) == 20
    assert CANDIDATES_SESSION_KEY not in session


@pytest.mark.parametrize(
    "owner_id,candidate_id,now",
    [("other", "candidate", 1001), ("10", "candidate", 1000 + TTL_SECONDS + 1)],
)
def test_get_candidate_rejects_owner_mismatch_and_expiry(
    book: ProviderBook, owner_id: str, candidate_id: str, now: float
) -> None:
    session: dict[str, object] = {}
    candidates = store_candidates(session, "10", (book,), now=1000)
    if candidate_id == "candidate":
        candidate_id = candidates[0].candidate_id

    with pytest.raises(SelectionCandidateError):
        get_candidate(session, owner_id, candidate_id, now=now)
