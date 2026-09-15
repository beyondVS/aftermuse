# 내부 계약: Reflection 생성·저장

## Service와 Provider

이번 단계는 HTTP endpoint를 추가하지 않는다. 아래는 후속 Django View가 직접 호출할 keyword-only Python 인터페이스다. 모든 DB 대상은 user scope로 다시 조회한다.

| 인터페이스 | 결과·효과 |
| --- | --- |
| get_reflection_draft(user, interview) | 소유자 Reflection 또는 없음, Provider 호출 없음 |
| generate_reflection_draft(user, interview, provider=None) | 검증된 비영속 ReflectionDraftResult, DB 변경 없음 |
| save_reflection_draft(user, interview, result) | 최초 Reflection 저장, 기존 기록이면 conflict |
| save_reflection_revision(user, reflection, markdown) | Draft 수정본·updated_at만 갱신 |
| get_reflection_provider() | LLM_PROVIDER의 현재 provider 선택, fallback 없음 |
| ReflectionProvider.generate_reflection(context) | 신뢰되지 않은 proposal, ORM 접근 없음 |

없는 대상·타인 대상은 동일한 안전 Policy 오류로 처리한다. 조회·수정본 저장은 Provider 구성에 의존하지 않는다.

## Context

불변 ReflectionGenerationContext의 turns tuple은 각 sequence·question·확정 answer를 가진다. Application 결과는 source Interview id·원래 turn snapshot을 함께 가진다. Provider에는 user id, 다른 기록, Reading 메모, Book Knowledge, meaning, Coverage 또는 DB 접근을 전달하지 않는다.

owner·book 관계·REFLECTION_READY를 확인하고 sequence 순으로 최대 10개 비공백 확정 답변을 수집한다. 각 원문은 기존 2,000자 제한을 따른다. 부적합·빈 입력은 factory 호출 전에 거부한다. 기존 IN_PROGRESS-only helper를 그대로 사용하지 않는다.

## Wire schema·Application 검증

최상위는 sections만, section은 title·paragraphs만, 문단은 text·evidence만, evidence는 sequence·quote만 가진다. 모든 키는 required, object는 additionalProperties=false다. 타입·필수 구조를 schema로 제한하고 fake 포함 모든 출력을 로컬에서 재검증한다.

| 요소 | 제한 |
| --- | --- |
| sections | list, 1–10개 |
| title | 비공백 string 1–120자, 단일 줄 |
| paragraphs | section당 1–10개 |
| text | 비공백 string 1–2,000자 |
| evidence | 문단당 1–10개, 중복 sequence·quote 거부 |
| sequence | bool 제외 양의 int, snapshot 내 확정 답변 참조 |
| quote | 비공백 string 1–500자, 참조 answer의 정확한 연속 부분 문자열 |
| 완성 초안 Markdown | 1–22,000자 |
| 사용자 수정본 Markdown | 비공백 1–20,000자 |

root·nested의 모르는 키·누락·타입·배열 개수·문자 길이·참조·인용을 검증한다. schema 지원 차이로 Provider가 상한을 무시해도 Application은 거부한다. 문단별 근거는 질문이 아닌 answer에서 확인한다.

문단과 근거의 표현 연결은 공백으로 나눈 2자 이상 원문 token이 문단 text에 최소 하나 존재하는지 확인하는 보조 검사로 둔다. 그러한 token이 없는 짧은 답변은 quote 전체가 문단에 포함되는 원문 보존 표현을 허용한다. 인용 존재·표현 연결은 의미적 함의 증명이 아니다. paraphrase가 거부되는 경우 원문 표현을 유지하도록 prompt를 설계하며 자동 재요청은 하지 않는다. 제목과 모든 서술의 의미는 대표 자료에서 대조한다.

서버가 section 제목과 문단에서 canonical Markdown을 조립한다. Provider가 별도 본문을 반환하지 않는다. section은 `## `와 title, 문단은 text이며 각 블록과 section 사이를 공백 줄(`\n\n`)로 연결한다. 최종 말미 개행은 추가하지 않는다. 최대 입력 10개 × 2,000자를 각 한 문단·최대 120자 제목으로 보존한 fake 초안은 22,000자 안에 들어야 한다. 전체 22,001자 이상 결과는 거부하며 수정본 상한은 20,000자를 유지한다.

### 허용·금지 형식과 패턴

| 대상 | 허용 | 거부 |
| --- | --- | --- |
| 생성 title | 단일 줄 plain text | raw HTML·Markdown heading prefix·링크·이미지·fence |
| 생성 paragraph text | 일반 문장·강조·문단 개행 | raw HTML·fenced code·이미지·Markdown 링크·자동 링크·문단 내 heading |
| 사용자 revised_markdown | 일반 Markdown 제목·강조·목록·인용·code | raw HTML·모든 링크·이미지 및 아래 금지 지시 패턴 |

