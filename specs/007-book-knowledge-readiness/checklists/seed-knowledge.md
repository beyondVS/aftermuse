# Seed Knowledge 출처 검수 체크리스트

**목적**: 공용 Book Knowledge로 적용할 각 Claim이 공식 출처의 내용으로 뒷받침되는지
사람이 확인하고 승인한 증거를 남긴다.

**적용 게이트**: 아래 모든 Claim 행의 출처 지지 여부와 승인 항목이 완료되기 전에는
`src/knowledge/seed_data/book_knowledge.json`을 적용하지 않는다.

## 검수 기준

- [ ] 각 Seed Claim의 ISBN13, kind, 최종 content가 아래 표의 항목과 일치한다.
- [ ] 각 URL은 해당 도서의 공식 출판사 페이지이며 ISBN13을 확인할 수 있다.
- [ ] 출처 본문이 Claim의 의미를 직접 뒷받침하며 목차나 제목만으로 내용을 추론하지 않았다.
- [ ] Claim은 원문을 장문 복제하지 않은 짧은 한국어 재서술이다.
- [ ] 사용자 기록이나 검증되지 않은 외부 자료가 Claim에 포함되지 않았다.

## Claim별 승인 기록

| 승인 | ISBN13 | kind | Seed content | 공식 출처 URL | 출처가 의미를 지지함 |
| --- | --- | --- | --- | --- | --- |
| [ ] | `9780452284234` | 작성 시 확정 | 작성 시 확정 | https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/ | [ ] |
| [ ] | `9780374275631` | 작성 시 확정 | 작성 시 확정 | https://us.macmillan.com/books/9780374275631/thinkingfastandslow/ | [ ] |

Seed 작성자는 도서별 3~5개 Claim 각각에 행을 하나씩 만들고, 독립 대조가 끝난 행만 승인한다.
