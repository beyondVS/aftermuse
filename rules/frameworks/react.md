# React.js Architecture & Development Rules (React.js 특화 개발 규칙)

React.js (Single Page Application, Vite) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. 컴포넌트 아키텍처 및 폴더 구조 (Component Architecture)

- **단일 책임 컴포넌트 (Single Responsibility)**:
  - 하나의 컴포넌트는 하나의 명확한 역할만 수행하도록 가급적 작게 작성하십시오.
  - UI 복잡성이나 JSX 템플릿 구조상 컴포넌트 크기가 길어지는 경우, 상태 처리 및 비즈니스 로직을 우선적으로 커스텀 훅(`use[Feature]`)이나 하위 UI 컴포넌트로 분리하여 가독성과 응집도를 유지하십시오.
- **도메인 중심 폴더 구조**:
  - `components/ui/` (공통 Atomic UI 컴포넌트), `features/[domain]/` (도메인 특화 컴포넌트 및 로직), `hooks/`, `services/`로 체계적으로 분리하십시오.
- **Container / Presentational 분리**:
  - 비즈니스 로직 및 API 호출은 커스텀 훅(`use[Feature]`)으로 추상화하고, UI 컴포넌트는 순수 렌더링에 집중하십시오.

---

## 🔄 2. 상태 관리 규칙 (State Management)

- **로컬 상태 최우선**:
  - 전역 상태에 무분별하게 상태를 올리지 마십시오. 컴포넌트 내부 상태(`useState`, `useReducer`)로 해결할 수 있다면 로컬 상태를 유지하십시오.
- **클라이언트 전역 상태 (Zustand / Jotai)**:
  - 전역 UI 상태나 세션 상태는 lightweight 상태 관리 도구(Zustand 등)를 활용하고, 불필요한 리렌더링을 방지하기 위해 Selector 함수를 명시하여 구독하십시오.
- **서버 상태 분리 (TanStack Query)**:
  - API 비동기 데이터는 `useState` + `useEffect` 대신 TanStack Query (React Query)를 사용하여 캐싱, Stale 시간 및 자동 재요청을 관리하십시오.

---

## ⚡ 3. 렌더링 성능 최적화 (Performance Optimization)

- **부작용 제어 (`useEffect` 최소화)**:
  - 파생된 상태(Derived State)를 계산하기 위해 `useEffect`를 사용하지 마십시오. 렌더링 시점에 직접 계산하거나 `useMemo`를 활용하십시오.
- **연속 이벤트 처리 시 `useState` 남용 지양**:
  - 마우스 위치, 스크롤 인터랙션, 포인터 피직스 등 연속적인 사용자 이벤트 처리 시 상위 컴포넌트 전체의 잦은 리렌더링을 유발하는 `useState` 남용을 지양하고, Uncontrolled Component(Ref), Debounce, 또는 렌더링 격리 훅/CSS 변수를 활용하십시오.
- **의존성 배열 무결성**:
  - `useEffect`, `useCallback`, `useMemo`의 의존성 배열(deps)을 임의로 누락하지 마십시오. ESLint 규칙(`react-hooks/exhaustive-deps`)을 완벽히 준수하십시오.
- **Key 속성 고유성**:
  - 배열 반복 렌더링 시 `index`를 key로 사용하는 것을 지양하고, 엔티티의 고유 ID(`item.id`)를 key로 지정하십시오.

---

## 🛡️ 4. 예외 처리 및 타입 안전성 (Error Boundaries & TypeScript)

- **Error Boundary 적용**:
  - 컴포넌트 트리의 런타임 에러가 전체 앱을 멈추지 않도록 주요 도메인 경계마다 Error Boundary를 배치하고 Fallback UI를 제공하십시오.
- **Strict Props & Event Typing**:
  - 컴포넌트 Props는 Interface/Type으로 명확히 정의하고 `any` 타입을 엄격히 금지하십시오.

---

## 💬 5. Framework Convention 문서화 범위

- React component, hook 및 framework callback은 이름·Props/type·framework contract만으로 책임이 명확하면 설명을 기계적으로 반복하지 않습니다.
- 비표준 lifecycle 제약, 의도적인 dependency 처리, 외부 호환성 또는 중요한 side effect가 있으면 Core 기준에 따라 차이를 문서화하고, 표현 형식은 JavaScript 또는 TypeScript style 규칙을 따릅니다.
