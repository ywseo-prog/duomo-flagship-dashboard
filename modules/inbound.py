"""모듈 8: 입고 추적 — 진행일지 2-Source 교차검증 + 4인 미입고 현황
※ Slack 발송은 사용자 결정으로 제외. 대시보드 시각화 + Notion 이력 DB만 운영.
   상세 스펙: inbound_alert_module/docs/01~04, README.md (zip 패키지 인수)

[Config 외부화 v1.4]
- inbound_alert_module/config/members.yaml      → 4인 R&R + Slack ID + receive policy
- inbound_alert_module/config/sheets_mapping.yaml → 시트별 컬럼 위치 (fallback)
- inbound_alert_module/config/brands_leadtime.yaml → 브랜드·운송모드 리드타임
PyYAML 로드 → 인라인 상수보다 우선. YAML 미존재/PyYAML 미설치 시 인라인 fallback.
"""
from __future__ import annotations  # PEP 604 (`X | None`) 호환 — Python 3.9 이하 대응
import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime, date, timedelta
from io import BytesIO

# Direct sub-module imports — surface exact symbol on Streamlit Cloud ImportError
from utils.styles import (
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)
from utils.notion_client import (
    render_task_widget,
    INBOUND_MEMBERS, fetch_inbound_history, record_inbound_history,
    make_inbound_alarm_key,
)


# ============================================================
# Config 로드 — YAML 우선, 미존재 시 인라인 fallback
# ============================================================
_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "inbound_alert_module", "config",
)


def _load_yaml(filename: str) -> dict:
    path = os.path.join(_CONFIG_DIR, filename)
    if not os.path.exists(path):
        return {}
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return {}
    except Exception:
        return {}


@st.cache_resource
def load_members_config() -> dict:
    """members.yaml → {"members": {name: {aliases, role, slack_user_id, ...}}}"""
    return _load_yaml("members.yaml")


@st.cache_resource
def load_sheets_mapping() -> dict:
    """sheets_mapping.yaml → {duomo/notocasa: {file_id, sheets, ...}, exclude_sheets: [...]}"""
    return _load_yaml("sheets_mapping.yaml")


@st.cache_resource
def load_brands_leadtime() -> dict:
    """brands_leadtime.yaml → {shipping_modes, brands, v3_triggers}"""
    return _load_yaml("brands_leadtime.yaml")


def _get_member_aliases() -> dict:
    """YAML members 우선, 미존재 시 인라인."""
    cfg = load_members_config().get("members") or {}
    if cfg:
        return {name: info.get("aliases", [name]) for name, info in cfg.items()}
    # fallback (이경 함정 가드)
    return {
        "서영완": ["서영완"],
        "조이경": ["조이경"],
        "윤소담": ["윤소담"],
        "추승민": ["추승민"],
    }


def _get_exclude_sheets() -> list:
    """sheets_mapping.exclude_sheets 우선."""
    cfg = load_sheets_mapping().get("exclude_sheets")
    if cfg:
        return cfg
    return ["OLD", "Fedex", "DHL", "BeB 지연"]


def _get_leadtime(shipping_mode: str, brand: str = "") -> int | None:
    """브랜드·운송모드별 typical_days 반환. ETA 3순위 산출용."""
    cfg = load_brands_leadtime()
    # 1) 브랜드별 typical_days_{air|sea}
    if brand:
        brand_info = (cfg.get("brands") or {}).get(brand)
        if brand_info:
            key = f"typical_days_{shipping_mode.lower()}"
            if key in brand_info:
                return int(brand_info[key])
            # Sea alias
            if shipping_mode.lower() == "ocean" and "typical_days_sea" in brand_info:
                return int(brand_info["typical_days_sea"])
    # 2) shipping_modes 기본값
    modes = cfg.get("shipping_modes") or {}
    mode_info = modes.get(shipping_mode) or modes.get(shipping_mode.capitalize())
    if mode_info and "typical_days" in mode_info:
        return int(mode_info["typical_days"])
    return None


# 모듈 로드 시점에 YAML 통합 적용 (cache_resource로 1회만)
MEMBER_ALIASES = _get_member_aliases()

