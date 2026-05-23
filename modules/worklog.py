"""모듈 2: 업무일지 v0.8 — AG-Grid 기반 스프레드시트 네이티브 UX

[목표] 시트와 100% 동일한 작성·조회 — iframe X, expander X, AG-Grid 직접 편집.

[구조]
1. 상단 1줄 KPI 4 (compact)
2. 검색바 + 기간/담당자 필터
3. AG-Grid:
   - 일자별 group rows (그룹 헤더: 날짜 + 일별 합계)
   - 셀 더블클릭 편집, dropdown, 드래그 채우기, 우클릭 메뉴
   - 셀 컬러: 상태(done/ing/결제완료/견적진행)
   - 매출 ₩ 포맷, 날짜 정렬
4. 진행/이슈 메모 (그리드 하단)
5. [➕ 행 추가] 버튼 → 그리드 맨 위 새 행
6. 변경 감지 → bulk_update_worklog (gspread batch_update)
7. 일/월/연 토글 (월/연은 기존 차트)

의존성: streamlit-aggrid>=0.3.5
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
    load_worklog_df, aggregate_monthly, aggregate_by_person, aggregate_by_brand,
    aggregate_by_customer, load_monthly_target, load_visitor_trend,
    SHEET_ID, WORKLOG_TAB,
    append_worklog_row, bulk_update_worklog,
    CHANNEL_OPTIONS, CATEGORY_OPTIONS, STATUS_OPTIONS,
)
from utils import (
    render_report_section, render_task_widget,
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)

VIP_THRESHOLD = 3_000_000
PERSON_OPTIONS_6 = ["조이경", "서영완", "추승민", "강혁진", "이현진", "신민정"]


def render():
    greeting_header(
        "서영완", role="조명플래그십파트 · 업무일지 (AG-Grid 네이티브)",
        page_title="📊 업무일지",
    )

    df_all = load_worklog_df(source="auto")
    if not len(df_all):
        st.error("본사 시트 로드 실패 — Google Sheets 권한 확인")
        return
    df_all = df_all.copy()
    target = load_monthly_target()

    # === 1. 상단 1줄 KPI 4 ===
    _render_compact_kpi_row(df_all, target)

    # === 2. 검색·필터 + 뷰 토글 ===
    view = st.radio(
        "뷰", ["📅 일별 (시트 편집)", "🗓 월별 분석", "📆 연별 분석"],
        horizontal=True, label_visibility="collapsed", key="wl_view",
    )

    f = _render_search_bar(df_all)

    if view == "📅 일별 (시트 편집)":
        _render_grid_view(f)
    elif view == "🗓 월별 분석":
        _render_monthly_view(f, target)
    else:
        _render_yearly_view(f)

    render_task_widget("업무일지")


# ============================================================
# 상단 1줄 KPI 4 (compact)
# ============================================================
def _render_compact_kpi_row(df: pd.DataFrame, target: dict | None):
    today = date.today()
    cur_ym = f"{today.year}-{today.month:02d}"
    month_df = df[df["ym"] == cur_ym]
    paid_month = month_df[month_df["amount"] > 0]
    cur_sales = int(paid_month["amount"].sum())
    active_days = month_df["date"].dt.date.nunique()
    daily_avg = cur_sales // max(active_days, 1) if active_days else 0
    target_val = target.get("target") if target else None
    rate = (cur_sales / target_val * 100) if target_val else None

    cols = st.columns(4)
    with cols[0]:
        if target_val:
            st.markdown(black_kpi_card(
                f"{today.month}월 목표", f"₩{target_val/1e8:.2f}억",
                "본사 시트", "gold", "🎯",
            ), unsafe_allow_html=True)
        else:
            st.markdown(black_kpi_card("목표", "—", "미입력", "neutral", "🎯"),
                        unsafe_allow_html=True)
    with cols[1]:
        st.markdown(black_kpi_card(
            "금일 누계 매출", f"₩{cur_sales/1e8:.2f}억",
            f"({cur_sales:,})", "gold", "💰",
        ), unsafe_allow_html=True)
    with cols[2]:
        if rate is not None:
            days_in_month = monthrange(today.year, today.month)[1]
            pace = today.day / days_in_month * 100
            trend = "up" if rate >= pace else "down"
            st.markdown(black_kpi_card(
                "달성률", f"{rate:.1f}%",
                f"진척 {pace:.0f}% / 잔여 ₩{max(target_val-cur_sales,0)/1e8:.2f}억",
                trend, "📊",
            ), unsafe_allow_html=True)
        else:
            conv = len(paid_month) / max(len(month_df), 1) * 100
            st.markdown(black_kpi_card(
                "전환률", f"{conv:.1f}%",
                f"{len(paid_month)}/{len(month_df)}", "neutral", "📊",
            ), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(black_kpi_card(
            "이번달 일평균", f"₩{daily_avg:,}",
            f"활성 {active_days}일", "gold", "📈",
        ), unsafe_allow_html=True)


# ============================================================
# 검색·필터 한 줄
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
# AG-Grid 메인 뷰 (시트 네이티브 편집)
# ============================================================
def _render_grid_view(f: pd.DataFrame):
    # 의존성 import — 미설치 환경 graceful
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
    except ImportError:
        st.error(
            "**streamlit-aggrid 미설치** — `pip install streamlit-aggrid>=0.3.5` 후 재배포 필요.\n\n"
            "Streamlit Cloud는 requirements.txt 변경 push 시 자동 설치됩니다."
        )
        st.caption("⏳ 다음 배포 (~1분) 후 자동 활성화됩니다. fallback: 표 모드로 표시 중.")
        _render_fallback_table(f)
        return

    if not len(f):
        st.info("검색·필터 결과 0건 — 조건을 완화해 주세요.")
        return

    # === Service Account 상태 ===
    from parsers.worklog_writer import _has_service_account
    has_sa = _has_service_account()
    sa_status = "✓ Google Service Account 활성 — 셀 편집 시 본사 시트 자동 동기화" if has_sa else \
                "⚠ Service Account 미설정 — 그리드 편집은 가능하나 시트 push 비활성 (저장 시 TSV 다운로드)"
    st.caption(sa_status)

    # === 데이터 준비 (AG-Grid용 컬럼명 + sheet_row 보존) ===
    grid_df = f.copy()
    grid_df["일자"] = grid_df["date"].dt.strftime("%Y.%m.%d (%a)")
    grid_df = grid_df.rename(columns={
        "channel": "채널", "category": "카테고리", "status": "현황",
        "customer": "고객", "phone": "연락처", "content": "내용",
        "person_raw": "담당자", "amount": "매출",
    })
    grid_df = grid_df[["_sheet_row", "일자", "채널", "카테고리", "현황",
                        "고객", "연락처", "내용", "담당자", "매출"]]
    # forward-fill 채널/카테고리 (셀 병합 효과)
    grid_df["채널"] = grid_df.groupby("일자")["채널"].transform(
        lambda s: s.replace("", pd.NA).ffill().fillna(""))
    grid_df["카테고리"] = grid_df.groupby("일자")["카테고리"].transform(
        lambda s: s.replace("", pd.NA).ffill().fillna(""))
    grid_df = grid_df.sort_values(["일자", "_sheet_row"], ascending=[False, True])

    # === GridOptionsBuilder ===
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(
        editable=True, resizable=True, sortable=True, filter=True,
        wrapText=True, autoHeight=False, minWidth=80,
    )
    # _sheet_row 숨김 (식별자)
    gb.configure_column("_sheet_row", hide=True, editable=False)

    # 일자 group
    gb.configure_column(
        "일자", rowGroup=True, hide=True, editable=False, width=130,
    )

    # 채널 / 카테고리 / 현황 dropdown
    gb.configure_column(
        "채널", cellEditor="agSelectCellEditor",
        cellEditorParams={"values": CHANNEL_OPTIONS}, width=80,
    )
    gb.configure_column(
        "카테고리", cellEditor="agSelectCellEditor",
        cellEditorParams={"values": CATEGORY_OPTIONS}, width=90,
    )

    # 현황 셀 컬러 JsCode
    status_color_js = JsCode("""
