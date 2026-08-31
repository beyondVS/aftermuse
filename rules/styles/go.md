# Go Coding Style Guide (Go 스타일 및 컨벤션 지침)

Effective Go 및 Google Go Style Guide 기반의 관용적(Idiomatic) Go 코딩 규격입니다. 기존 프로젝트에서는 설정 파일과 관례를 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 `gofmt`·linter 설정으로 기계적으로 확정하십시오.

---

## 🐹 1. 포맷팅 및 자동화 (Formatting)

- **`gofmt` 필수 적용**: 모든 Go 소스 코드는 빌드/커밋 전 반드시 `gofmt` (또는 `go fmt`)를 통해 자동 포맷팅되어야 합니다.
- **들여쓰기**: `gofmt` 표준에 따라 탭(Tab) 문자를 사용합니다.

---

## 🏷️ 2. 명명 규칙 (Naming Conventions)

- **`MixedCaps` 명명법**: 언더스코어(`_`)를 사용하지 않고 `MixedCaps` (Public) 또는 `mixedCaps` (Private) 형태를 적용합니다.
- **공개/비공개 (Exported vs Unexported)**:
  - 대문자로 시작하는 식별자는 외부로 공개(Exported)됩니다.
  - 소문자로 시작하는 식별자는 패키지 내부 전용(Unexported)입니다.
- **패키지 명**: 단수형의 명료하고 짧은 소문자 단어를 사용하십시오.
- **Getter 메서드**: Getter에 `Get` 접두사를 붙이지 않습니다. (`owner` 필드의 getter -> `Owner()`)
- **단일 메서드 인터페이스**: 1개의 메서드만 갖는 인터페이스는 메서드명에 `-er` 접미사를 붙입니다. (예: `Reader`, `Writer`)

---

## 🔀 3. 제어 구조 및 반환값 (Control Structures & Functions)

- **`if` 문 조건식**: 조건식 주변에 괄호`()`를 사용하지 않으며 초기화 구문(`if err := file.Chmod(0664); err != nil`)을 적극 활용합니다.
- **다중 반환 (Multiple Returns)**: 결과값과 에러(`value, err`)를 함께 반환하는 방식을 관용 표준으로 사용합니다.
- **`defer` 활용**: 파일 닫기, 락 해제 등 자원 정리 작업은 자원 할당 직후 `defer` 문을 사용해 지연 실행을 명시하십시오.

---

## 📦 4. 자원 관리 및 에러 처리 (Data & Errors)

- **`new` vs `make` 구분**:
  - `new(T)`: 메모리를 0으로 초기화 할당하고 포인터(`*T`)를 반환합니다.
  - `make(T, ...)`: Slice, Map, Channel 타입 전용으로, 초기화된 실체 값(`T`)을 반환합니다.
- **Map 키 존재 검사**: "comma ok" 관용구(`value, ok := myMap[key]`)를 이용해 안전하게 키 존재 여부를 확인합니다.
- **명시적 에러 검사**: 에러를 빈 식별자(`_`)로 묵살하지 말고 항상 `if err != nil`로 처리하십시오.
- **`panic` 자제**: 일반적인 에러 상황에서 `panic`을 발생시키지 말고 `error` 객체를 반환하십시오.

---

## 🔄 5. 동시성 (Concurrency Protocol)

- **동시성 철학**: *"메모리를 공유하여 통신하지 말고, 통신을 통해 메모리를 공유하라 (Do not communicate by sharing memory; instead, share memory by communicating)."*
- **Goroutine & Channel**: 경량 스레드 고루틴(`go fn()`)과 채널(`chan`)을 활용해 안전하게 데이터를 주고받으십시오.

---

## 💬 6. 주석 및 문서화 (Documentation)

- 문서화 대상과 설명 내용은 Core의 코드 문서화 및 주석 기준을 따릅니다.
- exported package, type, function, method, variable 및 constant의 documentation comment는 해당 식별자 이름으로 시작하는 완전한 문장으로 작성합니다.
- `gofmt`, `go vet` 및 소비 프로젝트가 채택한 linter가 검사하는 comment 형식은 해당 설정에 연결합니다.
