# Nuxt 3 Architecture & Development Rules (Nuxt 3 특화 개발 규칙)

Nuxt 3 (Fullstack / Universal SSR Framework) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🌐 1. 데이터 페칭 및 SSR 렌더링 규약 (Data Fetching & Universal SSR)

- **`useFetch` & `useAsyncData` 전용 훅 필수**:
  - Client-only 비동기 호출(`axios`, `fetch`)을 템플릿 최상단에서 직접 실행하지 마십시오. SSR 중복 호출 및 하이드레이션 불일치(Hydration Mismatch)를 방지하기 위해 `useFetch()` 또는 `useAsyncData()`를 사용하십시오.
- **`useState` 반응형 SSR 상태 보존**:
  - SSR 렌더링 간 서버에서 생성된 상태를 클라이언트로 안전하게 전달하기 위해 `ref()` 대신 `useState('key', initFn)`를 활용하십시오.

---

## 📂 2. 디렉터리 기반 자동 임포트 (Auto-imports & Structure)

- **Auto-import 컨벤션 준수**:
  - `components/`, `composables/`, `utils/` 폴더 내의 컴포넌트 및 로직은 Nuxt의 Auto-import 기능을 활용하되, 가독성을 저해하는 명시적 중복 `import` 선언을 줄이십시오.
- **Server Engine & API Routes (`server/`)**:
  - Backend API 및 Server Middleware는 `server/api/` 또는 `server/routes/` 아래에 `defineEventHandler()`를 통해 구성하십시오.
  - 비밀키(Secret Keys) 연동 시 `useRuntimeConfig()`의 `private` 설정 영역에서만 호출되도록 보장하십시오.

---

## 🚀 3. Nitro 서빙, SEO & 성능 최적화 (Nitro & SEO)

- **SEO & Meta 태그 표준**:
  - 페이지별 Title, Description, OpenGraph 메타 태그는 `useSeoMeta()` 또는 `useHead()`를 통해 SSR 렌더링 시점에 헤더에 정확히 주입하십시오.
- **클라이언트 전용 컴포넌트 처리**:
  - Window/Document 참조 등 브라우저 전용 라이브러리가 포함된 컴포넌트는 `<ClientOnly>` 컴포넌트로 감싸거나 `[Component].client.vue` 파일명 렌더링 규칙을 적용하십시오.
