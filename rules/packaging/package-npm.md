# NPM Packaging Rules (NPM & Node.js 생태계 패키징 규칙)

Node.js, TypeScript, JavaScript 생태계(NPM, JSR 등)의 라이브러리 및 모듈 구축/배포에 적용되는 패키징 규칙입니다.

---

## 📦 1. 매니페스트 및 익스포트 (package.json & Exports)

- **Modern Package Exports**: `package.json` 내에 `exports` 필드를 엄격히 정의하여 internal 구현 파일(예: `src/internal/*`)로의 무단 접근을 방지하고 공식 Public API 경로만 노출하십시오.
- **선언적 의존성 분리 (Dependencies Grouping)**: 런타임 필수 패키지(`dependencies`), 개발/테스트 도구(`devDependencies`), 호스트 런타임 공유 라이브러리(`peerDependencies`)를 엄격히 구분하여 작성하고, 프로젝트 전용 Lockfile(`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json` 등) 기반 환경 동기화를 엄수하십시오.
- **듀얼 포맷 지원 (ESM & CJS)**: 가급적 ES Module(ESM)을 기본 포맷으로 지원하며, 구형 환경 호환이 필요한 경우 CJS 듀얼 번들링 및 `main`, `module` 필드를 올바르게 지정하십시오.
- **타입 정의 선언**: TypeScript 패키지의 경우 `package.json`에 `types` (또는 `typings`) 필드를 정확히 지정하고, 빌드 산출물에 `.d.ts` declaration 파일이 포함되도록 구성하십시오.

---

## ⚡ 2. 트리쉐이킹 및 최적화 (Tree-shaking)

- **Side-Effects 선언**: 번들러가 사용하지 않는 코드를 안전하게 제거할 수 있도록 `package.json`에 `"sideEffects": false` (또는 특정 부작용 파일 목록)를 정확히 작성하십시오.
- **Peer Dependencies 관리**: React, Vue, Three.js 등 호스트 애플리케이션의 특정 버전에 의존하는 라이브러리는 `peerDependencies`로 분리하여 이중 번들링을 방지하십시오.

---

## 🧪 3. 린팅 및 검증

- **타입 검증 (publint / arethetypeswrong)**: `publint`나 `attw` 등의 검증 도구를 통해 `package.json` 타입 명세 및 번들링 엔트리포인트가 정확한지 기계적으로 검증하십시오.
