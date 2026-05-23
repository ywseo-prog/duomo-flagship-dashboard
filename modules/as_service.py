"""모듈 7: AS (8단계 칸반: 정보등록 → 진단 → 부품 → 수리 → 검수 → 발송 → 도착 → 고객수령)"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


STAGES = [
    ("정보 등록",   "#999999", "REGISTERED"),
    ("진단",        "#1976D2", "DIAGNOSING"),
    ("부품 발주",   "#7B1FA2", "PARTS-ORDER"),
    ("수리 중",     "#FF6B35", "REPAIRING"),
    ("내부 검수",   "#C9A961", "QC"),
    ("발송",        "#5D4037", "SHIPPING"),
    ("도착",        "#455A64", "ARRIVED"),
    ("고객 수령",   "#2E7D32", "DELIVERED"),
]
SLA_DAYS = 14  # 등록 후 14일 이내 고객 수령 권장


@st.cache_data(ttl=600)
def _load_as():
    today = datetime.now().date()
    rows = [
        {"AS#":"AS-2605-001","브랜드":"FLOS","품명":"IC T1 (소켓 불량)","고객":"김OO","등록일":today-timedelta(days=18),"단계":7,"긴급":False,"메모":"수령 완료"},
        {"AS#":"AS-2605-002","브랜드":"ARTEMIDE","품명":"Tolomeo 암 파손","고객":"박OO","등록일":today-timedelta(days=12),"단계":5,"긴급":False,"메모":"발송 준비"},
        {"AS#":"AS-2605-003","브랜드":"LASVIT","품명":"크리스탈 파손","고객":"이OO","등록일":today-timedelta(days=10),"단계":2,"긴급":True,"메모":"부품 본사 발주"},
        {"AS#":"AS-2605-004","브랜드":"VIABIZZUNO","품명":"드라이버 교체","고객":"최OO","등록일":today-timedelta(days=8),"단계":3,"긴급":False,"메모":"수리 중"},
        {"AS#":"AS-2605-005","브랜드":"MARSET","품명":"전구 깜빡임","고객":"정OO","등록일":today-timedelta(days=6),"단계":1,"긴급":False,"메모":"진단 진행"},
        {"AS#":"AS-2605-006","브랜드":"FLOS","품명":"리모컨 페어링","고객":"강OO","등록일":today-timedelta(days=4),"단계":0,"긴급":False,"메모":"방문 진단 예약"},
        {"AS#":"AS-2605-007","브랜드":"ARTEMIDE","품명":"디머 노이즈","고객":"윤OO","등록일":today-timedelta(days=3),"단계":4,"긴급":False,"메모":"검수"},
        {"AS#":"AS-2605-008","브랜드":"VIBIA","품명":"펜던트 와이어","고객":"한OO","등록일":today-timedelta(days=2),"단계":6,"긴급":False,"메모":"도착"},
        {"AS#":"AS-2605-009","브랜드":"LASVIT","품명":"전원부 점검","고객":"오OO","등록일":today-timedelta(days=20),"단계":3,"긴급":True,"메모":"SLA 초과"},
        {"AS#":"AS-2605-010","브랜드":"FLOS","품명":"갓 크랙","고객":"임OO","등록일":today-timedelta(days=1),"단계":0,"긴급":False,"메모":"신규"},
    ]
    return pd.DataFrame(rows)


def render():
    greeting_header("신정훈", role="AS 8단계 칸반 · CS 상담이력 + 클레임노트",
                    page_title="🔧 AS")

    df = _load_as()
    if not len(df):
        st.error("AS 데이터 없음")
        return
    render_report_section("AS", df, period_col="등록일")

    today = pd.Timestamp(datetime.now().date())
    df["등록일"] = pd.to_datetime(df["등록일"])
    df["경과일"] = (today - df["등록일"]).dt.days
    df["SLA초과"] = (df["단계"] < 7) & (df["경과일"] > SLA_DAYS)

    in_progress = df[df["단계"] < 7]
    sla_over = df[df["SLA초과"]]
    urgent = df[df["긴급"] & (df["단계"] < 7)]
    avg_days = int(df[df["단계"]==7]["경과일"].mean()) if (df["단계"]==7).any() else 0

    # === KPI ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("진행 중 AS", f"{len(in_progress)}",
                                     f"전체 {len(df)}건", "neutral", "🔧"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("긴급 케이스", f"{len(urgent)}",
                                     "VIP 또는 본사 컴플레인",
                                     "down" if len(urgent) else "neutral", "🚨"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(f"SLA 초과 (>{SLA_DAYS}일)", f"{len(sla_over)}",
                                     "사내 표준 권장 기간 초과",
                                     "down" if len(sla_over) else "neutral", "⏰"), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card("평균 처리일", f"{avg_days}일",
                                     "완료된 케이스 평균",
                                     "gold", "📊"), unsafe_allow_html=True)

    # === 알림 ===
    if len(sla_over):
        names = ", ".join(sla_over["AS#"].head(5).tolist())
        st.markdown(alert_banner(
            f"⏰ SLA 초과 {len(sla_over)}건 — 우선 처리 필요",
            f"케이스: {names}{'…' if len(sla_over) > 5 else ''}",
            level="orange", icon="⏰",
        ), unsafe_allow_html=True)

    # === 8단계 칸반 ===
    st.markdown(section_header("AS 칸반 보드", "8단계 · 카드 클릭 시 상세 (예정)"),
                unsafe_allow_html=True)

    # 4컬럼 × 2행으로 8단계 표시
    for row_idx in range(2):
        kanban_html = '<div class="kanban-grid">'
        for col_idx in range(4):
            stage_i = row_idx * 4 + col_idx
            label, color, badge = STAGES[stage_i]
            stage_df = df[df["단계"] == stage_i]
            kanban_html += f"""
