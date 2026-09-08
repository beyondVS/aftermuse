# Quickstart: 인터뷰 시작 검증

## 목적

완독 Reading의 책 확인, readiness 안내, 멱등 Interview 생성, 상태별 재진입 계약, Reading 잠금과 InterviewTurn 기반을 PostgreSQL 및 Desktop/Mobile Web에서 재현한다.

## 사전 조건

- `.env`에 개발 PostgreSQL과 필수 Django 환경변수가 설정되어 있다.
- `uv sync`로 의존성을 설치했고 Bundle 04A/05A migration이 적용되어 있다.
- 작업 디렉터리는 저장소 루트다.
- [data-model.md](data-model.md), [service-contract.md](contracts/service-contract.md), [web-contract.md](contracts/web-contract.md)를 따른다.

## 1. 정적·schema 검증

```powershell
uv run python src/manage.py check
uv run python src/manage.py makemigrations --check --dry-run reflections
uv run python src/manage.py sqlmigrate reflections 0001
uv run python src/manage.py sqlmigrate reflections 0001 --backwards
```

예상 결과:

- system check와 migration drift가 없다.
- forward SQL은 신규 Interview/Turn table과 FK·CHECK·UNIQUE만 생성한다.
- 기존 table 변경, rename, drop, backfill과 중복 Turn FK index가 없다.
- backward SQL은 신규 두 table만 제거하며 production rollback에는 사용하지 않는다.

## 2. Migration 적용과 왕복

```powershell
uv run python src/manage.py migrate
uv run pytest tests/reflections/test_migrations.py
```

예상 결과: 기존 데이터가 유지되고 격리 PostgreSQL의 forward → zero → forward에서 신규 table과 제약이 동일하게 복원된다.

## 3. 자동 도메인·Web 검증

```powershell
uv run pytest tests/reflections tests/readings
```

필수 검증:

- Reading당 Interview 하나, Turn sequence UNIQUE와 status/readiness/sequence/question 제약
- 저장된 Interview의 Reading/Book 변경 거부와 기존 관계 보존
- 본인 소유 완독 Reading만 시작 가능하고 타인·미존재 객체는 동일 404
- `READY`/`READY_LIMITED` snapshot과 제한 안내 분기
- 반복·동시 시작이 같은 Interview 한 건으로 수렴
- 실패 시 부분 Interview, Reading 변경과 Credit 변경 0건
- 새 Interview는 `IN_PROGRESS`, Turn 0건
- Interview 존재 후 완독 취소와 완독일 수정 거부
- GET 무부작용, POST method 제한, 실제 CSRF enforcement와 status destination 판정
- 후속 Reflection route가 없는 `REFLECTION_READY`/`COMPLETED`의 상태별 409 안내와 무변경

## 4. 수동 Desktop/Mobile 흐름

```powershell
uv run python src/manage.py runserver
```

1. Knowledge Claim이 있는 Book의 완독 Reading에서 CTA를 연다.
2. 1280px와 375px에서 서지정보와 변경 불가 안내를 확인한다.
3. `책 다시 선택`이 Interview를 만들지 않고 검색으로 돌아가는지 확인한다.
4. 시작 후 진행 화면으로 이동하고 재진입해도 같은 Interview인지 확인한다.
5. Claim이 없는 Book에서 제한 안내가 보이고 시작은 허용되며 readiness가 보존되는지 확인한다.
6. keyboard와 screen reader로 heading, 안내, link/button, focus와 오류 alert를 확인한다.
7. 선택 metadata가 없는 Book에서 깨진 이미지, 빈 label과 추측 값이 없는지 확인한다.

## 5. 전체 품질 게이트

```powershell
uv run python scripts/verify.py
```

예상 결과: Django check, migration drift, Ruff format/lint와 전체 기본 pytest가 통과한다.
