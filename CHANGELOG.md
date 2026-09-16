# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/ko/1.1.0/)을 따르며,
버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 기준으로 관리합니다.

## [Unreleased]

### Fixed

- Reflection wire 최상위 추가 키 거부, 검증 오류의 인용·외부값 비노출 및 저장 잠금 후 현재 소유자·관계·상태·답변 snapshot 재검증

- Interview 503 화면에 안전한 실패 사유와 오류 코드·질문 번호를 표시하고 답변 분석 Coverage 검증 위반을 조건별 로그 코드로 구별
- Gemini가 저정보 답변의 미완료 Coverage에서 질문 생략을 제안해 503이 발생하던 경로를 요청별 schema·prompt 제약으로 차단하고, 불필요한 AFC를 비활성화하며 실제 HTTP·저정보 live 검증을 추가
- Interview 자동 질문 준비 form의 submit을 HTMX로 처리하고 실행 중 버튼·추가 요청을 차단하여 일반 navigation과 자동 POST의 경쟁을 방지
- 첫 질문·후속 질문 503에 민감한 원문 없이 예외 chain 타입·발생 위치·HTTP 상태 진단 로그를 추가하고, 후속 질문 prompt의 근거 문자열 계약과 live smoke의 Application 검증을 보완

### Changed

- README를 구현 상태·설정·실행·진단 중심으로 재구성하고 문서 인덱스와 Day 10 구현 계획의 수렴 결과·실제 품질 미검증 범위를 동기화

### Added

- Day 11 질문 건너뛰기(Skip) 모델 제약, `InterviewTurn.user_skipped_at`, `ENDED_NO_REFLECTION` 상태 및 2단계 무중단 PostgreSQL 마이그레이션 (`0008_turn_skip_and_ended_no_reflection.py`, `0009_validate_turn_skip_constraints.py`) 구현 (IMP-096)
- Day 11 `skip_interview_turn` 2단계 원자성 트랜잭션, Budget `user_skipped_count` 계산, `ENDED_NO_REFLECTION` 종결 및 `POST /reflections/interviews/{id}/turns/{seq}/skip/` endpoint 구현 (IMP-096)
- Day 11 `generate_or_get_reflection_draft` 멱등성 보장 오케스트레이션, `POST /reflections/interviews/{id}/reflection/generate/`, HTMX Loading/Error/Retry UI, 최소 임시 결과 화면 (`GET /reflections/{reflection_id}/`) 구현 (IMP-092)
- Day 11 Interview 시작/상세 화면에서 `READY`, `READY_LIMITED`, `준비 수준`, `RAG` 등 내부 용어 제거 및 친화적 비오류 안내 적용, 미확인 책 사실 전제 방지 (IMP-095)

- Day 10 Reflection 기본 모델과 `OneToOneField(Interview)`, DB CHECK 제약 조건, additive migration(2초 lock_timeout) 및 최초 초안 불변·수정본 분리 보존 Service 구현 (IMP-090)
- Day 10 확정 답변 기반 비영속 Reflection 초안 생성 계약(`generate_reflection_draft`), exact substring 인용 및 2자 이상 단어 토큰 접지 검증, 결정론적 canonical Markdown 렌더러 (IMP-091)
- StructuredInterviewProvider의 네 번째 capability인 `generate_reflection`, OpenAI(`reflection_draft`, `store=False`), Gemini(`AFC disable`, `attempts=1`), Ollama(`stream=False`, `format: schema`) transport 어댑터 및 Reflection 전용 오류 격리 매핑 (IMP-091)
- fake/openai/gemini/ollama를 독립 선택하고 자동 fallback을 차단하는 `get_reflection_provider()` 팩토리 (IMP-091)
- Reflection 단위/통합/마이그레이션 테스트 및 OpenAI, Gemini, Ollama opt-in live smoke 테스트
- Day 10 설계의 초안 상한을 22,000자로 조정하고 초안·수정본 금지 형식과 패턴 정규화 및 최대 입력 검증 조건을 명시
- Day 10 Reflection 기본 모델과 답변 기반 초안 생성(IMP-090·IMP-091)의 기능 명세 및 품질 체크리스트 작성
- Day 10 Reflection의 저장 관계·구조화 생성 계약·Provider 재사용·검증 절차에 대한 구현 계획과 설계 산출물 작성
- Day 10 Reflection의 사용자 스토리별 구현·회귀 검증 작업과 의존성 및 병렬 실행 조건 정의

