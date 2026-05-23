"""모듈 2: 업무일지 v2 — 첫 화면 정보 밀도 ↑, 스프레드시트 1:1 + 좌우 split

UI 우선순위:
  1. 첫 화면 재배치 (좌 7/12 카드 / 우 5/12 컴팩트 KPI)
  2. 일별 카드 스프레드시트 양식 재현 + 일일 합계 푸터
  3. 빠른 탐색 칩 ([오늘][어제][최근7일][최근30일][📅 날짜])
  4. 데이터 무결성 알림 (시트 헤더 vs 산정값 갭)
  5. 신규 입력 인라인 폼 (헤더 [+신규입력] 토글)

데이터: Google Sheets '플래그십 업무일지' (NEW+OLD 통합 parser)
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
from calendar import monthrange
import re

from parsers import (
    load_worklog_df, aggregate_monthly, aggregate_by_person, aggregate_by_brand,
    aggregate_by_customer, load_monthly_target, load_visitor_trend,
    SHEET_ID, WORKLOG_TAB,
    append_worklog_row,
    CHANNEL_OPTIONS, CATEGORY_OPTIONS, STATUS_OPTIONS,
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


# ============================================================
# 컬러 매핑 (스펙 v2)
# ============================================================
STATUS_COLOR = {
    "done":      "#999999",
    "ing":       "#FFA000",
    "결제 완료": "#C9A961",
    "결제완료":  "#C9A961",
    "견적 진행": "#1976D2",
    "견적진행":  "#1976D2",
    "예정":      "#1976D2",
    "보류":      "#F57C00",
    "취소":      "#D32F2F",
    "문의":      "#7B1FA2",
    "재방문":    "#5D4037",
}

# 6인 고정 컬러 (스펙 v2)
PERSON_COLOR = {
    "조이경": "#1976D2",  # 블루
    "서영완": "#2E7D32",  # 그린
    "추승민": "#7B1FA2",  # 보라
    "강혁진": "#C2185B",  # 핑크
    "이현진": "#00838F",  # 청록
    "신민정": "#F57C00",  # 오렌지
}

CHANNEL_LABEL = {"내방": "📍 내방", "유선": "📞 유선", "온라인": "💻 온라인", "소개": "🤝 소개"}
CHANNEL_CSS = {"내방": "", "유선": "phone", "온라인": "online", "소개": "intro"}

VIP_THRESHOLD = 3_000_000


def _person_color(name: str) -> str:
    if not name:
        return "#999999"
    s = str(name)
    for k, v in PERSON_COLOR.items():
        if k in s:
            return v
    return "#5D4037"


def _person_badge(person_raw: str) -> str:
    if not person_raw:
        return ""
    parts = []
    for tok in re.split(r"[,，、/]\s*", str(person_raw)):
        tok = tok.strip()
        if not tok:
            continue
        color = _person_color(tok)
        parts.append(f'<span class="wp-badge" style="background:{color}">{tok}</span>')
    return " ".join(parts)


# ============================================================
# 메인 entry
# ============================================================
def render():
    df_all = load_worklog_df(source="auto")
    if not len(df_all):
        st.error("본사 시트 데이터 로드 실패 — Google Sheets 권한 또는 네트워크 확인")
        return
    df_all = df_all.copy()
    target = load_monthly_target()

    # === 1. 페이지 헤더: greeting + 액션 버튼 ===
    h1, h2 = st.columns([5, 2])
    with h1:
        greeting_header(
            "서영완",
            role="조명플래그십파트 · 본사 업무일지 1:1",
            page_title="📊 업무일지",
        )
    with h2:
        st.markdown("<div style='height:34px'></div>", unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        if bc1.button("➕ 신규 입력", use_container_width=True, key="wl_btn_new"):
            st.session_state["wl_show_form"] = not st.session_state.get("wl_show_form", False)
        bc2.button("↓ 리포트", use_container_width=True, key="wl_btn_report",
                   help="페이지 하단 본사 시트 추이로 스크롤")

    # === 2. 데이터 무결성 알림 ===
    _render_integrity_banner(df_all, target)

    # === 3. 빠른 탐색 칩 ===
    chip_key = _render_quick_chips()

    # === 4. 검색 + 필터 (한 줄) ===
    f = _render_search_filters(df_all)

    # === 5. 칩으로 추가 필터 적용 ===
    f = _apply_chip_filter(f, chip_key)

    if not len(f):
        st.warning("필터/탐색 결과 0건 — 다른 칩이나 필터를 시도해 주세요.")
        return

    # === 6. 본문: 좌 7/12 카드 + 우 5/12 KPI ===
    main_l, main_r = st.columns([7, 5])
    with main_l:
        # 신규 입력 폼 (인라인 토글)
        if st.session_state.get("wl_show_form"):
            _render_inline_form()

        # 일별 카드 렌더
        _render_daily_cards(f, chip_key)

    with main_r:
        _render_compact_kpi(df_all, target)
        _render_persons_quick_summary(df_all)
        _render_visitor_trend()

    # === 하단: 리포트 영역 (월/연 뷰) ===
    st.markdown("---")
    render_report_section("업무일지", f, period_col="date")
    with st.expander("🗓 월별 / 📆 연별 분석", expanded=False):
        view = st.radio("뷰", ["🗓 월별", "📆 연별"], horizontal=True, key="wl_extra_view")
        if view == "🗓 월별":
            _render_monthly_view(f, target)
        else:
            _render_yearly_view(f)

    render_task_widget("업무일지")


# ============================================================
# 데이터 무결성 알림
# ============================================================
def _render_integrity_banner(df: pd.DataFrame, target: dict | None):
    if not target or not target.get("achieved"):
        return  # 시트 헤더 미입력 → 비교 불가
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    computed = int(month_df[month_df["amount"] > 0]["amount"].sum())
    header_val = int(target["achieved"])
    gap = header_val - computed
    abs_gap = abs(gap)
    if abs_gap < 100_000:
        cls = ""
        icon = "✓"
        label = "데이터 무결성 양호"
    elif abs_gap < 1_000_000:
        cls = ""
        icon = "ℹ"
        label = "소폭 차이"
    elif abs_gap < 5_000_000:
        cls = "warn"
        icon = "⚠"
        label = "갭 주의"
    else:
        cls = "error"
        icon = "🚨"
        label = "갭 큼 — 점검 필요"

    sign = "+" if gap > 0 else ""
    html = f"""
