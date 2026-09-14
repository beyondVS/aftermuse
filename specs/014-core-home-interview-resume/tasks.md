# 작업: Core Home 사용자 상태 연결과 인터뷰 재진입

**입력**: `specs/014-core-home-interview-resume/`의 [계획](plan.md), [사양](spec.md), [데이터 모델](data-model.md), [계약](contracts/home-resume.md)

**구성**: Day 09 IMP-085/086을 사용자 스토리별로 구현한다. 새 모델·마이그레이션·외부 API는 필요하지 않다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일에서 미완료 작업에 의존하지 않고 병렬 진행 가능
- **[Story]**: 사양의 사용자 스토리 번호
- 모든 경로는 저장소 루트 기준이다.

## Phase 1: 설정

**목적**: 기존 경로와 검증 기준을 고정한다.

- [X] T001 `src/config/views.py`, `src/config/urls.py`, `src/reflections/views.py`, `tests/test_home_page.py`에서 공개 Home·`setup-status`·Interview 상세의 기존 응답과 소유권 계약을 확인하고 `specs/014-core-home-interview-resume/contracts/home-resume.md`와 일치시키기

---

## Phase 2: 기반

**목적**: 세 스토리가 공유할 Home 조회·표시 규칙을 확정한다.

- [X] T002 `src/readings/models.py`, `src/reflections/models.py`의 기존 관계만 사용해 `src/config/views.py`에서 현재 사용자 Reading을 도서·Interview와 함께 조회하고, `want_to_read`·`reading`, `completed`+Interview 없음, Interview `IN_PROGRESS`로 분류하며 최신 변경 시각·식별자 역순으로 정렬하기; `REFLECTION_READY`·`COMPLETED`는 이어하기에서 제외하고 스키마는 변경하지 않기

**체크포인트**: 현재 사용자에 한정한 세 그룹이 Home 렌더링에 제공된다.

---

## Phase 3: 사용자 스토리 1 - 내 독서 상태에서 다음 행동 찾기 (우선순위: P1) 🎯 MVP

**목표**: 실제 Reading 상태에 맞는 Home 카드·빈 상태·직접 이동을 제공한다.

**독립 테스트**: Reading 없음, `읽고 싶음`, `읽는 중`, 완독·Interview 없음과 복수 기록에서 실제 도서·상태·목적지를 확인한다.

- [X] T003 [US1] `tests/test_home_page.py`에 Reading 없음·세 상태·상태 변경·복수 기록의 Home 제목, 빈 상태, `books:search`·`readings:detail`·`reflections:interview_start` 링크와 상태별 행동의 접근 가능한 이름·키보드 탐색 순서·명확한 focus·색상 외 상태 표현을 검증하는 테스트 작성하기
- [X] T004 [US1] `src/templates/pages/home.html`에서 고정 도서·가상 사색·임의 진행률을 실제 기록처럼 보이지 않게 제거하고, `지금 읽고 있는 책` 및 `사색을 기다리는 책`에 도서·상태별 카드와 `[책 찾아보기]`·`[독서 기록 계속하기]`·`[AI 독서노트 만들기]`를 각 기록의 올바른 경로로 렌더링하기
- [X] T005 [US1] `src/config/views.py`에서 비로그인 Home은 개인 조회 없이 공개 소개를 제공하고 로그인 Home은 T002의 두 Reading 그룹을 전달하며, `/setup-status/` HTMX partial 응답은 그대로 유지하기
- [X] T006 [US1] `tests/test_home_page.py`와 `tests/accounts/test_auth_views.py`를 실행해 Reading별 표시·이동 및 기존 공개 Home·인증 탐색·`setup-status` 계약을 확인하기

**체크포인트**: US1은 Interview 이어하기 없이도 독서 상태별 다음 행동을 제공한다.

---

## Phase 4: 사용자 스토리 2 - 기존 Interview로 복귀하기 (우선순위: P1)

**목표**: Home에서 기존 진행 중 Interview의 현재 단계로 안전하게 돌아간다.

**독립 테스트**: 첫 질문 전, 미답변 Turn, 답변 저장 뒤 후속 처리·오류, 진행 선택 대기에서 Home → 기존 Interview 상세 이동과 데이터 불변을 확인한다.

- [X] T007 [P] [US2] `tests/reflections/test_views.py`에 첫 질문 전·미답변·답변 저장 후·진행 선택 대기·후속 처리 오류 상태의 Interview 상세 재방문이 기존 질문·답변·선택을 유지하고 Interview/Turn 수를 늘리지 않는 테스트 작성하기; 오류 상태에서는 답변 재입력 없이 오류 안내와 재시도 행동으로 복귀하는지 확인하기
- [X] T008 [US2] `tests/test_home_page.py`에 `IN_PROGRESS` Interview의 도서·현재 단계·`[인터뷰 이어하기]` 링크가 기존 `reflections:interview_detail`로 향하며 `REFLECTION_READY`·`COMPLETED`는 진행 카드에서 제외되는 테스트 작성하기
- [X] T009 [US2] `src/templates/pages/home.html`에 T002의 진행 중 Interview 그룹을 실제 도서·진행 단계·기존 상세 링크로 표시하고, 같은 Reading에 새 Interview 시작 카드를 중복 표시하지 않기
- [X] T010 [US2] `src/reflections/views.py`와 `src/templates/reflections/interview_detail.html`의 기존 GET 분기를 T007로 검증하고, 첫 질문 전·미답변·답변 저장 뒤·선택 대기·후속 처리 오류 중 복귀가 누락되는 분기만 수정하기; GET에서 Interview·Turn 생성이나 답변 변경을 하지 않기
- [X] T011 [US2] `tests/test_home_page.py`와 `tests/reflections/test_views.py`를 실행해 Home 이어하기 링크, 현재 단계, 질문·답변·Interview 수 불변을 확인하기