- Home 화면을 실제 사용자 Reading 상태(읽고 싶음, 읽는 중, 완독) 및 진행 중 Interview와 연결하는 최소 Navigation Hub, 상태별 카드와 영역별 빈 상태 구현
- 진행 중인 Interview로 질문·답변 유실 및 중복 생성 없이 현재 단계로 복귀하고 이전 확정 질문·답변을 확인하는 재진입(Resume) 흐름 및 소유자 격리 검증

- 네 Core Coverage 축 완료 후 Soft Stop 선택과 8문항 일반 상한·최대 10문항 예외 진행을 연결하고, 실제 답변 수와 최신 후보 축을 재검증하며 종료 시 답변을 보존한 독서노트 준비 안내를 제공

- Gemini API와 로컬 Ollama의 Interview 세 작업 Adapter, 명시적 Provider·모델·timeout 설정 및 opt-in live smoke test

- Python 3.14와 uv 기반의 런타임 및 의존성 관리 환경
- Django 6.1과 Psycopg 3 기반의 최소 Django 프로젝트
- PostgreSQL 18 개발 데이터베이스용 Docker Compose 구성
- 환경변수 검증, PostgreSQL 전용 연결과 Django 6.1 Content Security Policy 설정
- Django Templates, HTMX 2.0.10과 Alpine.js CSP 3.17.1 기반의 공통 웹 UI 토대
- pytest, pytest-django와 Ruff를 사용하는 테스트 및 정적 검사 환경
- 전체 품질 검사를 단일 명령으로 실행하는 `scripts/verify.py`
- Core MVP 기획, 아키텍처, UI/UX 및 구현 계획 문서
- 프로젝트 에이전트 거버넌스, 규칙과 로컬 스킬 구성
- 기존 context 문서와 skill 구성을 보존하는 GitNexus 프로젝트 분석 설정
- Custom User 모델과 세션 기반 회원가입, 로그인, 로그아웃 흐름
- ISBN13 기반 Book 모델과 PostgreSQL unique/CHECK 제약, 초기 migration 및 저장·조회 테스트
- 주입 가능한 transport와 정상·실패·timeout 구분을 지원하는 알라딘 Metadata Adapter
- 실제 credential을 포함하지 않는 `ALADIN_TTB_KEY` 환경 예시
- Provider 중립 계약으로 성공·빈 결과·안전한 오류 상태를 구분하는 도서 검색 Service
- 로그인 사용자용 도서 검색 화면과 HTMX 기반 Loading·Empty·Error 상태
- Kakao 도서 검색 Adapter, Provider 중립 계약과 legacy Aladin 호환 re-export
- 검색 결과 session 후보 ID 기반의 CSRF 보호 Book 선택·등록 및 중복 방지 흐름
- Book 저장 실패 후 같은 검색 후보를 안전하게 다시 선택할 수 있는 복구 UI
- Kakao 실제 credential을 명시적으로 사용하는 `live` smoke test
- 사용자·Book별 Reading 모델, 상태/완독일 CHECK와 활성 Reading 조건부 unique 제약
- 명시적 Reading 시작·재독·상태/완독일 변경 Service와 소유자 전용 상세 화면
- Book 선택 성공 시 Reading 진입으로 연결하는 일반 redirect와 HTMX `HX-Redirect`
- Book별 Claim을 저장·조회하는 `knowledge` 도메인과 PostgreSQL 제약 migration
- 승인된 2권·8개 Claim의 멱등 수동 Seed command와 전체 rollback 검증
- Claim 존재 여부에서 파생하는 `READY` / `READY_LIMITED` Book 준비 상태
- 완독 Reading의 Book 확인과 명시적 POST 기반 Interview 시작, 진행 상태 재진입 흐름
- Reading당 하나의 Interview와 순서가 보장되는 InterviewTurn 영속 모델 및 migration
- 시작된 Interview의 Reading 완독 상태·완독일 변경 잠금과 `READY_LIMITED` 기억 중심 안내
- `READY`/`READY_LIMITED` 신뢰 경계를 지키는 첫 질문 Context, fake·OpenAI Provider와 strict structured output Adapter
- 첫 질문의 멱등 저장, HTMX Loading·Question·Error 전환과 명시적 재시도
- 공백을 거부하는 2,000자 답변 form, 최초 답변의 불변·멱등 저장과 Saved 상태
- 첫 질문·답변 Web 계약 및 network·credential 없는 Provider 회귀 테스트
- 생성 질문의 금지 지시·상태 변경·허용되지 않은 참조를 저장 전에 거부하는 안전성 검사
- HTMX 정책 충돌을 내부 정보 비노출 안내와 Interview 영역 전체 교체로 복구하는 fragment
- 확정 답변의 의미·low-information 여부와 원문 근거 기반 Core Coverage 상승 후보를 반환하는
  비영속 Answer Analysis 계약, fake·OpenAI Adapter 및 Application 검증 경계
