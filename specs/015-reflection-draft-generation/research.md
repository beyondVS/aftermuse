# 조사: Reflection Draft 생성

## 1. 저장 표현과 관계

**Decision**: Interview OneToOne의 별도 Reflection, 최초 Markdown·순서 있는 JSON section과 선택적 수정본을 보존한다. Reading·Book·user는 Interview 관계에서 도출한다.

**Rationale**: PRD §9 및 Architecture §10.3–10.4의 가변 구조·원본/수정본 분리를 지키면서 중복 FK 불일치를 줄인다. 기존 models에는 아직 Reflection이 없으며 Interview는 Reading OneToOne이다.

**Alternatives considered**: Interview에 본문 추가는 과정/결과 구분을 깨뜨린다. section 전용 테이블·중복 소유자 FK는 이번 조회와 저장에 불필요하다.

**Source**: [PRD](../../docs/AfterMuse_MVP_PRD_v4.md), [Architecture](../../docs/AfterMuse_Architecture_Decisions_v4.md), [현재 모델](../../src/reflections/models.py), [Django fields](https://docs.djangoproject.com/en/5.1/ref/models/fields/). 공식 문서의 기본 관계 표현만 참고하며 실제 동작은 프로젝트 Django 6.1 ORM 테스트로 확인한다.

## 2. 공통 Provider 재사용

**Decision**: 기존 `StructuredInterviewProvider._request(task, instructions, payload, schema)`를 재사용하고 reflection prompt·schema·decode만 새 helper 모듈에 둔다. transport의 analysis/else 오류 분기와 OpenAI format name에 reflection을 명시적으로 추가한다.

**Rationale**: read-only 조사 agent가 세 transport와 공통 seam을 확인했다. 현재 분기는 새 task를 질문 오류로 오분류하며 OpenAI names에는 새 task가 없다. 기존 store=False·tools 없음·한 번 요청·Gemini AFC disable·Ollama loopback 정책을 유지할 수 있다.

**Alternatives considered**: transport 복제, LiteLLM 및 Agent framework 도입은 새 운영 표면과 의존성을 늘린다. 기존 클래스명 변경도 불필요하다.

**Source**: [공통 Provider](../../src/integrations/llm/interview.py), [factory](../../src/integrations/llm/factory.py), [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs), [Gemini](https://ai.google.dev/gemini-api/docs/structured-output), [Ollama](https://docs.ollama.com/capabilities/structured-outputs).

## 3. 생성 근거와 결과 검증

**Decision**: 확정 질문·답변의 순서 있는 snapshot만 입력으로 전달한다. 문단별 text와 sequence·quote evidence를 포함하는 section을 반환받아 재검증하고 Markdown은 서버가 조립한다. schema는 필수 키·타입·array items 중심이며 Application에서 길이·개수·참조·금지 패턴을 검증한다.

**Rationale**: 별도 Markdown을 함께 생성하면 이중 표현이 불일치할 수 있다. 공식 structured output 문서는 schema subset과 출력 오류 가능성을 설명한다. 정확한 인용은 근거 존재를 검증하지만 의미 왜곡을 증명하지 않으므로 대표 자료 대조를 별도로 둔다.

**Alternatives considered**: 자유 Markdown은 근거·구조 검사에 취약하다. section 단위 근거보다 문단 단위가 무근거 서술을 좁혀 확인하기 좋다. 추가 LLM 의미 판정은 비용과 불확실성을 늘린다.

**Bounds**: 최대 10 section·각 10문단, title 120자·문단 2,000자·quote 500자·초안 전체 22,000자·수정본 20,000자. 초안 상한은 최대 답변 원문 20,000자와 제목·Markdown 구분자 공간을 확보한다. 외부 Provider 공식 상한이 아닌 내부 안전 정책이며 최소 분량을 강제하지 않는다.

## 4. 비영속 생성과 짧은 저장 transaction

**Decision**: 생성 결과는 DB를 변경하지 않는다. 저장은 owner·REFLECTION_READY·관계·snapshot·결과를 재검증하고 짧은 atomic에서 최초 기록만 삽입한다. 수정본은 별도 owner-scoped Service로 저장한다.

**Rationale**: 기존 Interview helper는 IN_PROGRESS만 허용하여 그대로 재사용할 수 없다. Provider 호출 중 lock을 유지하지 않으며 같은 Interview의 중복은 OneToOne과 conflict로 막는다. UI Retry·single-flight·완료 전이는 Day 11/12가 책임진다.

**Alternatives considered**: 생성과 저장을 하나의 긴 transaction으로 묶거나 get_or_create로 기존 초안을 무조건 덮어쓰는 방식은 원문 보호와 실패 분리를 약화한다.

## 5. Migration과 복구

**Decision**: 기존 0006 다음 additive CreateModel, backfill 없음. 실제 SQL에서 FK·lock을 확인하고 기존 2초 transaction-scoped timeout 관례를 참고한다. 기존 테이블의 컬럼을 변경하지 않는다.

**Rationale**: 새 빈 테이블이어도 FK는 참조 테이블에 잠금을 요구할 수 있다. migration 전후 기존 기록 및 역방향은 테스트 DB에서 검증한다. 실제 Reflection이 생긴 이후 운영 rollback에서는 테이블 삭제보다 구 코드 복귀·테이블 보존을 우선한다.

**Alternatives considered**: 기존 테이블 재작성·데이터 이관이나 새 빈 테이블에 대한 일괄 concurrent index 배포는 현재 필요하지 않다.

**Source**: [PostgreSQL 18 CREATE TABLE](https://www.postgresql.org/docs/18/sql-createtable.html), [기존 migration 검사](../../tests/reflections/test_migrations.py). SQL 생성 및 잠금 검수는 구현 단계에서 수행한다.

## 조사 완료

미해결 기술 선택 없음. 신규 패키지·모델 다운로드·제품 정책 변경 없음. 조사에서 실제 유료 호출이나 운영 migration은 실행하지 않았다.
