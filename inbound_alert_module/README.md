# 📦 입고알람 모듈 (inbound_alert)

> **OWNER / 플래그십 대쉬보드** 프로젝트 추가 모듈
> Duomo&Co 조명플래그십파트 4인 발주건 입고 알람 자동화
> 작성: 2026-05-23 | Chat 세션 분석 결과 인수인계

---

## 🎯 모듈 목적 (한 줄)

**재고 엑셀(Source 1)에서 4인 이름 발견 → 진행일지 시트(Source 2)에서 입고일정 더블체크 → Slack 알람**

기존 플래그십 대쉬보드(캘린더·주작업·회의록 Notion DB 연동)에 **'입고 추적' 4번째 모듈**로 추가.

---

## 🏗 기존 프로젝트와의 관계

```
OWNER / 플래그십 대쉬보드 (Streamlit Cloud)
├── 캘린더 모듈      (Notion DB: 2bf27f0f...)
├── 주작업 모듈      (Notion DB: d0f673d9...)
├── 회의록 모듈      (Notion DB: 신규 생성 중)
└── ★ 입고알람 모듈  (Notion DB: 신규, 발송이력)  ← 본 모듈
```

기존 Streamlit Cloud Secrets 구조 그대로 활용 (`NOTION_TOKEN` 공용):
```toml
# .streamlit/secrets.toml 추가 항목
INBOUND_HISTORY_DB_ID = "신규-발송이력-DB-ID"
SLACK_BOT_TOKEN       = "xoxb-..."
SLACK_CHANNEL         = "C0XXXXXXX"  # #조명플래그쉽파트 채널 ID
DRIVE_DUOMO_FILE_ID   = "1Bjxf2H_spRMfdsdEvpSF7ykh6JEqkP3o"
DRIVE_NOTOCASA_FILE_ID = "1NB7xqqhh0obYUAfOhJY5_W_ez8js4Xp6"
```

---

## 📂 모듈 구조

```
inbound_alert_module/
├── README.md                          ← 본 문서 (시작점)
├── docs/
│   ├── 01_project_context.md          ← 전체 컨텍스트·결정사항
│   ├── 02_data_structure.md           ← 2-Source 컬럼 매핑·실측
│   ├── 03_open_issues.md              ← TBD 항목 체크리스트
│   └── 04_work_plan.md                ← Claude Code 권장 진행 순서
├── config/
│   ├── members.yaml                   ← 4인 R&R 매핑
│   ├── sheets_mapping.yaml            ← 시트별 컬럼 위치
│   └── brands_leadtime.yaml           ← 브랜드별 리드타임(v3 기준)
├── src/
│   ├── loaders/
│   │   ├── inventory_loader.py        ← Source 1: 재고 엑셀(카드형)
│   │   └── progress_loader.py         ← Source 2: 진행일지(표형)
│   ├── matchers/
│   │   ├── owner_matcher.py           ← 4인 매칭
│   │   └── cross_matcher.py           ← Source 1-2 교차 매칭
│   ├── analyzers/
│   │   ├── eta_calculator.py          ← 입항예정일 산출
│   │   └── status_judge.py            ← 입고완료 판단
│   ├── notifiers/
│   │   ├── slack_notifier.py          ← Slack 발송
│   │   └── message_templates.py       ← 메시지 템플릿
│   ├── storage/
│   │   └── notion_history.py          ← Notion DB 발송이력
│   └── main.py                        ← 통합 실행 엔트리포인트
└── samples/
    └── parse_progress_poc.py          ← Chat 세션 PoC 스크립트
```

---

## 🚀 Claude Code 진입 후 첫 5분

```bash
# 1. 모듈 디렉토리로 이동
cd inbound_alert_module

# 2. 핵심 문서 4개 순서대로 읽기
cat docs/01_project_context.md      # 무엇을 만드는가
cat docs/02_data_structure.md       # 데이터는 어떻게 생겼는가
cat docs/03_open_issues.md          # 무엇이 미정인가
cat docs/04_work_plan.md            # 어떤 순서로 작업할까

# 3. 설정 파일 확인
cat config/members.yaml
cat config/sheets_mapping.yaml

# 4. PoC 스크립트 검토 (Chat 세션에서 실제 시도한 코드)
cat samples/parse_progress_poc.py
```

---

## 🔑 확정 사항 (변경 불필요)

