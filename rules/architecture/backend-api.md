# Backend & API Architecture Rules (백엔드 및 API 특화 규칙)

백엔드 서버, REST API, GraphQL, 데이터베이스 처리 프로젝트에 적용되는 아키텍처 및 개발 규칙입니다.

---

## 🔒 1. API 계약 및 보안 표준

- **API 응답 및 오류 계약**: 기존 프로젝트·클라이언트의 응답 형식과 content type을 보존합니다.
  새 계약은 일관된 성공·오류 형식을 문서화하되 고정 JSON envelope를 강제하지 않습니다.
- **인증 및 권한 검증**: 모든 Protected 엔드포인트에는 JWT/Session 검증 미들웨어가 필수적으로 통과되도록 설계하십시오.
- **입력 검증 (Input Validation)**: 요청 body, query, params는 컨트롤러 진입 전 Schema Validator(Zod, Joi, Pydantic 등)를 통해 기계적으로 검증하십시오.
- **SQL Injection 및 XSS 방어**:
  - DB 쿼리는 parameterized query 또는 ORM으로 구성하고 문자열 결합으로 사용자 입력을 쿼리에 넣지 마십시오.
  - 출력은 HTML·URL·JavaScript 등 렌더링 문맥에 맞게 encoding·sanitization하여 XSS를 별도로 방어합니다.

---

## 🗄️ 2. 데이터베이스 및 쿼리 최적화

- **트랜잭션 관리**: 복수의 데이터 변경(CUD) 작업이 이루어지는 경우 트랜잭션을 명시적으로 적용하고 실패 시 Rollback을 보장하십시오.
- **N+1 문제 대응**: 반복되는 관계 접근과 관찰·측정된 추가 query가 함께 확인될 때 Join, Eager Loading 또는 조회 구조 개선을 적용합니다.
- **마이그레이션 이력 관리**: 데이터베이스 스키마 변경 시 직접 DB를 수정하지 말고 공식 Migration 스크립트를 작성하여 스키마 버전을 관리하십시오.

---

## 📝 3. 로깅, 트레이싱 및 에러 핸들링

- **에러 처리**: 예외를 숨기지 말고 프로젝트·플랫폼이 제공하는 일관된 처리 방식으로 오류 계약을 지킵니다.
  중앙 middleware, framework-native handler 등 구현 방식은 프로젝트에 맞게 선택합니다.
- **로깅 및 추적**: 운영 진단에 필요한 구조화된 필드와 요청 상관관계 정보를 프로젝트 관례에 맞는 logger 또는 observability 도구로 남깁니다.
  JSON logger나 특정 middleware를 일률적으로 강제하지 않습니다.
- **민감 정보 마스킹**: 로그에 패스워드, 개인정보, API 토큰 등이 평문으로 출력되지 않도록 필터링 처리하십시오.
