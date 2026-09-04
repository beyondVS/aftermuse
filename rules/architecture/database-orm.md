# Database & ORM General Rules (범용 DB & ORM 설계 및 마이그레이션 규칙)

프레임워크나 ORM 종류(Prisma, SQLAlchemy, TypeORM, Django ORM 등)에 구애받지 않고 적용되는 범용 데이터베이스 설계, 인덱싱 및 마이그레이션 안전 규칙입니다.

---

## ⚠️ 1. 파괴적 마이그레이션 절차 (Non-Destructive Schema Migration)

- **혼재 버전 온라인 배포의 Zero Downtime 원칙**:
  - 구·신 버전 애플리케이션이 함께 실행되는 운영 배포에서는 컬럼 삭제·이름 변경을 단일 마이그레이션으로 즉시 적용하지 마십시오.
- **필요 시 2단계 Deprecation 절차**:
  - **1단계 (Add/Deprecate)**: 신규 컬럼 추가 또는 Nullable 처리 후 코드 배포 및 데이터 이관 수행
  - **2단계 (Cleanup)**: 구버전 코드 및 데이터 참조가 완전히 제거된 후 별도의 마이그레이션으로 구 컬럼 DROP
  - 혼재 버전 온라인 배포가 아닌 경우에도 영향 범위와 rollback 가능성을 검토합니다.

---

## 🔍 2. 인덱싱(Indexing) 및 쿼리 성능 원칙

- **외래키(FK) 및 검색 필드 인덱스 판단**:
  - 관계형 DB의 외래키(FK) 컬럼, 자주 조인되는 필드 및 `WHERE` 조건절에 빈번히 포함되는 검색 필드는 실제 쿼리 패턴, 카디널리티, 데이터 규모와 쓰기 비용을 근거로 인덱스 필요성을 판단하십시오.
- **복합 인덱스(Composite Index) 순서 지침**:
  - 복합 인덱스의 선행 컬럼은 카디널리티만으로 정하지 말고, 대표 쿼리의 필터·정렬·조인 순서와 실행 계획을 기준으로 결정하십시오.
- **N+1 쿼리 대응**:
  - 반복적으로 접근하는 관계가 있으며 query count, profiler 또는 실행 동작에서 추가 쿼리가 관찰될 때 적합한 eager loading 또는 조회 구조를 선택합니다.
    사용하지 않는 관계의 일괄 eager loading은 피하십시오.

---

## 🔒 3. 데이터 무결성 및 트랜잭션 수칙

- **DB 수준의 제약 조건 (Constraints)**:
  - DB가 invariant를 신뢰성 있게 표현할 수 있으면 `NOT NULL`, `UNIQUE`, `CHECK`, `FOREIGN KEY` 등 DB 제약 조건을 사용합니다.
    DB가 표현할 수 없는 정책은 애플리케이션 검증과 함께 관리합니다.
- **트랜잭션 바운더리 최소화**:
  - `@transaction` 블록 또는 DB 트랜잭션 범위 내에서 외부 API 호출, 파일 I/O 등 느린 작업을 수행하지 마십시오. DB 커넥션 풀 고갈을 초래합니다.
- **Rollback 및 복구 검증**:
  - 가역적 마이그레이션은 rollback을 테스트합니다. 비가역적 마이그레이션은 비가역성을 문서화하고 backup·recovery 또는 안전한 forward plan을 검증합니다.
