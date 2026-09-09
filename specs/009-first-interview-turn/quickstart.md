# Quickstart: 첫 인터뷰 Turn 검증

## 목적

READY/READY_LIMITED Context, Provider 경계, 첫 질문의 멱등 생성, 같은 화면
Loading/Error/Question 전환과 최초 답변 보존을 network 없는 자동 검증으로 재현한다.

## 사전 조건

- `.env`에 개발 PostgreSQL과 필수 Django 환경변수가 설정되어 있다.
- `uv sync`로 lockfile 의존성을 설치했고 기존 migration이 적용되어 있다.
- 작업 디렉터리는 저장소 루트다.
- [data-model.md](data-model.md), [LLM Provider 계약](contracts/llm-provider-contract.md),
  [Service 계약](contracts/service-contract.md), [Web 계약](contracts/web-contract.md)을 따른다.

## 1. 의존성·설정·migration drift 검증

```powershell
uv sync --locked
uv run python src/manage.py check
uv run python src/manage.py makemigrations --check --dry-run reflections
```

예상 결과:

- OpenAI SDK는 lockfile에서 재현되고 Python 3.14 환경에 설치된다.
- 필수 Django 설정이 유효하다.
- reflections schema migration이 새로 필요하지 않다.
- 실제 credential 값은 출력되지 않는다.

## 2. Provider와 Context 단위 검증

```powershell
uv run pytest tests/integrations/llm tests/reflections/test_context.py
```

필수 검증:

- fake provider가 정상, timeout, unavailable, invalid output을 network 없이 재현
- OpenAI Adapter가 30초 timeout, retry 0, structured output, no-tools, `store=False` 계약을 사용
- SDK 오류/refusal/invalid schema가 내부 오류 taxonomy로 변환되고 secret/raw context 비노출
- READY는 정렬된 최소 Claim을 포함하고 READY_LIMITED는 Claim을 제외
- 다른 user/Credit/admin 데이터가 Context에 포함되지 않음

## 3. Service·동시성·답변 불변 검증

```powershell
uv run pytest tests/reflections/test_services.py tests/reflections/test_models.py tests/reflections/test_forms.py
```

필수 검증:

- 기존 first Turn이면 Provider 미호출
- Provider I/O 실패/timeout/invalid question이면 Turn 0건
- 정상 질문은 한 문장·300자 이하 sequence 1로 저장
- 동시 생성 요청이 first Turn 한 건으로 수렴
- 공백/2,001자 답변 거부, 2,000자 답변 원문 전체 저장
- 동일 답변 재제출은 멱등, 다른 답변 재제출은 기존 원문 유지
- 답변 저장 뒤 Coverage/다음 질문/Interview status/Credit 변화 0건
- DB 실패 후 answer `NULL` 유지 및 재시도 가능

## 4. HTML·HTMX Web 계약 검증

```powershell
uv run pytest tests/reflections/test_views.py
```

필수 검증:

- detail GET은 side-effect 없이 Loading/fallback form, Question form 또는 Saved 상태를 렌더링
- 질문 준비/답변 POST의 method, CSRF, owner 404와 status/relationship 409
- HTMX fragment와 일반 POST redirect가 동일 Service 계약 사용
- Loading `aria-busy`, Error `role="alert"`/focus/retry, textarea label/help/error
- 질문 생성 30초 timeout과 invalid output의 same-screen Error
- 저장/validation/DB 오류에서 textarea 입력 보존
- 성공 후 수정/다음 질문 action 없음
- Desktop/Mobile용 semantic HTML과 keyboard focus 계약

## 5. 전체 기본 품질 게이트

```powershell
uv run python scripts/verify.py
```

예상 결과: Django check, migration drift, Ruff format/lint와 network·credential 없는 전체 기본
pytest가 통과한다.

## 선택: 실제 OpenAI 연결 smoke

실제 Adapter 검증이 필요할 때만 `.env`에 `OPENAI_API_KEY`를 설정하고 별도 `live` marker 테스트를
명시적으로 실행한다. 테스트는 request id 외 prompt, Context, response body와 credential을
출력하지 않는다. 실제 브라우저 검증은 이번 계획의 필수 완료 조건이 아니다.
