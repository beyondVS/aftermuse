# 조사: Reflection 결과·수정과 Home 재진입

## 1. Reflection 완료 상태와 배포 안전한 CHECK 교체

**Decision**: 새 컬럼 없이 기존 `status`에 `COMPLETED`를 추가하고 `completed_at`과의
일관성을 CHECK로 강제한다. 현재 두 CHECK는 schema-first의 2단계 migration으로 교체한다.
첫 migration은 `SET LOCAL lock_timeout = '2s'` 뒤 constraint를 짧게 교체해 새 CHECK를
`NOT VALID`로 추가하고, 다음 non-atomic migration이 `VALIDATE CONSTRAINT`한다.

**Rationale**: 기존 모델이 이미 미래 완료를 위해 nullable `completed_at`과 20자 status를
보유하므로 새 컬럼이나 backfill이 필요 없다. DRAFT 기존 행은 새 제약을 이미 만족한다.
프로젝트의 0008/0009 migration이 같은 PostgreSQL 패턴과 SQL 검증 테스트를 사용하므로
일관된 위험 통제가 가능하다.

**Alternatives considered**: Django `RemoveConstraint`/`AddConstraint`만 사용하는 단일
migration은 새 CHECK 추가 시 기존 행 전체 검증을 짧은 exclusive lock과 결합한다. status만
애플리케이션에서 검사하면 DB 직접 쓰기에서 완료 시각 불일치를 허용한다. 새 `final_markdown`
컬럼은 현재 본문이 이미 draft/revised 우선 규칙으로 결정되므로 중복 상태를 만든다.

## 2. 저장·완료 동시성과 오래된 편집본

**Decision**: 기존 `updated_at`을 낙관적 version token으로 사용하고, 수정과 완료 Service가
owner scope의 행을 `select_for_update()`한 뒤 status와 token을 재검사한다. 완료는 Reflection과
Interview를 같은 transaction에서 바꾸며 반복 완료는 기존 결과로 수렴한다.

**Rationale**: 새 version column 없이 명세의 조용한 덮어쓰기 금지를 충족한다. 행 잠금은
같은 Reflection의 수정·완료 경합을 직렬화하고, token 비교는 사용자가 오래된 화면에서
작성한 내용을 최신 수정본 위에 저장하는 것을 감지한다.

**Alternatives considered**: 마지막 쓰기 우선은 데이터 손실을 숨긴다. 매 수정본 version을
별도 table에 저장하는 방식은 이번 범위에서 제외한 버전 이력 UI와 저장 정책을 선행한다.
DB advisory lock이나 캐시는 단일 행 transaction보다 복잡하다.

## 3. Markdown 렌더링과 사용자 입력 안전성

**Decision**: `Markdown~=3.10.3`을 추가하고 기본 parser만 사용한다. 기존
`validate_revised_markdown()`으로 raw HTML, 링크, 이미지 및 금지 입력을 먼저 차단하고,
본문을 HTML escape한 뒤 Markdown을 HTML fragment로 변환한다. 결과만 제한된 renderer
경계에서 safe string으로 전달한다.

**Rationale**: Python-Markdown 3.10.3은 Python 3.14를 공식 분류하며 BSD-3-Clause의
production/stable package다. 공식 문서는 라이브러리 자체가 HTML을 sanitize하지 않는다고
명시하므로 parser만 신뢰하지 않고 기존 입력 검증과 pre-escape를 겹친다. 기본 문법으로
명세가 요구하는 headings, 문단, 목록, 인용을 보존하면서 raw HTML과 외부 action을 만들지
않는다.

**Alternatives considered**: Django `linebreaks`는 목록·소제목·인용 구조를 잃는다. 직접
Markdown parser를 구현하면 검증 표면과 유지보수 책임이 커진다. Python-Markdown 출력만
`mark_safe`하면 공식 보안 경고를 무시하므로 채택하지 않는다. 범용 HTML sanitizer까지
추가하면 현재 금지된 링크·이미지·raw HTML보다 넓은 입력 계약을 불필요하게 연다.

