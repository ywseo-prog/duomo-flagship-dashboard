"""
Duomo&Co Dashboard — Design System v0.5 (Material 3 통합)
바우하우스 기능미학 × 하이엔드 리테일 × 핀테크 데이터 밀도 + M3 Tokens
"""
import streamlit as st
from datetime import datetime

# Material 3 토큰 + 기존 v0.4 컬러
from constants.material3_tokens import build_css_variables as _m3_vars


_CSS_HEAD = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

/* === Material 3 Tokens (Duomo Gold adaptation) — auto-generated === */
"""

_CSS_REST = """
/* === Duomo v0.4 Tokens (호환 유지) === */
:root {
  --bg-base: #F8F8F8;
  --bg-panel: #FFFFFF;
  --bg-dark: #0A0A0A;
  --bg-dark-soft: #1A1A1A;
  --accent-gold: #C9A961;
  --accent-orange: #FF6B35;
  --accent-green: #2E7D32;
  --accent-red: #D32F2F;
  --accent-blue: #1976D2;
  --text-primary: #0A0A0A;
  --text-secondary: #555555;
  --text-muted: #999999;
  --text-on-dark: #FFFFFF;
  --text-on-dark-soft: #BBBBBB;
  --border: #E8E8E8;
  --shadow: 0 2px 8px rgba(0,0,0,0.04);
  --radius-card: 12px;
  --radius-btn: 8px;
  --radius-badge: 4px;
}

html, body, [class*="css"], .stApp {
  font-family: 'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
  background: var(--bg-base) !important;
  color: var(--text-primary);
}
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1480px; }

h1, .duomo-h1 {
  font-family: 'Pretendard','Inter',sans-serif !important;
  font-size: 28px !important; font-weight: 800 !important;
  letter-spacing: -0.5px; color: var(--text-primary);
  border-bottom: 2px solid var(--bg-dark); padding-bottom: 8px;
  margin: 4px 0 18px 0;
}
h2 { font-size: 18px !important; font-weight: 700 !important; margin: 18px 0 10px 0 !important; }
h3 { font-size: 15px !important; font-weight: 600 !important; }

