# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다.

형식은 [Keep a Changelog 1.1.0](https://keepachangelog.com/ko/1.1.0/)을 따르며,
버전은 [Semantic Versioning](https://semver.org/lang/ko/)을 기준으로 관리합니다.

## [Unreleased]

### Added

- Python 3.14와 uv 기반의 런타임 및 의존성 관리 환경
- Django 6.1과 Psycopg 3 기반의 최소 Django 프로젝트
- PostgreSQL 18 개발 데이터베이스용 Docker Compose 구성
- 환경변수 검증, PostgreSQL 전용 연결과 Django 6.1 Content Security Policy 설정
- Django Templates, HTMX 2.0.10과 Alpine.js CSP 3.17.1 기반의 공통 웹 UI 토대
- pytest, pytest-django와 Ruff를 사용하는 테스트 및 정적 검사 환경
- 전체 품질 검사를 단일 명령으로 실행하는 `scripts/verify.py`
- Core MVP 기획, 아키텍처, UI/UX 및 구현 계획 문서
- 프로젝트 에이전트 거버넌스, 규칙과 로컬 스킬 구성
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

### Changed

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
