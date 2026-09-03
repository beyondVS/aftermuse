# Quickstart: IMP-022 검증 가이드

실제 알라딘 호출과 database 접근 없이 도서 검색 Service의 검색어 정규화, 결과 보존 및
상태 격리 계약을 검증한다. 세부 계약은 [service-contract.md](contracts/service-contract.md)와
[data-model.md](data-model.md)를 기준으로 한다.

## 사전 조건

- Python 3.14와 `uv`
- `uv sync --locked`로 준비된 기존 개발 의존성
- IMP-021의 Provider 중립 계약 구현
- 실제 `ALADIN_TTB_KEY`와 실행 중인 PostgreSQL은 집중 Service 테스트에 불필요

## 검증 시나리오

1. 앞뒤 공백이 있는 검색어가 내부 문자열을 유지한 채 trim되어 fake Provider에 정확히
   한 번 전달되는지 확인한다.
2. 한 건 이상의 `ProviderBook`이 원래 순서와 전체 Metadata를 유지한 `SUCCESS` 결과인지
   확인한다.
3. 정상 빈 tuple이 빈 `books`의 `EMPTY` 결과인지 확인한다.
4. 빈 문자열과 공백 검색어가 Provider 호출 0건의 `EMPTY` 결과인지 확인한다.
5. configuration, timeout, unavailable, response 오류가 모두 빈 `books`의 `ERROR`로
   변환되고 외부 오류 상세를 노출하지 않는지 확인한다.
6. `ProviderError`가 아닌 예외는 숨겨지지 않고 호출자에게 전파되는지 확인한다.
7. 검색 중 `Book` 조회·생성·변경, cache, retry 및 실제 외부 요청이 없는지 확인한다.
8. 전체 출간일을 포함한 `ProviderBook`의 모든 필드가 변경 없이 보존되는지 확인한다.

## 실행 명령

```powershell
uv run pytest tests/books/test_services.py -v
uv run ruff format --check src tests
uv run ruff check src tests
uv run python src/manage.py check
uv run python scripts/verify.py
```

## 기대 결과

- 집중 Service 테스트와 프로젝트 전체 품질 게이트가 통과한다.
- 실제 알라딘 호출과 credential 사용은 0건이다.
- database query, Book 변경 및 migration 생성은 0건이다.
- IMP-023의 검색 화면이나 IMP-024의 Book 등록 동작은 생성되지 않는다.

전체 검증이 통과한 뒤 `CHANGELOG.md`의 `[Unreleased]`와
`docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-022 완료 상태를 동기화한다.
