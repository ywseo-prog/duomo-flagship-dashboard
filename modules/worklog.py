"""모듈 2: 업무일지 — 스프레드시트 양식 1:1 재현 + 3단 뷰 + 신규 입력 폼

[원본] Google Sheets '플래그십 업무일지' 탭 (ID 1enUaMwY...)
일별 반복 블록: 날짜 행 → 카테고리 헤더 → 데이터(채널/카테고리 그룹) → 진행/이슈

[대시보드]
1. 상단 KPI 4 (목표/누계/달성률/일평균)
2. 검색·필터 (텍스트/기간/다중/매출)
3. 3단 뷰 토글: 일별(카드) / 월별 / 연별
4. 신규 입력 폼 (expander 하단)

컬러 매핑:
- 상태: done=#999, ing=#FFB300, 결제완료=#C9A961, 견적진행=#1976D2
- 담당자 6인: 서영완(골드) / 조이경(블루) / 윤소담(보라) / 추승민(그린)
  / 신민정(오렌지) / 박OO(블루그레이)
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime, timedelta
from calendar import monthrange

from parsers import (
    load_worklog_df, aggregate_monthly, aggregate_by_person, aggregate_by_brand,
    aggregate_by_customer, load_monthly_target, load_visitor_trend,
    SHEET_ID, WORKLOG_TAB,
    append_worklog_row, append_worklog_block,
    CHANNEL_OPTIONS, CATEGORY_OPTIONS, STATUS_OPTIONS,
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


# ============================================================
# 컬러 매핑 (디자인 시스템 v0.4)
# ============================================================
STATUS_COLOR = {
    "done":      "#999999",
    "ing":       "#FFB300",
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

PERSON_COLOR = {
    "서영완": "#C9A961",  # 골드 (파트장)
    "조이경": "#1976D2",  # 블루
    "윤소담": "#7B1FA2",  # 보라
    "추승민": "#2E7D32",  # 그린
    "신민정": "#FF6B35",  # 오렌지
    "박미진": "#455A64",  # 블루그레이
}

CHANNEL_LABEL = {"내방": "📍 내방", "유선": "📞 유선", "온라인": "💻 온라인", "소개": "🤝 소개"}
CHANNEL_CSS = {"내방": "", "유선": "phone", "온라인": "online", "소개": "intro"}

VIP_THRESHOLD = 3_000_000


def _person_color(name: str) -> str:
    """담당자 컬러 fallback — 정규화된 풀네임에서 첫 매치"""
    if not name:
        return "#999999"
    s = str(name)
    for k, v in PERSON_COLOR.items():
        if k in s:
            return v
    return "#5D4037"


def _person_badge(person_raw: str) -> str:
    """담당자 raw 문자열 → 6인별 배지 HTML (콤마/슬래시 구분 시 다중)"""
    if not person_raw:
        return ""
    parts = []
    import re as _re
    for tok in _re.split(r"[,，、/]\s*", str(person_raw)):
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
    greeting_header(
        "서영완",
        role="조명플래그십파트 · 본사 업무일지 1:1 재현 + 통합 분석",
        page_title="📊 업무일지",
    )

    df_all = load_worklog_df(source="auto")
    if not len(df_all):
        st.error("본사 시트 데이터 로드 실패 — Google Sheets 권한 또는 네트워크 확인")
        return
    df_all = df_all.copy()
    target = load_monthly_target()

    # === 상단 고정 KPI 4 ===
    _render_top_kpi(df_all, target)

    # === 뷰 토글 + 검색·필터 ===
    vc1, vc2 = st.columns([2, 5])
    view = vc1.radio(
        "뷰",
        ["📅 일별 (스프레드시트)", "🗓 월별", "📆 연별"],
        horizontal=True,
        label_visibility="collapsed",
        key="wl_view",
    )
    fmt_count = df_all["fmt"].value_counts().to_dict()
    fmt_caption = " · ".join(f"{k} {v:,}건" for k, v in fmt_count.items())
    vc2.caption(f"📂 총 {len(df_all):,}건 ({fmt_caption}) · 자동 분류: 브랜드 12종 + 담당자 정규화")

    f = _render_filters(df_all)
    if not len(f):
        st.warning("필터 결과 0건 — 조건을 완화해 주세요.")
        return

    render_report_section("업무일지", f, period_col="date")

    if view == "📅 일별 (스프레드시트)":
        _render_daily_cards(f)
    elif view == "🗓 월별":
        _render_monthly_view(f, target)
    else:
        _render_yearly_view(f)

    # === 신규 입력 폼 (하단) ===
    _render_input_form()

    # === 본사 시트 별도 탭 ===
    _render_visitor_trend()

    render_task_widget("업무일지")


# ============================================================
# 상단 고정 KPI 4종
# ============================================================
def _render_top_kpi(df: pd.DataFrame, target: dict | None):
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    paid_month = month_df[month_df["amount"] > 0]
    cur_sales = int(paid_month["amount"].sum())
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = cur_sales // max(active_days, 1) if active_days else 0

    target_val = target.get("target") if target else None
    rate = (cur_sales / target_val * 100) if target_val else None

    cols = st.columns(4)
    if target_val:
        cols[0].markdown(black_kpi_card(
            f"{today.month}월 목표", f"₩{target_val/1e8:.2f}억",
            f"본사 시트 1행", "gold", "🎯"
        ), unsafe_allow_html=True)
    else:
        cols[0].markdown(black_kpi_card(
            f"{today.month}월 목표", "—",
            "본사 시트에 목표 미입력", "neutral", "🎯"
        ), unsafe_allow_html=True)

    cols[1].markdown(black_kpi_card(
        "금일 누계 매출", f"₩{cur_sales:,}",
        f"{today.month}월 누계 · {len(paid_month)}건", "gold", "💰"
    ), unsafe_allow_html=True)

    if rate is not None:
        days_in_month = monthrange(today.year, today.month)[1]
        pace = today.day / days_in_month * 100
        trend = "up" if rate >= pace else "down"
        cols[2].markdown(black_kpi_card(
            "달성률", f"{rate:.1f}%",
            f"진척 {pace:.0f}% · 잔여 ₩{max(target_val-cur_sales, 0)/1e8:.2f}억",
            trend, "📊"
        ), unsafe_allow_html=True)
    else:
        cols[2].markdown(black_kpi_card(
            "전환률", f"{len(paid_month)/max(len(month_df),1)*100:.1f}%",
            f"결제 {len(paid_month)} / 상담 {len(month_df)}",
            "neutral", "📊"
        ), unsafe_allow_html=True)

    cols[3].markdown(black_kpi_card(
        "이번달 일평균", f"₩{daily_avg:,}",
        f"활성일 {active_days}일", "gold", "📈"
    ), unsafe_allow_html=True)


# ============================================================
# 검색·필터 (collapsible)
# ============================================================
def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    with st.expander("🔧 검색 · 필터", expanded=False):
        search = st.text_input(
            "🔍 텍스트 검색 (고객·내용·연락처·담당자·브랜드)",
            placeholder="예) 카민디자인 / FLOS / 010-1234 / 추승민",
            key="wl_search",
        )
        c1, c2, c3 = st.columns([1, 1, 2])
        min_date = df["date"].min().date() if pd.notna(df["date"].min()) else date.today()
        max_date = df["date"].max().date() if pd.notna(df["date"].max()) else date.today()
        d1 = c1.date_input("시작", min_date, key="wl_d1")
        d2 = c2.date_input("종료", max_date, key="wl_d2")
        c3.caption(f"전체 기간: {min_date} ~ {max_date}")

        c4, c5, c6, c7 = st.columns(4)
        chans = sorted([c for c in df["channel"].unique() if c])
        chan_f = c4.multiselect("📍 채널", chans, default=[], key="wl_ch")
        cats = sorted([c for c in df["category"].unique() if c])
        cat_f = c5.multiselect("🏷 카테고리", cats, default=[], key="wl_cat")
        sts = sorted([s for s in df["status"].unique() if s])
        st_f = c6.multiselect("🚦 현황", sts, default=[], key="wl_st")
        person_opts = sorted(set(p for ps in df["persons"] for p in ps if p))
        per_f = c7.multiselect("👤 담당자", person_opts, default=[], key="wl_per")

        c8, c9 = st.columns([3, 2])
        max_amt = int(df["amount"].max()) if len(df) else 10_000_000
        amt_range = c8.slider(
            "💰 매출 범위", 0, max(max_amt, 1_000_000),
            (0, max(max_amt, 1_000_000)), 100_000, key="wl_amt"
        )
        only_paid = c9.checkbox("결제건만", value=False, key="wl_paid")
        only_vip = c9.checkbox(f"VIP만 (≥₩{VIP_THRESHOLD/1e6:.0f}M)", value=False, key="wl_vip")

    f = f[(f["date"].dt.date >= d1) & (f["date"].dt.date <= d2)]
    if chan_f:
        f = f[f["channel"].isin(chan_f)]
    if cat_f:
        f = f[f["category"].isin(cat_f)]
    if st_f:
        f = f[f["status"].isin(st_f)]
    if per_f:
        f = f[f["persons"].apply(lambda ps: any(p in ps for p in per_f))]
    f = f[(f["amount"] >= amt_range[0]) & (f["amount"] <= amt_range[1])]
    if only_paid:
        f = f[f["amount"] > 0]
    if only_vip:
        f = f[f["amount"] >= VIP_THRESHOLD]
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
    return f


# ============================================================
# View 1. 📅 일별 — 스프레드시트 1:1 재현 카드
# ============================================================
def _render_daily_cards(f: pd.DataFrame):
    st.markdown(section_header(
        "본사 업무일지 — 일별 블록", "스프레드시트 양식 1:1 재현"
    ), unsafe_allow_html=True)

    today = date.today()
    # 날짜별 group 후 역순 정렬
    grouped = sorted(
        f.groupby(f["date"].dt.date),
        key=lambda kv: kv[0],
        reverse=True,
    )

    PAGE_SIZE = 7
    total_days = len(grouped)
    if total_days > PAGE_SIZE:
        page = st.number_input(
            f"페이지 (총 {total_days}일, 페이지당 {PAGE_SIZE}일)",
            min_value=1, max_value=(total_days + PAGE_SIZE - 1) // PAGE_SIZE,
            value=1, step=1, key="wl_daily_page",
        )
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
    else:
        start, end = 0, total_days

    for d_obj, day_df in grouped[start:end]:
        _render_day_block(d_obj, day_df, is_today=(d_obj == today))


def _render_day_block(d_obj: date, day_df: pd.DataFrame, is_today: bool = False):
    weekday = ["월","화","수","목","금","토","일"][d_obj.weekday()]
    paid = day_df[day_df["amount"] > 0]
    total_paid = int(paid["amount"].sum())
    n_entries = len(day_df)

    # 진행/이슈 메모 분리 (parser는 이를 별도로 보존 안 함 — content에 합쳐져 있을 가능성)
    # 여기서는 표시만 (시트의 진행/이슈 행은 parser에서 skip됨)
    progress_notes = []
    issue_notes = []

    # 헤더 + 미니 KPI
    header_label = f"📅 {d_obj.strftime('%Y.%m.%d')} ({weekday})"
    if is_today:
        header_label = f"⭐ {header_label} · 오늘"

    with st.expander(header_label, expanded=is_today):
        # 메타 행
        mc1, mc2, mc3, mc4 = st.columns([2, 1, 1, 1])
        mc1.markdown(f"""
