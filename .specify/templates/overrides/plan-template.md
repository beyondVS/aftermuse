# 구현 계획: [FEATURE]

**브랜치**: `[###-feature-name]` | **날짜**: [DATE] | **사양**: [link]

**입력**: `/specs/[###-feature-name]/spec.md`의 기능 사양

**참고**: 이 템플릿은 `$speckit-plan` 명령이 채웁니다. 템플릿 정의에는 실행 워크플로가 설명되어 있습니다.

## 요약

[기능 사양에서 추출한 주요 요구사항 + 조사에서 도출한 기술적 접근법]

## 기술적 맥락

<!--
  작업 필요: 이 섹션을 프로젝트의 기술 세부사항으로 교체합니다.
  아래 구조는 반복 작업을 안내하기 위한 참고용입니다.
-->

**언어/버전**: [예: Python 3.11, Swift 5.9, Rust 1.75 또는 NEEDS CLARIFICATION]

**주요 의존성**: [예: FastAPI, UIKit, LLVM 또는 NEEDS CLARIFICATION]

**저장소**: [해당하는 경우, 예: PostgreSQL, CoreData, 파일 또는 N/A]

**테스트**: [예: pytest, XCTest, cargo test 또는 NEEDS CLARIFICATION]

**대상 플랫폼**: [예: Linux 서버, iOS 15+, WASM 또는 NEEDS CLARIFICATION]

**프로젝트 유형**: [예: library/cli/web-service/mobile-app/compiler/desktop-app 또는 NEEDS CLARIFICATION]

**성능 목표**: [도메인별 목표, 예: 1000 req/s, 10k lines/sec, 60 fps 또는 NEEDS CLARIFICATION]

**제약 조건**: [도메인별 제약, 예: <200ms p95, <100MB memory, offline-capable 또는 NEEDS CLARIFICATION]

**규모/범위**: [도메인별 범위, 예: 10k users, 1M LOC, 50 screens 또는 NEEDS CLARIFICATION]

## 헌법 검사

*게이트: 0단계 조사 전에 통과해야 합니다. 1단계 설계 후 다시 확인합니다.*

[헌법 파일을 바탕으로 결정한 게이트]

## 프로젝트 구조

### 문서화 (이 기능)

```text
specs/[###-feature]/
├── plan.md              # 이 파일 ($speckit-plan 명령 출력)
├── research.md          # 0단계 출력 ($speckit-plan 명령)
├── data-model.md        # 1단계 출력 ($speckit-plan 명령)
├── quickstart.md        # 1단계 출력 ($speckit-plan 명령)
├── contracts/           # 1단계 출력 ($speckit-plan 명령)
└── tasks.md             # 2단계 출력 ($speckit-tasks 명령 - $speckit-plan이 생성하지 않음)
```

### 소스 코드 (저장소 루트)
<!--
  작업 필요: 아래의 자리 표시자 트리를 이 기능의 구체적인 배치로 교체합니다.
  사용하지 않는 선택지를 삭제하고 실제 경로(예: apps/admin, packages/something)로
  선택한 구조를 확장합니다. 완성된 계획에는 Option 레이블이 포함되어서는 안 됩니다.
-->

```text
# [사용하지 않으면 삭제] 선택지 1: 단일 프로젝트 (기본값)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [사용하지 않으면 삭제] 선택지 2: 웹 애플리케이션 ("frontend" + "backend"가 감지된 경우)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [사용하지 않으면 삭제] 선택지 3: 모바일 + API ("iOS/Android"가 감지된 경우)
api/
└── [위 backend와 동일]

ios/ 또는 android/
└── [플랫폼별 구조: 기능 모듈, UI 흐름, 플랫폼 테스트]
```

**구조 결정**: 선택한 구조를 문서화하고 위에 기록한 실제 디렉터리를 참조합니다.

## 복잡성 추적

> **헌법 검사에서 정당화해야 하는 위반이 있는 경우에만 작성합니다.**

| 위반 | 필요한 이유 | 더 단순한 대안을 거부한 이유 |
|-----------|------------|-------------------------------------|
| [예: 4번째 프로젝트] | [현재 필요] | [3개 프로젝트로 충분하지 않은 이유] |
| [예: Repository 패턴] | [구체적인 문제] | [직접 DB 접근으로 충분하지 않은 이유] |
