"""모듈 2: 업무일지 — 3단 뷰 (일별/월별/연별) + 강력한 필터/검색 + 7개 KPI

데이터 소스: Google Sheets 'flagship_worklog' v1.0 (본사 시트)
  - ID: 1enUaMwY092nn27BDTxvHCz9hmrZRVIxXTSU3JKjmw64
  - 탭: '플래그십 업무일지'
  - 8 필드: 일자/채널/카테고리/현황/고객/연락처/내용/담당자/매출

자동 분류:
  - 브랜드 태깅 (12종, parser의 BRAND_KEYWORDS 사용)
  - 담당자 정규화 (직책 제거, parser의 normalize_person 사용)
  - 양식 호환 (NEW 2025.10~ / OLD 2025.05 자동 감지)

KPI 공식:
  - 당월 매출, MoM, 목표 달성률, 일평균, 객단가, 전환율, VIP(≥₩3M)
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
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


VIP_THRESHOLD = 3_000_000


def render():
    greeting_header(
        "서영완",
        role="조명플래그십파트 · 업무일지 통합 분석 (3단 뷰)",
        page_title="📊 업무일지",
    )

    # === 데이터 로드 ===
    df_all = load_worklog_df(source="auto")
    if not len(df_all):
        st.error("업무일지 데이터 로드 실패 — Google Sheets 권한 또는 네트워크 확인")
        return
    df_all = df_all.copy()
    target = load_monthly_target()

    # === 양식 통합 (NEW + OLD 자동 감지) — parse_worklog가 이미 처리 ===
    fmt_count = df_all["fmt"].value_counts().to_dict()
    fmt_caption = " · ".join(f"{k} {v:,}건" for k, v in fmt_count.items())

    # === 뷰 토글 (상단 라디오) ===
    vc1, vc2 = st.columns([2, 3])
    view = vc1.radio(
        "뷰",
        ["📅 일별", "🗓 월별", "📆 연별"],
        horizontal=True,
        label_visibility="collapsed",
        key="wl_view",
    )
    vc2.caption(f"📂 총 {len(df_all):,}건 ({fmt_caption}) · 자동 분류: 브랜드 12종 + 담당자 정규화")

    # === 전역 필터 ===
    f = _render_filters(df_all)

    # === 결과 통계 헤더 ===
    if not len(f):
        st.warning("필터 결과 0건 — 조건을 완화해 주세요.")
        return

    render_report_section("업무일지", f, period_col="date")

    # === 뷰 렌더 ===
    if view == "📅 일별":
        _render_daily_view(f)
    elif view == "🗓 월별":
        _render_monthly_view(f, target)
    else:
        _render_yearly_view(f)

    # === 본사 시트 별도 탭: 내방객 추이 ===
    _render_visitor_trend()

    render_task_widget("업무일지")


# ====================================================================
# 전역 필터 (collapsible)
# ====================================================================
def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    with st.expander("🔧 검색 · 필터", expanded=False):
        # 1행: 텍스트 검색
        search = st.text_input(
            "🔍 텍스트 검색 (고객·내용·연락처·담당자)",
            placeholder="예) 카민디자인 / FLOS / 010-1234 / 추승민",
            key="wl_search",
        )

        # 2행: 기간
        c1, c2, c3 = st.columns([1, 1, 2])
        min_date = df["date"].min().date() if pd.notna(df["date"].min()) else date.today()
        max_date = df["date"].max().date() if pd.notna(df["date"].max()) else date.today()
        d1 = c1.date_input("시작", min_date, key="wl_date_from")
        d2 = c2.date_input("종료", max_date, key="wl_date_to")
        c3.caption(f"전체 기간: {min_date} ~ {max_date}")

        # 3행: 다중 필터
        c4, c5, c6, c7 = st.columns(4)
        channels = sorted([c for c in df["channel"].unique() if c])
        chan_filter = c4.multiselect("📍 채널", channels, default=[], key="wl_ch")
        cats = sorted([c for c in df["category"].unique() if c])
        cat_filter = c5.multiselect("🏷 카테고리", cats, default=[], key="wl_cat")
        statuses = sorted([s for s in df["status"].unique() if s])
        st_filter = c6.multiselect("🚦 현황", statuses, default=[], key="wl_st")
        person_options = sorted(set(p for ps in df["persons"] for p in ps if p))
        person_filter = c7.multiselect("👤 담당자", person_options, default=[], key="wl_per")

        # 4행: 매출 범위
        c8, c9 = st.columns([3, 2])
        max_amount = int(df["amount"].max()) if len(df) else 10_000_000
        amount_range = c8.slider(
            "💰 매출 범위 (0 = 미결제 포함)",
            min_value=0, max_value=max(max_amount, 1_000_000),
            value=(0, max(max_amount, 1_000_000)),
            step=100_000, key="wl_amt",
        )
        only_paid = c9.checkbox("결제건만 (>0)", value=False, key="wl_paid_only")
        only_vip = c9.checkbox(f"VIP만 (≥₩{VIP_THRESHOLD/1e6:.0f}M)", value=False, key="wl_vip")

    # === 필터 적용 ===
    f = f[(f["date"].dt.date >= d1) & (f["date"].dt.date <= d2)]
    if chan_filter:
        f = f[f["channel"].isin(chan_filter)]
    if cat_filter:
        f = f[f["category"].isin(cat_filter)]
    if st_filter:
        f = f[f["status"].isin(st_filter)]
    if person_filter:
        f = f[f["persons"].apply(lambda ps: any(p in ps for p in person_filter))]
    if amount_range[0] > 0:
        f = f[f["amount"] >= amount_range[0]]
    f = f[f["amount"] <= amount_range[1]]
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


# ====================================================================
# View 1. 📅 일별 — 날짜 선택 + KPI 4 + 채널 도넛 + 시간순 레코드
# ====================================================================
def _render_daily_view(f: pd.DataFrame):
    today = date.today()
    available_dates = sorted(f["date"].dt.date.unique(), reverse=True)
    if not available_dates:
        st.info("필터 결과에 데이터가 없습니다.")
        return
    default_date = available_dates[0] if today not in available_dates else today

    sel_date = st.date_input("📅 보고 날짜", value=default_date, key="wl_daily_date")
    day_df = f[f["date"].dt.date == sel_date]
    if not len(day_df):
        st.warning(f"{sel_date} 데이터 없음")
        return

    paid = day_df[day_df["amount"] > 0]
    weekday = ["월","화","수","목","금","토","일"][sel_date.weekday()]

    # === KPI 4종 ===
    sales_today = int(paid["amount"].sum())
    deals_today = len(paid)
    consult_today = len(day_df)
    conv_rate = deals_today / max(consult_today, 1) * 100
    avg_ticket = sales_today // max(deals_today, 1) if deals_today else 0

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        f"{sel_date.strftime('%m.%d')}({weekday}) 매출", f"₩{sales_today:,}",
        f"객단가 ₩{avg_ticket:,}", "gold" if sales_today else "neutral", "💰"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "상담 / 결제", f"{consult_today} / {deals_today}",
        f"전환률 {conv_rate:.1f}%",
        "up" if conv_rate >= 20 else ("down" if conv_rate < 5 else "neutral"), "📋"
    ), unsafe_allow_html=True)
    walk_in = int((day_df["channel"] == "내방").sum())
    phone_in = int((day_df["channel"] == "유선").sum())
    cols[2].markdown(black_kpi_card(
        "유입 (워크인/유선)", f"{walk_in} / {phone_in}",
        f"전체 {consult_today}팀", "neutral", "🚶"
    ), unsafe_allow_html=True)
    vip_today = paid[paid["amount"] >= VIP_THRESHOLD]
    cols[3].markdown(black_kpi_card(
        f"VIP (≥₩{VIP_THRESHOLD/1e6:.0f}M)", f"{len(vip_today)}건",
        f"VIP 매출 ₩{int(vip_today['amount'].sum()):,}",
        "gold" if len(vip_today) else "neutral", "💎"
    ), unsafe_allow_html=True)

    # === 채널 도넛 + 시간순 레코드 ===
    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.markdown(section_header("채널 매출 비중", "내방 / 유선 / 기타"), unsafe_allow_html=True)
        ch_df = paid.groupby("channel")["amount"].sum().reset_index()
        ch_df = ch_df[ch_df["channel"] != ""]
        if len(ch_df):
            colors = {"내방":"#C9A961", "유선":"#1976D2", "온라인":"#7B1FA2", "소개":"#F57C00"}
            fig = px.pie(
                ch_df, names="channel", values="amount", hole=0.55,
                color="channel", color_discrete_map=colors,
            )
            fig.update_traces(textposition="outside", textinfo="label+percent",
                               marker=dict(line=dict(color="#fff", width=3)))
            fig.update_layout(
                height=320, margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
                annotations=[dict(text=f"₩{sales_today/1e6:.1f}M", showarrow=False,
                                  font=dict(size=20, color="#0A0A0A", family="Inter"))],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("채널별 결제 데이터 없음")

    with col_r:
        st.markdown(section_header("시간순 레코드", f"{sel_date} ({len(day_df)}건)"),
                    unsafe_allow_html=True)
        show = day_df.copy()
        show["채널/분류"] = show["channel"] + "/" + show["category"]
        show["고객"] = show["customer"].astype(str).str[:30]
        show["담당"] = show["person_raw"].astype(str).str[:20]
        show["금액"] = show["amount"].apply(lambda v: f"₩{int(v):,}" if v else "—")
        show["브랜드"] = show["brands"].apply(lambda b: ", ".join(b[:3]) if isinstance(b, list) else "")
        show["내용"] = show["content"].astype(str).str[:60] + show["content"].astype(str).apply(lambda c: "…" if len(c) > 60 else "")
        cols_show = ["채널/분류", "status", "고객", "담당", "금액", "브랜드", "내용"]
        show = show[cols_show].rename(columns={"status":"현황"})
        st.dataframe(show, hide_index=True, use_container_width=True, height=380)


# ====================================================================
# View 2. 🗓 월별 — 월 선택 + KPI 4 + 일별 막대 + 담당자 + 브랜드
# ====================================================================
def _render_monthly_view(f: pd.DataFrame, target: dict | None):
    today = date.today()
    available_yms = sorted(f["ym"].unique(), reverse=True)
    if not available_yms:
        st.info("월별 데이터 없음")
        return

    cur_ym = f"{today.year}-{today.month:02d}"
    default_ym = cur_ym if cur_ym in available_yms else available_yms[0]
    sel_ym = st.selectbox("🗓 월 선택", available_yms, index=available_yms.index(default_ym),
                          key="wl_monthly_ym")
    sel_year, sel_month = int(sel_ym[:4]), int(sel_ym[5:7])

    month_df = f[f["ym"] == sel_ym]
    paid = month_df[month_df["amount"] > 0]

    # === KPI 4종 ===
    total_sales = int(paid["amount"].sum())
    deals = len(paid)
    consult = len(month_df)
    conv_rate = deals / max(consult, 1) * 100
    avg_ticket = total_sales // max(deals, 1) if deals else 0
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = total_sales // max(active_days, 1) if active_days else 0

    # MoM
    monthly_agg = aggregate_monthly(f)
    if sel_ym in monthly_agg["ym"].values:
        cur_idx = monthly_agg[monthly_agg["ym"] == sel_ym].index[0]
        cur_sales = int(monthly_agg.loc[cur_idx, "sales"])
        if cur_idx > 0:
            prev_sales = int(monthly_agg.loc[cur_idx - 1, "sales"])
            mom = (cur_sales - prev_sales) / max(prev_sales, 1) * 100 if prev_sales else 0
        else:
            mom = 0
    else:
        mom = 0

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        f"{sel_ym} 매출", f"₩{total_sales/1e8:.2f}억",
        f"({total_sales:,})", "gold" if total_sales else "neutral", "💰"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "MoM (전월 대비)", f"{mom:+.1f}%",
        f"활성일 {active_days}일", "up" if mom >= 0 else "down", "📈"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "객단가 / 전환율", f"₩{avg_ticket:,}",
        f"전환 {conv_rate:.1f}% · {deals}건/{consult}건",
        "gold" if conv_rate >= 20 else "neutral", "🎯"
    ), unsafe_allow_html=True)
    # 목표 달성률
    if target and target.get("target") and target.get("month") == sel_month:
        rate = total_sales / target["target"] * 100
        days_passed = today.day if sel_year == today.year and sel_month == today.month else monthrange(sel_year, sel_month)[1]
        days_in_month = monthrange(sel_year, sel_month)[1]
        pace_target = days_passed / days_in_month * 100
        cols[3].markdown(black_kpi_card(
            "목표 달성률", f"{rate:.1f}%",
            f"진척 {pace_target:.0f}% / 목표 ₩{target['target']/1e8:.2f}억",
            "up" if rate >= pace_target else "down", "🎯"
        ), unsafe_allow_html=True)
    else:
        cols[3].markdown(black_kpi_card(
            "일평균 매출", f"₩{daily_avg:,}",
            f"{active_days}일 활성", "gold", "📊"
        ), unsafe_allow_html=True)

    # === 일별 막대 + 채널 분포 ===
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown(section_header(f"{sel_ym} 일별 매출", f"활성 {active_days}일"),
                    unsafe_allow_html=True)
        if len(paid):
            daily = paid.groupby(paid["date"].dt.date)["amount"].sum().reset_index()
            daily.columns = ["date", "amount"]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=daily["date"], y=daily["amount"],
                marker_color="#C9A961",
                text=[f"₩{int(v/1e6):,}M" if v >= 1e6 else "" for v in daily["amount"]],
                textposition="outside",
            ))
            fig.update_layout(
                height=320, margin=dict(t=30,b=20,l=20,r=20),
                plot_bgcolor="#fff", paper_bgcolor="#fff",
                showlegend=False,
            )
            fig.update_xaxes(gridcolor="#E8E8E8")
            fig.update_yaxes(gridcolor="#E8E8E8")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("결제 데이터 없음")

    with col_r:
        st.markdown(section_header("VIP / 일반 비중", "₩3M 기준"), unsafe_allow_html=True)
        if total_sales:
            vip_amt = int(paid[paid["amount"] >= VIP_THRESHOLD]["amount"].sum())
            normal_amt = total_sales - vip_amt
            vip_df = pd.DataFrame([
                {"등급":"VIP (≥3M)","매출":vip_amt},
                {"등급":"일반","매출":normal_amt},
            ])
            fig = px.pie(vip_df, names="등급", values="매출", hole=0.6,
                          color_discrete_sequence=["#C9A961","#E8E8E8"])
            fig.update_traces(textposition="outside", textinfo="label+percent",
                               marker=dict(line=dict(color="#fff", width=3)))
            fig.update_layout(
                height=320, margin=dict(t=10,b=10,l=10,r=10), showlegend=False,
                annotations=[dict(text=f"VIP {vip_amt/max(total_sales,1)*100:.0f}%",
                                   showarrow=False, font=dict(size=16, color="#C9A961", family="Inter"))],
            )
            st.plotly_chart(fig, use_container_width=True)

    # === 담당자 리더보드 + 브랜드 ===
    col_p, col_b = st.columns([1, 1])
    with col_p:
        st.markdown(section_header("HR Leaderboard", "이 달 담당자별 상담/결제/매출"),
                    unsafe_allow_html=True)
        by_p = aggregate_by_person(month_df).head(8)
        if len(by_p):
            for i, row in enumerate(by_p.itertuples(), 1):
                color = "#C9A961" if i == 1 else ("#0A0A0A" if i <= 3 else "#999999")
                st.markdown(leaderboard_row(
                    rank=i, name=row.persons,
                    sub=f"상담 {row.consult_count}건 · 결제 {row.paid_count}건",
                    value=f"₩{int(row.sales):,}", value_label="SALES", color=color,
                ), unsafe_allow_html=True)
        else:
            st.caption("담당자 데이터 없음")

    with col_b:
        st.markdown(section_header("브랜드 매출 도넛", "Top 8"), unsafe_allow_html=True)
        by_b = aggregate_by_brand(month_df).head(8)
        if len(by_b) and by_b["sales"].sum() > 0:
            fig = px.pie(
                by_b, names="brands", values="sales", hole=0.5,
                color_discrete_sequence=px.colors.sequential.YlOrBr_r,
            )
            fig.update_traces(textposition="outside", textinfo="label+percent",
                               marker=dict(line=dict(color="#fff", width=2)))
            fig.update_layout(height=380, margin=dict(t=20,b=20,l=20,r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("브랜드 매출 데이터 없음 (멘션 카운트만 가능)")


# ====================================================================
# View 3. 📆 연별 — 연도 + KPI 4 + 월별 라인 + 분기 비교 + LTV Top 10
# ====================================================================
def _render_yearly_view(f: pd.DataFrame):
    f = f.copy()
    f["year"] = f["date"].dt.year
    f["quarter"] = f["date"].dt.quarter
    f["month"] = f["date"].dt.month

    available_years = sorted(f["year"].dropna().unique(), reverse=True)
    if not available_years:
        st.info("연도별 데이터 없음")
        return
    sel_year = st.selectbox("📆 연도 선택", available_years, index=0, key="wl_yearly_year")
    year_df = f[f["year"] == sel_year]
    paid = year_df[year_df["amount"] > 0]

    # === KPI 4종 ===
    total_sales = int(paid["amount"].sum())
    deals = len(paid)
    consult = len(year_df)
    avg_ticket = total_sales // max(deals, 1) if deals else 0
    active_months = year_df["ym"].nunique()
    avg_monthly = total_sales // max(active_months, 1) if active_months else 0
    # 최고 월
    monthly_sum = paid.groupby("ym")["amount"].sum()
    best_ym = monthly_sum.idxmax() if len(monthly_sum) else None
    best_sales = int(monthly_sum.max()) if len(monthly_sum) else 0
    vip = paid[paid["amount"] >= VIP_THRESHOLD]

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        f"{sel_year}년 누계", f"₩{total_sales/1e8:.2f}억",
        f"({total_sales:,}) · {deals}건", "gold", "💰"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "월 평균 매출", f"₩{avg_monthly/1e8:.2f}억",
        f"{active_months}개월 활성", "neutral", "📊"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "최고 월", best_ym or "—",
        f"₩{best_sales/1e8:.2f}억", "up", "🏆"
    ), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card(
        "VIP 매출", f"₩{int(vip['amount'].sum())/1e8:.2f}억",
        f"{len(vip)}건 ({len(vip)/max(deals,1)*100:.0f}% 점유)",
        "gold", "💎"
    ), unsafe_allow_html=True)

    # === 월별 라인 차트 ===
    st.markdown(section_header(f"{sel_year}년 월별 매출 추세", "선=매출 / 막대=결제건수"),
                unsafe_allow_html=True)
    monthly_agg = paid.groupby("ym").agg(
        sales=("amount", "sum"),
        deals=("amount", "count"),
    ).reset_index().sort_values("ym")
    if len(monthly_agg):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            x=monthly_agg["ym"], y=monthly_agg["deals"],
            name="결제 건수", marker_color="#E8E8E8",
        ), secondary_y=True)
        fig.add_trace(go.Scatter(
            x=monthly_agg["ym"], y=monthly_agg["sales"],
            name="매출", mode="lines+markers",
            line=dict(color="#C9A961", width=3),
            marker=dict(size=10, color="#0A0A0A"),
        ), secondary_y=False)
        fig.update_layout(
            height=340, margin=dict(t=30,b=20,l=20,r=20),
            plot_bgcolor="#fff", paper_bgcolor="#fff",
            legend=dict(orientation="h", y=1.1), hovermode="x unified",
        )
        fig.update_yaxes(title_text="매출(₩)", secondary_y=False, gridcolor="#E8E8E8")
        fig.update_yaxes(title_text="결제 건수", secondary_y=True, gridcolor="#E8E8E8")
        st.plotly_chart(fig, use_container_width=True)

    # === 분기 비교 + LTV Top 10 ===
    col_q, col_l = st.columns([1, 1])

    with col_q:
        st.markdown(section_header("분기 비교", "Q1 / Q2 / Q3 / Q4"), unsafe_allow_html=True)
        q_df = paid.groupby("quarter").agg(
            sales=("amount", "sum"),
            deals=("amount", "count"),
        ).reset_index()
        if len(q_df):
            q_df["분기"] = q_df["quarter"].apply(lambda q: f"Q{q}")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=q_df["분기"], y=q_df["sales"],
                marker_color=["#0A0A0A","#1976D2","#C9A961","#FF6B35"][:len(q_df)],
                text=[f"₩{int(v/1e8):,}억" if v >= 1e8 else f"₩{int(v/1e6):,}M" for v in q_df["sales"]],
                textposition="outside",
            ))
            fig.update_layout(
                height=320, margin=dict(t=30,b=20,l=20,r=20),
                plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False,
            )
            fig.update_yaxes(gridcolor="#E8E8E8")
            st.plotly_chart(fig, use_container_width=True)

    with col_l:
        st.markdown(section_header("LTV Top 10 고객", f"{sel_year}년 누적 매출 기준"),
                    unsafe_allow_html=True)
        ltv = aggregate_by_customer(paid).sort_values("sales", ascending=False).head(10)
        if len(ltv):
            for i, row in enumerate(ltv.itertuples(), 1):
                color = "#C9A961" if i == 1 else ("#0A0A0A" if i <= 3 else "#999999")
                name = (row.customer or "—")[:25]
                last = row.last_visit.strftime("%m/%d") if pd.notna(row.last_visit) else "—"
                st.markdown(leaderboard_row(
                    rank=i, name=name,
                    sub=f"{row.visits}건 · 최근 {last}",
                    value=f"₩{int(row.sales):,}",
                    value_label="LIFETIME", color=color,
                ), unsafe_allow_html=True)


# ====================================================================
# 본사 시트 별도 탭: 내방객 추이 (existing, 보존)
# ====================================================================
def _render_visitor_trend():
    st.markdown(section_header(
        "내방객 추이 (본사 시트 '내방객 추이 표' 탭 연동)",
        "내방객 / 견적건 / 결제 전환율 — 단순 내방객 vs 구매 가능 고객"
    ), unsafe_allow_html=True)
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
        st.markdown(alert_banner(
            "내방객 추이 표 데이터 미입력",
            "본사 시트 '내방객 추이 표' 탭(B4:D6)에 단순 내방객/구매 가능 고객별 내방·견적·전환율을 입력하면 자동 활성화됩니다.",
            level="blue", icon="ℹ"
        ), unsafe_allow_html=True)
