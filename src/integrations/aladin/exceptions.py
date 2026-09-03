class ProviderError(Exception):
    """도서 Metadata Provider 오류의 기반 예외다."""


class ProviderConfigurationError(ProviderError):
    """Provider 설정이 없어 요청을 시작할 수 없다."""


class ProviderTimeoutError(ProviderError):
    """Provider가 허용된 대기시간 안에 응답하지 않았다."""


class ProviderUnavailableError(ProviderError):
    """Provider network, HTTP 또는 명시적 오류 응답으로 요청에 실패했다."""


class ProviderResponseError(ProviderError):
    """Provider 응답을 계약에 맞게 해석할 수 없다."""
