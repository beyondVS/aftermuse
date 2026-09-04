# Docker Architecture & Packaging Rules (Docker 컨테이너화 수칙)

Docker 및 Containerization 기반 배포 이미지를 직접 작성·운영할 때 적용되는 표준 규약 및 보안 지침입니다.
PaaS, 서버리스 또는 조직의 관리형 빌드 시스템이 이미지 구조·보안 정책을 제공하는 경우에는 해당 플랫폼 규칙을 우선합니다.

---

## 📦 1. Multi-stage Build 및 이미지 경량화

- **Multi-stage Build**: 빌드 전용 도구·산출물이 최종 런타임 이미지에 들어갈 위험이 있을 때 build와 production stage를 분리하십시오.
  - 빌드 도구(GCC, SDK, Node.js full image)가 프로덕션 최종 이미지에 남아 커스텀 바이너리 크기를 키우거나 보안 헛점을 남기지 않도록 하십시오.
- **호환 가능한 Base Image**: 런타임·보안 요구사항과 운영 도구 호환성을 근거로 base image를 선택하십시오.

---

## 🔒 2. 컨테이너 보안 수칙 (Non-root & Layer Security)

- **Non-root 사용자 실행 (`USER`)**:
  - 기본적으로 non-root로 실행하고, 이미지·플랫폼·프로세스 요구가 다른 방식을 필요로 하면 그 메커니즘과 사유를 문서화하십시오.
- **자격 증명 및 시크릿 하드코딩 금지**:
  - `ENV` 또는 `ARG` 지시어에 API Key, DB Password 등 비밀값을 하드코딩하지 마십시오. Build-time secret 또는 런타임 주입 방식을 사용하십시오.
- **Layer 캐싱 최적화**:
  - 변경이 적은 패키지 파일(`package.json`, `requirements.txt`, `go.mod`)을 소스 코드 복사(`COPY . .`)보다 먼저 COPY하여 명령 캐시를 최대 활용하십시오.

---

## ⚙️ 3. Healthcheck & Graceful Shutdown

- **`HEALTHCHECK` 지시어 정의**:
  - 오케스트레이터가 동등한 readiness 신호를 제공하지 않을 때 `HEALTHCHECK`를 정의하십시오.
- **SIGTERM 시그널 수용**:
  - 이미지가 직접 프로세스를 실행하고 signal handling이 중요할 때 exec-form entrypoint를 사용하십시오.
