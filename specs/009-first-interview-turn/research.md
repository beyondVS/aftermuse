# Phase 0 조사: 첫 인터뷰 Turn

## 결정 1: Provider-neutral 계약과 fake를 먼저 둔다

**Decision**: `generate_first_question(context) -> GeneratedQuestion` 내부 계약과 명시적 오류
taxonomy를 정의하고, 기본 자동 테스트는 deterministic fake로 정상·timeout·실패·invalid
output을 재현한다.

**Rationale**: 실제 Provider 없이 전체 흐름을 검증하면서 도메인 Service가 SDK 예외나 응답
객체를 알지 않게 해야 Day 07/09에서도 같은 경계를 재사용할 수 있다.

**Alternatives considered**: View의 SDK 직접 호출은 thin view와 test isolation을 깨고, OpenAI
client mock만 사용하면 도메인 흐름이 SDK 모양에 결합되며, 자체 HTTP client는 공식 SDK를
중복 구현한다.

## 결정 2: OpenAI Responses API와 structured output을 사용한다

**Decision**: `openai~=3.10.0`의 Responses API와 `{question: string}` strict schema를 사용한다.
기본 모델은 설정 가능한 pinned snapshot `gpt-5.4-mini-2026-03-17`이며 tools를 제공하지 않고
`store=False`로 호출한다.

**Rationale**: 공식 OpenAI 문서는 Responses API를 기본 text generation 경계로 안내하고 JSON
Schema Structured Outputs를 지원한다. GPT-5.4 Mini snapshot은 text/structured output을
지원하며 고정 snapshot은 질문 품질 회귀를 재현하기 쉽다. PyPI의 SDK 3.10.0은 Python 3.14를
지원한다.

**Alternatives considered**: moving alias는 예고 없는 품질 변화를 만들 수 있고, flagship 모델은
짧은 질문 생성에 비용이 크며, nano 모델은 핵심 제품 가설인 질문 품질의 기본값으로 보수적이지
않다. plain text parsing은 structured output 원칙보다 약하다.

**Sources**:

- [OpenAI Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
- [OpenAI Structured Outputs reference](https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses)
- [GPT-5.4 Mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [OpenAI Python SDK on PyPI](https://pypi.org/project/openai/)

## 결정 3: 30초 전체 timeout과 SDK retry 0회를 사용한다

**Decision**: Provider client의 전체 timeout을 30초로 설정하고 SDK automatic retry는 끈다.
timeout, 연결 오류, rate limit, status 오류와 parse/validation 오류를 domain-safe 오류로 변환한다.

**Rationale**: SDK 기본 timeout과 retry를 그대로 두면 명세의 30초 UX 상한을 넘을 수 있다.
사용자가 같은 화면에서 명시적으로 재시도하므로 SDK retry까지 겹치지 않는다.

**Alternatives considered**: 기본 retry 2회는 총 대기시간이 불명확하고, application 자동 retry는
명확화 결정과 충돌하며, background job은 상태·queue·polling 복잡성을 추가한다.

## 결정 4: HTMX 자동 POST와 일반 form fallback을 함께 사용한다

**Decision**: Interview 상세 GET은 무부작용 page shell을 반환한다. 질문이 없으면 CSRF form에
`hx-post`와 load trigger를 적용해 자동 준비하고, JavaScript가 없으면 같은 form의 버튼으로
사용자가 질문 준비 POST를 실행한다.

**Rationale**: 질문 생성과 Turn 저장은 GET이 아니라 POST에 남기면서 Loading → Question/Error
전환을 같은 화면에서 제공하고 progressive enhancement를 유지한다.

**Alternatives considered**: GET에서 질문 저장은 HTTP 의미를 위반하고, Interview 시작 POST가
Provider까지 기다리면 기존 생성 transaction과 외부 I/O가 결합되며, 별도 준비 page는
same-screen 계약보다 복잡하다.

## 결정 5: Provider I/O 뒤 짧은 transaction에서 sequence 1을 멱등 저장한다

**Decision**: 기존 first Turn을 먼저 조회한다. 없으면 Context를 만들고 Provider를 transaction
밖에서 호출·검증한 뒤, 짧은 transaction에서 Interview를 잠그고 기존 Turn을 재확인해 없을 때만
sequence 1을 생성한다. 경쟁 요청의 loser는 이미 저장된 Turn을 반환한다.

**Rationale**: 느린 I/O 동안 DB lock을 보유하지 않으면서 기존 UNIQUE를 최종 방어로 사용한다.
중복 Provider 호출 가능성은 Core MVP에서 허용하되 DB 상태는 하나로 수렴한다.

**Alternatives considered**: Provider 호출을 row lock 안에 넣으면 connection과 lock을 최대 30초
점유하고, lease/status column은 migration과 stale lease 복구가 필요하며, cache lock은 새 운영
의존성이다.

## 결정 6: 답변은 최초 성공 값만 저장한다

**Decision**: Answer form은 trim 후 1~2,000자를 검증한다. Service는 Turn을 잠그고 answer가
`NULL`일 때만 저장한다. 동일 값 재제출은 멱등 성공, 다른 값 재제출은 conflict로 처리하고 기존
원문을 반환한다. 저장 오류 응답은 bound form을 그대로 다시 렌더링한다.

**Rationale**: 최초 저장 후 불변이라는 명확화와 동시 제출의 결정적 수렴을 함께 만족한다.

**Alternatives considered**: last-write-wins는 확정 원문을 조용히 바꾸고, 모든 중복을 오류로 만들면
네트워크 재전송의 정상 멱등성을 잃으며, client-side 영구 draft는 이번 범위를 넘는다.

## 결정 7: schema migration을 만들지 않는다

**Decision**: 기존 `question varchar(2000)`과 nullable answer 저장 형식을 유지하고, 좁은 300자/
2,000자 계약은 form, model validation과 public Service에서 강제한다. migration drift 0건을
검증한다.

**Rationale**: 기존 schema는 새 값을 손실 없이 저장하는 상위 호환 형식이다. varchar 축소나
새 CHECK는 PostgreSQL에서 `ACCESS EXCLUSIVE`와 기존 행 검사 위험을 만들지만 이 Bundle의
Service-only write 경계에는 실익이 작다.

**Alternatives considered**: column 축소와 answer type 변경은 배포 잠금을 만들고,
NOT VALID/VALIDATE CHECK는 두 단계 migration과 운영 복잡성을 추가하며, 새 Answer 모델은 현재
1:1 Turn-answer 계약에 불필요하다.
