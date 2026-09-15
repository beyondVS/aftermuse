# 검증 가이드: Day 10 Reflection

## 준비

아래는 구현 후 실행할 명령이다. 현재 계획 작성으로 테스트 통과를 주장하지 않는다. [데이터 모델](data-model.md)과 [계약](contracts/reflection-generation.md)을 기준으로 검증한다. 저장소 루트 PowerShell 및 기존 로컬 개발 .env를 사용하며 운영·공유 DB에 연결하지 않는다.

```powershell
docker compose up -d --wait db
uv sync --locked
$env:LLM_PROVIDER = 'fake'
uv run python src/manage.py check
uv run python src/manage.py sqlmigrate reflections 0007
```

0007은 실제 migration 번호와 맞춘다. SQL의 새 테이블·unique·CHECK·FK·transaction-scoped lock timeout과 기존 테이블 변경 부재를 검토한다. migration 역방향은 pytest 테스트 DB에서만 확인한다.

## 좁은 자동 검사

```powershell
uv run pytest tests/reflections/test_drafts.py tests/reflections/test_models.py tests/reflections/test_migrations.py tests/integrations/llm/test_reflection.py tests/integrations/llm/test_structured_providers.py tests/integrations/llm/test_factory.py
uv run python src/manage.py makemigrations --check --dry-run
```

| 시나리오 | 기대 결과 |
| --- | --- |
| 초안·수정본 저장/조회, 수정본 없음 | 별도 내용 보존·DRAFT·완료 시각 없음; SC-001 |
| 같은 Interview 재저장 | conflict, 최대 1개, 기존 원본·수정본 불변; SC-006 |
| 타인·관계 불일치·준비 전·빈 답변 | 외부 호출 전에 거부·원문 보존; SC-005 |
| fake 생성 → 명시 저장 | 생성 자체는 비영속, 저장 본문과 render 일치 |
| 최대 입력 10개 × 2,000자 fake 생성·저장 | 제목·구분자 포함 22,000자 이하, 답변 원문 모두 보존 |
| 초안 22,001자·수정본 20,001자 | 각각 길이 거부, 기존 기록 불변 |
| 명시된 허용/금지 형식·패턴 변형 | plain text·수정본 일반 Markdown 허용, 링크·이미지·HTML 및 지시 패턴 거부 |
| 입력 answer 속 정책 변경·출력에 복사된 패턴 | 입력은 지시로 실행하지 않고, 출력 거부를 별도 검증 |
| 짧은 답변·미완료 Coverage | 실제 답변만 짧게 구성; SC-002·003 |
| 잘못된 key/type/길이/참조/인용/금지 내용 | Rejected, 저장 없음 |
| cross-Interview·변조·stale 결과 | 저장 재검증에서 거부 |
| timeout·설정·외부 오류 | 안전 reflection 오류, 원문 유출·자동 재시도·fallback 없음 |
| provider request·factory | 네 번째 capability와 기존 세 작업 회귀 없음; SC-004 |
| migration 앞뒤·역방향·제약 | 기존 Interview·Turn·Coverage·Decision 보존 |

외부 transport만 격리하고 대상 정책·저장·transaction은 실제 코드와 PostgreSQL로 검증한다. 소유자 격리·초안 불변·실패 보존은 독립된 검토 관점으로 diff와 검사 결과를 대조하여 기록한다.

## 품질 평가와 opt-in 연결

인수 자료는 풍부한 비문학 답변, 소설 장면·감정, 제한된 책 정보, 짧은 답변, 유보·반대·감정의 공존 및 정책 변경 입력을 포함한다. 모든 제목·문단을 원문에 대조하여 새 의견·경험·사실 추가 0건, 유보 표현 보존, 가변 구성을 확인한다. fake의 원문 복사를 실제 Provider의 의미적 품질 증거로 간주하지 않는다.

사용자가 실제 연결을 선택하고 provider·모델·credential을 구성했을 때만 실행한다.

```powershell
uv run pytest -m live tests/integrations/llm/test_live_smoke.py -k reflection
```

Ollama는 기존 OLLAMA_LIVE_TEST=1 조건도 따른다. 미구성·미선택 환경은 안전한 사유로 skip한다. 실제 key·답변·원본 응답을 로그에 남기지 않고 자료 식별자·provider/model·계약 검증·충실성 판정을 기록한다. 연결을 수행하지 않았다면 해당 provider의 실제 품질·호환성 미검증을 보고한다. 브라우저 조작은 필수 조건이 아니다.

## 완료 게이트

```powershell
uv run python scripts/verify.py
```

Django check·Ruff format/lint·기본 pytest를 확인한다. 환경 실패는 회귀와 구분해 보고한다. 검증된 IMP만 완료 표시하고 코드·README·CHANGELOG를 같은 작업에서 동기화한다.
