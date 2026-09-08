import json
from json import JSONDecodeError
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from knowledge.services import seed_book_knowledge

SEED_DATA_PATH = (
    Path(__file__).resolve().parents[2] / "seed_data" / "book_knowledge.json"
)


class Command(BaseCommand):
    """승인된 수동 Book Knowledge Seed를 적용한다."""

    help = "승인된 수동 Book Knowledge Seed를 멱등 적용합니다."

    def handle(self, *args, **options) -> None:
        """JSON 입력을 해석하고 Seed Service 결과만 사용자에게 보고한다."""
        del args, options
        entries = _load_seed_entries()
        try:
            result = seed_book_knowledge(entries)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error
        self.stdout.write(
            self.style.SUCCESS(
                "Book Knowledge Seed 완료: "
                f"생성 {result.created}건, 재사용 {result.reused}건"
            )
        )


def _load_seed_entries() -> list[dict[str, object]]:
    try:
        with SEED_DATA_PATH.open(encoding="utf-8") as seed_file:
            entries = json.load(seed_file)
    except (JSONDecodeError, OSError) as error:
        raise CommandError("Book Knowledge Seed JSON을 읽을 수 없습니다.") from error
    if not isinstance(entries, list):
        raise CommandError("Book Knowledge Seed JSON은 항목 목록이어야 합니다.")
    return entries
