# 구현 계획: 알라딘 Metadata Provider Adapter

**브랜치**: `feature/day-02-auth-book-search` | **날짜**: 2026-09-03 | **사양**: [spec.md](spec.md)

## 요약

알라딘 ItemSearch 응답을 Provider 중립 불변 값 객체로 변환하는 동기 Adapter를
`integrations.aladin`에 구현한다. 기본 호출은 표준 라이브러리 `urllib`로 수행하되
`(url, timeout) -> bytes` transport를 주입할 수 있게 한다. 정상 빈 결과는 빈 tuple,
설정·timeout·통신/Provider·응답 형식 실패는 별도 예외로 표현한다.

## 기술적 맥락

**언어/버전**: Python 3.14
**주요 의존성**: Django 6.1, django-environ 0.14, 표준 라이브러리 `urllib`
**저장소**: N/A — 검색은 무상태이며 `Book`을 읽거나 변경하지 않음
**테스트**: pytest 9.1, pytest-django 4.14, Ruff 0.16, `scripts/verify.py`
**대상 플랫폼**: Django 기반 Linux Web server
**프로젝트 유형**: 단일 Django Web application
**성능 목표**: 검색당 외부 요청 1회, 최대 20개 항목 선형 변환
**제약 조건**: 기본 timeout 3초, 자동 테스트의 외부 호출 0건, 신규 runtime 의존성
없음, credential·원본 오류 본문 비노출, 저장/retry/cache 없음
**규모/범위**: Adapter 1개, Provider 중립 DTO와 Protocol, 실패 범주 4개

## 헌법 검사

*게이트: 0단계 조사 전에 통과했으며 1단계 설계 후 재확인했다.*

| 원칙/게이트 | 설계 대응 | 결과 |
| --- | --- | --- |
| II. 범위 규율 | Adapter만 구현하고 Service/UI/저장/retry/cache는 제외한다. | 통과 |
| III. 신뢰 경계 | 외부 JSON과 필수값을 검증하고 key/원본 오류 본문을 노출하지 않는다. | 통과 |
| IV. 단순한 아키텍처 | `integrations.aladin` 경계와 Protocol을 사용하며 새 HTTP 패키지를 추가하지 않는다. | 통과 |
| V. 증거 기반 품질 | 주입 transport로 정상/빈 결과/실패를 재현하고 전체 verify를 실행한다. | 통과 |
| Runtime/도구 | Python 3.14, Django 6.1, uv/pytest/Ruff를 유지한다. | 통과 |
| 환경변수 | TTB key는 Adapter 호출 시 필요한 조건부 credential이며 누락 시 호출 전에 명시적으로 실패한다. | 통과 |

설계 후에도 헌법 위반이나 정당화가 필요한 추가 복잡성은 없다.

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/002-aladin-metadata-adapter/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── provider-contract.md
└── tasks.md                 # $speckit-tasks 단계에서 생성
```

### 소스 코드 (저장소 루트)

```text
src/
├── config/
│   └── settings.py
└── integrations/
    ├── __init__.py
    └── aladin/
        ├── __init__.py
        ├── client.py
        ├── contracts.py
        └── exceptions.py

tests/
└── integrations/
    └── aladin/
        └── test_client.py
```

**구조 결정**: Provider 고유 코드는 `books`에 넣지 않고 승인된
`integrations.aladin` 경계에 둔다. 후속 Service는 알라딘 JSON이나 HTTP 구현이 아닌
`BookMetadataProvider`와 `ProviderBook` 계약에만 의존한다.

## 복잡성 추적

헌법 위반이 없으므로 해당 사항이 없다.
