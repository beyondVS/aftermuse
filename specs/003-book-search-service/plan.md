# 구현 계획: 도서 검색 Service와 결과 정규화

**브랜치**: `feature/day-02-auth-book-search` | **날짜**: 2026-09-03 | **사양**: [spec.md](spec.md)

**입력**: `/specs/003-book-search-service/spec.md`의 기능 사양

## 요약

검색어 양끝 공백을 제거하고 Provider 중립 검색 계약을 호출하는 순수 Python Service를
`books` 도메인에 추가한다. Service는 불변 결과 객체와 `SUCCESS`, `EMPTY`, `ERROR`
상태를 반환하고, Provider가 반환한 `ProviderBook` tuple과 전체 출간일을 그대로
보존한다. 공백 검색어는 외부 호출 없이 `EMPTY`, 모든 `ProviderError`는 세부 내용을
노출하지 않는 `ERROR`로 변환하며 저장, cache, retry 및 UI는 포함하지 않는다.

## 기술적 맥락

**언어/버전**: Python 3.14

**주요 의존성**: Django 6.1 애플리케이션, 표준 라이브러리 `dataclasses`, `enum`, 기존
`BookMetadataProvider`와 `ProviderBook` 계약

**저장소**: N/A — 검색 Service는 ORM을 사용하거나 데이터를 영속화하지 않음

**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16, `scripts/verify.py`

**대상 플랫폼**: Django 기반 Linux Web server

**프로젝트 유형**: 단일 Django Web application 내부의 도메인 Service

**성능 목표**: 유효한 검색당 Provider 호출 1회, Provider가 반환한 결과의 순서와
Metadata를 변형하거나 누락하지 않고 전달

**제약 조건**: 공백 검색 시 Provider 호출 0회, Provider 오류 상세 비노출, DB query와
mutation 0건, 신규 runtime 의존성·retry·cache·Provider 병합 없음

**규모/범위**: Service 모듈 1개, 상태 enum 1개, 불변 결과 값 객체 1개, 집중 단위 테스트
모듈 1개

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 재확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| II. 핵심 제품 루프와 범위 규율 | 책 선택으로 이어지는 검색 상태 정규화만 구현하고 IMP-023 UI와 IMP-024 저장은 제외한다. | 통과 |
| III. 신뢰 경계와 데이터 통제 | 외부 Provider 오류를 안전한 상태로 격리하며 오류 상세나 자격 증명을 결과에 싣지 않는다. | 통과 |
| IV. 단순하고 일관된 아키텍처 | HTTP 및 Django View에 의존하지 않는 `books` Service가 기존 Provider Protocol만 소비한다. | 통과 |
| V. 증거 기반 품질 | fake Provider로 성공, 빈 결과, 오류, 공백 입력을 검증하고 전체 품질 게이트를 실행한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, pytest와 Ruff의 기존 환경을 유지하고 의존성을 추가하지 않는다. | 통과 |
| 영속성 경계 | ORM import와 DB 접근 없이 검색 결과를 transient 값으로만 반환한다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/003-book-search-service/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── service-contract.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── books/
│   ├── models.py            # 기존 Book 모델, 이 기능에서 변경하지 않음
│   └── services.py          # 검색 상태와 결과 정규화 Service
└── integrations/
    └── aladin/
        ├── contracts.py     # 기존 Provider Protocol과 ProviderBook
        └── exceptions.py    # 기존 ProviderError 계층

tests/
└── books/
    └── test_services.py     # fake Provider 기반 Service 계약 테스트

docs/AfterMuse_MVP_Implementation_Plan_v5.md  # 전체 검증 후 IMP-022 완료 표시
CHANGELOG.md                                  # Unreleased 기능 기록
```

**구조 결정**: 검색 orchestration과 화면용 상태 정규화는 `books` 도메인의 Service에
둔다. Service는 구체 알라딘 Adapter가 아닌 기존 `BookMetadataProvider` Protocol에만
의존하며, View·Template·ORM 또는 network 구현을 import하지 않는다. 별도 DTO를 다시
만들지 않고 검증된 `ProviderBook`을 보존해 Metadata 손실과 중복 변환을 피한다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
