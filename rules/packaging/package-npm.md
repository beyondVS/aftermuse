# NPM Packaging Rules (NPM & Node.js 생태계 패키징 규칙)

Node.js, TypeScript, JavaScript 생태계(NPM, JSR 등)의 라이브러리 및 모듈 구축/배포에 적용되는 패키징 규칙입니다.

---

## 📦 1. 매니페스트 및 익스포트 (package.json & Exports)

- **공개 엔트리포인트**: 패키지가 명시적 public entrypoint 계약을 제공해야 할 때 `exports`로 공식 API만 노출하고, 기존 manifest/consumer 계약을 우선하십시오.
- **선언적 의존성 분리 (Dependencies Grouping)**:
  런타임 필수 패키지(`dependencies`), 개발/테스트 도구(`devDependencies`), 호스트 런타임 공유 라이브러리(`peerDependencies`)를 엄격히 구분하여 작성하고,
  프로젝트 전용 Lockfile(`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json` 등) 기반 환경 동기화를 엄수하십시오.
- **모듈 포맷**: 소비자 런타임 호환성에 따라 ESM-only 또는 ESM/CJS 듀얼 포맷을 선택하고 manifest 필드를 일치시키십시오.
- **타입 정의 선언**: TypeScript 패키지의 경우 `package.json`에 `types` (또는 `typings`) 필드를 정확히 지정하고, 빌드 산출물에 `.d.ts` declaration 파일이 포함되도록 구성하십시오.

---

## ⚡ 2. 트리쉐이킹 및 최적화 (Tree-shaking)

- **Side-Effects 선언**: 실제 부작용이 있는 파일과 번들러 요구사항을 확인한 경우에만 `sideEffects`를 선언하십시오.
- **Peer Dependencies 관리**: 호스트가 소유해야 하는 의존성일 때만 `peerDependencies`로 분리하십시오.

---

## 🧪 3. 린팅 및 검증

- **패키지 검증**: TypeScript/package entrypoint 검증이 필요한 패키지에서 `publint` 또는 `attw`를 사용하십시오.
