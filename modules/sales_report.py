"""모듈 9: 영업보고 — 일일 카톡 보고 자동 생성 + 고객/브랜드 분석 + 캘린더 리포트
※ 참조 앱: https://sales-report-ivory.vercel.app
   동일 SHEET_ID 활용. 본사 시트 fetch → 자동 분석 → 카톡 텍스트 + 분석 탭.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import calendar as cal
from datetime import date, datetime, timedelta

from parsers import (
    load_worklog_df, load_monthly_target, SHEET_ID, WORKLOG_TAB,
    aggregate_by_brand, aggregate_by_customer,
    daily_report_data, format_katalk_report,
    append_worklog_row, append_worklog_block,
    format_row_tsv, format_date_header_tsv,
    CHANNEL_OPTIONS, CATEGORY_OPTIONS, STATUS_OPTIONS,
)
from utils.styles import (
    greeting_header, black_kpi_card, multi_card_row, leaderboard_row,
    section_header, alert_banner, status_badge_html,
)


def render():
    greeting_header(
        "조명 플래그십",
        role="일일 영업보고 자동화 · 카톡 텍스트 생성 + 고객/브랜드/리포트 분석",
        page_title="📝 영업보고",
    )

    df = load_worklog_df(source="auto")
    if not len(df):
        st.error("본사 시트 데이터 로드 실패 — Google Sheets 권한 확인")
        return
    df = df[df["fmt"] == "NEW"].copy()
    target = load_monthly_target()

    tab_write, tab_board, tab_today, tab_calendar, tab_customers, tab_brands = st.tabs([
        "✍ 영업 기록 작성",
        "📋 영업 보드",
        "📝 오늘 보고",
        "📅 캘린더 리포트",
        "👥 고객 (LTV)",
        "🏷 브랜드 분석",
    ])

    with tab_write:
        _render_write_tab()
    with tab_board:
        _render_board_tab(df)
    with tab_today:
        _render_today_tab(df, target)
    with tab_calendar:
        _render_calendar_tab(df)
    with tab_customers:
        _render_customers_tab(df)
    with tab_brands:
        _render_brands_tab(df)


# ====================================================================
# Tab 1.5 📋 영업 보드 — 본사 시트 레이아웃의 한눈에 보기 + 필터/검색
# ====================================================================

_CHANNEL_COLOR = {
    "내방":   "#C9A961",  # 골드
    "유선":   "#1976D2",
    "온라인": "#7B1FA2",
    "소개":   "#F57C00",
    "기타":   "#999999",
}
_CATEGORY_COLOR = {
    "소비자":   "#1976D2",
    "업체":     "#7B1FA2",
    "디자이너": "#2E7D32",
    "기타":     "#999999",
}
_STATUS_COLOR = {
    "done":     "#2E7D32",
    "결제 완료": "#2E7D32",
    "결제완료":  "#2E7D32",
    "ing":      "#FF6B35",
    "예정":     "#1976D2",
    "보류":     "#F57C00",
    "취소":     "#999999",
    "문의":     "#7B1FA2",
    "재방문":   "#C9A961",
}


def _render_board_tab(df: pd.DataFrame):
    if not len(df):
        st.warning("데이터 없음")
        return

    today = date.today()

    # === 필터 바 ===
    st.markdown(section_header(
        "영업 기록 보드", "본사 시트의 일별 블록을 한눈에 + 강력한 필터/검색"
    ), unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([2, 2, 3])
    period = fc1.selectbox(
        "📅 기간",
        ["오늘", "이번주", "이번달", "최근 7일", "최근 30일", "전체", "사용자지정"],
        index=2, key="board_period"
    )
    channel_filter = fc2.multiselect(
        "📍 채널",
        sorted([c for c in df["channel"].unique() if c]),
        default=[], key="board_channel"
    )
    search = fc3.text_input(
        "🔍 검색", placeholder="고객명·내용·담당자·브랜드 어디든", key="board_search"
    )

    fc4, fc5, fc6 = st.columns([2, 2, 3])
    category_filter = fc4.multiselect(
        "🏷 카테고리",
        sorted([c for c in df["category"].unique() if c]),
        default=[], key="board_cat"
    )
    status_filter = fc5.multiselect(
        "🚦 상태",
        sorted([s for s in df["status"].unique() if s]),
        default=[], key="board_status"
    )
    person_options = sorted(set(p for ps in df["persons"] for p in ps if p))
    person_filter = fc6.multiselect(
        "👤 담당자",
        person_options, default=[], key="board_person"
    )

    # === 기간 필터 적용 ===
    f = df.copy()
    if period == "오늘":
        f = f[f["date"].dt.date == today]
    elif period == "이번주":
        week_start = today - timedelta(days=today.weekday())
        f = f[f["date"].dt.date >= week_start]
    elif period == "이번달":
        f = f[f["date"].dt.date >= today.replace(day=1)]
    elif period == "최근 7일":
        f = f[f["date"].dt.date >= today - timedelta(days=7)]
    elif period == "최근 30일":
        f = f[f["date"].dt.date >= today - timedelta(days=30)]
    elif period == "사용자지정":
        cc1, cc2 = st.columns(2)
        d1 = cc1.date_input("시작", today - timedelta(days=14), key="board_d1")
        d2 = cc2.date_input("종료", today, key="board_d2")
        f = f[(f["date"].dt.date >= d1) & (f["date"].dt.date <= d2)]

    if channel_filter:
        f = f[f["channel"].isin(channel_filter)]
    if category_filter:
        f = f[f["category"].isin(category_filter)]
    if status_filter:
        f = f[f["status"].isin(status_filter)]
    if person_filter:
        f = f[f["persons"].apply(lambda ps: any(p in ps for p in person_filter))]
    if search:
        s = search.strip().lower()
        mask = (
            f["customer"].astype(str).str.lower().str.contains(s, na=False) |
            f["content"].astype(str).str.lower().str.contains(s, na=False) |
            f["person_raw"].astype(str).str.lower().str.contains(s, na=False) |
            f["brands"].apply(lambda b: any(s in br.lower() for br in (b or [])))
        )
        f = f[mask]

    # === 결과 요약 ===
    total_entries = len(f)
    paid_f = f[f["amount"] > 0]
    total_paid = int(paid_f["amount"].sum())
    n_days = f["date"].dt.date.nunique()
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("기록 수", f"{total_entries:,}")
    rc2.metric("결제 건", f"{len(paid_f):,}")
    rc3.metric("결제 합계", f"₩{total_paid:,}")
    rc4.metric("커버 일수", f"{n_days}일")

    if not total_entries:
        st.info("조건에 맞는 기록이 없습니다. 필터를 완화해 주세요.")
        return

    # === 정렬: 날짜 내림차순 ===
    sort_opt = st.radio(
        "정렬",
        ["최신순", "오래된순", "결제 큰순"],
        horizontal=True, key="board_sort"
    )

    # === 날짜별 그룹 카드 렌더 ===
    grouped = sorted(
        f.groupby(f["date"].dt.date),
        key=lambda kv: kv[0],
        reverse=(sort_opt != "오래된순"),
    )

    # 결제 큰순 정렬은 그룹 단위로
    if sort_opt == "결제 큰순":
        grouped = sorted(
            grouped,
            key=lambda kv: int(kv[1][kv[1]["amount"] > 0]["amount"].sum()),
            reverse=True,
        )

    # 페이지네이션 — 한 번에 너무 많으면 무거움
    PAGE_SIZE = 10
    page = st.number_input(
        f"페이지 (총 {len(grouped)}일, 페이지당 {PAGE_SIZE}일)",
        min_value=1, max_value=max((len(grouped) + PAGE_SIZE - 1) // PAGE_SIZE, 1),
        value=1, step=1, key="board_page",
    )
    start, end = (page - 1) * PAGE_SIZE, page * PAGE_SIZE

    for d_obj, day_df in grouped[start:end]:
        _render_day_card(d_obj, day_df)


def _render_day_card(d_obj: date, day_df: pd.DataFrame):
    weekday = ["월","화","수","목","금","토","일"][d_obj.weekday()]
    paid_today = day_df[day_df["amount"] > 0]
    total_paid = int(paid_today["amount"].sum())
    n_entries = len(day_df)

    # 채널·카테고리별 group 후 정렬 (내방→유선→온라인 / 소비자→업체→디자이너)
    channel_order = {"내방": 0, "유선": 1, "온라인": 2, "소개": 3, "기타": 4}
    category_order = {"소비자": 0, "업체": 1, "디자이너": 2, "기타": 3}
    day_df = day_df.copy()
    day_df["_ch_o"] = day_df["channel"].map(lambda c: channel_order.get(c, 9))
    day_df["_ct_o"] = day_df["category"].map(lambda c: category_order.get(c, 9))
    day_df = day_df.sort_values(["_ch_o", "_ct_o"])

    # 카드 HTML
    head_html = f"""
