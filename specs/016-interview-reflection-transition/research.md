# 조사: Interview 상호작용과 Reflection 생성 Transition

## 1. 사용자 Skip 저장 표현과 경합

**Decision**: `InterviewTurn.user_skipped_at` nullable 시각을 추가하고 `answer`와 상호 배타인 DB CHECK 및 model validation을 둔다. Skip Service는 Interview와 현재 Turn을 같은 transaction에서 잠그며, 같은 Skip 재요청은 멱등 성공하고 답변과 경합한 요청은 먼저 확정된 결과만 보존한다.

**Rationale**: 기존 `next_question_skipped_at`은 답변 후 Provider가 다음 질문을 생략한 결과이므로 사용자 미답변과 의미가 다르다. nullable timestamp는 기존 행 backfill 없이 선택 시점과 상태를 함께 표현한다. row lock과 DB CHECK를 겹치면 일반 Service와 우회 write 모두에서 답변·Skip 동시 상태를 막을 수 있다.

**Alternatives considered**: 빈 Answer는 저정보 답변과 사용자 선택을 구분하지 못한다. 기존 skip 필드 재사용은 “현재 질문 미답변”과 “다음 질문 없음”을 혼동한다. 별도 Skip 테이블은 현재 1:1 상태에 불필요한 관계와 query를 늘린다.

## 2. Skip 이후 다음 질문과 Coverage

**Decision**: Skip은 답변 분석을 호출하지 않고 Coverage를 그대로 둔다. 다음 질문 입력에는 `user_skipped=true`, 현재 answer 없음, 건너뛴 질문 목록을 별도 trusted shape로 전달하여 low-information 답변과 구분한다. Provider는 같은 질문을 압박하거나 반복하지 않고 미충족 축으로 전환하며, Application은 기존 READY_LIMITED 사실 전제 방지를 그대로 적용한다.

**Rationale**: 현재 `NextQuestionContext`는 answer가 있다고 가정한다. 빈 문자열과 `low_information=true`로 우회하면 명시적 Skip과 실제 “모르겠어요” 답변이 wire·prompt·검증에서 다시 섞인다. 별도 신호는 FR-011을 지키고 반복 질문 방지 자료를 제공한다.

**Alternatives considered**: 첫 질문 Provider 재사용은 답변/이력 문맥이 없어 질문 반복 가능성이 높다. Skip을 분석 Provider에 전달하면 존재하지 않는 사용자 발화에서 의미·Coverage를 만들 위험이 있다. 고정 질문 목록은 Coverage 기반 Interview 원칙을 훼손한다.

## 3. Budget과 답변 없는 종결 상태

**Decision**: budget snapshot을 `question_count`, `answered_count`, `user_skipped_count`로 확장하고 `answered_count + user_skipped_count == question_count`를 해결된 Turn 불변식으로 사용한다. 질문 일반/절대 상한은 해결된 Turn 수로 계산한다. 종료 선택 또는 절대 상한에서 답변이 하나 이상이면 `REFLECTION_READY`, 0개면 새 terminal `ENDED_NO_REFLECTION`로 전이한다.

**Rationale**: Skip을 budget에서 제외하면 사용자가 계속 Skip할 때 safety cap을 넘는다. 기존 `COMPLETED`는 Reflection 최종 확인을 뜻하므로 답변 없는 종결에 재사용하면 Home·destination·후속 Day 12 의미가 깨진다. 별도 상태는 생성 실패/재시도와도 구분된다.

**Alternatives considered**: 마지막 Skip 차단은 사용자의 명시적 선택과 확정 명세를 위반한다. 빈 Reflection 생성은 헌법의 사용자 생각 충실성을 위반한다. 기존 `REFLECTION_READY` 유지는 생성 불가능한 Interview에 Retry를 계속 노출한다.

## 4. Skip persistence와 Provider 실패 복구

**Decision**: Skip 표식은 짧은 transaction에서 먼저 확정한다. budget상 추가 질문이 필요할 때만 transaction 밖에서 Provider를 호출하고, 두 번째 짧은 transaction에서 상태/Turn을 재검증해 다음 Turn을 삽입한다. Provider 실패 시 Skip은 유지되고 동일 endpoint 재요청이 후속 전이를 재개한다.

**Rationale**: 사용자의 Skip 선택은 외부 서비스 성공 여부와 무관한 원본 행동이다. Provider 호출 중 row lock을 유지하면 다른 요청과 DB 자원을 불필요하게 막는다. 기존 답변 저장→다음 질문 생성의 회복 패턴과도 일치한다.

**Alternatives considered**: 전체 흐름을 한 transaction으로 묶으면 최대 Provider timeout 동안 lock을 유지한다. 실패 시 Skip까지 rollback하면 사용자가 같은 질문을 다시 Skip해야 한다. 비동기 queue는 Scope Gate를 넘는다.

## 5. Reflection 생성 orchestration과 멱등성