**Sources**:

- [Python-Markdown 3.10.3 on PyPI](https://pypi.org/project/Markdown/)
- [Python-Markdown library security warning](https://python-markdown.github.io/reference/markdown/)

## 4. 서버 렌더링 Interaction 계약

**Decision**: 결과는 GET, 수정은 GET/POST, 완료는 별도 GET 확인/POST로 제공한다. POST
성공은 Django messages와 PRG redirect를 사용하며 validation 400, stale edit 409, 타인 또는
없는 기록 404로 처리한다. HTMX 전용 분기를 추가하지 않고 일반 form이 HTMX 없이도 완전하게
동작하게 한다.

**Rationale**: 완료 confirmation GET의 side effect를 막고 새로고침 재전송을 피한다. 기존
function view와 Form 관례를 유지하며 Day 12에 필요 없는 partial 분기를 줄인다. 소유권 거부를
404로 통일하면 기록 존재 여부를 노출하지 않는다.

**Alternatives considered**: 결과 화면의 inline Alpine state로 저장하면 서버 권한·validation
계약이 분산된다. JSON API나 SPA는 헌법의 서버 렌더링 우선과 맞지 않는다. GET 완료 action은
CSRF와 예측 가능한 HTTP 의미를 위반한다.

## 5. Home 최신 기록 조회

**Decision**: `Reflection.objects.filter(interview__reading__user=user)`를
`updated_at DESC, id DESC`로 정렬해 하나만 가져오고 책까지 `select_related`한다. DRAFT와
COMPLETED를 모두 포함하며 사용자 상태 label을 각각 `작성 중`, `완료`로 표현한다.

**Rationale**: clarification에서 생성·수정·완료 중 마지막 활동을 최근 기준으로 확정했다.
동률에서 PK 역순은 결정론을 제공한다. 기존 Home Reading loop에 reflection prefetch를 섞는
것보다 단일 bounded query가 선택 규칙과 query count를 명확히 한다.

**Alternatives considered**: 최초 생성일 기준은 방금 수정한 오래된 기록으로의 복귀를 막는다.
완료본만 표시하면 초안 재진입 요구를 위반한다. 모든 Reflection을 가져와 Python에서 정렬하면
사용자 기록 수에 비례해 메모리와 query payload가 늘어난다.

## 6. 검증용 책 세트의 재사용과 READY_LIMITED 보장

**Decision**: 기존 승인 Seed의 《1984》와 《Thinking, Fast and Slow》을 각각 fiction READY,
nonfiction READY로 재사용한다. 제한 책은 공식 출판사 ISBN이 확인된
《The Left Hand of Darkness》(`9780143111597`)를 생성하되 Knowledge Claim을 추가하지 않는다.
새 command는 세 Book 준비와 기존 Seed 적용을 orchestrate하고 LIMITED 대상에 Knowledge가
있으면 삭제 대신 실패한다.

**Rationale**: 승인된 8개 Claim과 멱등 Service를 중복하지 않으면서 사용자 합의인
소설 READY 1권·비문학 READY 1권·READY_LIMITED 1권을 정확히 만든다. LIMITED 보장을 위해
기존 데이터를 삭제하면 외부 영향을 확대하므로, 불일치를 명시적으로 보고하는 것이 안전하다.

**Alternatives considered**: 테스트용 가상 책은 실제 Day 13 제품 검증의 현실성을 낮춘다.
기존 seed command가 Book까지 생성하게 바꾸면 “Seed는 Book을 만들지 않는다”는 승인 계약을
깨뜨린다. LIMITED 책의 Knowledge를 자동 삭제하면 복구하기 어려운 데이터 변경이 된다.

**Source**: [Penguin Random House — The Left Hand of Darkness, ISBN 9780143111597](https://www.penguinrandomhouse.com/books/538943/the-left-hand-of-darkness-by-ursula-k-le-guin/)
