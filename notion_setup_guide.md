# Notion 셋업 가이드 (Duomo Flagship Dashboard v0.4.1)

본 가이드는 대시보드를 Notion DB와 양방향 연결하기 위한 단계별 설정입니다.

> **변경 (v0.4.1):**
> - ❌ **발주마스터 Notion 연동 제외** — 발주시스템 v3 (외부) 별도 운영
> - ✅ **캘린더 DB**: 사용자 워크스페이스에 이미 생성됨 → ID 등록만
> - 🆕 **회의록 DB**: 플래그십 전용으로 **신규 생성** 필요 (기존 통합 회의록 X)

---

## 1. Internal Integration 생성

1. https://www.notion.so/my-integrations 접속
2. **+ New integration** 클릭
3. 이름: `Duomo Flagship Dashboard`
4. **Type**: Internal
5. **Capabilities**: ✓ Read content / ✓ Update content / ✓ Insert content
6. **Submit** → 표시되는 **Internal Integration Secret** (`ntn_xxxxxxxxxxxx…`) 복사 = `NOTION_TOKEN`

> ⚠ Secret은 1회만 표시되며 분실 시 재발급 필요.

---

## 2. 연결할 DB 4개 (발주 제외)

| 용도 | 상태 | DB ID |
|---|---|---|
| 📅 캘린더 | ✅ 생성 완료 (사용자 제공) | `2bf27f0f-c317-8054-a65d-ead0fef4cbe0` |
| 📋 주작업 (태스크) | ✅ 기존 사용 | `d0f673d9-dc62-4f20-9a6b-1090d96a5313` |
| 📝 회의록 (플래그십 전용) | 🆕 **신규 생성 필요** | — (Step 5) |
| 🚢 입고알람 이력 | 🆕 **신규 생성 필요** | — (Step 5-B) |

> 발주 모듈은 더미 데이터로 동작합니다. 추후 발주시스템 v3 연동은 별도 작업.
> 입고알람 이력 DB는 "확인 처리"한 알람을 기록해 다음 스캔 시 중복 노출을 방지합니다.

---

## 3. 각 DB에 Integration 연결 (3개)

위 표의 **캘린더**, **주작업**, **(신규 생성한) 회의록** DB 각각:

1. DB 페이지 우상단 **⋯ (More)** → **Connections** → **+ Add connections**
2. `Duomo Flagship Dashboard` 선택 → **Confirm**

미연결 시 더미 데이터로 fallback.

---

## 4. 캘린더 DB 컬럼 확인

이미 생성된 캘린더 DB(`2bf27f0fc3178054a65dead0fef4cbe0`)가 아래 컬럼을 갖춰야 합니다. 누락 시 직접 추가:

| 컬럼 이름 | Type | 옵션 |
|---|---|---|
| **이름** | Title | (기본) |
| **날짜** | Date | 시간 포함 권장 |
| **분류** | Select | 발주마감, 매장이벤트, 시몬스미팅, VIP컨설팅, 인플루언서협찬, 교육, 휴가, 회의, 출장, 기타 |
| **담당자** | Text 또는 People | |
| **메모** | Text | |

### 분류 옵션 컬러 매핑 (Notion에서 직접 지정 권장)

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

---

## 5. 회의록 DB 신규 생성 (플래그십 전용)

기존 통합 회의록과 분리, 플래그십 운영 회의만 별도 관리.

### 5-1. DB 생성

1. 임의 Notion 페이지 → `/database` → **Database - Full page**
2. 이름: `플래그십 회의록`
3. 아이콘: 📝 / 커버는 선택

### 5-2. 컬럼 스키마

| 컬럼 이름 | Type | 옵션 / 비고 |
|---|---|---|
| **이름** | Title | 회의 제목 (예: "5월 4주차 정기 회의") |
| **일시** | Date | 시간 포함 |
| **분류** | Select | 정기 / 긴급 / 시몬스 / VIP / 교육 / 외부미팅 / 기타 |
| **참석자** | Multi-select 또는 Text | 서영완, 이혜지, 신정훈, 박OO 등 |
| **주관자** | Text 또는 People | |
| **장소** | Text | 4F 사무실, ZOOM, 시몬스 사옥 등 |
| **결정사항** | Text | 핵심 결정 BLUF |
| **액션아이템** | Text 또는 Relation → 주작업 | 후속 태스크 연결 |
| **태그** | Multi-select | 매출 / 발주 / 제안서 / 대여 / AS / 캘린더 / 인사 |
| **링크** | URL | Drive 진행일지 / 자료 링크 |

