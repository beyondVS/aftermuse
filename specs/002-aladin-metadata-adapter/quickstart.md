# Quickstart: IMP-021 검증 가이드

실제 알라딘 API와 credential 없이 정상, 빈 결과, 실패 및 timeout 계약을 검증한다.
[provider-contract.md](contracts/provider-contract.md)와 [data-model.md](data-model.md)를
기준으로 한다.

## 사전 조건

- Python 3.14와 `uv`
- `uv sync --locked`로 준비된 의존성
- 프로젝트의 PostgreSQL 환경변수
- 실제 `ALADIN_TTB_KEY`는 불필요

## 검증 시나리오

1. 완전한 JSON을 반환하는 fake로 URL 파라미터, timeout 전달, 모든 필드 매핑을 확인한다.
2. `{"item": []}`가 `()`이며 실패가 아님을 확인한다.
3. 유효/무효 항목 혼합에서 ASCII ISBN13 또는 제목이 무효인 항목만 제외되는지 확인한다.
4. 누락 선택값과 잘못된 날짜가 빈 문자열/`None`이고 추측값이 없는지 확인한다.
5. 빈 key는 호출 0회의 `ProviderConfigurationError`인지 확인한다.
6. timeout, I/O, Provider 오류 payload, malformed JSON/구조가 각각 약속된 예외인지 확인한다.
7. 예외에 fake key와 원본 오류 본문이 노출되지 않고 `Book` 저장이 없는지 확인한다.

## 실행 명령

```powershell
uv run pytest tests/integrations/aladin/test_client.py -v
uv run ruff format --check src tests
uv run ruff check src tests
uv run python src/manage.py check
uv run python scripts/verify.py
```

## 기대 결과

- 집중 테스트와 IMP-003 전체 품질 게이트가 통과한다.
- 자동 테스트 중 실제 알라딘 호출은 0건이다.
- migration 생성이나 `Book` 데이터 변경이 없다.

실제 key smoke test와 운영 이용 승인은 자동 완료 조건이 아니며 별도 승인 때만 수행한다.
