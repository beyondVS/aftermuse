# Python Application Server Rules (Python 웹 서버 운영 규칙)

Python 웹 애플리케이션(FastAPI, Litestar, Django, Flask 등)의 애플리케이션 서버를 직접 운영할 때 적용되는 규칙입니다. Gunicorn과 Uvicorn 조합을 사용할 때는 아래 Gunicorn 프로필을 적용하십시오. PaaS·서버리스·컨테이너 플랫폼이 런타임과 프로세스 관리를 제공하는 경우에는 해당 플랫폼의 공식 운영 가이드를 우선합니다.

---

## 🦄 1. Gunicorn + UvicornWorker 실행 표준

- **Gunicorn + UvicornWorker 프로필**:
  - 프로세스 관리가 애플리케이션 책임인 ASGI 배포에서는 Gunicorn을 마스터 프로세스로 사용하고, 호환되는 Uvicorn worker 클래스를 연결하는 구성을 검토하십시오.
  - Uvicorn 단독, 다른 ASGI 서버, 플랫폼 관리형 프로세스 모델을 사용할 때는 해당 런타임의 공식 lifecycle·worker·timeout 권고를 우선하십시오.

---

## ⚙️ 2. Worker 산출 공식 및 프로세스 설정

- **워커 수 측정 및 상한 관리**:
  - `(2 * CPU 코어 수) + 1` 같은 공식은 초기 가설로만 사용하고, 동시성 모델, CPU·메모리 제한, 요청 지연 시간, 부하 테스트 결과에 따라 워커 수와 상한을 조정하십시오.
- **Worker Timeout & Keepalive**:
  - HTTP Keep-alive 시간(`keepalive 5`) 및 작업 수용 타임아웃(`timeout 60` ~ `120`)을 명시하여 교착 상태(Deadlock) 워커를 자동으로 수거하게 하십시오.

---

## 🔄 3. Graceful Shutdown 및 무중단 배포

- **Graceful Timeout 설정**:
  - 서버 중지 시 진행 중인 요청을 정상 처리하고 종료할 수 있도록 `graceful_timeout 30` 옵션을 지정하십시오.
- **재로딩 방식**:
  - Gunicorn을 직접 운영할 때는 HUP 기반 graceful reload를 사용할 수 있습니다. 오케스트레이터·PaaS 환경에서는 플랫폼이 제공하는 rollout 또는 restart 절차를 우선하십시오.
