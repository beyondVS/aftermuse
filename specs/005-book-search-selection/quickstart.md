# Quickstart: Bundle 03A 검증 가이드

세부 계약은 [provider](contracts/provider-contract.md),
[selection](contracts/selection-contract.md), [UI](contracts/ui-contract.md)와
[data model](data-model.md)을 기준으로 한다.

## 사전 조건

- Python 3.14, `uv`, 실행 중인 PostgreSQL 18과 적용된 기존 migration
- 기본 pytest는 `-m "not live"`로 외부 연결 테스트를 제외하며 실제 key가 필요 없음
- 명시적 live smoke에만 `KAKAO_REST_API_KEY`가 필요

## 자동 검증

1. Kakao 요청 header/parameter/timeout, 정상·빈 결과·오류·timeout과 ISBN/date/list mapping
2. key·원본 오류 비노출, legacy Aladin과 기존 검색 Service 회귀
3. session 후보 최대 20건, 15분 TTL, 새 검색/Empty/Error의 이전 후보 제거
4. 후보 변조·만료·다른 사용자 차단과 client Metadata 불신
5. 신규 Book 생성, 기존 Book 무변경 재사용, 순차·동시 선택의 ISBN 중복 0건
6. 검색·선택 인증, POST/CSRF, 전체/HTMX 응답과 접근성 계약
7. 선택 실패의 rollback 및 Reading/Knowledge side effect 0건

```powershell
uv run pytest tests/integrations/kakao/test_client.py -v
uv run pytest tests/integrations/aladin/test_client.py tests/books -v
uv run ruff format --check src tests
uv run ruff check src tests
uv run python src/manage.py check
uv run python scripts/verify.py
```

## 실제 Kakao key smoke

key는 저장소가 아닌 로컬 환경변수나 `.env`에만 둔다. 전용 smoke는 대표 한국 도서 검색이
유효한 ISBN13·제목을 한 건 이상 반환하는지만 확인하고 key와 원본 응답을 출력하지 않는다.

```powershell
uv run pytest tests/integrations/kakao/test_live_smoke.py -m live -v
```

`pyproject.toml`은 `live` marker를 등록하고 기본 선택식에서 제외한다. 명령줄의 `-m live`로
명시한 경우에만 smoke가 선택되며, 그때 key가 없으면 skip한다. IMP-025 완료 시에는 key가
있는 환경의 `passed` 결과가 필요하다.

## 수동 browser 검증

- 1280px Desktop과 375px Mobile에서 검색·판본 구분·선택을 완료한다.
- Tab/Enter만으로 검색, 책 선택과 다른 책 선택을 수행한다.
- 새 검색은 이전 결과·후보를 제거하고 최신 결과만 남긴다.
- 이중 제출은 같은 Book을 반환하고 만료·다른 session 후보는 재검색을 안내한다.
- 상태는 색상 외 제목·텍스트로 구분되며 CSP 오류가 없다.

완료 후 `README.md`, `.env.example`, `CHANGELOG.md`와 구현 계획의 IMP-024/025를 동기화한다.

## 검증 기록 (2026-09-06)

- `uv run python scripts/verify.py`: 112 passed, 1 skipped, 1 deselected
- `uv run pytest -m live tests/integrations/kakao/test_live_smoke.py -v`: 1 passed
- Desktop browser에서 실제 Kakao 검색 결과의 표지·제목·저자·출판사·출간연도와 선택 버튼을 확인하고, `은하영웅전설 한정박스세트(완전판)`을 새 Book으로 선택·등록해 완료 화면을 확인했다.
- Desktop에서 Tab으로 선택 버튼 간 이동하고 Enter로 Book 등록을 완료했으며, 375px Mobile에서도 검색·판본 선택·완료 화면을 확인했다.
- 키보드 전용 흐름은 1280px Desktop과 375px Mobile에서 각각 2회 연속 완료했으며, 사용자 확인 기준 각 회차는 2분 이내였다.
