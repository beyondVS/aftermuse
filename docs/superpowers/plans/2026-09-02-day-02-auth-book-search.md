# Day 02 Authentication and Book Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 신규 사용자가 가입·로그인한 뒤 알라딘 기반 도서 검색 결과를
Loading/Empty/Error 상태와 함께 확인할 수 있는 Day 02 흐름을 완성한다.

**Architecture:** Django session auth와 ORM을 `accounts`, `books` 도메인 앱에 두고,
알라딘 요청·응답·실패 변환은 `integrations.aladin` Adapter에 격리한다. `books`의
Service와 Template은 Provider 중립 `ProviderBook` 계약만 사용하며, HTMX는 동일 GET
endpoint의 결과 partial을 점진적으로 교체한다.

**Tech Stack:** Python 3.14, Django 6.1, PostgreSQL 18, Django Templates,
HTMX 2.0.10, Alpine.js CSP 3.17.1, pytest-django, Ruff, uv

**Spec:** `docs/superpowers/specs/2026-09-02-day-02-auth-book-search-design.md`

## Global Constraints

- Python은 `>=3.14,<3.15`, Django는 `~=6.1.0`을 유지한다.
- 새 runtime dependency를 추가하지 않고 Python 표준 라이브러리 HTTP client를 쓴다.
- 모든 외부 호출은 `integrations.aladin` Adapter 뒤에 두고 자동 테스트에서 실제
  알라딘 endpoint를 호출하지 않는다.
- 인증은 Django session auth와 CSRF 보호를 사용하며 로그아웃은 POST만 허용한다.
- 검색만으로 `Book`을 저장하지 않는다. Book upsert와 선택은 IMP-024 범위다.
- 목차와 누락 metadata를 추측해 생성하지 않는다.
- production code보다 실패하는 테스트를 먼저 작성하고 예상한 이유의 실패를 확인한다.
- 문서·주석은 한국어를 우선하고 identifier와 표준 기술 용어는 원문을 유지한다.
- formatter, lint, test, Django check, PostgreSQL migration 검증이 모두 통과하기 전에는
  Day 02 IMP 항목을 완료 처리하지 않는다.
- Custom User 도입 전에 `compose.yaml`의 유일한 named volume `postgres_data`를
  재생성한다. 사용자가 2026-09-02에 이 개발 DB 삭제를 승인했으며 다른 Docker
  volume은 삭제하지 않는다.

---

### Task 1: Custom User 모델과 프로젝트 인증 기반

**Files:**
- Create: `src/accounts/__init__.py`
- Create: `src/accounts/apps.py`
- Create: `src/accounts/models.py`
- Create: `src/accounts/migrations/__init__.py`
- Create: `src/accounts/migrations/0001_initial.py` (Django 생성)
- Modify: `src/config/settings.py`
- Test: `tests/accounts/test_user_model.py`

**Interfaces:**
- Consumes: Django `AbstractUser`와 현재 PostgreSQL 설정
- Produces: `accounts.User`, `AUTH_USER_MODEL = "accounts.User"`

- [ ] **Step 1: Custom User 계약을 고정하는 실패 테스트 작성**

```python
# tests/accounts/test_user_model.py
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model


def test_project_uses_accounts_user_model() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert get_user_model()._meta.label == "accounts.User"


@pytest.mark.django_db
def test_user_password_is_hashed() -> None:
    user_model = get_user_model()

    user = user_model.objects.create_user(
        username="reader",
        password="safe-reading-password",
    )

    assert user.password != "safe-reading-password"
    assert user.check_password("safe-reading-password")
```

- [ ] **Step 2: 테스트가 앱/모델 부재로 실패하는지 확인**

Run: `uv run pytest tests/accounts/test_user_model.py -v`

Expected: FAIL because `settings.AUTH_USER_MODEL` is absent or
`accounts.User` cannot be resolved.

- [ ] **Step 3: 최소 accounts 앱과 User 모델 구현**

```python
# src/accounts/apps.py
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """사용자 계정과 인증 도메인 설정이다."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
```

```python
# src/accounts/models.py
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """AfterMuse 사용자를 나타낸다."""
```

`src/config/settings.py`의 `INSTALLED_APPS`에
`"accounts.apps.AccountsConfig"`를 추가하고 다음 설정을 추가한다.

```python
AUTH_USER_MODEL = "accounts.User"
```

- [ ] **Step 4: 초기 migration 생성 및 모델 테스트 통과 확인**

Run: `uv run python src/manage.py makemigrations accounts`

Expected: `src/accounts/migrations/0001_initial.py` created with a
`CreateModel` operation whose model name is `User`.

Run: `uv run pytest tests/accounts/test_user_model.py -v`

Expected: 2 passed.

- [ ] **Step 5: Task 1 변경 커밋**

```powershell
git add src/accounts src/config/settings.py tests/accounts/test_user_model.py
git commit -m "feat: 사용자 모델 기반 추가"
```

---

### Task 2: 회원가입·로그인·로그아웃 흐름

**Files:**
- Create: `src/accounts/forms.py`
- Create: `src/accounts/urls.py`
- Create: `src/accounts/views.py`
- Create: `src/templates/accounts/signup.html`
- Create: `src/templates/registration/login.html`
- Modify: `src/config/settings.py`
- Modify: `src/config/urls.py`
- Modify: `src/templates/base.html`
- Test: `tests/accounts/test_auth_views.py`

