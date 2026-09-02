# Day 02 인증 및 도서 검색 설계

> 대상: `AfterMuse_MVP_Implementation_Plan_v5.md`의 IMP-010, IMP-020,
> IMP-021, IMP-022, IMP-023

## 1. 목적과 성공 기준

Day 02의 목적은 신규 사용자가 계정을 만들고 로그인한 뒤 알라딘 서지정보를
이용해 책을 검색할 수 있는 첫 번째 실제 사용자 흐름을 완성하는 것이다.

다음 조건을 모두 만족하면 완료로 본다.

- 신규 사용자가 가입, 로그인, 로그아웃을 수행할 수 있다.
- 로그인하지 않은 사용자는 도서 검색 화면에 접근할 수 없다.
- ISBN13을 기준으로 `Book`을 저장하고 데이터베이스 수준에서 중복을 막는다.
- 알라딘 Adapter가 정상, 잘못된 응답, Provider 오류, timeout을 구분한다.
- 검색 Service가 Provider 응답을 화면 계약으로 정규화하고 정상, 결과 없음,
  Provider 실패를 구분한다.
- Desktop과 Mobile에서 표지, 제목, 저자, 출판사, 출간연도를 확인할 수 있다.
- 검색 UI가 Loading, Empty, Error 상태를 접근 가능한 서버 렌더링 HTML로 제공한다.
- Django check, Ruff, pytest, PostgreSQL migration 검증이 통과한다.

## 2. 범위

### 포함

- Django session 기반 회원가입, 로그인, 로그아웃
- `accounts.User`와 `books.Book`의 초기 모델 및 migration
- 알라딘 ItemSearch Adapter와 외부 호출을 대체할 수 있는 transport 경계
- 도서 검색 결과 정규화 Service
- Django Template 및 HTMX 기반 도서 검색 화면
- 환경변수, 개발 문서, CHANGELOG, Day 02 진행 체크리스트 동기화

### 제외

- 이메일 인증, 소셜 로그인, 비밀번호 재설정
- 검색 결과를 로컬 `Book`으로 저장하거나 upsert하는 동작(IMP-024)
- 도서 선택, Book Detail, Reading 생성(모두 Day 03 이후)
- pagination, 검색 이력, 추천, 자동완성
- 실제 알라딘 API 키 발급, 상업적 이용 승인, 운영 호출 검증
- 목차가 없는 응답을 LLM이나 애플리케이션이 추측해 채우는 동작

## 3. 검토한 접근

### 접근 A — Django 기본 기능과 명시적 Adapter 경계 사용(채택)

`AbstractUser`, Django auth view/form, Django ORM을 사용한다. 외부 도서 검색만
`integrations.aladin`에 격리하고, `books`는 Provider 중립 DTO와 Service 계약에만
의존한다. 추가 runtime 패키지 없이 표준 라이브러리 HTTP client를 사용한다.

장점은 현재 아키텍처 결정과 일치하고 의존성이 늘지 않으며 외부 실패를 실제 호출
없이 테스트할 수 있다는 것이다. 단점은 timeout과 JSON 오류 매핑을 직접 명시해야
한다는 것이다.

### 접근 B — Django 기본 `auth.User`와 `books` 내부 API 호출

초기 파일 수는 적지만 향후 사용자 모델 변경 비용이 커지고 도메인 코드가 알라딘
응답 형식에 결합된다. `accounts`, `books`, `integrations` 경계를 명시한 Architecture
Decisions와 맞지 않아 채택하지 않는다.

### 접근 C — django-allauth와 별도 HTTP client 도입

이메일 검증과 확장 기능은 풍부하지만 Day 02 범위를 넘어서는 설정, Template,
dependency가 생긴다. Core MVP에서 필요하지 않아 채택하지 않는다.

## 4. 애플리케이션 구조

```text
src/
├─ accounts/
│  ├─ forms.py
│  ├─ models.py
│  ├─ urls.py
│  └─ views.py
├─ books/
│  ├─ forms.py
│  ├─ models.py
│  ├─ services.py
│  ├─ urls.py
│  └─ views.py
├─ integrations/
│  └─ aladin/
│     ├─ client.py
│     ├─ contracts.py
│     └─ exceptions.py
└─ templates/
   ├─ accounts/
   └─ books/
```

`accounts`는 사용자와 인증 HTTP 흐름을 소유한다. `books`는 로컬 Book 데이터와
Provider 중립 검색 결과를 소유한다. `integrations.aladin`은 요청 생성, network I/O,
알라딘 JSON 파싱과 외부 오류 변환만 담당한다. View는 form 검증과 Service 호출,
Template 선택만 담당한다.

