# Quickstart: IMP-023 검증 가이드

도서 검색 화면의 인증, 입력 검증, 상태 표현, 판본 구분과 Desktop/Mobile 접근성을 실제 외부
Provider 호출 없이 검증한다. 세부 계약은 [ui-contract.md](contracts/ui-contract.md)와
[data-model.md](data-model.md)를 기준으로 한다.

## 사전 조건

- Python 3.14와 `uv`
- `uv sync --locked`로 준비된 기존 개발 의존성
- IMP-004 공통 Web UI, IMP-010 인증 및 IMP-022 검색 Service 완료
- 실제 `ALADIN_TTB_KEY`는 자동 View 테스트에 불필요

## 자동 검증 시나리오

1. 익명 사용자가 전체 화면과 Fragment 검색에 접근할 수 없고 기존 로그인 흐름으로
   이동하는지 확인한다.
2. 로그인한 사용자의 초기 화면에는 이름 있는 검색 입력과 실행 버튼만 있고 Empty/Error가
   없는지 확인한다.
3. 빈 값, 공백과 200자 초과 입력이 오류로 표시되고 Provider factory 호출은 0건인지
   확인한다.
4. 유효한 검색이 Provider factory의 fake를 통해 실제 검색 Service를 한 번 통과하는지
   확인한다.
5. Success 결과가 Provider 순서대로 모두 표시되고 표지, 제목, 저자, 출판사와 전체
   출간일에서 파생한 연도가 보이는지 확인한다.
6. 누락된 표지·선택 Metadata를 추측하지 않으며 대체 텍스트와 layout 계약을 유지하는지
   확인한다.
7. Empty와 Error가 다른 안내를 제공하고 Error에 같은 검색어 재시도 행동이 있는지
   확인한다.
8. Error HTML에 credential, 원본 오류, 예외 및 Provider 세부사항이 없는지 확인한다.
9. 일반 요청은 전체 문서, HTMX 요청은 검색 영역 Fragment만 반환하는지 확인한다.
10. Form에 최신 요청 교체, Loading indicator, 검색 영역 교체와 주소 유지 계약이 있는지
    확인한다.
11. 검색 흐름에서 Book, Reading 또는 Book Knowledge가 생성·변경되지 않는지 확인한다.

## 실행 명령

```powershell
uv run pytest tests/books/test_views.py -v
uv run ruff format --check src tests
uv run ruff check src tests
uv run python src/manage.py check
uv run python scripts/verify.py
```

## 실제 browser 검증

개발 서버를 실행하고 로그인한 뒤 `/books/search/`에서 fake 또는 안전한 개발 검색 응답으로
다음을 확인한다.

- 1280px Desktop과 375px Mobile에서 page-level 가로 scroll이 없다.
- 긴 제목, 여러 저자, 표지가 없는 결과 및 의도적으로 실패하는 표지 URL의 결과가 다른 카드와 겹치지 않고, 실패한 표지는 제목 `alt` 텍스트와 나머지 서지정보로 식별할 수 있다.
- Tab만으로 입력, 검색과 Error 재시도에 순서대로 접근하고 focus를 식별할 수 있다.
- 새 검색 시작 즉시 이전 결과가 숨고 Loading 텍스트만 보이며 최신 결과만 남는다.
- 상태 변화가 색상 외 제목·텍스트로 구분되고 browser console에 CSP 오류가 없다.
- 준비된 응답이 도착한 뒤 1초 이내에 검색 영역이 갱신된다.

## 기대 결과

- 전체 자동 품질 게이트와 위 browser 시나리오가 통과한다.
- 실제 credential, Provider 오류 상세 및 외부 호출은 자동 검증에 사용되지 않는다.
- 검색 결과 저장, 도서 선택·등록, Reading 생성과 Book Knowledge 준비는 발생하지 않는다.
- 신규 migration, runtime dependency, JSON API 및 client 전역 상태가 추가되지 않는다.

전체 검증 뒤 `CHANGELOG.md`의 `[Unreleased]`와
`docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-023 완료 상태를 동기화한다.
