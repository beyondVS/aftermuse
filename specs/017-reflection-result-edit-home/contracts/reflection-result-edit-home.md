# Reflection 결과·수정·완료 및 Home 계약

## 공통 규칙

- 모든 Reflection endpoint는 로그인과 owner scope를 요구한다.
- 타인 또는 없는 Reflection은 동일하게 404로 처리하고 존재 여부를 노출하지 않는다.
- GET은 상태를 변경하지 않는다. 모든 쓰기는 CSRF 보호 POST다.
- 성공 POST는 결과 GET으로 redirect하는 PRG 패턴을 사용한다.
- 오류 응답에는 credential 또는 내부 예외를 노출하지 않는다.

## 결과 조회

```text
GET /reflections/{reflection_id}/
```

### 200

- 책 제목, 존재할 때만 저자, `created_at` 기준 작성일
- 안전하게 렌더링한 `current_markdown` (headings, paragraphs, lists, blockquotes, emphasis)
- `작성 중` 또는 `완료` 상태
- DRAFT: 수정, 완료, Home 이동
- COMPLETED: 읽기 전용 안내, Home 이동
- 저장 직후 redirect인 경우 저장 완료 message

### 404

- 미인증 redirect 이후 접근 불가, 타인 기록, 없는 기록
- 기록 내용과 상태 미노출

## 수정

```text
GET  /reflections/{reflection_id}/edit/
POST /reflections/{reflection_id}/edit/
```

### GET

- DRAFT: 200 OK, `current_markdown`이 textarea 원문으로 제공되며 저장과 취소 행동 제공.
- COMPLETED: 수정 불가 (결과 화면으로 안내/redirect).

### POST 입력

```text
markdown: 1..20000 chars, nonblank
```

### POST 결과

| 결과 | 응답 |
| --- | --- |
| 저장 성공 | 302 결과 화면, 저장 완료 message |
| form validation 실패 | 400, 입력과 field error 유지 |
| 이미 COMPLETED | 수정 거부 (400 또는 결과 화면 안내) |
| 타인·없음 | 404 |

## 완료 확인과 완료

```text
GET  /reflections/{reflection_id}/complete/
POST /reflections/{reflection_id}/complete/
```

### GET

- DRAFT: 200 OK, 현재 본문을 완료할 것인지 확인 및 완료 POST/취소 링크 제공.
- COMPLETED: 완료 불필요 (결과 화면으로 안내/redirect).

### POST 결과

| 결과 | 응답 |
| --- | --- |
| DRAFT 완료 성공 | 302 결과 화면; Reflection/Interview 모두 COMPLETED |
| 이미 COMPLETED | 302 기존 결과 화면, 추가 쓰기 없음 (단순 guard) |
| 타인·없음 | 404 |

## 안전 렌더링

1. 현재 본문 선택 (`revised_markdown` 우선)
2. 기본 Markdown 구조(headings, paragraphs, lists, blockquotes, emphasis) 렌더링
3. 사용자 작성 raw HTML이 브라우저에서 실행되지 않도록 안전하게 처리 (보안 불변식)

## Home

```text
GET /
```

- 인증 사용자만 `recent_reflection` 조회
- owner scope, `updated_at DESC, id DESC`, limit 1
- UI 섹션 명칭: `최근 독서노트`
- 상태 텍스트: DRAFT는 `작성 중`, COMPLETED는 `완료`
- `[독서노트 보기]`는 결과 조회 endpoint로 연결
- Reflection 없음: 최근 카드 미표시, 기존 Home 영역과 행동 유지
- 전체 목록, pagination, 필터, 정렬 UI 없음