# 처리 제외 시트 키워드 (YAML 우선, 미존재 시 인라인)
EXCLUDE_SHEET_KEYWORDS = _get_exclude_sheets()

# 헤더 후보 키워드 → 표준 컬럼명
HEADER_KEYWORDS = {
    "supplier":    ["Supplier", "공급사", "브랜드"],
    "project":     ["Project", "프로젝트", "현장"],
    "sales":       ["영업부 담당자", "영업담당자", "담당자", "Sales"],
    "po_no":       ["PO No.", "PO No", "PO#", "PO 번호"],
    "shipping":    ["Shipping", "운송", "Ship mode"],
    "eta":         ["도착", "ETA", "도착/ETA", "도착 ETA"],
    "inbound":     ["입고"],
    "description": ["description", "Description", "Item", "품명", "내용"],
    "qty":         ["qty", "QTY", "Quantity", "수량"],
}

D14_THRESHOLD = 14  # 입항 임박 기준 (일)
OVERDUE_GRACE = 0   # 지연 알림 시작 일수 (0=즉시)


def _match_member(cell_value) -> str | None:
    """E열 셀값에서 4인 매칭. 함정: '이경' 단독은 고객명 빈출 → 풀네임만"""
    if not cell_value:
        return None
    s = str(cell_value).strip()
    if not s:
        return None
    for std, aliases in MEMBER_ALIASES.items():
        for a in aliases:
            if a in s:
                return std
    return None


def _find_header_row(ws, max_scan: int = 5) -> int:
    """앞 5행 중 'Supplier' 또는 '영업부 담당자'가 등장하는 행 = 헤더"""
    for r_idx in range(1, max_scan + 1):
        row = [str(c.value or "").strip() for c in ws[r_idx]]
        joined = " ".join(row)
        if any(kw in joined for kw in ["Supplier", "영업부 담당자", "PO No"]):
            return r_idx
    return 1


def _build_col_map(header_row_cells) -> dict:
    """헤더 셀 리스트 → {표준컬럼명: col_index (1-based)} 매핑"""
    col_map = {}
    for col_idx, cell in enumerate(header_row_cells, start=1):
        val = str(cell.value or "").strip()
        if not val:
            continue
        for std, candidates in HEADER_KEYWORDS.items():
            if std in col_map:
                continue
            for cand in candidates:
                if cand.lower() in val.lower() or val.lower() in cand.lower():
                    col_map[std] = col_idx
                    break
    return col_map


