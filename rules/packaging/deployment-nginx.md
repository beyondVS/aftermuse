# Nginx Deployment & Proxy Rules (Nginx 리버스 프록시 및 서버 수칙)

Nginx를 Reverse Proxy, Web Server, TLS Termination 또는 ingress 계층으로 운영할 때 적용되는 아키텍처 및 보안 설정 지침입니다.
CDN, API Gateway, 관리형 ingress 또는 PaaS가 이 책임을 제공하는 경우에는 해당 플랫폼의 공식 보안·운영 가이드를 우선합니다.

---

## 🌐 1. 프록시 헤더 필수 설정 (Proxy Headers)

- **신뢰 경계 내 클라이언트 식별 헤더**:
  - Nginx가 신뢰하는 상위 프록시 또는 직접 연결된 클라이언트의 요청을 백엔드로 전달할 때, 애플리케이션의 proxy trust 설정과 일치하도록 아래 헤더를 구성하십시오.
    공개 인터넷에서 전달된 임의의 `X-Forwarded-*` 헤더를 무조건 신뢰하지 마십시오:
    ```nginx
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    ```

---

## 🔒 2. 보안 및 버퍼/타임아웃 최적화 (Security & Buffers)

- **서버 버전 정보 숨김**:
  - 보안 취약점 노출을 막기 위해 `server_tokens off;` 옵션을 반드시 포함하십시오.
- **클라이언트 바디 용량 제한 (`client_max_body_size`)**:
  - 무제한 업로드로 인한 DoS 공격을 방지하기 위해 서비스에 알맞은 용량(예: `client_max_body_size 10M;`)을 지정하십시오.
- **보안 헤더 주입**:
  - 애플리케이션·CDN·Nginx 중 한 계층에서 일관된 보안 헤더 정책을 적용하십시오.
  - `X-Frame-Options`와 `X-Content-Type-Options`는 검토하되, 폐기된 `X-XSS-Protection`은 새 설정의 기본값으로 추가하지 마십시오.
  - CSP, HSTS 등은 서비스의 TLS·콘텐츠 정책과 호환성을 검증한 뒤 적용하십시오.

---

## ⚡ 3. Static File Serving & Gzip/Brotli 압축

- **정적 자원 캐싱 규칙**:
  - Static 파일(`images`, `css`, `js`)에는 캐싱 정책과 `add_header Cache-Control "public, no-transform";`을 적용하십시오.
  - 캐시 기간은 asset fingerprinting, CDN 및 invalidation 전략에 따라 정하며, 신규 프로젝트에서는 `expires 30d;`를 시작점 예시로 사용할 수 있습니다.
  - 기존 운영 설정이 있으면 이를 우선합니다.
- **Gzip/Brotli 압축 활성화**:
  - 텍스트 기반 자원(`text/plain`, `text/css`, `application/json`, `application/javascript`)의 네트워크 전송량 절감을 위해 `gzip on;`을 활성화하십시오.
  - 압축 최소 크기는 payload, CPU 및 플랫폼 설정에 따라 정하며, 신규 프로젝트에서는 `gzip_min_length 1000;`을 시작점 예시로 사용할 수 있습니다.
  - 기존 운영 설정이 있으면 이를 우선합니다.
