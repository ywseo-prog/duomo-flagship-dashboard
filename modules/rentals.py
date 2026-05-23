"""모듈 6: 대여 (4단계: 계약서 → 등록 → 일정 → 회수 + 연체 알림)"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


STAGES = [
    ("계약서 작성",  "#1976D2", "CONTRACT"),
    ("등록 (입고)",  "#C9A961", "REGISTERED"),
    ("출고 / 일정",   "#7B1FA2", "ON-LOAN"),
    ("회수 완료",    "#2E7D32", "RETURNED"),
]


@st.cache_data(ttl=600)
def _load_rentals():
    """더미 대여 데이터 (실제는 Notion 또는 별도 시트 연동 예정)"""
    today = datetime.now().date()
    rows = [
        {"ID":"R-026-01","고객":"카민디자인","품명":"FLOS IC T1 × 4","계약일":today-timedelta(days=20),"출고일":today-timedelta(days=14),"회수예정":today-timedelta(days=2),"단계":2,"금액":1_200_000,"담당자":"이혜지"},
        {"ID":"R-026-02","고객":"영화 제작팀 A","품명":"ARTEMIDE Tolomeo × 6","계약일":today-timedelta(days=15),"출고일":today-timedelta(days=10),"회수예정":today+timedelta(days=5),"단계":2,"금액":2_400_000,"담당자":"이혜지"},
        {"ID":"R-026-03","고객":"인플루언서 OO","품명":"LASVIT Never-ending","계약일":today-timedelta(days=8),"출고일":today-timedelta(days=5),"회수예정":today+timedelta(days=2),"단계":2,"금액":800_000,"담당자":"신정훈"},
        {"ID":"R-026-04","고객":"건축사무소 B","품명":"VIABIZZUNO N55 × 8","계약일":today-timedelta(days=3),"출고일":None,"회수예정":today+timedelta(days=20),"단계":1,"금액":3_200_000,"담당자":"서영완"},
        {"ID":"R-026-05","고객":"가구쇼룸 C","품명":"MARSET Ginger × 3","계약일":today-timedelta(days=1),"출고일":None,"회수예정":today+timedelta(days=14),"단계":0,"금액":900_000,"담당자":"이혜지"},
        {"ID":"R-026-06","고객":"드라마 촬영 D","품명":"FLOS Aplomb × 5","계약일":today-timedelta(days=45),"출고일":today-timedelta(days=40),"회수예정":today-timedelta(days=10),"단계":2,"금액":1_500_000,"담당자":"신정훈"},
        {"ID":"R-026-07","고객":"잡지 화보 E","품명":"INGO MAURER Zettel'z","계약일":today-timedelta(days=30),"출고일":today-timedelta(days=25),"회수예정":today-timedelta(days=20),"단계":3,"금액":600_000,"담당자":"이혜지"},
        {"ID":"R-026-08","고객":"카페 F","품명":"MARSET Dipping × 2","계약일":today-timedelta(days=25),"출고일":today-timedelta(days=20),"회수예정":today-timedelta(days=15),"단계":3,"금액":450_000,"담당자":"신정훈"},
    ]
    return pd.DataFrame(rows)


def render():
    greeting_header("이혜지", role="대여 4단계 진행 · 연체 모니터링",
                    page_title="🎬 대여")

    df = _load_rentals()
    if not len(df):
        st.error("대여 데이터 없음")
        return
    render_report_section("대여", df, period_col="계약일")

    today = pd.Timestamp(datetime.now().date())
    df["회수예정"] = pd.to_datetime(df["회수예정"])
    df["계약일"] = pd.to_datetime(df["계약일"])

    in_progress = df[df["단계"] < 3]
    overdue = df[(df["단계"] == 2) & (df["회수예정"] < today)]
    on_loan = df[df["단계"] == 2]
    total_amt = int(df["금액"].sum())

    # === KPI ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("진행 중 계약", f"{len(in_progress)}",
                                     f"전체 {len(df)}건 중", "neutral", "📑"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("출고 중 (ON-LOAN)", f"{len(on_loan)}",
                                     "현재 외부 출고된 자산",
                                     "gold", "🚚"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("연체 회수", f"{len(overdue)}",
                                     "회수예정 경과",
                                     "down" if len(overdue) else "neutral", "⚠"), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card("누계 매출", f"₩{total_amt:,}",
                                     f"건당 ₩{total_amt//max(len(df),1):,}",
                                     "gold", "💰"), unsafe_allow_html=True)

    # === 연체 알림 ===
    if len(overdue):
        names = ", ".join(overdue["고객"].head(3).tolist())
        st.markdown(alert_banner(
            f"⚠ {len(overdue)}건의 대여 자산이 회수 예정일을 초과했습니다",
            f"고객: {names}{'…' if len(overdue) > 3 else ''} — 즉시 연락 또는 회수 일정 갱신",
            level="red", icon="⏰",
        ), unsafe_allow_html=True)

    # === 4단계 카드 ===
    st.markdown(section_header("4단계 진행", "계약서 → 등록 → 출고 → 회수"),
                unsafe_allow_html=True)
    stage_counts = [int((df["단계"]==i).sum()) for i in range(4)]
    stage_cards = [
        {"label": f"① {STAGES[0][0]}", "value": f"{stage_counts[0]}",
         "sub": "계약서 작성 중", "color": STAGES[0][1], "trend":""},
        {"label": f"② {STAGES[1][0]}", "value": f"{stage_counts[1]}",
         "sub": "자산 등록 / 입고 대기", "color": STAGES[1][1], "trend":""},
        {"label": f"③ {STAGES[2][0]}", "value": f"{stage_counts[2]}",
         "sub": "출고 / 외부 일정 중", "color": STAGES[2][1], "trend":""},
    ]
    st.markdown(multi_card_row(stage_cards), unsafe_allow_html=True)
    # 4번째 카드 단독
    st.markdown(f"""
