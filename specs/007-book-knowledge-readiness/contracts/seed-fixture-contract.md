# 수동 Seed Fixture 계약

## 목적

자동 Research 없이 Core MVP의 Interview Context를 검증할 수 있도록, 공식 자료로 확인한
도서 2권의 작은 Claim 집합을 반복 가능하게 적용한다.

## 데이터 형식

`src/knowledge/seed_data/book_knowledge.json`의 각 항목은 다음 정보를 가진다.

```text
book_isbn13: 기존 Book의 ISBN13
kind: theme | argument | concept | character | event
content: 1~500자의 짧은 한국어 Claim
```

숫자 Book PK나 BookKnowledge PK는 데이터 계약에 포함하지 않는다. 중복은 ISBN13으로 찾은
Book, kind, 앞뒤 공백을 제거한 content의 조합으로 판정한다.

## 대상

| ISBN13 | 제목 | 최소 Claim 범주 |
| --- | --- | --- |
| `9780452284234` | 1984 | Theme, Character, Concept 또는 Event |
| `9780374275631` | Thinking, Fast and Slow | Argument, Concept, Theme |

Seed는 대상 Book을 만들거나 서지정보를 갱신하지 않는다.

## 적용 전 조건

- schema migration 완료
- 두 ISBN13에 해당하는 Book이 모두 존재
- `checklists/seed-knowledge.md`의 모든 Claim 출처 대조·승인 완료

## 성공 결과

- 두 Book 각각에 3~5개의 유효한 Claim 존재
- 대상 Book 이외의 Book 변경 없음
- 반복 실행 전후 Claim 행 수와 내용 동일
- 대상 Book 모두 `READY`

## 실패 결과

다음 중 하나라도 발생하면 Seed 실행 전체가 실패하고 실행 전 DB 상태를 유지한다.

- 대상 Book 누락 또는 모호한 식별
- 허용되지 않은 kind
- 비어 있거나 500자를 넘는 content
- DB 제약 또는 직렬화 오류

오류가 발생해도 누락 Book을 생성하거나 다른 Book을 추측해 연결하지 않는다.

## 출처와 내용 규칙

- Claim은 `research.md`에 기록된 공식 출판사 소개를 근거로 작성한다.
- 각 Claim은 `checklists/seed-knowledge.md`에 ISBN, kind, content, 공식 출처 URL과 출처의
  지지 여부를 기록하고 승인된 뒤에만 Seed 데이터에 포함한다. 승인된 최종 Claim 값은
  해당 체크리스트의 표를 기준 원본으로 삼는다.
- 원문 문장을 장문 복제하지 않고 검증 가능한 사실·주제를 짧게 한국어로 재서술한다.
- 목차 제목만으로 주장이나 내용을 추론하지 않는다.
- 사용자 Reading, ReadingEntry, Interview 답변 또는 Reflection을 포함하지 않는다.

## 적용 경계

- `seed_book_knowledge` management command가 JSON을 읽고 형식 오류를 보고한다.
- command는 전체 항목을 `seed_book_knowledge()` Service에 전달하며 ORM 쓰기를 하지 않는다.
- Service는 모든 Book과 Claim의 선검증을 완료한 뒤 하나의 transaction에서만 저장한다.
