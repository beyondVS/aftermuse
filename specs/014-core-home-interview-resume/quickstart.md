# Day 09 검증 가이드

## 준비

- 프로젝트 가상환경과 PostgreSQL 테스트 DB를 준비한다.
- [데이터 모델](data-model.md)과 [Home·재진입 계약](contracts/home-resume.md)을 기준으로 결과를 확인한다.
- 실제 외부 Provider credential과 브라우저 자동화는 기본 검증에 필요하지 않다.

## 검증 순서

1. `uv run pytest tests/test_home_page.py tests/accounts/test_auth_views.py tests/reflections/test_views.py`를 실행한다. Home의 공개 응답·`setup-status` 계약과 개인 기록 응답이 모두 통과해야 한다.
2. Reading 없음, `읽고 싶음`, `읽는 중`, 완독·Interview 없음, 진행 중 Interview를 구성해 실제 제목·상태·영역과 검색·Reading 상세·Interview 시작·기존 Interview 상세 링크를 확인한다. 복수 기록에서도 책과 링크가 뒤섞이지 않아야 한다.
3. 다른 사용자의 Reading·Interview를 함께 구성해 Home에 타인의 제목·상태·이어하기 링크가 없고 타인 Interview 상세는 기존 404인지 확인한다. 비로그인 Home에도 개인 기록이 없어야 한다.
4. 첫 질문 전, 미답변 Turn, 답변 저장 후 후속 처리 대기·오류, 진행 선택 대기에서 Home → 이어하기를 확인한다. 각 경우 기존 Interview·Turn·답변을 유지하고 새 Interview·질문을 만들지 않아야 한다.
5. Reading 상태를 바꾸거나 Interview를 준비 상태로 전환한 뒤 Home을 다시 열어 최신 상태와 행동을 확인한다. `REFLECTION_READY`·`COMPLETED`는 진행 카드에서 제외한다.
6. 구현 완료 시 `uv run python scripts/verify.py`를 실행한다. `uv run python src/manage.py makemigrations --check --dry-run`으로 마이그레이션이 필요 없음을 확인하고 README, 구현 계획 IMP-085/086, CHANGELOG를 실제 결과와 동기화한다.

실제 브라우저 UX 확인은 명시적으로 요청된 경우에만 별도로 수행한다.
