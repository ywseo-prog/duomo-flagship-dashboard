"""HTML 양식 동적 생성 — parse_worklog_v2 dict의 일자 블록을 시트 1:1 시각으로.

사용자 인계 mockup (worklog_entry_form_5_22.html)을 Python 템플릿화.
CSS var(--color-*)는 고정 컬러로 변환 (iframe 임베드 호환).

[흐름]
- render_worklog_html(parsed, target_date) → str
- modules/worklog.py에서 st.components.v1.html() 로 임베드
"""
from __future__ import annotations
from datetime import date
import html as _html


STATUSES = ["done", "ing", "결제 완료", "to do"]
PERSONS = ["서영완 선임", "조이경 사원", "추승민 선임", "신민정 사원"]

STATUS_CSS = {
    "done": "s-done",
    "ing": "s-ing",
    "결제 완료": "s-paid",
    "결제완료": "s-paid",
    "to do": "s-todo",
    "todo": "s-todo",
    "": "s-todo",
}


_CSS = """
<style>
.wl{font-family:'Pretendard','Inter',sans-serif;font-size:13px;color:#1a1a1a;background:#fff;border-radius:8px;border:0.5px solid #e5e5e5;overflow:hidden}
.wl table{width:100%;border-collapse:collapse;table-layout:fixed}
.wl th,.wl td{border:0.5px solid #eee;padding:4px 6px;vertical-align:middle;text-align:center;font-weight:400}
.wl thead th{background:#f5f5f0;font-size:12px;color:#555;padding:10px 6px;font-weight:500}
.wl .date-label{background:#f9f9f9;font-weight:500;text-align:center}
.wl .date-val{background:#f9f9f9;font-weight:500;font-size:14px}
.wl .cat-label{background:#f9f9f9;font-weight:500;text-align:left;padding-left:14px;color:#555}
.wl .total-amt{background:#f9f9f9;font-weight:500;color:#185FA5;text-align:right;padding-right:12px;font-size:14px}
.wl .ch-cell{background:#f9f9f9;padding:4px}
.wl .cat-cell{background:#f9f9f9;padding:4px}
.wl input,.wl select{width:100%;height:28px;border:0.5px solid #eee;border-radius:4px;padding:0 6px;font-size:12px;background:transparent;color:#1a1a1a;font-family:inherit}
.wl input:focus,.wl select:focus{outline:none;border-color:#185FA5;background:#fff}
.wl input::placeholder{color:#999}
.wl .content-cell input{text-align:left}
.wl .row-amount input{text-align:right;color:#185FA5;font-weight:500}
.badge{display:inline-flex;align-items:center;justify-content:center;padding:3px 12px;border-radius:14px;font-size:11px;font-weight:500;min-width:48px;line-height:1.5}
.b-naebang{background:#B5D4F4;color:#185FA5}
.b-yuseon{background:#9FE1CB;color:#0F6E56}
.b-cat{background:#FAC775;color:#854F0B}
.wl select.st{height:26px;border-radius:14px;font-weight:500;font-size:11px;text-align:center;text-align-last:center;padding:0 4px;cursor:pointer;border-width:0.5px}
.st.s-done{background:#E6F1FB;color:#185FA5;border-color:#85B7EB}
.st.s-ing{background:#FAEEDA;color:#854F0B;border-color:#FAC775}
.st.s-paid{background:#FCEBEB;color:#A32D2D;border-color:#F09595}
.st.s-todo{background:#F1EFE8;color:#444441;border-color:#D3D1C7}
.wl select.pp{height:26px;border-radius:14px;font-weight:500;font-size:11px;text-align:center;text-align-last:center;padding:0 6px;cursor:pointer;background:#FBEAF0;color:#993556;border:0.5px solid #ED93B1}
.wl .progress-row td,.wl .issue-row td{background:#FBF7EE}
.wl .progress-row .lbl,.wl .issue-row .lbl{background:#FAC775;color:#854F0B;font-weight:500;font-size:11px}
.wl .toolbar{display:flex;gap:8px;padding:12px;background:#f5f5f0;border-bottom:0.5px solid #ddd;align-items:center}
.wl .toolbar .spacer{flex:1}
.wl .toolbar .info{font-size:12px;color:#555}
.wl .toolbar .info b{color:#1a1a1a;font-weight:600}
</style>
"""