### 5-3. DB ID 복사

생성한 DB URL: `https://www.notion.so/{workspace}/{32자hash}?v=...`
- 32자 hash가 DB ID
- 대시보드 코드가 자동으로 hyphen 형식으로 변환하므로 양식 무관

### 5-4. Integration 연결

위 **3단계**와 동일 → `Duomo Flagship Dashboard` integration 추가.

---

## 5-B. 입고알람 이력 DB 신규 생성 🆕

입고 추적 모듈의 "확인 처리" 액션을 기록해 동일 알람을 다음 스캔에서 숨깁니다.

### 5-B-1. DB 생성

1. 임의 Notion 페이지 → `/database` → **Database - Full page**
2. 이름: `플래그십 입고알람 이력`
3. 아이콘: 🚢

### 5-B-2. 컬럼 스키마 (정확한 이름·타입 필수)

| 컬럼 이름 | Type | 옵션 |
|---|---|---|
| **알람키** | Title | (코드가 자동 생성: `{PO_NO}__{member}__{alarm_type}`) |
| **담당자** | Select | 서영완 / 조이경 / 윤소담 / 추승민 |
| **알람유형** | Select | 입항임박_D14 / 입고완료 |
| **Supplier** | Text | |
| **Project** | Text | |
| **PO No.** | Text | |
| **ETA** | Date | 입항 임박 알람용 |
| **입고일** | Date | 입고완료 알람용 |
| **발송일시** | Date | timestamp 자동 |
| **상태** | Select | 기록완료 / 재확인필요 |
| **비고** | Text | |

> ⚠ "알람키"는 반드시 **Title 타입** + 정확히 그 이름이어야 합니다 (중복 체크 키).

### 5-B-3. DB ID 복사 + Integration 연결

위 5-3, 5-4와 동일 방식.

---

## 6. 주작업 DB 권장 컬럼

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

## 7. Streamlit Secrets 등록

### 로컬 (개발)

`.streamlit/secrets.toml` 생성:

```toml
NOTION_TOKEN = "ntn_여기에토큰입력"

# 캘린더 (사용자 제공 - 이미 생성됨)
CALENDAR_DB_ID = "2bf27f0f-c317-8054-a65d-ead0fef4cbe0"

# 주작업 (기존)
TASKS_DB_ID = "d0f673d9-dc62-4f20-9a6b-1090d96a5313"

# 회의록 (5단계에서 생성한 신규 DB ID)
MEETING_DB_ID = "여기에-새로만든-회의록-DB-ID"

# 입고알람 이력 (5-B 단계에서 생성)
INBOUND_HISTORY_DB_ID = "여기에-새로만든-입고알람이력-DB-ID"

# 발주: Notion 미연동 (v3 외부 시스템)
```

### Streamlit Cloud (배포)

App settings → **Secrets** → 위 내용 그대로 붙여넣기 → **Save**.
저장 후 앱 자동 재기동 (~30초).

---

## 8. 동작 확인

| 동작 | 기대 결과 |
|---|---|
| 사이드바 캡션 | `🟢 Notion 연동 활성` |
| 캘린더 모듈 월간 그리드 | 사용자 생성 DB 이벤트 렌더링 |
| 신규 이벤트 추가 폼 | Notion DB에 즉시 row 생성 |
| 발주 모듈 | 더미 데이터 (정상 — 발주 Notion 연동 안 함) |
| 입고 추적 모듈 | 진행일지 .xlsx 2개 업로드 → 4인별 미입고/임박/완료 분류 |
| 입고 알람 "확인 처리" 버튼 | Notion 이력 DB에 row 추가, 다음 스캔에서 숨김 |
| 5분 캐시 | TTL 자동 갱신, 즉시 반영 필요 시 `Cmd/Ctrl+R` |

---

## 9. 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| `🟢` 안 뜨고 더미만 나옴 | `NOTION_TOKEN` 미입력 또는 형식 오류 |
| DB는 보이는데 빈 결과 | DB에 Integration Connection 미추가 (3단계) |
| 이벤트 생성 실패 | DB 컬럼명 불일치 — 4단계의 정확한 컬럼명 사용 |
| 회의록 위젯 비활성 | `MEETING_DB_ID` 미입력 — 5단계 완료 후 입력 |
| 5분간 변경사항 미반영 | TTL 캐시. `Cmd/Ctrl+R` 강제 새로고침 |

---

© Duomo&Co 2026 — Notion Integration Guide v0.5 (입고알람 8번째 모듈 추가)
