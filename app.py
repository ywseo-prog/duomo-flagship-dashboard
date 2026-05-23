"""
Duomo&Co 플래그십 통합 대시보드 v0.4 (디자인 시안 5종 반영)
- 7개 모듈 + Notion 양방향
- Streamlit Cloud / 고정 URL: duomo-flagship.streamlit.app
"""
import streamlit as st

st.set_page_config(
    page_title="Duomo Flagship Dashboard",
    page_icon="🗓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils import inject_global_css
inject_global_css()

with st.sidebar:
    st.markdown("""
<div style="padding:14px 0;border-bottom:1px solid var(--border);margin-bottom:14px">
  <div style="font-size:18px;font-weight:800;color:#0A0A0A;letter-spacing:-0.3px">■ Duomo Flagship</div>
  <div style="font-size:11px;color:#777;margin-top:2px">조명리테일팀 · v0.4</div>
</div>
    """, unsafe_allow_html=True)
    module = st.radio(
        "모듈 선택",
        options=[
            "🗓 팀 캘린더",
            "📊 업무일지",
            "💰 매출",
            "📋 제안서 관리",
            "📦 발주 상황",
            "🎬 대여",
            "🔧 AS",
            "🚢 입고 추적",
        ],
        index=0,
        label_visibility="collapsed",
    )
    st.markdown("---")
    with st.expander("ⓘ 데이터 소스"):
        st.caption("• 캘린더 · 회의록 · 주작업: Notion DB (양방향)")
        st.caption("• 업무일지: Google Sheets gviz")
        st.caption("• 매출/제안서: 업무일지 재가공")
        st.caption("• 발주: 발주시스템 v3 (외부)")
        st.caption("• AS: CS 상담이력 + 클레임노트")
        st.caption("• 입고 추적: 진행일지 .xlsx 업로드 + Notion 이력")
    with st.expander("ⓘ Notion sync"):
        st.caption("Read: 5분 캐시 자동 갱신")
        st.caption("Write: 즉시 반영 (cache.clear)")
        st.caption("토큰 미입력 시 더미 fallback")
    st.markdown("---")
    st.caption("© Duomo&Co 2026")

from modules import calendar as calendar_mod, worklog, sales, proposals, orders, rentals, as_service, inbound

ROUTES = {
    "🗓 팀 캘린더": calendar_mod.render,
    "📊 업무일지": worklog.render,
    "💰 매출": sales.render,
    "📋 제안서 관리": proposals.render,
    "📦 발주 상황": orders.render,
    "🎬 대여": rentals.render,
    "🔧 AS": as_service.render,
    "🚢 입고 추적": inbound.render,
}
ROUTES[module]()