<div class="wl-integrity {cls}">
  <span class="wi-icon">{icon}</span>
  <span><b>{label}</b> · {today.month}월 누계
    산정 ₩{computed:,} · 시트 헤더 ₩{header_val:,}
    <span class="wi-gap">갭 {sign}₩{gap:,}</span>
  </span>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# 빠른 탐색 칩
# ============================================================
def _render_quick_chips() -> str:
    chip = st.session_state.get("wl_chip", "today")
    today = date.today()
    cols = st.columns([1, 1, 1.2, 1.2, 2.5, 4])
    if cols[0].button("오늘", use_container_width=True,
                       type="primary" if chip == "today" else "secondary",
                       key="ck_today"):
        st.session_state["wl_chip"] = "today"
        st.rerun()
    if cols[1].button("어제", use_container_width=True,
                       type="primary" if chip == "yesterday" else "secondary",
                       key="ck_yest"):
        st.session_state["wl_chip"] = "yesterday"
        st.rerun()
    if cols[2].button("최근 7일", use_container_width=True,
                       type="primary" if chip == "7d" else "secondary",
                       key="ck_7d"):
        st.session_state["wl_chip"] = "7d"
        st.rerun()
    if cols[3].button("최근 30일", use_container_width=True,
                       type="primary" if chip == "30d" else "secondary",
                       key="ck_30d"):
        st.session_state["wl_chip"] = "30d"
        st.rerun()
    # 날짜 picker
    sel_date = cols[4].date_input(
        "📅 날짜 점프", value=st.session_state.get("wl_pick_date", today),
        key="wl_pick_date_input", label_visibility="collapsed",
    )
    if st.session_state.get("wl_pick_date") != sel_date:
        st.session_state["wl_pick_date"] = sel_date
        st.session_state["wl_chip"] = "date"
    cols[5].caption(f"기준 일자: {today.strftime('%Y.%m.%d')}")
    return st.session_state.get("wl_chip", "today")


