# Reflection 결과·수정·완료 및 Home 계약

## 공통 규칙

- 모든 Reflection endpoint는 로그인과 owner scope를 요구한다.
- 타인 또는 없는 Reflection은 동일하게 404로 처리하고 존재 여부를 노출하지 않는다.
- GET은 상태를 변경하지 않는다. 모든 쓰기는 CSRF 보호 POST다.
- 성공 POST는 결과 GET으로 redirect하는 PRG 패턴을 사용한다.
- 오류 응답에는 본문 원문, revision token, credential 또는 내부 예외를 노출하지 않는다.

## 결과 조회

```text
GET /reflections/{reflection_id}/
```

### 200

- 책 제목, 존재할 때만 저자, `created_at` 기준 작성일
- 안전하게 렌더링한 `current_markdown`
- `작성 중` 또는 `완료` 상태
- DRAFT: 수정, 완료, Home 이동
- COMPLETED: 읽기 전용 안내, Home 이동
- 저장 직후 redirect인 경우 aria-live 가능한 저장 완료 message

### 404

- 미인증 redirect 이후 접근 불가, 타인 기록, 없는 기록
- 기록 내용과 상태 미노출

## 수정

```text
GET  /reflections/{reflection_id}/edit/
POST /reflections/{reflection_id}/edit/
```

### GET 200

- DRAFT의 `current_markdown`이 textarea 원문
- hidden `expected_updated_at`
- 저장과 취소 행동

### POST 입력

```text
markdown: 1..20000 chars, nonblank, raw HTML/link/image/prohibited instruction 없음
expected_updated_at: GET 시 발급한 token
```

### POST 결과

| 결과 | 응답 |
| --- | --- |
| 저장 성공 | 302 결과 화면, 저장 완료 message |
| 동일 내용·현재 token | 성공으로 수렴하되 의미 없는 별도 version 없음 |
| form validation 실패 | 400, 입력과 field error 유지 |
| 오래된 token | 409, 최신 결과 확인 링크와 덮어쓰기 없음 |
| COMPLETED | 409, 읽기 전용 결과 링크 |
| 타인·없음 | 404 |
| persistence 오류 | 503, 기존 본문 보존 및 재시도 가능 |

## 완료 확인과 완료

```text
GET  /reflections/{reflection_id}/complete/
POST /reflections/{reflection_id}/complete/
```

### GET 200

- DRAFT 현재 본문을 완료할 것인지 확인
- hidden `expected_updated_at`
- 완료 POST와 결과 화면으로 돌아가는 취소 링크
- 쓰기 0건

### POST 결과

| 결과 | 응답 |
| --- | --- |
| DRAFT 완료 성공 | 302 결과 화면; Reflection/Interview 모두 COMPLETED |
| 이미 COMPLETED | 302 기존 결과 화면, 쓰기 없음 |
| 오래된 token | 409, 최신 결과 확인 후 다시 완료하도록 안내 |
| 타인·없음 | 404 |
| persistence 오류 | 503, Reflection/Interview 기존 상태 보존 |

## 안전 렌더링

입력은 저장 시 validator를 통과하고, 표시 직전에 다시 다음 경계를 적용한다.

1. 현재 본문 선택(`revised_markdown` 우선)
2. HTML escape
3. extension 없는 Python-Markdown 기본 변환
4. 허용 결과 구조(headings, paragraphs, lists, blockquotes, text emphasis) 출력

raw HTML, script/event attribute, link, image, iframe, form 또는 외부 resource action은 결과에
존재할 수 없다. validator를 우회한 legacy/직접 DB 값도 pre-escape되어 실행되지 않는다.

## Home

```text
GET /
```

- 인증 사용자만 `recent_reflection` 조회
- owner scope, `updated_at DESC, id DESC`, limit 1
- DRAFT는 `작성 중`, COMPLETED는 `완료`
- `[독서노트 보기]`는 결과 조회 endpoint로 연결
- Reflection 없음: 최근 카드 미표시, 기존 Home 영역과 행동 유지
- 전체 목록, pagination, 필터, 정렬 UI 없음
