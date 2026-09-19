# Django Architecture & Development Rules (Django 특화 개발 규칙)

Django 및 Django REST Framework (DRF) / Django Ninja 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. 프로젝트 구조 및 도메인 분리 (Project Structure)

- **도메인 단위 앱 분리 (Modular Apps)**: 
  도메인 경계, 소유권 또는 독립 배포·권한 정책이 명확할 때 앱을 분리합니다. 기존 프로젝트의 앱 구조가 이를 이미 표현한다면 불필요한 재구성을 하지 마십시오.
- **Service & Selector 패턴 (조건부 계층 분리)**:
  - Service·Selector/Query 등 추가 레이어는 여러 View/API에서 재사용되는 도메인 연산, 명확한 트랜잭션 경계, 복잡한 CUD 오케스트레이션, 여러 모델이나 외부 시스템 조합, 또는 책임 혼재로 가독성·유지보수성이 저하될 때나 프로젝트가 이미 해당 아키텍처를 일관되게 채택한 경우에 도입합니다.
  - 단순한 CRUD나 작은 로직에서는 Django의 프레임워크 네이티브 구조(ORM, QuerySet, View/Serializer)와 기존 프로젝트 관례만으로 충분하다면 새로운 Service/Selector 계층을 강제하지 마십시오.
  - **Model**: 데이터 구조와 유효성 검증뿐만 아니라, 해당 모델 자체에 자연스럽게 속하는 도메인 동작(Domain Behavior)을 둘 수 있습니다.
  - **View / API**: 요청 수신, 입력 검증, 응답 반환을 담당하며 단순한 경우 모델/쿼리셋 API를 직접 조합할 수 있습니다. 위 조건에 따라 별도 계층이 필요한 경우 Service/Selector로 위임하십시오.

---

## 🗄️ 2. ORM 및 쿼리 최적화 (ORM & DB Performance)

- **N+1 쿼리 방지**:
  - 반복적으로 실제 접근하는 관계가 있고 query count, 실행 계획 또는 실행 동작이 추가 쿼리를 보일 때 이를 해결합니다.
    관계와 접근 방식에 맞춰 `select_related()`, `prefetch_related()` 또는 다른 방법을 선택하고, 사용하지 않는 관계를 일괄 eager loading하지 마십시오.
- **다량 데이터 처리 및 ORM 최적화**:
  - 다수의 객체 생성/수정 시 반복문 내부 `save()` 호출과 `bulk_create()` / `bulk_update()` 사용 간의 **코드의 간결함, 성능상 이점, 그리고 모델 시그널(`post_save` 등) 동작 유무**를 종합적으로 고려하여 가장 적절한 방식을 선택하십시오.
- **트랜잭션 세분화**:
  - 여러 CUD 작업이 함께 성공·실패해야 하는 일관성 경계에 `transaction.atomic`을 적용합니다.
- **`only()` 및 `defer()` 활용**: 측정 가능한 payload 또는 query 이점이 있을 때만 사용하고, 지연 필드 접근이 추가 query나 오류를 일으키지 않는지 검증하십시오.

---

## 🔒 3. API 및 입력 검증 (DRF / Ninja Standards)

- **Serializer / Schema 검증**:
  - 클라이언트 입력값 검증은 반드시 Serializer (DRF) 또는 Pydantic Schema (Django Ninja)를 거치도록 하십시오.
- **API 응답 및 에러 규격**:
  - 기존 클라이언트 계약·content type을 보존합니다.
    새 API에 오류 계약이 필요하면 일관된 오류 형식을 선택해 문서화하고, framework-native 처리 또는 custom handler 중 프로젝트에 맞는 방식을 사용합니다.
- **Pagination 적용 규약**:
  - 목록 조회 API는 결과 집합이 비한정적이거나 지속 증가할 수 있는 경우, 실제 데이터 규모·응답 크기가 문제를 일으킬 수 있는 경우, 또는 기존 API 계약 및 프로젝트 관례가 요구할 때 페이징을 적용합니다.
  - 제품 계약상 최대 개수가 작고 명확하게 제한된(bounded) 목록이거나 페이징이 사용자 흐름 및 계약에 실질적 가치를 주지 않는 경우에는 페이징을 필수 요구사항으로 강제하지 마십시오.
  - 페이징 적용 시 기존 프로젝트의 관례와 API 계약(PageNumber, LimitOffset, Cursor 등)을 우선하여 자율적으로 따르고, 관례로 결정 가능한 방식을 불필요하게 사용자에게 다시 질문하지 마십시오.

---

## 🔐 4. 보안 및 환경 설정 (Security & Config)

- **설정 분리 (`settings.py`)**:
  - Secret Key, DB Password, API Key 등 자격 증명과 환경별 보안값은 하드코딩하지 않고 환경 변수 또는 비밀 관리 체계로 주입·분리합니다.
  - split settings는 환경 차이 또는 설정 소유권이 이를 정당화할 때 사용하며, 기존 프로젝트 구조를 보존합니다.
- **배포 보안 옵션**:
  - 운영 환경에서는 `DEBUG = False`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `SECURE_SSL_REDIRECT` 등의 보안 옵션을 철저히 확인하십시오.

---

## ⚙️ 5. 비동기 작업 및 마이그레이션 (Celery & Migrations)

- **비동기 태스크 분리**:
  - 요청 지연, 재시도·내구성 또는 독립 실행 요구가 확인되는 이메일·외부 연동·대용량 처리에 적절한 background task를 사용합니다.
- **마이그레이션 이력 관리**:
  - 마이그레이션 파일(`makemigrations`)은 항상 테스트 후 Git 버전 관리에 포함시키고, 배포 시 `migrate`를 안전하게 수행하십시오.

---

## 📚 6. 외부 생태계 & 레퍼런스 (Ecosystem & References)

- **`python-ecosystem-kb` 스킬**: Django 서드파티 패키지(Auth, REST, Celery 등) 및 파이썬 생태계 큐레이션 탐색 필요 시 `python-ecosystem-kb` 스킬을 활성화하여 온디맨드로 실시간 조회하십시오.
- **[django-ai-plugins 카탈로그](../architecture/recommended-external-skills.md)**:
  Django ORM, DRF, Celery 비동기, DB 마이그레이션 안전 수칙 및 코드 리뷰어 외부 스킬 상세 지침 및 설치 가이드는 [recommended-external-skills.md](../architecture/recommended-external-skills.md) 모듈을 참조하십시오.

---

## 💬 7. Framework Override 문서화 범위

- Django CBV의 `get()`, `post()` 및 lifecycle hook처럼 framework convention만 따르는 override는 이름과 상위 계약만으로 책임이 명확하면 기계적으로 docstring을 반복하지 않습니다.
- override가 상위 계약과 다른 권한, transaction, side effect, 오류 조건 또는 domain policy를 추가하면 Core 기준에 따라 그 차이를 문서화합니다.
  구체적인 docstring 형식은 Python style 규칙을 따릅니다.