## 5. 인증 설계

`accounts.User`는 Django `AbstractUser`를 상속한다. Day 02에서는 Django의 검증된
username/password 계약을 유지하고 화면에서는 username을 `아이디`로 표현한다.
`AUTH_USER_MODEL = "accounts.User"`를 프로젝트의 첫 도메인 migration에서 설정한다.

회원가입은 username, password1, password2만 요구한다. 성공하면 사용자를 즉시
로그인시키고 도서 검색 화면으로 이동한다. 로그인은 Django `LoginView`와
`AuthenticationForm`을 사용한다. 로그아웃은 CSRF가 적용되는 POST 요청만 허용한다.
인증이 필요한 도서 검색 화면은 원래 목적지를 `next`로 보존해 로그인 화면으로
보낸다.

비밀번호는 Django password validator와 hasher를 그대로 사용하며 로그, message,
Template에 평문으로 노출하지 않는다.

## 6. Book 모델

`Book`은 다음 필드를 가진다.

| 필드 | 저장 계약 |
| --- | --- |
| `isbn13` | 숫자 13자리, `unique=True` |
| `title` | 필수 제목 |
| `authors` | Provider가 제공한 저자 표시 문자열 |
| `publisher` | 출판사 표시 문자열 |
| `published_date` | 알 수 없으면 `NULL` |
| `cover_url` | 알 수 없으면 빈 문자열 |
| `description` | 알 수 없으면 빈 문자열 |
| `table_of_contents` | 제공되지 않으면 빈 문자열 |

ISBN 중복 방지는 form/service 검사에만 의존하지 않고 PostgreSQL unique constraint로
보장한다. Work/Edition 분리, raw metadata JSONB, 별도 Provider 식별자는 실제 저장
흐름이 시작되는 Day 03 이후 필요가 확인될 때 추가한다.

신규 빈 테이블을 만드는 초기 migration이므로 기존 행 backfill은 없다. 생성 SQL과
reverse migration을 PostgreSQL에서 확인한다.

Day 01에서 Django 기본 `auth/admin` migration이 적용된 개발 DB는 Custom User를
나중에 추가할 때 migration dependency가 충돌할 수 있다. 아직 보존할 사용자 데이터가
없는 초기 개발 단계이므로 `compose.yaml`의 유일한 named volume `postgres_data`를
한 번 재생성하고 빈 DB에서 전체 migration을 다시 적용한다. 삭제 직전 Compose가
가리키는 volume 이름과 범위를 읽기 전용으로 확인하며, 다른 Docker volume은 건드리지
않는다. 사용자는 2026-09-02에 이 개발 DB 재생성을 승인했다.

## 7. Provider Adapter 계약

Provider 중립 검색 항목은 immutable `ProviderBook` 값 객체로 표현한다.

```python
@dataclass(frozen=True, slots=True)
class ProviderBook:
    isbn13: str
    title: str
    authors: str
    publisher: str
    published_date: date | None
    cover_url: str
    description: str
    table_of_contents: str
    external_url: str
```

Adapter의 public 계약은 다음과 같다.

```python
class BookMetadataProvider(Protocol):
    def search(self, query: str) -> tuple[ProviderBook, ...]: ...
```

`AladinBookMetadataProvider`는 `ALADIN_TTB_KEY`, timeout, 주입 가능한 transport를
받는다. 요청에는 ItemSearch endpoint, `QueryType=Keyword`, `SearchTarget=Book`,
`output=js`, `Version=20131101`을 사용한다. transport의 기본 구현만 실제 network를
사용하고 테스트는 byte payload 또는 예외를 반환하는 fake transport를 사용한다.

오류는 다음 의미로 분리한다.

- `ProviderConfigurationError`: API key가 비어 있음
- `ProviderTimeoutError`: timeout 발생
- `ProviderUnavailableError`: network/HTTP 실패 또는 Provider 오류 응답
- `ProviderResponseError`: JSON 또는 item 구조가 계약과 맞지 않음

항목별 선택 필드 누락은 빈 문자열 또는 `None`으로 정규화한다. ISBN13이나 제목이
없는 항목은 사용자가 판본을 식별할 수 없으므로 결과에서 제외한다. 목차가 없으면
빈 문자열로 유지하며 생성하지 않는다. API key와 원본 오류 본문은 사용자 message나
로그에 포함하지 않는다.

알라딘 공식 이용 안내상 일반 OpenAPI의 영리 서비스 이용에는 제한이 있으므로,
구현 완료는 실제 운영 호출을 의미하지 않는다. 승인된 key가 환경에 제공된 경우에만
Adapter가 호출된다.

## 8. 검색 Service 계약