**Decision**: 동기식 POST에서 owner-scoped 기존 Reflection을 먼저 조회하고 있으면 Provider 없이 반환한다. 없으면 기존 `generate_reflection_draft`를 transaction 밖에서 한 번 호출하고 `save_reflection_draft`로 저장한다. concurrent save conflict는 기존 owner Reflection을 다시 조회해 성공으로 수렴한다. UI는 `hx-sync=drop`, disabled submit 및 loading indicator로 같은 화면의 중복 요청을 억제한다.

**Rationale**: Day 10의 OneToOne·Interview lock·snapshot 재검증이 최종 중복과 overwrite를 이미 방어한다. persisted “GENERATING” row 없이도 결과 멱등성을 보장하며, synchronous Scope Gate와 기존 Provider timeout을 유지한다.

**Alternatives considered**: 생성 중 상태 테이블·distributed lock·Celery polling은 복잡한 background 체계를 만든다. Provider 호출 동안 Interview row lock을 유지하면 긴 DB lock이 된다. 자동 retry/fallback은 비용·실패 의미를 숨긴다.

**Known limit**: 서로 다른 HTTP 요청이 정확히 동시에 시작되면 외부 Provider 호출 자체는 둘 발생할 수 있으나 저장 결과는 하나로 수렴한다. 이번 범위의 single-flight는 한 화면의 중복 행동 억제와 최종 persistence 멱등성이다.

## 6. 생성 화면, 오류와 최소 결과

**Decision**: `REFLECTION_READY` GET은 기존 Reflection이 없으면 progressive enhancement form을 포함한 생성 화면을 반환한다. HTMX는 load 직후 POST하고 loading status를 표시하며, JavaScript가 없으면 명시적 생성 버튼으로 제출한다. 성공은 Reflection id 기반 최소 임시 결과 GET으로 redirect하고, 실패는 같은 region에 안전한 오류와 Retry form을 반환한다.

**Rationale**: 첫 질문 loading 흐름과 동일한 서버 렌더링/HTMX 관례를 재사용한다. 최소 결과 화면은 생성 성공과 소유한 Reflection의 존재만 확인하여 Day 11을 독립 검증하면서 Day 12 본문 레이아웃·편집을 선행하지 않는다.

**Alternatives considered**: 성공 상태에 머무르면 명세의 자동 전환을 충족하지 못한다. Day 12 화면 전체를 구현하면 범위가 확장된다. JSON API/클라이언트 polling은 현재 architecture와 맞지 않는다.

## 7. 사용자용 Knowledge 표현

**Decision**: View의 내부 readiness 값은 분기용으로만 사용하고 template에는 사용자 안내 boolean/문구를 제공한다. READY는 별도 기술 상태를 표시하지 않고, READY_LIMITED는 “확인할 수 있는 정보가 많지 않아 기억에 남은 내용부터 함께 이야기한다”는 안내를 시작·질문 화면에 일관되게 표시한다.

**Rationale**: 현재 두 template이 `준비 수준: READY[_LIMITED]`를 직접 노출한다. 분기와 domain enum은 유지하면서 presentation만 바꾸면 기존 정책·저장 계약을 건드리지 않는다.

**Alternatives considered**: enum label만 한국어로 번역해도 내부 준비도 개념을 노출한다. READY_LIMITED를 오류 alert로 표시하면 정상 진입 가능한 상태를 장애처럼 보이게 한다.

## 8. Migration과 PostgreSQL lock

**Decision**: 첫 migration에서 프로젝트 관례의 transaction-scoped 2초 `lock_timeout`을 적용해 nullable `user_skipped_at`을 추가한다. Interview status CHECK 교체와 Turn 결과 CHECK는 `NOT VALID`로 생성하고 Django state와 DB state를 `SeparateDatabaseAndState`로 일치시킨다. 다음 `atomic = False` migration에서 두 CHECK를 `VALIDATE CONSTRAINT`한다.

**Rationale**: nullable 열은 backfill·table rewrite가 없지만 ADD COLUMN과 CHECK metadata 변경은 짧은 `ACCESS EXCLUSIVE`가 필요하다. `NOT VALID`는 기존 행 scan을 lock window에서 분리하고 VALIDATE는 읽기·쓰기를 막지 않는 lock으로 수행한다. 기존 migration 0004·0005·0007도 2초 timeout 관례를 사용한다.

**Alternatives considered**: 일반 `RemoveConstraint`+`AddConstraint`는 새 CHECK의 기존 행 scan을 blocking lock에서 수행한다. 새 상태를 CHECK 없이 두면 현재 DB 무결성 관례를 약화한다. 별도 테이블은 migration과 domain을 모두 복잡하게 한다.

**Rollback**: 새 terminal 상태 행이 생긴 후 DB schema reverse는 기존 status CHECK와 양립하지 않는다. 운영 복구는 구 코드 배포 시 새 additive 열·확장 CHECK를 보존하는 forward-compatible rollback을 우선한다. migration 역방향은 새 상태 데이터가 없는 테스트 DB에서만 검증한다.

## 조사 완료

미해결 기술 선택 없음. 신규 dependency·유료 호출·운영 데이터 변경 없음. 구현 시 실제 leaf migration 번호와 `sqlmigrate` SQL을 재확인한다.
