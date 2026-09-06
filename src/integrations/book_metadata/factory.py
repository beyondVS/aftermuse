"""현재 운영 기본 도서 Metadata Provider를 조합한다."""

from django.conf import settings

from integrations.kakao.client import KakaoBookMetadataProvider


def get_default_provider() -> KakaoBookMetadataProvider:
    """Django 설정으로 Kakao 도서 Metadata Provider를 만든다."""
    return KakaoBookMetadataProvider(settings.KAKAO_REST_API_KEY)
