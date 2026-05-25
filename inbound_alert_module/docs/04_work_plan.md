# 04. 작업 순서 (Work Plan)

> Claude Code에서 본 모듈 작업 시 권장 진행 순서.

---

## Phase 0. 환경 세팅 (30분)

### 0.1 1순위 이슈 결정
- [ ] Issue #1: 추승민 R&R 정책 (A/B/C/D)
- [ ] Issue #2: 발송 이력 DB 선택 (Notion 권장)

### 0.2 사전 작업
- [ ] Slack Bot 생성 및 `#조명플래그쉽파트` 채널 초대
- [ ] Slack Bot Token 발급 (`xoxb-...`)
- [ ] 4인의 Slack User ID 수집 (멘션용)
- [ ] Notion 발송이력 DB 신규 생성 + Integration 연결
- [ ] Streamlit Secrets 갱신:
```toml
SLACK_BOT_TOKEN = "xoxb-..."
SLACK_CHANNEL_ID = "C0XXXXXXX"
SLACK_USER_IDS = {
  "서영완" = "U0XXX1",
  "조이경" = "U0XXX2",
  "윤소담" = "U0XXX3",
  "추승민" = "U0XXX4",
}
INBOUND_HISTORY_DB_ID = "..."
DRIVE_DUOMO_FILE_ID = "1Bjxf2H_spRMfdsdEvpSF7ykh6JEqkP3o"
DRIVE_NOTOCASA_FILE_ID = "1NB7xqqhh0obYUAfOhJY5_W_ez8js4Xp6"
```

---

## Phase 1. PoC (1~2시간)

목표: **Drive에서 파일 가져와 4인 담당 미입고 건을 콘솔에 출력**

### 1.1 progress_loader.py 작성
```python
# src/loaders/progress_loader.py
import openpyxl
from io import BytesIO

def load_progress_files(drive_client, file_ids):
    """Drive에서 진행일지 2개 파일 다운로드 → 모든 시트의 4인 매칭 건 반환"""
    all_rows = []
    for src, fid in file_ids.items():
        xlsx_bytes = drive_client.download(fid)
        wb = openpyxl.load_workbook(BytesIO(xlsx_bytes), data_only=True)
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            rows = parse_sheet(ws, source=src, sheet_name=sheet)
            all_rows.extend(rows)
    return all_rows

def parse_sheet(ws, source, sheet_name):
    """헤더 동적 탐지 후 4인 매칭 행 반환"""
    header_row = find_header_row(ws)
    col_map = build_column_map(ws[header_row])
    
    results = []
    for row in ws.iter_rows(min_row=header_row+1, values_only=True):
        mgr = row[col_map['영업부 담당자']] if col_map['영업부 담당자'] else None
        member = match_member(mgr)
        if not member:
            continue
        results.append({
            'source': source,
            'sheet': sheet_name,
            'member': member,
            'supplier': row[col_map['Supplier']],
            'project': row[col_map['Project']],
            'po_no': row[col_map['PO No.']],
            'shipping': row[col_map['Shipping']],
            'eta': row[col_map['도착']],
            'inbound': row[col_map['입고']],
            'description': row[col_map.get('description', col_map.get('Item'))],
            'qty': row[col_map.get('qty', col_map.get('Quantity'))],
        })
    return results
```

### 1.2 owner_matcher.py 작성
```python
# src/matchers/owner_matcher.py
MEMBERS = {
    "서영완": ["서영완"],
    "조이경": ["조이경"],
    "윤소담": ["윤소담"],
    "추승민": ["추승민"],
}

def match_member(cell_value):
    if not cell_value:
        return None
    s = str(cell_value).strip()
    for std, aliases in MEMBERS.items():
        for a in aliases:
            if a in s:
                return std
    return None
```

### 1.3 콘솔 검증
```python
# main.py (PoC 버전)
from src.loaders.progress_loader import load_progress_files

rows = load_progress_files(drive_client, FILE_IDS)
print(f"4인 매칭: {len(rows)}건")
for r in rows[:20]:
    print(f"[{r['member']}] {r['supplier']} | {r['project']} | ETA: {r['eta']} | 입고: {r['inbound']}")
```

