---
description: "알라딘 Metadata Provider Adapter 구현 작업"
---

# 작업: 알라딘 Metadata Provider Adapter

**입력**: `/specs/002-aladin-metadata-adapter/`의 설계 문서

**사전 조건**: plan.md, spec.md, research.md, data-model.md,
contracts/provider-contract.md, quickstart.md

**테스트**: 명세의 FR-016 및 완료 조건이 자동 검증을 요구하므로 테스트 작업을 포함한다.
이는 구현 순서를 TDD로 강제하지 않는다. 각 테스트는 해당 구현의 완료 조건을 증명하며,
작업 수행 시점에 관련 구현과 함께 작성·실행할 수 있다.

**구성**: 각 사용자 스토리를 독립 검증 가능한 증분으로 구성한다. 정상 검색은 MVP이며,
실패 유형·timeout·외부 호출 없는 계약 검증은 순서대로 확장한다.

## 형식: `[ID] [P?] [Story] 설명`

- **[P]**: 서로 다른 파일이고 미완료 작업에 의존하지 않아 병렬 실행 가능
- **[Story]**: 사용자 스토리 작업에만 붙이는 추적 레이블
- 모든 설명은 정확한 파일 경로를 포함한다.

## Phase 1: 설정 (공유 인프라)

**목적**: Provider 전용 모듈 경로와 조건부 credential 설정을 준비한다.

- [X] T001 [P] `src/integrations/__init__.py` 및 `src/integrations/aladin/__init__.py`에 알라딘 Adapter 패키지 구조를 생성한다.
- [X] T002 [P] `src/config/settings.py`에 빈 문자열 기본값의 조건부 `ALADIN_TTB_KEY` 환경 설정을 추가한다.
- [X] T003 [P] `.env.example`을 Django, PostgreSQL, External metadata providers 섹션으로 재구성하고 실제 값 없는 `ALADIN_TTB_KEY=` 예시와 사용 조건 주석을 추가한다.
- [X] T004 [P] `README.md`에 `ALADIN_TTB_KEY`의 용도, 실제 key 없이 자동 테스트가 가능함, 운영 호출에 승인된 key가 필요함을 문서화한다.

---

## Phase 2: 기반 (차단 전제조건)

**목적**: 모든 검색·실패 흐름이 공유할 Provider 중립 계약과 오류 계층을 구현한다.

**⚠️ 중요**: 이 단계가 완료될 때까지 사용자 스토리 Adapter 작업을 시작할 수 없다.

- [X] T005 [P] `src/integrations/aladin/contracts.py`에 불변 `ProviderBook`과 `BookMetadataProvider` Protocol을 provider-contract.md의 필드·반환 계약대로 구현한다.
- [X] T006 [P] `src/integrations/aladin/exceptions.py`에 `ProviderError` 및 configuration, timeout, unavailable, response 하위 예외를 구현한다.
- [X] T007 `tests/integrations/aladin/test_client.py`에 fake transport fixture와 공통 JSON payload helper를 추가하여 실제 외부 호출 없이 URL·timeout·예외를 검증할 기반을 만든다.

**체크포인트**: Provider 중립 계약과 테스트 대체 경계가 준비되어 모든 스토리를 구현할 수 있다.

---

## Phase 3: 사용자 스토리 1 - 알라딘 도서 Metadata 검색 (우선순위: P1) 🎯 MVP

**목표**: 알라딘 검색 응답을 Provider 중립 Metadata로 변환하고 정상 빈 결과와 개별 무효
항목을 올바르게 처리한다.

**독립 테스트**: fake transport가 완전한 JSON, 빈 `item` 목록, 유효/무효 항목 혼합
payload를 반환할 때 필수·선택 Metadata, 빈 tuple, 유효 항목 보존을 검증한다.

