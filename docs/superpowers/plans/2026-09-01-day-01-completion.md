# AfterMuse Day 01 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 초기 프로젝트 설정을 재작성하지 않고 `IMP-001`부터 `IMP-004`까지의 완료 조건을 격리된 환경에서 검증하고, 증거가 확보된 항목만 Day 01 완료로 표시한다.

**Architecture:** 현재 checkout의 자동 검증을 기준선으로 삼되, 별도의 Docker Compose project와 새 PostgreSQL volume을 사용해 빈 database migration을 검증한다. 실제 browser에서 Desktop/Mobile Layout과 HTMX/Alpine 동작을 확인한 뒤 문서 상태를 동기화하며, 실패가 발견되면 완료 표시를 중단하고 관찰된 실패를 입력으로 별도의 TDD 수정 작업을 만든다.

**Tech Stack:** Python 3.14, Django 6.1, PostgreSQL 18.6, Psycopg 3.3, uv, Docker Compose, pytest 9.1, pytest-django 4.14, Ruff 0.16, Django Templates, HTMX 2.0.10, Alpine.js CSP 3.17.1

**Spec:** `docs/superpowers/specs/2026-09-01-day-01-completion-design.md`

## Global Constraints

- 기존 초기화 구현을 삭제하거나 다시 scaffold하지 않는다.
- `accounts`, `books`, `readings`, `knowledge`, `reflections`, `credits`, `insights`, `backoffice`, `integrations`, `common` app을 만들지 않는다.
- SQLite fallback, Node build chain, CSS framework와 새 dependency를 추가하지 않는다.
- 실제 `.env`와 credential을 Git에 추가하거나 출력하지 않는다.
- 내부 PK는 Django의 `BigAutoField`를 유지한다.
- PostgreSQL 재현성 검증은 기존 `aftermuse` database와 분리된 Compose project 및 volume에서 수행한다.
- 임시 Compose project의 container 또는 volume 삭제는 정확한 대상을 확인한 뒤 사용자 승인을 받아 수행한다.
- 테스트되지 않은 결함을 즉석에서 수정하지 않는다. 실패가 발견되면 해당 동작의 실패 테스트를 먼저 설계한다.
- 커밋은 diff와 검증 결과를 보고한 뒤 사용자 승인을 받아 수행한다.
- `codex-downshift`는 실제 실행 중 확정된 명령 실행이나 기계적 문서 갱신처럼 bounded 작업에만 검토하며, 검증 해석·실패 원인 판단·완료 결정에는 사용하지 않는다.

---

### Task 1: 격리 상태와 Day 01 추적 범위 확정

**Files:**

- Read: `docs/AfterMuse_MVP_Implementation_Plan_v5.md`
- Read: `docs/superpowers/specs/2026-09-01-day-01-completion-design.md`
- Read: `pyproject.toml`
- Read: `compose.yaml`
- Read: `src/config/settings.py`
- Read: `scripts/verify.py`
- Read: `tests/test_repository_contract.py`
- Read: `tests/test_settings.py`
- Read: `tests/test_home_page.py`
- Read: `tests/test_verify_script.py`

**Interfaces:**

- Consumes: Day 01의 `IMP-001`, `IMP-002`, `IMP-003`, `IMP-004` 완료 조건
- Produces: 이후 Task가 검증할 네 가지 계약과 격리된 실행 위치

- [ ] **Step 1: Git 격리 상태와 변경 파일 확인**

Run:

```powershell
$gitDir = git rev-parse --path-format=absolute --git-dir
$gitCommon = git rev-parse --path-format=absolute --git-common-dir
$branch = git branch --show-current
$superproject = git rev-parse --show-superproject-working-tree
Write-Output "GIT_DIR=$gitDir"
Write-Output "GIT_COMMON=$gitCommon"
Write-Output "BRANCH=$branch"
Write-Output "SUPERPROJECT=$superproject"
git status --short
```