def _apply_chip_filter(f: pd.DataFrame, chip: str) -> pd.DataFrame:
    today = date.today()
    if chip == "today":
        return f[f["date"].dt.date == today]
    if chip == "yesterday":
        return f[f["date"].dt.date == today - timedelta(days=1)]
    if chip == "7d":
        return f[f["date"].dt.date >= today - timedelta(days=7)]
    if chip == "30d":
        return f[f["date"].dt.date >= today - timedelta(days=30)]
    if chip == "date":
        sel = st.session_state.get("wl_pick_date", today)
        return f[f["date"].dt.date == sel]
    return f


# ============================================================
# 검색·필터 (한 줄, 항상 노출)
# ============================================================
def _render_search_filters(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    fc1, fc2, fc3 = st.columns([3, 2, 2])
    search = fc1.text_input(
        "🔍 검색 (고객·내용·연락처·담당자)",
        placeholder="예) 카민디자인 / 010-1234 / 추승민",
        key="wl_search_v2", label_visibility="collapsed",
    )
    chans = sorted([c for c in df["channel"].unique() if c])
    chan_f = fc2.multiselect("📍 채널", chans, default=[], key="wl_chan_v2",
                              placeholder="채널 선택")
    person_opts = sorted(set(p for ps in df["persons"] for p in ps if p))
    per_f = fc3.multiselect("👤 담당자", person_opts, default=[], key="wl_per_v2",
                             placeholder="담당자 선택")

    if chan_f:
        f = f[f["channel"].isin(chan_f)]
    if per_f:
        f = f[f["persons"].apply(lambda ps: any(p in ps for p in per_f))]
    if search:
        s = search.strip().lower()
        mask = (
            f["customer"].astype(str).str.lower().str.contains(s, na=False) |
            f["content"].astype(str).str.lower().str.contains(s, na=False) |
            f["phone"].astype(str).str.lower().str.contains(s, na=False) |
            f["person_raw"].astype(str).str.lower().str.contains(s, na=False) |
            f["brands"].apply(lambda bl: any(s in b.lower() for b in (bl or [])))
        )
        f = f[mask]

    # 고급 필터 (collapsed)
    with st.expander("🔧 고급 필터 (현황/카테고리/매출 범위)", expanded=False):
        c1, c2, c3 = st.columns(3)
        cats = sorted([c for c in df["category"].unique() if c])
        cat_f = c1.multiselect("카테고리", cats, default=[], key="wl_cat_v2")
        sts = sorted([s for s in df["status"].unique() if s])
        st_f = c2.multiselect("현황", sts, default=[], key="wl_st_v2")
        only_paid = c3.checkbox("결제건만", value=False, key="wl_paid_v2")
        max_amt = int(df["amount"].max()) if len(df) else 10_000_000
        amt_range = st.slider("💰 매출 범위", 0, max(max_amt, 1_000_000),
                               (0, max(max_amt, 1_000_000)), 100_000, key="wl_amt_v2")
        if cat_f:
            f = f[f["category"].isin(cat_f)]
        if st_f:
            f = f[f["status"].isin(st_f)]
        f = f[(f["amount"] >= amt_range[0]) & (f["amount"] <= amt_range[1])]
        if only_paid:
            f = f[f["amount"] > 0]
    return f


# ============================================================
# 컴팩트 KPI (우측 5/12)
# ============================================================
def _render_compact_kpi(df: pd.DataFrame, target: dict | None):
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    paid_month = month_df[month_df["amount"] > 0]
    cur_sales = int(paid_month["amount"].sum())
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = cur_sales // max(active_days, 1) if active_days else 0
    target_val = target.get("target") if target else None
    rate = (cur_sales / target_val * 100) if target_val else None

    st.markdown("##### 📊 이번달 핵심")
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        if target_val:
            st.markdown(_mini_kpi(
                f"{today.month}월 목표", f"₩{target_val/1e8:.2f}억",
                "본사 시트", "gold", "🎯"
            ), unsafe_allow_html=True)
        else:
            st.markdown(_mini_kpi("목표", "—", "미입력", "neutral", "🎯"),
                        unsafe_allow_html=True)
    with r1c2:
        st.markdown(_mini_kpi(
            "누계 매출", f"₩{cur_sales/1e8:.2f}억",
            f"({cur_sales:,})", "gold", "💰"
        ), unsafe_allow_html=True)
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        if rate is not None:
            days_in_month = monthrange(today.year, today.month)[1]
            pace = today.day / days_in_month * 100
            trend = "up" if rate >= pace else "down"
            st.markdown(_mini_kpi(
                "달성률", f"{rate:.1f}%",
                f"진척 {pace:.0f}%", trend, "📊"
            ), unsafe_allow_html=True)
        else:
            conv = len(paid_month) / max(len(month_df), 1) * 100
            st.markdown(_mini_kpi(
                "전환률", f"{conv:.1f}%",
                f"{len(paid_month)}/{len(month_df)}", "neutral", "📊"
            ), unsafe_allow_html=True)
    with r2c2:
        st.markdown(_mini_kpi(
            "일평균", f"₩{daily_avg/1e6:.1f}M",
            f"{active_days}일 활성", "gold", "📈"
        ), unsafe_allow_html=True)


def _mini_kpi(label: str, value: str, sub: str = "", trend: str = "neutral", icon: str = "") -> str:
    sub_cls = trend if trend in ("up","down","gold") else ""
    icon_html = f'<div class="km-icon">{icon}</div>' if icon else ""
    return f"""
<div class="wl-kpi-mini">
  {icon_html}
  <div class="km-label">{label}</div>
  <div>
    <div class="km-value">{value}</div>
    <div class="km-sub {sub_cls}">{sub}</div>
  </div>
</div>
"""


def _render_persons_quick_summary(df: pd.DataFrame):
    """우측: 이번달 담당자별 매출 미니 리더보드"""
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    if not len(month_df):
        return
    st.markdown("##### 👤 이번달 담당자 Top 5")
    by_p = aggregate_by_person(month_df).head(5)
    if not len(by_p):
        st.caption("담당자 데이터 없음")
        return
    for i, row in enumerate(by_p.itertuples(), 1):
        color = _person_color(row.persons)
        st.markdown(leaderboard_row(
            rank=i, name=row.persons,
            sub=f"상담 {row.consult_count} · 결제 {row.paid_count}",
            value=f"₩{int(row.sales/1e6):,}M", value_label="MONTH",
            color=color,
        ), unsafe_allow_html=True)


# ============================================================
# 일별 카드 (좌측 7/12) — 스프레드시트 1:1
# ============================================================
def _render_daily_cards(f: pd.DataFrame, chip: str):
    today = date.today()
    grouped = sorted(
        f.groupby(f["date"].dt.date),
        key=lambda kv: kv[0],
        reverse=True,
    )
    if not grouped:
        st.info("선택 기간에 데이터 없음")
        return

    # 칩에 따라 펼침 정책
    if chip in ("today", "yesterday", "date"):
        # 단일 일자 → 모두 펼침
        expanded_set = {d for d, _ in grouped}
    else:
        # 다일 → 첫번째(최신)만 펼침
        expanded_set = {grouped[0][0]} if grouped else set()

    # 30일 같이 많을 때는 좌우 네비
    if chip == "30d" and len(grouped) > 10:
        nav = st.columns([1, 4, 1])
        page_key = "wl_30d_page"
        page = nav[1].slider(
            f"날짜 슬라이드 (총 {len(grouped)}일)",
            1, len(grouped), st.session_state.get(page_key, 1),
            key=page_key, label_visibility="collapsed",
        )
        # 5일 윈도우 표시
        win_start = (page - 1)
        grouped = grouped[win_start: win_start + 7]
        nav[0].caption(f"← {grouped[0][0].strftime('%m/%d') if grouped else ''}")
        nav[2].caption(f"{grouped[-1][0].strftime('%m/%d') if grouped else ''} →")

    for d_obj, day_df in grouped:
        _render_day_block(d_obj, day_df,
                          is_today=(d_obj == today),
                          force_expanded=(d_obj in expanded_set))


def _render_day_block(d_obj: date, day_df: pd.DataFrame,
                      is_today: bool = False, force_expanded: bool = False):
    weekday = ["월","화","수","목","금","토","일"][d_obj.weekday()]
    paid = day_df[day_df["amount"] > 0]
    total_paid = int(paid["amount"].sum())
    n_entries = len(day_df)

    header_label = f"📅 {d_obj.strftime('%Y.%m.%d')} ({weekday})"
    if is_today:
        header_label = f"⭐ {header_label} · 오늘"

    with st.expander(
        f"{header_label}  ·  유입 {n_entries}팀  ·  결제 ₩{total_paid:,}",
        expanded=(is_today or force_expanded),
    ):
        # 채널·카테고리 forward-fill (셀 병합 효과 재현)
        day_df_d = day_df.copy().reset_index(drop=True)
        day_df_d["channel"] = day_df_d["channel"].replace("", pd.NA).ffill().fillna("(미지정)")
        day_df_d["category"] = day_df_d["category"].replace("", pd.NA).ffill().fillna("(미지정)")

        channel_order = {"내방":0, "유선":1, "온라인":2, "소개":3, "(미지정)":9}
        category_order = {"소비자":0, "업체":1, "디자이너":2, "(미지정)":9}

        for ch in sorted(day_df_d["channel"].unique(),
                          key=lambda c: channel_order.get(c, 5)):
            ch_df = day_df_d[day_df_d["channel"] == ch]
            ch_label = CHANNEL_LABEL.get(ch, f"  {ch}")
            ch_css = CHANNEL_CSS.get(ch, "")
            ch_paid_sum = int(ch_df[ch_df["amount"] > 0]["amount"].sum())
            ch_paid_caption = f" · ₩{ch_paid_sum:,}" if ch_paid_sum else ""
            st.markdown(
                f'<div class="wl-channel {ch_css}">{ch_label} '
                f'<span style="font-weight:400;font-size:11px;color:#999">({len(ch_df)}건{ch_paid_caption})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            for cat in sorted(ch_df["category"].unique(),
                               key=lambda c: category_order.get(c, 5)):
                cat_df = ch_df[ch_df["category"] == cat]
                st.markdown(
                    f'<div class="wl-category">└─ {cat} '
                    f'<span style="font-weight:400;color:#999">({len(cat_df)}건)</span></div>',
                    unsafe_allow_html=True,
                )
                for r in cat_df.itertuples():
                    _render_record_row(r)

        # 일일 합계 푸터
        st.markdown(f"""
<div class="wl-day-footer">
  <span>상담 <b>{n_entries}건</b></span>
  <span>결제 <b>{len(paid)}건</b></span>
  <span>매출 <b>₩{total_paid:,}</b></span>
  <span>객단가 <b>₩{(total_paid // max(len(paid), 1)) if len(paid) else 0:,}</b></span>
</div>
""", unsafe_allow_html=True)


def _render_record_row(r):
    status_v = (r.status or "").strip() or "—"
    status_color = STATUS_COLOR.get(status_v, "#999")
    cust = (r.customer or "—").replace("\n", " / ")
    phone = (r.phone or "").strip()
    content = (r.content or "").strip().replace("\n", " ")
    if len(content) > 50:
        content_disp = content[:50] + "…"
    else:
        content_disp = content
    amount = int(r.amount or 0)
    brands = r.brands if isinstance(r.brands, list) else []
    brands_html = f'<div class="wr-brands">🏷 {" · ".join(brands[:5])}</div>' if brands else ""
    phone_html = f'<span class="wr-phone">☎ {phone}</span>' if phone else ""
    amount_html = (
        f'<div class="wr-amount">₩{amount:,}</div>' if amount > 0
        else '<div class="wr-amount zero">—</div>'
    )
    person_html = _person_badge(r.person_raw or "") or '<span style="color:#999">—</span>'

    st.markdown(f"""
<div class="wl-record">
  <div class="wr-status" style="background:{status_color}">{status_v}</div>
  <div class="wr-body">
    <div><span class="wr-customer">{cust}</span>{phone_html}</div>
    <div class="wr-content" title="{content}">{content_disp}</div>
    {brands_html}
  </div>
  <div class="wr-person">{person_html}</div>
  {amount_html}
</div>
""", unsafe_allow_html=True)


# ============================================================
# 신규 입력 인라인 폼
# ============================================================
def _render_inline_form():
    st.markdown('<div class="wl-inline-form"><div class="if-title">➕ 새 영업 기록</div></div>',
                unsafe_allow_html=True)
    from parsers.worklog_writer import _has_service_account
    if not _has_service_account():
        st.caption("ⓘ Service Account 미설정 — 저장 시 TSV 텍스트 출력 (수동 모드)")

    with st.form("wl_inline_form", clear_on_submit=True):
        r1 = st.columns([1.2, 1, 1, 1])
        f_date = r1[0].date_input("일자", value=date.today())
        f_channel = r1[1].selectbox("채널", CHANNEL_OPTIONS, index=0)
        f_category = r1[2].selectbox("카테고리", CATEGORY_OPTIONS, index=0)
        f_status = r1[3].selectbox("현황", STATUS_OPTIONS, index=1)

        r2 = st.columns([2, 2])
        f_customer = r2[0].text_input("고객명", placeholder="예) 단체 가족")
        f_phone = r2[1].text_input("연락처", placeholder="010-XXXX-XXXX")

        f_content = st.text_area("내용", height=70,
                                  placeholder="상담 내용 한 줄")

        r3 = st.columns([1.5, 1])
        f_person = r3[0].text_input("담당자", placeholder="예) 서영완 / 추승민")
        f_amount = r3[1].number_input("매출(원)", min_value=0, step=10_000, value=0)

        bc1, bc2 = st.columns([1, 1])
        submitted = bc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancel = bc2.form_submit_button("✕ 닫기", use_container_width=True)

    if cancel:
        st.session_state["wl_show_form"] = False
        st.rerun()

    if submitted:
        if not f_customer.strip():
            st.error("고객명 필수")
            return
        record = {
            "channel": f_channel, "category": f_category, "status": f_status,
            "customer": f_customer.strip(), "phone": f_phone.strip(),
            "content": f_content.strip(), "person": f_person.strip(),
            "amount": f_amount if f_amount > 0 else "",
        }
        with st.spinner("본사 시트 저장 중..."):
            result = append_worklog_row(record, f_date, SHEET_ID, WORKLOG_TAB)
        if result["ok"]:
            st.success(f"✓ 저장 완료 (행 {result['row']})")
            st.session_state["wl_show_form"] = False
            st.cache_data.clear()
            st.balloons()
            st.rerun()
        else:
            st.warning(f"⚠ 자동 write 미실행: {result.get('error', '')}")
            if result.get("header_tsv"):
                st.caption("📌 새 날짜 블록 헤더:")
                st.code(result["header_tsv"], language="text")
            st.caption("📌 데이터 행:")
            st.code(result["tsv"], language="text")


# ============================================================
# 월별 / 연별 (하단 expander 안)
# ============================================================
def _render_monthly_view(f: pd.DataFrame, target: dict | None):
    avail = sorted(f["ym"].unique(), reverse=True)
    if not avail:
        st.info("월별 데이터 없음")
        return
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    default = cur_ym if cur_ym in avail else avail[0]
    sel_ym = st.selectbox("🗓 월", avail, index=avail.index(default), key="wl_m_ym2")
    month_df = f[f["ym"] == sel_ym]
    paid = month_df[month_df["amount"] > 0]
    total = int(paid["amount"].sum())
    deals = len(paid)

    cols = st.columns(3)
    cols[0].metric("매출", f"₩{total:,}")
    cols[1].metric("결제건", f"{deals}건")
    cols[2].metric("객단가", f"₩{total//max(deals,1):,}")

    if len(paid):
        daily = paid.groupby(paid["date"].dt.date)["amount"].sum().reset_index()
        daily.columns = ["date", "amount"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["amount"], mode="lines+markers",
            line=dict(color="#C9A961", width=3, shape="spline"),
            marker=dict(size=8, color="#0A0A0A"), fill="tozeroy",
            fillcolor="rgba(201,169,97,0.1)",
        ))
        fig.update_layout(height=260, margin=dict(t=20,b=20,l=20,r=20),
                          plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
        fig.update_xaxes(gridcolor="#E8E8E8")
        fig.update_yaxes(gridcolor="#E8E8E8")
        st.plotly_chart(fig, use_container_width=True)


def _render_yearly_view(f: pd.DataFrame):
    f = f.copy()
    f["year"] = f["date"].dt.year
    f["quarter"] = f["date"].dt.quarter
    avail = sorted(f["year"].dropna().unique(), reverse=True)
    if not avail:
        return
    sel_year = st.selectbox("📆 연도", avail, index=0, key="wl_y_year2")
    year_df = f[f["year"] == sel_year]
    paid = year_df[year_df["amount"] > 0]
    total = int(paid["amount"].sum())
    cols = st.columns(3)
    cols[0].metric("연 누계", f"₩{total/1e8:.2f}억")
    cols[1].metric("결제건", f"{len(paid)}건")
    vip = paid[paid["amount"] >= VIP_THRESHOLD]
    cols[2].metric("VIP 매출", f"₩{int(vip['amount'].sum())/1e8:.2f}억")

    # 월별 라인
    m_agg = paid.groupby("ym").agg(sales=("amount","sum")).reset_index().sort_values("ym")
    if len(m_agg):
        fig = px.line(m_agg, x="ym", y="sales", markers=True,
                      color_discrete_sequence=["#C9A961"])
        fig.update_layout(height=260, plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)

    # LTV Top 5
    ltv = aggregate_by_customer(paid).sort_values("sales", ascending=False).head(5)
    for i, row in enumerate(ltv.itertuples(), 1):
        color = _person_color("") if i > 3 else ["#C9A961", "#0A0A0A", "#0A0A0A"][i-1]
        st.markdown(leaderboard_row(
            rank=i, name=(row.customer or "—")[:25],
            sub=f"{row.visits}건 · 최근 {row.last_visit.strftime('%m/%d') if pd.notna(row.last_visit) else '—'}",
            value=f"₩{int(row.sales):,}", value_label="LIFETIME", color=color,
        ), unsafe_allow_html=True)


# ============================================================
# 본사 시트 내방객 추이 표
# ============================================================
def _render_visitor_trend():
    with st.expander("📊 내방객 추이 (본사 시트 별도 탭)", expanded=False):
        vdf = load_visitor_trend()
        has_data = False
        if len(vdf) >= 3:
            try:
                header_row = vdf.iloc[0].tolist()
                metrics = [c for c in header_row[1:4] if c and str(c).strip()]
                simple_row = vdf.iloc[1].tolist()
                buying_row = vdf.iloc[2].tolist()
                simple_vals = [str(simple_row[i+1]).strip() for i in range(len(metrics))]
                buying_vals = [str(buying_row[i+1]).strip() for i in range(len(metrics))]
                has_data = any(v and v not in ("nan", "") for v in simple_vals + buying_vals)
                if has_data:
                    vt_df = pd.DataFrame({
                        "구분": [str(simple_row[0]).strip() or "단순 내방객",
                                  str(buying_row[0]).strip() or "구매 가능 고객"],
                        **{metrics[i]: [simple_vals[i] or "—", buying_vals[i] or "—"]
                           for i in range(len(metrics))},
                    })
                    st.dataframe(vt_df, hide_index=True, use_container_width=True)
            except Exception:
                has_data = False
        if not has_data:
            st.caption("ℹ 본사 시트 '내방객 추이 표' 탭에 데이터 입력 시 자동 활성화")
