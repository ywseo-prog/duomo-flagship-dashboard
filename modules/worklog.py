"""모듈 2: 업무일지 v0.9 — 5-RowType parser + AG-Grid 3-level rowGroup

[원본 5-Row-Type]
① DATE_HEADER   날짜+담당자+내방팀수
② CATEGORY_META "카테고리" 라벨 + 일자 총매출 (J열)
③ RECORD        상담 레코드
④ PROGRESS      진행사항
⑤ ISSUE         이슈사항

[UI]
- AG-Grid 3-level rowGroup (date → channel → category)
- DATE_HEADER 그룹 헤더 컴포넌트 (담당자/내방팀수/결제금액)
- 진행/이슈 행: row_type 컬러 배경
- 셀 더블클릭 편집 + 변경 감지 → services/sheets_sync.push_changes

데이터: parsers.load_worklog_v2() → dict
저장:  services.sheets_sync.push_changes() → gspread batch_update
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
    load_worklog_df, load_worklog_v2,
    aggregate_monthly, aggregate_by_person, aggregate_by_brand,
    aggregate_by_customer, load_monthly_target, load_visitor_trend,
    CHANNEL_OPTIONS, CATEGORY_OPTIONS, STATUS_OPTIONS,
)
from services.sheets_sync import (
    has_service_account, push_changes, append_row,
    SHEET_ID, WORKLOG_TAB,
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)

VIP_THRESHOLD = 3_000_000


def render():
    greeting_header(
        "서영완", role="조명플래그십파트 · 업무일지 (5-RowType + AG-Grid)",
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

    # === 1. 상단 1줄 KPI 4 ===
    _render_compact_kpi(df_all, parsed.get("header") or {}, target)

    # === 2. 뷰 토글 ===
    view = st.radio(
        "뷰", ["📅 일별 (시트 편집)", "🗓 월별 분석", "📆 연별 분석"],
        horizontal=True, label_visibility="collapsed", key="wl_view",
    )

    # === 3. 검색·필터 (한 줄) ===
    f = _render_search_bar(df_all)

    if view == "📅 일별 (시트 편집)":
        _render_grid_view(parsed, f)
    elif view == "🗓 월별 분석":
        _render_monthly_view(f, target)
    else:
        _render_yearly_view(f)

    render_task_widget("업무일지")


# ============================================================
# KPI 4 (compact, 1줄)
# ============================================================
def _render_compact_kpi(df: pd.DataFrame, header: dict, target: dict | None):
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    paid_month = month_df[month_df["amount"] > 0]
    cur_sales = int(paid_month["amount"].sum())
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = cur_sales // max(active_days, 1) if active_days else 0
    # 시트 헤더 직접값 우선
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
        # 시트 헤더 vs 산정값 비교
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
            conv = len(paid_month) / max(len(month_df), 1) * 100
            st.markdown(black_kpi_card(
                "전환률", f"{conv:.1f}%", "결제/상담", "neutral", "📊",
            ), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(black_kpi_card(
            "이번달 일평균", f"₩{daily_avg/1e6:.1f}M",
            f"활성 {active_days}일", "gold", "📈",
        ), unsafe_allow_html=True)


# ============================================================
# 검색·필터 (한 줄, 항상 노출)
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
# Flatten v2 dict → AG-Grid 평면 DataFrame
# ============================================================
def flatten_for_aggrid(parsed: dict, filter_df: pd.DataFrame) -> pd.DataFrame:
    """v2 dict + 필터된 df의 sheet_row 교집합 → 평면 DataFrame.

    row_type 컬럼 포함:
    - 'record'   : 일반 상담 행
    - 'progress' : 진행사항
    - 'issue'    : 이슈사항
    DATE_HEADER는 AG-Grid의 rowGroup이 자동 생성하므로 별도 행 미포함.
    """
    filter_rows = set(filter_df["_sheet_row"].tolist()) if "_sheet_row" in filter_df.columns else None
    rows = []
    for d in parsed.get("dates", []):
        # 해당 일자의 records가 필터에 하나라도 있어야 그 블록 표시
        date_records = d.get("records", [])
        if filter_rows is not None:
            date_records = [r for r in date_records if r["_sheet_row"] in filter_rows]
        if not date_records:
            continue
        meta = d.get("meta", {})
        for r in date_records:
            rows.append({
                "row_type": "record",
                "date": d["date"],
                "_sheet_row": r["_sheet_row"],
                "_meta": meta,  # 그룹 헤더 렌더러용
                "channel": r.get("channel") or "",
                "category": r.get("category") or "",
                "status": r.get("status") or "",
                "customer": r.get("customer") or "",
                "phone": r.get("phone") or "",
                "content": r.get("content") or "",
                "person_raw": r.get("person_raw") or "",
                "amount": int(r.get("amount") or 0),
            })
        # 진행/이슈는 필터 결과와 무관하게 같은 블록이 보일 때만
        for p in d.get("progress", []):
            rows.append({
                "row_type": "progress", "date": d["date"], "_meta": meta,
                "channel": "", "category": "", "status": "📝 진행사항",
                "customer": "", "phone": "", "content": p,
                "person_raw": "", "amount": 0, "_sheet_row": -1,
            })
        for i in d.get("issues", []):
            rows.append({
                "row_type": "issue", "date": d["date"], "_meta": meta,
                "channel": "", "category": "", "status": "⚠ 이슈사항",
                "customer": "", "phone": "", "content": i,
                "person_raw": "", "amount": 0, "_sheet_row": -1,
            })
    df = pd.DataFrame(rows)
    # 같은 블록 내 channel/category forward-fill (셀 병합 효과)
    if len(df):
        # record 행만 ffill (progress/issue는 빈 채로)
        rec_mask = df["row_type"] == "record"
        for col in ["channel", "category"]:
            df.loc[rec_mask, col] = (
                df[rec_mask].groupby("date")[col]
                .transform(lambda s: s.replace("", pd.NA).ffill().fillna(""))
            )
    return df


# ============================================================
# AG-Grid 메인 뷰
# ============================================================
def _render_grid_view(parsed: dict, f: pd.DataFrame):
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
        from components import (
            DATE_HEADER_RENDERER, CHANNEL_BADGE, CATEGORY_BADGE,
            STATUS_CELL_STYLE, AMOUNT_FORMATTER, AMOUNT_STYLE,
            ROW_TYPE_STYLE, PERSON_BADGE,
        )
    except ImportError as e:
        st.error(f"**streamlit-aggrid 또는 components 미설치/오류**: {e}")
        st.caption("Streamlit Cloud는 requirements.txt push 시 자동 설치됩니다. fallback 표 모드:")
        _render_fallback_table(f)
        return

    if not len(f):
        st.info("검색·필터 결과 0건")
        return

    # Service Account 상태 안내
    sa_active = has_service_account()
    if sa_active:
        st.caption("✓ Google Service Account 활성 — 셀 편집 후 💾 저장 시 본사 시트 자동 동기화")
    else:
        st.caption("⚠ Service Account 미설정 — 그리드 편집은 가능하나 시트 push 비활성")

    # Flatten
    grid_df = flatten_for_aggrid(parsed, f)
    if not len(grid_df):
        st.info("표시할 데이터 없음")
        return

    # 컬럼명 한글화
    grid_df = grid_df.rename(columns={
        "channel": "채널", "category": "카테고리", "status": "현황",
        "customer": "고객", "phone": "연락처", "content": "내용",
        "person_raw": "담당자", "amount": "매출",
    })

    # === GridOptionsBuilder ===
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(
        editable=True, resizable=True, sortable=True, filter=True,
        wrapText=True, minWidth=80,
    )
    # 내부 컬럼 숨김
    gb.configure_column("_sheet_row", hide=True, editable=False)
    gb.configure_column("_meta", hide=True, editable=False)
    gb.configure_column("row_type", hide=True, editable=False)

    # === 3-level rowGroup: date → channel → category ===
    gb.configure_column("date", rowGroup=True, hide=True, editable=False, rowGroupIndex=0)
    gb.configure_column(
        "채널", rowGroup=True, hide=True, rowGroupIndex=1,
        cellRenderer=CHANNEL_BADGE,
    )
    gb.configure_column(
        "카테고리", rowGroup=True, hide=True, rowGroupIndex=2,
        cellRenderer=CATEGORY_BADGE,
    )

    # === 셀 설정 ===
    gb.configure_column(
        "현황", cellEditor="agSelectCellEditor",
        cellEditorParams={"values": STATUS_OPTIONS + ["📝 진행사항", "⚠ 이슈사항"]},
        cellStyle=STATUS_CELL_STYLE, width=110,
    )
    gb.configure_column("고객", width=220)
    gb.configure_column("연락처", width=130)
    gb.configure_column("내용", width=380, wrapText=True, autoHeight=True)
    gb.configure_column(
        "담당자", cellRenderer=PERSON_BADGE, width=180,
    )
    gb.configure_column(
        "매출", type=["numericColumn"],
        valueFormatter=AMOUNT_FORMATTER, cellStyle=AMOUNT_STYLE, width=130,
    )

    # === 그룹 헤더 + 진행/이슈 행 배경 ===
    gb.configure_grid_options(
        groupDisplayType="groupRows",
        groupDefaultExpanded=1,
        autoGroupColumnDef={
            "headerName": "",
            "cellRendererParams": {
                "innerRenderer": DATE_HEADER_RENDERER,
                "suppressCount": True,
            },
            "minWidth": 480,
        },
        getRowStyle=ROW_TYPE_STYLE,
        animateRows=True,
        enableRangeSelection=True,
        enableFillHandle=True,
        rowHeight=42,
        domLayout="normal",
    )

    grid_options = gb.build()

    # === 액션 바 ===
    ac1, ac2, ac3, ac4 = st.columns([1, 1, 1, 3])
    if ac1.button("➕ 행 추가", use_container_width=True, key="wl_add"):
        st.session_state["wl_show_new"] = True
    if ac2.button("🔄 새로고침", use_container_width=True, key="wl_refresh"):
        st.cache_data.clear()
        st.rerun()
    if ac3.button("💾 변경 저장", type="primary", use_container_width=True, key="wl_save"):
        st.session_state["wl_save_trigger"] = True
    ac4.caption(f"📂 record {(grid_df['row_type']=='record').sum()}건 + 진행 {(grid_df['row_type']=='progress').sum()} + 이슈 {(grid_df['row_type']=='issue').sum()}")

    # 인라인 신규 입력
    if st.session_state.get("wl_show_new"):
        _render_inline_form()

    # === AG-Grid 렌더 ===
    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        fit_columns_on_grid_load=False,
        theme="alpine",
        height=620,
        allow_unsafe_jscode=True,
        reload_data=False,
        key=f"wl_grid_{len(grid_df)}",
    )

    # === 변경 감지 + push ===
    if st.session_state.get("wl_save_trigger"):
        edited_df = pd.DataFrame(grid_response.get("data") or [])
        # progress/issue 행은 push 대상 제외 (시트의 메타 행)
        if "row_type" in edited_df.columns:
            edited_df = edited_df[edited_df["row_type"] == "record"]
        orig_records = grid_df[grid_df["row_type"] == "record"].copy()
        changes = _detect_changes(orig_records, edited_df)
        if not changes:
            st.toast("변경 사항 없음", icon="ℹ")
        elif sa_active:
            with st.spinner(f"본사 시트에 {len(changes)}개 셀 push 중..."):
                result = push_changes(changes)
            if result["ok"]:
                st.toast(f"✓ 시트에 {result['updated']}개 셀 저장됨", icon="✅")
                st.cache_data.clear()
            else:
                st.error(f"저장 실패: {result.get('error')}")
        else:
            st.warning(f"Service Account 미설정 — 변경 {len(changes)}건 push 보류")
            st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
        st.session_state["wl_save_trigger"] = False


def _detect_changes(orig: pd.DataFrame, edited: pd.DataFrame) -> list[dict]:
    """orig vs edited diff → [{row, field, value}]"""
    changes = []
    field_map = {
        "채널": "channel", "카테고리": "category", "현황": "status",
        "고객": "customer", "연락처": "phone", "내용": "content",
        "담당자": "person", "매출": "amount",
    }
    if "_sheet_row" not in orig.columns or "_sheet_row" not in edited.columns:
        return changes
    orig_idx = orig.set_index("_sheet_row")
    edited_idx = edited.set_index("_sheet_row")
    for sheet_row in edited_idx.index:
        if sheet_row not in orig_idx.index or sheet_row == -1:
            continue
        for col_kor, col_field in field_map.items():
            if col_kor not in edited_idx.columns or col_kor not in orig_idx.columns:
                continue
            orig_v = orig_idx.loc[sheet_row, col_kor]
            new_v = edited_idx.loc[sheet_row, col_kor]
            if col_field == "amount":
                try:
                    orig_n = int(orig_v) if orig_v not in ("", None) else 0
                    new_n = int(float(new_v)) if new_v not in ("", None) else 0
                    if orig_n != new_n:
                        changes.append({"row": int(sheet_row), "field": col_field,
                                       "value": new_n if new_n else ""})
                except (ValueError, TypeError):
                    pass
            else:
                if str(orig_v or "").strip() != str(new_v or "").strip():
                    changes.append({"row": int(sheet_row), "field": col_field,
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


def _render_inline_form():
    st.markdown("##### ➕ 새 영업 기록")
    with st.form("wl_new_row", clear_on_submit=True):
        r1 = st.columns([1.2, 1, 1, 1])
        f_date = r1[0].date_input("일자", value=date.today())
        f_channel = r1[1].selectbox("채널", CHANNEL_OPTIONS, index=0)
        f_category = r1[2].selectbox("카테고리", CATEGORY_OPTIONS, index=0)
        f_status = r1[3].selectbox("현황", STATUS_OPTIONS, index=1)
        r2 = st.columns([2, 2])
        f_customer = r2[0].text_input("고객명")
        f_phone = r2[1].text_input("연락처")
        f_content = st.text_area("내용", height=70)
        r3 = st.columns([1.5, 1])
        f_person = r3[0].text_input("담당자")
        f_amount = r3[1].number_input("매출(원)", min_value=0, step=10_000)
        bc1, bc2 = st.columns(2)
        submitted = bc1.form_submit_button("💾 저장", type="primary", use_container_width=True)
        cancel = bc2.form_submit_button("✕ 닫기", use_container_width=True)
    if cancel:
        st.session_state["wl_show_new"] = False
        st.rerun()
    if submitted:
        if not f_customer.strip():
            st.error("고객명 필수")
            return
        record = {
            "channel": f_channel, "category": f_category, "status": f_status,
            "customer": f_customer.strip(), "phone": f_phone.strip(),
            "content": f_content.strip(), "person": f_person.strip(),
            "amount": f_amount if f_amount > 0 else "",
        }
        with st.spinner("시트 저장 중..."):
            result = append_row(record, f_date)
        if result["ok"]:
            st.toast(f"✓ 행 {result['row']} 추가", icon="✅")
            st.session_state["wl_show_new"] = False
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning(f"⚠ {result.get('error')}")


# ============================================================
# 월별 / 연별 (간소화)
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
