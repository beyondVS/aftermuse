# Python Coding Style Guide (Python 스타일 및 컨벤션 지침)

Google Python Style Guide 및 현대 파이썬 코딩 베스트 프랙티스 기반의 스타일 규격입니다.
기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🐍 1. 언어 활용 규칙 (Language Rules)

- **형식 검사 및 린팅 (Linting)**: `ruff` 또는 `pylint`를 활용해 문법 및 스타일 오류를 조기에 탐지하십시오.
- **순환 복잡도 통제 (McCabe Complexity Limit)**:
  프로젝트에 설정된 C901 또는 복잡도 임계값을 따릅니다.
  신규 프로젝트의 기본·권고값은 `max-complexity = 10`이며, 초과 시 가독성·테스트 가능성을 점검하거나 사유를 문서화한 예외인지 확인하십시오.
- **모듈 임포트 규칙 (Imports)**:
  - 프로젝트 도구와 기존 관례가 정한 형식을 우선하며, 직접 심볼 import도 가독성과 충돌 위험을 고려해 사용할 수 있습니다.
  - 임포트는 **표준 라이브러리**, **서드파티 패키지**, **자체 프로젝트 모듈** 순서로 그룹화하여 빈 줄로 구분하십시오.
- **예외 처리 (Exceptions)**:
  - 파이썬 내장 예외 클래스 또는 명시적 커스텀 예외를 사용하고, 예외 종류를 지정하지 않는 bare `except:` 구문 사용을 엄격히 금지합니다.
- **전역 상태 제어 (Global State)**:
  - 가변(Mutable) 전역 상태 사용을 지양하십시오. 모듈 수준의 상수는 허용되며 `ALL_CAPS_WITH_UNDERSCORES` 명명 규칙을 적용합니다.
- **디폴트 인자 값 (Default Arguments)**:
  - 함수의 기본 인자 값으로 리스트(`[]`), 딕셔너리(`{}`) 등 가변 객체를 절대 직접 지정하지 마십시오. (`None`을 디폴트로 사용 후 내부 동적 할당)
- **조건문 진위 평가 (Truth Value Testing)**:
  - 빈 리스트나 문자열 체크 시 `if not my_list:`와 같은 암묵적 거짓 평가를 적극 활용하십시오.
  - `None` 검사 시에는 반드시 `if foo is None:` 또는 `if foo is not None:`을 사용하십시오.
- **타입 힌팅 (Type Annotations)**:
  - 프로젝트 type checker의 적용 범위와 public export 계약에는 annotation을 작성합니다.
    framework callback·override 등은 프로젝트 설정과 framework 관례가 허용하는 예외를 따릅니다.

---

## 🎨 2. 코드 스타일 및 포맷팅 (Style Rules)

- **들여쓰기 (Indentation)**: 탭(Tab) 사용을 금지하고, 4개의 공백(Spaces)을 사용합니다.
- **라인 길이 (Line Length)**: formatter/linter 설정, 기존 관례, 기본값 88자 순으로 적용합니다.
- **빈 줄 (Blank Lines)**: 최상위 클래스 및 함수 정의 사이에는 2줄, 클래스 내부 메서드 정의 사이에는 1줄의 빈 줄을 둡니다.
- **문자열 포맷팅 (Strings)**:
  - 동적 문자열 구성 시 `f-string`을 우선적으로 사용합니다.
  - 따옴표 표기법은 팀 및 프로젝트 내에서 일관성을 유지하십시오.
- **Docstring 형식**:
  - 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따르고, Python에서는 Google-style docstring과 `"""triple double quotes"""`를 사용합니다.
  - 첫 줄에 간결한 요약을 작성하고, 필요한 경우 빈 줄 뒤에 상세 설명을 이어서 작성합니다.
  - `Args:`, `Returns:`, `Raises:`, `Yields:` 구획은 실제로 설명할 내용이 있을 때만 작성하며 빈 구획을 만들지 않습니다.
  - 타입 힌트와 식별자 이름을 그대로 반복하는 설명을 작성하지 않습니다.
- **공개 범위와 문서화 판단**:
  - Python에서 선행 밑줄이 없는 모듈·클래스·함수·메서드는 public, `_name`은 internal/private이라는 명명 관례를 따릅니다.
    이 visibility 관례는 Docstring 필요성을 결정하지 않으며, 실제 범위는 package export, framework 규칙 및 소비 프로젝트 설정으로 확정합니다.

    예를 들어 `_build_url`이 URL 정책을 조합하거나 외부 요청 형식을 결정하면 문서화하고, `_parse_item`이 입력을 변환·매핑하거나 `_parse_date`가 허용 형식·오류 정책을 적용하면 문서화합니다.
    반면 `_get_name`처럼 이름과 타입만으로 동작과 계약이 자명한 단순 getter는 생략할 수 있습니다.
- **Docstring 및 주석 언어**:
  - Core의 사용자 소통 및 문서화 언어 규칙을 따릅니다.
  - `Args`, `Returns`, `Raises`와 같은 표준 섹션명 및 기술 고유명사는 영어를 사용할 수 있습니다.
- **검사 및 예외**:
  - 문서화 필요성, Why 주석, 처리 문맥 전환 및 구조 개선 우선순위는 Core 기준을 따릅니다.
  - framework override의 문서화 예외는 해당 framework 규칙 또는 소비 프로젝트 설정에서 결정하며, 기존 프로젝트의 설정과 일관된 관례를 범용 기본값보다 우선합니다.
  - Ruff를 사용하는 프로젝트에서는 pydocstyle `D` 규칙과 `lint.pydocstyle.convention` 설정을 검토하되, 활성화할 규칙은 소비 프로젝트가 정합니다.
  - 해결이 필요한 작업에는 프로젝트가 채택한 TODO 형식을 사용합니다. 별도 관례가 없으면 `TODO(username): 설명` 형식을 사용할 수 있습니다.

---

## 🏷️ 3. 명명 규칙 (Naming Conventions)

- **모듈 / 패키지 / 함수 / 변수 / 메서드**: `snake_case`
- **클래스 / 예외 클래스**: `PascalCase`
- **전역 상수**: `ALL_CAPS_WITH_UNDERSCORES`
- **내부 전용 멤버 (Internal Use)**: 캡슐화가 필요한 모듈/클래스 내부 멤버는 단일 선행 밑줄(`_private_var`)을 부여합니다.

---

## 🚀 4. 메인 엔트리포인트 (Main Protocol)

- 여러 단계를 수행하거나 테스트 가능한 CLI 진입점에는 `main()` 함수와 `if __name__ == '__main__':` 호출을 권장합니다.
  단순 스크립트는 프로젝트 관례에 맞는 구조를 사용합니다.
