# 검증 가이드: Book 기본 모델

이 문서는 구현 완료 후 IMP-020을 실제 PostgreSQL 환경에서 검증하는 절차다. 필드와
제약의 상세 계약은 [data-model.md](data-model.md)를 따른다.

## 1. 사전 조건

- IMP-002의 PostgreSQL 개발 환경 구성이 완료되어 있어야 한다.
- 저장소 루트에 안전한 로컬 `.env`가 준비되어 있어야 한다.
- `uv`, Python 3.14 및 Docker Compose를 사용할 수 있어야 한다.

```powershell
docker compose up -d --wait db
uv sync --locked
```

기대 결과: PostgreSQL 컨테이너가 healthy이고 잠금 파일 변경 없이 개발 환경이 준비된다.

## 2. 모델 집중 검증

```powershell
uv run pytest tests/books/test_models.py -v
```

테스트는 다음 결과를 모두 입증해야 한다.

1. ISBN13과 7개 서지정보를 저장한 뒤 모든 값이 동일하게 조회된다.
2. ISBN13과 제목만 저장하면 선택 문자열은 빈 문자열, 출간일은 `NULL`로 조회된다.
3. 짧거나 문자가 섞였거나 Unicode 숫자를 포함한 ISBN13과 빈 제목은 `full_clean()`에서
   거부된다.
4. ISBN13 exact lookup은 일치하는 한 건만 반환하고 미존재를 구분한다.
5. 순차 중복 저장은 무결성 오류가 발생하며 기존 Book 값은 바뀌지 않는다.
6. 실제 PostgreSQL에서 같은 ISBN13의 동시 저장 경쟁 후 성공은 한 건이고 최종 행도
   한 건이다.
7. 서로 다른 ISBN13 100건은 잘못된 반환이나 필드 손실 없이 각각 조회되고, 단건 조회의
   95% 이상이 1초 이내에 완료된다.
8. `tests/test_settings.py`의 격리된 관리 명령이 새 `books` 앱을 포함한 상태에서도
   성공한다.

## 3. Migration SQL 검토

```powershell
uv run python src/manage.py sqlmigrate books 0001
uv run python src/manage.py sqlmigrate books 0001 --backwards
uv run python src/manage.py makemigrations --check --dry-run books
```

기대 결과:

- forward SQL은 신규 `books_book` 테이블, 기본 PK, ISBN13 unique constraint와 Django의
  `varchar_pattern_ops` 보조 index를 생성한다.
- reverse SQL은 `books_book` 테이블 삭제이며 데이터가 사라지는 동작임이 명확하다.
- 기존 테이블 rewrite, data backfill, 외래키 또는 불필요한 추가 index가 없다.
- model state와 migration 사이에 미생성 변경이 없다.

## 4. Forward/Reverse 검증

데이터를 보존할 필요가 없는 격리된 개발 또는 test database에서만 reverse를 실행한다.

```powershell
uv run python src/manage.py migrate books 0001 --noinput
uv run python src/manage.py migrate --check
uv run python src/manage.py migrate books zero --noinput
uv run python src/manage.py migrate books 0001 --noinput
uv run pytest tests/books/test_models.py -v
```

기대 결과: 초기 migration이 forward, reverse, 재적용 모두 성공하고 재적용 후 모델 테스트가
다시 통과한다. 공유 또는 운영 데이터베이스에서는 이 reverse 절차를 실행하지 않는다.

## 5. 전체 품질 게이트

```powershell
uv run python scripts/verify.py
```

기대 결과: Django system check, Ruff format, Ruff lint와 전체 pytest가 모두 성공한다.

## 6. 범위 확인

다음 항목은 이 검증에서 다루지 않는다.

- 실제 알라딘 또는 다른 Metadata Provider 호출
- 도서 검색 Service와 결과 정규화
- 검색 화면, HTMX fragment 또는 브라우저 흐름
- 검색 결과를 기존 Book과 병합하거나 갱신하는 동작
- Reading 또는 Book Knowledge 관계
