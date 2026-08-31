# Web Frontend Architecture Rules (웹 프론트엔드 특화 규칙)

웹 프론트엔드(React, Next.js, Vue, Vite, Svelte 등) 프로젝트에 적용되는 아키텍처 및 개발 규칙입니다.

---

## 🎨 1. UI/UX 디자인 및 디벨롭먼트 표준

- **시각적 우수성 (Rich Aesthetics)**: 단순한 최소 기능 구현에 그치지 않고 현대적이고 감각적인 UI 스타일링(조화로운 컬러 팔레트, 현대적 서체, Glassmorphism, 부드러운 트랜지션 및 Hover 효과)을 적용하십시오.
- **모던 CSS/Styling**: 픽셀 하드코딩 대신 HSL tailored 색상 모듈 및 Vanilla CSS/TailwindCSS 디자인 토큰을 활용하고, 브라우저 기본 폰트 대신 Google Fonts 등 현대적 폰트를 활용하십시오.
- **동적 뷰포트 안정성 (Dynamic Viewport Stability)**: 모바일 브라우저 주소창 반응으로 인한 뷰포트 덜컹거림(Jump)을 방지하도록 고정 `100vh` 대신 동적 뷰포트 단위(`min-height: 100dvh` / `100dvh`)를 우선 사용하십시오.
- **아티클 본문 가독성 제약 (Contextual Line-Length)**: 랜딩페이지, 아티클, 포트폴리오 등 장문 파라그래프 텍스트 작성 시에는 가독성 최적화를 위해 문자 단위 너비 제한(`max-width: 65ch` 내외) 및 여유 있는 줄간격(`line-height: 1.625` / `relaxed`) 사용을 고려하십시오. (단, 고밀도 정보 배치가 필수적인 백오피스, 어드민 패널, 대시보드/데이터 테이블 표면에서는 본 제약을 적용하지 않습니다.)
- **인터랙티브 마이크로 애니메이션**: 사용자 인터랙션 요소(버튼, 카드, 모달 등)에는 부드러운 상태 변화 애니메이션을 적용하여 사용성을 높이십시오.
- **플레이스홀더 이미지 자제**: 이미지가 필요한 경우 실제 동작 가능한 미디어 및 생성형 에셋을 활용하십시오.

---

## 🛠️ 2. 프론트엔드 아키텍처 및 상태 관리

- **컴포넌트 단일 책임**: 컴포넌트는 단일 기능에 집중하고, UI 렌더링과 비즈니스 로직(API 호출, 상태 처리)을 가급적 커스텀 훅(Custom Hooks) 등으로 분리하십시오.
- **CSS Grid 레이아웃 우선**: 복잡한 Flexbox 수식 계산 대신 CSS Grid 구조 및 중앙 정렬 컨테이너 바운더리(`max-width` 지정 및 중앙 정렬)를 활용하십시오.
- **아이콘 시스템 일관성 및 SVG 패스 직접 그리기 금지 (No Hand-rolled SVG)**: 에이전트가 `<svg><path ...></svg>` 패스를 직접 임의로 작성하지 말고, 표준 아이콘 컴포넌트를 활용하며 `strokeWidth` 등 선 두께를 통일하십시오.
- **지역 상태 우선 (Local State First)**: 전역 상태(Redux, Zustand 등)는 앱 전체에서 공유해야 하는 최소한의 데이터에만 사용하고, 컴포넌트 내부 렌더링 상태는 React State 등 지역 상태로 격리하십시오.
- **Form 및 유효성 검사**: 폼 입력 요소에는 적절한 validation 지침 및 ARIA 접근성 속성을 명시하십시오.

---

## ♿ 3. 접근성 (A11y) 및 SEO 표준

- **시맨틱 HTML5**: `<div>` 남용을 지양하고 `<header>`, `<main>`, `<nav>`, `<article>`, `<section>`, `<footer>` 등 적절한 시맨틱 태그를 활용하십시오.
- **접근성 (Accessibility)**: 이미지에는 `alt` 속성, 버튼에는 `aria-label`을 명시하고 키보드 포커스 링(Focus state)을 유지하십시오.
- **자동화 브라우저 검증 및 접근성 트리 (Accessibility Tree & Automation)**: 브라우저 통합 도구(Playwright 등)로 웹 UI를 탐색하고 요소 클릭 등 자동 검증을 수행할 때 오작동이 많은 단순 시각적 좌표(Coordinates) 대신 Accessibility Tree (Ref) 구조를 우선 지정하여 타겟팅하십시오.
- **SEO 기본 적용**: 페이지별 Title 태그, Meta Description, OpenGraph 태그 및 단일 `<h1>` 구조를 준수하십시오.

---

## 📚 4. 외부 에이전트 스킬 카탈로그 (Recommended Agent Skills)

- **[taste-skill 카탈로그](recommended-external-skills.md)**: Anti-slop 프론트엔드 모던 타이포그래피, Notion/Linear 스타일 `minimalist-ui`, 시안 기반 `image-to-code` 비주얼 파이프라인 등 외부 추천 스킬 상세 지침 및 설치 가이드는 [recommended-external-skills.md](recommended-external-skills.md) 모듈을 참조하십시오.