**Interfaces:**
- Consumes: `accounts.User`
- Produces: named URLs `accounts:signup`, `accounts:login`, `accounts:logout`;
  성공한 signup은 session login 후 `settings.LOGIN_REDIRECT_URL`로 이동

- [ ] **Step 1: 사용자 관점의 인증 흐름 실패 테스트 작성**

```python
# tests/accounts/test_auth_views.py
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_signup_creates_and_logs_in_user(client) -> None:
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "new-reader",
            "password1": "A-safe-reading-password-2026",
            "password2": "A-safe-reading-password-2026",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("home")
    assert get_user_model().objects.filter(username="new-reader").exists()
    assert client.session["_auth_user_id"]


@pytest.mark.django_db
def test_signup_shows_duplicate_username_error(client, django_user_model) -> None:
    django_user_model.objects.create_user(username="reader", password="safe-pass")

    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "reader",
            "password1": "A-safe-reading-password-2026",
            "password2": "A-safe-reading-password-2026",
        },
    )

    assert response.status_code == 200
    assert "이미 존재하는 사용자" in response.content.decode()


@pytest.mark.django_db
def test_login_and_post_logout_flow(client, django_user_model) -> None:
    django_user_model.objects.create_user(
        username="reader",
        password="A-safe-reading-password-2026",
    )

    login_response = client.post(
        reverse("accounts:login"),
        {"username": "reader", "password": "A-safe-reading-password-2026"},
    )
    logout_response = client.post(reverse("accounts:logout"))

    assert login_response.status_code == 302
    assert login_response.url == reverse("home")
    assert logout_response.status_code == 302
    assert logout_response.url == reverse("home")
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_logout_rejects_get(client, django_user_model) -> None:
    user = django_user_model.objects.create_user(username="reader", password="safe-pass")
    client.force_login(user)

    response = client.get(reverse("accounts:logout"))

    assert response.status_code == 405
```

- [ ] **Step 2: URL 부재로 RED 상태 확인**

Run: `uv run pytest tests/accounts/test_auth_views.py -v`

Expected: FAIL with `NoReverseMatch` for `accounts`.

- [ ] **Step 3: signup form/view와 auth URLs 구현**

```python
# src/accounts/forms.py
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class SignupForm(UserCreationForm):
    """아이디와 비밀번호로 신규 사용자를 등록한다."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)
```

```python
# src/accounts/views.py
from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from accounts.forms import SignupForm


def signup(request: HttpRequest) -> HttpResponse:
    """신규 사용자를 만들고 즉시 로그인한다."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, "accounts/signup.html", {"form": form})
```

```python
# src/accounts/urls.py
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="logout",
    ),
]
```

`src/config/urls.py`에 `path("accounts/", include("accounts.urls"))`를 추가하고
`src/config/settings.py`에 다음을 추가한다.

```python
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"
```

- [ ] **Step 4: 접근 가능한 auth Template과 공통 navigation 구현**

```django
{# src/templates/accounts/signup.html #}
{% extends "base.html" %}

{% block title %}회원가입 · AfterMuse{% endblock %}

{% block content %}
  <section class="auth-panel" aria-labelledby="signup-title">
    <h1 id="signup-title">회원가입</h1>
    <form method="post">
      {% csrf_token %}
      {{ form.non_field_errors }}
      <div>
        <label for="{{ form.username.id_for_label }}">아이디</label>
        {{ form.username }}
        {{ form.username.errors }}
      </div>
      <div>
        <label for="{{ form.password1.id_for_label }}">비밀번호</label>
        {{ form.password1 }}
        {{ form.password1.errors }}
      </div>
      <div>
        <label for="{{ form.password2.id_for_label }}">비밀번호 확인</label>
        {{ form.password2 }}
        {{ form.password2.errors }}
      </div>
      <button type="submit">계정 만들기</button>
    </form>
  </section>
{% endblock %}
```

```django
{# src/templates/registration/login.html #}
{% extends "base.html" %}

{% block title %}로그인 · AfterMuse{% endblock %}

{% block content %}
  <section class="auth-panel" aria-labelledby="login-title">
    <h1 id="login-title">로그인</h1>
    <form method="post">
      {% csrf_token %}
      {{ form.non_field_errors }}
      <div>
        <label for="{{ form.username.id_for_label }}">아이디</label>
        {{ form.username }}
        {{ form.username.errors }}
      </div>
      <div>
        <label for="{{ form.password.id_for_label }}">비밀번호</label>
        {{ form.password }}
        {{ form.password.errors }}
      </div>
      {% if next %}<input type="hidden" name="next" value="{{ next }}">{% endif %}
      <button type="submit">로그인</button>
    </form>
  </section>
{% endblock %}
```

`base.html` header에는 인증 상태에 따라 다음 구조를 렌더링한다.

```django
<nav aria-label="사용자 메뉴">
  {% if user.is_authenticated %}
    <form method="post" action="{% url 'accounts:logout' %}">
      {% csrf_token %}
      <button type="submit">로그아웃</button>
    </form>
  {% else %}
    <a href="{% url 'accounts:login' %}">로그인</a>
    <a href="{% url 'accounts:signup' %}">회원가입</a>
  {% endif %}
</nav>
```

- [ ] **Step 5: 인증 테스트와 기존 home 테스트 통과 확인**

Run: `uv run pytest tests/accounts/test_auth_views.py tests/test_home_page.py -v`

Expected: all tests pass.

- [ ] **Step 6: Task 2 변경 커밋**