Expected: linked worktree라면 `GIT_DIR`과 `GIT_COMMON`이 다르고 `SUPERPROJECT`는 비어 있다. 일반 checkout이면 구현을 시작하기 전에 `superpowers:using-git-worktrees`에 따라 사용자에게 격리 worktree 생성 승인을 요청한다. 기존 사용자 변경은 수정하거나 이동하지 않는다.

- [ ] **Step 2: Day 01 밖의 Django app이 생성되지 않았는지 확인**

Run:

```powershell
Get-ChildItem -Directory src | Select-Object -ExpandProperty Name
Get-ChildItem -Directory src/config | Select-Object -ExpandProperty Name
```

Expected: `src` 아래 application package는 `config`뿐이며 Day 02 이후의 domain app이 없다. `__pycache__`는 source package로 세지 않는다.

- [ ] **Step 3: 계획과 현재 구현의 추적 항목 확인**

Run:

```powershell
rg -n "IMP-001|IMP-002|IMP-003|IMP-004" docs/AfterMuse_MVP_Implementation_Plan_v5.md
rg -n "postgres:18\.6-trixie|django-environ|scripts/verify.py|htmx.min.js|alpine.min.js|BigAutoField" pyproject.toml compose.yaml src tests scripts README.md
```

Expected: 네 IMP는 아직 `[ ]`이고, 각 완료 조건에 대응하는 runtime, database, 품질 명령과 UI 산출물이 현재 저장소에서 발견된다.

- [ ] **Step 4: Task 1 결과 판정**

Expected: 격리된 작업 위치와 네 IMP의 검증 대상이 확정된다. domain app이 이미 존재하거나 기존 변경과 충돌하면 이후 Task를 실행하지 않고 사용자에게 보고한다.

---

### Task 2: Runtime, dependency와 저장소 계약 검증

**Files:**

- Verify: `.python-version`
- Verify: `.env.example`
- Verify: `pyproject.toml`
- Verify: `uv.lock`
- Verify: `compose.yaml`
- Verify: `src/static/vendor/htmx.min.js`
- Verify: `src/static/vendor/alpine.min.js`
- Verify: `src/static/vendor/HTMX-LICENSE.txt`
- Verify: `src/static/vendor/ALPINE-LICENSE.txt`
- Test: `tests/test_repository_contract.py`

**Interfaces:**

- Consumes: Task 1에서 확정한 `IMP-001`~`IMP-004` 추적 범위
- Produces: 고정 runtime, locked dependency, PostgreSQL Compose와 local browser asset의 검증 증거

- [ ] **Step 1: 도구 및 framework version 기록**

Run:

```powershell
uv --version
docker --version
docker compose version
uv run python --version
uv run python -c "import django, psycopg; print(f'Django {django.get_version()}'); print(f'psycopg {psycopg.__version__}')"
```

Expected: Python은 `3.14.x`, Django는 `6.1.x`, Psycopg는 `3.3.x`이며 uv, Docker와 Compose version이 출력된다.

- [ ] **Step 2: lockfile과 동일한 dependency 환경 확인**

Run:

```powershell
uv sync --locked
```

Expected: `uv.lock` 변경 없이 성공한다. 실행 후 `git status --short`에 dependency metadata 변경이 없어야 한다.

- [ ] **Step 3: 저장소 계약 테스트 실행**

Run:

```powershell
uv run pytest tests/test_repository_contract.py -q
```

Expected: `.python-version`, `.env.example` 변수 집합과 PostgreSQL 18 Compose 계약을 검증하는 `3 passed`.

- [ ] **Step 4: local vendor asset과 license 확인**

Run:

```powershell
Get-FileHash src/static/vendor/htmx.min.js -Algorithm SHA256
Get-FileHash src/static/vendor/alpine.min.js -Algorithm SHA256
Select-String -Path src/static/vendor/htmx.min.js -Pattern "2.0.10"
Select-String -Path src/static/vendor/alpine.min.js -Pattern "3.17.1"
Get-Item src/static/vendor/HTMX-LICENSE.txt
Get-Item src/static/vendor/ALPINE-LICENSE.txt
```

