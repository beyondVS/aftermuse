# Day 09 데이터 모델

## 기존 영속 엔터티

| 엔터티 | 필요한 정보 | 관계와 제약 |
|---|---|---|
| Reading | 소유 사용자, 도서, `want_to_read`·`reading`·`completed`, 완독일, 변경 시각 | 사용자 소유 기록. 상태와 Interview 유무에 따라 분류한다. |
| Book | 제목·저자 등 실제 서지 정보 | Reading의 도서 정보를 Home에 표시한다. |
| Interview | Reading, 도서, `IN_PROGRESS`·`REFLECTION_READY`·`COMPLETED` | 완독 Reading당 최대 한 개. `IN_PROGRESS`만 이어하기 대상이다. |
| InterviewTurn | 순서, 질문, 확정 답변, 질문 생략 상태 | 기존 상세에서 현재 단계를 판별한다. |
| InterviewProgressDecision | 확정 답변 뒤 보류된 선택 | 기존 상세에서 Soft Stop·상한 선택 대기를 판별한다. |

## 파생 표시 항목

Home 카드는 별도 테이블 없이 사용자 소유 Reading과 연결된 Interview 상태로 파생한다.

| 조건 | Home 영역 | 행동 |
|---|---|---|
| Reading `want_to_read` 또는 `reading` | 지금 읽고 있는 책 | Reading 상세 |
| Reading `completed`, Interview 없음 | 사색을 기다리는 책 | 해당 Reading의 Interview 시작 화면 |
| Interview `IN_PROGRESS` | 진행 중인 인터뷰 | 기존 Interview 상세 |
| Interview `REFLECTION_READY` 또는 `COMPLETED` | Day 09 영역에 표시하지 않음 | Day 12 Reflection 연계 대상 |

각 영역은 최신 변경 시각과 식별자 역순으로 정렬한다. 대상이 없으면 빈 상태를 표시하고 카드 링크는 같은 카드의 식별자만 사용한다.

## 상태 전이와 불변조건

- Home GET과 이어하기 GET은 Reading·Interview·Turn·진행 선택을 생성하거나 변경하지 않는다.
- Reading 상태 변경과 Interview 시작·진행은 기존 흐름이 수행한다. 다음 Home 방문은 저장된 최신 상태를 반영한다.
- Interview가 `IN_PROGRESS`를 벗어나면 이어하기 카드에서 제거한다. 한 Reading에 진행 중 Interview와 새 시작 카드를 동시에 만들지 않는다.
- 타 사용자 소유 기록은 Home 조회 결과에 넣지 않고 기존 Interview 상세에서도 소유권을 다시 검사한다.
- 새 필드·제약·마이그레이션은 필요하지 않다.