<div class="kanban-col">
  <div class="kc-head">
    <span>{stage_i+1}. {label}</span>
    <span class="kc-count" style="background:{color}">{len(stage_df)}</span>
  </div>
"""
            for r in stage_df.itertuples():
                flag = "🚨 " if r.긴급 else ""
                sla = " ⏰" if r.SLA초과 else ""
                kanban_html += f"""
<div class="kanban-card" style="border-left-color:{color}">
  <div class="kk-title">{flag}{r._asdict()['AS#']}{sla}</div>
  <div class="kk-meta">{r.브랜드} · {r.품명[:20]}</div>
  <div class="kk-meta">{r.고객} · D+{r.경과일}</div>
</div>
"""
            kanban_html += "</div>"
        kanban_html += "</div>"
        st.markdown(kanban_html, unsafe_allow_html=True)

    # === 긴급 / 진행 리스트 ===
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown(section_header("긴급 케이스", "VIP / 본사 클레임"),
                    unsafe_allow_html=True)
        u_df = df[df["긴급"]].sort_values("경과일", ascending=False)
        if len(u_df):
            for i, row in enumerate(u_df.itertuples(), 1):
                stage_color = STAGES[row.단계][1]
                badge = status_badge_html(STAGES[row.단계][2], color=stage_color)
                st.markdown(leaderboard_row(
                    rank=i, name=f"{row._asdict()['AS#']} · {row.브랜드}",
                    sub=f"{badge} · {row.고객} · {row.품명[:24]}",
                    value=f"D+{row.경과일}", value_label="등록 후 경과",
                    color="#D32F2F",
                ), unsafe_allow_html=True)
        else:
            st.caption("긴급 케이스 없음")

    with col_r:
        st.markdown(section_header("브랜드별 AS 비중", "최근 등록 기준"),
                    unsafe_allow_html=True)
        by_brand = df.groupby("브랜드").size().reset_index(name="건수").sort_values("건수", ascending=False)
        if len(by_brand):
            import plotly.express as px
            fig = px.bar(by_brand, x="브랜드", y="건수",
                         color_discrete_sequence=["#C9A961"])
            fig.update_layout(height=300, margin=dict(t=20,b=20,l=20,r=20),
                              plot_bgcolor="#fff", paper_bgcolor="#fff")
            fig.update_xaxes(gridcolor="#E8E8E8")
            fig.update_yaxes(gridcolor="#E8E8E8")
            st.plotly_chart(fig, use_container_width=True)

    # === 전체 테이블 ===
    with st.expander("📋 전체 AS 리스트"):
        show = df.copy()
        show["등록일"] = show["등록일"].dt.strftime("%Y-%m-%d")
        show["단계"] = show["단계"].map(lambda i: f"{i+1}. {STAGES[i][0]}")
        st.dataframe(show, hide_index=True, use_container_width=True)

    render_task_widget("AS")