- 답변 분석과 Core Coverage를 반영한 적응형 다음 질문, 여러 Turn의 답변 저장 및 검증된
  질문 생략 기록과 실패 후 답변 보존·재시도 흐름

### Changed

- Interview LLM의 공통 structured 요청·decode를 Provider 중립 모듈로 통합하고 OpenAI·Gemini·Ollama transport를 각각 분리

- 후속 질문을 LLM의 검증된 원문으로 저장하고, 예약된 답변 마무리 문구 없이 Coverage와 추가 탐색 근거로 질문 생략을 검증

- 남은 MVP 구현 계획의 Bundle을 사용자 결과와 상태·LLM·트랜잭션·신뢰·복구·UI 검증 경계에 맞게 재구성
- 기본 도서 Metadata Provider를 Aladin에서 Kakao 도서 검색 API로 전환
- 기본 pytest 실행에서 실제 외부 연결이 필요한 `live` marker 테스트를 제외하고, 명시적인
  `-m live` 실행에서만 선택하도록 테스트 정책을 강화
- OS 및 IDE가 생성하는 파일과 민감하거나 사용자별인 JetBrains 설정은 Git에서 제외하고, `codeStyles`와 `runConfigurations` 같은 공유 가능한 IDE 설정은 추적하도록 `.gitignore` 정책을 정리
- `django-environ`으로 저장소 루트의 `.env`를 자동으로 읽고 OS 환경변수를 우선하도록
  Django 설정 로딩을 변경
- 내부 모델의 기본 PK 정책을 `BigAutoField`로 확정하고 UUIDv7은 필요한 모델의
  별도 공개 식별자로 검토하도록 제한
- Ruff 검사 범위를 애플리케이션 코드, 테스트와 프로젝트 스크립트로 제한
- Reading 상태 변경의 HTMX 오류 panel 교체와 결과 focus, 활성 Reading 충돌 복구 안내를
  일반 Form POST와 동일한 의미 계약으로 강화
- 첫 답변 validation·conflict·DB 오류와 첫 질문 생성 오류가 HTMX 4xx/5xx에서도 Interview
  영역을 교체하고 입력 보존·오류 focus 계약을 유지하도록 강화
- 첫 질문의 소유권·관계·상태 검증과 기존 Turn 재사용 이후에만 Provider를 생성하도록 호출
  순서를 변경해 저장된 질문과 정책 충돌 응답이 Provider 설정에 의존하지 않도록 개선
- Interview별 Core Coverage JSONB 상태와 단방향·원자적 patch Service를 추가하고, 소유권·답변·진행 상태 경계를 검증
