"""AG-Grid JsCode 셀 렌더러 v1.0 — constants/design_tokens 컬러 적용

[6종 렌더러]
1. CHANNEL_BADGE   — 내방(블루) / 유선(민트) pill
2. CATEGORY_BADGE  — 골드 pill
3. STATUS_CLASS_RULES — cellClassRules dict (CSS로 색칠)
4. AMOUNT_CELL_STYLE — 결제 완료 시 핑크 강조, 기본 블루
5. ROW_STYLE       — 진행/이슈 행 베이지 배경
6. DATE_HEADER_RENDERER — 일자 그룹 헤더 (담당자/내방팀수/결제금액)

[추가]
7. PERSON_BADGE    — 4인 통합 핑크 배지 (fallback)
"""
from st_aggrid import JsCode


# ============================================================
# 1. 채널 배지 — 내방(연블루) / 유선(민트)
# ============================================================
CHANNEL_BADGE = JsCode("""
function(p){
  if(!p.value) return '';
  const c = {
    '내방': {bg:'#B5D4F4', fg:'#185FA5'},
    '유선': {bg:'#9FE1CB', fg:'#0F6E56'}
  };
  const s = c[String(p.value).trim()] || {bg:'#999', fg:'#fff'};
  return `<span style="display:inline-flex;align-items:center;justify-content:center;
    padding:3px 12px;border-radius:14px;font-size:11px;font-weight:500;
    background:${s.bg};color:${s.fg}">${p.value}</span>`;
}
""")


# ============================================================
# 2. 카테고리 배지 — 소비자·업체 공통 골드
# ============================================================
CATEGORY_BADGE = JsCode("""
function(p){
  if(!p.value) return '';
  return `<span style="display:inline-flex;align-items:center;justify-content:center;
    padding:3px 12px;border-radius:14px;font-size:11px;font-weight:500;
    background:#FAC775;color:#854F0B">${p.value}</span>`;
}
""")


# ============================================================
# 3. 상태 cellClassRules — CSS 클래스 매핑
# ============================================================
STATUS_CLASS_RULES = {
    "status-done": "params.value === 'done'",
    "status-ing":  "params.value === 'ing'",
    "status-paid": "params.value === '결제 완료' || params.value === '결제완료'",
    "status-todo": "params.value === 'to do' || params.value === 'todo' || params.value === 'TO DO'",
}


# ============================================================
# 4. 금액 셀 동적 스타일 — 결제 완료 시 핑크, 기본 블루
# ============================================================
AMOUNT_CELL_STYLE = JsCode("""
function(p){
  const status = p.data?.status || p.data?.['현황'] || '';
  const isPaid = status === '결제 완료' || status === '결제완료';
  if (isPaid) {
    return {
      background:'#FCEBEB',
      color:'#A32D2D',
      fontWeight:500,
      textAlign:'right',
      fontFamily:'Inter,Pretendard,monospace'
    };
  }
  if (p.value && p.value > 0) {
    return {
      textAlign:'right',
      color:'#185FA5',
      fontWeight:500,
      fontFamily:'Inter,Pretendard,monospace'
    };
  }
  return {textAlign:'right', color:'#BBB'};
}
""")


AMOUNT_FORMATTER = JsCode("""
function(p){
  if (p.value == null || p.value === '' || p.value === 0) return '';
  const n = parseInt(p.value, 10);
  if (isNaN(n)) return p.value;
  return '₩' + n.toLocaleString('ko-KR');
}
""")


# ============================================================
# 5. row_type별 배경 — 진행사항/이슈사항 베이지
# ============================================================
ROW_STYLE = JsCode("""
function(p){
  const t = p.data?.row_type;
  if (t === 'progress') return {background:'#FBF7EE', fontStyle:'italic'};
  if (t === 'issue')    return {background:'#FBF7EE', fontStyle:'italic'};
  return null;
}
""")


