# Notion 셋업 가이드 (Duomo Flagship Dashboard v0.4)

본 가이드는 대시보드의 7개 모듈을 Notion DB와 양방향으로 연결하기 위한 단계별 설정입니다.

---

## 1. Internal Integration 생성

1. https://www.notion.so/my-integrations 접속
2. **+ New integration** 클릭
3. 이름: `Duomo Flagship Dashboard`
4. **Type**: Internal
5. **Capabilities**: ✓ Read content / ✓ Update content / ✓ Insert content
6. **Submit** 후 표시되는 **Internal Integration Secret** (`ntn_xxxxxxxxxxxx…`)을 복사 — 이것이 `NOTION_TOKEN`.

> ⚠ Secret은 1회만 표시되며 분실 시 재발급 필요.

---

## 2. 발견된 Duomo Notion DB (이미 매핑됨)

대시보드는 아래 3개 DB ID를 기본값으로 사용합니다. 별도 입력 불필요 (단, **3에서 Integration Connection만 추가**해야 합니다).

| 용도 | DB 이름 | DB ID |
|---|---|---|
| 발주마스터 | 발주 권고 마스터 | `b4a420d2-9bdc-4971-b1c9-a19306ad8cbe` |
| 주작업 (태스크) | 주작업 | `d0f673d9-dc62-4f20-9a6b-1090d96a5313` |
| 회의록 | 회의록 | `0699ce3b-e55f-4995-8242-a5098c50fcc6` |

---

## 3. 각 DB에 Integration 연결

위 3개 DB 페이지를 각각 열고:

1. 우상단 **⋯ (More)** → **Connections** → **+ Add connections**
2. 방금 만든 `Duomo Flagship Dashboard` 선택 → **Confirm**

3개 DB 모두 동일하게 수행. 미연결 시 대시보드는 더미 데이터로 fallback.

---

## 4. 캘린더 DB 생성 (권장)

기존 "주작업"의 날짜 컬럼으로도 fallback 동작하지만, **별도 캘린더 DB** 생성을 권장합니다.

### 4-1. 새 DB 생성

1. 임의 Notion 페이지에서 `/database` → **Database - Full page**
2. 이름: `Duomo 팀 캘린더`
3. 아래 컬럼 추가:

| 컬럼 이름 | Type | 옵션 |
|---|---|---|
| 이름 | Title | (기본) |
| 날짜 | Date | 시간 포함 |
| 분류 | Select | 발주마감, 매장이벤트, 시몬스미팅, VIP컨설팅, 인플루언서협찬, 교육, 휴가, 회의, 출장, 기타 |
| 담당자 | Text (또는 People) | |
| 메모 | Text | |

### 4-2. 분류 옵션 컬러 매핑 (Notion에서 직접 지정)

| 분류 | Notion Color | 대시보드 HEX |
|---|---|---|
| 발주마감 | Red | `#D32F2F` |
| 매장이벤트 | Blue | `#1976D2` |
| 시몬스미팅 | Purple | `#7B1FA2` |
| VIP컨설팅 | Pink | `#C2185B` |
| 인플루언서협찬 | Orange | `#F57C00` |
| 교육 | Green | `#388E3C` |
| 휴가 | Gray | `#9E9E9E` |
| 회의 | Default | `#455A64` |
| 출장 | Brown | `#5D4037` |
| 기타 | Default | `#607D8B` |

### 4-3. DB ID 복사

생성한 DB 페이지 URL: `https://www.notion.so/{workspace}/{DB_ID}?v=...`
중간 32자 hyphen 포함 hash가 `CALENDAR_DB_ID`. (예: `12345678-1234-1234-1234-123456789012`)

### 4-4. Integration 연결

위 3과 동일하게 `Duomo Flagship Dashboard` integration 연결.

---

## 5. 주작업 DB 권장 컬럼

대시보드의 태스크 위젯은 아래 컬럼명을 가정합니다 (없으면 자동 생성/생략):

| 컬럼 이름 | Type |
|---|---|
| 이름 | Title |
| 상태 | Select (대기 / 진행중 / 완료 / 보류 / 취소) |
| 우선순위 | Select (긴급 / 높음 / 보통 / 낮음) |
| 마감일 | Date |
| 담당자 | Text 또는 People |
| 태그 | Multi-select (매출 / 제안서 / 발주 / 대여 / AS / 캘린더 / 업무일지) |
| 내용 | Text |

---

## 6. Streamlit Secrets 등록

### 로컬 (개발)

`dashboard/.streamlit/secrets.toml` 생성:

```toml
NOTION_TOKEN = "ntn_여기에토큰입력"

# 기본값 그대로 사용 가능
ORDERS_DB_ID = "b4a420d2-9bdc-4971-b1c9-a19306ad8cbe"
TASKS_DB_ID = "d0f673d9-dc62-4f20-9a6b-1090d96a5313"
MEETING_DB_ID = "0699ce3b-e55f-4995-8242-a5098c50fcc6"

# 4에서 생성한 캘린더 DB ID
CALENDAR_DB_ID = "여기에-생성한-캘린더-DB-ID"
```

### Streamlit Cloud (배포)

App Settings → **Secrets** → 위 내용 그대로 붙여넣기 → Save.

---

## 7. 동작 확인

| 동작 | 기대 결과 |
|---|---|
| 사이드바 캡션 | `🟢 Notion 연동 활성` |
| 캘린더 모듈 | 이벤트 카드 표시됨 |
| 발주 상황 | 결품/긴급 SKU 알람 노출 |
| 신규 이벤트 추가 | Notion DB에 즉시 row 생성 |
| 5분 캐시 | 자동 갱신, 강제는 `Cmd+R` |

---

## 8. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `🟢` 안 뜨고 더미만 나옴 | Secrets > NOTION_TOKEN 미입력 또는 형식 오류 |
| DB는 보이는데 빈 결과 | DB에 Integration Connection 미추가 (3단계) |
| 이벤트 생성 실패 | DB 컬럼명이 가이드와 다름 — 컬럼명 정확히 일치 필요 |
| 5분간 변경사항 미반영 | TTL 캐시. 강제 새로고침 또는 5분 대기 |

---

© Duomo&Co 2026 — Notion Integration Guide v0.4
