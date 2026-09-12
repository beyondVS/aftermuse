# 조사: 답변 분석 계약

## 결정 1: Provider 제안과 검증된 application 결과를 분리한다

**Decision**: LLM/fake가 반환한 DTO는 string·nullable 기반 제안으로 유지하고, Application
Service가 이를 enum과 immutable trusted result로 변환한다.

**Rationale**: strict JSON schema는 wire shape를 제한하지만 business invariant까지 보장하지
않는다. 알 수 없는 값, 중복 축, 동일·하락 후보, 근거 불일치와 low-information 모순을
Application이 다시 검사해야 Structured Output + Application Validation 경계를 충족한다.

**Alternatives considered**:

- Adapter에서 곧바로 domain enum으로 변환: Application 검증을 우회하고 다른 Adapter의 손상
  결과를 동일하게 방어하기 어렵다.
- raw dict 전달: 손상 사례는 보존되지만 타입·필수 field 계약이 지나치게 느슨하다.

## 결정 2: 분석 결과와 시도는 저장하지 않는다

**Decision**: 검증된 분석 결과를 immutable 값으로 반환할 뿐 Turn, Interview, JSON metadata 또는
신규 모델에 저장하지 않는다.

**Rationale**: 명세에서 확정된 범위이며 Coverage 적용과 다음 Turn의 원자성은 Bundle 07C가
소유한다. 지금 저장하면 stale 분석 lifecycle과 재분석 versioning을 선행 결정해야 한다.

**Alternatives considered**:

- Turn JSON field: schema migration과 stale 결과 교체 정책이 필요하다.
- 분석 이력 모델: 비공개 답변 중복 저장과 운영 복잡성이 현재 요구를 초과한다.

## 결정 3: 기존 Context Pack에 Turn과 현재 Coverage를 합성한다

**Decision**: 기존 book/reading/readiness/verified claims/policy를 재사용하고 대상 질문·답변 및
네 canonical Coverage 상태를 추가한 `AnswerAnalysisContext`를 만든다.

**Rationale**: IMP-060의 READY/READY_LIMITED 경계를 유지하면서 질문 문맥에서 답변을 해석하고
현재 상태보다 높은 후보만 제안할 수 있다.

**Alternatives considered**:

- 질문과 답변만 전달: Coverage 상승과 책 맥락 해석이 불안정하다.
- 전체 ORM 객체: Adapter가 DB/domain 객체에 결합된다.
- 과거 Turn 전체: 단일 답변 분석 범위와 payload를 불필요하게 확장한다.

## 결정 4: 후보 근거는 원문 연속 부분 문자열로 검증한다

**Decision**: 각 후보는 1~500자의 양끝 공백 없는 evidence를 포함하고 Application은
`evidence in answer`인 exact contiguous substring만 허용한다.

**Rationale**: 위치 index는 Unicode 계산 오류에 취약하고 자유 paraphrase는 원문 근거를
기계적으로 확인할 수 없다.

**Alternatives considered**:

- 시작/끝 offset: Provider가 Unicode 문자열 index를 정확히 계산해야 한다.
- paraphrased evidence: application에서 원문 일치를 검증할 수 없다.
- 공통 evidence 목록: 축별 판정 근거를 분리할 수 없다.

## 결정 5: Coverage 후보는 strict promotion만 허용한다

**Decision**: `UNCOVERED`는 `PARTIAL`/`COVERED`, `PARTIAL`은 `COVERED`만 허용하고
`COVERED`에는 후보를 허용하지 않는다.

**Rationale**: 후보는 답변의 절대 분류가 아니라 현재 Interview 상태에 대한 실제 진전이다.
동일 상태를 제거하면 재분석과 반복 답변이 불필요한 patch를 만들지 않는다.

**Alternatives considered**:

- 동일 상태 허용: Bundle 07A에서는 no-op이지만 `변경 후보`의 의미가 흐려진다.
- Application이 위반 후보를 조용히 제거: 결과 전체 검증 계약과 맞지 않는다.

## 결정 6: low-information은 nullable invariant로 표현한다

**Decision**: `low_information=True`이면 `meaning=None`과 빈 후보 tuple, `False`이면 1~1,000자의
nonblank meaning이며 후보는 비어 있을 수도 있다.

**Rationale**: `None`은 추출 가능한 의미 없음과 빈 문자열/생성 실패를 구분한다. 정상 답변이
이미 다룬 내용을 반복할 수 있으므로 빈 후보가 low-information을 뜻하지는 않는다.

**Alternatives considered**:

- 빈 문자열: 누락·trim 결과와 의도적 무의미 판정을 구분하기 어렵다.
- 분류 이유를 meaning으로 반환: 사용자의 생각과 시스템 설명이 섞인다.

## 결정 7: 기존 설정을 공유하되 별도 Protocol과 Adapter 클래스를 둔다

**Decision**: 질문과 분석은 기존 LLM 설정을 공유하지만 분석 전용 Protocol과
`OpenAIAnswerAnalysisProvider`/`FakeAnswerAnalysisProvider`를 둔다.

**Rationale**: 운영 설정을 추가하지 않으면서 질문 생성과 분석의 입출력·오류 계약을 섞지 않는다.

**Alternatives considered**:

- 질문 Provider class에 분석 메서드 추가: 서로 다른 책임과 테스트가 결합된다.
- 분석 전용 환경변수: 현재 승인된 설정과 범위를 불필요하게 넓힌다.

## 결정 8: 외부 호출은 정책 검증 뒤 transaction 밖에서 한 번만 수행한다

**Decision**: 소유권, 관계, status, Turn 소속, 답변과 Coverage를 먼저 검증한 뒤 Provider를 만들고
한 번 호출한다. DB transaction과 write는 없다.

**Rationale**: 권한 없는 요청이 비용을 발생시키지 않고 설정 오류가 정책 오류를 가리지 않는다.
느린 I/O 동안 lock을 유지하지 않으며 실패가 저장된 답변을 손상시킬 경로가 없다.

**Alternatives considered**:

- Provider 호출 후 검증: 권한·비용·정보 노출 경계를 위반한다.
- transaction에서 호출: 장시간 transaction이 생기며 commit할 상태도 없다.
- 자동 재시도: 중복 비용과 지연을 키우므로 기존처럼 SDK retry를 0으로 둔다.
