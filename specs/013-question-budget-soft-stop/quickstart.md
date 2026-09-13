# Day 08 검증 가이드

## 준비

- PostgreSQL 테스트 DB와 프로젝트 가상환경을 준비한다.
- 기본 검증에서는 fake LLM Provider를 사용하고 실제 credential은 사용하지 않는다.
- [데이터 모델](data-model.md)과 [Web·Service 계약](contracts/interview-flow.md)의 상태를 기준으로 관찰한다.

## 검증 순서

1. Migration을 생성한 뒤 `uv run python src/manage.py makemigrations --check --dry-run reflections`로 누락을 확인하고 새 migration 번호로 `uv run python src/manage.py sqlmigrate reflections 0005`를 실행해 실제 SQL·잠금 범위를 검토한다. PostgreSQL 적용·역적용 테스트에서 기존 Interview/Turn이 유지되는지 확인한다.
2. `uv run pytest tests/reflections/test_services.py tests/reflections/test_views.py tests/reflections/test_models.py tests/reflections/test_migrations.py`로 질문 수·선택·상태 전이를 검증한다. 분석·생성·저장 실패 및 두 선택의 반복·경합에서는 답변 유실, 중복 Turn, 부분 Coverage가 없어야 한다.
3. 4번째 답변 후 네 축 `COVERED`이며 근거 있는 다음 질문 후보가 있으면 Soft Stop 두 선택을 확인한다. `end`는 `REFLECTION_READY` 준비 안내로, `continue`는 질문 하나로 이어진다. 이어진 질문의 답변 뒤에도 조건이 유지되면 선택을 다시 보여준다.
4. 8번째 답변에서 네 축이 모두 `COVERED`이면 Soft Stop 재노출 없이 준비 안내로 끝나는지 확인한다. `UNCOVERED` 축을 목표로 하는 근거 있는 후보가 있으면 별도 상한 선택을 확인한다. 계속을 선택해도 열 번째 질문까지이며, 열 번째 답변 뒤 열한 번째 질문은 없어야 한다. `PARTIAL`만 남으면 준비 안내로 끝난다.
5. 예외 진행을 선택한 뒤 9번째 답변에서 근거가 사라지면 유효한 생략으로 준비 상태에 도달하고 10번째 질문이 없는지 확인한다. Day 07에 이미 질문 생략 표식이 있는 진행 중 Interview는 GET에서 DB 변경 없이 준비 안내, 후속 확정 POST에서 재분석 없이 `REFLECTION_READY`가 되는지 확인한다.
6. Provider timeout·무효 결과, 소유권 위반 및 stale POST를 각각 확인한다. 유효한 생략은 준비 상태, 오류는 503 재시도, 비소유는 404, 충돌은 내부 사유 없는 409여야 한다.
7. 구현 완료 시 `uv run python scripts/verify.py`를 실행하고 README, 구현 계획의 IMP-080/081/084, CHANGELOG를 실제 검증 결과에 맞춰 동기화한다.

실제 브라우저와 외부 LLM live 호출은 이번 기능의 필수 완료 조건이 아니다.
