"""모듈 2: 업무일지 v1.2 — HTML 양식 1:1 임베드 (스펙 인계 mockup)

[목표]
사용자가 제공한 mockup (worklog_entry_form_5_22.html)의 시각을 그대로 재현.
- 시트 1:1 rowspan 양식
- 라운드 배지 (내방·유선·카테고리·현황·담당자)
- 결제 완료 시 매출 셀 자동 강조
- toolbar (날짜 정보 + 월 목표 + 달성률)

[아키텍처]
- components.render_worklog_html(parsed, date) → str (시트 1:1 HTML 동적 생성)
- st.components.v1.html() 로 iframe 임베드 (CSS·JS·라운드 배지 100% 적용)
- 행 추가·저장은 Streamlit 측 사이드 폼 (iframe ↔ 부모 통신 한계 회피)

[데이터]
- parsers.load_worklog_v2() → dict
- services.append_row / push_changes → 시트 sync
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime, timedelta

from parsers import load_worklog_v2, load_monthly_target
from services.sheets_sync import (
    has_service_account, append_row, push_changes,
)
from components import (
    render_worklog_html, estimate_height,
    HTML_STATUSES as STATUSES,
    HTML_PERSONS as PERSONS,
)
from constants.design_tokens import CHANNELS, CATEGORIES

# Streamlit native 컴포넌트 (KPI 등)
from utils.styles import (
    greeting_header, black_kpi_card, section_header, alert_banner,
)


def render():
    # ── 헤더 ──
    greeting_header(
        "서영완", role="조명플래그십파트 · 업무일지 (HTML 양식 1:1)",
        page_title="📊 업무일지",
    )

    parsed = load_worklog_v2(source="auto")
    if not parsed.get("dates"):
        st.error("본사 시트 로드 실패")
        return
    target_info = load_monthly_target()

    # ── KPI 1줄 (블랙 패널) ──
    _render_kpi(parsed.get("header") or {}, target_info)

    # ── 일자 네비 ──
    avail_dates = sorted([d["date"] for d in parsed["dates"]], reverse=True)
    today_iso = date.today().isoformat()
    default_date_str = today_iso if today_iso in avail_dates else (avail_dates[0] if avail_dates else today_iso)
    try:
        default_date_obj = datetime.strptime(default_date_str, "%Y-%m-%d").date()
    except ValueError:
        default_date_obj = date.today()

    nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([1, 2, 1, 4])
    if nav_c1.button("◀ 이전", use_container_width=True, key="wl_prev"):
        try:
            idx = avail_dates.index(st.session_state.get("wl_date_iso", default_date_str))
            if idx < len(avail_dates) - 1:
                st.session_state["wl_date_iso"] = avail_dates[idx + 1]
        except ValueError:
            pass
        st.rerun()
    sel_date = nav_c2.date_input(
        "조회 일자", value=datetime.strptime(
            st.session_state.get("wl_date_iso", default_date_str), "%Y-%m-%d"
        ).date(),
        key="wl_date_picker", label_visibility="collapsed",
    )
    if sel_date.isoformat() != st.session_state.get("wl_date_iso", default_date_str):
        st.session_state["wl_date_iso"] = sel_date.isoformat()
    if nav_c3.button("다음 ▶", use_container_width=True, key="wl_next"):
        try:
            idx = avail_dates.index(st.session_state.get("wl_date_iso", default_date_str))
            if idx > 0:
                st.session_state["wl_date_iso"] = avail_dates[idx - 1]
        except ValueError:
            pass
        st.rerun()
    nav_c4.caption(f"📂 {len(avail_dates)} 일자 보유 · 가장 최근 {avail_dates[0] if avail_dates else '—'}")

    # ── HTML 양식 임베드 (시트 1:1 시각) ──
    html_str = render_worklog_html(parsed, sel_date)
    h = estimate_height(parsed, sel_date)
    components.html(html_str, height=h, scrolling=True)

    # ── Service Account 상태 ──
    sa_active = has_service_account()
    if sa_active:
        st.caption("✓ Service Account 활성 — 행 추가/저장 시 본사 시트 자동 동기화")
    else:
        st.caption("⚠ Service Account 미설정 — 행 추가/저장 시 TSV 출력만 (수동 시트 붙여넣기)")

    # ── 행 추가 + 저장 (Streamlit 측 사이드 폼) ──
    st.markdown(section_header(
        "➕ 행 추가 / 편집 (iframe 안 입력은 시각 미리보기, 실제 저장은 아래 폼)",
        "본사 시트에 새 행을 즉시 append. 동일 일자 블록이면 그 안에 추가, 새 일자면 블록 신규 생성."
    ), unsafe_allow_html=True)

    add_tabs = st.tabs(["내방·소비자", "내방·업체", "유선·소비자", "유선·업체"])
    for i, (ch, cat) in enumerate([("내방", "소비자"), ("내방", "업체"),
                                     ("유선", "소비자"), ("유선", "업체")]):
        with add_tabs[i]:
            _render_add_form(ch, cat, sel_date, key_suffix=f"{i}")


def _render_kpi(header: dict, target_info: dict | None):
    today = date.today()
    target_v = header.get("month_target") or (target_info.get("target") if target_info else 0) or 0
    current_v = header.get("current_total") or 0
    rate_v = (header.get("achievement") or 0) * 100
    if not rate_v and target_v:
        rate_v = current_v / target_v * 100
    month_v = header.get("month", today.month)

    cols = st.columns(4)
    with cols[0]:
        if target_v:
            st.markdown(black_kpi_card(
                f"{month_v}월 목표", f"₩{target_v/1e8:.2f}억",
                "본사 시트 헤더", "gold", "🎯",
            ), unsafe_allow_html=True)
        else:
            st.markdown(black_kpi_card("목표", "—", "미입력", "neutral", "🎯"),
                        unsafe_allow_html=True)
    with cols[1]:
        st.markdown(black_kpi_card(
            "금일 누계 매출", f"₩{current_v/1e8:.2f}억",
            "본사 시트 헤더", "gold", "💰",
        ), unsafe_allow_html=True)
    with cols[2]:
        from calendar import monthrange
        days_in_month = monthrange(today.year, today.month)[1]
        pace = today.day / days_in_month * 100
        trend = "up" if rate_v >= pace else "down"
        st.markdown(black_kpi_card(
            "달성률", f"{rate_v:.2f}%",
            f"진척 {pace:.0f}%", trend, "📊",
        ), unsafe_allow_html=True)
    with cols[3]:
        active_days = max(today.day - 1, 1)
        daily_avg = current_v // max(active_days, 1) if current_v else 0
        st.markdown(black_kpi_card(
            "일평균 매출", f"₩{daily_avg/1e6:.1f}M",
            f"활성 {active_days}일", "gold", "📈",
        ), unsafe_allow_html=True)


def _render_add_form(channel: str, category: str, target_date: date, key_suffix: str):
    """행 추가 폼 — 채널·카테고리 고정, 나머지 필드 입력 → 시트 append."""
    with st.form(f"add_form_{key_suffix}", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1.5, 1.5])
        f_status = c1.selectbox("현황", STATUSES, index=3, key=f"st_{key_suffix}")
        f_customer = c2.text_input(
            "고객 / 업체명",
            placeholder="예) 단체 가족 / 김아름 사원" if category == "소비자" else "예) 아울디자인 / 강동현",
            key=f"cust_{key_suffix}",
        )
        f_phone = c3.text_input("연락처", placeholder="010-0000-0000", key=f"ph_{key_suffix}")

        f_content = st.text_area("내용", placeholder="상담 내용", height=70, key=f"ct_{key_suffix}")

        c4, c5 = st.columns([1.5, 1])
        f_person = c4.selectbox("담당자", PERSONS, key=f"per_{key_suffix}")
        f_amount = c5.number_input("매출(원)", min_value=0, step=10_000, value=0, key=f"amt_{key_suffix}")

        submit = st.form_submit_button(
            f"💾 {channel}·{category} 행 추가 (본사 시트 즉시 반영)",
            type="primary", use_container_width=True,
        )

    if submit:
        if not f_customer.strip():
            st.error("고객명 필수")
            return
        record = {
            "channel": channel, "category": category,
            "status": f_status, "customer": f_customer.strip(),
            "phone": f_phone.strip(), "content": f_content.strip(),
            "person": f_person.strip(), "amount": f_amount if f_amount > 0 else "",
        }
        with st.spinner("본사 시트에 append 중..."):
            result = append_row(record, target_date)
        if result.get("ok"):
            st.success(f"✓ {target_date.isoformat()} 블록에 {channel}·{category} 행 추가됨 (행 {result.get('row')})")
            st.balloons()
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning(f"⚠ 자동 write 미실행: {result.get('error', '')}")
            if result.get("header_tsv"):
                st.caption("📌 새 날짜 블록 헤더:")
                st.code(result["header_tsv"], language="text")
            st.caption("📌 데이터 행 (시트에 붙여넣기):")
            st.code(result["tsv"], language="text")