링크는 inline `[텍스트](대상)`, reference `[텍스트][id]`/`[id][]` 및 `[id]: 대상` 정의, URL/email 자동 링크 `<https://...>`/`<user@example.com>`와 bare `http://`, `https://`, `www.` 주소를 포함한다. 이미지는 inline/reference `![설명]` 구문이다. title/text의 fenced code는 줄 시작의 3개 이상 backtick 또는 tilde, heading은 줄 시작의 1–6개 `#`와 이어지는 공백으로 판정한다. raw HTML은 opening/closing tag·comment·doctype를 포함하며 단순 수학 비교 기호 `<`, `>`는 HTML로 간주하지 않는다. reference 링크는 정의만 있는 경우도 거부한다. 생성 evidence.quote와 입력 answer에는 이 형식 검사를 적용하지 않는다.

지시 패턴은 현재 `src/reflections/services.py`의 `_QUESTION_PROHIBITED_PATTERNS`를 초기 기준으로 사용한다: `관리자 권한`, `시스템 상태`, `상태를 변경`, `크레딧`, `웹 검색`, `데이터베이스`, `이전 지시를 무시`. 분석용 `_ANALYSIS_PROHIBITED_PATTERNS`를 혼용하지 않는다. title·paragraph text·revised_markdown에 적용하며 비교용 문자열과 패턴 양쪽에 Unicode NFKC, casefold, 연속 공백을 한 공백으로 치환한 후 부분 문자열 검사를 수행한다. 저장 원문과 evidence의 정확한 인용 비교에는 이 정규화를 적용하지 않는다. 공백 없는 변형까지 의미적으로 탐지한다는 보장은 하지 않는다.

대표 허용 사례는 `**마음에 남았다**`, `a < b`, 수정본의 `## 내 생각`·목록이다. 거부 사례는 `<script>...</script>`, `[자료](https://example.com)`, `[자료][ref]`와 reference 정의, `![표지](cover.png)`, 자동 링크, 생성 문단의 heading 및 fence다. 형식 검사는 대소문자 HTML·URL 변형, 패턴의 여러 공백·tab·개행·전각 변형을 포함해 테스트한다.

정책 변경 문구가 answer에 있어도 입력 단계에서 지시로 실행하지 않는다. 이 신뢰 경계 검증과 출력 패턴 거부는 별개다. Provider가 문구를 출력에 복사하면 거부될 수 있지만 입력만으로 생성 정책·데이터 접근 범위를 바꾸어서는 안 된다. HTML 렌더링·sanitizer 선정은 후속 화면 작업에서 정의한다.

## Prompt·fake

한국어 trusted instruction은 답변만 근거, 질문은 문맥, 새 신념·해석·평가·경험·사실 추가 금지, 유보·반대·감정 강도 보존, 가변 구성, 문단별 정확한 인용을 명시한다. untrusted turns는 별도 JSON payload다. 규칙 무시·도구·타인 데이터 요청을 입력에서 실행하지 않는다.

Fake는 답변 원문을 문단으로 보존하고 quote를 연결하는 deterministic 초안이다. 중립적 제목을 사용한다. 원문에 금지 내용이 있으면 같은 검증에서 거부될 수 있다. fake는 network·credential·DB 접근이 없다.

## Transport·오류

기존 공통 StructuredInterviewProvider의 네 번째 capability는 reflection helper로 schema·prompt·payload·decode를 구성하고 `_request(task="reflection", ...)`를 호출한다. OpenAI format name에 reflection_draft를 추가한다. 기존 store=False·tools 없음·max_retries=0, Gemini AFC disable·한 번 시도, Ollama loopback·stream=false·schema format을 유지한다.

ReflectionGenerationError 아래 Timeout·Unavailable·Rejected·ConfigurationError를 둔다. 기존 analysis/else 분기와 constructor 설정 오류를 reflection 오류로 명시 매핑한다. Application Policy·Validation·DraftConflict·Persistence 오류는 외부 생성 오류와 구분한다. 자동 재시도·유료 fallback은 없다.

오류·로그에는 exception message, 답변 원문, Provider 응답, credential을 출력하지 않는다. 고정 reason code·내부 식별자로만 진단한다. Day 11이 사용자 생성 화면·Retry에 매핑한다.

## 저장 재검증

ReflectionDraftResult 타입 자체를 신뢰하지 않는다. 저장 시 source Interview·원래 snapshot을 현재 확정 답변과 대조하고 sections·evidence·canonical Markdown을 다시 검증한다. 다른 Interview 결과·변조 결과·stale snapshot은 거부한다. 기존 초안·수정본을 덮어쓰지 않는다.