Expected: 두 SHA256 값이 출력되고 HTMX `2.0.10`, Alpine.js `3.17.1` 문자열과 두 license 파일이 확인된다.

- [ ] **Step 5: Task 2 결과 판정**

Expected: version, dependency, repository contract 또는 vendor 검증 중 하나라도 실패하면 IMP 완료 처리를 중단한다. 현재 계약과 다른 의도적 변경이 필요한 경우 계획을 수정한 뒤 진행한다.

---

### Task 3: 빈 PostgreSQL volume에서 migration 재현

**Files:**

- Read: `.env.example`
- Read: `compose.yaml`
- Verify: `src/config/settings.py`
- Verify: Django built-in migrations

**Interfaces:**

- Consumes: `compose.yaml`의 `db` service와 `django-environ`이 OS 환경변수를 `.env`보다 우선하는 설정
- Produces: 기존 개발 DB와 분리된 `aftermuse-day01-verify` Compose project의 healthy 상태와 빈 DB migration 증거

- [ ] **Step 1: 검증용 host port가 비어 있는지 확인**

Run:

```powershell
Get-NetTCPConnection -LocalPort 55432 -ErrorAction SilentlyContinue
```

Expected: 출력이 없다. 이미 점유되어 있으면 임의로 process를 종료하거나 port를 바꾸지 말고 사용자에게 보고한다.

- [ ] **Step 2: 현재 Compose project와 volume 대상을 읽기 전용으로 기록**

Run:

```powershell
docker compose ps
docker volume ls --filter name=aftermuse
docker compose -p aftermuse-day01-verify ps
docker volume ls --filter name=aftermuse-day01-verify
```

Expected: 기존 `aftermuse` project 상태가 기록된다. `aftermuse-day01-verify` project나 같은 이름의 volume이 이미 있으면 새 환경으로 간주하지 않고 실행을 중단해 사용자에게 보고한다.

- [ ] **Step 3: process 범위의 검증 환경변수 설정**

Run in one PowerShell session used through Step 7:

```powershell
$env:DJANGO_SECRET_KEY = "day01-verification-only"
$env:DJANGO_DEBUG = "false"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:POSTGRES_DB = "aftermuse_day01_verify"
$env:POSTGRES_USER = "aftermuse_day01_verify"
$env:POSTGRES_PASSWORD = "day01-verification-only"
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "55432"
```

Expected: 값은 현재 PowerShell process와 그 child process에만 적용되고 파일에는 기록되지 않는다. 이 값은 검증용 비밀이 아닌 local disposable credential이다.

- [ ] **Step 4: 별도 Compose project와 새 volume 시작**

Run:

```powershell
docker compose -p aftermuse-day01-verify up -d --wait db
docker compose -p aftermuse-day01-verify ps
```

Expected: `postgres:18.6-trixie` 기반 검증 container가 `healthy`이고 host port `55432`가 container port `5432`에 연결된다.

- [ ] **Step 5: migration 적용 전 빈 상태 확인**

Run:

```powershell
docker compose -p aftermuse-day01-verify exec -T db psql -U aftermuse_day01_verify -d aftermuse_day01_verify -tAc "SELECT to_regclass('public.django_migrations') IS NULL;"
```

Expected: `t`가 출력되어 `django_migrations` table이 아직 없음을 증명한다.

- [ ] **Step 6: Django 기본 migration을 처음부터 적용**

Run:

```powershell
uv run python src/manage.py migrate --noinput
```

Expected: Django 기본 `admin`, `auth`, `contenttypes`, `sessions` migration이 오류 없이 적용된다.

- [ ] **Step 7: migration 적용 상태와 system check 확인**

Run:

