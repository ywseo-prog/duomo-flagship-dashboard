"""
Duomo&Co Dashboard — Design System v0.4 components
바우하우스 기능미학 × 하이엔드 리테일 × 핀테크 데이터 밀도
"""
import streamlit as st
from datetime import datetime


CSS_GLOBAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

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
</style>
"""


def inject_global_css():
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)


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
