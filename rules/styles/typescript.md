# TypeScript Coding Style Guide (TypeScript 스타일 및 컨벤션 지침)

Google TypeScript Style Guide 및 현대 TypeScript 코딩 베스트 프랙티스 기반의 스타일 규격입니다. 기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🔷 1. 언어 기능 사용 규칙 (Language Features)

- **변수 선언**: `var` 사용을 금지하고 `const` 또는 `let`을 사용하십시오. 불변성이 유지되는 모든 변수에는 `const`를 기본으로 적용합니다.
- **모듈 시스템**: ES6 모듈 (`import`/`export`) 규격을 준수하십시오. TypeScript 고유의 `namespace` 구문 사용은 금지됩니다.
- **모듈 내보내기 (Exports)**: Named export (`export { MyClass };`) 방식을 사용하고 `default export` 사용을 지양합니다.
- **클래스 및 접근 제어자**:
  - `#private` 필드 대신 TypeScript 고유의 `private` 접근 수식어를 사용하십시오.
  - 생성자 외부에서 재할당되지 않는 속성에는 `readonly`를 지정합니다.
  - 기본값이 public이므로 불필요한 `public` 키워드는 생략하고, `private` 또는 `protected`로 접근 권한을 명확히 제한하십시오.
- **동등성 비교 (Equality)**: 엄격한 동등성 연산자(`===`, `!==`)만을 사용하십시오. (`==`, `!=` 금지)
- **타입 단언 지양 (Type Assertions)**:
  - `x as SomeType` 또는 Non-nullability assertion (`y!`)의 사용을 가급적 지양하십시오. 부득이하게 사용할 경우 주석으로 정당성을 명시해야 합니다.

---

## 🚫 2. 금지 패턴 (Disallowed Features)

- **`any` 타입 금지**: `any` 타입 사용을 엄격히 제한하고, 알 수 없는 타입에는 `unknown` 또는 구체적인 유니온 타입을 명시하십시오.
- **원시 타입 래퍼 객체 금지**: `String`, `Boolean`, `Number` 등 래퍼 클래스를 직접 인스턴스화하지 마십시오. (원시 타입 `string`, `boolean`, `number` 사용)
- **세미콜론 정책**: 세미콜론 사용 여부는 프로젝트 formatter·linter 설정으로 일관되게 강제하십시오. 신규 프로젝트의 기본값은 명시적 세미콜론 사용입니다.
- **`const enum` 금지**: 일반 `enum` 또는 const 객체 맵(`as const`)을 활용하십시오.
- **동적 코드 실행 금지**: `eval()` 및 `Function(...string)` 사용을 엄격히 금지합니다.

---

## 🏷️ 3. 명명 규칙 (Naming Conventions)

- **클래스 / 인터페이스 / 타입 / 에넘 / 데코레이터**: `UpperCamelCase` (PascalCase)
- **변수 / 매개변수 / 함수 / 메서드 / 속성**: `lowerCamelCase`
- **전역 상수 및 에넘 값**: `CONSTANT_CASE`
- **식별자 접두사/접미사 밑줄 금지**: private 멤버를 포함해 변수명 앞뒤에 `_`를 붙이지 마십시오. (접근 제어자 `private` 사용)

---

## 📐 4. 타입 시스템 활용 (Type System)

- **타입 추론 활용**: 명확하고 자명한 타입은 선언을 생략하고 타입 추론(Type Inference)에 의존하여 코드를 간결하게 유지하십시오.
- **옵셔널 필드 vs `| undefined`**: 타입 선언 시 `| undefined`를 결합하는 대신 옵셔널 표기법(`?`)을 권장합니다.
- **배열 타입 명세**: 단일 타입 배열은 `T[]`를 사용하고, 복합 유니온 타입 배열은 `Array<T | U>` 형태를 사용하십시오.
- **빈 객체 타입 (`{}`) 금지**: `{}` 대신 `unknown`, `Record<string, unknown>`, 또는 `object`를 사용하십시오.

---

## 💬 5. 주석 및 문서화 (Documentation)

- 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따릅니다.
- **TSDoc/JSDoc 형식**: public 계약을 문서화할 때 프로젝트가 채택한 TSDoc 또는 JSDoc의 `/** ... */` 형태를 사용합니다.
- **중복 타입 지정 금지**: TypeScript 타입 시스템이 이미 표현한 타입을 `@param {string}`처럼 documentation comment에 반복하지 않습니다. 프로젝트 도구가 요구하는 tag와 형식은 해당 설정을 따릅니다.
