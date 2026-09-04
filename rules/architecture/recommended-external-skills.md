# Optional Agent Capability Catalog (선택형 에이전트 역량 카탈로그)

> [!NOTE]
> 본 카탈로그는 특정 전문성이 필요한 경우 검토할 수 있는 3rd-party 외부 스킬 후보군입니다.
> 설치는 필수가 아니며, 작업 범위와 현재 환경에 맞는 기본 도구·규칙으로 충분한지 먼저 판단하십시오.
> 외부 레포지토리의 스킬명이나 설치 옵션은 변경될 수 있으므로 원본 README를 최신 출처로 확인하고, 설치 전 유지보수 상태·라이선스·권한·전이 의존성을 검토하십시오.

---

## 💡 설치 전 확인 및 CLI 예시 (`npx skills add`)

- 스킬 설치는 의존성·외부 코드를 추가하는 변경이므로 프로젝트의 승인 및 패키지 관리 정책을 따르십시오.
- 아래 명령은 설치 인터페이스의 예시이며, 실제 지원 여부와 선택 옵션은 원본 README에서 확인하십시오.

```bash
# 1) 레포지토리 전체 스킬 일괄 설치 예시
npx skills add <repository-url>

# 2) 특정 단독 스킬 선택 설치 예시
npx skills add <repository-url> --skill "<skill-name>"
```

---

## 🎨 1. 프론트엔드 & UI 디자인 스킬

### [taste-skill](https://github.com/Leonxlnx/taste-skill)
- **개요**: AI 프론트엔드 코드(AI Slop) 방지, 모던 타이포그래피, 동적 뷰포트 레이아웃, micro-interaction 디자인 및 비주얼 파이프라인 지침 모음
- **전체 일괄 설치**: `npx skills add https://github.com/Leonxlnx/taste-skill`

| 하위 스킬명 (Skill Name) | 주요 역할 및 제공 지침 | 단독 선택 설치 명령어 |
| :--- | :--- | :--- |
| **design-taste-frontend** | Anti-Slop 디자인 규격, CSS Grid, 뷰포트 및 모던 스타일 기본 지침 | `npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"` |
| **minimalist-ui** | Notion/Linear 스타일의 미니멀리즘 인터페이스 & 절제된 색상 지침 | `npx skills add https://github.com/Leonxlnx/taste-skill --skill "minimalist-ui"` |
| **image-to-code** | 시안/참고 이미지를 분석하여 모던 프론트엔드 코드로 구현하는 비주얼 파이프라인 | `npx skills add https://github.com/Leonxlnx/taste-skill --skill "image-to-code"` |
| **brand-kit** | 브랜딩 색상 고정(Color Lock) 및 디자인 시스템 구성 지침 | `npx skills add https://github.com/Leonxlnx/taste-skill --skill "brand-kit"` |
| **reference-board** | Web/Mobile reference 보드 뷰포트 구도 및 UX 구성 가이드 | `npx skills add https://github.com/Leonxlnx/taste-skill --skill "reference-board"` |

> 💡 *추가 하위 스킬 및 세부 옵션은 [Leonxlnx/taste-skill README](https://github.com/Leonxlnx/taste-skill)를 참조하십시오.*

---

## 🛠️ 2. 백엔드 & 프레임워크 스킬

### [django-ai-plugins](https://github.com/vintasoftware/django-ai-plugins)
- **개요**: Django 백엔드 아키텍처 모범 사례(ORM, DRF, Celery 비동기, DB 마이그레이션 안전 수칙 및 코드 리뷰어) 지침 모음
- **전체 일괄 설치**: `npx skills add https://github.com/vintasoftware/django-ai-plugins`

| 하위 스킬명 (Skill Name) | 주요 역할 및 제공 지침 | 단독 선택 설치 명령어 |
| :--- | :--- | :--- |
| **django-expert** | Django ORM 쿼리 최적화, DRF API 설계 및 유닛 테스트 지침 | `npx skills add https://github.com/vintasoftware/django-ai-plugins --skill "django-expert"` |
| **django-celery-expert** | Celery 백그라운드 Task, Redis 비동기 큐 처리 전문 지침 | `npx skills add https://github.com/vintasoftware/django-ai-plugins --skill "django-celery-expert"` |
| **django-safe-migration** | DB 마이그레이션 시 테이블 락 방지 및 데이터 무결성 안전 수칙 | `npx skills add https://github.com/vintasoftware/django-ai-plugins --skill "django-safe-migration"` |
| **django-reviewer** | Django 코드 품질 및 헌법 부합성 비판적 검수 스킬 | `npx skills add https://github.com/vintasoftware/django-ai-plugins --skill "django-reviewer"` |

> 💡 *추가 하위 스킬 및 세부 옵션은 [vintasoftware/django-ai-plugins README](https://github.com/vintasoftware/django-ai-plugins)를 참조하십시오.*

---

## 📐 3. 신규 추천 스킬 등록 템플릿 (Skill Registration Template)

향후 신규 외부 3rd-party 에이전트 스킬 및 AI 플러그인을 본 카탈로그에 추가할 때는 아래 표준 양식을 준수하여 작성하십시오:

```markdown
### [<repository-name>](https://github.com/owner/repository-name)
- **개요**: <스킬의 주요 목적 및 에이전트에 주입하는 핵심 지침 1줄 요약>
- **전체 일괄 설치**: `npx skills add https://github.com/owner/repository-name`

| 하위 스킬명 (Skill Name) | 주요 역할 및 제공 지침 | 단독 선택 설치 명령어 |
| :--- | :--- | :--- |
| **<skill-name-1>** | <주요 기능 1줄 요약> | `npx skills add https://github.com/owner/repository-name --skill "<skill-name-1>"` |
| **<skill-name-2>** | <주요 기능 1줄 요약> | `npx skills add https://github.com/owner/repository-name --skill "<skill-name-2>"` |

> 💡 *추가 하위 스킬 및 세부 옵션은 [<owner/repository-name> README](https://github.com/owner/repository-name)를 참조하십시오.*
```
