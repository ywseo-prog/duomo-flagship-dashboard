"""
Notion API 래퍼 — 실 DB ID 자동매핑 / 토큰 미입력 시 더미 fallback
- 발주마스터: b4a420d2-9bdc-4971-b1c9-a19306ad8cbe
- 주작업    : d0f673d9-dc62-4f20-9a6b-1090d96a5313
- 회의록    : 0699ce3b-e55f-4995-8242-a5098c50fcc6
- 캘린더    : st.secrets["CALENDAR_DB_ID"] (선택, 미입력 시 주작업 fallback)
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


DEFAULT_DB_IDS = {
    # 발주: Notion 연동 제외 — 발주시스템 v3 (외부) 사용. 더미 fallback만 동작.
    "orders":   "",
    "tasks":    "d0f673d9-dc62-4f20-9a6b-1090d96a5313",
    # 회의록: 기존 통합본 → 플래그십 전용 신규 DB 사용 권장 (secrets로 override)
    "meeting":  "",
    "calendar": "",
}

CATEGORY_COLORS = {
    "발주마감":     "#D32F2F",
    "매장이벤트":   "#1976D2",
    "시몬스미팅":   "#7B1FA2",
    "VIP컨설팅":    "#C2185B",
    "인플루언서협찬": "#F57C00",
    "교육":         "#388E3C",
    "휴가":         "#9E9E9E",
    "회의":         "#455A64",
    "출장":         "#5D4037",
    "기타":         "#607D8B",
}

STATUS_COLORS = {
    "대기":     "#999999",
    "진행중":   "#1976D2",
    "완료":     "#2E7D32",
    "보류":     "#F57C00",
    "취소":     "#D32F2F",
    "검토중":   "#7B1FA2",
    "승인":     "#388E3C",
}

PRIORITY_COLORS = {
    "긴급":   "#D32F2F",
    "높음":   "#FF6B35",
    "보통":   "#1976D2",
    "낮음":   "#999999",
}


def _get_secret(key: str, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


def _normalize_db_id(raw: str) -> str:
    """Notion DB ID 정규화 — 32자 no-hyphen이면 8-4-4-4-12 hyphen 형식으로 변환.
    API는 양쪽 다 받지만 일관성·디버깅 편의를 위해 통일.
    """
    s = (raw or "").strip().replace("-", "")
    if len(s) == 32 and all(c in "0123456789abcdefABCDEF" for c in s):
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    return raw or ""


@st.cache_resource
def get_notion_client():
    """notion-client 인스턴스 lazy init. 토큰 없으면 None."""
    token = _get_secret("NOTION_TOKEN")
    if not token or token.startswith("ntn_xxxx"):
        return None
    try:
        from notion_client import Client
        return Client(auth=token)
    except Exception as e:
        st.warning(f"Notion 클라이언트 초기화 실패: {e}")
        return None


def get_db_id(key: str) -> str:
    """secrets > 기본값 순으로 DB ID 조회. key: orders|tasks|meeting|calendar"""
    secret_key = {
        "orders": "ORDERS_DB_ID", "tasks": "TASKS_DB_ID",
        "meeting": "MEETING_DB_ID", "calendar": "CALENDAR_DB_ID",
    }.get(key)
    val = _get_secret(secret_key) if secret_key else None
    return _normalize_db_id(val or DEFAULT_DB_IDS.get(key, ""))


def _extract_text(prop):
    """Notion property → plain text"""
    if not prop: return ""
    t = prop.get("type")
    if t == "title":
        return "".join(x.get("plain_text","") for x in prop.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text","") for x in prop.get("rich_text", []))
    if t == "select":
        s = prop.get("select")
        return s.get("name") if s else ""
    if t == "multi_select":
        return ", ".join(x.get("name","") for x in prop.get("multi_select", []))
    if t == "status":
        s = prop.get("status")
        return s.get("name") if s else ""
    if t == "number":
        return prop.get("number") or 0
    if t == "date":
        d = prop.get("date")
        return d.get("start") if d else ""
    if t == "people":
        return ", ".join(p.get("name","") for p in prop.get("people", []))
    if t == "checkbox":
        return prop.get("checkbox", False)
    if t == "url":
        return prop.get("url","")
    return ""


def _props_to_dict(props: dict) -> dict:
    return {k: _extract_text(v) for k, v in props.items()}


@st.cache_data(ttl=300)
def fetch_calendar_events(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """캘린더 DB → DataFrame. 캘린더 DB 미설정 시 주작업 DB 날짜로 fallback."""
    client = get_notion_client()
    if not client:
        return _dummy_calendar()
    db_id = get_db_id("calendar") or get_db_id("tasks")
    if not db_id:
        return _dummy_calendar()
    try:
        results = client.databases.query(database_id=db_id, page_size=100).get("results", [])
        rows = []
        for r in results:
            d = _props_to_dict(r.get("properties", {}))
            d["_id"] = r.get("id")
            rows.append(d)
        df = pd.DataFrame(rows)
        if "날짜" in df.columns:
            df["date"] = pd.to_datetime(df["날짜"], errors="coerce")
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception as e:
        st.warning(f"캘린더 조회 실패 (더미로 대체): {e}")
        return _dummy_calendar()


@st.cache_data(ttl=300)
def fetch_tasks(filter_status: str = None) -> pd.DataFrame:
    """주작업 DB → DataFrame"""
    client = get_notion_client()
    if not client:
        return _dummy_tasks()
    db_id = get_db_id("tasks")
    if not db_id:
        return _dummy_tasks()
    try:
        kwargs = {"database_id": db_id, "page_size": 100}
        results = client.databases.query(**kwargs).get("results", [])
        rows = []
        for r in results:
            d = _props_to_dict(r.get("properties", {}))
            d["_id"] = r.get("id")
            rows.append(d)
        df = pd.DataFrame(rows)
        if filter_status and "상태" in df.columns:
            df = df[df["상태"] == filter_status]
        return df
    except Exception as e:
        st.warning(f"주작업 조회 실패 (더미로 대체): {e}")
        return _dummy_tasks()


@st.cache_data(ttl=300)
def fetch_orders() -> pd.DataFrame:
    """발주마스터 DB → DataFrame"""
    client = get_notion_client()
    if not client:
        return _dummy_orders()
    db_id = get_db_id("orders")
    if not db_id:
        return _dummy_orders()
    try:
        results = client.databases.query(database_id=db_id, page_size=100).get("results", [])
        rows = []
        for r in results:
            d = _props_to_dict(r.get("properties", {}))
            d["_id"] = r.get("id")
            rows.append(d)
        return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"발주마스터 조회 실패 (더미로 대체): {e}")
        return _dummy_orders()


def create_calendar_event(title: str, date_str: str, category: str = "기타", person: str = "", note: str = ""):
    """캘린더 DB에 이벤트 생성"""
    client = get_notion_client()
    if not client:
        st.info("Notion 토큰 미설정 — 로컬 캐시에만 반영됩니다.")
        return None
    db_id = get_db_id("calendar") or get_db_id("tasks")
    try:
        props = {
            "이름": {"title": [{"text": {"content": title}}]},
            "날짜": {"date": {"start": date_str}},
            "분류": {"select": {"name": category}},
        }
        if person: props["담당자"] = {"rich_text": [{"text": {"content": person}}]}
        if note:   props["메모"]   = {"rich_text": [{"text": {"content": note}}]}
        res = client.pages.create(parent={"database_id": db_id}, properties=props)
        fetch_calendar_events.clear()
        return res
    except Exception as e:
        st.error(f"캘린더 생성 실패: {e}")
        return None


def create_task(title: str, status: str = "대기", priority: str = "보통", due: str = "", assignee: str = "", desc: str = ""):
    """주작업 DB에 태스크 생성"""
    client = get_notion_client()
    if not client:
        st.info("Notion 토큰 미설정 — 로컬 캐시에만 반영됩니다.")
        return None
    db_id = get_db_id("tasks")
    try:
        props = {
            "이름": {"title": [{"text": {"content": title}}]},
            "상태": {"select": {"name": status}},
            "우선순위": {"select": {"name": priority}},
        }
        if due: props["마감일"] = {"date": {"start": due}}
        if assignee: props["담당자"] = {"rich_text": [{"text": {"content": assignee}}]}
        if desc: props["내용"] = {"rich_text": [{"text": {"content": desc}}]}
        res = client.pages.create(parent={"database_id": db_id}, properties=props)
        fetch_tasks.clear()
        return res
    except Exception as e:
        st.error(f"태스크 생성 실패: {e}")
        return None


def update_task_status(page_id: str, status: str):
    """주작업 상태 업데이트"""
    client = get_notion_client()
    if not client: return None
    try:
        res = client.pages.update(page_id=page_id, properties={"상태": {"select": {"name": status}}})
        fetch_tasks.clear()
        return res
    except Exception as e:
        st.error(f"상태 업데이트 실패: {e}")
        return None


def render_notion_status_badge():
    """사이드바/상단에 Notion 연동 상태 배지 표시"""
    client = get_notion_client()
    if client:
        st.caption("🟢 Notion 연동 활성")
    else:
        st.caption("⚪ Notion 토큰 미설정 (더미 모드)")


def render_task_widget(module_name: str):
    """공통 태스크 위젯 — 모듈 하단에 placeholder. 노션 연결 시 해당 모듈 태그 task 표시."""
    from .styles import section_header
    st.markdown(section_header("🗂 관련 태스크", module_name), unsafe_allow_html=True)
    tasks = fetch_tasks()
    if "태그" in tasks.columns:
        tasks = tasks[tasks["태그"].astype(str).str.contains(module_name, na=False)]
    if not len(tasks):
        st.caption("해당 모듈 관련 태스크 없음. (또는 Notion 미연결)")
        return
    show = tasks.head(5)
    name_col = "이름" if "이름" in show.columns else show.columns[0]
    status_col = "상태" if "상태" in show.columns else None
    due_col = "마감일" if "마감일" in show.columns else None
    cols_to_show = [c for c in [name_col, status_col, due_col] if c]
    st.dataframe(show[cols_to_show], hide_index=True, use_container_width=True)

    with st.expander("➕ 새 태스크"):
        c1, c2, c3 = st.columns([3,1,1])
        title = c1.text_input("제목", key=f"task_title_{module_name}")
        prio = c2.selectbox("우선순위", list(PRIORITY_COLORS.keys()), key=f"task_prio_{module_name}")
        due = c3.date_input("마감일", key=f"task_due_{module_name}")
        if st.button("저장", key=f"task_save_{module_name}"):
            if title:
                create_task(title=f"[{module_name}] {title}", priority=prio, due=str(due))
                st.success("저장됨")
                st.rerun()


# ===== 더미 데이터 (토큰 미설정 시 시연용) =====
def _dummy_calendar() -> pd.DataFrame:
    today = datetime.now().date()
    rows = []
    for i, (off, t, cat, ppl) in enumerate([
        (0, "월요 정기 회의",       "회의",         "전 인원"),
        (0, "시몬스 신상품 사전공유", "시몬스미팅",   "서영완"),
        (1, "VIP 컨설팅 - 김OO",   "VIP컨설팅",    "이혜지"),
        (2, "5월 발주 마감",        "발주마감",     "서영완"),
        (3, "교육: FLOS 신제품",    "교육",         "전 인원"),
        (5, "인플루언서 협찬 촬영",  "인플루언서협찬","이혜지"),
        (7, "백화점 매장이벤트",     "매장이벤트",   "신정훈"),
        (10, "광주 출장",           "출장",         "서영완"),
        (-1, "휴가 - 박OO",         "휴가",         "박OO"),
    ]):
        rows.append({
            "_id": f"dummy-{i}", "이름": t, "분류": cat, "담당자": ppl,
            "날짜": (today + timedelta(days=off)).isoformat(),
            "date": pd.Timestamp(today + timedelta(days=off)),
            "메모": "",
        })
    return pd.DataFrame(rows)


def _dummy_tasks() -> pd.DataFrame:
    return pd.DataFrame([
        {"_id":"t1","이름":"[발주] FLOS 5월 입고 확인","상태":"진행중","우선순위":"높음","마감일":"2026-05-25","담당자":"서영완","태그":"발주"},
        {"_id":"t2","이름":"[제안서] 김OO 고객 견적 회신","상태":"대기","우선순위":"긴급","마감일":"2026-05-24","담당자":"이혜지","태그":"제안서"},
        {"_id":"t3","이름":"[AS] LASVIT 클레임 대응","상태":"진행중","우선순위":"보통","마감일":"2026-05-28","담당자":"신정훈","태그":"AS"},
        {"_id":"t4","이름":"[매출] 5월 마감 보고","상태":"대기","우선순위":"높음","마감일":"2026-05-31","담당자":"서영완","태그":"매출"},
        {"_id":"t5","이름":"[대여] 영화 촬영 협찬 회수","상태":"대기","우선순위":"보통","마감일":"2026-05-26","담당자":"이혜지","태그":"대여"},
    ])


def _dummy_orders() -> pd.DataFrame:
    return pd.DataFrame([
        {"_id":"o1","SKU":"FLOS-IC-T1-BLK","브랜드":"FLOS","품명":"IC T1 Black","현재고":2,"MoC":5,"ROP":3,"권고수량":8,"운송":"SEA","납기":"2026-07-15","상태":"발주필요","비고":""},
        {"_id":"o2","SKU":"ARTEMIDE-TOLO-S","브랜드":"ARTEMIDE","품명":"Tolomeo Small","현재고":1,"MoC":3,"ROP":2,"권고수량":6,"운송":"AIR","납기":"2026-06-05","상태":"긴급","비고":"VIP 발주건"},
        {"_id":"o3","SKU":"LASVIT-NEG-CL","브랜드":"LASVIT","품명":"Never-ending Glory","현재고":0,"MoC":2,"ROP":1,"권고수량":3,"운송":"AIR","납기":"2026-06-10","상태":"결품","비고":""},
        {"_id":"o4","SKU":"VIA-N55-W","브랜드":"VIABIZZUNO","품명":"N55 White","현재고":4,"MoC":6,"ROP":4,"권고수량":5,"운송":"SEA","납기":"2026-07-20","상태":"발주필요","비고":""},
        {"_id":"o5","SKU":"MARSET-GNG-M","브랜드":"MARSET","품명":"Ginger Medium","현재고":3,"MoC":4,"ROP":3,"권고수량":4,"운송":"SEA","납기":"2026-07-12","상태":"권고","비고":""},
        {"_id":"o6","SKU":"VIBIA-NW-CL","브랜드":"VIBIA","품명":"Northwind","현재고":5,"MoC":5,"ROP":3,"권고수량":3,"운송":"SEA","납기":"2026-07-25","상태":"여유","비고":""},
    ])
