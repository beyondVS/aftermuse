# aftermuse
독서 경험을 깊이 있는 AI 인터뷰와 나만의 독서노트로 이어주는 리플렉션 서비스

## 개발 환경

### 요구 도구

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop 또는 Docker Engine과 Compose plugin

Python 3.14는 `.python-version`을 기준으로 uv가 관리한다. Django는 호스트에서
실행하고 PostgreSQL 18만 container로 구동한다.

### 처음 실행

```powershell
Copy-Item .env.example .env
docker compose up -d db
uv sync --locked
uv run --env-file .env python src/manage.py migrate --noinput
uv run --env-file .env python src/manage.py runserver
```

`.env.example`의 값은 로컬 개발 예시이며 운영 credential로 사용하지 않는다.

### 품질 검증

PostgreSQL container가 healthy인 상태에서 전체 검증을 실행한다.

```powershell
uv run --env-file .env python scripts/verify.py
```

개별 명령은 다음과 같다.

```powershell
uv run --env-file .env python src/manage.py check
uv run --env-file .env ruff format --check .
uv run --env-file .env ruff check .
uv run --env-file .env pytest
```

## Django 앱 생성 원칙

도메인 app은 초기 설정에서 미리 만들지 않는다. 각 MVP 구현 계획에서 실제 책임과
model 경계가 확정될 때 app, service, selector를 함께 추가한다. 내부 PK는 기본
`BigAutoField`를 사용하며 UUID7은 공개 식별자가 필요한 model에서만 별도로 검토한다.
