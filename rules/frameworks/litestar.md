# Litestar Architecture & Development Rules (Litestar 특화 개발 규칙)

Litestar (Python 초고속 ASGI 비동기 프레임워크) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. Controller 및 라우팅 구조 (Controller Architecture)

- **`Controller` 클래스 기반 라우팅**:
  - 엔드포인트를 단일 함수로 나열하기보다 관련 도메인별로 `Controller` 클래스(`class UserController(Controller): path = "/users"`)로 그룹화하여 관리하십시오.
- **라우터 훅 및 미들웨어 계층화**:
  - 인증, 요청 로깅, Exception Handler 훅은 컨트롤러 레벨 또는 최상위 Litestar 앱 레벨에서 중앙 집중식으로 등록하십시오.

---

## 🔀 2. DTO (Data Transfer Object) 패턴 규약

- **Litestar Native DTO 활용**:
  - 데이터 요청과 응답 구조를 변환할 때 Litestar의 `DataclassDTO` 또는 `PydanticDTO`를 활용하십시오.
- **DTO 필드 제어 (`dto_data`)**:
  - `dto_data`를 활용하여 생성/수정 시 읽기 전용 필드(`id`, `created_at`)가 입력으로 주입되는 것을 차단하고, 응답 시 민감한 필드가 자동 마스킹되도록 지정하십시오.

---

## ⚡ 3. Dependency Injection & Plugin 생태계

- **Litestar Dependency Injection (`Provide`)**:
  - 컨트롤러 매개변수로 주입되는 서비스/리포지토리는 `Provide()` 팩토리 함수를 통해 선언하고, 테스트 시 쉽게 Mocking/Override 가능하도록 설계하십시오.
- **Litestar 플러그인 활용 (SQLAlchemy / Advanced ALchemy)**:
  - DB 연동 시 `SQLAlchemyPlugin`을 적용하여 세션 생명주기 관리 및 트랜잭션 수명을 플러그인에 위임하십시오.

---

## 🔒 4. 예외 처리 & 응답 표준화

- **Litestar Native Exceptions**:
  - `NotFoundException`, `NotAuthorizedException`, `ValidationException` 등 Litestar 내장 예외 클래스를 활용하여 일관된 HTTP 상태 코드와 JSON 응답을 반환하십시오.