```powershell
git add src/accounts src/config src/templates/accounts src/templates/registration src/templates/base.html tests/accounts/test_auth_views.py
git commit -m "feat: 최소 사용자 인증 흐름 구현"
```

---

### Task 3: ISBN13 중심 Book 모델

**Files:**
- Create: `src/books/__init__.py`
- Create: `src/books/apps.py`
- Create: `src/books/models.py`
- Create: `src/books/migrations/__init__.py`
- Create: `src/books/migrations/0001_initial.py` (Django 생성)
- Modify: `src/config/settings.py`
- Test: `tests/books/test_models.py`

**Interfaces:**
- Consumes: Django ORM와 PostgreSQL
- Produces: `books.Book`과 database-level unique `isbn13`

- [ ] **Step 1: 저장·검증·중복 방지 실패 테스트 작성**

```python
# tests/books/test_models.py
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from books.models import Book


@pytest.mark.django_db
def test_book_stores_core_metadata() -> None:
    book = Book.objects.create(
        isbn13="9788937834790",
        title="정의란 무엇인가",
        authors="마이클 샌델",
        publisher="와이즈베리",
        published_date=date(2014, 11, 20),
        cover_url="https://image.example.test/justice.jpg",
        description="정의에 관한 철학적 질문을 다룬다.",
        table_of_contents="1장 옳은 일 하기",
    )

    saved = Book.objects.get(pk=book.pk)
    assert saved.isbn13 == "9788937834790"
    assert saved.title == "정의란 무엇인가"
    assert saved.authors == "마이클 샌델"
    assert saved.published_date == date(2014, 11, 20)
    assert str(saved) == "정의란 무엇인가"


@pytest.mark.django_db
def test_book_rejects_non_isbn13_value() -> None:
    book = Book(isbn13="893783479X", title="잘못된 ISBN")

    with pytest.raises(ValidationError):
        book.full_clean()


@pytest.mark.django_db
def test_book_prevents_duplicate_isbn13() -> None:
    Book.objects.create(isbn13="9788937834790", title="첫 번째 판본")

    with pytest.raises(IntegrityError), transaction.atomic():
        Book.objects.create(isbn13="9788937834790", title="중복 판본")
```

- [ ] **Step 2: books 앱 부재로 RED 상태 확인**

Run: `uv run pytest tests/books/test_models.py -v`

Expected: collection fails because module `books` does not exist.

- [ ] **Step 3: Book 모델 최소 구현**

```python
# src/books/models.py
from django.core.validators import RegexValidator
from django.db import models

validate_isbn13 = RegexValidator(
    regex=r"^\d{13}$",
    message="ISBN13은 숫자 13자리여야 합니다.",
)


class Book(models.Model):
    """ISBN13으로 구분하는 도서 판본이다."""

    isbn13 = models.CharField(max_length=13, unique=True, validators=[validate_isbn13])
    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=500, blank=True)
    publisher = models.CharField(max_length=255, blank=True)
    published_date = models.DateField(null=True, blank=True)
    cover_url = models.URLField(max_length=1000, blank=True)
    description = models.TextField(blank=True)
    table_of_contents = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.title
```

`src/books/apps.py`에 `BooksConfig`를 정의하고 `INSTALLED_APPS`에
`"books.apps.BooksConfig"`를 추가한다.

- [ ] **Step 4: migration 생성과 모델 테스트 GREEN 확인**

Run: `uv run python src/manage.py makemigrations books`

Expected: `books/0001_initial.py` with one `CreateModel` and unique ISBN column.

Run: `uv run pytest tests/books/test_models.py -v`

Expected: 3 passed.

- [ ] **Step 5: Task 3 변경 커밋**

```powershell
git add src/books src/config/settings.py tests/books/test_models.py
git commit -m "feat: ISBN13 중심 Book 모델 추가"
```

---

### Task 4: 알라딘 Metadata Provider Adapter

**Files:**
- Create: `src/integrations/__init__.py`
- Create: `src/integrations/aladin/__init__.py`
- Create: `src/integrations/aladin/contracts.py`
- Create: `src/integrations/aladin/exceptions.py`
- Create: `src/integrations/aladin/client.py`
- Modify: `src/config/settings.py`
- Test: `tests/integrations/aladin/test_client.py`

**Interfaces:**
- Consumes: `settings.ALADIN_TTB_KEY`, injected `Transport(url: str, timeout: float) -> bytes`
- Produces: `ProviderBook`, `BookMetadataProvider.search()`,
  `AladinBookMetadataProvider.search()`, `get_default_provider()` 및 네 가지 Provider 예외

- [ ] **Step 1: 정상 응답과 요청 계약 실패 테스트 작성**

```python
# tests/integrations/aladin/test_client.py
import json
from urllib.parse import parse_qs, urlparse

import pytest

from integrations.aladin.client import AladinBookMetadataProvider
from integrations.aladin.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def test_search_maps_aladin_items_and_request_parameters() -> None:
    captured: dict[str, object] = {}

    def transport(url: str, timeout: float) -> bytes:
        captured.update(url=url, timeout=timeout)
        return json.dumps(
            {
                "item": [
                    {
                        "isbn13": "9788937834790",
                        "title": "정의란 무엇인가",
                        "author": "마이클 샌델",
                        "publisher": "와이즈베리",
                        "pubDate": "2014-11-20",
                        "cover": "https://image.example.test/justice.jpg",
                        "description": "정의에 관한 철학적 질문",
                        "link": "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1",
                        "subInfo": {"toc": "1장 옳은 일 하기"},
                    }
                ]
            }
        ).encode()

    provider = AladinBookMetadataProvider("secret-key", transport=transport, timeout=2.5)
    books = provider.search("정의")

    query = parse_qs(urlparse(str(captured["url"])).query)
    assert query["ttbkey"] == ["secret-key"]
    assert query["Query"] == ["정의"]
    assert query["QueryType"] == ["Keyword"]
    assert query["SearchTarget"] == ["Book"]
    assert query["output"] == ["js"]
    assert captured["timeout"] == 2.5
    assert books[0].isbn13 == "9788937834790"
    assert books[0].published_date.isoformat() == "2014-11-20"
    assert books[0].table_of_contents == "1장 옳은 일 하기"
```

