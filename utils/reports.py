"""
공통 리포트 다운로드 모듈
- 일·월·연 단위 PDF/Excel 자동 생성
- 모듈별로 호출: render_report_section(module_name, df, period_col='date')
"""
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import date, timedelta

def render_report_section(module_name: str, df: pd.DataFrame = None, period_col: str = "date"):
    """모듈 상단 리포트 다운로드 영역 (공통 helper)"""
    st.markdown(f'<div class="report-box">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    period = c1.selectbox(
        "📥 리포트 기간",
        ["일일", "주간", "월간", "분기", "연간", "사용자지정"],
        key=f"period_{module_name}",
    )
    today = date.today()
    if period == "일일":
        start = end = today
    elif period == "주간":
        start = today - timedelta(days=7); end = today
    elif period == "월간":
        start = today.replace(day=1); end = today
    elif period == "분기":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = today.replace(month=q_start_month, day=1); end = today
    elif period == "연간":
        start = today.replace(month=1, day=1); end = today
    else:
        d1 = c1.date_input("시작", today - timedelta(days=30), key=f"d1_{module_name}")
        d2 = c1.date_input("종료", today, key=f"d2_{module_name}")
        start, end = d1, d2

    c2.metric("기간", f"{start} ~ {end}")
    fmt = c3.selectbox("포맷", ["Excel", "PDF (BLUF)", "PPT"], key=f"fmt_{module_name}")

    if c4.button("📥 다운로드", key=f"dl_{module_name}", use_container_width=True):
        if df is None or not len(df):
            st.warning("데이터 없음")
        else:
            # 기간 필터
            if period_col in df.columns:
                df_p = df[(df[period_col] >= pd.Timestamp(start)) & (df[period_col] <= pd.Timestamp(end))]
            else:
                df_p = df
            if fmt == "Excel":
                buf = generate_excel_report(module_name, df_p, period, start, end)
                st.download_button(
                    label=f"⬇ {module_name}_{period}_{end}.xlsx",
                    data=buf, file_name=f"{module_name}_{period}_{end}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"final_{module_name}",
                )
            elif fmt == "PDF (BLUF)":
                buf = generate_pdf_report(module_name, df_p, period, start, end)
                st.download_button(
                    label=f"⬇ {module_name}_{period}_{end}.pdf",
                    data=buf, file_name=f"{module_name}_{period}_{end}.pdf",
                    mime="application/pdf", key=f"final_{module_name}",
                )
            else:
                st.info("PPT 생성은 python-pptx 통합 시 자동 활성화. 현재 Excel/PDF 우선 지원.")
    st.markdown("</div>", unsafe_allow_html=True)


def generate_excel_report(module_name, df, period, start, end):
    """모듈별 Excel 리포트 생성"""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Sheet 1: 요약
        summary = pd.DataFrame([
            {"항목": "모듈", "값": module_name},
            {"항목": "리포트 기간", "값": f"{period} ({start} ~ {end})"},
            {"항목": "총 레코드", "값": len(df)},
            {"항목": "생성 일시", "값": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")},
        ])
        summary.to_excel(writer, sheet_name="요약", index=False)
        # Sheet 2: 원본
        if len(df):
            df.to_excel(writer, sheet_name="데이터", index=False)
        # Sheet 3: 집계 (매출 컬럼 있으면)
        if "amount" in df.columns:
            agg = df.groupby(df.get("ym", df.get("date", pd.Series()).astype(str).str[:7]))["amount"].agg(["sum","count","mean"]).reset_index()
            agg.columns = ["기간","합계","건수","평균"]
            agg.to_excel(writer, sheet_name="기간별집계", index=False)
    buf.seek(0)
    return buf


def generate_pdf_report(module_name, df, period, start, end):
    """간이 PDF 리포트 (BLUF 1페이지) — reportlab 사용"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
        font = "HeiseiMin-W3"
    except Exception:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        font = "Helvetica"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont(font, 16)
    c.drawString(40, h - 50, f"■ {module_name} 리포트 ({period})")
    c.setFont(font, 10)
    c.drawString(40, h - 70, f"Period: {start} ~ {end}  /  Records: {len(df)}")
    c.line(40, h - 80, w - 40, h - 80)

    # 핵심 지표
    c.setFont(font, 11)
    y = h - 110
    c.drawString(40, y, "[Key Metrics]")
    y -= 18
    c.setFont(font, 10)
    if "amount" in df.columns and len(df):
        total = int(df["amount"].sum())
        paid_cnt = int((df["amount"] > 0).sum())
        avg = total // paid_cnt if paid_cnt else 0
        c.drawString(50, y, f"- Total Sales : KRW {total:,}"); y -= 14
        c.drawString(50, y, f"- Paid Count  : {paid_cnt:,}"); y -= 14
        c.drawString(50, y, f"- Avg Ticket  : KRW {avg:,}"); y -= 14
    c.drawString(50, y, f"- Total Entries : {len(df):,}"); y -= 14

    # 푸터
    c.setFont(font, 8)
    c.drawString(40, 30, f"Generated by Duomo Flagship Dashboard / {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf
