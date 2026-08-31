# Docker Architecture & Packaging Rules (Docker 컨테이너화 수칙)

Docker 및 Containerization 기반 배포 이미지를 직접 작성·운영할 때 적용되는 표준 규약 및 보안 지침입니다. PaaS, 서버리스 또는 조직의 관리형 빌드 시스템이 이미지 구조·보안 정책을 제공하는 경우에는 해당 플랫폼 규칙을 우선합니다.

---

## 📦 1. Multi-stage Build 및 이미지 경량화

- **Multi-stage Build 필수**:
  - 소스 코드 컴파일, 의존성 패키지 설치(Build Stage)와 실제 런타임 환경(Production Stage)을 Multi-stage로 분리하십시오.
  - 빌드 도구(GCC, SDK, Node.js full image)가 프로덕션 최종 이미지에 남아 커스텀 바이너리 크기를 키우거나 보안 헛점을 남기지 않도록 하십시오.
- **Minimal Base Image 사용**:
  - 프로덕션 런타임 이미지로는 `alpine`, `slim`, 또는 Distroless 이미지를 활용하여 이미지 크기 및 취약점 공격 표면을 최소화하십시오.

---

## 🔒 2. 컨테이너 보안 수칙 (Non-root & Layer Security)

- **Non-root 사용자 실행 (`USER`)**:
  - Dockerfile 내에서 `root` 권한으로 컨테이너 프로세스를 실행하는 것을 금지합니다. 반드시 앱 전용 유저(`USER appuser` 또는 `USER 1000:1000`)를 생성하여 실행하십시오.
- **자격 증명 및 시크릿 하드코딩 금지**:
  - `ENV` 또는 `ARG` 지시어에 API Key, DB Password 등 비밀값을 하드코딩하지 마십시오. Build-time secret 또는 런타임 주입 방식을 사용하십시오.
- **Layer 캐싱 최적화**:
  - 변경이 적은 패키지 파일(`package.json`, `requirements.txt`, `go.mod`)을 소스 코드 복사(`COPY . .`)보다 먼저 COPY하여 명령 캐시를 최대 활용하십시오.

---

## ⚙️ 3. Healthcheck & Graceful Shutdown

- **`HEALTHCHECK` 지시어 정의**:
  - 컨테이너가 정상적으로 요청을 받을 준비가 되었는지 검증하는 `HEALTHCHECK` 명령어를 명시하십시오.
- **SIGTERM 시그널 수용**:
  - 컨테이너 메인 프로세스는 OS 시그널(`SIGTERM`)을 즉시 받아 graceful shutdown을 수행할 수 있도록 엔트리포인트를 배열 형상(`ENTRYPOINT ["node", "server.js"]`)으로 선언하십시오.