def _parse_eta(val) -> date | None:
    """ETA 셀 값을 date로 — datetime/str/숫자 모두 처리"""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s:
        return None
    # ISO: 2026-05-21
    m = re.search(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # M/D
    m = re.search(r"\b(\d{1,2})/(\d{1,2})\b", s)
    if m:
        try:
            mo, d = int(m.group(1)), int(m.group(2))
            today = date.today()
            cand = date(today.year, mo, d)
            # 과거 30일 이전이면 차기년도
            if cand < today - timedelta(days=30):
                cand = date(today.year + 1, mo, d)
            return cand
        except ValueError:
            return None
    return None


def _parse_sheet(ws, source_name: str, sheet_name: str) -> list[dict]:
    """단일 시트 → 4인 매칭 row 리스트"""
    header_row = _find_header_row(ws)
    col_map = _build_col_map(ws[header_row])
    if "sales" not in col_map:
        return []  # 영업담당자 컬럼 못 찾으면 skip

    results = []
    for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not row or len(row) < col_map["sales"]:
            continue
        sales_val = row[col_map["sales"] - 1]
        member = _match_member(sales_val)
        if not member:
            continue

        def get(col_key):
            idx = col_map.get(col_key)
            if not idx or idx > len(row):
                return None
            return row[idx - 1]

        eta_raw = get("eta")
        inb_raw = get("inbound")
        results.append({
            "source":      source_name,
            "sheet":       sheet_name,
            "member":      member,
            "supplier":    str(get("supplier") or "").strip(),
            "project":     str(get("project") or "").strip(),
            "po_no":       str(get("po_no") or "").strip(),
            "shipping":    str(get("shipping") or "").strip(),
            "eta_raw":     eta_raw,
            "eta":         _parse_eta(eta_raw),
            "inbound_raw": inb_raw,
            "inbound":     _parse_eta(inb_raw),
            "description": str(get("description") or "").strip(),
            "qty":         get("qty"),
        })
    return results


@st.cache_data(ttl=600)
def _parse_uploaded_file(file_bytes: bytes, source_name: str) -> pd.DataFrame:
    """업로드된 xlsx → 4인 매칭 DataFrame"""
    try:
        import openpyxl
    except ImportError:
        st.error("openpyxl 모듈이 필요합니다. requirements.txt 확인.")
        return pd.DataFrame()

    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    except Exception as e:
        st.error(f"파일 로드 실패 ({source_name}): {e}")
        return pd.DataFrame()

    all_rows = []
    for sheet_name in wb.sheetnames:
        if any(kw in sheet_name for kw in EXCLUDE_SHEET_KEYWORDS):
            continue
        try:
            rows = _parse_sheet(wb[sheet_name], source_name, sheet_name)
            all_rows.extend(rows)
        except Exception as e:
            st.warning(f"[{source_name}/{sheet_name}] 파싱 실패: {e}")
    return pd.DataFrame(all_rows)


def _dummy_progress_df() -> pd.DataFrame:
    """진행일지 미업로드 시 시연용 더미 데이터 (Phase 1.6 실측 기반)"""
    today = date.today()
    return pd.DataFrame([
        {"source":"DUOMO","sheet":"이동가구일지 (DUOMO KNOLL+외)","member":"조이경","supplier":"B&B","project":"샐러드보울_이자원 (1/2)","po_no":"PO-BB-260301-A","shipping":"Air","eta_raw":"","eta":today+timedelta(days=8),"inbound_raw":"","inbound":None,"description":"D.150.9 Dresser","qty":1},
        {"source":"DUOMO","sheet":"이동가구일지 (DUOMO KNOLL+외)","member":"조이경","supplier":"B&B","project":"샐러드보울_이자원 (2/2)","po_no":"PO-BB-260301-B","shipping":"Ocean","eta_raw":"","eta":today+timedelta(days=45),"inbound_raw":"","inbound":None,"description":"Tufty Time Sofa","qty":1},
        {"source":"DUOMO","sheet":"이동가구일지 (DUOMO KNOLL+외)","member":"조이경","supplier":"Knoll","project":"김정민 일점영안과의원","po_no":"PO-KN-251215","shipping":"SEA","eta_raw":"","eta":today-timedelta(days=3),"inbound_raw":"","inbound":today-timedelta(days=1),"description":"Saarinen Table","qty":2},
        {"source":"DUOMO","sheet":"이동가구일지 (DUOMO KNOLL+외)","member":"윤소담","supplier":"Knoll","project":"헤파이스토스 이수동 실장","po_no":"PO-KN-260120","shipping":"SEA","eta_raw":"","eta":today+timedelta(days=12),"inbound_raw":"","inbound":None,"description":"Womb Chair","qty":4},
        {"source":"DUOMO","sheet":"이동가구일지 (DUOMO KNOLL+외)","member":"서영완","supplier":"Knoll","project":"김민정 고객","po_no":"PO-KN-260205","shipping":"SEA","eta_raw":"","eta":today+timedelta(days=20),"inbound_raw":"","inbound":None,"description":"Barcelona Chair","qty":2},
        {"source":"NOTOCASA","sheet":"이동가구 진행일지 (NOTOCASA)","member":"서영완","supplier":"B&B Italia","project":"카민디자인(윤혜영)","po_no":"PO-BB-260115","shipping":"Ocean","eta_raw":"","eta":today+timedelta(days=5),"inbound_raw":"","inbound":None,"description":"Charles Sofa","qty":1},
        {"source":"NOTOCASA","sheet":"이동가구 진행일지 (NOTOCASA)","member":"서영완","supplier":"MAXALTO","project":"스튜디오베이스_수지","po_no":"PO-MX-260101","shipping":"Ocean","eta_raw":"2026-04-23","eta":date(2026,4,23),"inbound_raw":"","inbound":date(2026,7,2),"description":"Apta Table","qty":1},
        {"source":"NOTOCASA","sheet":"이동가구 진행일지 (NOTOCASA)","member":"조이경","supplier":"Poltrona Frau","project":"이건축 사옥","po_no":"PO-PF-260210","shipping":"Air","eta_raw":"","eta":today+timedelta(days=2),"inbound_raw":"","inbound":None,"description":"Vanity Fair Chair","qty":3},
    ])


def _classify_alarm(row, history_keys: set) -> tuple[str, int | None]:
    """알람 유형 판정 — (type, dday). history 중복은 'SENT'로 표시"""
    today = date.today()
    eta = row.get("eta")
    inbound = row.get("inbound")
    po = row.get("po_no") or ""
    member = row.get("member") or ""

    # 2차: 입고완료 (날짜값 있음)
    if inbound:
        key = make_inbound_alarm_key(po, member, "입고완료")
        if key in history_keys:
            return ("SENT_COMPLETED", None)
        return ("COMPLETED", None)

    # 1차: 입항 D-14 / OVERDUE
    if eta:
        dday = (eta - today).days
        if dday < 0:
            key = make_inbound_alarm_key(po, member, "입항임박_D14")
            if key in history_keys:
                return ("SENT_OVERDUE", dday)
            return ("OVERDUE", dday)
        if dday <= D14_THRESHOLD:
            key = make_inbound_alarm_key(po, member, "입항임박_D14")
            if key in history_keys:
                return ("SENT_IMMINENT", dday)
            return ("IMMINENT", dday)
        return ("MONITORING", dday)

    return ("UNKNOWN", None)


def render():
    greeting_header(
        "조명플래그십파트",
        role="입고 추적 · 4인 미입고 / 입항 임박 / 입고완료 자동 감지",
        page_title="📦 입고 추적",
    )

    st.markdown(alert_banner(
        "운영 안내",
        "Slack 자동 발송은 비활성 상태이며, 본 대시보드에서만 시각화합니다. "
        "Notion 이력 DB(`INBOUND_HISTORY_DB_ID`) 등록 시 '확인 처리'한 알람은 중복 표시되지 않습니다.",
        level="blue", icon="ℹ",
    ), unsafe_allow_html=True)

    # === 진행일지 파일 업로드 ===
    st.markdown(section_header("진행일지 업로드", "DUOMO + NOTO CASA 진행일지 .xlsx (lilychoi 공유)"),
                unsafe_allow_html=True)
    ucol1, ucol2, ucol3 = st.columns([2, 2, 1])
    duomo_file = ucol1.file_uploader("DUOMO 진행일지", type=["xlsx"], key="up_duomo")
    notocasa_file = ucol2.file_uploader("NOTO CASA 진행일지", type=["xlsx"], key="up_notocasa")
    scan_clicked = ucol3.button("🔄 지금 스캔", type="primary", use_container_width=True)

    # === 데이터 로드 ===
    if duomo_file or notocasa_file:
        frames = []
        if duomo_file:
            df_d = _parse_uploaded_file(duomo_file.getvalue(), "DUOMO")
            if len(df_d): frames.append(df_d)
        if notocasa_file:
            df_n = _parse_uploaded_file(notocasa_file.getvalue(), "NOTOCASA")
            if len(df_n): frames.append(df_n)
        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        data_source = "업로드 파일"
    else:
        df = _dummy_progress_df()
        data_source = "더미 데이터 (실제 파일 업로드 시 자동 대체)"

    if not len(df):
        st.error("4인 매칭 결과 없음 — 시트 컬럼 구조 확인 필요 (E열 영업부 담당자)")
        return

    st.caption(f"📂 데이터 소스: **{data_source}** · 매칭된 4인 진행건 **{len(df):,}건**")

    # === 발송이력 (중복 표시 방지용) ===
    hist = fetch_inbound_history()
    history_keys = set()
    if len(hist) and "알람키" in hist.columns:
        history_keys = set(hist["알람키"].dropna().astype(str).tolist())

    # 알람 분류
    df[["alarm_type", "dday"]] = df.apply(
        lambda r: pd.Series(_classify_alarm(r, history_keys)), axis=1
    )

    today = date.today()
    imminent = df[df["alarm_type"] == "IMMINENT"].copy()
    completed = df[df["alarm_type"] == "COMPLETED"].copy()
    overdue = df[df["alarm_type"] == "OVERDUE"].copy()
    monitoring = df[df["alarm_type"] == "MONITORING"].copy()

    # === KPI 4종 ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        "진행 중 발주건", f"{len(df) - len(completed):,}",
        f"전체 {len(df):,}건", "neutral", "📋"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "🚢 입항 임박 (D≤14)", f"{len(imminent):,}",
        f"신규 알림 대상", "up" if len(imminent) else "neutral", "🚢"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "📦 신규 입고완료", f"{len(completed):,}",
        "출고 처리 필요", "gold" if len(completed) else "neutral", "📦"
    ), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card(
        "⚠ 지연 (ETA 경과)", f"{len(overdue):,}",
        "확인 필요", "down" if len(overdue) else "neutral", "⏰"
    ), unsafe_allow_html=True)

    # === 알림 배너 ===
    if len(imminent):
        st.markdown(alert_banner(
            f"🚢 입항 임박 {len(imminent)}건 — 출고 일정 사전 확정 필요",
            f"{', '.join(imminent['member'].unique())} 담당",
            level="orange", icon="🚢",
        ), unsafe_allow_html=True)
    if len(overdue):
        st.markdown(alert_banner(
            f"⏰ 입항 지연 {len(overdue)}건 — 예정일 경과, 즉시 확인",
            f"{', '.join(overdue['member'].unique())} 담당",
            level="red", icon="⏰",
        ), unsafe_allow_html=True)

    # === 4인별 multi-card ===
    st.markdown(section_header("4인 미입고 현황", "담당자별 진행 중 발주건"),
                unsafe_allow_html=True)
    member_cards = []
    palette = {"서영완":"#0A0A0A", "조이경":"#C9A961", "윤소담":"#1976D2", "추승민":"#7B1FA2"}
    for m in INBOUND_MEMBERS:
        mdf = df[df["member"] == m]
        in_progress_count = len(mdf[mdf["alarm_type"] != "COMPLETED"])
        imm_count = len(mdf[mdf["alarm_type"] == "IMMINENT"])
        member_cards.append({
            "label": m,
            "value": f"{in_progress_count}",
            "sub": "미입고 발주건",
            "color": palette.get(m, "#999"),
            "trend": f"🚢 임박 {imm_count}건" if imm_count else "",
        })
    # 4인이므로 multi_card_row는 3개 기준 → 직접 4컬럼 렌더
    mcols = st.columns(4)
    for i, c in enumerate(member_cards):
        mcols[i].markdown(f"""
<div class="mc-item" style="border-top-color:{c['color']}">
  <div class="mc-label" style="color:{c['color']}">{c['label']}</div>
  <div class="mc-value">{c['value']}</div>
  <div class="mc-sub">{c['sub']}</div>
  {f'<div class="mc-trend">{c["trend"]}</div>' if c['trend'] else ''}
</div>
""", unsafe_allow_html=True)

    # === 알람 리스트 (탭) ===
    tabs = st.tabs([
        f"🚢 입항 임박 ({len(imminent)})",
        f"📦 입고완료 ({len(completed)})",
        f"⏰ 지연 ({len(overdue)})",
        f"📅 모니터링 ({len(monitoring)})",
    ])

    with tabs[0]:
        if len(imminent):
            for i, row in enumerate(imminent.sort_values("eta").itertuples(), 1):
                eta_str = row.eta.strftime("%Y-%m-%d") if row.eta else "—"
                desc = (row.description or "")[:30]
                st.markdown(leaderboard_row(
                    rank=i,
                    name=f"{row.supplier} · {row.project[:30]}",
                    sub=f"D-{row.dday} · ETA {eta_str} · {row.shipping or '—'} · {desc} (x{row.qty or '?'})",
                    value=row.member,
                    value_label=f"PO {row.po_no[:18]}",
                    color="#FF6B35",
                ), unsafe_allow_html=True)
                _confirm_button(row, "입항임박_D14", eta_iso=row.eta.isoformat() if row.eta else "")
        else:
            st.caption("입항 임박 건 없음")

    with tabs[1]:
        if len(completed):
            for i, row in enumerate(completed.sort_values("inbound", ascending=False).itertuples(), 1):
                inb_str = row.inbound.strftime("%Y-%m-%d") if row.inbound else "—"
                desc = (row.description or "")[:30]
                st.markdown(leaderboard_row(
                    rank=i,
                    name=f"{row.supplier} · {row.project[:30]}",
                    sub=f"입고일 {inb_str} · {row.shipping or '—'} · {desc} (x{row.qty or '?'})",
                    value=row.member,
                    value_label=f"PO {row.po_no[:18]}",
                    color="#2E7D32",
                ), unsafe_allow_html=True)
                _confirm_button(row, "입고완료", inbound_iso=row.inbound.isoformat() if row.inbound else "")
        else:
            st.caption("신규 입고완료 건 없음")

    with tabs[2]:
        if len(overdue):
            for i, row in enumerate(overdue.sort_values("eta").itertuples(), 1):
                eta_str = row.eta.strftime("%Y-%m-%d") if row.eta else "—"
                desc = (row.description or "")[:30]
                st.markdown(leaderboard_row(
                    rank=i,
                    name=f"{row.supplier} · {row.project[:30]}",
                    sub=f"D+{abs(row.dday)} 지연 · ETA {eta_str} · {row.shipping or '—'} · {desc}",
                    value=row.member,
                    value_label=f"PO {row.po_no[:18]}",
                    color="#D32F2F",
                ), unsafe_allow_html=True)
        else:
            st.caption("지연 건 없음")

    with tabs[3]:
        if len(monitoring):
            mon_show = monitoring.sort_values("eta").copy()
            mon_show["ETA"] = mon_show["eta"].apply(lambda d: d.strftime("%Y-%m-%d") if d else "—")
            mon_show["D-"] = mon_show["dday"].apply(lambda d: f"D-{d}" if d is not None else "—")
            st.dataframe(
                mon_show[["member","supplier","project","po_no","shipping","ETA","D-","description","qty"]],
                hide_index=True, use_container_width=True,
            )
        else:
            st.caption("모니터링 건 없음")

    # === 발송이력 expander ===
    with st.expander("📜 Notion 발송이력 / 확인 처리 기록"):
        if len(hist):
            show_cols = [c for c in ["담당자","알람유형","Supplier","Project","PO No.","발송일시","상태"] if c in hist.columns]
            st.dataframe(hist[show_cols], hide_index=True, use_container_width=True)
        else:
            st.caption("이력 없음 — `INBOUND_HISTORY_DB_ID` 미설정이거나 아직 확인 처리된 알람이 없음.")

    render_task_widget("입고")


def _confirm_button(row, alarm_type_label: str, eta_iso: str = "", inbound_iso: str = ""):
    """알람 row 옆 '확인 처리' 버튼 — Notion 이력 DB에 기록 → 다음 스캔 시 숨김"""
    btn_key = f"conf_{alarm_type_label}_{row.po_no}_{row.member}"
    if st.button(f"✓ 확인 처리 (이력 기록)", key=btn_key, help="다음 스캔부터 이 알람을 숨깁니다"):
        key = make_inbound_alarm_key(row.po_no, row.member, alarm_type_label)
        ok = record_inbound_history(
            alarm_key=key, member=row.member, alarm_type=alarm_type_label,
            supplier=row.supplier, project=row.project, po_no=row.po_no,
            eta=eta_iso, inbound_date=inbound_iso,
        )
        if ok:
            st.success("Notion 이력에 기록됨")
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning("기록 실패 — Notion 토큰 또는 `INBOUND_HISTORY_DB_ID` 확인")