# ============================================================
# 6. 일자 헤더 그룹 렌더러
# ============================================================
DATE_HEADER_RENDERER = JsCode("""
class DateHeaderRenderer {
  init(p) {
    this.eGui = document.createElement('div');
    const leaves = p.node.allLeafChildren || [];
    const dateVal = p.value || '';

    // leaf로부터 메타 추출
    let count = 0, paid = 0, paidCnt = 0;
    const persons = new Set();
    leaves.forEach(n => {
        if (n.data?.row_type === 'record') {
            count += 1;
            const v = parseInt(n.data['매출']) || parseInt(n.data['amount']) || 0;
            if (v > 0) { paid += v; paidCnt += 1; }
            const pRaw = n.data['담당자'] || n.data['person_raw'] || '';
            String(pRaw).split(/[,，、/]/).forEach(x => {
                const t = x.trim().replace(/(선임|사원|부장|과장|대리|팀장|이사님|이사|실장|대표(님)?|차장)$/, '').trim();
                if (t && /^[가-힣]{2,4}$/.test(t)) persons.add(t);
            });
        }
    });
    const meta = leaves[0]?.data?._meta || {};
    const weekday = meta.weekday || '';
    const visitorTeams = meta.visitor_teams || count;
    const totalSales = meta.total_sales || paid;
    const personList = (meta.persons && meta.persons.length) ? meta.persons : Array.from(persons);

    this.eGui.style.cssText = 'display:flex;gap:20px;align-items:center;padding:10px 14px;background:#FBF7EE;color:#444441;font-weight:500;font-size:13px;border-radius:6px;';
    this.eGui.innerHTML = `
      <span style="font-size:14px;color:#0A0A0A;font-weight:600">📅 ${dateVal}${weekday ? ' (' + weekday + ')' : ''}</span>
      <span style="color:#5F5E5A;font-size:11px">담당 <b style="color:#993556;font-weight:600">${personList.slice(0,4).join('·') || '—'}</b></span>
      <span style="color:#5F5E5A;font-size:11px">내방 <b style="color:#185FA5;font-family:Inter">${visitorTeams}팀</b></span>
      <span style="color:#5F5E5A;font-size:11px">결제건 <b style="color:#854F0B;font-family:Inter">${paidCnt}</b></span>
      <span style="color:#5F5E5A;font-size:11px;margin-left:auto">금액 <b style="color:#A32D2D;font-family:Inter;font-size:13px;background:#FCEBEB;padding:2px 8px;border-radius:10px">₩${(totalSales||0).toLocaleString('ko-KR')}</b></span>
    `;
  }
  getGui() { return this.eGui; }
}
""")


# ============================================================
# 7. 담당자 배지 — 통합 핑크 (cellClass와 함께 사용)
# ============================================================
PERSON_BADGE = JsCode("""
function(p) {
    if (!p.value) return '';
    return `<span style="display:inline-flex;align-items:center;
      padding:2px 10px;border-radius:14px;font-size:11px;font-weight:500;
      background:#FBEAF0;color:#993556;border:1px solid #ED93B1">${p.value}</span>`;
}
""")


# ============================================================
# Legacy alias (이전 코드 호환)
# ============================================================
STATUS_CELL_STYLE = JsCode("""
function(params) {
    const colors = {
        'done':{bg:'#E6F1FB', fg:'#185FA5'},
        'ing':{bg:'#FAEEDA', fg:'#854F0B'},
        '결제 완료':{bg:'#FCEBEB', fg:'#A32D2D'},
        '결제완료':{bg:'#FCEBEB', fg:'#A32D2D'},
        'to do':{bg:'#F1EFE8', fg:'#444441'},
    };
    const v = (params.value || '').toString().trim();
    if (colors[v]) {
        return {
            backgroundColor: colors[v].bg, color: colors[v].fg,
            fontWeight: '500', textAlign: 'center',
            borderRadius: '14px', fontSize: '11px'
        };
    }
    return {textAlign: 'center'};
}
""")

AMOUNT_STYLE = AMOUNT_CELL_STYLE  # alias
ROW_TYPE_STYLE = ROW_STYLE  # alias