`books.services.search_books(query, provider)`는 query 양끝 공백을 제거한 뒤 Provider를
호출하고 다음 결과를 반환한다.

```python
class BookSearchStatus(StrEnum):
    SUCCESS = "success"
    EMPTY = "empty"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class BookSearchResult:
    status: BookSearchStatus
    books: tuple[ProviderBook, ...]
```

공백뿐인 query는 Provider를 호출하지 않고 `EMPTY`를 반환한다. 한 개 이상의 유효한
항목은 `SUCCESS`, 빈 결과는 `EMPTY`다. 모든 Provider 예외는 외부 상세를 감춘
`ERROR`로 변환한다. View와 Template은 구체 Provider 오류에 결합하지 않는다.

## 9. HTTP 및 UI 흐름

URL은 다음 계약을 사용한다.

```text
/accounts/signup/       GET, POST
/accounts/login/        GET, POST
/accounts/logout/       POST
/books/search/          GET
```

전체 페이지 GET은 검색 form과 아직 검색하지 않은 초기 상태를 렌더링한다. `q`가 있는
GET은 동일 View가 검색을 수행한다. HTMX 요청이면 결과 영역 partial만 반환하고 일반
요청이면 전체 페이지를 반환한다. 검색은 read-only이므로 GET을 사용한다.

상태 표현은 다음과 같다.

- Loading: submit button과 연계된 `aria-live` indicator를 HTMX 요청 중 표시
- Empty: 검색어에 맞는 책을 찾지 못했다는 문구와 다른 검색어 안내
- Error: 서지정보를 가져오지 못했음을 알리고 같은 form으로 재시도 가능
- Results: 표지, 제목, 저자, 출판사, 출간연도를 카드 목록으로 표시

결과 카드는 Day 02에서 저장이나 선택 side effect를 만들지 않는다. 표지가 없으면
텍스트 placeholder를 표시하고 빈 `img`를 렌더링하지 않는다. 공통 header는 인증
상태에 따라 로그인/회원가입 link 또는 POST 로그아웃 form과 도서 검색 link를
표시한다. focus-visible, label, alt text, `aria-live`를 유지한다.

## 10. 설정과 문서

`.env.example`에 secret 값 없이 `ALADIN_TTB_KEY=`를 추가한다. 설정에서는 이를 빈
문자열 기본값으로 읽어 Django 자체 부팅과 fake 기반 테스트를 막지 않는다. 실제 검색
시 빈 key는 `ProviderConfigurationError`를 거쳐 Error UI로 표시한다.

README에는 Day 02 사용자 흐름, 환경변수, 개발 URL과 실제 알라딘 이용 조건을
추가한다. `CHANGELOG.md`의 `[Unreleased]`와 구현 계획의 IMP-010, IMP-020, IMP-021,
IMP-022, IMP-023 상태는 전체 검증이 끝난 뒤에만 갱신한다.

## 11. 테스트 및 검증

모든 production 동작은 실패하는 테스트를 먼저 확인한 뒤 최소 구현으로 통과시킨다.

- 인증: signup 성공/중복/비밀번호 오류, login 성공/실패, POST logout, 보호 경로 redirect
- 모델: 전체 metadata 저장/조회, ISBN13 database uniqueness
- Adapter: 요청 파라미터, 정상/빈/필드 누락 payload, malformed JSON, Provider 오류,
  network 오류, timeout, key 누락
- Service: query trim, 정상, empty, 각 Provider 예외의 Error 변환
- UI: 전체/HTMX partial, Results/Empty/Error, 반응형 구조와 접근성 label
- Migration: PostgreSQL `sqlmigrate`, forward migration, reverse migration, 재적용
- 전체: `uv run python scripts/verify.py`

외부 알라딘 endpoint는 자동 테스트에서 호출하지 않는다. 실제 key를 사용하는 smoke
test는 이용 승인이 확인되고 사용자가 별도로 요청한 경우에만 수행한다.

## 12. 잔여 위험

- 알라딘의 상업적 이용 조건과 API key 발급은 코드로 해결할 수 없는 운영 선행조건이다.
- 검색 API의 선택 필드 제공 범위는 key 등급에 따라 달라질 수 있다. 누락 필드는
  정규화하고 사실 데이터를 추측하지 않는다.
- Custom User 초기 migration은 다른 도메인 FK가 생기기 전인 지금 적용해야 한다.
  Day 01 기본 auth migration 이력과 충돌하지 않도록 승인된 개발 `postgres_data`
  volume 재생성을 한 번 수행한다. Day 02 이후 기본 auth user로 되돌리는 것은 파괴적
  변경이므로 이번 구현에서 계약을 고정한다.
