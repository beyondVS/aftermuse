# 데이터 모델: Reflection Draft

## Reflection 필드

| 필드 | 표현 | 계약 |
| --- | --- | --- |
| id | BigAutoField | 내부 PK, 공개 식별자 없음 |
| interview | OneToOneField, related_name=reflection, CASCADE | Interview당 최대 하나, 생성 후 관계 불변 |
| draft_markdown | TextField | 최초 AI 초안, 비공백 1–22,000자 |
| draft_sections | JSONField | 순서 있는 section·문단·evidence 배열, canonical 본문과 일치 |
| revised_markdown | nullable TextField | None은 수정본 없음, 저장 시 비공백 1–20,000자 |
| status | CharField, default=DRAFT | Day 10은 DRAFT만 허용 |
| completed_at | nullable DateTimeField | Day 10은 항상 None |
| created_at | auto_now_add | 최초 생성 시각 |
| updated_at | auto_now | 수정본 저장 시 갱신 |

Reading·Book·user는 Interview에서 도출한다. 별도 중복 FK 없이 서비스에서 Interview와 Reading의 book 일치를 확인한다. CASCADE는 기존 Interview 관계 관례를 따른다. 삭제 기능·실제 사용자 기록 삭제는 이번 범위가 아니다.

## Section·근거

[생성 계약](contracts/reflection-generation.md)의 검증된 sections JSON을 그대로 보존한다. section은 title·paragraphs, 문단은 text·evidence, 근거는 sequence·quote다. evidence는 같은 Interview의 확정 답변을 참조하며 사용자 Markdown 본문에는 삽입하지 않는다. section 전용 테이블은 없다.

canonical render는 각 `## 제목`, 공백 줄, 문단 text를 순서대로 연결한다. Provider의 별도 Markdown 결과를 받지 않아 두 표현의 불일치를 제거한다. 제목도 원문이 뒷받침하는 중립적 요약이어야 한다.

## 검증과 불변

- DB는 FK·unique, DRAFT 상태·완료 시각 없음, 본문 비공백·길이, 수정본 None 또는 유효 길이·비공백, JSON array shape를 CHECK로 보장한다. JSON 세부 구조·근거·render는 Application에서 검증한다.
- Model `save()` validation은 최초 interview·draft_markdown·draft_sections 변경을 차단한다. ORM update·raw SQL까지 model guard가 보호하지는 않으므로 영속 변경은 Service만 수행한다.
- create는 owner·REFLECTION_READY·관계·확정 답변을 재검증한다. Coverage 전체 완료는 추가 조건이 아니다.
- 수정본에는 AI 답변 근거 제한을 적용하지 않는다. 사용자는 자신의 생각을 추가할 수 있으며 초안 원본은 유지한다.
- 유효 본문은 잘라내거나 임의 정규화하지 않고 동일한 내용으로 저장·조회한다. 제한 밖 입력은 거부한다.

## 상태·transaction

`없음 → DRAFT`는 명시적 초안 저장, `DRAFT → DRAFT`는 수정본 저장이다. 최종 확인 없이 Interview나 Reflection을 완료하지 않는다. FINALIZING·COMPLETED와 CHECK 확장은 후속 완료 명세에서 정의한다.

create는 짧은 atomic에서 Interview를 잠그고 owner·관계·상태·현재 답변 snapshot과 생성 결과를 재검증한다. 기존 Reflection이면 conflict로 거부하며 unique가 최종 DB 방어다. 수정본 저장은 Reflection을 잠그고 owner·Draft 상태를 확인하여 revised_markdown·updated_at만 변경한다. 외부 호출은 transaction 밖에서 수행한다.

## Migration

현재 leaf 0006 뒤에 새 테이블 CreateModel을 작성한다. 기존 Interview·Turn·Coverage·Decision의 schema·데이터를 바꾸지 않으며 backfill 없음. 새 빈 테이블의 unique·CHECK를 생성 시 정의한다.

실제 sqlmigrate에서 FK와 lock을 검토하고 기존 2초 lock timeout 관례 및 안전 스킬 규칙을 적용한다. SQL이 FK NOT VALID/VALIDATE 분리를 요구하면 database/state를 일치시켜 처리한다. SQL 검수 전 무잠금·운영 무중단을 단정하지 않는다.

테스트 DB에서 이전 기록 보존·새 제약·역방향을 검증한다. 역방향은 Reflection 테이블 데이터를 삭제하므로 운영에서는 실행하지 않는다. 실제 기록 생성 후 복구는 구 코드로 복귀하고 additive 테이블을 보존하는 방식을 우선한다.