### 1.4 검증 체크리스트
- [ ] 서영완 7건+ 매칭 확인
- [ ] 조이경 7건+ 매칭 확인  
- [ ] 윤소담 2건+ 매칭 확인
- [ ] '이경아 고객님' 등 고객명 오탐 0건
- [ ] 시트별 컬럼 위치 차이 정상 처리

---

## Phase 2. MVP (1~2일)

목표: **알람 조건 판정 + Slack 실제 발송**

### 2.1 ETA Calculator
```python
# src/analyzers/eta_calculator.py
from datetime import date, datetime, timedelta
import re

def calculate_eta(progress_row, inventory_row=None, po_date=None, shipping_mode=None):
    """우선순위에 따른 ETA 산출"""
    # 1순위: 진행일지 P열 직접 값
    if progress_row.get('eta'):
        return parse_date(progress_row['eta']), 'PROGRESS_DIRECT'
    
    # 2순위: 재고엑셀 Delivery time 파싱
    if inventory_row and inventory_row.get('delivery_time'):
        parsed = parse_delivery_time(inventory_row['delivery_time'])
        if parsed:
            return parsed, 'INVENTORY_PARSED'
    
    # 3순위: PO date + 리드타임
    if po_date and shipping_mode:
        leadtime = get_leadtime(shipping_mode)  # Air: 30, Sea: 90
        return po_date + timedelta(days=leadtime), 'CALCULATED'
    
    return None, 'UNKNOWN'

def parse_delivery_time(text):
    """'5/28 입고 예정', '6/4 도착예상' 등 파싱"""
    # M/D 패턴
    m = re.search(r'\b(\d{1,2})/(\d{1,2})\b', str(text))
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        year = date.today().year
        # 과거 날짜면 차기년도
        candidate = date(year, mo, d)
        if candidate < date.today() - timedelta(days=30):
            candidate = date(year+1, mo, d)
        return candidate
    # ISO 패턴
    m = re.search(r'(20\d{2})[-./](\d{1,2})[-./](\d{1,2})', str(text))
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None
```

### 2.2 Status Judge
```python
# src/analyzers/status_judge.py
from datetime import date, timedelta

def judge_alarm_type(row, today=None):
    """알람 유형 판정"""
    today = today or date.today()
    
    inbound = row.get('inbound')
    eta, eta_source = row.get('eta_date'), row.get('eta_source')
    
    # 2차 알람: 입고완료
    if inbound:
        return 'COMPLETED', None
    
    # 1차 알람: 입항 D-14
    if eta:
        dday = (eta - today).days
        if 0 <= dday <= 14:
            return 'IMMINENT', dday
        elif dday < 0:
            return 'OVERDUE', dday  # 지연 경보 (선택)
    
    return None, None
```

### 2.3 Slack Notifier
```python
# src/notifiers/slack_notifier.py
from slack_sdk import WebClient

def send_alarm(client, channel, user_id, alarm_type, row, dday=None):
    template = TEMPLATES[alarm_type]
    text = template.format(
        member_mention=f"<@{user_id}>",
        po_no=row['po_no'],
        supplier=row['supplier'],
        project=row['project'],
        shipping=row['shipping'],
        eta=row['eta_date'].isoformat() if row.get('eta_date') else 'N/A',
        inbound=row.get('inbound', 'N/A'),
        qty=row.get('qty', 'N/A'),
        description=row.get('description', 'N/A'),
        dday=dday or 0,
    )
    response = client.chat_postMessage(channel=channel, text=text)
    return response['ts']
```

### 2.4 메시지 템플릿
`src/notifiers/message_templates.py`에 1차/2차 템플릿 분리.

