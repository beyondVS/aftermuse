# Quickstart: 최소 Book Knowledge 및 준비 상태 검증

## 목적

신규 schema, Claim 제약, 수동 Seed 멱등성·전체 rollback, Book별 조회와
`READY`/`READY_LIMITED` 판정을 PostgreSQL에서 재현한다.

## 사전 조건

- 프로젝트 `.env`에 개발 PostgreSQL과 필수 Django 환경변수가 설정되어 있다.
- 의존성이 `uv sync`로 설치되어 있다.
- 작업 디렉터리는 저장소 루트다.
- 자세한 모델과 경계는 [data-model.md](data-model.md),
  [service-contract.md](contracts/service-contract.md),
  [seed-fixture-contract.md](contracts/seed-fixture-contract.md)를 따른다.

## 1. 정적·schema 사전 검증

```powershell
uv run python src/manage.py check
uv run python src/manage.py makemigrations --check --dry-run
uv run python src/manage.py sqlmigrate knowledge 0001
```

예상 결과:

- Django system check 오류가 없다.
- 누락된 migration 변경이 없다.
- SQL은 신규 `knowledge_bookknowledge` table과 FK·kind/content CHECK·UNIQUE만 만들며
  기존 table의 column 변경, rename, drop 또는 data backfill을 포함하지 않는다.

## 2. Migration 적용

```powershell
uv run python src/manage.py migrate
```

예상 결과: `knowledge.0001_initial`이 성공하고 기존 Book·Reading 데이터는 유지된다.

## 3. 대상 Book 준비

Seed는 Book을 생성하지 않으므로 검증 환경에 두 Book을 먼저 등록한다.

```powershell
uv run python src/manage.py shell -c "from books.models import Book; Book.objects.get_or_create(isbn13='9780452284234', defaults={'title': '1984'}); Book.objects.get_or_create(isbn13='9780374275631', defaults={'title': 'Thinking, Fast and Slow'})"
```

예상 결과: 두 ISBN13의 기존 Book이 있거나 새 검증용 Book이 준비된다. 이 명령은 Seed가
Book을 생성한다는 의미가 아니라 quickstart 사전 조건을 수동으로 구성한다.

## 4. Seed 최초·반복 로드

```powershell
uv run python src/manage.py seed_book_knowledge
uv run python src/manage.py seed_book_knowledge
```

예상 결과:

- 두 실행이 모두 성공한다.
- 두 번째 실행 후에도 같은 Book·kind·content Claim이 중복되지 않는다.
- 각 대상 Book에 3~5개 Claim이 존재한다.

## 5. 조회와 준비 상태 확인

```powershell
uv run python src/manage.py shell -c "from books.models import Book; from knowledge.services import get_book_knowledge_readiness, list_book_knowledge; books=Book.objects.filter(isbn13__in=['9780452284234','9780374275631']).order_by('isbn13'); print([(book.isbn13, get_book_knowledge_readiness(book), len(list_book_knowledge(book))) for book in books])"
```

예상 결과: 두 Book 모두 `READY`이고 각각의 Claim 수가 Seed 정의와 일치한다.

Claim이 없는 별도 Book을 만든 뒤 판정을 확인한다.

```powershell
uv run python src/manage.py shell -c "from books.models import Book; from knowledge.services import get_book_knowledge_readiness; book,_=Book.objects.get_or_create(isbn13='9780000000002', defaults={'title':'Knowledge 없는 검증 도서'}); print(get_book_knowledge_readiness(book))"
```

예상 결과: `READY_LIMITED`이며 오류나 차단 상태로 바뀌지 않는다.

## 6. 자동 인수 검증

```powershell
uv run pytest tests/books/test_models.py tests/knowledge
uv run python scripts/verify.py
```

필수 검증:

- 모델 유형·내용·Book 관계와 DB CHECK/UNIQUE
- 같은 Book·kind·content의 순차·동시 중복 등록 방지
- Book별 Claim 격리와 결정적 조회 순서
- Claim 유무에 따른 `READY`/`READY_LIMITED` 정확성
- Seed 3회 반복 로드 후 행 수·내용 불변
- 누락 Book 또는 잘못된 Claim Seed의 전체 rollback과 Book 자동 생성 0건
- migration forward/reverse/forward 왕복
- Django check, Ruff format/lint, 전체 pytest

## 7. 실패 복구 확인

자동 테스트는 대상 Book 하나가 누락된 격리 DB에서 Seed command를 실행하고 다음을
검증해야 한다.

- 명령이 실패를 반환한다.
- 이번 실행에서 추가된 BookKnowledge는 0건이다.
- 기존 Book과 기존 Claim은 실행 전 상태 그대로다.
- 누락된 Book은 자동 생성되지 않는다.
