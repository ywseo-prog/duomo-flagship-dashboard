# Streamlit Cloud 배포 가이드 (5단계)

Duomo Flagship Dashboard v0.4를 영구 URL `https://duomo-flagship.streamlit.app` 로 배포합니다.

---

## Step 1 — GitHub Repo 확인

- 저장소: https://github.com/ywseo-prog/duomo-flagship-dashboard
- 브랜치: `main`
- 진입 파일: `app.py`
- 의존성: `requirements.txt`

다음 26개 파일이 모두 main에 있어야 합니다:

```
.gitignore
.streamlit/config.toml
.streamlit/secrets.toml.example
README.md
app.py
data/.gitkeep
data/README.md
deploy_guide.md
design_system.md
modules/__init__.py
modules/as_service.py
modules/calendar.py
modules/delivery.py
modules/orders.py
modules/proposals.py
modules/rentals.py
modules/sales.py
modules/worklog.py
notion_setup_guide.md
parsers/__init__.py
parsers/worklog_parser.py
requirements.txt
utils/__init__.py
utils/notion_client.py
utils/reports.py
utils/styles.py
```

---

## Step 2 — Streamlit Cloud 로그인 & New app

1. https://share.streamlit.io 접속
2. **Sign in with GitHub** (계정: `ywseo-prog`)
3. 우상단 **New app** 클릭
4. **Deploy from existing repo** 선택

---

## Step 3 — 배포 폼 입력

| 항목 | 값 |
|---|---|
| Repository | `ywseo-prog/duomo-flagship-dashboard` |
| Branch | `main` |
| Main file path | `app.py` |
| **App URL** | `duomo-flagship` ← 핵심! |
| Python version | `3.11` (권장) |

> **App URL**을 `duomo-flagship`으로 정확히 입력해야 최종 운영 URL이 `https://duomo-flagship.streamlit.app` 이 됩니다. 한 번 정해지면 변경 시 새 배포가 필요합니다.

---

## Step 4 — Secrets 설정 (v0.4.1)

**Advanced settings** → **Secrets** 영역에 다음을 붙여넣기:

```toml
# === Notion API ===
NOTION_TOKEN = "ntn_여기에토큰입력"

# === 캘린더 (사용자 제공 - 이미 생성됨) ===
CALENDAR_DB_ID = "2bf27f0f-c317-8054-a65d-ead0fef4cbe0"

# === 주작업 (기존) ===
TASKS_DB_ID = "d0f673d9-dc62-4f20-9a6b-1090d96a5313"

# === 회의록 (플래그십 전용 신규 생성 - notion_setup_guide.md Step 5) ===
MEETING_DB_ID = "여기에-새로만든-회의록-DB-ID"

# === 발주: Notion 미연동 (발주시스템 v3 외부 운영) ===

# === Google Sheets (선택) ===
# 업무일지 시트가 공개 상태라면 생략 가능.
# 비공개 시 service account 등록 필요 (secrets.toml.example 참조)
```

> 토큰 발급은 [notion_setup_guide.md](notion_setup_guide.md) Step 1 참조.
> 회의록 DB 신규 생성: [notion_setup_guide.md Step 5](notion_setup_guide.md) 참조.

---

## Step 5 — Deploy & 검증

1. **Deploy!** 버튼 클릭
2. 빌드 로그 확인 (~2-3분 소요)
3. 배포 완료 시 자동으로 새 탭이 열림: `https://duomo-flagship.streamlit.app`

### 배포 후 체크리스트

- [ ] 사이드바 7개 모듈 정상 노출 (캘린더/업무일지/매출/제안서/발주/대여/AS)
- [ ] `🟢 Notion 연동 활성` 캡션 (Secrets 정상 시)
- [ ] 캘린더 모듈에 월간 그리드 + Today's Timeline 표시
- [ ] 매출 모듈 KPI 4종 + multi-card 정상
- [ ] 발주 모듈에 결품/긴급 알림 배너 노출
- [ ] 폰트: Pretendard + Inter 적용 (영문 KPI 숫자가 Inter로 보여야 함)
- [ ] 컬러: 골드(#C9A961) accent 강조선 / 블랙(#0A0A0A) KPI 패널 / 오프화이트(#F8F8F8) 배경

---

## 운영 / 유지보수

### 자동 재배포
`main` 브랜치에 push 시 ~1분 내 자동 재배포.

### 수동 reboot
Streamlit Cloud 우상단 ⋯ → **Reboot app** (캐시 완전 초기화)

### 5분 캐시
Notion API는 5분 TTL 캐시. 즉시 반영 필요 시:
- 사용자: 새 이벤트 생성 액션은 즉시 cache.clear 실행
- 수동: 우상단 ☰ → **Clear cache**

### Secrets 변경
App settings → Secrets → 수정 → Save → 자동 reboot.

### 로그 확인
앱 우하단 **Manage app** → 실시간 stderr/stdout 스트림.

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `ModuleNotFoundError: notion_client` | requirements.txt에 `notion-client>=2.2` 포함되었는지 확인 |
| 한글 깨짐 | config.toml `font="sans serif"` 설정 + Pretendard CDN 로드 확인 (브라우저 캐시 강제 새로고침) |
| Notion 401 | Secrets 토큰 형식 (`ntn_…`) 또는 DB Connection 미추가 |
| Google Sheets 403 | 시트 공개 또는 service account 추가 |
| 빌드 timeout (10분) | requirements.txt에 무거운 패키지 제거. reportlab은 필수 |

---

## 변경 이력

| Date | Version | Note |
|---|---|---|
| 2026-05-23 | v0.4 | 초기 배포 — 7개 모듈, Notion 양방향, 디자인 시안 5종 반영 |
| 2026-05-23 | v0.4.1 | 발주 Notion 연동 제외 / 캘린더 실 DB ID 등록 / 회의록 플래그십 전용 분리 |

---

© Duomo&Co 2026 — Streamlit Cloud Deploy Guide v0.4