```powershell
uv run python src/manage.py migrate --check
uv run python src/manage.py check
docker compose -p aftermuse-day01-verify exec -T db psql -U aftermuse_day01_verify -d aftermuse_day01_verify -tAc "SELECT COUNT(*) > 0 FROM django_migrations;"
```

Expected: `migrate --check`와 system check가 종료 코드 `0`으로 끝나고 SQL 결과는 `t`다.

- [ ] **Step 8: 검증 환경 cleanup 대상을 확인하고 승인 요청**

Run:

```powershell
docker compose -p aftermuse-day01-verify ps
docker volume ls --filter name=aftermuse-day01-verify
```

Expected: 삭제 대상은 `aftermuse-day01-verify` project의 container, network와 `aftermuse-day01-verify_postgres_data` volume으로 한정된다. 사용자 승인 전에는 `down --volumes`를 실행하지 않는다.

- [ ] **Step 9: 승인된 경우에만 검증 환경 삭제**

Run only after approval:

```powershell
docker compose -p aftermuse-day01-verify down --volumes
```

Expected: 검증용 container, network와 volume만 삭제된다. 삭제 후 복구할 수 없음을 완료 보고에 명시한다.

---

### Task 4: 전체 자동 검증 실행

**Files:**

- Verify: `scripts/verify.py`
- Test: `tests/test_repository_contract.py`
- Test: `tests/test_settings.py`
- Test: `tests/test_home_page.py`
- Test: `tests/test_verify_script.py`

**Interfaces:**

- Consumes: healthy PostgreSQL 환경과 locked uv environment
- Produces: IMP-001~IMP-004의 자동 검증 결과와 전체 test 수

- [ ] **Step 1: 기존 개발 DB container 상태 확인**

Run after clearing the process-scoped variables from Task 3 or in a new PowerShell process:

```powershell
docker compose ps
```

Expected: 기본 `db` service가 `healthy`다. 검증용 `POSTGRES_*` 변수가 기본 project 명령에 섞이지 않는다.

- [ ] **Step 2: 단일 품질 명령 실행**

Run:

```powershell
uv run python scripts/verify.py
```

Expected: Django system check, Ruff format check, Ruff lint와 pytest가 순서대로 모두 통과하며 전체 test 수와 `0 failed`가 출력된다.

- [ ] **Step 3: 검증 스크립트 fail-fast 계약 확인**

Run:

```powershell
uv run pytest tests/test_verify_script.py -q
```

Expected: 첫 실패 종료 코드를 반환하고 이후 명령을 실행하지 않는 계약이 `1 passed`로 확인된다.

- [ ] **Step 4: 변경 오염 확인**

Run:

```powershell
git status --short
git diff --check
```

Expected: 계획 및 설계 문서 외에 검증 명령이 만든 추적 파일 변경이 없다. 예상하지 못한 변경은 삭제하거나 되돌리지 말고 원인을 보고한다.

---

### Task 5: Desktop/Mobile과 progressive enhancement 검증

**Files:**

- Verify: `src/templates/base.html`
- Verify: `src/templates/pages/home.html`
- Verify: `src/static/css/app.css`
- Verify: `src/static/js/app.js`
- Verify: `src/static/vendor/htmx.min.js`
- Verify: `src/static/vendor/alpine.min.js`

**Interfaces:**

- Consumes: `home` URL, `setup-status` URL, local static assets와 same-origin CSP
- Produces: Desktop/Mobile Layout, keyboard focus, HTMX partial 교체와 Alpine.js CSP 동작의 browser 증거

- [ ] **Step 1: 개발 서버 시작**

Run in a local terminal with the normal project `.env`:

```powershell
uv run python src/manage.py runserver 127.0.0.1:8000
```

Expected: 서버가 시작되고 Django system check가 통과한다. 이 terminal session id를 기록해 검증 후 `Ctrl+C`로 종료한다.

- [ ] **Step 2: HTTP와 CSP baseline 확인**

Run in a second PowerShell session:

```powershell
$home = Invoke-WebRequest http://127.0.0.1:8000/
$partial = Invoke-WebRequest http://127.0.0.1:8000/setup-status/ -Headers @{"HX-Request" = "true"}
Write-Output $home.StatusCode
Write-Output $home.Headers["Content-Security-Policy"]
Write-Output $partial.StatusCode
Write-Output $partial.Content
```

Expected: 두 status는 `200`; CSP에 `default-src 'self'`, `script-src 'self'`, `style-src 'self'`가 있고 `unsafe-eval`은 없다. partial content에는 `<section id="setup-status"`가 있지만 `<html`과 `<main`은 없다.

- [ ] **Step 3: Desktop viewport 검증**

Use the in-app browser at `1440x900` and open `http://127.0.0.1:8000/`.

Expected:

- skip link, header와 `main` landmark가 존재한다.
- 콘텐츠가 중앙의 제한된 폭으로 표시되고 수평 scrollbar가 없다.
- `Tab`으로 skip link, brand와 두 button에 이동할 때 focus indicator가 보인다.
- browser console에 CSP, HTMX 또는 Alpine initialization error가 없다.

- [ ] **Step 4: HTMX partial 교체 검증**

In the Desktop viewport, activate `HTMX partial 다시 확인`.

Expected: `#setup-status` 영역만 교체되고 full-page navigation이나 document 중첩이 발생하지 않는다. Network response는 `/setup-status/`의 partial HTML이며 status `200`이다.

- [ ] **Step 5: Alpine.js CSP 상태 전환 검증**

In the Desktop viewport, activate `Alpine.js 상태 확인` twice.

Expected: 첫 activation에서 `Alpine.js CSP build가 동작합니다.`가 보이고 button의 `aria-expanded`가 `true`; 두 번째 activation에서 문구가 숨겨지고 `aria-expanded`가 `false`다. CSP violation이 없다.

- [ ] **Step 6: Mobile viewport 검증**

Use the in-app browser at `390x844` and reload `http://127.0.0.1:8000/`.

Expected: heading, status와 action controls가 viewport 안에 표시되고 수평 scrollbar나 잘린 text가 없다. 두 button은 focus 및 activation이 가능하며 HTMX와 Alpine 동작이 Desktop과 동일하다.

- [ ] **Step 7: 개발 서버 종료**

Run: send `Ctrl+C` to the terminal session started in Step 1.

Expected: server process가 정상 종료되고 port `8000`에서 더 이상 응답하지 않는다.

- [ ] **Step 8: Task 5 결과 판정**

Expected: 모든 browser 항목이 확인되어야 IMP-004를 완료할 수 있다. 하나라도 실패하면 screenshot, console 또는 network 증거를 보존하고 완료 표시 전에 별도 TDD 수정 계획을 작성한다.

---

### Task 6: Day 01 완료 상태와 문서 동기화

**Files:**

- Modify: `docs/AfterMuse_MVP_Implementation_Plan_v5.md:113-132`
- Verify: `README.md`
- Verify: `CHANGELOG.md`
- Verify: `docs/superpowers/specs/2026-09-01-day-01-completion-design.md`
- Verify: `docs/superpowers/plans/2026-09-01-day-01-completion.md`

**Interfaces:**

- Consumes: Task 1~5에서 확보한 IMP별 자동·database·browser 검증 증거
- Produces: 사실과 일치하는 Day 01 완료 체크박스와 검토 가능한 최종 diff

- [ ] **Step 1: 네 IMP의 완료 증거를 각각 대조**

Acceptance matrix:

| IMP | 필수 증거 |
| --- | --- |
| IMP-001 | `manage.py check` 성공, `/` HTTP 200, domain app 미생성 |
| IMP-002 | 별도 빈 PostgreSQL 18.6 volume, migration 전 빈 상태, migrate와 `migrate --check` 성공 |
| IMP-003 | `uv sync --locked` 성공, `scripts/verify.py` 전체 성공, fail-fast test 성공 |
| IMP-004 | full/partial HTTP 계약, CSP, Desktop/Mobile, HTMX 교체, Alpine 상태 전환 성공 |