- [ ] **Step 2: Adapter 부재로 예상한 RED 확인**

Run: `uv run pytest tests/integrations/aladin/test_client.py -v`

Expected: collection fails because `integrations.aladin.client` does not exist.

- [ ] **Step 3: Provider 값 객체와 예외 계층 구현**

```python
# src/integrations/aladin/contracts.py
from datetime import date
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderBook:
    isbn13: str
    title: str
    authors: str
    publisher: str
    published_date: date | None
    cover_url: str
    description: str
    table_of_contents: str
    external_url: str


class BookMetadataProvider(Protocol):
    def search(self, query: str) -> tuple[ProviderBook, ...]:
        """검색어와 일치하는 정규화된 도서를 반환한다."""
```

```python
# src/integrations/aladin/exceptions.py
class ProviderError(Exception):
    """도서 Metadata Provider 오류의 기반 예외다."""


class ProviderConfigurationError(ProviderError):
    """Provider 설정이 없어 요청할 수 없다."""


class ProviderTimeoutError(ProviderError):
    """Provider가 제한 시간 안에 응답하지 않았다."""


class ProviderUnavailableError(ProviderError):
    """Provider network 또는 HTTP 요청에 실패했다."""


class ProviderResponseError(ProviderError):
    """Provider 응답을 계약에 맞게 해석할 수 없다."""
```

- [ ] **Step 4: 최소 Aladin client로 정상 테스트 GREEN 확인**

```python
# src/integrations/aladin/client.py
import json
import socket
from collections.abc import Callable
from datetime import date
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

from integrations.aladin.contracts import ProviderBook
from integrations.aladin.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

ALADIN_SEARCH_ENDPOINT = "https://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
Transport = Callable[[str, float], bytes]


def _urlopen_transport(url: str, timeout: float) -> bytes:
    with urlopen(url, timeout=timeout) as response:
        return response.read()


class AladinBookMetadataProvider:
    """알라딘 ItemSearch 응답을 Provider 중립 도서로 변환한다."""

    def __init__(
        self,
        ttb_key: str,
        *,
        transport: Transport = _urlopen_transport,
        timeout: float = 3.0,
    ) -> None:
        self._ttb_key = ttb_key.strip()
        self._transport = transport
        self._timeout = timeout

    def search(self, query: str) -> tuple[ProviderBook, ...]:
        if not self._ttb_key:
            raise ProviderConfigurationError
        url = self._build_url(query)
        try:
            payload = self._transport(url, self._timeout)
        except (TimeoutError, socket.timeout) as error:
            raise ProviderTimeoutError from error
        except (OSError, URLError) as error:
            raise ProviderUnavailableError from error

        data = self._decode_payload(payload)
        if data.get("errorCode"):
            raise ProviderUnavailableError
        items = data.get("item", [])
        if not isinstance(items, list):
            raise ProviderResponseError

        books = (self._parse_item(item) for item in items)
        return tuple(book for book in books if book is not None)

    def _build_url(self, query: str) -> str:
        parameters = {
            "ttbkey": self._ttb_key,
            "Query": query,
            "QueryType": "Keyword",
            "MaxResults": "20",
            "start": "1",
            "SearchTarget": "Book",
            "output": "js",
            "Version": "20131101",
        }
        return f"{ALADIN_SEARCH_ENDPOINT}?{urlencode(parameters)}"

    @staticmethod
    def _decode_payload(payload: bytes) -> dict[str, object]:
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProviderResponseError from error
        if not isinstance(data, dict):
            raise ProviderResponseError
        return data

    @staticmethod
    def _parse_item(item: object) -> ProviderBook | None:
        if not isinstance(item, dict):
            raise ProviderResponseError
        isbn13 = str(item.get("isbn13", "")).strip()
        title = str(item.get("title", "")).strip()
        if len(isbn13) != 13 or not isbn13.isdigit() or not title:
            return None
        sub_info = item.get("subInfo")
        table_of_contents = (
            _text(sub_info.get("toc"))
            if isinstance(sub_info, dict)
            else ""
        )
        return ProviderBook(
            isbn13=isbn13,
            title=title,
            authors=_text(item.get("author")),
            publisher=_text(item.get("publisher")),
            published_date=_parse_date(item.get("pubDate")),
            cover_url=_text(item.get("cover")),
            description=_text(item.get("description")),
            table_of_contents=table_of_contents,
            external_url=_text(item.get("link")),
        )


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
```

Run: `uv run pytest tests/integrations/aladin/test_client.py::test_search_maps_aladin_items_and_request_parameters -v`

Expected: 1 passed.

- [ ] **Step 5: 실패 경계 테스트 추가**