- [X] T008 [US1] `src/integrations/aladin/client.py`에 HTTPS ItemSearch URL 생성, 기본 `urllib` transport, 구성 가능한 timeout 및 `AladinBookMetadataProvider` 생성자 경계를 구현한다.
- [X] T009 [US1] `src/integrations/aladin/client.py`에 JSON object/item list 검증, ASCII 13자리 ISBN13·제목 검증, 선택 Metadata 및 날짜 정규화, 유효 항목 tuple 변환을 구현한다.
- [X] T010 [US1] `tests/integrations/aladin/test_client.py`에 요청 파라미터/percent encoding/timeout 전달, 전체 Metadata 매핑, 정상 빈 결과, 유효 항목 보존 및 선택값 정규화 테스트를 추가한다.
- [X] T011 [US1] `tests/integrations/aladin/test_client.py`의 사용자 스토리 1 테스트를 실행하여 기본 transport가 호출되지 않고 정상·빈·항목 필터 계약이 통과하는지 검증한다.

**체크포인트**: 정상 검색 결과를 후속 Service가 소비할 수 있으며, 이 증분만으로
독립 테스트 가능하다.

---

## Phase 4: 사용자 스토리 2 - Provider 실패 식별 (우선순위: P1)

**목표**: 설정, 가용성 및 응답 형식 실패를 정상 또는 빈 결과와 분명히 구분한다.

**독립 테스트**: 빈 key, Provider 오류 payload, I/O 실패, malformed JSON, 잘못된 최상위
구조와 item 구조를 fake로 재현하여 약속된 예외 유형과 호출 여부를 검증한다.

- [X] T012 [US2] `src/integrations/aladin/client.py`에 key 누락 시 transport 호출 전 `ProviderConfigurationError`, Provider 오류·`OSError`·`URLError` 시 `ProviderUnavailableError`, JSON·구조 손상 시 `ProviderResponseError` 변환을 구현한다.
- [X] T013 [US2] `src/integrations/aladin/client.py`에 `get_default_provider()`를 추가하고 `src/config/settings.py`의 조건부 TTB key를 사용하도록 연결한다.
- [X] T014 [US2] `tests/integrations/aladin/test_client.py`에 configuration, Provider 오류 payload, I/O, malformed JSON, object가 아닌 최상위 값, list가 아닌 `item` 및 object가 아닌 item의 실패 분류 테스트를 추가한다.
- [X] T015 [US2] `tests/integrations/aladin/test_client.py`에 key·원본 오류 본문이 공개 예외 메시지에 노출되지 않고 설정 오류에서 transport 호출 횟수가 0인지 확인하는 회귀 테스트를 추가한다.

**체크포인트**: Provider 가용성과 응답 형식 실패가 정상·빈 결과와 혼동되지 않으며,
실패 정보가 credential을 누출하지 않는다.

---

## Phase 5: 사용자 스토리 3 - Timeout 식별 (우선순위: P1)

**목표**: timeout을 일반 Provider 가용성 실패와 별도의 안정된 오류로 분류한다.

**독립 테스트**: fake transport가 `TimeoutError`와 `socket.timeout`을 각각 발생시키고,
`OSError` 결과와 다른 `ProviderTimeoutError`가 발생하는지 검증한다.

- [X] T016 [US3] `src/integrations/aladin/client.py`에 `socket.timeout` 별칭을 포함하는 `TimeoutError`를 `ProviderTimeoutError`로 우선 변환하는 예외 경계를 구현한다.
- [X] T017 [US3] `tests/integrations/aladin/test_client.py`에 `TimeoutError`와 일반 I/O 실패가 각각 timeout 및 unavailable 예외로 구별되는지 테스트한다.

**체크포인트**: timeout이 일반 Provider 실패, 정상 결과 및 빈 결과와 혼동되지 않는다.

---

## Phase 6: 사용자 스토리 4 - 외부 호출 없는 계약 검증 (우선순위: P2)

**목표**: 실제 알라딘 서비스나 credential 없이 모든 Adapter 결과 범주를 재현하고
검증한다.

**독립 테스트**: fake transport의 기록으로 검색어·timeout 전달을 확인하고, 전체
Adapter 테스트가 실제 endpoint 호출 없이 정상·실패·timeout을 재현하는지 확인한다.

- [X] T018 [US4] `tests/integrations/aladin/test_client.py`에 fake transport 기록을 이용한 실제 endpoint 호출 0건, 검색어·timeout 전달 및 모든 결과 범주의 외부 I/O 대체 계약 테스트를 완성한다.
- [X] T019 [US4] `tests/integrations/aladin/test_client.py`에 Adapter가 `books.models.Book`을 import하거나 ORM 저장을 호출하지 않고 DB fixture 없이 검색을 완료하는 구조적 비영속성 회귀 테스트를 추가한다.