Expected: 각 행의 모든 증거가 존재한다. 일부만 충족한 IMP는 완료 표시하지 않는다.

- [ ] **Step 2: 증거가 완전한 IMP만 완료 표시**

Exact change in `docs/AfterMuse_MVP_Implementation_Plan_v5.md`:

```diff
-- [ ] **IMP-001 — Django 프로젝트 Bootstrap**
+- [x] **IMP-001 — Django 프로젝트 Bootstrap**
-- [ ] **IMP-002 — PostgreSQL 개발 환경 구성**
+- [x] **IMP-002 — PostgreSQL 개발 환경 구성**
-- [ ] **IMP-003 — 테스트 / 품질 명령 구성**
+- [x] **IMP-003 — 테스트 / 품질 명령 구성**
-- [ ] **IMP-004 — 공통 Layout + HTMX/Alpine 토대**
+- [x] **IMP-004 — 공통 Layout + HTMX/Alpine 토대**
```

Expected: Task 1~5가 모두 성공한 경우 네 줄만 `[x]`로 바뀐다. 실패한 IMP가 있으면 해당 줄은 `[ ]`로 유지한다.

- [ ] **Step 3: README와 CHANGELOG의 사실성 확인**

Run:

```powershell
rg -n "현재 구현 상태|Python 3\.14|Django 6\.1|PostgreSQL 18|scripts/verify.py|HTMX 2\.0\.10|Alpine.js CSP 3\.17\.1" README.md CHANGELOG.md
```

Expected: 현재 구현과 실행 절차가 이미 정확하면 수정하지 않는다. 검증 결과와 모순되는 문장만 수술적으로 고치며 새로운 기능 설명은 추가하지 않는다.

- [ ] **Step 4: 문서 정합성과 diff 검사**

Run:

```powershell
rg -n "IMP-001|IMP-002|IMP-003|IMP-004" docs/AfterMuse_MVP_Implementation_Plan_v5.md
git diff --check
git diff -- docs/AfterMuse_MVP_Implementation_Plan_v5.md docs/superpowers/specs/2026-09-01-day-01-completion-design.md docs/superpowers/plans/2026-09-01-day-01-completion.md README.md CHANGELOG.md
```

Expected: 네 IMP의 상태가 증거와 일치하고 whitespace 오류 또는 범위 밖 diff가 없다.

- [ ] **Step 5: 최종 전체 검증**

Run:

```powershell
uv run python scripts/verify.py
```

Expected: Django system check, Ruff format check, Ruff lint와 전체 pytest suite가 모두 통과한다.

- [ ] **Step 6: 변경 보고 후 커밋 승인 요청**

Report:

```text
완료: IMP-001, IMP-002, IMP-003, IMP-004
검증: Python/Django/PostgreSQL versions, 빈 DB migration, scripts/verify.py, Desktop/Mobile, HTMX, Alpine, CSP
변경: Day 01 체크박스와 승인된 계획 문서
잔여 위험: 자동화하지 않은 browser 수동 검증의 범위
```

Expected: 커밋 대상과 검증 증거를 사용자에게 제시하고 승인을 기다린다.

- [ ] **Step 7: 승인된 경우에만 원자적 커밋 생성**

Run only after approval:

```powershell
git add docs/AfterMuse_MVP_Implementation_Plan_v5.md docs/superpowers/specs/2026-09-01-day-01-completion-design.md docs/superpowers/plans/2026-09-01-day-01-completion.md
git commit -m "docs: Day 01 구현 완료 근거 정리"
```

Expected: Day 01 완료 상태와 그 근거가 하나의 문서 커밋에 포함된다. README 또는 CHANGELOG를 실제로 수정했다면 승인 전에 staging 목록에 명시하고 같은 커밋에 포함한다.