```python
def test_search_rejects_missing_key() -> None:
    provider = AladinBookMetadataProvider("")

    with pytest.raises(ProviderConfigurationError):
        provider.search("책")


@pytest.mark.parametrize(
    ("failure", "expected_exception"),
    [
        (TimeoutError(), ProviderTimeoutError),
        (OSError("network down"), ProviderUnavailableError),
    ],
)
def test_search_maps_transport_failures(failure, expected_exception) -> None:
    def transport(url: str, timeout: float) -> bytes:
        raise failure

    provider = AladinBookMetadataProvider("key", transport=transport)

    with pytest.raises(expected_exception):
        provider.search("책")


@pytest.mark.parametrize(
    "payload",
    [b"not-json", json.dumps({"item": {"isbn13": "9788937834790"}}).encode()],
)
def test_search_rejects_malformed_response(payload: bytes) -> None:
    provider = AladinBookMetadataProvider(
        "key",
        transport=lambda url, timeout: payload,
    )

    with pytest.raises(ProviderResponseError):
        provider.search("책")


def test_search_skips_items_without_isbn13_or_title() -> None:
    payload = json.dumps(
        {
            "item": [
                {"isbn13": "", "title": "ISBN 없음"},
                {"isbn13": "9788937834790", "title": ""},
            ]
        }
    ).encode()
    provider = AladinBookMetadataProvider(
        "key",
        transport=lambda url, timeout: payload,
    )

    assert provider.search("책") == ()


def test_search_normalizes_missing_optional_fields() -> None:
    payload = json.dumps(
        {
            "item": [
                {
                    "isbn13": "9788937834790",
                    "title": "정의란 무엇인가",
                    "author": None,
                    "pubDate": "확인되지 않음",
                }
            ]
        }
    ).encode()
    provider = AladinBookMetadataProvider(
        "key",
        transport=lambda url, timeout: payload,
    )

    book = provider.search("정의")[0]
    assert book.authors == ""
    assert book.publisher == ""
    assert book.published_date is None
    assert book.table_of_contents == ""
```

- [ ] **Step 6: 오류 변환과 기본 Provider factory 구현 후 전체 Adapter 테스트**

`client.py`는 `TimeoutError`와 `socket.timeout`을 `ProviderTimeoutError`로,
`OSError`와 `urllib.error.URLError`을 `ProviderUnavailableError`로 변환한다.
JSON decode 실패, 최상위 object 아님, `item` list 아님은 `ProviderResponseError`로
변환한다. 다음 factory를 추가한다.

```python
def get_default_provider() -> AladinBookMetadataProvider:
    """현재 Django 설정으로 기본 알라딘 Provider를 만든다."""
    return AladinBookMetadataProvider(settings.ALADIN_TTB_KEY)
```

`src/config/settings.py`의 `environ.Env` 선언과 하단 설정에 다음을 추가한다.

```python
ALADIN_TTB_KEY=str,
```

```python
ALADIN_TTB_KEY = env("ALADIN_TTB_KEY", default="")
```

Run: `uv run pytest tests/integrations/aladin/test_client.py -v`

Expected: all Adapter tests pass without network access.

- [ ] **Step 7: Task 4 변경 커밋**

```powershell
git add src/integrations src/config/settings.py tests/integrations
git commit -m "feat: 알라딘 Metadata Adapter 구현"
```

---

### Task 5: Provider 중립 도서 검색 Service

**Files:**
- Create: `src/books/services.py`
- Test: `tests/books/test_services.py`

**Interfaces:**
- Consumes: `BookMetadataProvider.search(query)`와 `ProviderBook`
- Produces: `BookSearchStatus`, `BookSearchResult`,
  `search_books(query: str, provider: BookMetadataProvider) -> BookSearchResult`

- [ ] **Step 1: 정상·empty·오류 결과의 실패 테스트 작성**

```python
# tests/books/test_services.py
from datetime import date

import pytest

from books.services import BookSearchStatus, search_books
from integrations.aladin.contracts import ProviderBook
from integrations.aladin.exceptions import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

BOOK = ProviderBook(
    isbn13="9788937834790",
    title="정의란 무엇인가",
    authors="마이클 샌델",
    publisher="와이즈베리",
    published_date=date(2014, 11, 20),
    cover_url="https://image.example.test/justice.jpg",
    description="정의에 관한 철학적 질문",
    table_of_contents="",
    external_url="https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1",
)


class FakeProvider:
    def __init__(self, result=(), failure: Exception | None = None) -> None:
        self.result = result
        self.failure = failure
        self.queries: list[str] = []

    def search(self, query: str):
        self.queries.append(query)
        if self.failure is not None:
            raise self.failure
        return self.result


def test_search_trims_query_and_returns_success() -> None:
    provider = FakeProvider(result=(BOOK,))

    result = search_books("  정의  ", provider)

    assert provider.queries == ["정의"]
    assert result.status is BookSearchStatus.SUCCESS
    assert result.books == (BOOK,)


def test_search_returns_empty_without_calling_provider_for_blank_query() -> None:
    provider = FakeProvider(result=(BOOK,))

    result = search_books("   ", provider)

    assert provider.queries == []
    assert result.status is BookSearchStatus.EMPTY
    assert result.books == ()


def test_search_returns_empty_for_no_provider_results() -> None:
    result = search_books("없는 책", FakeProvider())

    assert result.status is BookSearchStatus.EMPTY


@pytest.mark.parametrize(
    "failure",
    [
        ProviderConfigurationError(),
        ProviderTimeoutError(),
        ProviderUnavailableError(),
        ProviderResponseError(),
    ],
)
def test_search_hides_provider_failures(failure: Exception) -> None:
    result = search_books("책", FakeProvider(failure=failure))

    assert result.status is BookSearchStatus.ERROR
    assert result.books == ()
```

