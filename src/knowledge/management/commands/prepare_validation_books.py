from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from knowledge.services import prepare_validation_books


class Command(BaseCommand):
    """검증용 대표 도서 3권과 승인 Claim을 멱등하게 준비한다."""

    help = "검증용 대표 도서 3권과 승인 Knowledge Claim을 멱등 적용합니다."

    def handle(self, *args, **options) -> None:
        """검증 도서 세트를 원자적으로 준비하고 결과를 보고한다."""
        del args, options
        try:
            result = prepare_validation_books()
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error

        self.stdout.write(
            self.style.SUCCESS(
                "검증 도서 준비 완료: "
                f"도서 생성 {result.books_created}건, 재사용 {result.books_reused}건, "
                f"Claim 생성 {result.claims_created}건, 재사용 {result.claims_reused}건"
            )
        )
