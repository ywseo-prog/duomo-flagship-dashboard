"""모듈 2: 업무일지 v1.0 — 디자인 토큰 분리 + 4종 행 추가 + session_state

[v1.0 스펙 변경]
- constants/design_tokens.py에서 컬러·옵션 import
- STATUSES 4종 (done/ing/결제 완료/to do) — 단순화
- CHANNELS 2종 (내방/유선), CATEGORIES 2종 (소비자/업체)
- PERSONS 4인 (직책 포함, 시트 호환)
- 행 추가 버튼 4종 (내방·소비자 / 내방·업체 / 유선·소비자 / 유선·업체)
- session_state로 편집 보존 (rerun 시 초기화 방지)
- cellClassRules + GRID_CSS로 라운드 배지

[데이터]
parsers.load_worklog_v2() → dict → flatten_for_aggrid() → 평면 DataFrame
services.sheets_sync.push_changes() → 본사 시트 batch_update
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
    load_worklog_df, load_worklog_v2, flatten_for_aggrid,
    aggregate_monthly, aggregate_by_person, aggregate_by_brand,
    aggregate_by_customer, load_monthly_target, load_visitor_trend,
)
from services.sheets_sync import (
    has_service_account, push_changes, append_row,
    SHEET_ID, WORKLOG_TAB,
)
from constants import (
    COLORS, PERSONS, STATUSES, CHANNELS, CATEGORIES, GRID_CSS,
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)

VIP_THRESHOLD = 3_000_000


def render():
    # CSS 토큰 inject (그리드 진입 전)
    st.markdown(GRID_CSS, unsafe_allow_html=True)

    greeting_header(
        "서영완", role="조명플래그십파트 · 업무일지 v1.0 (디자인 토큰)",
        page_title="📊 업무일지",
    )

    parsed = load_worklog_v2(source="auto")
    if not parsed.get("dates"):
        st.error("본사 시트 로드 실패 또는 데이터 없음")
        return
    df_all = load_worklog_df(source="auto")
    if not len(df_all):
        st.error("DataFrame 변환 실패")
        return
    df_all = df_all.copy()
    target = load_monthly_target()

    # === 1. 상단 KPI ===
    _render_compact_kpi(df_all, parsed.get("header") or {}, target)

    # === 2. 뷰 토글 ===
    view = st.radio(
        "뷰", ["📅 일별 (시트 편집)", "🗓 월별 분석", "📆 연별 분석"],
        horizontal=True, label_visibility="collapsed", key="wl_view",
    )

    # === 3. 검색·필터 ===
    f = _render_search_bar(df_all)

    if view == "📅 일별 (시트 편집)":
        _render_grid_view(parsed, f)
    elif view == "🗓 월별 분석":
        _render_monthly_view(f, target)
    else:
        _render_yearly_view(f)

    render_task_widget("업무일지")


# ============================================================
# KPI 1줄
# ============================================================
def _render_compact_kpi(df: pd.DataFrame, header: dict, target: dict | None):
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    paid_month = month_df[month_df["amount"] > 0]
    cur_sales = int(paid_month["amount"].sum())
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = cur_sales // max(active_days, 1) if active_days else 0
    target_val = header.get("month_target") or (target.get("target") if target else None)
    sheet_total = header.get("current_total")
    rate = (header.get("achievement") * 100) if header.get("achievement") else \
           (cur_sales / target_val * 100 if target_val else None)

    cols = st.columns(4)
    with cols[0]:
        if target_val:
            st.markdown(black_kpi_card(
                f"{today.month}월 목표", f"₩{target_val/1e8:.2f}억",
                "본사 시트 헤더", "gold", "🎯",
            ), unsafe_allow_html=True)
        else:
            st.markdown(black_kpi_card("목표", "—", "미입력", "neutral", "🎯"),
                        unsafe_allow_html=True)
    with cols[1]:
        show_val = sheet_total if sheet_total else cur_sales
        sub = "본사 시트 헤더" if sheet_total else "산정"
        st.markdown(black_kpi_card(
            "금일 누계 매출", f"₩{show_val/1e8:.2f}억",
            f"{sub} · {len(paid_month)}건", "gold", "💰",
        ), unsafe_allow_html=True)
    with cols[2]:
        if rate is not None:
            days_in_month = monthrange(today.year, today.month)[1]
            pace = today.day / days_in_month * 100
            trend = "up" if rate >= pace else "down"
            st.markdown(black_kpi_card(
                "달성률", f"{rate:.1f}%",
                f"진척 {pace:.0f}%", trend, "📊",
            ), unsafe_allow_html=True)
        else:
            st.markdown(black_kpi_card("달성률", "—", "목표 미입력", "neutral", "📊"),
                        unsafe_allow_html=True)
    with cols[3]:
        st.markdown(black_kpi_card(
            "이번달 일평균", f"₩{daily_avg/1e6:.1f}M",
            f"활성 {active_days}일", "gold", "📈",
        ), unsafe_allow_html=True)


# ============================================================
# 검색·필터
# ============================================================
def _render_search_bar(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    today = date.today()
    sc1, sc2, sc3 = st.columns([4, 2, 2])
    search = sc1.text_input(
        "🔍 검색", placeholder="고객·내용·연락처·담당자·브랜드",
        key="wl_search", label_visibility="collapsed",
    )
    period = sc2.selectbox(
        "기간", ["오늘", "어제", "최근 7일", "최근 30일", "이번달", "전체"],
        index=2, key="wl_period",
    )
    person_opts = sorted(set(p for ps in df["persons"] for p in ps if p))
    per_f = sc3.multiselect(
        "👤 담당자", person_opts, default=[], key="wl_per",
        placeholder="전체",
    )

    if period == "오늘":
        f = f[f["date"].dt.date == today]
    elif period == "어제":
        f = f[f["date"].dt.date == today - timedelta(days=1)]
    elif period == "최근 7일":
        f = f[f["date"].dt.date >= today - timedelta(days=7)]
    elif period == "최근 30일":
        f = f[f["date"].dt.date >= today - timedelta(days=30)]
    elif period == "이번달":
        f = f[f["ym"] == f"{today.year}-{today.month:02d}"]

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
    return f


# ============================================================
# AG-Grid 메인 뷰 (v1.0 토큰 + 4종 행 추가)
# ============================================================
def _render_grid_view(parsed: dict, f: pd.DataFrame):
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
        from components import (
            DATE_HEADER_RENDERER, CHANNEL_BADGE, CATEGORY_BADGE,
            STATUS_CLASS_RULES, AMOUNT_FORMATTER, AMOUNT_CELL_STYLE,
            ROW_STYLE, PERSON_BADGE,
        )
    except ImportError as e:
        st.error(f"**streamlit-aggrid 또는 components 미설치/오류**: {e}")
        st.caption("requirements.txt push 시 자동 설치됩니다. fallback 표:")
        _render_fallback_table(f)
        return

    if not len(f):
        st.info("검색·필터 결과 0건")
        return

    sa_active = has_service_account()
    if sa_active:
        st.caption("✓ Service Account 활성 — 💾 저장 시 본사 시트 자동 동기화")
    else:
        st.caption("⚠ Service Account 미설정 — 그리드 편집은 가능, 시트 push 비활성")

    # === Flatten ===
    filter_rows = set(f["_sheet_row"].tolist()) if "_sheet_row" in f.columns else None
    grid_df = flatten_for_aggrid(parsed, filter_rows)
    if not len(grid_df):
        st.info("표시할 데이터 없음")
        return

    # === session_state로 편집 보존 ===
    state_key = "wl_grid_df"
    # 새 데이터 로드 시 session_state 동기화 (filter/period 변경 감지)
    cache_key = f"{len(grid_df)}_{grid_df['_sheet_row'].sum() if len(grid_df) else 0}"
    if st.session_state.get("wl_grid_cache_key") != cache_key:
        st.session_state[state_key] = grid_df.copy()
        st.session_state["wl_grid_cache_key"] = cache_key
    # 신규 행이 추가됐다면 보존
    work_df = st.session_state.get(state_key, grid_df).copy()

    # === GridOptionsBuilder ===
    gb = GridOptionsBuilder.from_dataframe(work_df)
    gb.configure_default_column(
        editable=True, resizable=True, sortable=True, filter=True,
        wrapText=True, minWidth=80,
    )
    gb.configure_column("_sheet_row", hide=True, editable=False)
    gb.configure_column("_meta", hide=True, editable=False)
    gb.configure_column("row_type", hide=True, editable=False)

    # 3-level rowGroup
    gb.configure_column("date", rowGroup=True, hide=True, editable=False, rowGroupIndex=0)
    gb.configure_column(
        "channel", rowGroup=True, hide=True, rowGroupIndex=1,
        cellRenderer=CHANNEL_BADGE,
    )
    gb.configure_column(
        "category", rowGroup=True, hide=True, rowGroupIndex=2,
        cellRenderer=CATEGORY_BADGE,
    )

    # 편집 컬럼
    gb.configure_column(
        "status", editable=True, width=110,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": STATUSES + ["📝 진행사항", "⚠ 이슈사항"]},
        cellClassRules=STATUS_CLASS_RULES,
        headerName="현황",
    )
    gb.configure_column("customer", editable=True, width=200, headerName="고객")
    gb.configure_column("phone", editable=True, width=130, headerName="연락처")
    gb.configure_column(
        "content", editable=True, flex=1, wrapText=True, autoHeight=True,
        headerName="내용", minWidth=300,
    )
    gb.configure_column(
        "person", editable=True, width=140,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": PERSONS},
        cellRenderer=PERSON_BADGE,
        headerName="담당자",
    )
    gb.configure_column(
        "amount", editable=True, width=130, type=["numericColumn"],
        cellStyle=AMOUNT_CELL_STYLE, valueFormatter=AMOUNT_FORMATTER,
        headerName="매출",
    )

    # 그룹 디스플레이 + 행 스타일
    gb.configure_grid_options(
        groupDisplayType="groupRows",
        groupRowRendererParams={
            "innerRenderer": DATE_HEADER_RENDERER,
            "suppressCount": True,
        },
        groupDefaultExpanded=1,
        getRowStyle=ROW_STYLE,
        rowHeight=38,
        animateRows=True,
        enableRangeSelection=True,
        enableFillHandle=True,
    )

    grid_options = gb.build()

    # === 액션 바 + 행 추가 4종 ===
    st.markdown("##### 행 추가 (4종)")
    bc1, bc2, bc3, bc4, bc5 = st.columns([1, 1, 1, 1, 2])
    if bc1.button("➕ 내방·소비자", use_container_width=True, key="add_nb_so"):
        _add_row_session(state_key, "내방", "소비자")
    if bc2.button("➕ 내방·업체", use_container_width=True, key="add_nb_up"):
        _add_row_session(state_key, "내방", "업체")
    if bc3.button("➕ 유선·소비자", use_container_width=True, key="add_yu_so"):
        _add_row_session(state_key, "유선", "소비자")
    if bc4.button("➕ 유선·업체", use_container_width=True, key="add_yu_up"):
        _add_row_session(state_key, "유선", "업체")
    if bc5.button("🔄 시트에서 재로드 (편집 폐기)", use_container_width=True, key="wl_reload"):
        st.cache_data.clear()
        st.session_state.pop(state_key, None)
        st.session_state.pop("wl_grid_cache_key", None)
        st.rerun()

    # 저장 버튼
    sav_c1, sav_c2 = st.columns([3, 1])
    sav_c1.caption(f"📂 record {(work_df['row_type']=='record').sum()}건 + 진행 {(work_df['row_type']=='progress').sum()} + 이슈 {(work_df['row_type']=='issue').sum()} · 더블클릭으로 셀 편집")
    if sav_c2.button("💾 변경 저장", type="primary", use_container_width=True, key="wl_save"):
        st.session_state["wl_save_trigger"] = True

    # === AG-Grid 렌더 ===
    grid_response = AgGrid(
        work_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=False,
        theme="streamlit",
        height=620,
        allow_unsafe_jscode=True,
        reload_data=False,
        key=f"wl_grid_{cache_key}",
    )

    # 편집된 상태를 session_state에 즉시 반영
    edited_df = pd.DataFrame(grid_response.get("data") or [])
    if len(edited_df):
        st.session_state[state_key] = edited_df

    # === 변경 감지 + push ===
    if st.session_state.get("wl_save_trigger"):
        if "row_type" in edited_df.columns:
            edited_records = edited_df[edited_df["row_type"] == "record"]
        else:
            edited_records = edited_df
        orig_records = grid_df[grid_df["row_type"] == "record"].copy()
        changes = _detect_changes(orig_records, edited_records)
        new_rows = edited_records[edited_records["_sheet_row"] == -1]  # 신규 추가된 행

        if not changes and not len(new_rows):
            st.toast("변경 사항 없음", icon="ℹ")
        elif sa_active:
            # 1. 기존 행 update
            if changes:
                with st.spinner(f"본사 시트에 {len(changes)}개 셀 push 중..."):
                    result = push_changes(changes)
                if result["ok"]:
                    st.toast(f"✓ {result['updated']}개 셀 저장됨", icon="✅")
                else:
                    st.error(f"저장 실패: {result.get('error')}")
            # 2. 신규 행 append
            for _, r in new_rows.iterrows():
                if not str(r.get("customer", "")).strip():
                    continue
                record = {
                    "channel": r.get("channel", ""),
                    "category": r.get("category", ""),
                    "status": r.get("status", ""),
                    "customer": r.get("customer", ""),
                    "phone": r.get("phone", ""),
                    "content": r.get("content", ""),
                    "person": r.get("person", ""),
                    "amount": int(r.get("amount") or 0),
                }
                d_str = r.get("date", date.today().isoformat())
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                with st.spinner(f"신규 행 append..."):
                    result = append_row(record, d_obj)
                if result["ok"]:
                    st.toast(f"✓ 신규 행 {result['row']} 추가", icon="✅")
            st.cache_data.clear()
            st.session_state.pop("wl_grid_cache_key", None)
        else:
            st.warning(f"Service Account 미설정 — 변경 {len(changes)}건 + 신규 {len(new_rows)}건 push 보류")
            if changes:
                st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
            if len(new_rows):
                st.caption("📋 신규 행 (수동 시트 추가):")
                st.dataframe(new_rows[["date","channel","category","status","customer","content","person","amount"]],
                              hide_index=True, use_container_width=True)
        st.session_state["wl_save_trigger"] = False


def _add_row_session(state_key: str, channel: str, category: str):
    """session_state DataFrame에 빈 신규 행 추가 (_sheet_row = -1)"""
    df = st.session_state.get(state_key, pd.DataFrame())
    new_row = {
        "row_type": "record",
        "date": date.today().isoformat(),
        "_sheet_row": -1,  # 신규 표시
        "_meta": {},
        "channel": channel, "category": category,
        "status": "to do",
        "customer": "", "phone": "", "content": "",
        "person": "", "amount": 0,
    }
    # 첫 행에 추가 (위쪽)
    new_df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
    st.session_state[state_key] = new_df
    st.toast(f"➕ {channel}·{category} 행 추가 (행 채우고 💾 저장)", icon="➕")
    st.rerun()


def _detect_changes(orig: pd.DataFrame, edited: pd.DataFrame) -> list[dict]:
    """orig vs edited diff → [{row, field, value}]. _sheet_row가 -1인 신규 행은 별도 처리(append)."""
    changes = []
    field_map = {
        "channel": "channel", "category": "category", "status": "status",
        "customer": "customer", "phone": "phone", "content": "content",
        "person": "person", "amount": "amount",
    }
    if "_sheet_row" not in orig.columns or "_sheet_row" not in edited.columns:
        return changes
    orig_idx = orig.set_index("_sheet_row")
    edited_idx = edited.set_index("_sheet_row")
    for sheet_row in edited_idx.index:
        if sheet_row == -1 or sheet_row not in orig_idx.index:
            continue
        for col, field in field_map.items():
            if col not in edited_idx.columns or col not in orig_idx.columns:
                continue
            orig_v = orig_idx.loc[sheet_row, col]
            new_v = edited_idx.loc[sheet_row, col]
            if field == "amount":
                try:
                    orig_n = int(orig_v) if orig_v not in ("", None) else 0
                    new_n = int(float(new_v)) if new_v not in ("", None) else 0
                    if orig_n != new_n:
                        changes.append({"row": int(sheet_row), "field": field,
                                       "value": new_n if new_n else ""})
                except (ValueError, TypeError):
                    pass
            else:
                if str(orig_v or "").strip() != str(new_v or "").strip():
                    changes.append({"row": int(sheet_row), "field": field,
                                   "value": str(new_v or "").strip()})
    return changes


def _render_fallback_table(f: pd.DataFrame):
    if not len(f):
        return
    show = f.copy()
    show["일자"] = show["date"].dt.strftime("%Y.%m.%d")
    show["매출"] = show["amount"].apply(lambda v: f"₩{int(v):,}" if v else "—")
    show = show[["일자", "channel", "category", "status", "customer",
                  "phone", "content", "person_raw", "매출"]]
    show.columns = ["일자", "채널", "카테고리", "현황", "고객", "연락처", "내용", "담당자", "매출"]
    st.dataframe(show, hide_index=True, use_container_width=True, height=500)


# ============================================================
# 월별 / 연별 분석 (간소화)
# ============================================================
def _render_monthly_view(f: pd.DataFrame, target: dict | None):
    avail = sorted(f["ym"].unique(), reverse=True)
    if not avail:
        st.info("월별 데이터 없음")
        return
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    default = cur_ym if cur_ym in avail else avail[0]
    sel_ym = st.selectbox("🗓 월", avail, index=avail.index(default), key="wl_m_ym")
    month_df = f[f["ym"] == sel_ym]
    paid = month_df[month_df["amount"] > 0]
    total = int(paid["amount"].sum())
    deals = len(paid)

    monthly_agg = aggregate_monthly(f)
    mom = 0
    if sel_ym in monthly_agg["ym"].values:
        cur_idx = monthly_agg[monthly_agg["ym"] == sel_ym].index[0]
        if cur_idx > 0:
            prev_sales = int(monthly_agg.loc[cur_idx - 1, "sales"])
            mom = (total - prev_sales) / max(prev_sales, 1) * 100 if prev_sales else 0

    cols = st.columns(4)
    cols[0].metric("매출", f"₩{total:,}")
    cols[1].metric("결제", f"{deals}건")
    cols[2].metric("MoM", f"{mom:+.1f}%")
    cols[3].metric("객단가", f"₩{total//max(deals,1):,}")

    if len(paid):
        daily = paid.groupby(paid["date"].dt.date)["amount"].sum().reset_index()
        daily.columns = ["date", "amount"]
        fig = go.Figure(go.Bar(
            x=daily["date"], y=daily["amount"], marker_color="#C9A961",
            text=[f"₩{int(v/1e6):,}M" if v >= 1e6 else "" for v in daily["amount"]],
            textposition="outside",
        ))
        fig.update_layout(height=320, margin=dict(t=30,b=20,l=20,r=20),
                          plot_bgcolor="#fff", paper_bgcolor="#fff", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    by_p = aggregate_by_person(month_df).head(8)
    if len(by_p):
        st.markdown(section_header(f"{sel_ym} 담당자 리더보드"), unsafe_allow_html=True)
        for i, row in enumerate(by_p.itertuples(), 1):
            color = "#C9A961" if i == 1 else "#0A0A0A" if i <= 3 else "#999"
            st.markdown(leaderboard_row(
                rank=i, name=row.persons,
                sub=f"상담 {row.consult_count} · 결제 {row.paid_count}",
                value=f"₩{int(row.sales):,}", value_label="SALES", color=color,
            ), unsafe_allow_html=True)


def _render_yearly_view(f: pd.DataFrame):
    f = f.copy()
    f["year"] = f["date"].dt.year
    avail = sorted(f["year"].dropna().unique(), reverse=True)
    if not avail:
        return
    sel_year = st.selectbox("📆 연도", avail, index=0, key="wl_y_year")
    year_df = f[f["year"] == sel_year]
    paid = year_df[year_df["amount"] > 0]
    total = int(paid["amount"].sum())
    cols = st.columns(3)
    cols[0].metric("연 누계", f"₩{total/1e8:.2f}억")
    cols[1].metric("결제", f"{len(paid)}건")
    vip = paid[paid["amount"] >= VIP_THRESHOLD]
    cols[2].metric("VIP", f"₩{int(vip['amount'].sum())/1e8:.2f}억")

    m_agg = paid.groupby("ym").agg(sales=("amount","sum")).reset_index().sort_values("ym")
    if len(m_agg):
        fig = px.line(m_agg, x="ym", y="sales", markers=True,
                      color_discrete_sequence=["#C9A961"])
        fig.update_layout(height=280, plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(section_header(f"{sel_year}년 LTV Top 10"), unsafe_allow_html=True)
    ltv = aggregate_by_customer(paid).sort_values("sales", ascending=False).head(10)
    for i, row in enumerate(ltv.itertuples(), 1):
        color = ["#C9A961", "#0A0A0A", "#0A0A0A"][i-1] if i <= 3 else "#999"
        st.markdown(leaderboard_row(
            rank=i, name=(row.customer or "—")[:25],
            sub=f"{row.visits}건 · 최근 {row.last_visit.strftime('%m/%d') if pd.notna(row.last_visit) else '—'}",
            value=f"₩{int(row.sales):,}", value_label="LIFETIME", color=color,
        ), unsafe_allow_html=True)