- [ ] **Step 2: Service 부재로 RED 확인**

Run: `uv run pytest tests/books/test_services.py -v`

Expected: collection fails because `books.services` does not exist.

- [ ] **Step 3: 최소 Service 구현**

```python
# src/books/services.py
from dataclasses import dataclass
from enum import StrEnum

from integrations.aladin.contracts import BookMetadataProvider, ProviderBook
from integrations.aladin.exceptions import ProviderError


class BookSearchStatus(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BookSearchResult:
    status: BookSearchStatus
    books: tuple[ProviderBook, ...]


def search_books(query: str, provider: BookMetadataProvider) -> BookSearchResult:
    """검색어를 정규화하고 Provider 실패를 화면용 상태로 격리한다."""
    normalized_query = query.strip()
    if not normalized_query:
        return BookSearchResult(BookSearchStatus.EMPTY, ())
    try:
        books = provider.search(normalized_query)
    except ProviderError:
        return BookSearchResult(BookSearchStatus.ERROR, ())
    status = BookSearchStatus.SUCCESS if books else BookSearchStatus.EMPTY
    return BookSearchResult(status, books)
```

- [ ] **Step 4: Service 테스트 GREEN 확인**

Run: `uv run pytest tests/books/test_services.py -v`

Expected: all Service tests pass.

- [ ] **Step 5: Task 5 변경 커밋**

```powershell
git add src/books/services.py tests/books/test_services.py
git commit -m "feat: 도서 검색 결과 정규화 구현"
```

---

### Task 6: 보호된 반응형 도서 검색 UI

**Files:**
- Create: `src/books/forms.py`
- Create: `src/books/urls.py`
- Create: `src/books/views.py`
- Create: `src/templates/books/search.html`
- Create: `src/templates/books/_search_results.html`
- Modify: `src/config/settings.py`
- Modify: `src/config/urls.py`
- Modify: `src/templates/base.html`
- Modify: `src/static/css/app.css`
- Test: `tests/books/test_search_view.py`
- Modify: `tests/accounts/test_auth_views.py`

**Interfaces:**
- Consumes: `search_books()`, `get_default_provider()`, Django session auth
- Produces: `books:search` at `/books/search/`; HTMX partial result contract;
  최종 signup/login redirect target

- [ ] **Step 1: 보호 경로와 결과 상태 실패 테스트 작성**

```python
# tests/books/test_search_view.py
from datetime import date

import pytest
from django.urls import reverse

from integrations.aladin.contracts import ProviderBook


class FakeProvider:
    def __init__(self, books=(), failure=None) -> None:
        self.books = books
        self.failure = failure

    def search(self, query: str):
        if self.failure is not None:
            raise self.failure
        return self.books


BOOK = ProviderBook(
    isbn13="9788937834790",
    title="정의란 무엇인가",
    authors="마이클 샌델",
    publisher="와이즈베리",
    published_date=date(2014, 11, 20),
    cover_url="https://image.example.test/justice.jpg",
    description="",
    table_of_contents="",
    external_url="https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=1",
)


@pytest.mark.django_db
def test_search_requires_login(client) -> None:
    response = client.get(reverse("books:search"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
    assert "next=%2Fbooks%2Fsearch%2F" in response.url


@pytest.mark.django_db
def test_search_page_renders_normalized_results(client, django_user_model, monkeypatch) -> None:
    user = django_user_model.objects.create_user(username="reader", password="safe-pass")
    client.force_login(user)
    monkeypatch.setattr(
        "books.views.get_default_provider",
        lambda: FakeProvider((BOOK,)),
    )

    response = client.get(reverse("books:search"), {"q": "정의"})
    content = response.content.decode()

    assert response.status_code == 200
    assert "정의란 무엇인가" in content
    assert "마이클 샌델" in content
    assert "와이즈베리" in content
    assert "2014" in content
    assert 'id="book-search-results"' in content


@pytest.mark.django_db
def test_htmx_search_returns_only_results_partial(client, django_user_model, monkeypatch) -> None:
    user = django_user_model.objects.create_user(username="reader", password="safe-pass")
    client.force_login(user)
    monkeypatch.setattr(
        "books.views.get_default_provider",
        lambda: FakeProvider((BOOK,)),
    )

    response = client.get(
        reverse("books:search"),
        {"q": "정의"},
        headers={"HX-Request": "true"},
    )
    content = response.content.decode()

    assert response.status_code == 200
    assert 'id="book-search-results"' in content
    assert "<html" not in content
    assert "<main" not in content


@pytest.mark.django_db
def test_search_renders_empty_state(client, django_user_model, monkeypatch) -> None:
    user = django_user_model.objects.create_user(username="reader", password="safe-pass")
    client.force_login(user)
    monkeypatch.setattr("books.views.get_default_provider", lambda: FakeProvider())

    response = client.get(reverse("books:search"), {"q": "없는 책"})

    assert "검색 결과가 없습니다" in response.content.decode()


@pytest.mark.django_db
def test_search_renders_retryable_error(client, django_user_model, monkeypatch) -> None:
    from integrations.aladin.exceptions import ProviderTimeoutError

    user = django_user_model.objects.create_user(username="reader", password="safe-pass")
    client.force_login(user)
    monkeypatch.setattr(
        "books.views.get_default_provider",
        lambda: FakeProvider(failure=ProviderTimeoutError()),
    )

    response = client.get(reverse("books:search"), {"q": "정의"})

    assert "도서 정보를 가져오지 못했습니다" in response.content.decode()
    assert "다시 검색" in response.content.decode()
```

