from django.core.validators import RegexValidator
from django.db import models

isbn13_validator = RegexValidator(
    regex=r"\A[0-9]{13}\Z",
    message="ISBN13은 ASCII 숫자 13자리여야 합니다.",
)


class Book(models.Model):
    """ISBN13으로 식별되는 도서 서지정보를 나타낸다."""

    isbn13 = models.CharField(max_length=13, unique=True, validators=[isbn13_validator])
    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=500, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateField(null=True, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    table_of_contents = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(isbn13__regex=r"^[0-9]{13}$"),
                name="books_book_isbn13_ascii_digits",
            ),
            models.CheckConstraint(
                condition=models.Q(title__gt=""),
                name="books_book_title_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return self.title
