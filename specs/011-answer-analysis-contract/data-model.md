# 데이터 모델: 답변 분석 계약

이 기능은 DB schema를 추가하지 않는다. 아래 객체는 Provider 경계와 Application에서 사용하는
immutable 비영속 값이다.

## AnswerAnalysisContext

| 필드 | 형식 | 계약 |
| --- | --- | --- |
| `question_context` | 기존 `InterviewQuestionContext` | Book metadata, Reading 상태, Knowledge readiness/claims와 trusted 질문 정책 |
| `question` | string | 대상 Turn의 저장된 nonblank 질문 |
| `answer` | string | 확정된 1~2,000자 사용자 원문, 수정하지 않음 |
| `current_coverage` | `CurrentCoverageItem` 4개 tuple | 네 canonical 축의 현재 상태 |

질문, 답변, Book metadata와 Knowledge Claim은 Provider에게 명령이 아닌 untrusted data로 전달한다.

## CurrentCoverageItem

| 필드 | 형식 | 허용값 |
| --- | --- | --- |
| `axis` | string | 네 `CoreCoverageAxis` token |
| `status` | string | `UNCOVERED`, `PARTIAL`, `COVERED` |

항상 네 축을 canonical 순서로 한 번씩 포함하며 DB의 검증된 snapshot에서 생성한다.

## ProposedAnswerAnalysis

| 필드 | 형식 | 계약 |
| --- | --- | --- |
| `meaning` | string 또는 null | low-information이면 null, 아니면 의미 요약 |
| `low_information` | boolean | 단일 답변 수준의 정보 부족 여부 |
| `coverage_patch` | `ProposedCoverageChange` tuple | 0~4개 후보 |

Provider DTO 생성에 성공했더라도 Application validation 전에는 신뢰하지 않는다.

## ProposedCoverageChange

| 필드 | 형식 | wire 허용값 |
| --- | --- | --- |
| `axis` | string | 네 Core Coverage 축 |
| `status` | string | `PARTIAL`, `COVERED` |
| `evidence` | string | 축 판정의 사용자 답변 원문 인용 |

## AnswerAnalysisResult

| 필드 | 형식 | 계약 |
| --- | --- | --- |
| `meaning` | string 또는 `None` | 정상은 trim된 1~1,000자, low-information은 `None` |
| `low_information` | bool | 아래 invariant와 일치 |
| `coverage_patch` | `AnalyzedCoverageChange` tuple | canonical 축 순서의 0~4개 strict promotion |

```text
low_information = True  → meaning is None, coverage_patch == ()
low_information = False → meaning is nonblank string, coverage_patch may be empty
```

## AnalyzedCoverageChange

| 필드 | 형식 | 계약 |
| --- | --- | --- |
| `axis` | `CoreCoverageAxis` | 후보 tuple 안에서 유일 |
| `status` | `CoverageStatus` | 현재 상태보다 엄격히 높은 `PARTIAL` 또는 `COVERED` |
| `evidence` | string | trim된 1~500자, answer의 exact contiguous substring |

| 현재 | 허용 후보 |
| --- | --- |
| `UNCOVERED` | `PARTIAL`, `COVERED` |
| `PARTIAL` | `COVERED` |
| `COVERED` | 없음 |

같은 상태, 하락, `UNCOVERED`와 알 수 없는 token은 전체 결과를 거부한다.

## 불변조건과 저장소 영향

1. Context는 사용자 소유의 유효한 `IN_PROGRESS` Interview와 그 Interview의 확정 답변 Turn에서만 생성한다.
2. 한 분석은 한 Turn만 대상으로 하며 과거 Turn 전체를 포함하지 않는다.
3. 한 후보라도 잘못되면 trusted 결과 전체를 만들지 않는다.
4. 분석은 Interview, Coverage, Turn과 다른 aggregate를 변경하지 않는다.
5. Provider 제안과 trusted 결과는 DB model이 아니며 저장 lifecycle이 없다.
6. model, migration, index, constraint와 Coverage JSON shape를 변경하지 않는다.