function(params) {
  const colors = {
    'done':'#999999', 'ing':'#FFA000',
    '결제 완료':'#C9A961', '결제완료':'#C9A961',
    '견적 진행':'#1976D2', '견적진행':'#1976D2',
    '예정':'#1976D2', '보류':'#F57C00',
    '취소':'#D32F2F', '문의':'#7B1FA2', '재방문':'#5D4037'
  };
  const v = (params.value || '').toString().trim();
  if (colors[v]) {
    return {
      backgroundColor: colors[v], color: '#fff',
      fontWeight: '700', textAlign: 'center',
      borderRadius: '3px', fontSize: '11px', letterSpacing: '0.5px'
    };
  }
  return {textAlign: 'center'};
}
""")
    gb.configure_column(
        "현황", cellEditor="agSelectCellEditor",
        cellEditorParams={"values": STATUS_OPTIONS},
        cellStyle=status_color_js, width=100,
    )

    # 담당자 dropdown (6인) — 자유 입력도 허용 (agTextCellEditor fallback)
    gb.configure_column("담당자", width=140, editable=True)

    # 고객 / 연락처 / 내용
    gb.configure_column("고객", width=200)
    gb.configure_column("연락처", width=130)
    gb.configure_column("내용", width=360, wrapText=True, autoHeight=True)

    # 매출 (numeric + ₩ format + 골드 강조)
    amount_style_js = JsCode("""
