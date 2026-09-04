# Python Packaging Rules (Python & PyPI 생태계 패키징 규칙)

Python 생태계(PyPI, uv, pyproject.toml)의 라이브러리 및 패키지 개발/배포에 적용되는 표준 규칙입니다.

---

## ⚡ 1. 현대적 패키징 및 환경 관리 표준

- **패키지 매니저 우선 선택**:
  저장소의 설정과 기존 컨벤션에 맞는 패키지 매니저를 먼저 선택하고, 그 매니저가 정한 lockfile과 locked/frozen 설치 명령으로 재현 가능한 환경을 구성하십시오.
  기존 프로젝트의 `poetry`, `pip/venv`, `conda`, `uv` 등 도구와 계약이 우선합니다.
- **PEP 621 pyproject.toml 명세**: Legacy `setup.py` 대신 PEP 621 규격을 준수하는 `pyproject.toml`을 단일 메타데이터 매니페스트로 사용하십시오.
- **Lockfile 기반 배포 재현성 보장**: 애플리케이션 및 서비스는 선택된 매니저의 lockfile을 CI/배포에서 locked 또는 frozen 방식으로 사용하여 의존성 변동을 방지하십시오.
- **의존성 그룹 분류 표준 (Dependency Grouping)**:
  - **프로덕션 런타임 의존성 (`[project.dependencies]`)**: 서비스 구동 및 SDK 실행 시 필수적인 런타임 패키지만 선언합니다.
  - **개발/테스트 전용 의존성**: pytest, ruff, mypy 등은 채택한 빌드·패키징 도구가 제공하는 그룹/extra 구성을 따르되 프로덕션 런타임과 분리하십시오.
- **빌드 백엔드 명시**: `[build-system]` 섹션에 빌드 툴(hatchling, flit_core, setuptools 등)을 명확히 정의하십시오.

---

## 🛡️ 2. 의존성 범위 지정 규격 (Dependency Versioning)

- **호환성 정책 기반 버전 범위**: 애플리케이션/라이브러리 구분, 지원 Python 런타임, 호환성 정책과 보안 업데이트 정책을 근거로 범위를 정하십시오.
  `~=`, 상한선, tight pin은 해당 위험을 줄이는 경우에만 선택합니다.
- **라이브러리 패키지 선언**:
  공용 라이브러리/SDK 개발 시에는 타 프로젝트와의 충돌 방지를 위해 명시적 하한선 및 상한선 범위(`>= 2.0.0, < 3.0.0`)를 지정하되, 과도하게 단일 버전(`==`)으로 묶는 것은 지양합니다.

---

## 🏷️ 3. Public API 캡슐화 및 타입 지원 (PEP 561)

- **공개 API 경계**: 패키지가 명시적 export 경계를 제공해야 할 때만 `__all__`을 사용하고, 그 외에는 기존 공개 계약과 패키징 설정을 따르십시오.
- **PEP 561 Type Marker (`py.typed`)**:
  타입 정보를 제공하는 배포 라이브러리/SDK는 mypy, pyright 등이 타입 힌팅을 인식할 수 있도록 패키지 루트에 `py.typed` 마커 파일을 포함하십시오.
  외부에 배포하지 않는 애플리케이션에는 적용하지 않습니다.
- **Docstring 및 Type Annotations**:
  배포 패키지의 public 범위는 export와 packaging 설정으로 확정하고, Core의 계약 문서화 기준 및 Python style의 Google-style docstring 형식을 적용합니다.
  Public API에는 소비자가 사용할 수 있는 Type Annotations를 제공합니다.
- **Docstring 언어**: Core의 사용자 소통 및 문서화 언어 규칙을 따릅니다.

---

## 🧪 4. 패키지 검증 및 보안 감사 (twine, audit & testing)

- **의존성 취약점 보안 스캔 (Security Audit)**: CI/CD 및 배포 검증 시 `uv audit` 또는 `pip-audit` 명령을 실행하여 CVE 보안 취약점이 있는 의존성 유입 여부를 정기 감사하십시오.
- **배포 검증**: PyPI 업로드 전 `build` 툴로 파이프라인 산출물(wheel, sdist)을 생성하고 `twine check`를 통해 메타데이터 및 README 렌더링 정상 여부를 확인하십시오.
- **속성 기반 테스트**: 속성/불변식과 생성 사례가 실제 경계 위험을 포착할 때 Hypothesis 도입을 고려하십시오.

---

## 📚 5. 외부 생태계 & 레퍼런스 (Ecosystem & References)

- **`python-ecosystem-kb` 스킬**: 파이썬 모던 툴체인, 서드파티 라이브러리 추천 및 생태계 조회가 필요한 경우 `python-ecosystem-kb` 스킬을 활성화하여 온디맨드로 실시간 조회하십시오.