- [ ] **Step 2: URL 부재로 RED 확인**

Run: `uv run pytest tests/books/test_search_view.py -v`

Expected: FAIL with `NoReverseMatch` for `books:search`.

- [ ] **Step 3: Search form, URL, View 최소 구현**

```python
# src/books/forms.py
from django import forms


class BookSearchForm(forms.Form):
    q = forms.CharField(
        label="책 제목, 저자 또는 ISBN",
        max_length=200,
        strip=True,
    )
```

```python
# src/books/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from books.forms import BookSearchForm
from books.services import BookSearchResult, BookSearchStatus, search_books
from integrations.aladin.client import get_default_provider


@login_required
def search(request: HttpRequest) -> HttpResponse:
    """도서 검색 전체 페이지 또는 HTMX 결과 partial을 반환한다."""
    form = BookSearchForm(request.GET or None)
    result: BookSearchResult | None = None
    if form.is_valid():
        result = search_books(form.cleaned_data["q"], get_default_provider())
    context = {"form": form, "result": result, "statuses": BookSearchStatus}
    template_name = (
        "books/_search_results.html"
        if request.headers.get("HX-Request") == "true"
        else "books/search.html"
    )
    return render(request, template_name, context)
```

```python
# src/books/urls.py
from django.urls import path

from books import views

app_name = "books"

urlpatterns = [path("search/", views.search, name="search")]
```

`src/config/urls.py`에 `path("books/", include("books.urls"))`를 추가하고
`LOGIN_REDIRECT_URL = "books:search"`로 변경한다.

- [ ] **Step 4: 전체 검색 Template과 결과 partial 구현**

```django
{# src/templates/books/search.html #}
{% extends "base.html" %}

{% block title %}책 찾기 · AfterMuse{% endblock %}

{% block content %}
<section class="search-intro" aria-labelledby="search-title">
  <p class="eyebrow">Book Search</p>
  <h1 id="search-title">어떤 책을 읽으셨나요?</h1>
  <p>제목, 저자 또는 ISBN으로 정확한 판본을 찾아보세요.</p>
</section>
<form
  class="book-search-form"
  method="get"
  action="{% url 'books:search' %}"
  hx-get="{% url 'books:search' %}"
  hx-target="#book-search-results"
  hx-swap="outerHTML"
  hx-indicator="#book-search-loading"
>
  {{ form.q.label_tag }}
  {{ form.q }}
  <button type="submit">책 찾기</button>
  <span id="book-search-loading" class="htmx-indicator" role="status">
    도서 정보를 찾고 있습니다.
  </span>
</form>
{% include "books/_search_results.html" %}
{% endblock %}
```

```django
{# src/templates/books/_search_results.html #}
<section id="book-search-results" aria-live="polite">
  {% if result.status == statuses.SUCCESS %}
    <h2>검색 결과</h2>
    <ul class="book-grid">
      {% for book in result.books %}
        <li class="book-card">
          {% if book.cover_url %}
            <img
              class="book-cover"
              src="{{ book.cover_url }}"
              alt="{{ book.title }} 표지"
              loading="lazy"
            >
          {% else %}
            <div class="book-cover-placeholder" aria-hidden="true">표지 없음</div>
          {% endif %}
          <div>
            <h3>{{ book.title }}</h3>
            <p>{{ book.authors|default:"저자 정보 없음" }}</p>
            <p>
              {{ book.publisher|default:"출판사 정보 없음" }}
              {% if book.published_date %} · {{ book.published_date|date:"Y" }}{% endif %}
            </p>
            <p>ISBN {{ book.isbn13 }}</p>
          </div>
        </li>
      {% endfor %}
    </ul>
  {% elif result.status == statuses.EMPTY %}
    <div class="search-state">
      <h2>검색 결과가 없습니다</h2>
      <p>책 제목, 저자 또는 ISBN을 바꿔 다시 검색해 보세요.</p>
    </div>
  {% elif result.status == statuses.ERROR %}
    <div class="search-state search-state-error">
      <h2>도서 정보를 가져오지 못했습니다</h2>
      <p>잠시 후 다시 검색해 주세요.</p>
      <a href="{% url 'books:search' %}">다시 검색</a>
    </div>
  {% endif %}
</section>
```

`base.html`의 인증 사용자 navigation에 다음 link를 추가한다.

```django
<a href="{% url 'books:search' %}">책 찾기</a>
```

- [ ] **Step 5: 반응형 CSS와 focus/indicator 상태 구현**