<div class="sb-day">
  <div class="sb-day-head">
    <div>
      <div class="sd-date">{d_obj.strftime('%Y.%m.%d')} ({weekday})</div>
      <div class="sd-meta">D{(d_obj - date.today()).days:+d} · {(date.today() - d_obj).days}일 전</div>
    </div>
    <div class="sd-kpi">
      <span>유입 <b>{n_entries}팀</b></span>
      <span>계약 <b>{len(paid_today)}건</b></span>
      <span>결제 <b>₩{total_paid:,}</b></span>
    </div>
  </div>
"""
    rows_html = []
    for r in day_df.itertuples():
        channel = r.channel or "기타"
        category = r.category or "기타"
        status_v = r.status or ""
        cust = (r.customer or "—").replace("\n", " / ")
        content = (r.content or "").replace("\n", " ")
        person = r.person_raw or ""
        phone = r.phone or ""
        amount = int(r.amount or 0)

        ch_color = _CHANNEL_COLOR.get(channel, "#999")
        ct_color = _CATEGORY_COLOR.get(category, "#999")
        st_color = _STATUS_COLOR.get(status_v, "#999")

        badges = (
            f'<span class="sb-status" style="background:{ch_color}">{channel}</span>'
            f'<span class="sb-status" style="background:{ct_color}">{category}</span>'
        )
        st_badge = f'<span class="sb-status" style="background:{st_color}">{status_v or "—"}</span>' if status_v else ""
        amt_html = f'<div class="sb-amount {"zero" if amount == 0 else ""}">₩{amount:,}</div>' if amount else '<div class="sb-amount zero">—</div>'
        phone_html = f'<div class="sb-phone">☎ {phone}</div>' if phone else ""

        rows_html.append(f"""
