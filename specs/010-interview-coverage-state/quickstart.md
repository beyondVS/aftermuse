# Quickstart: Interview Coverage 상태 검증

## 1. 사전 조건

- PostgreSQL 개발 DB가 실행 중이다.
- 프로젝트 의존성이 `uv.lock` 기준으로 설치되어 있다.
- `.env`에는 기존 Django 실행에 필요한 개발 환경값만 설정한다. 외부 Provider credential은
  필요하지 않다.

## 2. Migration 정합성 및 SQL 검토

```powershell
uv run python src/manage.py makemigrations --check --dry-run reflections
uv run python src/manage.py sqlmigrate reflections 0002
uv run python src/manage.py sqlmigrate reflections 0003
uv run python src/manage.py migrate
uv run python src/manage.py check
```

`sqlmigrate` 결과에서 다음을 확인한다.

- `coverage`는 non-null JSONB이며 canonical DB default를 가진다.
- column 추가 DDL의 lock 대기가 transaction-local `lock_timeout`으로 제한된다.
- CHECK는 먼저 `NOT VALID`로 추가되고 별도로 `VALIDATE CONSTRAINT`된다.
- validation이 앞선 DDL transaction을 불필요하게 오래 유지하지 않는다.
- forward/reverse SQL과 Django migration state가 일치한다.

## 3. Model 및 기본값 검증

```powershell
uv run pytest tests/reflections/test_models.py tests/reflections/test_migrations.py
```

필수 관찰 결과:

- migration 전 생성된 Interview도 migration 후 네 축이 모두 `UNCOVERED`다.
- migration 후 ORM과 DB default 경로로 생성된 Interview가 각각 canonical object를 가진다.
- 서로 다른 Interview instance가 mutable default object를 공유하지 않는다.
- 누락·추가 키, 비-object와 허용되지 않은 상태는 저장 경계 또는 DB CHECK에서 거부된다.
- migration reverse 검증이 기존 Interview/Turn 데이터를 손상하지 않는다.

## 4. Service 상태 전환 검증

```powershell
uv run pytest tests/reflections/test_services.py
```

[service-contract.md](contracts/service-contract.md)와 [data-model.md](data-model.md)를 기준으로 다음을
확인한다.

- 첫 patch가 지정하지 않은 축을 `UNCOVERED`로 유지한다.
- 단일·다중 축 상승과 `UNCOVERED` → `COVERED` 직접 상승이 동작한다.
- 같은 patch 재적용과 빈 patch는 write 없이 `changed=False`다.
- 상태 하락, 알 수 없는 축·상태, 중복 축과 mixed-validity patch는 전체 거부된다.
- 답변 없음, 비진행 Interview, Book 연결 손상과 다른 사용자 접근은 상태를 바꾸지 않는다.
- 소유자는 `REFLECTION_READY`와 `COMPLETED` Interview의 Coverage를 조회할 수 있지만 변경할 수 없다.
- Coverage 변경 후 Interview status, Turn 수·순서, 답변 원문과 다른 domain 데이터가 그대로다.

## 5. PostgreSQL 원자성·동시성 검증

실제 PostgreSQL transaction을 사용하는 테스트로 다음 경쟁을 재현한다.

- 서로 다른 축을 동시에 상승시키면 두 변경이 모두 보존된다.
- 같은 축을 같은 상태로 동시에 상승시키면 하나의 상태로 수렴한다.
- 같은 축의 `PARTIAL`과 `COVERED` 경쟁은 `COVERED`를 보존하며 낮은 stale 변경이 덮어쓰지 않는다.
- 한 patch의 write 실패를 주입하면 어떤 축도 부분 저장되지 않는다.

동시성 테스트는 thread별 DB connection을 사용하고 barrier로 lock 경쟁 구간을 제어한다. 외부
Provider나 network는 호출하지 않는다.

## 6. 전체 품질 게이트

```powershell
uv run python scripts/verify.py
```

완료 기준:

- 모든 관련 및 전체 회귀 검사가 통과한다.
- migration drift가 없다.
- Bundle 06A의 첫 질문·답변 저장 흐름이 그대로 통과한다.
- Answer Analysis, 다음 질문, Soft Stop과 UI가 새로 실행되거나 추가되지 않는다.