### 2.5 검증 체크리스트
- [ ] 테스트 채널에 발송 성공
- [ ] @멘션 정상 작동
- [ ] 메시지 포맷 가독성 좋음
- [ ] 본 채널 (#조명플래그쉽파트) 발송 (1회 테스트)

---

## Phase 3. 발송 이력 + 중복 방지 (0.5일)

### 3.1 Notion 발송이력 DB 연동
```python
# src/storage/notion_history.py
import os
from notion_client import Client

class InboundHistory:
    def __init__(self, db_id):
        self.notion = Client(auth=os.environ['NOTION_TOKEN'])
        self.db_id = db_id
    
    def is_already_sent(self, alarm_key):
        result = self.notion.databases.query(
            database_id=self.db_id,
            filter={"property": "알람키", "title": {"equals": alarm_key}}
        )
        return len(result['results']) > 0
    
    def record(self, alarm_key, member, alarm_type, row, slack_ts):
        self.notion.pages.create(
            parent={"database_id": self.db_id},
            properties={
                "알람키": {"title": [{"text": {"content": alarm_key}}]},
                "담당자": {"select": {"name": member}},
                "알람유형": {"select": {"name": alarm_type}},
                "Supplier": {"rich_text": [{"text": {"content": row['supplier']}}]},
                "Project": {"rich_text": [{"text": {"content": row['project']}}]},
                "PO No.": {"rich_text": [{"text": {"content": row['po_no']}}]},
                "발송일시": {"date": {"start": datetime.now().isoformat()}},
                "Slack메시지링크": {"url": f"https://slack.com/.../{slack_ts}"},
                "상태": {"select": {"name": "발송완료"}},
            }
        )

def make_alarm_key(po_no, member, alarm_type):
    return f"{po_no}__{member}__{alarm_type}"
```

### 3.2 통합 main.py
```python
# src/main.py
def run():
    # 1. 진행일지 로드
    rows = load_progress_files(...)
    
    # 2. 알람 판정 + 중복 체크 + 발송
    history = InboundHistory(SECRETS['INBOUND_HISTORY_DB_ID'])
    slack = WebClient(token=SECRETS['SLACK_BOT_TOKEN'])
    
    for row in rows:
        eta, source = calculate_eta(row)
        row['eta_date'] = eta
        
        alarm_type, dday = judge_alarm_type(row)
        if not alarm_type:
            continue
        
        alarm_key = make_alarm_key(row['po_no'], row['member'], alarm_type)
        if history.is_already_sent(alarm_key):
            continue
        
        slack_ts = send_alarm(slack, SECRETS['SLACK_CHANNEL_ID'], 
                              SECRETS['SLACK_USER_IDS'][row['member']], 
                              alarm_type, row, dday)
        history.record(alarm_key, row['member'], alarm_type, row, slack_ts)
        
    print("✅ 입고 알람 스캔 완료")
```

### 3.3 검증
- [ ] 동일 알람 2회 발송 안 됨
- [ ] Notion DB에 정확히 기록
- [ ] 발송 실패 시 graceful degradation

---

## Phase 4. Streamlit 대시보드 통합 (0.5일)

### 4.1 사이드바에 '📦 입고 추적' 메뉴 추가
```python
# 기존 app.py 수정
import streamlit as st

with st.sidebar:
    page = st.radio("메뉴", ["캘린더", "주작업", "회의록", "📦 입고 추적"])

if page == "📦 입고 추적":
    from src.main import run, get_dashboard_data
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 지금 스캔", type="primary"):
            with st.spinner("진행일지 분석 중..."):
                run()
            st.success("스캔 완료")
    
    # 4인별 미입고 현황 표시
    data = get_dashboard_data()
    for member in ['서영완', '조이경', '윤소담', '추승민']:
        with st.expander(f"{member} - 미입고 {len(data[member])}건"):
            st.dataframe(data[member])
```

### 4.2 검증
- [ ] 사이드바 4번째 모듈로 표시
- [ ] 4인별 현황 정확히 표시
- [ ] '지금 스캔' 버튼 동작

---

## Phase 5. 운영 자동화 (추후)

- [ ] GitHub Actions로 매일 오전 9시 자동 실행
- [ ] 실행 결과 Slack 시스템 채널에 로그
- [ ] 발주시스템 v3와 통합 검토

---

## 🎯 마일스톤 체크리스트

| 마일스톤 | 완료 기준 | 상태 |
|---|---|---|
| M1: PoC 완료 | 콘솔에 4인 미입고 건 정확히 출력 | ☐ |
| M2: MVP 완료 | 실제 Slack 테스트 발송 성공 | ☐ |
| M3: 중복방지 | 동일 알람 2회 발송 안 됨 확인 | ☐ |
| M4: 대시보드 | OWNER 프로젝트 사이드바 통합 | ☐ |
| M5: 운영 | 자동 스케줄 + 1주일 안정 운영 | ☐ |
| M6: 통합 | 발주시스템 v3와 통합 | ☐ |
