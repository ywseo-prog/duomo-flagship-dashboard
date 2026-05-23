"""모듈 4: 제안서 관리 (시안 3 funnel + 만료 임박 알림)"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from parsers import load_worklog_df
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, status_badge_html,
    section_header, alert_banner, leaderboard_row,
)
from utils.notion_client import STATUS_COLORS


FUNNEL_STAGES = [
    ("제안 요청",      "#0A0A0A", "REQUESTED"),
    ("견적 발송",      "#1976D2", "QUOTED"),
    ("협상 진행",      "#7B1FA2", "NEGOTIATING"),
    ("계약 임박",      "#FF6B35", "CLOSING"),
    ("성사 / 결제",     "#2E7D32", "WON"),
]


def render():
    greeting_header("이혜지", role="제안서 관리 · 5단계 깔때기", page_title="📋 제안서 관리")

    df = load_worklog_df(source="auto")
    if not len(df):
        st.error("데이터 없음")
        return

    # 분류 매핑: status 컬럼 키워드로 funnel stage 분류
    def classify(row):
        s = str(row.get("status",""))
        amt = row.get("amount", 0)
        if amt > 0: return 4   # 성사
        if "임박" in s or "계약" in s: return 3
        if "협상" in s or "조율" in s or "조정" in s: return 2
        if "견적" in s or "발송" in s or "송부" in s: return 1
        if "제안" in s or "문의" in s or "요청" in s: return 0
        return 0

    work = df.copy()
    work["stage"] = work.apply(classify, axis=1)
    work["created"] = pd.to_datetime(work["date"], errors="coerce")
    work["expire"] = work["created"] + pd.Timedelta(days=30)
    today = pd.Timestamp(datetime.now().date())

    stage_counts = [int((work["stage"]==i).sum()) for i in range(len(FUNNEL_STAGES))]
    total = max(sum(stage_counts), 1)
    won = stage_counts[4]
    win_rate = won / total * 100

    # === Black KPI ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("진행 중 제안", f"{total - won:,}",
                                     f"전체 {total:,}건", "neutral", "📋"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("승률 (Win Rate)", f"{win_rate:.1f}%",
                                     f"성사 {won:,}건 / 전체 {total:,}건",
                                     "up" if win_rate >= 30 else "down", "🎯"), unsafe_allow_html=True)
    paid_amt = int(work[work["stage"]==4]["amount"].sum())
    cols[2].markdown(black_kpi_card("성사 매출", f"₩{paid_amt/1e8:.2f}억",
                                     f"건당 ₩{paid_amt//max(won,1):,}", "gold", "💰"), unsafe_allow_html=True)
    expiring = work[(work["stage"] < 4) & (work["expire"].between(today, today + pd.Timedelta(days=7)))]
    cols[3].markdown(black_kpi_card("만료 임박 (7일)", f"{len(expiring):,}",
                                     "30일 발송 → 7일 이내 만료",
                                     "down" if len(expiring) else "neutral", "⏰"), unsafe_allow_html=True)

    # === 만료 임박 알림 배너 ===
    if len(expiring):
        st.markdown(alert_banner(
            f"⚠ {len(expiring)}건의 제안이 7일 이내 만료 예정입니다",
            "고객 follow-up 또는 단계 갱신을 권장합니다.",
            level="orange", icon="⏰",
        ), unsafe_allow_html=True)

    # === 5단계 깔때기 (커스텀 CSS) ===
    st.markdown(section_header("Pipeline Funnel", "5단계 흐름 · 단계별 전환률"), unsafe_allow_html=True)
    max_count = max(stage_counts) if max(stage_counts) > 0 else 1
    for i, (label, color, _) in enumerate(FUNNEL_STAGES):
        cnt = stage_counts[i]
        pct = cnt / total * 100 if total else 0
        fill_pct = cnt / max_count * 100 if max_count else 0
        st.markdown(f"""
<div class="funnel-row" style="background:{color}">
  <div class="fn-stage">{label}</div>
  <div class="fn-bar"><div class="fn-fill" style="width:{fill_pct}%"></div></div>
  <div class="fn-value">{cnt:,}</div>
  <div class="fn-pct">{pct:.1f}%</div>
</div>
""", unsafe_allow_html=True)

    # === 만료 임박 / 진행 중 상위 ===
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown(section_header("만료 임박 Top 10", "7일 이내 / 단계별 정렬"), unsafe_allow_html=True)
        if len(expiring):
            top_exp = expiring.sort_values("expire").head(10)
            for i, row in enumerate(top_exp.itertuples(), 1):
                days_left = (row.expire - today).days
                badge = status_badge_html(FUNNEL_STAGES[row.stage][2], color=FUNNEL_STAGES[row.stage][1])
                st.markdown(leaderboard_row(
                    rank=i, name=(row.customer or "-")[:24],
                    sub=f"{badge} · {row.created.strftime('%m/%d')} 발송 · D-{days_left}",
                    value=f"₩{int(row.amount):,}" if row.amount else "—",
                    value_label="EXPECTED", color=FUNNEL_STAGES[row.stage][1],
                ), unsafe_allow_html=True)
        else:
            st.caption("만료 임박 제안 없음")

    with col_r:
        st.markdown(section_header("최근 성사 Top 10", "Won / 결제 완료"), unsafe_allow_html=True)
        won_df = work[work["stage"]==4].sort_values("amount", ascending=False).head(10)
        for i, row in enumerate(won_df.itertuples(), 1):
            st.markdown(leaderboard_row(
                rank=i, name=(row.customer or "-")[:24],
                sub=f"{row.created.strftime('%m/%d')} · {row.channel or '-'}",
                value=f"₩{int(row.amount):,}",
                value_label="WON", color="#2E7D32",
            ), unsafe_allow_html=True)

    render_task_widget("제안서")
