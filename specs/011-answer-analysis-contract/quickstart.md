# 빠른 검증: 답변 분석 계약

## 목적

확정 답변을 안전하게 분석해 의미, 단일 low-information 판정과 근거 있는 Core Coverage 상승
후보를 반환하면서 어떤 상태도 저장하지 않는지 검증한다.

## 사전 조건

```powershell
docker compose up -d --wait db
uv sync --locked
uv run python src/manage.py migrate --noinput
```

기본 `LLM_PROVIDER=fake`를 사용하며 실제 OpenAI credential과 network는 필요하지 않다.

## 1. Provider 계약

```powershell
uv run pytest tests/integrations/llm/test_fake.py tests/integrations/llm/test_openai.py -q
```

- fake가 정상/low-information/오류와 exact Context를 재현한다.
- OpenAI 호출은 strict schema, `store=False`, tools 없음, 고정 timeout과 무재시도를 사용한다.
- untrusted 문자열은 instructions와 분리된 data payload에 있다.
- timeout, 연결/rate limit/HTTP 오류와 손상 출력은 detail 없는 안전한 오류로 변환된다.

## 2. Context와 Service 계약

```powershell
uv run pytest tests/reflections/test_context.py tests/reflections/test_services.py -q
```

정상 검증:

- READY/READY_LIMITED별 Claim과 policy가 기존 Context 계약을 유지한다.
- 정상 답변은 non-null 의미와 0~4개 strict-promotion 후보를 반환한다.
- 각 후보는 유일한 축과 answer exact substring evidence를 가진다.
- low-information은 `meaning=None`, 빈 patch다.
- 정상이나 현재 Coverage를 높이지 않는 답변은 `False`, non-null 의미, 빈 patch다.

거부 검증:

- unsaved/다른 사용자/완료 상태/관계 손상 Interview
- 다른 Interview 또는 unsaved Turn, 미확정 답변, noncanonical Coverage
- provider/factory 동시 전달
- low-information invariant 모순, 빈/과도한 meaning, 후보 5개 이상
- 알 수 없는/중복 축, `UNCOVERED`, 동일 상태, 하락 상태
- 빈/과도한/원문에 없는 evidence와 금지된 지시 패턴

## 3. 무변경 회귀

성공과 모든 오류 전후에 Interview/Turn/Reading/Knowledge를 다시 조회해 값과 개수가 같고 query
log에 `INSERT`, `UPDATE`, `DELETE`가 없음을 확인한다. 잘못된 대상은 Provider factory 호출 전에
거부되어야 한다.

## 4. 정적 검사와 전체 품질 게이트

```powershell
uv run ruff format --check src/integrations/llm src/reflections tests/integrations/llm tests/reflections
uv run ruff check src/integrations/llm src/reflections tests/integrations/llm tests/reflections
uv run python src/manage.py check
uv run python src/manage.py makemigrations --check --dry-run
uv run python scripts/verify.py
```

새 migration이 없어야 하며 기존 첫 질문, 답변 저장과 Coverage 테스트가 그대로 통과해야 한다.
실제 OpenAI 연결과 browser 검증은 이번 Bundle의 완료 조건이 아니다.
