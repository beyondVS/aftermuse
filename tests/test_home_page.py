import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_page_contains_progressive_enhancement_assets(client) -> None:
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert '<main id="main-content"' in content
    assert "static/vendor/htmx.min.js" in content
    assert "static/vendor/alpine.min.js" in content
    assert 'hx-get="/setup-status/"' in content
    assert "x-data" in content


@pytest.mark.django_db
def test_htmx_request_returns_only_setup_partial(client) -> None:
    response = client.get(reverse("setup-status"), headers={"HX-Request": "true"})
    content = response.content.decode()

    assert response.status_code == 200
    assert '<section id="setup-status"' in content
    assert "<html" not in content
    assert "<main" not in content


@pytest.mark.django_db
def test_home_page_enforces_same_origin_csp(client) -> None:
    response = client.get(reverse("home"))
    policy = response.headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy
    assert "img-src 'self' data: https:" in policy
    assert "'unsafe-eval'" not in policy