[data-testid="stSidebar"] {
  background: #fff !important; border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stRadio > label { font-size: 14px; padding: 6px 0; }

.kpi-black {
  background: var(--bg-dark); color: var(--text-on-dark);
  border-radius: var(--radius-card); padding: 22px 22px;
  box-shadow: var(--shadow);
  min-height: 130px; display: flex; flex-direction: column; justify-content: space-between;
  position: relative; overflow: hidden;
}
.kpi-black .kpi-icon {
  position: absolute; top: 14px; right: 16px; font-size: 18px; opacity: 0.6;
}
.kpi-black .kpi-label {
  font-size: 11px; font-weight: 500; letter-spacing: 0.8px;
  text-transform: uppercase; color: var(--text-on-dark-soft);
}
.kpi-black .kpi-value {
  font-family: 'Inter','Pretendard',sans-serif;
  font-size: 30px; font-weight: 800; letter-spacing: -0.5px;
  margin: 6px 0 4px 0; color: #fff;
}
.kpi-black .kpi-sub { font-size: 12px; color: var(--text-on-dark-soft); }
.kpi-black .kpi-sub.up { color: var(--accent-orange); font-weight: 600; }
.kpi-black .kpi-sub.down { color: var(--accent-red); font-weight: 600; }
.kpi-black .kpi-sub.gold { color: var(--accent-gold); font-weight: 600; }

.multi-card {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 10px 0 16px;
}
.multi-card .mc-item {
  background: #fff; border-radius: var(--radius-card);
  border: 1px solid var(--border); padding: 18px;
  box-shadow: var(--shadow); position: relative;
  border-top: 3px solid var(--accent-gold);
}
.multi-card .mc-label { font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600; }
.multi-card .mc-value { font-family: 'Inter',sans-serif; font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 6px 0 2px; letter-spacing: -0.3px; }
.multi-card .mc-sub { font-size: 11px; color: var(--text-muted); }
.multi-card .mc-trend { font-size: 11px; color: var(--accent-green); font-weight: 600; margin-top: 6px; }

.greeting {
  background: linear-gradient(135deg, #fff 0%, #FAF7F0 100%);
  border-left: 4px solid var(--accent-gold);
  padding: 16px 22px; border-radius: var(--radius-card);
  margin: 6px 0 18px 0; box-shadow: var(--shadow);
  display: flex; justify-content: space-between; align-items: center;
}
.greeting .grt-emoji { font-size: 26px; margin-right: 12px; }
.greeting .grt-text { font-family: 'Pretendard',sans-serif; font-size: 22px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.3px; }
.greeting .grt-meta { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.greeting .grt-right { text-align: right; font-size: 12px; color: var(--text-secondary); }

.section-head {
  display: flex; align-items: baseline; justify-content: space-between;
  margin: 22px 0 10px 0;
}
.section-head .sh-title {
  font-size: 16px; font-weight: 700; color: var(--text-primary);
  letter-spacing: -0.2px;
  border-left: 3px solid var(--bg-dark); padding-left: 10px;
}
.section-head .sh-sub { font-size: 11px; color: var(--text-muted); letter-spacing: 0.5px; }

.status-badge {
  display: inline-block;
  font-family: 'Inter',sans-serif;
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase;
  padding: 3px 8px; border-radius: var(--radius-badge);
  color: #fff;
}

.alert-banner {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 18px; border-radius: var(--radius-card);
  margin: 8px 0 14px 0; font-size: 13px;
  border-left: 4px solid var(--accent-orange);
  background: #FFF6F0; color: var(--text-primary);
}
.alert-banner.red { background: #FDECEC; border-color: var(--accent-red); }
.alert-banner.blue { background: #ECF3FD; border-color: var(--accent-blue); }
.alert-banner.green { background: #ECF5ED; border-color: var(--accent-green); }
.alert-banner.gold { background: #FAF4E6; border-color: var(--accent-gold); }
.alert-banner .ab-icon { font-size: 18px; }
.alert-banner .ab-title { font-weight: 700; }
.alert-banner .ab-body { color: var(--text-secondary); font-size: 12px; margin-top: 2px; }

.lb-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; background: #fff;
  border: 1px solid var(--border); border-radius: var(--radius-btn);
  margin-bottom: 6px; box-shadow: var(--shadow);
  transition: transform 0.15s;
}
.lb-row:hover { transform: translateX(2px); border-color: var(--accent-gold); }
.lb-row .lb-rank {
  font-family: 'Inter',sans-serif; font-size: 14px; font-weight: 800;
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-dark); color: #fff; margin-right: 12px;
}
.lb-row .lb-rank.top1 { background: var(--accent-gold); }
.lb-row .lb-rank.top2 { background: #B0B0B0; }
.lb-row .lb-rank.top3 { background: #CD7F32; }
.lb-row .lb-name { flex: 1; }
.lb-row .lb-name .nm { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.lb-row .lb-name .sb { font-size: 11px; color: var(--text-muted); }
.lb-row .lb-value { text-align: right; }
.lb-row .lb-value .vl { font-family: 'Inter',sans-serif; font-size: 16px; font-weight: 700; color: var(--text-primary); }
.lb-row .lb-value .vlb { font-size: 9px; color: var(--text-muted); letter-spacing: 0.8px; text-transform: uppercase; }

.report-box {
  background: #fff; border: 1px solid var(--border); border-radius: var(--radius-card);
  padding: 12px 16px; margin-bottom: 16px; box-shadow: var(--shadow);
}

div[data-testid="stMetricValue"] { font-family: 'Inter',sans-serif !important; font-weight: 800 !important; letter-spacing: -0.3px; }
div[data-testid="stMetricLabel"] { font-size: 11px !important; letter-spacing: 0.6px; text-transform: uppercase; color: var(--text-secondary) !important; }

.stButton > button {
  border-radius: var(--radius-btn); font-weight: 600;
  border: 1px solid var(--border); background: #fff;
  transition: all 0.15s;
}
.stButton > button:hover {
  background: var(--bg-dark); color: #fff; border-color: var(--bg-dark);
}

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
  font-size: 13px; font-weight: 600; padding: 8px 14px;
  background: transparent; border-radius: 0;
}
.stTabs [aria-selected="true"] {
  color: var(--text-primary) !important;
  border-bottom: 2px solid var(--bg-dark) !important;
}

/* Timeline */
.tl-item {
  display: flex; gap: 12px; padding: 10px 0;
  border-bottom: 1px dashed var(--border);
}
.tl-item:last-child { border-bottom: none; }
.tl-item .tl-bar { width: 4px; border-radius: 2px; flex-shrink: 0; }
.tl-item .tl-time { font-family: 'Inter',sans-serif; font-size: 12px; font-weight: 700; color: var(--text-secondary); min-width: 60px; }
.tl-item .tl-body { flex: 1; }
.tl-item .tl-title { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.tl-item .tl-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

/* Kanban */
.kanban-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; }
.kanban-col {
  background: #fff; border: 1px solid var(--border); border-radius: var(--radius-card);
  padding: 12px; min-height: 200px;
}
.kanban-col .kc-head {
  font-size: 11px; letter-spacing: 0.6px; text-transform: uppercase;
  color: var(--text-secondary); font-weight: 700;
  display: flex; justify-content: space-between; padding-bottom: 8px;
  border-bottom: 2px solid var(--bg-dark); margin-bottom: 10px;
}
.kanban-col .kc-count {
  font-family: 'Inter',sans-serif; background: var(--bg-dark); color: #fff;
  border-radius: 10px; padding: 1px 7px; font-size: 10px;
}
.kanban-card {
  background: #FAFAFA; border-radius: var(--radius-btn);
  padding: 8px 10px; margin-bottom: 6px; font-size: 12px;
  border-left: 3px solid var(--accent-gold);
}
.kanban-card .kk-title { font-weight: 600; color: var(--text-primary); font-size: 13px; }
.kanban-card .kk-meta { color: var(--text-muted); font-size: 10px; margin-top: 3px; }

/* 영업 보드 — 날짜별 카드 */
.sb-day {
  background: #fff; border: 1px solid var(--border); border-radius: 12px;
  margin-bottom: 14px; box-shadow: var(--shadow); overflow: hidden;
}
.sb-day-head {
  background: linear-gradient(135deg, #0A0A0A 0%, #1A1A1A 100%);
  color: #fff; padding: 12px 18px;
  display: flex; align-items: center; justify-content: space-between;
}
.sb-day-head .sd-date { font-family: 'Inter',sans-serif; font-size: 16px; font-weight: 800; letter-spacing: -0.3px; }
.sb-day-head .sd-meta { font-size: 11px; color: #BBB; letter-spacing: 0.4px; }
.sb-day-head .sd-kpi { display: flex; gap: 18px; font-size: 12px; }
.sb-day-head .sd-kpi b { font-family: 'Inter',sans-serif; font-size: 15px; color: #C9A961; margin-left: 6px; }
.sb-row {
  display: grid; grid-template-columns: 80px 70px 1fr 130px 100px;
  gap: 10px; padding: 10px 18px; align-items: flex-start;
  border-top: 1px solid #F0F0F0; font-size: 13px;
}
.sb-row:hover { background: #FAFAFA; }
.sb-row .sb-badges { display: flex; flex-direction: column; gap: 3px; }
.sb-row .sb-status { font-family: 'Inter',sans-serif; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; padding: 2px 6px; border-radius: 3px; text-align: center; }
.sb-row .sb-customer { font-weight: 600; color: #0A0A0A; font-size: 13px; }
.sb-row .sb-content { color: #555; font-size: 12px; margin-top: 3px; line-height: 1.45; }
.sb-row .sb-phone { font-family: 'Inter',sans-serif; font-size: 11px; color: #999; margin-top: 2px; }
.sb-row .sb-person { font-size: 11px; color: #777; text-align: right; }
.sb-row .sb-amount { font-family: 'Inter',sans-serif; font-size: 14px; font-weight: 700; text-align: right; color: #C9A961; }
.sb-row .sb-amount.zero { color: #BBB; font-weight: 400; }
.sb-foot {
  background: #FAFAFA; padding: 8px 18px; border-top: 1px dashed var(--border);
  font-size: 11px; color: #777;
}
.sb-foot .sf-tag { font-weight: 700; color: #555; margin-right: 6px; }

.sb-filter-bar {
  background: #fff; padding: 10px 14px; border-radius: 8px;
  border: 1px solid var(--border); margin-bottom: 12px;
  box-shadow: var(--shadow);
}

/* 업무일지 v2 — 헤더·무결성·칩·미니KPI·인라인폼 */
.wl-integrity {
  padding: 8px 14px; border-radius: 8px; margin: 6px 0 12px 0;
  font-size: 12px; display: flex; gap: 10px; align-items: center;
  border-left: 3px solid #2E7D32;
  background: #ECF5ED; color: #1B5E20;
}
.wl-integrity.warn { background: #FFF8E1; color: #B26500; border-left-color: #F57C00; }
.wl-integrity.error { background: #FDECEC; color: #B71C1C; border-left-color: #D32F2F; }
.wl-integrity .wi-icon { font-size: 16px; }
.wl-integrity .wi-gap { font-family: 'Inter',sans-serif; font-weight: 700; margin-left: 4px; }

.wl-kpi-mini {
  background: #0A0A0A; color: #fff; padding: 12px 14px;
  border-radius: 10px; box-shadow: var(--shadow);
  min-height: 84px; display: flex; flex-direction: column; justify-content: space-between;
  position: relative; overflow: hidden;
}
.wl-kpi-mini .km-icon { position: absolute; top: 8px; right: 10px; font-size: 14px; opacity: 0.45; }
.wl-kpi-mini .km-label { font-size: 10px; letter-spacing: 0.6px; text-transform: uppercase; color: #BBB; }
.wl-kpi-mini .km-value { font-family: 'Inter',sans-serif; font-size: 19px; font-weight: 800; letter-spacing: -0.3px; margin: 4px 0 2px 0; color: #fff; }
.wl-kpi-mini .km-sub { font-size: 10px; color: #BBB; }
.wl-kpi-mini .km-sub.up { color: #FF6B35; font-weight: 700; }
.wl-kpi-mini .km-sub.down { color: #FF6B35; font-weight: 700; }
.wl-kpi-mini .km-sub.gold { color: #C9A961; font-weight: 700; }

.wl-inline-form {
  background: #FFFEF7; border: 2px dashed #C9A961;
  padding: 16px 18px; border-radius: 12px; margin: 8px 0 14px 0;
}
.wl-inline-form .if-title {
  font-weight: 700; color: #0A0A0A; margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}

.wl-day-footer {
  padding: 8px 14px; background: #F5F5F5; border-radius: 8px;
  margin-top: 10px; font-size: 11.5px; color: #555;
  display: flex; justify-content: space-around; align-items: center;
}
.wl-day-footer b { color: #0A0A0A; margin-left: 4px; font-family: 'Inter',sans-serif; }

/* 페이지 헤더 액션 (greeting 옆 버튼) */
.wl-page-actions { display: flex; gap: 8px; justify-content: flex-end; }

/* 업무일지 일별 카드 — 스프레드시트 1:1 재현 */
.wl-day-meta {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 0; margin-bottom: 6px;
}
.wl-day-meta .wm-kpi { display: flex; gap: 22px; font-size: 13px; }
.wl-day-meta .wm-kpi b { font-family: 'Inter',sans-serif; color: #C9A961; margin-left: 6px; font-weight: 700; }

.wl-channel {
  margin: 10px 0 6px 0; padding-left: 8px;
  border-left: 4px solid var(--accent-gold);
  font-weight: 700; font-size: 14px; color: #0A0A0A;
}
.wl-channel.phone { border-left-color: #1976D2; }
.wl-channel.online { border-left-color: #7B1FA2; }
.wl-channel.intro { border-left-color: #F57C00; }

.wl-category {
  margin: 6px 0 4px 18px; padding-left: 10px;
  border-left: 2px dashed #BBB; font-size: 12px;
  color: #555; font-weight: 600; letter-spacing: 0.3px;
}

.wl-record {
  display: grid; grid-template-columns: 92px 1fr 110px 110px;
  gap: 10px; padding: 8px 12px; margin: 4px 0 4px 36px;
  background: #FAFAFA; border-radius: 6px;
  border-left: 3px solid #E8E8E8;
  font-size: 12.5px; align-items: flex-start;
}
.wl-record:hover { background: #F0F0F0; }
.wl-record .wr-status {
  font-family: 'Inter',sans-serif; font-size: 10px; font-weight: 700;
  letter-spacing: 0.5px; text-transform: uppercase;
  padding: 3px 8px; border-radius: 3px; color: #fff;
  text-align: center; align-self: center;
}
.wl-record .wr-body .wr-customer {
  font-weight: 700; color: #0A0A0A; font-size: 13.5px;
}
.wl-record .wr-body .wr-phone {
  font-family: 'Inter',sans-serif; font-size: 11px; color: #999;
  margin-left: 8px;
}
.wl-record .wr-body .wr-content {
  color: #555; font-size: 12px; margin-top: 3px; line-height: 1.5;
}
.wl-record .wr-body .wr-brands {
  font-size: 10px; color: #C9A961; font-weight: 600;
  letter-spacing: 0.3px; margin-top: 3px;
}
.wl-record .wr-person {
  font-size: 11px; text-align: right; padding-top: 2px;
}
.wl-record .wr-person .wp-badge {
  display: inline-block; padding: 3px 8px; border-radius: 3px;
  color: #fff; font-weight: 700; font-size: 10px;
  letter-spacing: 0.3px;
}
.wl-record .wr-amount {
  font-family: 'Inter',sans-serif; font-size: 14px; font-weight: 700;
  text-align: right; color: #C9A961;
}
.wl-record .wr-amount.zero { color: #BBB; font-weight: 400; }

.wl-memo-box {
  background: #FAF7F0; border: 1px solid #EEE6D5;
  border-radius: 8px; padding: 10px 14px; margin: 8px 0 4px 0;
  font-size: 12px; color: #5D4037;
}
.wl-memo-box.issue { background: #FDECEC; border-color: #F5C2C2; color: #5D1F1F; }
.wl-memo-box .wm-tag {
  font-weight: 700; margin-right: 8px; font-size: 11px;
  letter-spacing: 0.5px;
}

/* Funnel */
.funnel-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; margin-bottom: 6px;
  border-radius: var(--radius-btn);
  color: #fff; font-weight: 600;
}
.funnel-row .fn-stage { width: 110px; font-size: 12px; letter-spacing: 0.4px; text-transform: uppercase; }
.funnel-row .fn-bar { flex: 1; height: 8px; background: rgba(255,255,255,0.25); border-radius: 4px; overflow: hidden; }
.funnel-row .fn-fill { height: 100%; background: #fff; border-radius: 4px; }
.funnel-row .fn-value { font-family: 'Inter',sans-serif; font-size: 18px; font-weight: 800; min-width: 90px; text-align: right; }
.funnel-row .fn-pct { font-size: 11px; opacity: 0.85; min-width: 50px; text-align: right; }

/* === Material 3 Utility Classes === */
.m3-card-filled {
  background: var(--m3-surface-container-highest);
  border-radius: var(--m3-shape-medium);
  box-shadow: var(--m3-elevation-0);
  padding: 16px;
}
.m3-card-elevated {
  background: var(--m3-surface-container-low);
  border-radius: var(--m3-shape-medium);
  box-shadow: var(--m3-elevation-1);
  padding: 16px;
  transition: box-shadow var(--m3-duration-short-3) var(--m3-easing-standard);
}
.m3-card-elevated:hover { box-shadow: var(--m3-elevation-2); }
.m3-card-outlined {
  background: var(--m3-surface);
  border-radius: var(--m3-shape-medium);
  border: 1px solid var(--m3-outline-variant);
  padding: 16px;
}
.m3-chip {
  display: inline-flex; align-items: center;
  padding: 6px 12px;
  border-radius: var(--m3-shape-small);
  background: var(--m3-secondary-container);
  color: var(--m3-on-secondary-container);
  font-size: var(--m3-type-label-large-size);
  font-weight: var(--m3-type-label-large-weight);
  border: 1px solid var(--m3-outline-variant);
}
.m3-chip.assist  { background: var(--m3-surface);          color: var(--m3-on-surface); }
.m3-chip.filter  { background: var(--m3-secondary-container);color: var(--m3-on-secondary-container); }
.m3-chip.input   { background: var(--m3-surface-container); color: var(--m3-on-surface); }
.m3-chip.suggest { background: var(--m3-surface);          color: var(--m3-on-surface); border-color: var(--m3-outline); }
.m3-btn {
  padding: 10px 24px;
  border-radius: var(--m3-shape-full);
  background: var(--m3-primary);
  color: var(--m3-on-primary);
  border: none;
  font-size: var(--m3-type-label-large-size);
  font-weight: var(--m3-type-label-large-weight);
  cursor: pointer;
  box-shadow: var(--m3-elevation-0);
  transition: box-shadow var(--m3-duration-short-3) var(--m3-easing-standard);
}
.m3-btn:hover { box-shadow: var(--m3-elevation-1); }
.m3-btn.outlined { background: transparent; color: var(--m3-primary); border: 1px solid var(--m3-outline); }
.m3-btn.text     { background: transparent; color: var(--m3-primary); }
.m3-btn.tonal    { background: var(--m3-secondary-container); color: var(--m3-on-secondary-container); }
</style>
"""


def inject_global_css():
    # M3 토큰을 :root에 inject + 기존 v0.4 변수 + 컴포넌트 스타일 모두 합쳐서 한 번에 주입
    full_css = _CSS_HEAD + _m3_vars() + "\n" + _CSS_REST
    st.markdown(full_css, unsafe_allow_html=True)


# 레거시 호환 — 기존 import 경로 (`from utils.styles import CSS_GLOBAL`) 대응
CSS_GLOBAL = _CSS_HEAD + _m3_vars() + "\n" + _CSS_REST


def greeting_header(name: str, role: str = "", page_title: str = ""):
    """Finexy 시안 차용 - 좌측 인사말 + 우측 날짜"""
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12: emoji, greet = "🌅", "Good morning"
    elif 12 <= hour < 18: emoji, greet = "☀️", "Good afternoon"
    else: emoji, greet = "🌙", "Good evening"
    weekday = ["월","화","수","목","금","토","일"][now.weekday()]
    date_str = now.strftime("%Y.%m.%d") + f" · {weekday}요일"

    if page_title:
        st.markdown(f'<h1 class="duomo-h1">{page_title}</h1>', unsafe_allow_html=True)

    role_html = f'<div class="grt-meta">{role}</div>' if role else ""
    html = f"""
<div class="greeting">
  <div style="display:flex;align-items:center;">
    <div class="grt-emoji">{emoji}</div>
    <div>
      <div class="grt-text">{greet}, {name}</div>
      {role_html}
    </div>
  </div>
  <div class="grt-right">
    <div style="font-size:13px;color:var(--text-primary);font-weight:600">Today</div>
    <div>{date_str}</div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def black_kpi_card(label: str, value: str, sub: str = "", trend: str = "neutral", icon: str = ""):
    """블랙 패널 KPI 카드 - trend: up|down|gold|neutral"""
    sub_class = trend if trend in ("up","down","gold") else ""
    icon_html = f'<div class="kpi-icon">{icon}</div>' if icon else ""
    return f"""
<div class="kpi-black">
  {icon_html}
  <div class="kpi-label">{label}</div>
  <div>
    <div class="kpi-value">{value}</div>
    <div class="kpi-sub {sub_class}">{sub}</div>
  </div>
</div>
"""


def multi_card_row(cards: list):
    """시안 2 multi-wallet — cards: [{label, value, sub, color, trend}]"""
    items = ""
    for c in cards:
        color = c.get("color", "#C9A961")
        items += f"""
<div class="mc-item" style="border-top-color:{color}">
  <div class="mc-label" style="color:{color}">{c.get('label','')}</div>
  <div class="mc-value">{c.get('value','')}</div>
  <div class="mc-sub">{c.get('sub','')}</div>
  {f'<div class="mc-trend">{c["trend"]}</div>' if c.get('trend') else ''}
</div>
"""
    return f'<div class="multi-card">{items}</div>'


def status_badge_html(text: str, color: str = "#1976D2"):
    return f'<span class="status-badge" style="background:{color}">{text}</span>'


def leaderboard_row(rank: int, name: str, sub: str = "", value: str = "", value_label: str = "", color: str = "#0A0A0A"):
    rank_cls = "top1" if rank == 1 else ("top2" if rank == 2 else ("top3" if rank == 3 else ""))
    return f"""
<div class="lb-row" style="border-left:3px solid {color}">
  <div class="lb-rank {rank_cls}">{rank}</div>
  <div class="lb-name">
    <div class="nm">{name}</div>
    <div class="sb">{sub}</div>
  </div>
  <div class="lb-value">
    <div class="vl">{value}</div>
    <div class="vlb">{value_label}</div>
  </div>
</div>
"""


def section_header(title: str, sub: str = ""):
    return f"""
<div class="section-head">
  <div class="sh-title">{title}</div>
  <div class="sh-sub">{sub}</div>
</div>
"""


def alert_banner(title: str, body: str = "", level: str = "orange", icon: str = "⚠"):
    """level: orange|red|blue|green|gold"""
    cls = "" if level == "orange" else level
    return f"""
<div class="alert-banner {cls}">
  <div class="ab-icon">{icon}</div>
  <div>
    <div class="ab-title">{title}</div>
    {f'<div class="ab-body">{body}</div>' if body else ''}
  </div>
</div>
"""
