# 구현 계획: Core Home 사용자 상태 연결과 인터뷰 재진입

**브랜치**: `feature/day-09-core-home-interview-resume` | **날짜**: 2026-09-14 | **사양**: [spec.md](spec.md)

**입력**: Day 09 IMP-085/086 및 기능 사양

## 요약

공개 Home의 소개와 설정 확인 기능은 유지하면서 로그인 사용자에게 실제 Reading과 진행 중 Interview를 상태별로 보여준다. 완독 후 Interview가 없는 Reading은 기존 시작 화면으로, 진행 중 Interview는 기존 상세 화면으로 직접 연결한다. Home과 재진입 GET은 새 Interview·질문·답변을 만들지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1, 서버 렌더링 Template, 기존 HTMX 부분 응답

**저장소**: PostgreSQL 18; 기존 Reading·Interview·InterviewTurn·InterviewProgressDecision 조회, 스키마 변경 없음

**테스트**: pytest-django, Django test client, Ruff, Django system check, `scripts/verify.py`

**대상 플랫폼**: Desktop/Mobile 반응형 Web

**프로젝트 유형**: 단일 Django Web 애플리케이션

**성능 목표**: Home에서 도서와 Interview 진행 요약을 카드마다 추가 조회하지 않고 구성한다.

**제약 조건**: 공개 Home·`setup-status` 응답 계약, 현재 사용자 소유권, GET의 무변경 성격, 기존 Interview 재진입 상태 보존

**규모/범위**: Day 09의 최소 Home 세 영역 및 기존 Interview 재진입. Full Library, Reflection Home 연계, Restart 정책 제외.

## 헌법 검사

*게이트: 설계 전 통과. 설계 후 재검사 결과는 아래에 기록한다.*

| 원칙 | 설계 적용 및 검증 |
|---|---|
| 사용자 생각의 충실성 | 샘플 답변·사색·임의 진행률을 실제 기록처럼 표시하지 않는다. |
| 핵심 제품 루프와 범위 | Reading 상세 → 완독 → Interview 시작·이어하기에 필요한 최소 동선만 연결한다. |
| 신뢰 경계와 데이터 통제 | Home 조회는 현재 사용자로 제한하고 Interview 상세의 소유권 검사도 유지한다. GET은 영속 상태를 바꾸지 않는다. |
| 단순한 아키텍처 | 기존 Home View·Template과 Reading·Interview 관계를 사용한다. 새 API·모델은 만들지 않는다. |
| 회복 가능한 UX | 빈 상태와 명확한 행동을 제공하고 현재 Interview 단계는 기존 상세 화면에서 복구한다. |
| 품질 게이트 | 사용자 격리, 링크, 상태 보존, 기존 공개 Home·HTMX 계약을 test client로 검증한다. 명시적 요청 없는 실제 브라우저 검증은 필수가 아니다. |

## 구현 흐름

1. 로그인 사용자 소유 Reading을 세 그룹으로 분류한다. `읽고 싶음`·`읽는 중`은 독서 카드, 완독·Interview 없음은 시작 카드, `IN_PROGRESS` Interview는 이어하기 카드다. 복수 기록은 최신 변경 시각·식별자 순으로 안정 정렬한다. 도서 관계 및 진행 요약의 반복 쿼리를 피한다.
2. Home View는 비로그인 방문자에게 개인 조회를 하지 않는다. 로그인 사용자에게만 세 그룹을 전달하고 `/setup-status/`의 HTMX partial은 기존대로 반환한다.
3. Home Template의 고정 도서·가상 사색·임의 진행률을 제거한다. 각 실제 카드에 도서·상태와 올바른 `books:search`, `readings:detail`, `reflections:interview_start`, `reflections:interview_detail` 행동을 붙인다. 대상이 없는 영역에는 빈 상태를 둔다.
4. 이어하기는 기존 `interview_detail` GET을 사용한다. 첫 질문 전, 미답변 Turn, 답변 저장 후 후속 처리·오류, 진행 선택 대기 분기를 확인하고 부족한 복귀 표시만 보완한다. 새 Interview 생성이나 재분석을 하지 않는다.
5. Home과 Interview 테스트에서 소유권·복수 기록·링크·재진입 후 데이터 불변을 검증한다. 구현 완료 시 관련 테스트와 `scripts/verify.py`를 실행하고 README·구현 계획·CHANGELOG를 실제 결과에 맞춰 동기화한다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/014-core-home-interview-resume/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/home-resume.md
```

### 소스 코드 (저장소 루트)

```text
src/config/views.py
src/config/urls.py
src/readings/models.py
src/reflections/models.py
src/reflections/views.py
src/templates/pages/home.html
src/templates/reflections/interview_detail.html
tests/test_home_page.py
tests/accounts/test_auth_views.py
tests/reflections/test_views.py
```

**구조 결정**: 현재 Home View의 공개 랜딩과 HTMX 상태 확인 경계를 유지한다. 조회 조합이 복잡해질 때만 작은 Selector로 분리하며 영속 엔터티는 추가하지 않는다.

## 설계 후 헌법 재검사

- 개인 데이터는 로그인 사용자로 필터링하며 공개 Home과 `setup-status`에는 포함하지 않는다.
- 기존 Interview 상세 경로를 재사용하여 질문·답변·선택 상태를 보존하고, Home GET은 순수 조회로 둔다.
- DB 스키마, 외부 API, LLM 호출 또는 새 제품 정책이 필요하지 않다. 헌법 위반과 미해결 기술 선택은 없다.
