# Vue.js 3 Architecture & Development Rules (Vue 3 특화 개발 규칙)

Vue 3 (Single Page Application, Composition API, Vite) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. SFC 구조 및 Script Setup 표준 (Single File Component)

- **API 스타일 및 언어 사양 (Composition API vs Options API & JS/TS)**:
  - 언어(JavaScript vs TypeScript) 및 API 스타일(Composition API 대 Options API)은 **프로젝트의 기존 컨벤션 및 규모**를 최우선으로 따르십시오.
  - 신규 프로젝트나 가독성/타입 안전성이 요구되는 경우, Composition API와 `<script setup>` 문법(필요 시 TypeScript `lang="ts"`)을 우선적으로 권장합니다.
- **SFC 태그 순서 정합성**:
  - 모든 `.vue` 파일은 `<script setup>` ➔ `<template>` ➔ `<style>` 순서로 정리하십시오.
- **`scoped` 스타일 가이드**:
  - 컴포넌트 전용 스타일에는 `<style scoped>`를 기본으로 사용합니다. 전역 디자인 토큰, reset, 테마 또는 프로젝트가 채택한 CSS Modules·유틸리티 CSS는 기존 스타일 아키텍처를 따릅니다.

---

## 🔄 2. 반응성 시스템 및 상태 관리 (Reactivity & Pinia)

- **`ref` 대 `reactive` 선택 기준**:
  - 기본 데이터/원시 값 및 객체 할당 시에는 `ref()`를 우선 활용하십시오.
  - Form 입력 데이터 묶음 등 구조화된 객체 상태 관리 시에 한해 `reactive()`를 적용하되, 분해 할당 시 반응성이 깨지지 않도록 주의하십시오.
- **Pinia 전역 상태 관리**:
  - Vuex 사용을 금지하고 Pinia 스토어를 사용하십시오.
  - Setup Stores (`defineStore('id', () => { ... })`) 형태를 사용하여 Composition API와의 작성 일관성을 유지하십시오.
- **Props & Emits 타입 선언**:
  - `defineProps<{ ... }>()` 및 `defineEmits<{ ... }>()`를 타입 기반 선언으로 작성하여 Props와 이벤트를 엄격히 타입화하십시오.

---

## ⚡ 3. Composables & 성능 최적화 (Composables & Performance)

- **Composable 함수 명명 규칙**:
  - 재사용 가능한 비즈니스 로직 및 상태는 `use[Feature]` 이름의 Composable로 분리하고, 반환 시 `ref` 상태의 반응성을 유지하도록 하십시오.
- **`computed` 활용 및 Side-effect 금지**:
  - 계산된 반응형 데이터는 `computed()`를 활용하고, `computed` getter 내부에서 외부 반응형 상태를 변경하는 Side-effect 코드를 금지하십시오.
- **`v-for` Key 설정**:
  - template의 `v-for` 문 내에서 인덱스 대신 고유한 ID (`:key="item.id"`)를 반드시 지정하십시오.