<div class="sb-row">
  <div class="sb-badges">{badges}</div>
  <div>{st_badge}</div>
  <div>
    <div class="sb-customer">{cust}</div>
    <div class="sb-content">{content[:200]}{'…' if len(content) > 200 else ''}</div>
    {phone_html}
  </div>
  <div class="sb-person">{person}</div>
  {amt_html}
</div>
""")

    foot_html = '<div class="sb-foot"><span class="sf-tag">💡</span>상세는 본사 시트 참조 · 진행/이슈 메모는 시트 내 유지</div>'
    full_html = head_html + "".join(rows_html) + foot_html + "</div>"
    st.markdown(full_html, unsafe_allow_html=True)


# ====================================================================
# Tab 0. ✍ 영업 기록 작성 (본사 시트 Write)
# ====================================================================
def _render_write_tab():
    """본사 시트의 일자 블록 형식 — date 헤더 + 표 편집 + 진행/이슈 메모 + 일괄 저장"""
    st.markdown(section_header(
        "본사 업무일지 작성 (대시보드 내장)",
        "본사 시트의 일자 블록과 동일한 형식 — 표를 직접 편집하고 일괄 저장"
    ), unsafe_allow_html=True)

    from parsers.worklog_writer import _has_service_account
    if _has_service_account():
        st.markdown(alert_banner(
            "✓ Service Account 활성 — 저장 시 본사 시트에 자동 기록",
            "동일 날짜 블록이 있으면 거기에 행 추가, 없으면 새 블록 생성 (날짜 헤더 + 카테고리 + 데이터 + 진행/이슈).",
            level="green", icon="✓"
        ), unsafe_allow_html=True)
    else:
        st.markdown(alert_banner(
            "ⓘ Service Account 미설정 — 저장 시 TSV 텍스트 출력",
            "복사해서 본사 시트 빈 행에 붙여넣으면 자동 분리됩니다. 자동 모드 활성화는 하단 expander 참조.",
            level="blue", icon="ⓘ"
        ), unsafe_allow_html=True)

    # === 일자 헤더 ===
    hc1, hc2, hc3 = st.columns([1.5, 2, 2])
    rec_date = hc1.date_input("📅 작성 날짜", value=date.today(), key="block_date")
    weekday = ["월","화","수","목","금","토","일"][rec_date.weekday()]
    hc2.metric("일자", f"{rec_date.strftime('%Y.%m.%d')} ({weekday})")

    # === session_state로 표 데이터 유지 ===
    state_key = f"worklog_rows_{rec_date.isoformat()}"
    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame([
            {"채널":"내방", "카테고리":"소비자", "상태":"ing", "고객명":"", "전화":"",
             "내용":"", "담당자":"", "금액":0}
            for _ in range(3)  # 빈 행 3개로 시작
        ])

    # === 표 편집기 (data_editor) ===
    st.markdown("##### 📋 거래 행 (자유롭게 추가/수정/삭제)")
    edited = st.data_editor(
        st.session_state[state_key],
        key=f"editor_{rec_date.isoformat()}",
        num_rows="dynamic",  # 행 추가/삭제 자유
        use_container_width=True,
        column_config={
            "채널": st.column_config.SelectboxColumn(
                "📍 채널", options=CHANNEL_OPTIONS, required=False, width="small",
            ),
            "카테고리": st.column_config.SelectboxColumn(
                "🏷 카테고리", options=CATEGORY_OPTIONS, required=False, width="small",
            ),
            "상태": st.column_config.SelectboxColumn(
                "🚦 상태", options=STATUS_OPTIONS, required=False, width="small",
            ),
            "고객명": st.column_config.TextColumn(
                "👤 고객명", width="medium",
                help="예) 김아름 사원 손님 / 단체 가족 / 30대 부부",
            ),
            "전화": st.column_config.TextColumn(
                "☎ 전화", width="small",
            ),
            "내용": st.column_config.TextColumn(
                "📝 내용", width="large",
                help="상담 내용 (제품·금액·다음 액션 등)",
            ),
            "담당자": st.column_config.TextColumn(
                "🧑 담당자", width="small",
                help="예) 서영완 선임 / 추승민 사원",
            ),
            "금액": st.column_config.NumberColumn(
                "💰 금액(원)", min_value=0, step=10_000, format="₩%d", width="small",
            ),
        },
        hide_index=True,
    )
    st.session_state[state_key] = edited

    # === 미리보기 통계 ===
    valid_rows = edited[edited["고객명"].astype(str).str.strip() != ""]
    paid_rows = valid_rows[valid_rows["금액"] > 0]
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("유효 행", f"{len(valid_rows)}")
    mc2.metric("결제 건", f"{len(paid_rows)}")
    mc3.metric("결제 합계", f"₩{int(paid_rows['금액'].sum()):,}")

    # === 진행사항 / 이슈사항 메모 ===
    st.markdown("##### 📝 블록 메모")
    nc1, nc2 = st.columns(2)
    progress_note = nc1.text_area(
        "진행사항 (선택)", height=100, key=f"prog_{rec_date.isoformat()}",
        placeholder="오늘의 핵심 진행건 메모 — 예) 카민디자인 견적 회신 / VIP A 컨설팅 일정 조율"
    )
    issue_note = nc2.text_area(
        "이슈사항 (선택)", height=100, key=f"issue_{rec_date.isoformat()}",
        placeholder="이슈/리스크 메모 — 예) FLOS 5월 입고 지연 / LASVIT 클레임 대응 중"
    )

    # === 저장 버튼 ===
    sc1, sc2 = st.columns([3, 1])
    save_clicked = sc2.button("💾 본사 시트에 저장", type="primary", use_container_width=True)
    sc1.caption(f"💡 {len(valid_rows)}건의 거래 + 진행/이슈 메모를 {rec_date.strftime('%Y.%m.%d')} 블록에 일괄 기록")

    if save_clicked:
        if not len(valid_rows):
            st.error("유효한 행이 없습니다. 고객명을 한 줄 이상 입력하세요.")
            return

        # df → records
        records = []
        for _, r in valid_rows.iterrows():
            records.append({
                "channel": str(r["채널"]).strip(),
                "category": str(r["카테고리"]).strip(),
                "status": str(r["상태"]).strip(),
                "customer": str(r["고객명"]).strip(),
                "phone": str(r["전화"]).strip(),
                "content": str(r["내용"]).strip(),
                "person": str(r["담당자"]).strip(),
                "amount": int(r["금액"]) if r["금액"] else "",
            })

        with st.spinner(f"본사 시트에 {len(records)}건 일괄 기록 중..."):
            result = append_worklog_block(
                records=records, target_date=rec_date,
                progress_note=progress_note.strip(),
                issue_note=issue_note.strip(),
                sheet_id=SHEET_ID, sheet_name=WORKLOG_TAB,
            )

        if result["ok"]:
            st.success(f"✓ 본사 시트에 {result['rows_added']}건 저장 완료 ({rec_date.isoformat()})")
            st.balloons()
            # 표 초기화 옵션
            if st.button("✨ 표 비우고 새 블록 작성", key="reset_after_save"):
                del st.session_state[state_key]
                st.cache_data.clear()
                st.rerun()
            else:
                st.cache_data.clear()
        else:
            st.warning(f"⚠ 자동 write 미실행: {result.get('error', '')}")
            st.markdown(section_header("📋 TSV 일괄 출력 — 본사 시트에 붙여넣기"), unsafe_allow_html=True)
            st.caption("아래 전체를 복사해서 본사 시트의 빈 영역에 붙여넣으면 한 번에 행 전체가 채워집니다.")
            st.code(result["tsv_bulk"], language="text")

    # === 도움말 ===
    with st.expander("ⓘ Service Account 자동 write 활성화 (저장 시 즉시 본사 시트 반영)"):
        st.markdown("""