function(params) {
  if (params.value && params.value > 0) {
    return {color:'#C9A961', fontWeight:'700', textAlign:'right',
            fontFamily:'Inter,monospace'};
  }
  return {color:'#BBB', textAlign:'right'};
}
""")
    amount_format_js = JsCode("""
function(params) {
  if (params.value == null || params.value === '' || params.value === 0) return '—';
  const n = parseInt(params.value, 10);
  if (isNaN(n)) return params.value;
  return '₩' + n.toLocaleString('ko-KR');
}
""")
    gb.configure_column(
        "매출", type=["numericColumn"],
        valueFormatter=amount_format_js,
        cellStyle=amount_style_js, width=130,
    )

    # 그룹 헤더 커스터마이즈 — 일별 합계
    group_header_js = JsCode("""
function(params) {
  if (!params.node.allLeafChildren) return params.value || '';
  let count = params.node.allLeafChildren.length;
  let paid = 0;
  let paidCnt = 0;
  params.node.allLeafChildren.forEach(n => {
    const v = parseInt(n.data['매출']) || 0;
    if (v > 0) { paid += v; paidCnt++; }
  });
  const paidStr = paid > 0 ? '₩' + paid.toLocaleString('ko-KR') : '₩0';
  return `📅 ${params.value} · 유입 ${count}팀 · 결제 ${paidCnt}건 · ${paidStr}`;
}
""")
    gb.configure_grid_options(
        groupDisplayType="groupRows",
        groupDefaultExpanded=1,  # 첫 그룹만 펼침
        autoGroupColumnDef={
            "headerName": "",
            "cellRendererParams": {
                "innerRenderer": group_header_js,
                "suppressCount": True,
            },
            "minWidth": 380,
        },
        animateRows=True,
        enableRangeSelection=True,
        enableFillHandle=True,
        suppressMultiRangeSelection=False,
        rowHeight=42,
        domLayout="normal",
    )

    grid_options = gb.build()

    # === 액션 바 ===
    ac1, ac2, ac3, ac4 = st.columns([1, 1, 1, 3])
    if ac1.button("➕ 행 추가", use_container_width=True, key="wl_add_row"):
        st.session_state["wl_show_new"] = True
    if ac2.button("🔄 새로고침", use_container_width=True, key="wl_refresh"):
        st.cache_data.clear()
        st.rerun()
    if ac3.button("💾 변경 저장", type="primary", use_container_width=True, key="wl_save"):
        st.session_state["wl_save_trigger"] = True
    ac4.caption(f"📂 {len(grid_df):,}건 · 더블클릭으로 셀 편집 / 드래그로 채우기 / 우클릭 메뉴")

    # === 인라인 신규 입력 ===
    if st.session_state.get("wl_show_new"):
        _render_inline_form_quick()

    # === AG-Grid 렌더 ===
    grid_response = AgGrid(
        grid_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,  # 셀 값 변경 시 rerun
        fit_columns_on_grid_load=False,
        theme="alpine",
        height=600,
        allow_unsafe_jscode=True,
        reload_data=False,
        key=f"wl_grid_{len(grid_df)}",
    )

    # === 변경 감지 + 시트 push ===
    edited_df = pd.DataFrame(grid_response["data"])
    if st.session_state.get("wl_save_trigger") and len(edited_df):
        changes = _detect_changes(grid_df, edited_df)
        if changes:
            if has_sa:
                with st.spinner(f"본사 시트에 {len(changes)}개 셀 push 중..."):
                    result = bulk_update_worklog(changes, SHEET_ID, WORKLOG_TAB)
                if result["ok"]:
                    st.toast(f"✓ 시트에 {result['updated']}개 셀 저장됨", icon="✅")
                    st.cache_data.clear()
                else:
                    st.error(f"⚠ 저장 실패: {result.get('error')}")
            else:
                st.warning("Service Account 미설정 — 변경사항은 그리드에만 반영, 시트 push 불가.")
                with st.expander(f"📋 변경 사항 {len(changes)}건 (TSV 복사)"):
                    diff_df = pd.DataFrame(changes)
                    st.dataframe(diff_df, hide_index=True, use_container_width=True)
        else:
            st.toast("변경사항 없음", icon="ℹ")
        st.session_state["wl_save_trigger"] = False


def _detect_changes(orig: pd.DataFrame, edited: pd.DataFrame) -> list[dict]:
    """원본 vs 편집본 diff → [{row, field, value}, ...]"""
    changes = []
    field_map = {
        "채널": "channel", "카테고리": "category", "현황": "status",
        "고객": "customer", "연락처": "phone", "내용": "content",
        "담당자": "person", "매출": "amount",
    }
    orig_idx = orig.set_index("_sheet_row")
    edited_idx = edited.set_index("_sheet_row") if "_sheet_row" in edited.columns else edited
    for sheet_row in edited_idx.index:
        if sheet_row not in orig_idx.index:
            continue
        for col_kor, col_field in field_map.items():
            if col_kor not in edited_idx.columns or col_kor not in orig_idx.columns:
                continue
            orig_v = orig_idx.loc[sheet_row, col_kor]
            new_v = edited_idx.loc[sheet_row, col_kor]
            # numeric 비교
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
                orig_s = str(orig_v or "").strip()
                new_s = str(new_v or "").strip()
                if orig_s != new_s:
                    changes.append({"row": int(sheet_row), "field": col_field,
                                   "value": new_s})
    return changes


def _render_fallback_table(f: pd.DataFrame):
    """streamlit-aggrid 미설치 시 임시 표 렌더"""
    if not len(f):
        st.info("데이터 없음")
        return
    show = f.copy()
    show["일자"] = show["date"].dt.strftime("%Y.%m.%d")
    show["매출"] = show["amount"].apply(lambda v: f"₩{int(v):,}" if v else "—")
    show = show[["일자", "channel", "category", "status", "customer",
                  "phone", "content", "person_raw", "매출"]]
    show.columns = ["일자", "채널", "카테고리", "현황", "고객", "연락처", "내용", "담당자", "매출"]
    st.dataframe(show, hide_index=True, use_container_width=True, height=500)


def _render_inline_form_quick():
    """그리드 위 신규 행 추가 인라인 폼"""
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
            result = append_worklog_row(record, f_date, SHEET_ID, WORKLOG_TAB)
        if result["ok"]:
            st.toast(f"✓ 행 {result['row']} 추가됨", icon="✅")
            st.session_state["wl_show_new"] = False
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning(f"⚠ {result.get('error')}")
            st.code(result.get("tsv", ""), language="text")


# ============================================================
# 월별 / 연별 분석 (기존 유지)
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
    sel_year, sel_month = int(sel_ym[:4]), int(sel_ym[5:7])
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
        fig = go.Figure()
        fig.add_trace(go.Bar(
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
