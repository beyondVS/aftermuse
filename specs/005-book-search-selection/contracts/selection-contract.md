# Contract: 선택 후보와 Book 등록

## 후보 계약

- 성공 검색 최대 20건을 사용자 PK·생성 시각·임의 `candidate_id`와 함께 session에 저장한다.
- 후보는 15분 유효하고 새 유효 검색이 이전 batch를 제거한다.
- Empty/Error는 후보를 남기지 않는다.
- 조회는 ID, 현재 사용자와 TTL을 모두 검사한다.
- client 입력은 `candidate_id` 하나이며 ISBN13/Metadata field는 허용하지 않는다.
- 없음·만료·소유자 불일치는 Book 변경 없이 공통 재검색 안내로 변환한다.

## Book 선택 Service

```text
select_book(candidate) -> BookSelectionResult(book, created)
```

- 새 ISBN13은 candidate Metadata로 한 건 생성하고 `created=true`다.
- 기존 ISBN13은 필드 변경 없이 재사용하고 `created=false`다.
- PostgreSQL unique 제약과 짧은 transaction으로 동시 요청도 최종 한 건을 보장한다.
- 외부 호출과 session I/O는 transaction 밖에서 완료한다.
- 같은 후보의 반복 POST는 같은 Book을 반환하며 Reading/Knowledge를 만들지 않는다.

## 보안 계약

- 선택은 인증·CSRF 보호 POST만 허용한다.
- 다른 사용자, 임의·만료 ID와 추가 client Metadata는 Book 생성값으로 사용하지 않는다.
- 실패 시 부분 Book, credential, 후보 원문과 내부 진단 정보를 노출하지 않는다.