<div class="wl-day-meta">
  <div class="wm-kpi">
    <span>유입 <b>{n_entries}팀</b></span>
    <span>결제 <b>{len(paid)}건</b></span>
    <span>매출 <b>₩{total_paid:,}</b></span>
  </div>
</div>
""", unsafe_allow_html=True)
        if mc4.button("✏ 빠른 추가", key=f"add_{d_obj.isoformat()}", help="이 날짜에 새 행을 추가합니다"):
            st.session_state["form_default_date"] = d_obj
            st.session_state["scroll_to_form"] = True

        # === 채널 → 카테고리 grouped 렌더 ===
        # 본사 시트는 같은 블록 내 채널/카테고리 셀을 병합으로 표시 (빈 셀 = 위 행 상속)
        # parser는 raw로 가져오므로 forward-fill로 시트와 동일한 시각 효과 재현.
        day_df_d = day_df.copy().reset_index(drop=True)
        day_df_d["channel"] = day_df_d["channel"].replace("", pd.NA).ffill().fillna("(미지정)")
        day_df_d["category"] = day_df_d["category"].replace("", pd.NA).ffill().fillna("(미지정)")
        day_df_d["channel_d"] = day_df_d["channel"]
        day_df_d["category_d"] = day_df_d["category"]

        channel_order = {"내방":0, "유선":1, "온라인":2, "소개":3, "기타":4, "(미지정)":9}
        category_order = {"소비자":0, "업체":1, "디자이너":2, "기타":3, "(미지정)":9}

        for ch in sorted(day_df_d["channel_d"].unique(), key=lambda c: channel_order.get(c, 5)):
            ch_df = day_df_d[day_df_d["channel_d"] == ch]
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
            for cat in sorted(ch_df["category_d"].unique(), key=lambda c: category_order.get(c, 5)):
                cat_df = ch_df[ch_df["category_d"] == cat]
                st.markdown(
                    f'<div class="wl-category">└─ {cat} '
                    f'<span style="font-weight:400;color:#999">({len(cat_df)}건)</span></div>',
                    unsafe_allow_html=True,
                )
                for r in cat_df.itertuples():
                    _render_record_row(r)

        # 진행/이슈 메모 (parser 미보존 — 자리 마련만)
        st.markdown(
            '<div class="wl-memo-box"><span class="wm-tag">📝 진행사항</span>'
            '<span style="color:#999">시트의 진행사항 행은 본 모듈에서 직접 표시되지 않습니다 — '
            '본사 시트에서 직접 확인하세요.</span></div>',
            unsafe_allow_html=True,
        )


def _render_record_row(r):
    status_v = (r.status or "").strip() or "—"
    status_color = STATUS_COLOR.get(status_v, "#999")
    cust = (r.customer or "—").replace("\n", " / ")
    phone = (r.phone or "").strip()
    content = (r.content or "").strip().replace("\n", " ")
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
    <div class="wr-content">{content[:200]}{'…' if len(content) > 200 else ''}</div>
    {brands_html}
  </div>
  <div class="wr-person">{person_html}</div>
  {amount_html}
</div>
""", unsafe_allow_html=True)


