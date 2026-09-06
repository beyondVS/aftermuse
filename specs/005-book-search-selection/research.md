# Phase 0 연구: 도서 검색 복구 및 선택

## 1. Provider 중립 경계와 Kakao 호출

**Decision**: 공통 계약·예외·factory의 정본을 `integrations.book_metadata`로 옮기고
legacy Aladin 경로는 re-export한다. Kakao Adapter는 표준 `urllib` 동기 GET으로 공식
`/v3/search/book` endpoint를 `sort=accuracy`, `page=1`, `size=20`, timeout 3초로 호출하며
REST API key는 Authorization header에만 넣는다.

**Rationale**: Service의 Aladin 이름 결합을 제거하면서 기존 import 회귀를 막는다. 공식
계약과 기존 20건 UI 규모를 유지하고 새 runtime dependency와 URL secret 노출을 피한다.

**Alternatives considered**: 기존 Aladin package를 정본으로 유지, 호환 경로 즉시 삭제,
key의 query string 전달, 50건 확대, `requests`/`httpx` 추가는 각각 중립성·회귀·보안·UI
크기·의존성 비용 때문에 제외했다.

## 2. Kakao 응답과 오류 정규화

**Decision**: JSON object와 `documents` list를 검증한다. document의 `isbn` 공백 token 중
ASCII 숫자 13자리와 trim한 제목을 필수로 하고, 저자 배열은 `, `로 연결하며 ISO datetime의
날짜만 보존한다. Kakao가 제공하지 않는 목차는 빈 문자열이다. 설정, timeout,
network/HTTP·quota, 응답 구조 오류는 기존 Provider 예외 계층으로 변환한다.

**Rationale**: Kakao는 ISBN10 또는 ISBN13을 제공하며 둘 다 있으면 공백으로 구분한다.
기존 Book 계약에 맞는 판본만 통과시키고 누락값을 추측하지 않는다. UI에는 모든 외부
실패를 안전한 Error로 유지한다.

**Alternatives considered**: ISBN10 변환은 외부에 없는 식별자를 생성한다. 첫 결함 항목에서
전체 실패시키면 유효 결과를 잃는다. 자동 retry와 Aladin fallback은 quota와 승인된 운영
정책에 맞지 않는다.

## 3. 선택 후보 저장과 수명

**Decision**: DB-backed Django session에 최신 성공 검색 최대 20건을 JSON 기본형으로
저장한다. 후보는 예측하기 어려운 ID, 사용자 PK, Metadata, Unix 생성 시각을 가지며
15분 뒤 만료한다. 새 유효 검색 시작 시 이전 batch를 제거하고 Empty/Error도 후보를
남기지 않는다.

**Rationale**: 명확화 답변 A의 서버 보관 경계를 기존 인프라로 충족한다. 사용자별 session,
20건·15분 제한은 별도 model/cache와 청소 작업 없이 payload와 오래된 데이터 사용을
제한한다.

**Alternatives considered**: 별도 model은 migration과 정리 작업을 만들고, 서명 payload는
Metadata를 client와 왕복하며, 선택 시 Kakao 재조회는 장애·quota 영향을 늘리고, process
memory는 다중 worker에서 일관되지 않는다.

## 4. 후보 직렬화·소유권·재시도

**Decision**: 날짜는 ISO 문자열, 생성 시각은 숫자로 저장한다. 선택 조회는 후보 ID,
현재 사용자 PK와 TTL을 모두 검증한다. 성공 후 후보는 TTL까지 유지하여 이중 클릭과
재전송이 같은 Book을 반환하게 한다.

**Rationale**: Django 기본 session serializer는 JSON 기본형만 안정적으로 처리한다.
명시적 소유권 검사는 보안 불변조건을 드러내며, 후보 유지와 Book unique 정책은 선택을
멱등적으로 만든다.

**Alternatives considered**: custom/pickle serializer는 공격 표면을 늘리고, session key에만
소유권을 맡기면 계약 검증이 약해지며, 일회성 삭제는 network 재시도 UX를 해친다.

## 5. Book 선택과 HTTP/UI

**Decision**: 후보 식별자만 받는 CSRF 보호 POST를 추가한다. 얇은 View가 session 후보를
조회하고, Service는 짧은 transaction에서 ISBN13 `get_or_create`로 기존 Book을 재사용하거나
새 Book을 만든다. HTMX는 결과 Fragment, 일반 요청은 전체 페이지를 반환하며 Reading
행동은 추가하지 않는다.

**Rationale**: client Metadata 변조를 차단하고 JavaScript 없이 상태 변경을 완료한다.
PostgreSQL unique 제약이 동시 선택을 최종 한 건으로 제한하며 기존 Metadata는 보존된다.

**Alternatives considered**: 선택 GET, JSON API, 사전 조회 후 무조건 create, table lock,
기존 Metadata 갱신, 미구현 Reading redirect는 보안·복잡성·경쟁 조건·범위 때문에 제외했다.

## 6. 검증 전략

**Decision**: Adapter는 fake transport로 결정적으로 검증하고, session·Service·View는 실제
Django/PostgreSQL 상태를 검증한다. 실제 Kakao key smoke에는 `live` marker를 지정한다.
프로젝트 기본 pytest 선택식은 `not live`로 두고 `-m live`를 명시한 실행에서만 수집한다.

**Rationale**: 기본 suite는 network·credential과 독립적이어야 하지만 IMP-025 완료에는
운영 후보 연결 증거도 필요하다. 외부 I/O만 fake로 두고 내부 정책은 실제로 실행하며,
credential 유무만으로 기본 전체 테스트에서 live 호출이 활성화되지 않게 한다.

**Alternatives considered**: 모든 테스트의 live 호출은 느리고 불안정하며, 내부 Service까지
mocking하면 통합 결함을 숨기고, 수동 curl만 사용하면 재현 가능한 assertion이 없다.

## 확인 근거

- `specs/005-book-search-selection/spec.md`
- `.specify/memory/constitution.md`
- `docs/AfterMuse_MVP_PRD_v4.md`
- `docs/AfterMuse_MVP_Implementation_Plan_v5.md`
- Kakao 공식 도서 검색 API: https://developers.kakao.com/docs/ko/daum-search/dev-guide
- Kakao 공식 quota 안내: https://developers.kakao.com/docs/ko/daum-search/common
- Django 6.1 session 설정: https://docs.djangoproject.com/en/6.1/ref/settings/#sessions
- Django 6.1 session 사용법: https://docs.djangoproject.com/en/6.1/topics/http/sessions/

모든 기술적 미확정 사항을 해소했으며 `NEEDS CLARIFICATION`은 없다.
