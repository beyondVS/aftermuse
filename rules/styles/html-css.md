# HTML/CSS Style Guide (HTML/CSS 스타일 및 컨벤션 지침)

Google HTML/CSS Style Guide 및 modern web 베스트 프랙티스 기반의 스타일 규격입니다.
기존 프로젝트에서는 설정 파일과 디자인 시스템을 우선하며, 신규 프로젝트에서는 이 문서를 기본 프로필로 사용하고 formatter·linter 설정으로 기계적으로 확정하십시오.

---

## 🌐 1. 일반 규칙 (General Rules)

- **프로토콜 (Protocol)**: 임베디드 리소스(이미지, 스크립트 등)는 항상 `HTTPS` 프로토콜을 사용합니다.
- **들여쓰기 (Indentation)**: 탭(Tab) 대신 2개 공백(Spaces)을 사용합니다.
- **대소문자 (Capitalization)**: 태그명, 속성명, CSS 선택자, 속성값 등 모든 코드는 소문자만 사용합니다.
- **인코딩 (Encoding)**: BOM이 없는 `UTF-8`을 사용하며 HTML 헤더에 `<meta charset="utf-8">`을 명시합니다.

---

## 📄 2. HTML 스타일 규칙 (HTML Rules)

- **문서 타입 (Doctype)**: 최상단에 `<!doctype html>`을 명시하십시오.
- **시맨틱 태그 (Semantics)**: HTML5 시맨틱 요소(`<article>`, `<section>`, `<nav>`, `<header>`, `<footer>` 등)를 목적에 맞게 적극 활용하십시오.
- **대체 텍스트 (Accessibility)**: 모든 `<img>` 태그에는 `alt` 속성을 필수 지정하십시오.
- **관심사 분리 (Separation of Concerns)**:
  HTML 구조, CSS 표현 및 JS 동작을 적절히 분리하고 불필요한 인라인 style/script를 피하십시오.
  스타일시트와 스크립트의 배치는 프로젝트의 bundler·component architecture 및 기존 관례에 따르십시오.
- **불필요한 type 속성 생략**: `<link rel="stylesheet">` 및 `<script>` 태그에서 `type="text/css"`, `type="text/javascript"` 속성을 생략하십시오.
- **속성값 감싸기**: 모든 HTML 속성값은 큰따옴표(`""`)로 감싸하십시오.

---

## 🎨 3. CSS 스타일 및 포맷팅 (CSS Rules)

- **클래스 명명 규칙 (Class Naming)**: Meaningful하고 하이픈(`-`)으로 구획된 소문자 명명(Kebab-case)을 사용하십시오.
  - Good: `.video-player`, `.site-navigation`
  - Bad: `.vid`, `.red-text`
- **ID 선택자 자제**: 스타일링 목적으로 ID 선택자(`#id`) 사용을 지양하고 클래스 선택자(`.class`)를 우선 사용하십시오.
- **축약 속성 (Shorthand)**: 가능한 경우 축약 속성(`padding`, `margin`, `font` 등)을 활용하십시오.
- **0과 단위 (Units)**: `0` 값에는 단위를 붙이지 마십시오. (예: `margin: 0;`)
- **소수점 0 (Leading Zeros)**: `1` 미만 소수점 표기 시 선행 `0`을 생략하지 마십시오. (예: `font-size: 0.8em;`)
- **`!important` 사용 금지**: css 특이도(Specificity) 구조를 깨뜨리는 `!important` 구문 사용을 지양하십시오.
- **단일 Accent 색상 및 Color Lock 규칙**:
  프로젝트당 핵심 강조 색상(Accent Color)은 1개로 제한(채도 80% 미만 권장)하고, 한 페이지 내부에서 Warm/Cool 회색조(Slate vs Stone 등)를 섞어 쓰지 않도록 톤앤매너를 일관되게 유지하십시오.
- **AI 진부함 방지 (Anti-Default Aesthetics)**: 무의미하고 상투적인 AI 보라색/네온 그라데이션 남발을 지양하고, 브랜드와 목적에 맞는 조화로운 컬러 팔레트를 사용하십시오.
- **속성 선언 순서**: 규칙 블록 내 속성은 알파벳순(Alphabetical order)으로 정렬하십시오.
- **세미콜론 및 띄어쓰기**:
  - 모든 속성 선언 끝에는 세미콜론(`;`)을 작성하십시오.
  - 속성명 콜론(`:`) 뒤와 블록 여는 중괄호(`{`) 앞에 1개의 공백을 둡니다.