<div class="mc-item" style="border-top-color:{STAGES[3][1]};max-width:380px;margin-top:8px">
  <div class="mc-label" style="color:{STAGES[3][1]}">④ {STAGES[3][0]}</div>
  <div class="mc-value">{stage_counts[3]}</div>
  <div class="mc-sub">완료 / 종결된 계약</div>
</div>
""", unsafe_allow_html=True)

    # === 진행 리스트 + 연체 리스트 ===
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown(section_header("진행 중 계약", "출고/등록/계약 작성 단계"),
                    unsafe_allow_html=True)
        for i, row in enumerate(in_progress.sort_values("회수예정").itertuples(), 1):
            stage_label = STAGES[row.단계][2]
            stage_color = STAGES[row.단계][1]
            badge = status_badge_html(stage_label, color=stage_color)
            days = (row.회수예정 - today).days
            ret_str = f"D{days:+d}" if days != 0 else "오늘"
            st.markdown(leaderboard_row(
                rank=i, name=f"{row.고객} · {row.품명[:18]}",
                sub=f"{badge} · 계약 {row.계약일.strftime('%m/%d')} → 회수 {row.회수예정.strftime('%m/%d')} ({ret_str})",
                value=f"₩{int(row.금액):,}", value_label=row.담당자, color=stage_color,
            ), unsafe_allow_html=True)

    with col_r:
        st.markdown(section_header("연체 / 회수 대기", "회수예정 < 오늘"),
                    unsafe_allow_html=True)
        if len(overdue):
            for i, row in enumerate(overdue.sort_values("회수예정").itertuples(), 1):
                days_over = (today - row.회수예정).days
                st.markdown(leaderboard_row(
                    rank=i, name=f"{row.고객} · {row.품명[:18]}",
                    sub=f"⚠ {days_over}일 연체 · 출고 {row.출고일.strftime('%m/%d') if pd.notna(row.출고일) else '-'}",
                    value=f"₩{int(row.금액):,}", value_label="OVERDUE",
                    color="#D32F2F",
                ), unsafe_allow_html=True)
        else:
            st.success("✓ 연체 없음")

    # === 전체 테이블 ===
    with st.expander("📋 전체 대여 리스트"):
        show = df.copy()
        show["계약일"] = show["계약일"].dt.strftime("%Y-%m-%d")
        show["회수예정"] = show["회수예정"].dt.strftime("%Y-%m-%d")
        show["단계"] = show["단계"].map(lambda i: f"{i+1}. {STAGES[i][0]}")
        st.dataframe(show, hide_index=True, use_container_width=True)

    render_task_widget("대여")
