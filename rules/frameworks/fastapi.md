# FastAPI Architecture & Development Rules (FastAPI 특화 개발 규칙)

FastAPI (Python 비동기 백엔드 프레임워크) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. 프로젝트 구조 및 계층 분리 (Project Architecture)

- **`APIRouter` 기반 모듈화**:
  - endpoint 수, domain 경계 또는 소유권이 분리를 필요로 할 때 라우터를 모듈화합니다. 기존 프로젝트의 구조를 우선합니다.
- **책임 기반 구조 (Router - Service - Repository - Schema)**:
  - **Router**: 요청 수신, Response Model 지정, HTTP 상태 코드 제어
  - **Schema (Pydantic)**: Request/Response 데이터 직렬화 및 유효성 검증
  - **Service**: 순수 비즈니스 로직 처리
  - **Repository/DB**: ORM (SQLAlchemy, SQLModel 등) DB 쿼리 실행.
    이 분리는 endpoint·domain·transaction 복잡성이 책임 분리를 요구할 때 적용합니다.

---

## 🧪 2. Pydantic v2 스키마 설계 규약 (Pydantic Standards)

- **Input / Output 스키마 분리**:
  - 생성(`[Model]Create`), 수정(`[Model]Update`), 응답(`[Model]Response`) 스키마를 엄격히 분리하여 불필요한 내부 필드(비밀번호 해시, 시스템 컬럼 등)가 API 응답에 노출되지 않도록 `response_model`을 명시하십시오.
- **Pydantic Field Validation**:
  - 문자열 길이, 숫자 범위, 정규식 등은 Pydantic `Field()` 및 `@field_validator`를 사용하여 라우터에 진입하기 전에 기계적으로 검증하십시오.

---

## ⚡ 3. Dependency Injection & async/await 수칙

- **`Depends()` 기반 의존성 주입**:
  - DB 세션, 인증 유저 정보(`get_current_user`), 외부 서비스 클라이언트는 라우터 매개변수에 `Depends()`를 활용하여 주입하십시오.
- **비동기(`async def`) 대 동기(`def`) 핸들러 구분**:
  - I/O Bound 작업(비동기 DB 쿼리, `httpx` 비동기 HTTP 요청)을 수행하는 라우터는 `async def`로 정의하십시오.
  - blocking/동기 I/O 작업(예: `requests`, 표준 파이썬 파일 I/O)을 포함할 경우 Thread Pool에서 동작하도록 일반 `def` 라우터로 정의하십시오.

---

## 🔒 4. 예외 처리 & API 문서화 (Exception Handling & OpenAPI)

- **`HTTPException` 및 오류 계약**:
  - 구체적인 `status_code`와 프로젝트·클라이언트 계약에 맞는 일관된 오류 응답을 사용합니다.
    FastAPI 기본 처리와 custom exception handler 중 적합한 방식을 선택합니다.
- **OpenAPI / Swagger 정보 내실화**:
  - 외부 소비자가 의존하는 endpoint 계약은 Core 기준에 따라 문서화하고, 자동 생성 OpenAPI에 필요한 `summary`, `description`, `responses`를 실제 계약과 동기화하십시오.
    Docstring과 metadata의 중복 범위는 소비 프로젝트 설정으로 정합니다.
