"""모듈 2: 업무일지 (시안 2 Finexy greeting + 시안 3 HR 리더보드)"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from parsers import load_worklog_df, aggregate_monthly, aggregate_by_person, aggregate_by_brand
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner,
)


def render():
    greeting_header("서영완", role="조명플래그십파트 · 업무일지 종합", page_title="📊 업무일지")

    df = load_worklog_df(source="auto")
    if not len(df):
        st.error("업무일지 데이터 로드 실패 — Google Sheets 권한 또는 네트워크 확인")
        return

    render_report_section("업무일지", df, period_col="date")

    # === Black KPI 4종 ===
    total_entries = len(df)
    paid = df[df["amount"] > 0]
    total_sales = int(paid["amount"].sum())
    distinct_days = df["date"].nunique()
    monthly = aggregate_monthly(df)
    cur_month = monthly.iloc[-1] if len(monthly) else None
    prev_month = monthly.iloc[-2] if len(monthly) >= 2 else None
    mom = 0
    if cur_month is not None and prev_month is not None and prev_month["sales"]:
        mom = (cur_month["sales"] - prev_month["sales"]) / prev_month["sales"] * 100

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        "당월 매출", f"₩{int(cur_month['sales']):,}" if cur_month is not None else "—",
        f"{int(cur_month['paid_count'])}건" if cur_month is not None else "",
        "up" if mom >= 0 else "down", "💎"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "전월 대비", f"{mom:+.1f}%",
        f"전월 ₩{int(prev_month['sales']):,}" if prev_month is not None else "—",
        "up" if mom >= 0 else "down", "📈"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "일평균 상담", f"{total_entries / max(distinct_days,1):.1f}",
        f"누계 {total_entries:,}건 · {distinct_days}일", "neutral", "📋"
    ), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card(
        "누계 매출", f"₩{total_sales/1e8:.2f}억",
        f"{len(paid):,} 거래", "gold", "🏆"
    ), unsafe_allow_html=True)

    # === Multi-card: 채널별 ===
    by_ch = df.groupby("channel")["amount"].agg(["sum","count"]).reset_index()
    by_ch = by_ch[by_ch["channel"]!=""]
    cards = []
    palette = ["#0A0A0A","#C9A961","#1976D2","#2E7D32","#7B1FA2"]
    for i, row in enumerate(by_ch.head(3).itertuples()):
        cards.append({
            "label": f"📞 {row.channel.upper() if row.channel else '기타'}",
            "value": f"₩{int(row.sum):,}",
            "sub": f"{int(row.count)}건",
            "color": palette[i % len(palette)],
            "trend": "",
        })
    while len(cards) < 3:
        cards.append({"label":"—","value":"—","sub":"","color":"#E8E8E8","trend":""})
    st.markdown(section_header("Channel Mix", "상담 채널별 매출/건수"), unsafe_allow_html=True)
    st.markdown(multi_card_row(cards), unsafe_allow_html=True)

    # === HR 리더보드 (시안 3) + 월별 트렌드 ===
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown(section_header("HR Leaderboard", "담당자별 상담 / 결제 / 매출"), unsafe_allow_html=True)
        by_p = aggregate_by_person(df).head(8)
        if len(by_p):
            max_sales = max(by_p["sales"].max(), 1)
            for i, row in enumerate(by_p.itertuples(), 1):
                color = "#C9A961" if i == 1 else ("#0A0A0A" if i <= 3 else "#999999")
                st.markdown(leaderboard_row(
                    rank=i, name=row.persons,
                    sub=f"상담 {row.consult_count}건 · 결제 {row.paid_count}건",
                    value=f"₩{int(row.sales):,}", value_label="SALES", color=color,
                ), unsafe_allow_html=True)
        else:
            st.caption("담당자 데이터 없음")

    with col_r:
        st.markdown(section_header("Monthly Trend", "최근 12개월 매출 / 상담건수"), unsafe_allow_html=True)
        m = monthly.tail(12)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=m["ym"], y=m["sales"], name="매출",
                              marker_color="#C9A961", yaxis="y1"))
        fig.add_trace(go.Scatter(x=m["ym"], y=m["entries"], name="상담건수",
                                  mode="lines+markers", line=dict(color="#0A0A0A", width=2), yaxis="y2"))
        fig.update_layout(
            height=380, margin=dict(t=20,b=20,l=20,r=20),
            plot_bgcolor="#fff", paper_bgcolor="#fff",
            legend=dict(orientation="h", y=1.1),
            yaxis=dict(title="매출(₩)", gridcolor="#E8E8E8"),
            yaxis2=dict(title="건수", overlaying="y", side="right", gridcolor="#E8E8E8"),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    # === 브랜드 멘션 TOP ===
    st.markdown(section_header("Brand Mentions Top 8", "업무일지 본문 브랜드 키워드 추출"), unsafe_allow_html=True)
    by_b = aggregate_by_brand(df).head(8)
    if len(by_b):
        fig2 = px.bar(by_b, x="brands", y="mention_count",
                      color="sales", color_continuous_scale=[[0,"#E8E8E8"],[1,"#C9A961"]],
                      labels={"brands":"브랜드","mention_count":"멘션","sales":"매출"})
        fig2.update_layout(height=300, margin=dict(t=20,b=20,l=20,r=20),
                           plot_bgcolor="#fff", paper_bgcolor="#fff")
        fig2.update_xaxes(gridcolor="#E8E8E8")
        fig2.update_yaxes(gridcolor="#E8E8E8")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.caption("브랜드 멘션 추출 결과 없음")

    # === 최근 활동 테이블 ===
    st.markdown(section_header("Recent Activities", "최근 15건"), unsafe_allow_html=True)
    recent = df.sort_values("date", ascending=False).head(15)[
        ["date","channel","category","status","customer","person_raw","amount"]
    ].copy()
    recent["date"] = recent["date"].dt.strftime("%m/%d")
    recent["amount"] = recent["amount"].apply(lambda v: f"₩{int(v):,}" if v else "—")
    recent.columns = ["일자","채널","카테고리","상태","고객","담당자","금액"]
    st.dataframe(recent, hide_index=True, use_container_width=True)

    render_task_widget("업무일지")
