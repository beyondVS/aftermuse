# Backend & API Architecture Rules (백엔드 및 API 특화 규칙)

백엔드 서버, REST API, GraphQL, 데이터베이스 처리 프로젝트에 적용되는 아키텍처 및 개발 규칙입니다.

---

## 🔒 1. API 계약 및 보안 표준

- **일관된 API 응답 규격**: 모든 API 응답은 통일된 JSON 구조(`{ success: boolean, data: T, error?: ErrorDetails }`)를 유지하십시오.
- **인증 및 권한 검증**: 모든 Protected 엔드포인트에는 JWT/Session 검증 미들웨어가 필수적으로 통과되도록 설계하십시오.
- **입력 검증 (Input Validation)**: 요청 body, query, params는 컨트롤러 진입 전 Schema Validator(Zod, Joi, Pydantic 등)를 통해 기계적으로 검증하십시오.
- **SQL Injection 및 XSS 방어**: 데이터베이스 쿼리는 반드시 Parameterized Query 또는 ORM을 사용하고, 사용자 입력을 그대로 쿼리에 바인딩하지 마십시오.

---

## 🗄️ 2. 데이터베이스 및 쿼리 최적화

- **트랜잭션 관리**: 복수의 데이터 변경(CUD) 작업이 이루어지는 경우 트랜잭션을 명시적으로 적용하고 실패 시 Rollback을 보장하십시오.
- **N+1 문제 방지**: 관계형 데이터베이스 조회 시 Join이나 Eager Loading(Include/Preload)을 사용하여 N+1 쿼리 성능 저하를 차단하십시오.
- **마이그레이션 이력 관리**: 데이터베이스 스키마 변경 시 직접 DB를 수정하지 말고 공식 Migration 스크립트를 작성하여 스키마 버전을 관리하십시오.

---

## 📝 3. 로깅, 트레이싱 및 에러 핸들링

- **중앙집중식 에러 핸들링**: 컨트롤러 내부에서 예외를 세어 삼키지 말고 중앙 에러 미들웨어(Error Middleware)로 위임하여 획일적인 에러 응답을 전달하십시오.
- **구조화된 로깅 (Structured Logging)**: 단순 `console.log` 대신 JSON 포맷의 구조화된 로거(Winston, Pino, Structlog 등)를 사용하고, 요청 ID(Trace ID)를 로그에 포함하십시오.
- **민감 정보 마스킹**: 로그에 패스워드, 개인정보, API 토큰 등이 평문으로 출력되지 않도록 필터링 처리하십시오.
