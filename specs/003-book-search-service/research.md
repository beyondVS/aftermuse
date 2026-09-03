# Phase 0 연구: 도서 검색 Service와 결과 정규화

## 1. Service 경계와 의존 방향

**Decision**: `books` 도메인의 순수 Python Service가 기존
`BookMetadataProvider` Protocol을 인자로 받고 구체 알라딘 Adapter, Django View 및 ORM에
의존하지 않게 한다.

**Rationale**: 검색 상태 정규화는 도서 도메인 정책이며 Provider별 network와 응답 파싱은
IMP-021 Adapter의 책임이다. Protocol 주입은 실제 외부 호출 없이 계약을 검증하고 IMP-023
화면이 구체 Provider에 결합되는 것을 막는다.

**Alternatives considered**:

- View에서 Adapter를 직접 호출: HTTP와 Provider 실패 정책이 결합되고 Service 계약을
  독립 검증할 수 없어 제외했다.
- Service 내부에서 기본 Provider를 생성: 테스트 대체 경계와 공급자 독립성이 약해져
  제외했다.
- Repository 계층 추가: 영속성 작업이 없으므로 불필요한 추상화라 제외했다.

## 2. 검색 결과 상태 모델

**Decision**: `SUCCESS`, `EMPTY`, `ERROR`의 세 상태와 `ProviderBook` tuple을 갖는 불변
결과 객체를 사용한다.

**Rationale**: 후속 화면은 성공, 정상 무결과, 복구 가능한 검색 실패를 안정적으로
구분해야 하지만 구체 Provider 오류 계층을 알 필요는 없다. enum과 불변 값 객체는 허용된
상태를 제한하고 상태-데이터 불변조건을 테스트하기 쉽다.

**Alternatives considered**:

- 빈 tuple과 예외만 반환: 정상 무결과와 화면에 표시할 검색 실패 처리가 호출부마다
  달라져 제외했다.
- Provider 예외 유형을 결과 상태로 그대로 노출: UI가 외부 연동 세부사항에 결합되고
  자격 증명·원본 오류 노출 위험이 커져 제외했다.
- 성공 여부 boolean 하나: 정상 무결과와 오류를 표현할 수 없어 제외했다.

## 3. Metadata 정규화 책임

**Decision**: Service는 Provider가 검증한 `ProviderBook`과 결과 순서를 그대로 보존하고,
별도 검색용 도서 DTO를 만들지 않는다. 전체 출간일을 유지하며 출간연도는 IMP-023 화면에서
파생한다.

**Rationale**: ISBN13, 제목 및 선택 Metadata 정규화는 IMP-021에서 이미 완료됐다. 다시
복사하거나 출간일을 연도로 축소하면 정보 손실과 두 계약의 불일치가 생긴다.

**Alternatives considered**:

- 출간연도만 가진 새 DTO: 전체 출간일을 잃고 중복 mapping이 생겨 제외했다.
- 전체 출간일과 파생 연도를 함께 저장: 파생값 중복과 일관성 관리가 필요해 제외했다.
- Service에서 빈 선택값을 보완: 사실을 추측하지 않는 명세와 신뢰 경계를 위반해 제외했다.

## 4. 검색어와 호출 정책

**Decision**: 양끝 공백만 제거하고 내부 문자열은 유지한다. 정규화 후 빈 검색어는 Provider를
호출하지 않고 `EMPTY`를 반환하며, 유효한 검색어는 정확히 한 번 호출한다.

**Rationale**: Service는 의미 없는 외부 요청을 차단하면서도 검색어의 사용자 의도를
변경하지 않아야 한다. 길이와 허용 문자 검증은 IMP-023 입력 경계의 책임으로 유지한다.

**Alternatives considered**:

- 모든 공백 압축 또는 대소문자 변환: 책 제목과 저자명 의미를 바꿀 수 있어 제외했다.
- 공백 검색도 Provider에 전달: 비용과 오류 가능성만 늘어나 제외했다.
- Service에서 화면 입력 제한까지 검증: IMP-023과 책임이 중복되어 제외했다.

## 5. 오류 격리 정책

**Decision**: 기존 `ProviderError` 계층만 포착해 도서가 없는 `ERROR` 결과로 변환한다.
예상하지 못한 프로그래밍 오류는 포착하지 않는다.

**Rationale**: 설정, timeout, 통신 및 응답 오류는 모두 후속 검색 흐름에 동일한 안전한
실패 상태로 제공해야 한다. 반면 광범위한 예외 포착은 코드 결함을 정상적인 외부 실패로
숨길 수 있다.

**Alternatives considered**:

- 모든 `Exception` 포착: 내부 결함을 은폐하므로 제외했다.
- Provider 오류를 그대로 재발생: 후속 화면이 구체 Provider 계약에 결합되어 제외했다.
- 오류 메시지를 결과에 포함: 민감한 외부 상세가 노출될 수 있어 제외했다.

## 6. 검증 전략

**Decision**: 호출 기록과 준비된 결과 또는 오류를 제공하는 작은 fake Provider로 Service를
단위 검증하고, 완료 시 프로젝트 전체 품질 스크립트를 실행한다.

**Rationale**: 대체 대상은 외부 I/O 경계뿐이며 Service의 실제 분기와 불변조건을 그대로
실행할 수 있다. DB fixture와 실제 알라딘 credential이 필요하지 않다.

**Alternatives considered**:

- 실제 알라딘 호출: 불안정하고 credential 및 이용 승인에 의존해 제외했다.
- Service 자체를 mock: 검증해야 할 상태 정책을 우회하므로 제외했다.
- DB 통합 테스트: 이 기능은 영속성이 없어 추가 가치가 없으므로 제외했다.

모든 기술적 미확정 사항을 해소했으며 `NEEDS CLARIFICATION`은 없다.