**체크포인트**: 실제 알라딘 호출과 Book 변경 없이 모든 완료 조건을 자동으로 검증할 수 있다.

---

## Phase 7: 마무리 및 교차 관심사

**목적**: 전체 품질 게이트와 문서화된 검증 절차를 실행해 완료 증거를 남긴다.

- [X] T020 `specs/002-aladin-metadata-adapter/quickstart.md`의 집중 Adapter 테스트 명령을 실행하고 결과를 확인한다.
- [X] T021 `scripts/verify.py`를 실행하여 Django check, Ruff format, Ruff lint 및 전체 pytest 품질 게이트를 통과하는지 확인한다.
- [X] T022 `specs/002-aladin-metadata-adapter/quickstart.md`의 기대 결과와 구현·검증 범위가 일치하는지 검토하고 필요 시 문서만 수술적으로 동기화한다.
- [X] T023 `CHANGELOG.md`의 `[Unreleased]`에 알라딘 Metadata Adapter와 조건부 환경 설정 추가 사항을 기록한다.

---

## 의존성 및 실행 순서

### 단계 의존성

- **Phase 1**: 의존성 없음.
- **Phase 2**: Phase 1 완료 후 시작하며 모든 사용자 스토리를 차단한다.
- **US1 (Phase 3)**: Phase 2 완료 후 시작 가능한 MVP다.
- **US2 (Phase 4)**: Phase 2의 예외 계층과 US1의 Adapter 호출 흐름에 의존한다.
- **US3 (Phase 5)**: US2의 가용성 오류 매핑을 기준으로 timeout 구분을 추가한다.
- **US4 (Phase 6)**: US1~US3의 모든 결과 범주가 구현된 뒤 전체 대체 계약을 검증한다.
- **Phase 7**: 모든 사용자 스토리 완료 후 실행한다.

### 사용자 스토리 의존성

```text
Setup → Foundational → US1 (MVP) → US2 → US3 → US4 → Polish
```

US2와 US3은 논리적으로 실패 분류를 확장하므로 정상 Adapter 호출을 구현한 US1 뒤에
순차 진행한다. US4는 앞선 모든 범주를 실제 외부 호출 없이 검증하는 통합 증거다.

### 병렬 작업 기회

- T001~T004는 서로 다른 파일이므로 병렬 수행할 수 있다.
- T005와 T006은 서로 다른 파일이므로 병렬 수행할 수 있다.
- T007은 T005/T006이 제공하는 import 계약이 확정된 뒤 진행한다.
- 같은 `client.py` 또는 `test_client.py`를 수정하는 사용자 스토리 작업은 충돌 방지를
  위해 순차 수행한다.

## 병렬 예시

```text
Task: "src/integrations/aladin/contracts.py에 ProviderBook과 Protocol 구현"
Task: "src/integrations/aladin/exceptions.py에 Provider 오류 계층 구현"
```

## 구현 전략

### MVP 우선

1. Phase 1~2로 Adapter 경계와 오류 계약을 준비한다.
2. US1로 정상 검색, 정상 빈 결과 및 항목별 정규화를 구현·검증한다.
3. US1 집중 테스트가 통과하면 정상 검색 Adapter MVP를 시연할 수 있다.

### 점진적 제공

1. US2로 설정·가용성·응답 형식 실패를 명확히 한다.
2. US3로 timeout을 일반 가용성 실패에서 분리한다.
3. US4로 외부 호출 0건과 비영속성 계약을 완결한다.
4. Phase 7의 전체 품질 게이트로 완료 증거를 확인한다.

## 참고 사항

- `[P]` 작업은 서로 다른 파일이며 선행 작업에 의존하지 않을 때만 표시했다.
- 사용자 스토리 레이블은 모든 스토리 작업에 포함했다.
- 작업은 실제 알라딘 key, smoke test, retry, rate limit, cache, Service/UI, Book 저장을
  포함하지 않는다.