| 항목 | 확정값 |
|---|---|
| 알람 채널 | Slack `#조명플래그쉽파트` |
| 멘션 방식 | 담당자별 개별 @멘션 |
| R&R 매칭 키 | 진행일지 **E열 '영업부 담당자'** |
| 입고완료 판단 | 진행일지 **'입고' 컬럼에 날짜 값 존재** |
| ETA 1순위 | 진행일지 **'도착/ETA' 컬럼** |
| ETA 2순위 | 재고엑셀 `Delivery time` 텍스트 파싱 |
| ETA 3순위 | PO date + 리드타임 자동 계산 |
| 1차 알람 | 입항예정 **D-14** |
| 2차 알람 | **입고완료** 신규 감지 |

---

## ⚠️ 미해결 이슈 (PoC 전 결정)

| # | 항목 | 옵션 |
|---|---|---|
| 1 | 추승민 R&R 정책 | A: 4인 통합 / B: 본인만(현재 0건) / C: 시스템관리자 |
| 2 | 발송 이력 DB | **A: Notion DB** (권장, 기존 인프라) / B: SQLite / C: JSON |
| 3 | Source 1-2 교차 매칭 키 | PO No. 우선 / Project 보조 |
| 4 | 실행 스케줄 | Streamlit 수동 트리거 / cron / GitHub Actions |

상세는 `docs/03_open_issues.md` 참조.

---

## 📊 데이터 소스 요약

### Source 1: 재고 엑셀 (수동 업로드, 카드형)
- `B&B 재고리스트.xlsb` (110MB)
- `PF_CC 재고리스트.xlsx` (272MB)
- `브랜드별 재고리스트.xlsx`
- 구조: PO 1건 = 1블록(10~30행), 메타정보(우측 I/J열) + 품목라인(좌측 B~H열)
- **선점 판단**: M열에 영업담당자명 표기 (4인 이름은 직접 없음 → 추가 분석 필요)

### Source 2: 진행일지 (Google Drive 실시간, 표형)
- `DUOMO 이동가구 진행일지.xlsx` (ID: `1Bjxf2H_spRMfdsdEvpSF7ykh6JEqkP3o`)
- `NOTO CASA 이동가구 진행일지.xlsx` (ID: `1NB7xqqhh0obYUAfOhJY5_W_ez8js4Xp6`)
- 소유자: lilychoi@duomonco.com (공유 권한)
- **핵심 컬럼**: B(Supplier) / C(Project) / **E(영업부 담당자)** / F(PO No.) / M(Shipping) / **P(ETA)** / **Q(입고)**

---

## 🐛 핵심 함정 5가지 (놓치면 시간 손실)

1. **MCP `read_file_content`는 행 구분자 누락** → `download_file_content` + 승인 필요
2. **'이경'은 고객명 빈출** → 풀네임 '조이경'으로만 매칭
3. **시트별 컬럼 위치 1~2칸씩 다름** → `sheets_mapping.yaml` 필수
4. **추승민은 진행일지 E열 미등장** → R&R 정책 별도 결정
5. **재고엑셀 M열에 4인 이름 직접 없음** → '선점' 정의 재검토 필요 (시즌별 추가 분석)

---

## ⏱ 권장 작업 일정

| Phase | 작업 | 소요 | 산출물 |
|---|---|---|---|
| 0 | 1순위 이슈 결정, MCP 인증 확인 | 30분 | 결정 메모 |
| 1 | PoC: Drive fetch → 4인 매칭 → 콘솔 출력 | 1~2시간 | `main.py` 초안 |
| 2 | MVP: 2-Source 통합 + 알람 판정 + Slack 발송 | 1~2일 | 동작하는 시스템 |
| 3 | Notion 발송이력 DB + 중복 방지 | 0.5일 | 운영 안정성 |
| 4 | Streamlit 대시보드 통합 | 0.5일 | 4번째 모듈 |
| 5 | 발주시스템 v3 통합 검토 | 추후 | 통합 아키텍처 |

---

## 📞 컨텍스트 키워드 (검색용)

- **OWNER / 플래그십 대쉬보드** (상위 Cowork 프로젝트)
- **발주시스템 v3** (선행 프로젝트, 통합 검토 대상)
- **조명플래그십파트** (Slack 채널 / 팀명)
- **코워크 프로젝트** (실행 환경)
- **lilychoi** (진행일지 소유자, Drive 공유)