```css
.book-search-form {
  display: grid;
  gap: 0.75rem;
  margin-block: 2rem;
}

.book-search-form input {
  min-height: 2.75rem;
  padding-inline: 0.75rem;
  border: 1px solid #77766f;
  border-radius: 0.25rem;
  background: #fff;
  font: inherit;
}

.htmx-indicator {
  display: none;
}

.htmx-request.htmx-indicator {
  display: inline;
}

.book-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  padding: 0;
  list-style: none;
}

.book-card {
  display: grid;
  grid-template-columns: 6rem 1fr;
  gap: 1rem;
  padding: 1rem;
  border: 1px solid #b8b7b1;
  border-radius: 0.5rem;
  background: #fff;
}

.book-cover,
.book-cover-placeholder {
  width: 6rem;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  background: #e6e3da;
}

.book-cover-placeholder {
  display: grid;
  place-items: center;
  padding: 0.5rem;
  color: #57564f;
  text-align: center;
}

input:focus-visible,
nav a:focus-visible {
  outline: 3px solid #315f78;
  outline-offset: 3px;
}

@media (min-width: 48rem) {
  .book-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

- [ ] **Step 6: auth redirect 최종 계약 테스트 수정 및 전체 UI 테스트 GREEN 확인**

`tests/accounts/test_auth_views.py`에서 signup/login 성공 redirect 기대값을
`reverse("books:search")`로 변경한다.

Run: `uv run pytest tests/accounts/test_auth_views.py tests/books/test_search_view.py tests/test_home_page.py -v`

Expected: all authentication, search UI, and home regression tests pass.

- [ ] **Step 7: Task 6 변경 커밋**

```powershell
git add src/books src/config src/templates src/static/css/app.css tests/accounts/test_auth_views.py tests/books/test_search_view.py
git commit -m "feat: 반응형 도서 검색 화면 구현"
```

---

### Task 7: 환경 문서, migration 안전성, Day 02 완료 검증

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/AfterMuse_MVP_Implementation_Plan_v5.md`
- Test: all existing test modules and generated migrations

**Interfaces:**
- Consumes: Tasks 1–6의 완성된 인증·모델·Adapter·Service·UI
- Produces: 재현 가능한 환경 계약, 검증 증거, 완료된 IMP-010/020/021/022/023 표시

- [ ] **Step 1: 환경 예시 동기화**

`.env.example`에 다음 줄을 추가한다.

```dotenv
ALADIN_TTB_KEY=
```

설정은 `env("ALADIN_TTB_KEY", default="")`를 유지하므로 기존 임시 `.env` fixture와
key 없는 Django check는 그대로 통과해야 한다.

- [ ] **Step 2: PostgreSQL 생성 SQL과 reverse migration 검증**

Run: `docker compose config --volumes`

Expected: exactly one line, `postgres_data`. 다른 이름이 함께 출력되면 삭제하지 말고
parent agent에게 범위 결정을 요청한다.

Run: `docker compose down --volumes`

Expected: AfterMuse Compose의 db container/network와 `postgres_data` volume만 제거된다.
이 단계는 Day 01 기본 auth migration 이력을 비우며 복구할 사용자 데이터가 없다는
사용자 승인에 근거한다.

Run: `docker compose up -d --wait db`

Run: `uv run python src/manage.py sqlmigrate accounts 0001`

Expected: SQL creates `accounts_user` and auth relation tables; no existing table rewrite,
data backfill, `DROP COLUMN`, or non-concurrent index rebuild is present.

Run: `uv run python src/manage.py sqlmigrate books 0001`

Expected: SQL creates `books_book` with a unique constraint/index for `isbn13`; no existing
table rewrite or data backfill is present.

Run: `uv run python src/manage.py migrate --noinput`

Run: `uv run python src/manage.py migrate books zero --noinput`

Run: `uv run python src/manage.py migrate accounts zero --noinput`

Run: `uv run python src/manage.py migrate --noinput`

Expected: forward, reverse, and re-apply all succeed on the development PostgreSQL database.

- [ ] **Step 3: 전체 정량 검증 실행**

Run: `uv run python scripts/verify.py`

Expected: Django system check, Ruff format check, Ruff lint, and all pytest tests pass with
no warnings or errors.

- [ ] **Step 4: 사용자 문서와 변경 이력 동기화**

README의 현재 구현 상태를 Day 02까지 갱신하고 다음 내용을 추가한다.

- `/accounts/signup/`, `/accounts/login/`, `/books/search/` 개발 URL
- `ALADIN_TTB_KEY` 환경변수 설명
- 검색 Adapter 자동 테스트는 실제 network를 사용하지 않는다는 설명
- 알라딘 OpenAPI 이용 조건과 승인된 key가 필요하다는 주의

`CHANGELOG.md`의 `[Unreleased]` 아래 `Added`에 인증, Book 모델, 알라딘 Adapter,
검색 Service/UI를 기록한다.

`docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 다음 항목만 `[x]`로 변경한다.

```text
IMP-010
IMP-020
IMP-021
IMP-022
IMP-023
```

- [ ] **Step 5: 문서 변경 후 최종 검증과 diff 검사**

Run: `uv run python scripts/verify.py`

Run: `git diff --check`

Expected: all verification passes and `git diff --check` produces no output.

- [ ] **Step 6: Task 7 변경 커밋**

```powershell
git add .env.example README.md CHANGELOG.md docs/AfterMuse_MVP_Implementation_Plan_v5.md
git commit -m "docs: Day 02 완료 상태와 환경 계약 반영"
```

---

## Final Review Gate

구현 agent는 모든 Task 완료 후 `superpowers:requesting-code-review`를 사용한다.
인증·migration 경계에 대해 독립 검토가 실질적 위험을 낮추므로 reviewer에게 다음을
제공한다.

- 본 spec과 plan 경로
- `git diff main...HEAD`
- `uv run python scripts/verify.py` 결과
- 두 `sqlmigrate` 출력과 forward/reverse/re-apply 결과
- 실제 알라딘 API 호출을 수행하지 않았다는 잔여 검증 범위

review finding을 반영한 뒤 관련 최소 테스트와 전체 verify를 다시 실행한다. 최종 통합
방식은 `superpowers:finishing-a-development-branch`에서 사용자가 선택한다.
