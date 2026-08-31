# Python Packaging Rules (Python & PyPI 생태계 패키징 규칙)

Python 생태계(PyPI, uv, pyproject.toml)의 라이브러리 및 패키지 개발/배포에 적용되는 표준 규칙입니다.

---

## ⚡ 1. 현대적 패키징 및 환경 관리 표준 (uv 중심)

- **uv 모던 도구 추천 및 프로젝트 도구 존중**: 가상환경 구축, 패키지 설치, 의존성 동기화 및 Lockfile 관리는 `uv`를 기본 추천 도구로 활용하되, 기존 프로젝트에 `poetry`, `pip/venv`, `conda` 등 지정된 패키지 도구가 존재하는 경우 해당 도구를 존중하여 구동하십시오. (`uv init`, `uv add`, `uv sync`)
- **PEP 621 pyproject.toml 명세**: Legacy `setup.py` 대신 PEP 621 규격을 준수하는 `pyproject.toml`을 단일 메타데이터 매니페스트로 사용하십시오.
- **Lockfile 기반 배포 재현성 보장**: 애플리케이션 및 서비스 배포 시 `uv.lock` 파일의 100% 버전 동결을 보장하기 위해 배포 환경에서는 `uv sync --locked` 명령으로만 환경을 동기화합니다.
- **의존성 그룹 분류 표준 (Dependency Grouping)**:
  - **프로덕션 런타임 의존성 (`[project.dependencies]`)**: 서비스 구동 및 SDK 실행 시 필수적인 런타임 패키지만 선언합니다.
  - **개발/테스트 전용 의존성 (`[dependency-groups.dev]`)**: pytest, ruff, mypy 등 개발 전용 도구는 프로덕션 배포 경량화를 위해 반드시 dev 그룹으로 격리 선언하십시오.
- **빌드 백엔드 명시**: `[build-system]` 섹션에 빌드 툴(hatchling, flit_core, setuptools 등)을 명확히 정의하십시오.

---

## 🛡️ 2. 의존성 범위 지정 규격 (Dependency Versioning)

- **마이너 변경 리스크 방어 (`~=` 우선 사용)**:
  마이너 버전 업데이트 시 발생할 수 있는 비호환 변경 및 동작 변경을 방지하기 위해, 의존성 범위 지정 시 Tilde 연산자(`~=`) 사용을 권장합니다.
  - 예: `~= 2.4.0` (`>= 2.4.0, < 2.5.0` 범위로 동일 마이너 내 안전한 버그 수정 패치만 허용)
- **`0.x` 미성숙 패키지 엄격 통제**:
  `0.x.y` 버전대 패키지는 마이너 변경 시 파괴적 변경(Breaking Change) 발생 위험이 높으므로 `~= 0.8.1` (`< 0.9.0`)과 같이 마이너 버전을 엄격히 고정(Tight Pinning)하십시오.
- **라이브러리 패키지 선언**:
  공용 라이브러리/SDK 개발 시에는 타 프로젝트와의 충돌 방지를 위해 명시적 하한선 및 상한선 범위(`>= 2.0.0, < 3.0.0`)를 지정하되, 과도하게 단일 버전(`==`)으로 묶는 것은 지양합니다.

---

## 🏷️ 3. Public API 캡슐화 및 타입 지원 (PEP 561)

- **`__all__`을 통한 공개 제어**: 패키지 `__init__.py` 파일에 `__all__` 리스트를 명시하여 외부에 공개할 Public 클래스/함수를 명확히 캡슐화하십시오.
- **PEP 561 Type Marker (`py.typed`)**: 타입 정보를 제공하는 배포 라이브러리/SDK는 mypy, pyright 등이 타입 힌팅을 인식할 수 있도록 패키지 루트에 `py.typed` 마커 파일을 포함하십시오. 외부에 배포하지 않는 애플리케이션에는 적용하지 않습니다.
- **Docstring 및 Type Annotations**: 배포 패키지의 public 범위는 export와 packaging 설정으로 확정하고, Core의 계약 문서화 기준 및 Python style의 Google-style docstring 형식을 적용합니다. Public API에는 소비자가 사용할 수 있는 Type Annotations를 제공합니다.
- **Docstring 언어**: Core의 사용자 소통 및 문서화 언어 규칙을 따릅니다.

---

## 🧪 4. 패키지 검증 및 보안 감사 (twine, audit & testing)

- **의존성 취약점 보안 스캔 (Security Audit)**: CI/CD 및 배포 검증 시 `uv audit` 또는 `pip-audit` 명령을 실행하여 CVE 보안 취약점이 있는 의존성 유입 여부를 정기 감사하십시오.
- **배포 검증**: PyPI 업로드 전 `build` 툴로 파이프라인 산출물(wheel, sdist)을 생성하고 `twine check`를 통해 메타데이터 및 README 렌더링 정상 여부를 확인하십시오.
- **Hypothesis 기반 속성 기반 테스트 (Property-based Testing)**: 복잡한 데이터 조작 또는 라이브러리 검증 시 단순 픽스처를 넘어 경계값(Edge Cases) 및 불변식(Invariant) 탐색을 위한 Hypothesis 테스트 도입을 적극 권장합니다.

---

## 📚 5. 외부 생태계 & 레퍼런스 (Ecosystem & References)

- **`python-ecosystem-kb` 스킬**: 파이썬 모던 툴체인, 서드파티 라이브러리 추천 및 생태계 조회가 필요한 경우 `python-ecosystem-kb` 스킬을 활성화하여 온디맨드로 실시간 조회하십시오.
