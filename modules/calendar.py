"""모듈 1: 팀 캘린더 (HEALTHIST 좌캘린더 + 우타임라인 + Notion 양방향)"""
import streamlit as st
import pandas as pd
import calendar as cal
from datetime import datetime, date, timedelta
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, status_badge_html, alert_banner,
)
from utils.notion_client import (
    fetch_calendar_events, create_calendar_event,
    CATEGORY_COLORS,
)


def render():
    greeting_header("서영완", role="팀 캘린더 · HEALTHIST 시안 차용",
                    page_title="🗓 팀 캘린더")

    df = fetch_calendar_events()
    if not len(df):
        st.info("캘린더 이벤트 없음 — Notion 연결 또는 신규 이벤트 추가 시 표시됩니다.")
        df = pd.DataFrame(columns=["이름","분류","담당자","날짜","date","메모"])

    today = datetime.now().date()
    # 월 선택
    cur_year = today.year; cur_month = today.month

    tcol1, tcol2, tcol3 = st.columns([1,1,3])
    sel_year = tcol1.selectbox("연도", list(range(cur_year-1, cur_year+2)),
                               index=1, key="cal_year")
    sel_month = tcol2.selectbox("월", list(range(1,13)),
                                index=cur_month-1, key="cal_month")
    view_mode = tcol3.radio("표시", ["월간","주간"], horizontal=True, key="cal_view")

    # === KPI ===
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    month_start = pd.Timestamp(date(sel_year, sel_month, 1))
    next_month = (month_start + pd.offsets.MonthBegin(1))
    month_df = df[(df["date"] >= month_start) & (df["date"] < next_month)] if len(df) else df
    today_df = df[df["date"].dt.date == today] if len(df) else df
    upcoming_7 = df[df["date"].between(pd.Timestamp(today), pd.Timestamp(today + timedelta(days=7)))] if len(df) else df
    urgent = month_df[month_df["분류"].isin(["발주마감","VIP컨설팅"])] if len(month_df) else month_df

    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("당월 이벤트", f"{len(month_df)}",
                                     f"{sel_year}.{sel_month:02d}",
                                     "neutral", "🗓"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("오늘 일정", f"{len(today_df)}",
                                     today.strftime("%Y.%m.%d"),
                                     "gold", "☀"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("7일 이내", f"{len(upcoming_7)}",
                                     "다가오는 일정", "neutral", "📍"), unsafe_allow_html=True)
    cols[3].markdown(black_kpi_card("우선 일정", f"{len(urgent)}",
                                     "발주마감 / VIP컨설팅",
                                     "down" if len(urgent) else "neutral", "⚠"), unsafe_allow_html=True)

    # === 좌측 캘린더 + 우측 타임라인 ===
    col_cal, col_tl = st.columns([2, 1])

    with col_cal:
        st.markdown(section_header(f"{sel_year}.{sel_month:02d} 월간 캘린더",
                                    "분류별 컬러바"), unsafe_allow_html=True)
        st.markdown(_render_calendar_grid(sel_year, sel_month, month_df, today),
                    unsafe_allow_html=True)

    with col_tl:
        st.markdown(section_header("Today's Timeline", today.strftime("%Y.%m.%d")),
                    unsafe_allow_html=True)
        if len(today_df):
            for r in today_df.sort_values("date").itertuples():
                cat = getattr(r, '분류', '') or '기타'
                color = CATEGORY_COLORS.get(cat, "#607D8B")
                time_str = ""
                if pd.notna(r.date):
                    time_str = r.date.strftime("%H:%M") if r.date.hour or r.date.minute else "종일"
                st.markdown(f"""
<div class="tl-item">
  <div class="tl-bar" style="background:{color}"></div>
  <div class="tl-time">{time_str}</div>
  <div class="tl-body">
    <div class="tl-title">{getattr(r, '이름', '-')}</div>
    <div class="tl-meta">{cat} · {getattr(r, '담당자', '-') or '-'}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.caption("오늘 일정 없음")

        st.markdown(section_header("Next 7 Days", ""), unsafe_allow_html=True)
        if len(upcoming_7):
            for r in upcoming_7.sort_values("date").head(8).itertuples():
                cat = getattr(r, '분류', '') or '기타'
                color = CATEGORY_COLORS.get(cat, "#607D8B")
                dt_str = r.date.strftime("%m/%d %a") if pd.notna(r.date) else ""
                badge = status_badge_html(cat, color=color)
                st.markdown(f"""
<div class="tl-item">
  <div class="tl-bar" style="background:{color}"></div>
  <div class="tl-time">{dt_str}</div>
  <div class="tl-body">
    <div class="tl-title">{getattr(r, '이름', '-')}</div>
    <div class="tl-meta">{badge} · {getattr(r, '담당자', '-') or '-'}</div>
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.caption("일정 없음")

    # === 신규 이벤트 추가 ===
    st.markdown(section_header("➕ 이벤트 추가", "Notion DB 양방향 (캘린더 또는 주작업)"),
                unsafe_allow_html=True)
    with st.form("new_event"):
        c1, c2, c3 = st.columns([3, 2, 2])
        title = c1.text_input("제목")
        ev_date = c2.date_input("날짜", today)
        category = c3.selectbox("분류", list(CATEGORY_COLORS.keys()))
        c4, c5 = st.columns([2, 4])
        person = c4.text_input("담당자")
        note = c5.text_input("메모")
        submitted = st.form_submit_button("Notion에 저장", type="primary")
        if submitted:
            if not title:
                st.error("제목을 입력하세요")
            else:
                res = create_calendar_event(
                    title=title, date_str=str(ev_date),
                    category=category, person=person, note=note,
                )
                if res:
                    st.success(f"✓ '{title}' 저장됨")
                    st.cache_data.clear()
                    st.rerun()

    # === 분류별 통계 ===
    st.markdown(section_header("당월 분류별 분포", ""), unsafe_allow_html=True)
    if len(month_df) and "분류" in month_df.columns:
        by_cat = month_df.groupby("분류").size().reset_index(name="건수")
        cards = []
        for i, row in enumerate(by_cat.head(3).itertuples()):
            color = CATEGORY_COLORS.get(row.분류, "#607D8B")
            cards.append({
                "label": row.분류, "value": f"{row.건수}",
                "sub": f"{sel_year}.{sel_month:02d}", "color": color, "trend":"",
            })
        while len(cards) < 3:
            cards.append({"label":"—","value":"—","sub":"","color":"#E8E8E8","trend":""})
        st.markdown(multi_card_row(cards), unsafe_allow_html=True)

    render_task_widget("캘린더")


def _render_calendar_grid(year: int, month: int, events_df: pd.DataFrame, today: date) -> str:
    """월간 캘린더 그리드 HTML 생성 (HEALTHIST 시안 차용)"""
    cal_obj = cal.Calendar(firstweekday=0)
    month_days = cal_obj.monthdayscalendar(year, month)

    # 날짜별 이벤트 그룹화
    ev_by_day = {}
    if len(events_df):
        for r in events_df.itertuples():
            if pd.notna(r.date):
                d = r.date.date()
                if d.year == year and d.month == month:
                    ev_by_day.setdefault(d.day, []).append({
                        "title": getattr(r, '이름', '-'),
                        "cat": getattr(r, '분류', '기타'),
                        "color": CATEGORY_COLORS.get(getattr(r, '분류', '기타'), "#607D8B"),
                    })

    html = """
<style>
.dm-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
           background: #fff; border: 1px solid var(--border); border-radius: 12px;
           padding: 10px; box-shadow: var(--shadow); }
.dm-head { font-family: 'Inter',sans-serif; font-size: 11px; font-weight: 700;
           text-align: center; padding: 6px 0; color: #555;
           letter-spacing: 0.6px; text-transform: uppercase; }
.dm-head.sun { color: #D32F2F; }
.dm-head.sat { color: #1976D2; }
.dm-cell { background: #FAFAFA; border-radius: 6px; min-height: 76px;
           padding: 4px 6px; font-size: 11px; }
.dm-cell.empty { background: transparent; }
.dm-cell.today { background: #0A0A0A; color: #fff; }
.dm-cell .dm-day { font-family: 'Inter',sans-serif; font-weight: 700; font-size: 12px;
                   color: #0A0A0A; margin-bottom: 2px; }
.dm-cell.today .dm-day { color: #fff; }
.dm-cell .dm-ev { font-size: 10px; padding: 1px 4px; border-radius: 3px;
                  margin-bottom: 1px; color: #fff; white-space: nowrap;
                  overflow: hidden; text-overflow: ellipsis; }
.dm-cell .dm-more { font-size: 9px; color: #999; }
</style>
<div class="dm-grid">
"""
    weekdays = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    for i, wd in enumerate(weekdays):
        cls = "sun" if i == 6 else ("sat" if i == 5 else "")
        html += f'<div class="dm-head {cls}">{wd}</div>'

    for week in month_days:
        for day in week:
            if day == 0:
                html += '<div class="dm-cell empty"></div>'
            else:
                is_today = (day == today.day and month == today.month and year == today.year)
                cls = "today" if is_today else ""
                evs = ev_by_day.get(day, [])
                cell = f'<div class="dm-cell {cls}"><div class="dm-day">{day}</div>'
                for ev in evs[:2]:
                    cell += f'<div class="dm-ev" style="background:{ev["color"]}" title="{ev["title"]}">{ev["title"][:9]}</div>'
                if len(evs) > 2:
                    cell += f'<div class="dm-more">+{len(evs)-2} more</div>'
                cell += "</div>"
                html += cell
    html += "</div>"
    return html
