# AfterMuse Planning Latest v2026-09-06

최신 기준 파일 묶음입니다.

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
- Day 06의 첫 질문 생성·최초 답변 보존·생성 오류 재시도(IMP-052~IMP-055)가 구현되었습니다. 기본 검증은 fake Provider와 Django test client를 사용하며, 실제 OpenAI 연결은 별도 `live` 실행에서만 확인합니다.
- Day는 엄격한 마감일이 아니라 매일 무엇을 구현할지 보기 쉽게 하는 작업 묶음입니다.
