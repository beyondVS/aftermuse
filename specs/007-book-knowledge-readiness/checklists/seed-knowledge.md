# Seed Knowledge 출처 검수 체크리스트

**목적**: 공용 Book Knowledge로 적용할 각 Claim이 공식 출처의 내용으로 뒷받침되는지
사람이 확인하고 승인한 증거를 남긴다.

**적용 게이트**: 아래 모든 Claim 행의 출처 지지 여부와 승인 항목이 완료되기 전에는
`src/knowledge/seed_data/book_knowledge.json`을 적용하지 않는다.

## 검수 기준

- [x] 각 Seed Claim의 ISBN13, kind, 최종 content가 아래 표의 항목과 일치한다.
- [x] 각 URL은 해당 도서의 공식 출판사 페이지이며 ISBN13을 확인할 수 있다.
- [x] 출처 본문이 Claim의 의미를 직접 뒷받침하며 목차나 제목만으로 내용을 추론하지 않았다.
- [x] Claim은 원문을 장문 복제하지 않은 짧은 한국어 재서술이다.
- [x] 사용자 기록이나 검증되지 않은 외부 자료가 Claim에 포함되지 않았다.

## Claim별 승인 기록

| 승인 | ISBN13 | kind | Seed content | 공식 출처 URL | 출처가 의미를 지지함 |
| --- | --- | --- | --- | --- | --- |
| [x] | `9780452284234` | `theme` | 정부는 서사를 통제하기 위해 진실과 역사를 조작한다. | https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/ | [x] |
| [x] | `9780452284234` | `character` | 윈스턴 스미스는 진리부에서 당의 요구에 맞춰 역사를 다시 쓴다. | https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/ | [x] |
| [x] | `9780452284234` | `argument` | 당은 권력 자체를 추구하며 사상범죄를 저지르는 사람들을 박해한다. | https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/ | [x] |
| [x] | `9780452284234` | `event` | 윈스턴이 스스로 생각하기 시작해도 빅 브라더의 감시에서 벗어나지 못한다. | https://www.penguinrandomhouse.com/books/326569/1984-by-george-orwell-with-a-foreword-by-thomas-pynchon/ | [x] |
| [x] | `9780374275631` | `concept` | 시스템 1은 빠르고 직관적이며 감정적으로 작동한다. | https://us.macmillan.com/books/9780374275631/thinkingfastandslow/ | [x] |
| [x] | `9780374275631` | `concept` | 시스템 2는 더 느리고 숙고하며 논리적으로 작동한다. | https://us.macmillan.com/books/9780374275631/thinkingfastandslow/ | [x] |
| [x] | `9780374275631` | `argument` | 두 사고 시스템은 인간의 판단과 결정을 함께 형성한다. | https://us.macmillan.com/books/9780374275631/thinkingfastandslow/ | [x] |
| [x] | `9780374275631` | `theme` | 직관을 신뢰할 수 있는 경우와 그렇지 않은 경우를 이해하면 느린 사고의 이점을 활용할 수 있다. | https://us.macmillan.com/books/9780374275631/thinkingfastandslow/ | [x] |

각 Claim은 공식 출판사 페이지의 Book Description 또는 Book Details 본문과 2026-09-08에
독립 대조했다. 이 표의 ISBN13, kind, Seed content를 승인된 Seed 데이터의 기준 원본으로
사용한다.
