# JavaScript Coding Style Guide (JavaScript 스타일 및 컨벤션 지침)

Google JavaScript Style Guide 및 ES6+ 베스트 프랙티스 기반의 스타일 규격입니다. 기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🟡 1. 소스 파일 기본 및 구조 (Source Files)

- **인코딩 & 공백**: UTF-8 인코딩을 사용하며 탭 대신 2개의 공백(Spaces)으로 들여쓰기를 수행합니다.
- **모듈 시스템**: ES6 모듈 (`import`/`export`) 표준을 준수하십시오.
- **내보내기 규칙**: Named Export (`export { MyClass };`) 방식을 사용하고 `default export` 사용을 지양합니다.

---

## ⚙️ 2. 코드 포맷팅 (Formatting)

- **중괄호 (Braces)**: `if`, `for`, `while` 등 모든 제어문은 1줄짜리 블록이라도 중괄호를 필수 사용하며 K&R 스타일("Egyptian brackets")을 적용합니다.
- **세미콜론 (Semicolons)**: Automatic Semicolon Insertion(ASI)에 의존하지 말고 모든 문장 끝에 세미콜론(`;`)을 명시하십시오.
- **라인 길이**: 80자를 기준으로 작성하되, 연장 라인은 4공백 이상 들여쓰기를 적용합니다.

---

## ⚡ 3. 언어 기능 규칙 (Language Features)

- **변수 선언**: `var` 사용을 완전 금지하고 `const`를 기본으로 선언하며, 값 재할당이 필요한 변수에만 `let`을 사용하십시오.
- **배열 / 객체 리터럴**:
  - Trailing comma(마지막 요소 뒤 쉼표)를 사용합니다.
  - `new Array()`, `new Object()` 생성자 대신 리터럴 표기법(`[]`, `{}`)을 사용하십시오.
- **화살표 함수**: 콜백 함수 및 중첩 함수 작성 시 `this` 바인딩 보존을 위해 화살표 함수(`() => {}`)를 권장합니다.
- **Getter/Setter 자제**: JS 개체 속성 접근자(`get name()`) 대신 명시적 메서드 호출을 권장합니다.
- **문자열 표기**: 기본적으로 단일 따옴표(`'`)를 사용하고, 보간 또는 템플릿 처리 시 템플릿 리터럴(백틱 `` ` ``)을 활용하십시오.
- **동등성 검사**: 반드시 엄격한 동등성 연산자(`===` / `!==`)를 사용하십시오.

---

## 🚫 4. 금지 기능 (Disallowed Features)

- `with` 구문 사용 금지.
- `eval()` 또는 `Function(...string)` 사용 금지.
- 기본 표준 내장 객체 프로토타입 변형 (`Array.prototype.foo = ...`) 금지.

---

## 🏷️ 5. 명명 규칙 (Naming)

- **클래스 / 타입**: `UpperCamelCase`
- **함수 / 메서드 / 변수 / 파라미터**: `lowerCamelCase`
- **전역 상수**: `CONSTANT_CASE` (모두 대문자 + 밑줄)

---

## 💬 6. 주석 및 문서화 (Documentation)

- 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따릅니다.
- public 계약의 documentation comment에는 프로젝트가 채택한 JSDoc의 `/** ... */` 형식을 사용하고, 매개변수·반환값·예외 tag는 실제로 설명할 계약이 있을 때만 작성합니다.
- TypeScript declaration이나 별도 schema가 계약을 제공하는 프로젝트에서는 동일 정보를 장문으로 반복하지 않습니다.
