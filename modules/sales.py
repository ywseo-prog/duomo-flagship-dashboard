"""모듈 3: 매출 (시안 2 Finexy multi-wallet + 시안 4 VIP 도넛)"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from parsers import load_worklog_df, aggregate_monthly
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row, section_header,
)

def render():
    greeting_header("Young Wan (매출 관리)")

    df = load_worklog_df(source="auto")
    if not len(df):
        st.error("데이터 없음")
        return
    df = df[df["fmt"]=="NEW"].copy()
    paid = df[df["amount"]>0].copy()
    render_report_section("매출", paid, period_col="date")

    # === Black KPI 4종 ===
    total = int(paid["amount"].sum())
    avg = total // len(paid) if len(paid) else 0
    vip = paid[paid["amount"]>=3_000_000]
    vip_ratio = (vip["amount"].sum() / total * 100) if total else 0
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("누계 매출", f"₩{total:,}", f"{len(paid):,} 거래", "neutral", "💎"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("평균 객단가", f"₩{avg:,}", "결제건당", "neutral", "🎯"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("VIP 매출 (≥₩300만)", f"₩{int(vip['amount'].sum()):,}", f"{len(vip)}건 · {vip_ratio:.0f}%", "up", "👑"), unsafe_allow_html=True)
    consumer_share = (paid["category"]=="소비자").sum() / len(paid) * 100 if len(paid) else 0
    cols[3].markdown(black_kpi_card("소비자 비중", f"{consumer_share:.1f}%", f"vs 업체 {100-consumer_share:.1f}%", "neutral", "👥"), unsafe_allow_html=True)

    # === 채널 3 multi-card (시안 2) ===
    st.markdown(section_header("Channel Performance (당월)", "Flagship · Department · Online"), unsafe_allow_html=True)
    may = paid[paid["ym"]=="2026-05"]
    by_ch = may.groupby("channel")["amount"].sum().to_dict()
    flagship = by_ch.get("내방", 0)
    phone = by_ch.get("유선", 0)
    online = sum(v for k,v in by_ch.items() if k not in ["내방","유선"])
    cards = [
        {"label":"🏬 FLAGSHIP", "value":f"₩{flagship:,}", "sub":"4F 본사 매장", "color":"#0A0A0A", "trend":f"▲ {(flagship/max(may['amount'].sum(),1)*100):.0f}% 점유"},
        {"label":"🏢 DEPARTMENT", "value":f"₩{phone:,}", "sub":"백화점 유선·문의", "color":"#C9A961", "trend":""},
        {"label":"💻 ONLINE", "value":f"₩{online:,}", "sub":"자사몰·기타", "color":"#1976D2", "trend":""},
    ]
    st.markdown(multi_card_row(cards), unsafe_allow_html=True)

    # === 월별 P/L 막대 + 채널 도넛 ===
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown(section_header("월별 매출 / 결제건수"), unsafe_allow_html=True)
        m = aggregate_monthly(paid)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=m["ym"], y=m["sales"], name="매출", marker_color=["#C9A961" if v>=0 else "#D32F2F" for v in m["sales"]]), secondary_y=False)
        fig.add_trace(go.Scatter(x=m["ym"], y=m["paid_count"], name="결제건수", mode="lines+markers", line=dict(color="#0A0A0A", width=2)), secondary_y=True)
        fig.update_layout(height=340, margin=dict(t=20,b=20,l=20,r=20), hovermode="x unified", plot_bgcolor="#fff", paper_bgcolor="#fff", legend=dict(orientation="h", y=1.1))
        fig.update_yaxes(title_text="매출(₩)", secondary_y=False, gridcolor="#E8E8E8")
        fig.update_yaxes(title_text="건수", secondary_y=True, gridcolor="#E8E8E8")
        st.plotly_chart(fig, use_container_width=True)
    with col_r:
        st.markdown(section_header("VIP / 일반 비중", "(시안 4)"), unsafe_allow_html=True)
        vip_data = pd.DataFrame([
            {"등급":"VIP (≥300만)","매출":int(vip["amount"].sum())},
            {"등급":"일반","매출":int(paid[paid["amount"]<3_000_000]["amount"].sum())},
        ])
        fig2 = px.pie(vip_data, names="등급", values="매출", hole=0.6, color_discrete_sequence=["#C9A961","#E8E8E8"])
        fig2.update_traces(textposition="outside", textinfo="label+percent", marker=dict(line=dict(color="#fff", width=3)))
        fig2.update_layout(height=340, margin=dict(t=10,b=10,l=10,r=10), showlegend=False, annotations=[dict(text=f"₩{total/1e6:.0f}M", showarrow=False, font=dict(size=20, color="#0A0A0A", family="Inter"))])
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(section_header("LTV Top 10 고객", "누적 매출 기준"), unsafe_allow_html=True)
    ltv = paid.groupby("customer").agg(누적매출=("amount","sum"), 거래건=("amount","count"), 최근거래=("date","max")).reset_index().sort_values("누적매출", ascending=False).head(10)
    for i, row in enumerate(ltv.itertuples(), 1):
        st.markdown(leaderboard_row(rank=i, name=(row.customer[:25] or "-"), sub=f"{row.거래건}건 · 최근 {row.최근거래.strftime('%m/%d')}", value=f"₩{int(row.누적매출):,}", value_label="LIFETIME", color="#C9A961"), unsafe_allow_html=True)

    render_task_widget("매출")
