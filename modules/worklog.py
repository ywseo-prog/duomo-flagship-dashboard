"""모듈 2: 업무일지 — 스펙 인계 골격 (단일 뷰 + 4-버튼 + 시트 sync)

[흐름]
1. 헤더
2. 데이터 로드 (services.fetch_worklog → parse_worklog → flatten)
3. KPI 3종 (월목표 / 금일누계 / 달성률)
4. 일자 필터
5. AG-Grid 빌드 + 렌더
6. 행 추가 4종 → session_state DataFrame prepend
7. 변경 감지 → push_changes (gspread batch_update)

[주의]
- st.set_page_config는 app.py에서 이미 호출 → 본 모듈에서 호출 X
- parsers.worklog_parser.parse_worklog는 DataFrame 반환 (호환)
  → 본 모듈은 parse_worklog_v2 (dict 반환)를 alias로 import
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import date, datetime

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from components.cell_renderers import (
    CHANNEL_BADGE, CATEGORY_BADGE, STATUS_CLASS_RULES,
    AMOUNT_CELL_STYLE, ROW_STYLE, DATE_HEADER_RENDERER,
)
from constants.design_tokens import PERSONS, STATUSES, GRID_CSS
from services.sheets_sync import fetch_worklog, push_changes, append_row
# 우리 프로젝트는 parsers/worklog_parser.py — 동일 이름의 단순 모듈 가정과 매핑
from parsers.worklog_parser import (
    parse_worklog_v2 as parse_worklog,
    flatten_for_aggrid,
)


# ============================================================
# 행 추가 헬퍼 — 4종 버튼이 호출
# ============================================================
def add_row(channel: str, category: str):
    """session_state DataFrame 맨 위에 빈 신규 행 (_sheet_row=-1) prepend."""
    state_key = "wl_df"
    df = st.session_state.get(state_key, pd.DataFrame())
    new = {
        "row_type": "record",
        "date": str(st.session_state.get("wl_selected_date") or date.today()),
        "_sheet_row": -1,
        "_meta": {},
        "channel": channel,
        "category": category,
        "status": "to do",
        "customer": "",
        "phone": "",
        "content": "",
        "person": "",
        "amount": 0,
    }
    df = pd.concat([pd.DataFrame([new]), df], ignore_index=True)
    st.session_state[state_key] = df
    st.toast(f"➕ {channel}·{category} 행 추가 (행 채우고 💾 저장)", icon="➕")
    st.rerun()


def render():
    # GRID_CSS inject (그리드 진입 전)
    st.markdown(GRID_CSS, unsafe_allow_html=True)

    # ─── 1. 헤더 ───────────────────────────
    st.title("■ 플래그십 업무일지")

    # ─── 2. 데이터 로드 ─────────────────────
    csv_text = fetch_worklog()
    parsed = parse_worklog(csv_text)
    df = flatten_for_aggrid(parsed)

    # ─── 3. KPI 카드 ────────────────────────
    header = parsed.get("header", {})
    target_v = header.get("month_target", 0) or 0
    current_v = header.get("current_total", 0) or 0
    rate_v = (header.get("achievement") or 0) * 100
    month_v = header.get("month", date.today().month)

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{month_v}월 목표", f"₩{target_v:,}")
    c2.metric("금일 누계", f"₩{current_v:,}")
    c3.metric("달성률", f"{rate_v:.2f}%")

    # ─── 4. 일자 필터 ───────────────────────
    selected_date = st.date_input("조회 일자", value=date.today(), key="wl_selected_date")
    df_filtered = df[df["date"] == str(selected_date)].copy() if len(df) else pd.DataFrame()

    # session_state 동기화 — filter 변경 시 신규 로드, 같으면 편집 유지
    state_key = "wl_df"
    cache_key = f"{selected_date.isoformat()}_{len(df_filtered)}"
    if st.session_state.get("wl_cache_key") != cache_key:
        st.session_state[state_key] = df_filtered.copy()
        st.session_state["wl_cache_key"] = cache_key
    work_df = st.session_state.get(state_key, df_filtered)

    # ─── 5. AG-Grid 옵션 빌드 ───────────────
    if len(work_df):
        gb = GridOptionsBuilder.from_dataframe(work_df)
        gb.configure_default_column(editable=True, resizable=True, sortable=True,
                                     filter=True, wrapText=True, minWidth=80)
        # 내부 컬럼 숨김
        gb.configure_column("_sheet_row", hide=True, editable=False)
        gb.configure_column("_meta",      hide=True, editable=False)
        gb.configure_column("row_type",   hide=True, editable=False)

        # 그룹화 컬럼 (3-level)
        gb.configure_column("date",     rowGroup=True, hide=True, rowGroupIndex=0, editable=False)
        gb.configure_column("channel",  rowGroup=True, hide=True, rowGroupIndex=1,
                             cellRenderer=CHANNEL_BADGE)
        gb.configure_column("category", rowGroup=True, hide=True, rowGroupIndex=2,
                             cellRenderer=CATEGORY_BADGE)

        # 편집 컬럼
        gb.configure_column("status", editable=True, width=100,
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": STATUSES + ["📝 진행사항", "⚠ 이슈사항"]},
            cellClassRules=STATUS_CLASS_RULES,
            headerName="현황")
        gb.configure_column("customer", editable=True, width=130, headerName="고객")
        gb.configure_column("phone",    editable=True, width=120, headerName="연락처")
        gb.configure_column("content",  editable=True, flex=1, wrapText=True, autoHeight=True,
                             headerName="내용")
        gb.configure_column("person", editable=True, width=120,
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": PERSONS},
            cellClass="person-cell",
            headerName="담당자")
        gb.configure_column("amount", editable=True, width=110, type=["numericColumn"],
            cellStyle=AMOUNT_CELL_STYLE,
            valueFormatter="value ? '₩' + value.toLocaleString() : ''",
            headerName="매출")

        # 그룹 디스플레이
        gb.configure_grid_options(
            groupDisplayType="groupRows",
            groupRowRendererParams={"innerRenderer": DATE_HEADER_RENDERER, "suppressCount": True},
            groupDefaultExpanded=-1,
            getRowStyle=ROW_STYLE,
            rowHeight=36,
        )

        # ─── 6. 그리드 렌더링 ───────────────────
        grid_response = AgGrid(
            work_df,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.MODEL_CHANGED,
            data_return_mode=DataReturnMode.AS_INPUT,
            allow_unsafe_jscode=True,
            theme="streamlit",
            height=600,
            reload_data=False,
            key=f"wl_grid_{cache_key}",
        )
        # 편집 결과를 session_state에 반영
        edited_df = pd.DataFrame(grid_response.get("data") or [])
        if len(edited_df):
            st.session_state[state_key] = edited_df
    else:
        st.info(f"{selected_date} 데이터 없음 — 아래 버튼으로 신규 행 추가")
        edited_df = work_df.copy()

    # ─── 7. 행 추가 버튼 (4종) ──────────────
    st.markdown("##### 행 추가")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("➕ 내방·소비자", use_container_width=True): add_row("내방", "소비자")
    if b2.button("➕ 내방·업체",   use_container_width=True): add_row("내방", "업체")
    if b3.button("➕ 유선·소비자", use_container_width=True): add_row("유선", "소비자")
    if b4.button("➕ 유선·업체",   use_container_width=True): add_row("유선", "업체")

    # ─── 8. 변경 감지 → Sheets sync ─────────
    if len(edited_df) and not edited_df.equals(df_filtered):
        st.caption("📝 변경사항 감지됨")
        if st.button("💾 저장 (Google Sheets 반영)", type="primary"):
            result = _sync_to_sheets(df_filtered, edited_df)
            if result.get("ok"):
                msg = []
                if result.get("updated"): msg.append(f"{result['updated']}개 셀 update")
                if result.get("appended"): msg.append(f"{result['appended']}개 행 append")
                st.success(f"✓ 동기화 완료 — {', '.join(msg) if msg else '변경 없음'}")
                st.cache_data.clear()
                st.session_state.pop("wl_cache_key", None)
            else:
                st.error(f"⚠ 동기화 실패: {result.get('error')}")


# ============================================================
# 시트 동기화 — diff 분리 후 (update / append) 각각 push
# ============================================================
def _sync_to_sheets(orig: pd.DataFrame, edited: pd.DataFrame) -> dict:
    result = {"ok": False, "updated": 0, "appended": 0, "error": None}
    try:
        # 신규 행 (_sheet_row=-1) 분리
        if "row_type" in edited.columns:
            edited_rec = edited[edited["row_type"] == "record"]
        else:
            edited_rec = edited
        new_rows = edited_rec[edited_rec["_sheet_row"] == -1] if "_sheet_row" in edited_rec.columns else pd.DataFrame()

        # 기존 행 diff
        changes = _detect_changes(orig, edited_rec)
        if changes:
            r = push_changes(changes)
            if r.get("ok"):
                result["updated"] = r.get("updated", 0)
            else:
                result["error"] = r.get("error")
                return result

        # 신규 행 append
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
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                d_obj = date.today()
            r2 = append_row(record, d_obj)
            if r2.get("ok"):
                result["appended"] += 1

        result["ok"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


def _detect_changes(orig: pd.DataFrame, edited: pd.DataFrame) -> list[dict]:
    changes = []
    fields = ["channel", "category", "status", "customer",
              "phone", "content", "person", "amount"]
    if "_sheet_row" not in orig.columns or "_sheet_row" not in edited.columns:
        return changes
    orig_idx = orig.set_index("_sheet_row")
    edited_idx = edited.set_index("_sheet_row")
    for sheet_row in edited_idx.index:
        if sheet_row == -1 or sheet_row not in orig_idx.index:
            continue
        for field in fields:
            if field not in edited_idx.columns or field not in orig_idx.columns:
                continue
            orig_v = orig_idx.loc[sheet_row, field]
            new_v = edited_idx.loc[sheet_row, field]
            if field == "amount":
                try:
                    o = int(orig_v) if orig_v not in ("", None) else 0
                    n = int(float(new_v)) if new_v not in ("", None) else 0
                    if o != n:
                        changes.append({"row": int(sheet_row), "field": field,
                                       "value": n if n else ""})
                except (ValueError, TypeError):
                    pass
            else:
                if str(orig_v or "").strip() != str(new_v or "").strip():
                    changes.append({"row": int(sheet_row), "field": field,
                                   "value": str(new_v or "").strip()})
    return changes
