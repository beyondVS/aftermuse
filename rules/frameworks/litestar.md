# Litestar Architecture & Development Rules (Litestar 특화 개발 규칙)

Litestar (Python 초고속 ASGI 비동기 프레임워크) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. Controller 및 라우팅 구조 (Controller Architecture)

- **라우팅 구조**: 엔드포인트 그룹과 프로젝트 아키텍처가 요구할 때 `Controller` 클래스로 라우트를 그룹화하고, 그렇지 않으면 기존 컨벤션을 유지하십시오.
- **라우터 훅 및 미들웨어 계층화**:
  - 인증·로깅·예외 처리가 여러 엔드포인트에 공통일 때 적절한 앱/컨트롤러 계층에 중앙 등록하십시오.

---

## 🔀 2. DTO (Data Transfer Object) 패턴 규약

- **Litestar Native DTO 활용**:
  - 별도 직렬화 경계가 필요할 때 `DataclassDTO`, `PydanticDTO` 또는 프로젝트가 채택한 DTO를 사용하십시오.
- **DTO 필드 제어 (`dto_data`)**:
  - `dto_data`를 활용하여 생성/수정 시 읽기 전용 필드(`id`, `created_at`)가 입력으로 주입되는 것을 차단하고, 응답 시 민감한 필드가 자동 마스킹되도록 지정하십시오.

---

## ⚡ 3. Dependency Injection & Plugin 생태계

- **Litestar Dependency Injection (`Provide`)**:
  - DI와 테스트 override가 필요한 서비스/리포지토리에 `Provide()` 또는 프로젝트의 호환 DI 방식을 적용하십시오.
- **Litestar 플러그인 활용 (SQLAlchemy / Advanced ALchemy)**:
  - SQLAlchemy 세션 생명주기·트랜잭션을 일관되게 관리해야 할 때 `SQLAlchemyPlugin`을 적용하십시오.

---

## 🔒 4. 예외 처리 & 응답 표준화

- **Litestar Native Exceptions**:
  - 일관된 HTTP 상태·JSON 오류 계약이 필요할 때 Litestar 내장 예외 또는 프로젝트 표준 예외를 사용하십시오.