**체크포인트**: US2는 Home에서 기존 Interview로 복귀하며 새 Interview·질문이 생기지 않는다.

---

## Phase 5: 사용자 스토리 3 - 내 기록만 안전하게 확인하기 (우선순위: P2)

**목표**: 비로그인·타 사용자 기록을 Home에 노출하지 않고 복수 기록의 링크를 정확히 묶는다.

**독립 테스트**: 두 사용자의 서로 다른 Reading·Interview를 섞어 Home과 Interview 상세의 표시·접근을 확인한다.

- [X] T012 [US3] `tests/test_home_page.py`에 비로그인·타 사용자 Reading/Interview 비노출, 사용자별 복수 카드의 책·상태·링크 일치, 완료 Interview의 이어하기 제외를 검증하는 테스트 작성하기
- [X] T013 [US3] `src/config/views.py`와 `src/templates/pages/home.html`에서 T012로 드러난 사용자 격리·카드 링크·빈 상태 문제만 수정하고 `src/reflections/views.py`의 기존 타 사용자 Interview 404를 유지하기
- [X] T014 [US3] `tests/test_home_page.py`, `tests/accounts/test_auth_views.py`, `tests/reflections/test_views.py`를 실행해 타인 정보·링크 노출 0건과 기존 소유권 계약을 확인하기

**체크포인트**: US3은 개인 기록의 표시와 이동을 사용자별로 격리한다.

---

## Phase 6: 마무리 및 교차 검증

- [X] T015 `specs/014-core-home-interview-resume/quickstart.md`의 상태·링크·재진입 시나리오를 결정적인 테스트 결과와 대조하고, `tests/test_home_page.py`에서 복수 카드 수가 늘어도 관계 조회가 카드마다 추가되지 않는지 검증하며, `src/templates/pages/home.html`과 관련 스타일의 Desktop/Mobile 레이아웃·상태별 HTML·접근성 정적 검사 결과를 확인하기; `uv run python src/manage.py makemigrations --check --dry-run` 및 `uv run python scripts/verify.py`로 스키마 무변경과 프로젝트 품질 게이트 확인하기
- [X] T016 `README.md`, `docs/AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-085/086, `CHANGELOG.md`를 실제 구현·검증 결과에 맞게 수술적으로 갱신하기

## 의존성 및 실행 순서

- **설정 → 기반**: T001 후 T002.
- **US1**: T002 → T003 → T004/T005 → T006. Template은 조회 문맥과 합쳐 검증한다.
- **US2**: T002 후 T007과 T008을 서로 다른 테스트 파일에서 병렬 작성 가능하다. T008 → T009, T007 → T010, 이후 T011. US1의 Home 골격에 통합하되 Interview 상세 재진입 테스트는 독립 실행 가능하다.
- **US3**: T002와 Home 표시 골격 후 T012 → T013 → T014. 사용자 격리 검증은 US1/US2와 별도로 실행할 수 있다.
- **마무리**: 세 스토리 완료 후 T015 → T016.

## 병렬 실행 예시

- **US1**: T003의 기대 계약을 확정한 뒤 T004·T005를 진행한다. 동일 Home 문맥을 공유하므로 병렬 실행을 권장하지 않는다.
- **US2**: T007 `tests/reflections/test_views.py`와 T008 `tests/test_home_page.py`는 기존 Interview 상세 계약과 Home 링크 계약을 각각 다루므로 병렬 작성 가능하다.
- **US3**: T012는 US2의 테스트 파일과 충돌하므로 같은 파일 편집이 끝난 뒤 진행한다. 다른 파일을 독립 수정하는 병렬 작업은 없다.

## 구현 전략

1. US1을 최소 Home Navigation Hub로 먼저 완성하고 단독 검증한다.
2. US2를 더해 기존 Interview 재진입을 완성한다. Day 09의 핵심 사용자 흐름은 여기서 성립한다.
3. US3의 격리·복수 기록 검증을 완료하고 전체 품질 게이트와 문서 동기화를 수행한다.

실제 브라우저 검증, Reflection 생성·목록, Interview Restart·14일 정책은 이번 완료 조건이 아니다.

## Phase 7: Convergence

- [X] T017 src/reflections/views.py와 src/templates/reflections/interview_detail.html에서 기존 Interview 재진입 시 최신 Turn의 현재 단계와 함께 이전에 확정한 질문·답변 기록을 표시하고, tests/reflections/test_views.py에서 복수 Turn 재방문 시 이전 답변 표시 및 Interview·Turn·답변 불변을 검증하기 per US2/AC1, FR-006 (partial)
- [X] T018 src/templates/pages/home.html에서 Reading은 있지만 현재 독서·사색 대기·진행 중 Interview 대상이 없는 경우와 개별 영역에 대상이 없는 경우에 허위 콘텐츠 없는 적절한 빈 상태를 제공하고, tests/test_home_page.py에 대표 상태를 검증하기 per FR-009 (partial)
