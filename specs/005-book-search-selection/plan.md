# 구현 계획: 도서 검색 복구 및 선택

**브랜치**: `feature/day-03-book-search-selection` | **날짜**: 2026-09-06 | **사양**: [spec.md](spec.md)

**입력**: `/specs/005-book-search-selection/spec.md`의 기능 사양

## 요약

Provider 중립 계약·예외·기본 factory를 `integrations.book_metadata`로 옮기고, Kakao 도서
검색 응답을 기존 `ProviderBook` 계약으로 변환하는 동기 Adapter를 추가한다. 기존 검색
Service와 화면 상태 계약은 유지하되 성공 결과 최대 20건을 현재 로그인 session에 15분간
JSON 선택 후보로 보관한다. 사용자는 후보 식별자만 POST하고, Book 선택 Service는
PostgreSQL unique 제약과 원자적 생성/조회로 기존 Book을 재사용하거나 새 Book을 만든다.

## 기술적 맥락

**언어/버전**: Python 3.14, HTML5, CSS

**주요 의존성**: Django 6.1 Templates·Forms·Session Authentication, HTMX 2.0.10,
django-environ 0.14, 표준 라이브러리 `urllib`, 기존 `Book`과 검색 Service

**저장소**: PostgreSQL 18의 기존 `Book`과 Django DB-backed session; 신규 도메인
테이블이나 migration 없음

**테스트**: pytest 9.1, pytest-django 4.14, Django test client, 주입 fake transport,
Ruff 0.16, 기본 `-m "not live"`의 `scripts/verify.py`, 명시적 `-m live` Kakao smoke

**대상 플랫폼**: Django 기반 Linux Web server와 최신 Desktop/Mobile Web browser

**프로젝트 유형**: 서버 렌더링 단일 Django Web application

**성능 목표**: 검색당 외부 요청 1회와 최대 20개 결과 선형 변환, 외부 응답 후 1초 이내
화면 갱신, 사용자 관점 검색 결과 3초 목표

**제약 조건**: Kakao timeout 3초, 검색 후보 15분 TTL·최신 성공 검색 최대 20건,
선택 POST·CSRF·로그인 필수, 화면 제출 Metadata 불신, 동일 ISBN13 Book 최대 1건,
credential·원본 오류 비노출, 기본 pytest 외부 호출 0건, 신규 runtime 의존성 없음

**규모/범위**: Kakao Adapter 1개, Provider 중립 package 1개, 검색 화면 확장과 선택 주소
1개, 선택 후보/session helper와 Book 선택 Service, 관련 단위·통합·live smoke 테스트

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 재확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| II. 핵심 제품 루프와 범위 규율 | 검색 복구와 Book 선택까지만 구현하고 Reading·Knowledge 준비는 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 외부 응답을 Adapter에서 검증하고, 선택은 서버 session 후보 식별자만 신뢰하며 Service만 Book을 변경한다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | 기존 Django Template/HTMX, Service/Adapter 경계와 DB session을 재사용한다. 책임 분리에 필요한 중립 integration package는 추가하되, 현재 요구에 불필요한 내부 HTTP API·신규 runtime dependency·새 영속 모델은 도입하지 않는다. | 통과 |
| V. 증거 기반 품질 | 정상·빈 결과·오류·timeout·ISBN 정규화, 후보 변조/만료/소유권, 중복 선택과 실제 key smoke를 분리 검증한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, PostgreSQL 18, uv/pytest/Ruff를 유지한다. | 통과 |
| 환경변수·비밀 | Kakao REST API key는 환경 설정으로만 주입하고 URL, HTML, 로그와 오류에 넣지 않는다. | 통과 |
| 데이터 무결성 | 기존 ISBN13 unique/CHECK 제약과 짧은 transaction을 사용하고 외부 호출은 transaction 밖에서 완료한다. | 통과 |
| 회복 가능한 UX | 후보 만료·불일치·검색 실패는 안전한 안내와 재검색/재시도를 제공하며 부분 Book을 남기지 않는다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/005-book-search-selection/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── provider-contract.md
│   ├── selection-contract.md
│   └── ui-contract.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── books/
│   ├── forms.py                    # 검색 Form + 후보 식별자 선택 Form
│   ├── models.py                   # 기존 Book; schema 변경 없음
│   ├── selection_candidates.py     # JSON session 후보 저장·조회·만료 정책
│   ├── services.py                 # 기존 검색 + Book 선택 Service
│   ├── urls.py                     # 검색 GET + 선택 POST
│   └── views.py                    # 얇은 검색/선택 요청 조합
├── config/settings.py              # KAKAO_REST_API_KEY 조건부 설정
├── integrations/
│   ├── aladin/                     # legacy Adapter와 중립 계약 호환 re-export
│   ├── book_metadata/              # 계약·예외·Kakao 기본 factory SSOT
│   └── kakao/client.py             # Kakao 요청·응답 검증·정규화
└── templates/books/
    ├── _search_region.html          # 후보 식별자 기반 선택 Form
    └── _selection_result.html       # 성공·만료/불일치 안내

tests/
├── books/                           # 후보·Service·View 테스트
└── integrations/
    ├── aladin/test_client.py         # 중립 계약 이동 회귀
    └── kakao/                        # Adapter와 명시적 live smoke 테스트

pyproject.toml                         # live marker 등록 및 기본 실행 제외
```

**구조 결정**: 도서 Metadata 공통 계약은 Provider 이름이 없는
`integrations.book_metadata`를 SSOT로 사용한다. Kakao와 legacy Aladin Adapter는 이
계약을 소비하고, 기존 Aladin import 경로는 작은 re-export로 회귀를 막는다. 검색과 선택
정책은 `books` Service에 두고, session 직렬화·TTL은 별도 helper가 담당하며 View는
Form 검증, 의존성 조합과 HTML 응답만 수행한다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