_SCRIPT = """
<script>
function updateStatus(sel){
  sel.classList.remove('s-done','s-ing','s-paid','s-todo');
  const v = sel.value;
  if(v==='done') sel.classList.add('s-done');
  else if(v==='ing') sel.classList.add('s-ing');
  else if(v==='결제 완료') sel.classList.add('s-paid');
  else sel.classList.add('s-todo');
  const row = sel.closest('tr');
  const amt = row.querySelector('.row-amount input');
  if(amt){
    if(v==='결제 완료'){ amt.style.background='#FCEBEB'; amt.style.color='#A32D2D'; amt.focus(); }
    else { amt.style.background='transparent'; amt.style.color='#185FA5'; }
  }
}
</script>
"""


def _esc(v) -> str:
    if v is None: return ""
    return _html.escape(str(v))


def _status_select(current: str) -> str:
    css_class = STATUS_CSS.get(current, "s-todo")
    norm = current if current in STATUSES else "to do"
    opts = []
    for opt in STATUSES:
        sel = " selected" if opt == norm else ""
        opts.append(f'<option value="{opt}"{sel}>{opt}</option>')
    return f'<select class="st {css_class}" onchange="updateStatus(this)">{"".join(opts)}</select>'


def _person_select(current_raw: str) -> str:
    opts = []
    matched = False
    for opt in PERSONS:
        sel = ""
        if not matched and opt in str(current_raw or ""):
            sel = " selected"; matched = True
        opts.append(f'<option{sel}>{opt}</option>')
    if not matched:
        opts.insert(0, '<option value="">담당자</option>')
    return f'<select class="pp">{"".join(opts)}</select>'


def _amount_input(amount: int, is_paid: bool) -> str:
    if amount and amount > 0:
        val = f"₩{int(amount):,}"
        return f'<input value="{val}">'
    return '<input placeholder="">'


