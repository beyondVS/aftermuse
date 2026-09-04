# Dart / Flutter Coding Style Guide (Dart 스타일 및 컨벤션 지침)

Effective Dart 및 Google Dart Style Guide 기반의 관용적 Dart/Flutter 코딩 규격입니다.
기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🏷️ 1. 명명 규칙 (Naming Conventions)

- **`UpperCamelCase`**: 클래스, 믹스인(Mixin), 에넘(Enum), typedef, 타입 파라미터
- **`lowercase_with_underscores`**: 라이브러리, 패키지, 소스 파일명, 디렉터리명
- **`lowerCamelCase`**: 변수, 함수, 메서드, 파라미터, 클래스 멤버 속성

---

## 📐 2. 코드 스타일 및 포맷팅 (Formatting)

- **`dart format` 적용**: 모든 Dart 코드는 `dart format` 도구로 자동 스타일 정렬하십시오.
- **Trailing Comma (마지막 쉼표)**: Flutter 위젯 트리 및 인자 목록 작성 시 줄바꿈 자동 포맷팅을 위해 트레일링 쉼표를 적극 부여하십시오.

---

## ⚡ 3. 관용적 Dart 구문 (Effective Dart)

- **Null Safety**: 널 안전성(Sound Null Safety) 규격을 준수하고 `?`, `!`, `late` 키워드를 안전하게 지정하십시오.
- **`const` 위젯 선언**: Flutter 위젯 리빌드 최소화를 위해 재렌더링이 불필요한 위젯에 `const` 키워드를 반드시 부착하십시오.
- **컬렉션 리터럴 & 카스케이딩 연산자**:
  - `[]`, `{}` 리터럴 사용
  - 객체 체이닝 시 카스케이딩 연산자(`..`) 활용

---

## 💬 4. 주석 및 문서화 (Documentation)

- 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따릅니다.
- public library, type 및 member의 documentation comment에는 Dart의 `///` 형식을 사용하고, API 식별자는 필요할 때 대괄호 링크 형식(`[Foo]`)으로 참조합니다.
- `dart doc`과 analyzer가 확인하는 형식 및 public 범위는 소비 프로젝트 설정에 연결합니다.
