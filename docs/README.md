# AfterMuse Planning Latest v2026-09-15

최신 기준 파일 묶음입니다.

## 최근 구현 확인 — 2026-09-15

- Interview 자동 POST와 일반 submit의 경쟁을 방지하고, 답변 선저장·재시도·서버 멱등성을 유지했습니다.
- Coverage가 미완료인 일반 모드는 요청 schema에서도 질문을 요구합니다. 네 축 완료 및 `CAP_EXTENSION`의 생략 정책은 유지했습니다.
- 첫 질문·다음 질문 503 화면은 안전한 실패 사유·오류 코드·질문 번호를 제공하며, 로그는 단계·Interview id·sequence·예외 chain·`reason`으로 구별합니다. 답변·credential·Provider 원문은 노출하지 않습니다.
- Gemini live smoke에서 first·analysis·next, 저정보 답변, 실제 HTTP·테스트 DB 저장 및 재요청을 확인했습니다. Ollama GPU runner 오류는 확인했으며 후속 대응은 보류했습니다.
- 관련 테스트 207 passed, Gemini live 2 passed. 커밋 전 표준 verify는 임시 부모 폴더를 준비한 상태에서 388 passed, 1 skipped, 4 deselected이며 lint·format도 통과했습니다.
- 상세 실행·오류 코드 안내는 저장소 루트 [README.md](../README.md)를 참조합니다.

## 문서 우선순위

1. AfterMuse_MVP_PRD_v4.md
2. AfterMuse_Architecture_Decisions_v4.md
3. AfterMuse_UI_UX_and_Design_Implementation_Guide_v8.md
4. AfterMuse_Product_Planning_and_System_Design_Handoff_v9.md
5. AfterMuse_Discord_Concept_Deck_v8.pptx

## 구현 실행

- AfterMuse_MVP_Implementation_Plan_v5.md
- v5는 2주 Core MVP를 Week/Day 상위 섹션으로 구분하고, 이후 Full MVP Backlog를 별도 Part로 분리합니다.
- 알라딘 OpenAPI 종료 대응을 위해 IMP-025를 Critical Path에 추가하고 전체 일정을 11개의 Day 작업 묶음으로 재기준화했습니다.
- Day 03 Bundle 03A의 Kakao 검색 복구와 로컬 Book 선택·등록(IMP-025, IMP-024)이 자동·live·Desktop/Mobile 검증을 거쳐 완료되었습니다.
- Day 05의 최소 Book Knowledge와 Interview 시작 준비(IMP-040~IMP-042, IMP-050~IMP-051)가 자동·Desktop/Mobile 검증을 거쳐 완료되었습니다.
- Day 06의 첫 질문 생성·최초 답변 보존·생성 오류 재시도(IMP-052~IMP-055)가 구현되었습니다. 생성 질문 안전성, HTMX 4xx/5xx 영역 교체와 오류 focus, 정책 충돌 정보 비노출, 기존 Turn 재사용 전 Provider 미생성까지 수렴 검증을 완료했습니다. 기본 검증은 fake Provider와 Django test client를 사용하며, 전체 품질 게이트는 233 passed, 1 skipped, 1 deselected입니다. 실제 OpenAI 연결은 별도 `live` 실행에서만 확인합니다.
- Day 09의 최소 Home Navigation Hub와 Interview 재진입(IMP-085~IMP-086)이 구현되었습니다. 실제 사용자 기록의 상태별 카드와 영역별 빈 상태, 기존 Interview의 현재 단계 및 이전 확정 질문·답변 표시를 검증했습니다.
- Day는 엄격한 마감일이 아니라 매일 무엇을 구현할지 보기 쉽게 하는 작업 묶음입니다.
