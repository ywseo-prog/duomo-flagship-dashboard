"""모듈 5: 발주 상황 (Notion 발주마스터 실연동 + MoC/ROP + AIR/SEA 듀얼카드)"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)
from utils.notion_client import fetch_orders


STATUS_COLOR = {
    "결품":      "#D32F2F",
    "긴급":      "#FF6B35",
    "발주필요":  "#1976D2",
    "권고":      "#C9A961",
    "여유":      "#2E7D32",
}


def render():
    greeting_header("서영완", role="발주 시뮬레이션 v3 · MoC / ROP 자동 산출",
                    page_title="📦 발주 상황")

    df = fetch_orders()
    if not len(df):
        st.error("발주마스터 데이터 없음")
        return
    render_report_section("발주", df)

    # === KPI 4종 ===
    total_sku = len(df)
    shortage = df[df["상태"] == "결품"]
    urgent = df[df["상태"] == "긴급"]
    needed = df[df["상태"].isin(["발주필요","권고","결품","긴급"])]
    air = df[df["운송"] == "AIR"]
    sea = df[df["운송"] == "SEA"]

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("관리 SKU 총", f"{total_sku:,}",
                                     "발주마스터 등록", "neutral", "📦"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("결품 SKU", f"{len(shortage):,}",
                                     "재고 0 · 즉시 발주 필요",
                                     "down" if len(shortage) else "neutral", "🚨"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("발주 권고", f"{len(needed):,}",
                                     "ROP 이하 / 재발주 권장",
                                     "gold", "📊"), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card("AIR 긴급", f"{len(urgent):,}",
                                     f"AIR {len(air)} · SEA {len(sea)}",
                                     "up" if len(urgent) else "neutral", "✈"), unsafe_allow_html=True)

    # === 결품 알람 배너 ===
    if len(shortage):
        sku_list = ", ".join(shortage["SKU"].head(5).tolist())
        st.markdown(alert_banner(
            f"🚨 결품 {len(shortage)}건 — 즉시 발주가 필요합니다",
            f"SKU: {sku_list}{'…' if len(shortage) > 5 else ''}",
            level="red", icon="🚨",
        ), unsafe_allow_html=True)

    # === AIR / SEA 듀얼 카드 ===
    st.markdown(section_header("운송 모드 듀얼 카드", "긴급 AIR / 일반 SEA 분리"),
                unsafe_allow_html=True)
    air_amt = int(air["권고수량"].sum()) if "권고수량" in air.columns else 0
    sea_amt = int(sea["권고수량"].sum()) if "권고수량" in sea.columns else 0
    cards = [
        {"label":"✈ AIR (긴급)", "value":f"{len(air)} SKU",
         "sub":f"권고 총 {air_amt:,}개", "color":"#FF6B35",
         "trend":f"긴급 {len(urgent)}건 포함" if len(urgent) else ""},
        {"label":"🚢 SEA (정기)", "value":f"{len(sea)} SKU",
         "sub":f"권고 총 {sea_amt:,}개", "color":"#1976D2",
         "trend":"평균 LT 45일"},
        {"label":"📋 발주 권고 합계", "value":f"₩{(air_amt+sea_amt)*100000:,}*",
         "sub":"*단가 가정치 (실 단가 매핑 필요)",
         "color":"#0A0A0A", "trend":""},
    ]
    st.markdown(multi_card_row(cards), unsafe_allow_html=True)

    # === MoC / ROP 차트 ===
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.markdown(section_header("MoC · ROP · 현재고 비교", "SKU별 재고 안전성"),
                    unsafe_allow_html=True)
        chart_df = df.copy().head(15)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=chart_df["SKU"], y=chart_df["현재고"], name="현재고",
                              marker_color="#0A0A0A"))
        fig.add_trace(go.Scatter(x=chart_df["SKU"], y=chart_df["ROP"], name="ROP",
                                  mode="lines+markers", line=dict(color="#FF6B35", width=2, dash="dot")))
        fig.add_trace(go.Scatter(x=chart_df["SKU"], y=chart_df["MoC"], name="MoC (안전재고)",
                                  mode="lines+markers", line=dict(color="#C9A961", width=2)))
        fig.update_layout(height=380, margin=dict(t=20,b=80,l=20,r=20),
                          plot_bgcolor="#fff", paper_bgcolor="#fff",
                          legend=dict(orientation="h", y=1.1),
                          xaxis=dict(tickangle=-30))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown(section_header("상태 분포", "결품/긴급/권고/여유"),
                    unsafe_allow_html=True)
        status_df = df.groupby("상태").size().reset_index(name="count")
        fig2 = px.pie(status_df, names="상태", values="count", hole=0.6,
                      color="상태", color_discrete_map=STATUS_COLOR)
        fig2.update_traces(textposition="outside", textinfo="label+value",
                            marker=dict(line=dict(color="#fff", width=3)))
        fig2.update_layout(height=380, margin=dict(t=10,b=10,l=10,r=10),
                           showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # === 발주 권고 TOP 리스트 ===
    st.markdown(section_header("발주 권고 TOP 10", "결품 > 긴급 > 발주필요 순"),
                unsafe_allow_html=True)
    priority = {"결품":0, "긴급":1, "발주필요":2, "권고":3, "여유":4}
    sorted_df = df.copy()
    sorted_df["_p"] = sorted_df["상태"].map(priority).fillna(9)
    sorted_df = sorted_df.sort_values(["_p","권고수량"], ascending=[True, False]).head(10)
    for i, row in enumerate(sorted_df.itertuples(), 1):
        badge = status_badge_html(row.상태, color=STATUS_COLOR.get(row.상태, "#999"))
        ship_badge = status_badge_html(row.운송, color="#FF6B35" if row.운송=="AIR" else "#1976D2")
        st.markdown(leaderboard_row(
            rank=i,
            name=f"{row.브랜드} · {row.SKU}",
            sub=f"{badge} {ship_badge} · 재고 {row.현재고} / ROP {row.ROP} · 납기 {row.납기}",
            value=f"+{row.권고수량}",
            value_label="권고수량",
            color=STATUS_COLOR.get(row.상태, "#0A0A0A"),
        ), unsafe_allow_html=True)

    # === 전체 테이블 ===
    with st.expander("📋 전체 발주마스터 보기"):
        show = df.drop(columns=[c for c in ["_id"] if c in df.columns], errors="ignore")
        st.dataframe(show, hide_index=True, use_container_width=True)

    render_task_widget("발주")
