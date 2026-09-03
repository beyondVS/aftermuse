# Phase 0 연구: 알라딘 Metadata Provider Adapter

## 1. HTTP 호출 구현

**Decision**: 새 패키지 없이 `urllib.request.urlopen`을 사용하는 동기 기본 transport를
구현한다.

**Rationale**: 현재 HTTP client 의존성이 없고 단일 GET과 byte 응답만 필요하다. 기존
Day 02 승인 설계도 표준 라이브러리를 채택한다.

**Alternatives considered**: `httpx`와 `requests`는 이 범위에 비해 의존성 비용이 크고,
비동기 client는 현재 동기 Django 흐름에 불필요하다.

## 2. 테스트 대체 경계

**Decision**: `Callable[[str, float], bytes]` transport를 Adapter 생성자에 주입하고
기본값만 실제 네트워크를 사용한다.

**Rationale**: closure fake가 payload/예외를 제공하고 URL과 timeout을 기록할 수 있다.
내부 파서는 실제로 검증하므로 과도한 mocking도 피한다.

**Alternatives considered**: `urlopen` monkeypatch는 구현 세부사항에 결합되고, fake
server는 이 단위 계약에 과하며, setting 기반 교체는 테스트 상태를 전역화한다.

## 3. 성공과 실패 표현

**Decision**: 성공은 `tuple[ProviderBook, ...]`, 정상 빈 결과는 `()`로 반환한다. 실패는
`ProviderError` 아래의 `ProviderConfigurationError`, `ProviderTimeoutError`,
`ProviderUnavailableError`, `ProviderResponseError`로 구분한다.

**Rationale**: 호출자는 예외 종류로 원인을 안정적으로 식별하고 IMP-022 Service는 이를
화면용 상태로 축약할 수 있다.

**Alternatives considered**: 단일 예외는 완료 조건을 만족하지 못하고, Result 객체는 후속
Service와 상태를 중복하며, 원본 라이브러리 예외 노출은 Provider 교체성을 훼손한다.

## 4. 알라딘 요청 계약

**Decision**: HTTPS `ItemSearch.aspx`에 `ttbkey`, `Query`, `QueryType=Keyword`,
`MaxResults=20`, `start=1`, `SearchTarget=Book`, `output=js`, `Version=20131101`을
URL encoding하여 전달하고 기본 timeout은 3초로 한다.

**Rationale**: 알라딘 공식 안내의 검색 계약을 따르며 HTTPS로 key 평문 전송을 피한다.
명시적 timeout은 무한 대기를 막는다.

**Alternatives considered**: XML은 파싱 복잡성이 늘고, 제목 전용 검색은 제품 계약보다
좁으며, retry 내장은 이번 범위를 넘어선다.

## 5. 외부 응답 검증과 정규화

**Decision**: 최상위 JSON object와 `item` list를 검증한다. ISBN13은 ASCII 숫자
13자리, 제목은 trim 후 비어 있지 않아야 한다. 결함 항목만 제외하고 선택 문자열은
빈 문자열, 해석 불가 날짜는 `None`으로 둔다.

**Rationale**: 구조 전체가 손상되면 추측하지 않되 개별 결함이 유효 항목을 폐기하게
하지 않는다. `str.isdigit()`만 사용하면 Unicode 숫자를 허용하므로 ASCII를 별도
검사한다.

**Alternatives considered**: 첫 항목 오류에서 전체 실패하면 유효 결과를 잃고, 누락값
추측이나 원본 payload 저장은 신뢰 경계와 기능 범위를 위반한다.

## 6. 설정 및 운영 조건

**Decision**: `ALADIN_TTB_KEY`는 빈 문자열 기본값을 가진 조건부 Django 설정으로 읽고,
검색 시 비어 있으면 transport 호출 전에 설정 오류를 발생시킨다.

**Rationale**: 알라딘 미사용 개발 명령과 fake 테스트는 credential 없이 실행 가능해야
하지만 실제 검색에서는 누락을 빈 결과로 숨기면 안 된다.

**Alternatives considered**: 시작 단계 무조건 실패는 무관한 품질 명령도 막고, key 내장은
보안 위반이며, 메서드 인자 전달은 secret 취급 범위를 확산한다.

## 확인 근거

- `docs/superpowers/specs/2026-09-02-day-02-auth-book-search-design.md`
- `docs/superpowers/plans/2026-09-02-day-02-auth-book-search.md`
- `.specify/memory/constitution.md`
- 알라딘 공식 검색 API: `https://blog.aladin.co.kr/openapi/5353290`
- 알라딘 공식 이용 안내: `https://blog.aladin.co.kr/openapi/6695306`
- 알라딘 공식 이용 조건: `https://blog.aladin.co.kr/openapi/5353304`

모든 기술적 미확정 사항을 해소했으며 `NEEDS CLARIFICATION`은 없다.
