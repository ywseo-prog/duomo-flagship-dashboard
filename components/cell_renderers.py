"""AG-Grid JsCode 셀 렌더러 — 스펙 인계 6종 verbatim (그 외 없음)"""
from st_aggrid import JsCode


# (1) 채널 배지
CHANNEL_BADGE = JsCode("""
function(p){
  if(!p.value) return '';
  const c={'내방':{bg:'#B5D4F4',fg:'#185FA5'},'유선':{bg:'#9FE1CB',fg:'#0F6E56'}};
  const s=c[p.value]||{bg:'#999',fg:'white'};
  return `<span style="display:inline-flex;align-items:center;justify-content:center;
    padding:3px 12px;border-radius:14px;font-size:11px;font-weight:500;
    background:${s.bg};color:${s.fg}">${p.value}</span>`;
}
""")


# (2) 카테고리 배지
CATEGORY_BADGE = JsCode("""
function(p){
  if(!p.value) return '';
  return `<span style="display:inline-flex;align-items:center;justify-content:center;
    padding:3px 12px;border-radius:14px;font-size:11px;font-weight:500;
    background:#FAC775;color:#854F0B">${p.value}</span>`;
}
""")


# (3) 상태 셀 클래스 룰 (cellClassRules)
STATUS_CLASS_RULES = {
    "status-done":  "params.value === 'done'",
    "status-ing":   "params.value === 'ing'",
    "status-paid":  "params.value === '결제 완료'",
    "status-todo":  "params.value === 'to do'",
}


# (4) 결제 완료 시 금액 강조
AMOUNT_CELL_STYLE = JsCode("""
function(p){
  const status = p.data?.status;
  if(status === '결제 완료'){
    return {background:'#FCEBEB',color:'#A32D2D',fontWeight:500,textAlign:'right'};
  }
  return {textAlign:'right',color:'#185FA5'};
}
""")


# (5) row_type별 배경 (진행사항/이슈사항)
ROW_STYLE = JsCode("""
function(p){
  if(p.data?.row_type === 'progress') return {background:'#FBF7EE'};
  if(p.data?.row_type === 'issue')    return {background:'#FBF7EE'};
  return null;
}
""")


# (6) 일자 헤더 그룹 렌더러 (이전 가이드 참조)
DATE_HEADER_RENDERER = JsCode("""
class DateHeaderRenderer {
  init(p){
    const m = p.node.allLeafChildren?.[0]?.data?._meta;
    this.eGui = document.createElement('div');
    if(!m){ return; }
    this.eGui.style.cssText = 'display:flex;gap:20px;padding:8px 12px;background:#F5F5F0;font-weight:500;font-size:13px;';
    this.eGui.innerHTML = `
      <span>${p.value} (${m.weekday})</span>
      <span style="color:#5F5E5A">담당: ${m.persons.join('·')}</span>
      <span style="color:#5F5E5A">내방: ${m.visitor_teams||0}팀</span>
      <span style="color:#C9A961">결제: ₩${(m.total_sales||0).toLocaleString()}</span>
    `;
  }
  getGui(){ return this.eGui; }
}
""")