# ============================================================
# View 2. 🗓 월별
# ============================================================
def _render_monthly_view(f: pd.DataFrame, target: dict | None):
    available_yms = sorted(f["ym"].unique(), reverse=True)
    if not available_yms:
        st.info("월별 데이터 없음")
        return
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    default_ym = cur_ym if cur_ym in available_yms else available_yms[0]
    sel_ym = st.selectbox("🗓 월", available_yms, index=available_yms.index(default_ym),
                          key="wl_m_ym")
    sel_year, sel_month = int(sel_ym[:4]), int(sel_ym[5:7])
    month_df = f[f["ym"] == sel_ym]
    paid = month_df[month_df["amount"] > 0]

    total_sales = int(paid["amount"].sum())
    deals = len(paid)
    consult = len(month_df)
    avg_ticket = total_sales // max(deals, 1) if deals else 0
    active_days = month_df["date"].dt.date.nunique()

    # MoM
    monthly_agg = aggregate_monthly(f)
    mom = 0
    if sel_ym in monthly_agg["ym"].values:
        cur_idx = monthly_agg[monthly_agg["ym"] == sel_ym].index[0]
        if cur_idx > 0:
            prev_sales = int(monthly_agg.loc[cur_idx - 1, "sales"])
            mom = (total_sales - prev_sales) / max(prev_sales, 1) * 100 if prev_sales else 0

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        f"{sel_ym} 매출", f"₩{total_sales/1e8:.2f}억",
        f"({total_sales:,})", "gold", "💰"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "MoM", f"{mom:+.1f}%", f"활성 {active_days}일",
        "up" if mom >= 0 else "down", "📈"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "객단가 / 전환률", f"₩{avg_ticket:,}",
        f"전환 {deals/max(consult,1)*100:.1f}%",
        "gold" if deals/max(consult,1)*100 >= 20 else "neutral", "🎯"
    ), unsafe_allow_html=True)
    if target and target.get("target") and target.get("month") == sel_month:
        rate = total_sales / target["target"] * 100
        days_in_month = monthrange(sel_year, sel_month)[1]
        cols[3].markdown(black_kpi_card(
            "목표 달성률", f"{rate:.1f}%",
            f"목표 ₩{target['target']/1e8:.2f}억", "up" if rate >= 80 else "down", "🎯"
        ), unsafe_allow_html=True)
    else:
        daily_avg = total_sales // max(active_days, 1) if active_days else 0
        cols[3].markdown(black_kpi_card(
            "일평균", f"₩{daily_avg:,}", f"{active_days}일", "gold", "📊"
        ), unsafe_allow_html=True)

    # 일별 매출 라인 차트
    st.markdown(section_header(f"{sel_ym} 일별 매출 추세"), unsafe_allow_html=True)
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
        fig.update_layout(
            height=300, margin=dict(t=20,b=20,l=20,r=20),
            plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False,
        )
        fig.update_xaxes(gridcolor="#E8E8E8")
        fig.update_yaxes(gridcolor="#E8E8E8", title_text="매출(₩)")
        st.plotly_chart(fig, use_container_width=True)

    # 일별 카드 압축 표시
    st.markdown(section_header(f"{sel_ym} 일별 블록 (압축)", "expander로 펼쳐서 보기"),
                unsafe_allow_html=True)
    _render_daily_cards(month_df)


