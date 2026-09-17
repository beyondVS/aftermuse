# 2주 검증용 책 세트 계약

## 실행 경계

```powershell
uv run python src/manage.py prepare_validation_books
```

명시적으로 실행하는 개발·테스트·검증용 command다. application 시작, migration 또는 일반
사용자 요청에서 자동 실행하지 않는다.

## 입력 원본

`src/knowledge/seed_data/validation_books.json`은 정확히 세 descriptor를 가진다.

| ISBN13 | 제목 | 장르 | 기대 상태 |
| --- | --- | --- | --- |
| `9780452284234` | 1984 | fiction | READY |
| `9780374275631` | Thinking, Fast and Slow | nonfiction | READY |
| `9780143111597` | The Left Hand of Darkness | fiction | READY_LIMITED |

READY 두 권의 Claim 기준 원본은 기존 `book_knowledge.json`과 승인 체크리스트다. 새 JSON에
Claim을 복제하지 않는다.

## 성공 계약

- 누락된 Book은 ISBN13 기준으로 생성한다.
- 이미 존재하는 Book은 재사용하고 서지정보를 덮어쓰지 않는다.
- READY 두 권에 기존 승인 Claim 8개를 멱등 적용한다.
- READY_LIMITED 책에는 BookKnowledge가 0개다.
- 첫 실행과 반복 실행 뒤 Book 3권 및 Claim 내용이 동일하다.
- command는 생성·재사용 Book 수와 Claim 생성·재사용 수만 보고하며 사용자 데이터를
  출력하지 않는다.

## 실패 계약

다음 조건에서는 전체 작업을 실패하고 이번 실행의 부분 변경을 rollback한다.

- JSON 형식, ISBN13, genre 또는 기대 상태가 잘못됨
- 정확히 3권 또는 READY fiction 1권·READY nonfiction 1권·READY_LIMITED 1권 구성이 아님
- READY_LIMITED 대상에 기존 BookKnowledge가 있음
- 기존 승인 Seed 또는 DB 쓰기 실패

READY_LIMITED 불일치 시 기존 Knowledge를 자동 삭제하지 않는다. 실제 사용자 Reading,
Interview 또는 Reflection은 생성·수정·삭제하지 않는다.

## 검증 계약

- command를 연속 두 번 실행해 두 번째 실행의 신규 Book·Claim이 0건인지 확인한다.
- 세 Book을 ISBN13으로 조회하고 기대 genre descriptor와 readiness를 확인한다.
- 다른 Book과 모든 사용자 소유 record의 행 수와 값이 바뀌지 않았는지 확인한다.
