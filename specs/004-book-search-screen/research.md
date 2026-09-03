# Phase 0 연구: 도서 검색 화면

## 1. 요청 방식과 주소 계약

**Decision**: 인증된 단일 GET 검색 주소가 query parameter를 받고, 검색어가 없으면 초기
화면을 반환한다.

**Rationale**: 검색은 읽기 전용이며 새로고침·뒤로 가기·주소 공유 시 현재 검색어를 유지할
수 있다. 동일 주소를 일반 요청과 점진적 향상 요청이 함께 사용하면 별도 내부 API 없이
헌법의 서버 렌더링 원칙을 지킬 수 있다.

**Alternatives considered**:

- POST 검색: 상태 변경이 없고 검색 주소를 재현하기 어려워 제외했다.
- JSON API와 browser client 분리: 현재 MVP에 불필요한 Schema, 인증 및 client state를
  추가하므로 제외했다.
- 초기 화면과 결과 주소 분리: 같은 Form과 상태 계약이 중복되어 제외했다.

## 2. View, 입력 검증과 의존성 경계

**Decision**: Django Form이 검색어를 trim하고 필수값·최대 200자를 검증한다. 얇은 function
View는 인증, query 존재 여부, Form 검증, `get_default_provider()`와 기존
`search_books()` 호출, 전체/Fragment Template 선택만 담당한다.

**Rationale**: 무효 입력은 Provider factory 생성 전에 차단할 수 있고, Provider 오류는
기존 Service의 안전한 상태로만 화면에 전달된다. 단순한 단일 메서드 흐름에는 function
View가 가장 명시적이며 별도 Service나 View class 추상화가 필요하지 않다.

**Alternatives considered**:

- View에서 직접 Provider 예외 처리: IMP-022 오류 경계를 중복하고 UI가 Adapter에
  결합되어 제외했다.
- View 내부 문자열 길이 조건: Form 오류 표현과 서버 검증이 분산되어 제외했다.
- Service 내부에서 기본 Provider 생성: 주입 가능성과 외부 호출 대체 경계를 약화해
  제외했다.

## 3. 전체 페이지와 검색 영역 Fragment

**Decision**: 일반 요청은 `books/search.html` 전체 페이지를, HTMX 요청은 Form, Loading,
입력 오류와 결과를 포함하는 `_search_region.html` Fragment를 반환한다. 응답은
`HX-Request`에 따라 달라짐을 명시한다.

**Rationale**: JavaScript가 없어도 검색을 완료할 수 있고, 사용 가능한 환경에서는 검색
영역만 교체해 응답 준비 후 1초 이내 표시 목표를 만족한다. Form까지 Fragment에 포함하면
서버 측 입력 오류와 정규화된 검색어를 같은 경계에서 갱신할 수 있다.

**Alternatives considered**:

- 결과 목록만 교체: Form 오류와 정규화된 검색어를 갱신하기 어려워 제외했다.
- 항상 전체 페이지 반환: Loading, 부분 갱신과 빠른 상태 반영을 제공하지 못해 제외했다.
- client-side Template 생성: 외부 데이터를 browser 코드가 다시 해석해야 해 제외했다.

## 4. 연속 검색과 Loading 상태

**Decision**: 검색 Form은 진행 중인 동일 Form 요청을 새 요청으로 교체한다. 요청 시작 즉시
CSS 요청 상태로 이전 결과를 숨기고 텍스트 Loading만 표시하며, 완료된 최신 응답이 검색
영역 전체를 교체한다.

**Rationale**: 별도 전역 client state 없이 오래된 응답이 최신 결과를 덮는 경쟁 조건과
이전 결과 오인을 함께 방지한다. 텍스트 상태와 `aria-live`는 색상이나 animation만으로
진행 상태를 전달하지 않는다.

**Alternatives considered**:

- 이전 결과를 흐리게 유지: 현재 검색 결과로 오인할 여지가 있어 명확화 답변과 맞지 않는다.
- 모든 검색 요청을 순서대로 완료: 느린 이전 응답이 최신 검색을 덮을 수 있어 제외했다.
- 별도 JavaScript 상태 저장소: 단일 검색 영역에 과도한 복잡성이므로 제외했다.

## 5. 검색 결과와 표지 실패 처리

**Decision**: Provider가 반환한 모든 `ProviderBook`을 기존 순서대로 한 목록에 표시한다.
제목은 항상, 제공된 표지·저자·출판사와 `published_date.year`는 조건부로 표시한다. URL이
없는 표지는 텍스트 placeholder를, URL이 있는 이미지는 의미 있는 대체 텍스트와 고정된
media 영역을 사용한다.

**Rationale**: 별도 DTO 복사 없이 검증된 Metadata를 보존하고, 동명 도서와 판본을 구분할
수 있다. 고정된 표지 영역과 대체 텍스트는 누락·load 실패에도 정보와 layout을 유지한다.
Django autoescape를 유지하고 외부 문자열에 `safe` 처리를 하지 않는다.

**Alternatives considered**:

- 결과를 20건으로 다시 자르기: Service의 Provider 중립 결과 보존 계약과 충돌해 제외했다.
- 누락 Metadata를 기본 문구로 모두 채우기: 제공되지 않은 사실을 추측할 수 있어 제외했다.
- 외부 원본 도서 링크 노출: 이번 기능의 검색·확인 범위를 넘어 제외했다.

## 6. 인증과 오류 노출

**Decision**: 전체 페이지와 Fragment를 제공하는 같은 주소에 기존 Session 인증을 적용한다.
Form 오류와 Empty는 정상 화면 응답으로, Provider 실패는 재시도 가능한 Error 화면으로
표시하되 예외·Provider 유형·원본 메시지는 context와 HTML에 포함하지 않는다.

**Rationale**: 하나의 인증 경계로 익명 사용자의 검색 및 결과 열람을 막고, UI가 외부
오류 계층에 결합되지 않는다. GET 검색에는 상태 변경과 CSRF 예외가 없다.

**Alternatives considered**:

- 공개 검색 화면: 명세의 인증 경계와 Day 02 사용자 흐름에 어긋나 제외했다.
- 오류 유형별 사용자 메시지: 외부 세부사항 노출과 UI 결합을 만들므로 제외했다.
- 오류에 HTTP transport 실패 상태 사용: HTMX 기본 swap과 사용자용 상태 표시를 복잡하게
  해 화면 상태로 안전하게 표현하는 방식을 선택했다.

## 7. 검증 범위

**Decision**: pytest와 Django test client로 인증, 입력 경계, Service 상태, 전체/Fragment
응답, Metadata 보존, 오류 비노출과 HTML 접근성 계약을 자동 검증한다. 새 browser 자동화
의존성 없이 1280px Desktop과 375px Mobile을 실제 browser에서 확인한다.

**Rationale**: 외부 Provider factory만 fake로 대체하면 실제 Service 흐름을 검증하면서
network 호출을 제거할 수 있다. 현재 도구로 검증 가능한 계약과 실제 layout·keyboard
검증을 분리하면 신규 dependency 없이 완료 증거를 남길 수 있다.

**Alternatives considered**:

- Service 자체까지 Mocking: 상태 변환과 View 결합 오류를 숨겨 제외했다.
- 이번 기능에서 browser test framework 추가: 한 화면의 MVP 검증에 dependency와 설정
  비용이 커 제외했다.
- 수동 검증만 수행: 회귀 가능한 인증·상태·보안 계약을 남기지 못해 제외했다.