1. Google Cloud Console → 프로젝트 생성/선택
2. **APIs & Services → Library** → "Google Sheets API" 활성화
3. **APIs & Services → Credentials → Create Credentials → Service Account** 만들기
4. 생성된 service account에서 **Keys → Add Key → Create new key (JSON)** → 다운로드
5. **본사 시트** 우상단 공유 → JSON 안의 `client_email` 값에 **편집자 권한** 부여
6. Streamlit Cloud → **Manage app → Settings → Secrets** 에 아래 추가:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "duomo-flagship-sa@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://..."
```

저장 후 앱 자동 재시작 → 본 탭 상단에 `✓ Active` 그린 배너 표시됨.
""")


# ====================================================================
# Tab 1. 📝 오늘 보고
# ====================================================================
def _render_today_tab(df: pd.DataFrame, target: dict | None):
    today = date.today()
    c1, c2 = st.columns([1, 4])
    sel_date = c1.date_input("보고 날짜", value=today, key="report_date")
    c2.caption(f"본사 시트 자동 분석 · {sel_date.strftime('%Y년 %m월 %d일')} ({['월','화','수','목','금','토','일'][sel_date.weekday()]}요일)")

    data = daily_report_data(df, sel_date)
    if not data:
        st.warning("해당 날짜 데이터 없음")
        return

    # === KPI 4종 ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card(
        "유입 (팀)", f"{data['total_entries']}",
        f"워크인 {data['walk_in']}건", "neutral", "🚶"
    ), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card(
        "금일 계약", f"{data['paid_count_today']}",
        f"건 / 전환률 {(data['paid_count_today']/max(data['total_entries'],1)*100):.0f}%",
        "up" if data['paid_count_today'] else "neutral", "✍"
    ), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card(
        "금일 계약 총액", f"₩{data['paid_sum_today']:,}",
        f"객단가 ₩{int(data['paid_sum_today']/max(data['paid_count_today'],1)):,}",
        "gold" if data['paid_sum_today'] else "neutral", "💰"
    ), unsafe_allow_html=True)
    month_label = f"{sel_date.month}월 누적"
    if target and target.get("target") and target.get("month") == sel_date.month:
        rate = data['paid_sum_month'] / target['target'] * 100
        cols[3].markdown(black_kpi_card(
            f"{month_label} / 목표", f"{rate:.1f}%",
            f"₩{data['paid_sum_month']:,} / ₩{target['target']:,}",
            "up" if rate >= (sel_date.day/30*100) else "down", "🎯"
        ), unsafe_allow_html=True)
    else:
        cols[3].markdown(black_kpi_card(
            month_label, f"₩{data['paid_sum_month']:,}",
            f"{data['paid_count_month']}건", "gold", "📊"
        ), unsafe_allow_html=True)

    # === 카톡 발송용 텍스트 ===
    st.markdown(section_header(
        "💬 카톡 발송용 메시지", "복사 후 단톡방 붙여넣기"
    ), unsafe_allow_html=True)
    katalk = format_katalk_report(data)
    st.code(katalk, language="text")

    # 단톡방 복사 헬퍼 (Streamlit native 클립보드 X → st.code의 복사 버튼 활용)
    st.caption("⌨ 위 박스 우상단 복사 아이콘 클릭 → 카톡 단톡방 붙여넣기")

    # === 계약/상담 표 ===
    if data['paid_count_today']:
        st.markdown(section_header("금일 계약 상세"), unsafe_allow_html=True)
        paid = data['paid_today_df'][["customer","person_raw","amount","content","brands"]].copy()
        paid["amount"] = paid["amount"].apply(lambda v: f"₩{int(v):,}")
        paid["brands"] = paid["brands"].apply(lambda b: ", ".join(b) if isinstance(b, list) else "")
        paid.columns = ["고객","담당","금액","내용","브랜드"]
        st.dataframe(paid, hide_index=True, use_container_width=True)


# ====================================================================
# Tab 2. 📅 캘린더 리포트
# ====================================================================
def _render_calendar_tab(df: pd.DataFrame):
    today = date.today()
    c1, c2, c3 = st.columns([1, 1, 4])
    sel_year = c1.selectbox("연도", list(range(today.year - 1, today.year + 1)),
                            index=1, key="cal_rep_year")
    sel_month = c2.selectbox("월", list(range(1, 13)),
                              index=today.month - 1, key="cal_rep_month")
    granularity = c3.radio("집계 단위", ["일간", "주간", "월간"],
                             horizontal=True, key="cal_rep_gran")

    # 월별 매출 통계 그리기
    ym = f"{sel_year}-{sel_month:02d}"
    month_df = df[df["ym"] == ym].copy()
    daily_sales = month_df[month_df["amount"] > 0].groupby(month_df["date"].dt.date)["amount"].agg(["sum", "count"])
    daily_sales = daily_sales.rename(columns={"sum": "sales", "count": "deals"})

    col_cal, col_report = st.columns([2, 3])

    with col_cal:
        st.markdown(section_header(
            f"{sel_year}.{sel_month:02d} 매출 캘린더",
            "초록 = 매출 / 회색 = 매출 없음 / 골드 = 선택"
        ), unsafe_allow_html=True)
        # 선택된 날짜 (URL session_state)
        sel_day = st.session_state.get("cal_rep_selected_day", today.day if today.month == sel_month and today.year == sel_year else 1)
        st.markdown(_render_sales_calendar(sel_year, sel_month, daily_sales, sel_day),
                    unsafe_allow_html=True)
        # 직접 날짜 선택
        max_day = cal.monthrange(sel_year, sel_month)[1]
        valid_day = min(sel_day, max_day)
        new_day = st.number_input(f"보고서 날짜 (1-{max_day})", 1, max_day, valid_day, key="cal_rep_day_input")
        st.session_state["cal_rep_selected_day"] = new_day

    with col_report:
        if granularity == "일간":
            try:
                report_date = date(sel_year, sel_month, new_day)
            except ValueError:
                st.error("잘못된 날짜")
                return
            data = daily_report_data(df, report_date)
            st.markdown(section_header(
                f"{report_date.strftime('%Y.%m.%d')} 일간 보고",
                f"매출 {daily_sales.loc[report_date]['sales']:,}원" if report_date in daily_sales.index else "매출 없음"
            ), unsafe_allow_html=True)
            if data:
                st.code(format_katalk_report(data), language="text")
            else:
                st.caption("데이터 없음")
        elif granularity == "주간":
            _render_weekly_summary(month_df, sel_year, sel_month, daily_sales, new_day)
        else:  # 월간
            _render_monthly_summary(month_df, sel_year, sel_month, daily_sales)


def _render_sales_calendar(year: int, month: int, daily_sales: pd.DataFrame, sel_day: int) -> str:
    """매출 캘린더 그리드 — 매출 있는 날 dot + 금액 표시"""
    cal_obj = cal.Calendar(firstweekday=0)
    month_days = cal_obj.monthdayscalendar(year, month)
    html = """
<style>
.rep-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
            background: #fff; border: 1px solid var(--border); border-radius: 12px;
            padding: 10px; box-shadow: var(--shadow); }
.rep-head { font-family: 'Inter',sans-serif; font-size: 11px; font-weight: 700;
            text-align: center; padding: 6px 0; color: #555;
            letter-spacing: 0.6px; text-transform: uppercase; }
.rep-head.sun { color: #D32F2F; }
.rep-head.sat { color: #1976D2; }
.rep-cell { background: #FAFAFA; border-radius: 6px; min-height: 64px;
            padding: 5px 6px; font-size: 11px; text-align: center; }
.rep-cell.empty { background: transparent; }
.rep-cell.sel { background: #C9A961; color: #fff; box-shadow: 0 0 0 2px #0A0A0A inset; }
.rep-cell.has { background: #E8F5E9; }
.rep-cell .rd-day { font-family: 'Inter',sans-serif; font-weight: 700; font-size: 12px; color: #0A0A0A; }
.rep-cell.sel .rd-day { color: #fff; }
.rep-cell .rd-amt { font-size: 10px; color: #2E7D32; font-weight: 700; margin-top: 2px; }
.rep-cell.sel .rd-amt { color: #fff; }
.rep-cell .rd-dot { width: 5px; height: 5px; border-radius: 50%; background: #2E7D32; margin: 2px auto; }
.rep-cell.sel .rd-dot { background: #fff; }
</style>
<div class="rep-grid">
"""
    weekdays = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    for i, wd in enumerate(weekdays):
        cls = "sun" if i == 6 else ("sat" if i == 5 else "")
        html += f'<div class="rep-head {cls}">{wd}</div>'
    for week in month_days:
        for day in week:
            if day == 0:
                html += '<div class="rep-cell empty"></div>'
                continue
            d_obj = date(year, month, day)
            classes = ["rep-cell"]
            amt_html = ""
            if d_obj in daily_sales.index:
                classes.append("has")
                amt = int(daily_sales.loc[d_obj]['sales'])
                if amt >= 10_000_000:
                    amt_html = f'<div class="rd-amt">₩{amt//10000:,}만</div>'
                else:
                    amt_html = '<div class="rd-dot"></div>'
            if day == sel_day:
                classes.append("sel")
            html += f'<div class="{" ".join(classes)}"><div class="rd-day">{day}</div>{amt_html}</div>'
    html += "</div>"
    return html


def _render_weekly_summary(month_df, year, month, daily_sales, focus_day):
    """주간 요약: focus_day가 속한 주 +/- 표시"""
    if not len(month_df):
        st.caption("월 데이터 없음")
        return
    target_dt = date(year, month, focus_day)
    week_start = target_dt - timedelta(days=target_dt.weekday())
    week_end = week_start + timedelta(days=6)
    st.markdown(section_header(
        f"{week_start.strftime('%m/%d')} – {week_end.strftime('%m/%d')} 주간 요약",
        f"{focus_day}일 포함 주차"
    ), unsafe_allow_html=True)
    week_df = month_df[(month_df["date"].dt.date >= week_start) & (month_df["date"].dt.date <= week_end)]
    paid = week_df[week_df["amount"] > 0]
    total_sales = int(paid["amount"].sum())
    total_entries = len(week_df)
    total_paid = len(paid)
    cols = st.columns(3)
    cols[0].metric("주간 유입", f"{total_entries}팀")
    cols[1].metric("주간 계약", f"{total_paid}건")
    cols[2].metric("주간 매출", f"₩{total_sales:,}")

    # 요일별 막대
    if len(paid):
        by_day = paid.copy()
        by_day["요일"] = by_day["date"].dt.dayofweek.map({0:"월",1:"화",2:"수",3:"목",4:"금",5:"토",6:"일"})
        agg = by_day.groupby("요일")["amount"].sum().reindex(["월","화","수","목","금","토","일"]).fillna(0)
        fig = px.bar(x=agg.index, y=agg.values, labels={"x":"요일","y":"매출(₩)"},
                     color_discrete_sequence=["#C9A961"])
        fig.update_layout(height=260, margin=dict(t=20,b=20,l=20,r=20),
                          plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)


def _render_monthly_summary(month_df, year, month, daily_sales):
    if not len(month_df):
        st.caption("월 데이터 없음")
        return
    paid = month_df[month_df["amount"] > 0]
    st.markdown(section_header(
        f"{year}년 {month}월 월간 요약",
        f"{len(paid)}건 / 누계 ₩{int(paid['amount'].sum()):,}"
    ), unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("월 유입", f"{len(month_df)}팀")
    cols[1].metric("월 계약", f"{len(paid)}건")
    cols[2].metric("월 매출", f"₩{int(paid['amount'].sum()):,}")
    cols[3].metric("객단가", f"₩{int(paid['amount'].sum()/max(len(paid),1)):,}")

    # 일자별 막대
    daily = paid.groupby(paid["date"].dt.date)["amount"].sum().reset_index()
    daily.columns = ["date", "amount"]
    if len(daily):
        fig = px.bar(daily, x="date", y="amount",
                     color_discrete_sequence=["#0A0A0A"],
                     labels={"date":"날짜","amount":"매출(₩)"})
        fig.update_layout(height=280, margin=dict(t=20,b=20,l=20,r=20),
                          plot_bgcolor="#fff", paper_bgcolor="#fff")
        st.plotly_chart(fig, use_container_width=True)


# ====================================================================
# Tab 3. 👥 고객
# ====================================================================
def _render_customers_tab(df: pd.DataFrame):
    cust = aggregate_by_customer(df)
    if not len(cust):
        st.warning("고객 데이터 없음")
        return

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    weekly_visits = int(((df["date"].dt.date >= week_ago) & (df["customer"].astype(str).str.strip() != "")).sum())
    monthly_visits = int(((df["date"].dt.date >= month_start) & (df["customer"].astype(str).str.strip() != "")).sum())

    # === KPI ===
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("총 고객", f"{len(cust):,}명", "Unique 고객", "neutral", "👥"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("이번주 방문", f"{weekly_visits:,}팀", f"{week_ago.strftime('%m/%d')}~", "gold", "📅"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("이번달 방문", f"{monthly_visits:,}팀", f"{month_start.strftime('%m')}월", "gold", "📊"), unsafe_allow_html=True)
    total_ltv = int(cust["sales"].sum())
    cols[3].markdown(black_kpi_card("누적 매출", f"₩{total_ltv/1e8:.2f}억", f"건당 ₩{total_ltv//max(len(cust),1):,}", "gold", "💎"), unsafe_allow_html=True)

    # === 필터 / 정렬 ===
    fcol1, fcol2, fcol3 = st.columns([2, 2, 3])
    cat_filter = fcol1.selectbox(
        "분류", ["전체"] + sorted(cust["category"].dropna().unique().tolist()),
        key="cust_cat"
    )
    sort_by = fcol2.selectbox(
        "정렬", ["최근순", "방문 많은순", "매출 높은순"], key="cust_sort"
    )
    search = fcol3.text_input("🔍 이름 검색", key="cust_search")

    f = cust.copy()
    if cat_filter != "전체":
        f = f[f["category"] == cat_filter]
    if search:
        f = f[f["customer"].astype(str).str.contains(search, case=False, na=False)]
    if sort_by == "최근순":
        f = f.sort_values("last_visit", ascending=False)
    elif sort_by == "방문 많은순":
        f = f.sort_values("visits", ascending=False)
    elif sort_by == "매출 높은순":
        f = f.sort_values("sales", ascending=False)

    st.caption(f"고객 {len(f):,}명 / 전체 {len(cust):,}명")

    # === 표 ===
    show = f.head(200).copy()
    show["누적"] = show["sales"].apply(lambda v: f"₩{int(v):,}" if v else "—")
    show["최근"] = show["last_visit"].apply(lambda d: d.strftime("%m/%d") if pd.notna(d) else "—")
    show = show[["customer", "phone", "category", "visits", "누적", "최근"]]
    show.columns = ["이름", "전화", "분류", "방문", "누적", "최근"]
    st.dataframe(show, hide_index=True, use_container_width=True)
    if len(f) > 200:
        st.caption(f"📜 상위 200명 표시 — 검색·필터로 좁혀보세요")


# ====================================================================
# Tab 4. 🏷 브랜드 분석
# ====================================================================
def _render_brands_tab(df: pd.DataFrame):
    brands = aggregate_by_brand(df)
    if not len(brands):
        st.warning("브랜드 멘션 데이터 없음")
        return

    st.markdown(section_header("브랜드별 분석", "언급 × 계약 × 누적금액"), unsafe_allow_html=True)

    # === KPI ===
    top_brand = brands.iloc[0]["brands"]
    top_sales_brand = brands.sort_values("sales", ascending=False).iloc[0]
    cols = st.columns(4)
    cols[0].markdown(black_kpi_card("관리 브랜드", f"{len(brands)}", "멘션된 브랜드 수", "neutral", "🏷"), unsafe_allow_html=True)
    cols[1].markdown(black_kpi_card("Top 멘션", top_brand, f"{int(brands.iloc[0]['mention_count'])}회", "gold", "💬"), unsafe_allow_html=True)
    cols[2].markdown(black_kpi_card("Top 매출", top_sales_brand['brands'], f"₩{int(top_sales_brand['sales']):,}", "gold", "💰"), unsafe_allow_html=True)
    total_paid = int(brands["paid_count"].sum())
    cols[3].markdown(black_kpi_card("총 계약 건수", f"{total_paid:,}건", "브랜드 합산", "neutral", "✍"), unsafe_allow_html=True)

    # === 가로 막대 차트 (참조 앱과 동일) ===
    chart_df = brands.head(12).sort_values("sales", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=chart_df["brands"], x=chart_df["sales"],
        orientation="h", name="누적 매출",
        marker_color="#C9A961",
        text=[f"₩{int(v/1e6):,}M" if v else "" for v in chart_df["sales"]],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        y=chart_df["brands"], x=chart_df["mention_count"] * 100_000,  # 스케일 매핑
        orientation="h", name="언급 (×100K 스케일)",
        marker_color="#0A0A0A", opacity=0.5,
    ))
    fig.update_layout(
        height=480, margin=dict(t=20, b=20, l=80, r=40),
        plot_bgcolor="#fff", paper_bgcolor="#fff",
        barmode="overlay", legend=dict(orientation="h", y=1.1),
    )
    fig.update_xaxes(gridcolor="#E8E8E8", title="누적 매출 (₩)")
    fig.update_yaxes(gridcolor="#E8E8E8")
    st.plotly_chart(fig, use_container_width=True)

    # === 표 (참조 앱 4컬럼) ===
    show = brands.copy()
    show["누적금액"] = show["sales"].apply(lambda v: f"₩{int(v):,}" if v else "—")
    show = show[["brands", "mention_count", "paid_count", "누적금액"]]
    show.columns = ["브랜드", "언급", "계약", "누적금액"]
    st.dataframe(show, hide_index=True, use_container_width=True)
