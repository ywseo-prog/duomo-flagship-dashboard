"""Duomo Flagship 업무일지 v1.0 — 디자인 토큰 (스펙 인계)

[컬러 팔레트]
- channel: 내방(블루) / 유선(민트)
- category: 소비자·업체 공통 골드 (소프트)
- status: done(연블루) / ing(연옐로우) / 결제 완료(연핑크) / to do(연그레이)
- person: 통합 핑크 배지
- footer: 일자 헤더용 베이지

[고정 옵션]
- PERSONS 4인 (직책 포함)
- STATUSES 4종
- CHANNELS 2종 (내방·유선)
- CATEGORIES 2종 (소비자·업체)
"""

COLORS = {
    "channel": {
        "내방": {"bg": "#B5D4F4", "fg": "#185FA5"},
        "유선": {"bg": "#9FE1CB", "fg": "#0F6E56"},
    },
    "category": {
        "소비자": {"bg": "#FAC775", "fg": "#854F0B"},
        "업체":   {"bg": "#FAC775", "fg": "#854F0B"},
    },
    "status": {
        "done":      {"bg": "#E6F1FB", "fg": "#185FA5", "border": "#85B7EB"},
        "ing":       {"bg": "#FAEEDA", "fg": "#854F0B", "border": "#FAC775"},
        "결제 완료": {"bg": "#FCEBEB", "fg": "#A32D2D", "border": "#F09595"},
        "to do":     {"bg": "#F1EFE8", "fg": "#444441", "border": "#D3D1C7"},
    },
    "person": {"bg": "#FBEAF0", "fg": "#993556", "border": "#ED93B1"},
    "footer": {"bg": "#FBF7EE", "label_bg": "#FAC775", "label_fg": "#854F0B"},
}

# 폼·드롭다운 옵션 (직책 포함, 시트와 동일)
PERSONS = [
    "서영완 선임",
    "조이경 사원",
    "추승민 선임",
    "신민정 사원",
]

# 상태 4종 — done / ing / 결제 완료 / to do
STATUSES = ["done", "ing", "결제 완료", "to do"]

# 채널·카테고리 단순화 (2종씩)
CHANNELS = ["내방", "유선"]
CATEGORIES = ["소비자", "업체"]


# ag-theme-streamlit 그리드용 CSS — modules/worklog.py 진입 시 inject
# 스펙 verbatim: status 4종 + person-cell 라운드 배지 (단순화)
GRID_CSS = """
<style>
.ag-theme-streamlit .status-done {background:#E6F1FB; color:#185FA5; border-radius:14px;}
.ag-theme-streamlit .status-ing  {background:#FAEEDA; color:#854F0B; border-radius:14px;}
.ag-theme-streamlit .status-paid {background:#FCEBEB; color:#A32D2D; border-radius:14px;}
.ag-theme-streamlit .status-todo {background:#F1EFE8; color:#444441; border-radius:14px;}
.ag-theme-streamlit .person-cell {background:#FBEAF0; color:#993556; border-radius:14px;}
</style>
"""
