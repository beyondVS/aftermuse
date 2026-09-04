# Vue.js 3 Architecture & Development Rules (Vue 3 특화 개발 규칙)

Vue 3 (Single Page Application, Composition API, Vite) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. SFC 구조 및 Script Setup 표준 (Single File Component)

- **API 스타일 및 언어 사양 (Composition API vs Options API & JS/TS)**:
  - 언어(JavaScript vs TypeScript) 및 API 스타일(Composition API 대 Options API)은 **프로젝트의 기존 컨벤션 및 규모**를 최우선으로 따르십시오.
  - 신규 프로젝트나 가독성/타입 안전성이 요구되는 경우, Composition API와 `<script setup>` 문법(필요 시 TypeScript `lang="ts"`)을 우선적으로 권장합니다.
- **SFC 태그 순서 정합성**:
  - SFC 태그 순서는 formatter와 프로젝트 기존 컨벤션을 따르십시오.
- **`scoped` 스타일 가이드**:
  - 신규 프로젝트에 별도 컨벤션이 없을 때 컴포넌트 전용 스타일에 `<style scoped>`를 기본으로 고려하십시오.

---

## 🔄 2. 반응성 시스템 및 상태 관리 (Reactivity & Pinia)

- **`ref` 대 `reactive` 선택 기준**:
  - 상태의 교체·중첩·재사용 요구와 프로젝트 컨벤션에 따라 `ref()` 또는 `reactive()`를 선택하십시오.
  - Form 입력 데이터 묶음 등 구조화된 객체 상태 관리 시에 한해 `reactive()`를 적용하되, 분해 할당 시 반응성이 깨지지 않도록 주의하십시오.
- **Pinia 전역 상태 관리**:
  - 기존 Vuex/Pinia 계약과 호환성을 우선하고, 신규 전역 상태에는 필요 시 Pinia를 선택하십시오.
  - Pinia를 채택한 경우에만 프로젝트 스타일에 맞는 Setup Store 등을 사용하십시오.
- **Props & Emits 타입 선언**:
  - TypeScript 프로젝트에서 공유 컴포넌트 계약을 검증해야 할 때 타입 기반 props/emits를 사용하십시오.

---

## ⚡ 3. Composables & 성능 최적화 (Composables & Performance)

- **Composable 함수 명명 규칙**:
  - 여러 컴포넌트에서 재사용되는 로직·상태일 때 composable로 추출하고 반응성을 보존하십시오.
- **`computed` 활용 및 Side-effect 금지**:
  - 계산된 반응형 데이터는 `computed()`를 활용하고, `computed` getter 내부에서 외부 반응형 상태를 변경하는 Side-effect 코드를 금지하십시오.
- **`v-for` Key 설정**:
  - `v-for`에는 안정적 고유 ID를 사용하고, 정적·비재정렬 목록에 한해 index key를 허용하십시오.