def render_worklog_html(parsed: dict, target_date: date) -> str:
    """parse_worklog_v2 dict → 시트 1:1 HTML 양식."""
    d_iso = target_date.isoformat()
    block = next((d for d in parsed.get("dates", []) if d["date"] == d_iso), None)

    header = parsed.get("header", {})
    target = header.get("month_target", 0) or 0
    rate = (header.get("achievement") or 0) * 100
    month = header.get("month", target_date.month)

    toolbar_info = f"{month}월 목표 ₩{target:,} · 달성률 {rate:.2f}%"

    if not block:
        return f"""
{_CSS}
<div class="wl">
  <div class="toolbar">
    <span class="info"><b>{target_date.year}.{target_date.month}.{target_date.day}</b> 데이터 없음</span>
    <div class="spacer"></div>
    <span class="info">{_esc(toolbar_info)}</span>
  </div>
</div>
"""

    weekday = block["meta"]["weekday"]
    visitor_teams = block["meta"]["visitor_teams"] or len(block["records"])
    total_sales = block["meta"]["total_sales"]
    records = block["records"]
    progress = block.get("progress", [])
    issues = block.get("issues", [])
    date_str = f"{target_date.year}.{target_date.month}.{target_date.day} ({weekday})"

    # 채널·카테고리 grouping (forward-fill)
    grouped: dict = {}
    cur_ch, cur_cat = "", ""
    for r in records:
        ch = r.get("channel") or cur_ch or "(미지정)"
        cat = r.get("category") or cur_cat or "(미지정)"
        cur_ch, cur_cat = ch, cat
        grouped.setdefault(ch, {}).setdefault(cat, []).append(r)

    # 채널·카테고리 순서 보장
    channel_order = {"내방": 0, "유선": 1, "온라인": 2, "소개": 3}
    category_order = {"소비자": 0, "업체": 1, "디자이너": 2}
    ordered_channels = sorted(grouped.keys(), key=lambda c: channel_order.get(c, 9))

    # tbody 생성
    tbody = ""
    for channel in ordered_channels:
        cats = grouped[channel]
        ch_total = sum(len(rs) for rs in cats.values())
        ch_class = "b-naebang" if channel == "내방" else ("b-yuseon" if channel == "유선" else "b-cat")
        first_ch_row = True
        ordered_cats = sorted(cats.keys(), key=lambda c: category_order.get(c, 9))
        for category in ordered_cats:
            rows = cats[category]
            first_cat_row = True
            for r in rows:
                tbody += "<tr>"
                if first_ch_row:
                    tbody += f'<td rowspan="{ch_total}" class="ch-cell"><span class="badge {ch_class}">{_esc(channel)}</span></td>'
                    first_ch_row = False
                if first_cat_row:
                    tbody += f'<td rowspan="{len(rows)}" class="cat-cell"><span class="badge b-cat">{_esc(category)}</span></td>'
                    first_cat_row = False
                # status
                tbody += f"<td>{_status_select(r.get('status') or '')}</td>"
                # customer / phone / content
                tbody += f'<td><input placeholder="고객명" value="{_esc(r.get("customer"))}"></td>'
                tbody += f'<td><input placeholder="010-0000-0000" value="{_esc(r.get("phone"))}"></td>'
                tbody += f'<td class="content-cell"><input placeholder="내용" value="{_esc(r.get("content"))}"></td>'
                # person
                tbody += f"<td>{_person_select(r.get('person_raw') or '')}</td>"
                # amount
                amount = int(r.get("amount") or 0)
                is_paid = (r.get("status") or "").strip() in ("결제 완료", "결제완료")
                tbody += f'<td class="row-amount">{_amount_input(amount, is_paid)}</td>'
                tbody += "</tr>"

    # 진행/이슈사항
    for p in progress:
        tbody += f'<tr class="progress-row"><td colspan="2" class="lbl">진행사항</td><td colspan="5"><input style="text-align:left" value="{_esc(p)}"></td><td>{_person_select("")}</td></tr>'
    if not progress:
        tbody += f'<tr class="progress-row"><td colspan="2" class="lbl">진행사항</td><td colspan="5"><input style="text-align:left" placeholder="당일 진행사항 입력"></td><td>{_person_select("")}</td></tr>'
    for i in issues:
        tbody += f'<tr class="issue-row"><td colspan="2" class="lbl">이슈사항</td><td colspan="5"><input style="text-align:left" value="{_esc(i)}"></td><td>{_person_select("")}</td></tr>'
    if not issues:
        tbody += f'<tr class="issue-row"><td colspan="2" class="lbl">이슈사항</td><td colspan="5"><input style="text-align:left" placeholder="이슈사항 입력"></td><td>{_person_select("")}</td></tr>'

    return f"""
{_CSS}
<div class="wl">
  <div class="toolbar">
    <span class="info"><b>{date_str}</b></span>
    <div class="spacer"></div>
    <span class="info">{_esc(toolbar_info)}</span>
  </div>
  <table>
    <colgroup>
      <col style="width:48px"><col style="width:60px">
      <col style="width:96px"><col style="width:110px"><col style="width:108px">
      <col><col style="width:108px"><col style="width:100px">
    </colgroup>
    <thead>
      <tr>
        <th colspan="2" class="date-label">날짜</th>
        <th colspan="2" class="date-val">{date_str}</th>
        <th colspan="2">내방객(팀)</th>
        <th>{visitor_teams}</th>
        <th>결제 금액</th>
      </tr>
      <tr>
        <td colspan="2" class="cat-label">카테고리</td>
        <td colspan="5"></td>
        <td class="total-amt">₩{total_sales:,}</td>
      </tr>
    </thead>
    <tbody>
      {tbody}
    </tbody>
  </table>
</div>
{_SCRIPT}
"""


def estimate_height(parsed: dict, target_date: date) -> int:
    """동적 iframe 높이 산정 (rough)"""
    d_iso = target_date.isoformat()
    block = next((d for d in parsed.get("dates", []) if d["date"] == d_iso), None)
    base = 200  # toolbar + thead + progress + issue
    if not block:
        return base
    n_rows = len(block["records"]) + len(block.get("progress", [])) + len(block.get("issues", []))
    if not block.get("progress"): n_rows += 1  # placeholder
    if not block.get("issues"): n_rows += 1
    return base + n_rows * 36