# ============================================================
# View 3. 📆 연별
# ============================================================
def _render_yearly_view(f: pd.DataFrame):
    f = f.copy()
    f["year"] = f["date"].dt.year
    f["quarter"] = f["date"].dt.quarter
    avail_years = sorted(f["year"].dropna().unique(), reverse=True)
    if not avail_years:
        st.info("연도별 데이터 없음")
        return
    sel_year = st.selectbox("📆 연도", avail_years, index=0, key="wl_y_year")
    year_df = f[f["year"] == sel_year]
    paid = year_df[year_df["amount"] > 0]

    total_sales = int(paid["amount"].sum())
    deals = len(paid)
    active_months = year_df["ym"].nunique()
    avg_monthly = total_sales // max(active_months, 1) if active_months else 0
    monthly_sum = paid.groupby("ym")["amount"].sum()
    best_ym = monthly_sum.idxmax() if len(monthly_sum) else "—"
    best_sales = int(monthly_sum.max()) if len(monthly_sum) else 0
    vip = paid[paid["amount"] >= VIP_THRESHOLD]

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        f"{sel_year}년 누계", f"₩{total_sales/1e8:.2f}억",
        f"{deals}건", "gold", "💰"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "월 평균", f"₩{avg_monthly/1e8:.2f}억",
        f"{active_months}개월 활성", "neutral", "📊"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "최고 월", best_ym, f"₩{best_sales/1e8:.2f}억", "up", "🏆"
    ), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card(
        "VIP 매출", f"₩{int(vip['amount'].sum())/1e8:.2f}억",
        f"{len(vip)}건 / {len(vip)/max(deals,1)*100:.0f}%",
        "gold", "💎"), unsafe_allow_html=True)

    # 월별 라인 + 분기 비교
    col_m, col_q = st.columns([2, 1])
    with col_m:
        st.markdown(section_header(f"{sel_year}년 월별 매출"), unsafe_allow_html=True)
        m_agg = paid.groupby("ym").agg(sales=("amount","sum"), deals=("amount","count")).reset_index().sort_values("ym")
        if len(m_agg):
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=m_agg["ym"], y=m_agg["deals"], name="결제 건수",
                                  marker_color="#E8E8E8"), secondary_y=True)
            fig.add_trace(go.Scatter(x=m_agg["ym"], y=m_agg["sales"], name="매출",
                                      mode="lines+markers",
                                      line=dict(color="#C9A961", width=3),
                                      marker=dict(size=10, color="#0A0A0A")),
                           secondary_y=False)
            fig.update_layout(height=320, margin=dict(t=30,b=20,l=20,r=20),
                              plot_bgcolor="#fff", paper_bgcolor="#fff",
                              legend=dict(orientation="h", y=1.1))
            fig.update_yaxes(title_text="매출(₩)", secondary_y=False, gridcolor="#E8E8E8")
            fig.update_yaxes(title_text="건수", secondary_y=True, gridcolor="#E8E8E8")
            st.plotly_chart(fig, use_container_width=True)

    with col_q:
        st.markdown(section_header("분기 비교"), unsafe_allow_html=True)
        q_df = paid.groupby("quarter").agg(sales=("amount","sum")).reset_index()
        if len(q_df):
            q_df["분기"] = q_df["quarter"].apply(lambda q: f"Q{q}")
            fig = go.Figure(go.Bar(
                x=q_df["분기"], y=q_df["sales"],
                marker_color=["#0A0A0A","#1976D2","#C9A961","#FF6B35"][:len(q_df)],
                text=[f"₩{int(v/1e8):.1f}억" if v >= 1e8 else f"₩{int(v/1e6):,}M" for v in q_df["sales"]],
                textposition="outside",
            ))
            fig.update_layout(height=320, margin=dict(t=30,b=20,l=20,r=20),
                              plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
            fig.update_yaxes(gridcolor="#E8E8E8")
            st.plotly_chart(fig, use_container_width=True)

    # LTV Top 10
    st.markdown(section_header(f"LTV Top 10 — {sel_year}년 누적"), unsafe_allow_html=True)
    ltv = aggregate_by_customer(paid).sort_values("sales", ascending=False).head(10)
    for i, row in enumerate(ltv.itertuples(), 1):
        color = "#C9A961" if i == 1 else ("#0A0A0A" if i <= 3 else "#999999")
        name = (row.customer or "—")[:25]
        last = row.last_visit.strftime("%m/%d") if pd.notna(row.last_visit) else "—"
        st.markdown(leaderboard_row(
            rank=i, name=name,
            sub=f"{row.visits}건 · 최근 {last}",
            value=f"₩{int(row.sales):,}", value_label="LIFETIME", color=color,
        ), unsafe_allow_html=True)


# ============================================================
# 신규 입력 폼 (하단 expander)
# ============================================================
def _render_input_form():
    default_date = st.session_state.get("form_default_date", date.today())
    expanded = st.session_state.pop("scroll_to_form", False)
    with st.expander("➕ 새 영업 기록 추가 (본사 시트에 즉시 기록)", expanded=expanded):
        from parsers.worklog_writer import _has_service_account
        if _has_service_account():
            st.markdown(alert_banner(
                "✓ Service Account 활성", "저장 시 본사 시트의 해당 날짜 블록에 자동 append됩니다.",
                level="green", icon="✓",
            ), unsafe_allow_html=True)
        else:
            st.markdown(alert_banner(
                "ⓘ Service Account 미설정 — 수동 모드",
                "저장 시 TSV 텍스트가 출력됩니다 — 복사 → 본사 시트에 붙여넣기.",
                level="blue", icon="ⓘ",
            ), unsafe_allow_html=True)

        with st.form("worklog_quick_form", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns([1.2, 1, 1, 1])
            f_date = r1c1.date_input("📅 날짜", value=default_date)
            f_channel = r1c2.selectbox("📍 채널", CHANNEL_OPTIONS, index=0)
            f_category = r1c3.selectbox("🏷 카테고리", CATEGORY_OPTIONS, index=0)
            f_status = r1c4.selectbox("🚦 현황", STATUS_OPTIONS, index=1)

            r2c1, r2c2 = st.columns([2, 2])
            f_customer = r2c1.text_input("👤 고객명",
                                          placeholder="예) 단체 가족 / 김아름 사원 손님")
            f_phone = r2c2.text_input("☎ 연락처", placeholder="010-XXXX-XXXX")

            f_content = st.text_area("📝 내용",
                                     placeholder="예) Luce / Grammoluce 견적 안내 > 다음주 재방문",
                                     height=80)

            r3c1, r3c2 = st.columns([1.5, 1])
            f_person = r3c1.text_input("🧑 담당자",
                                        placeholder="예) 서영완 선임 / 추승민 사원")
            f_amount = r3c2.number_input("💰 매출(원)", min_value=0, step=10_000, value=0)

            submitted = st.form_submit_button("💾 본사 시트에 저장", type="primary",
                                              use_container_width=True)

        if submitted:
            if not f_customer.strip():
                st.error("고객명은 필수입니다.")
                return
            record = {
                "channel": f_channel, "category": f_category, "status": f_status,
                "customer": f_customer.strip(), "phone": f_phone.strip(),
                "content": f_content.strip(), "person": f_person.strip(),
                "amount": f_amount if f_amount > 0 else "",
            }
            with st.spinner("본사 시트에 저장 중..."):
                result = append_worklog_row(record, f_date, SHEET_ID, WORKLOG_TAB)
            if result["ok"]:
                st.success(f"✓ 본사 시트에 저장 완료 (행 {result['row']}, {f_date.isoformat()})")
                st.balloons()
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning(f"⚠ 자동 write 미실행: {result.get('error', '')}")
                if result.get("header_tsv"):
                    st.caption("📌 같은 날짜 블록이 시트에 없습니다 — 헤더부터:")
                    st.code(result["header_tsv"], language="text")
                st.caption("📌 데이터 행:")
                st.code(result["tsv"], language="text")


# ============================================================
# 본사 시트: 내방객 추이 표
# ============================================================
def _render_visitor_trend():
    with st.expander("📊 내방객 추이 (본사 시트 별도 탭 연동)", expanded=False):
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
            st.caption("ℹ 본사 시트 '내방객 추이 표' 탭(B4:D6)에 단순 내방객/구매 가능 고객별 내방·견적·전환율을 입력하면 활성화됩니다.")
