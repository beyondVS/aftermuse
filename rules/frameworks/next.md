# Next.js Architecture & Development Rules (Next.js 특화 개발 규칙)

Next.js (App Router, Fullstack/SSR) 기반 프로젝트에 적용되는 아키텍처 및 코딩 규칙입니다.

---

## 🏛️ 1. App Router & 컴포넌트 경계 (Server vs. Client Components)

- **서버 컴포넌트(RSC) 기본화**:
  - `app/` 디렉터리 내의 모든 컴포넌트는 기본적으로 서버 컴포넌트로 작성하십시오.
- **`'use client'` 최소화 및 말단 격리**:
  - 이벤트 리스너(`onClick`), React Hook(`useState`, `useEffect`), 브라우저 전용 API가 필요한 최하단 인터랙티브 컴포넌트에만 서술적으로 `'use client'`를 선언하십시오.
  - Page/Layout 컴포넌트 최상단에 `'use client'`를 무분별하게 선언하여 번들 크기를 키우지 마십시오.
- **인터랙션/애니메이션 컴포넌트 말단 격리**:
  - Motion 라이브러리, 애니메이션 훅, 스크롤/포인터 피직스가 포함된 유저 인터랙티브 요소는 서버 컴포넌트 트리를 오염시키지 않도록 독립된 최하단(Leaf) 컴포넌트로 정밀하게 분리하고 최상단에 `'use client'`를 선언하십시오.

---

## 🌐 2. 데이터 페칭 및 렌더링 전략 (Data Fetching & Rendering)

- **서버 단 데이터 페칭**:
  - 가능하면 데이터 페칭은 서버 컴포넌트에서 직접 수행(`async/await`)하여 클라이언트 폭포수(Waterfall) 요청을 방지하십시오.
- **캐싱 및 Revalidation 전략**:
  - `fetch` 요청 시 캐싱 옵션(`cache: 'force-cache'`, `next: { revalidate: 60 }`)을 명확히 설정하고, CUD 실행 후에는 `revalidatePath()` 또는 `revalidateTag()`를 통해 캐시를 갱신하십시오.
- **Streaming & Suspense**:
  - 느린 비동기 데이터 페칭 구간은 `loading.tsx` 또는 `<Suspense>`로 감싸 선점형 스켈레톤 UI를 스트리밍 제공하십시오.

---

## 🔒 3. Server Actions & API Routes

- **Server Actions 안전성**:
  - Server Actions 함수 내에서는 클라이언트 전달 입력값을 반드시 Pydantic/Zod 등의 스키마 검증기로 재검증하십시오.
  - 인증(Authentication) 및 권한(Authorization)을 Server Actions 내부 최상단에서 명시적으로 확인하십시오.
- **API Routes (`app/api/`)**:
  - 외부 Webhook이나 RESTful 엔드포인트를 구축할 때 활용하며, 표준 `NextResponse.json()` 응답 구조를 지키십시오.

---

## 🚀 4. 라우팅, 이미지 & 폰트 최적화 (Routing & Performance)

- **Standard Routing Conventions**:
  - 동적 라우팅(`[id]`), 병렬 라우팅(`@slot`), 인터셉팅 라우팅(`(.)`) 규칙을 준수하고 라우터 이동 시 `<Link>` 컴포넌트를 우선 활용하십시오.
- **Built-in Optimization Component**:
  - 이미지 렌더링 시 외부 URL/로컬 이미지를 가리지 않고 `next/image` (`<Image />`) 컴포넌트를 사용하여 Layout Shift(CLS)를 방지하고 자동 WebP/AVIF 변환을 적용하십시오.
  - 외부 폰트는 `next/font`를 통해 빌드 타임에 자체 호스팅 처리하십시오.
