# C++ Coding Style Guide (C++ 스타일 및 컨벤션 지침)

Google C++ Style Guide 및 C++20 베스트 프랙티스 기반의 스타일 규격입니다.
기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🏷️ 1. 명명 규칙 (Naming Conventions)

- **파일 명**: 소문자와 밑줄(`_`) 또는 하이픈(`-`) 사용. 헤더는 `.h`, 소스는 `.cc` 확장자 사용.
- **클래스 / 구조체 / 에넘**: `PascalCase` (`MyClass`, `MyEnum`)
- **변수**: `snake_case` (`my_var`). 클래스 멤버 변수는 끝에 밑줄(`my_member_`) 작성.
- **상수 / 에넘 요소**: `k` + `PascalCase` (`kDays`, `kOk`)
- **함수 / 메서드**: `PascalCase` (`GetValue()`)
- **접근자 / 변경자 (Accessors/Mutators)**: `snake_case` (`count()`, `set_count(v)`)
- **매크로**: `ALL_CAPS` (`MY_MACRO`)

---

## 📁 2. 헤더 파일 및 혜택 관리 (Header Files)

- **Header Guard**: `#define <PROJECT>_<PATH>_<FILE>_H_` 형태 사용.
- **포워드 선언 금지**: Include 헤더 파일을 직접 사용하고, 특히 `std::` 심볼에 대한 전방 선언(Forward Declaration)은 엄격히 금지합니다.
- **임포트 순서**: 
  1. 관련 헤더 (`foo.h`)
  2. C 시스템 헤더 (`<unistd.h>`)
  3. C++ 표준 라이브러리 (`<vector>`)
  4. 기타 서드파티 라이브러리
  5. 프로젝트 내부 헤더

---

## ⚙️ 3. 클래스 및 기능 설계 (Classes & Scoping)

- **`explicit` 키워드**: 단일 인자 생성자 및 변환 연산자에는 `explicit`을 필수 지정하십시오.
- **Copy/Move 명시**: Copy/Move 생성자 및 대입 연산자는 `= default` 또는 `= delete`를 사용하여 명시적으로 제어하십시오.
- **상속 규칙**: `public` 상속만 사용하고 컴포지션(Composition)을 상속보다 우선시하십시오. 오버라이드 시 `override` 키워드를 사용합니다.
- **스마트 포인터**: 소유권 표현 시 raw pointer 대신 `std::unique_ptr` 또는 `std::shared_ptr`을 적극 사용하십시오.
- **`using namespace` 금지**: 전역 범위에서의 `using namespace std;` 구문 사용을 금지합니다.
- **`nullptr` 구문**: `NULL` 또는 `0` 대신 항상 `nullptr`을 사용하십시오.

---

## 🛠️ 4. 포맷팅 및 예외 처리 (Formatting & Safety)

- **들여쓰기 및 한 줄 길이**: 들여쓰기는 프로젝트 formatter 설정과 관례를 따르며, 별도 설정이 없으면 2공백을 사용합니다.
  줄 길이는 formatter/linter 설정, 기존 관례, 기본값 80자 순으로 적용합니다.
- **예외 처리 (Exceptions)**: C++ 구문 내 예외(Exceptions) 발생 기능을 지양하고 에러 코드 또는 `std::optional` / `absl::Status` 기반 처리를 권장합니다.

---

## 💬 5. 주석 및 문서화 (Documentation)

- 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따릅니다.
- public header의 계약 문서는 프로젝트가 채택한 Doxygen 호환 documentation comment 형식(`///` 또는 `/** ... */`)을 일관되게 사용합니다.
- `@param`, `@return`, `@throws` 등의 command는 실제로 설명할 계약과 프로젝트 도구 설정이 있을 때만 작성합니다.
