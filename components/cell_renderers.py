"""AG-Grid JsCode 셀 렌더러 모음 — 업무일지 모듈 UX의 시각 자산.

설계:
- DATE_HEADER_RENDERER: 그룹 헤더 (날짜 + 요일 + 담당자 + 내방팀수 + 결제금액)
- CHANNEL_BADGE / CATEGORY_BADGE: 채널·카테고리 컬러 배지
- STATUS_CELL_STYLE: 현황 셀 배경 컬러 (done/ing/결제완료/견적진행)
- AMOUNT_FORMATTER / AMOUNT_STYLE: 매출 ₩ 한국 포맷 + 골드 강조
- ROW_TYPE_STYLE: 진행/이슈 행 배경 (노랑/연빨강)
- PERSON_BADGE: 담당자 6인 컬러 배지

JsCode 문자열은 streamlit-aggrid의 allow_unsafe_jscode=True 환경에서만 동작.
"""
from st_aggrid import JsCode


# ============================================================
# 그룹 헤더 (날짜별)
# ============================================================
DATE_HEADER_RENDERER = JsCode("""
class DateHeaderRenderer {
    init(p) {
        this.eGui = document.createElement('div');
        // 일자 그룹의 leaf children에서 meta 정보를 추출
        const leaves = p.node.allLeafChildren || [];
        const dateVal = p.value || '';
        // 첫 record의 _meta가 있으면 사용 (parse_worklog_v2 dict 구조)
        // 또는 leaves를 직접 aggregate
        let count = 0, paid = 0, paidCnt = 0;
        const persons = new Set();
        leaves.forEach(n => {
            if (n.data?.row_type === 'record') {
                count += 1;
                const v = parseInt(n.data['매출']) || parseInt(n.data['amount']) || 0;
                if (v > 0) { paid += v; paidCnt += 1; }
                const p_raw = n.data['담당자'] || n.data['person_raw'] || '';
                String(p_raw).split(/[,，、/]/).forEach(x => {
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

        this.eGui.style.cssText = 'display:flex;gap:18px;align-items:center;padding:10px 14px;background:linear-gradient(135deg,#0A0A0A 0%,#1A1A1A 100%);color:#fff;font-weight:600;font-size:13px;border-radius:6px;';
        this.eGui.innerHTML = `
            <span style="font-size:14px;color:#fff">📅 ${dateVal}${weekday ? ' (' + weekday + ')' : ''}</span>
            <span style="color:#BBB;font-size:11px">담당 <b style="color:#C9A961;font-weight:700">${personList.slice(0,4).join(' · ') || '—'}</b></span>
            <span style="color:#BBB;font-size:11px">내방 <b style="color:#fff;font-family:Inter">${visitorTeams}팀</b></span>
            <span style="color:#BBB;font-size:11px">결제건 <b style="color:#fff;font-family:Inter">${paidCnt}</b></span>
            <span style="color:#BBB;font-size:11px;margin-left:auto">금액 <b style="color:#C9A961;font-family:Inter;font-size:13px">₩${(totalSales||0).toLocaleString('ko-KR')}</b></span>
        `;
    }
    getGui() { return this.eGui; }
}
""")


# ============================================================
# 채널 / 카테고리 배지
# ============================================================
CHANNEL_BADGE = JsCode("""
function(p) {
    if (!p.value) return '';
    const c = {'내방':'#C9A961', '유선':'#1976D2', '온라인':'#7B1FA2', '소개':'#F57C00'};
    const v = String(p.value).trim();
    const color = c[v] || '#999';
    return `<span style="background:${color};color:#fff;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;letter-spacing:0.3px">${v}</span>`;
}
""")


CATEGORY_BADGE = JsCode("""
function(p) {
    if (!p.value) return '';
    const c = {'소비자':'#1976D2', '업체':'#7B1FA2', '디자이너':'#2E7D32', '기타':'#999'};
    const v = String(p.value).trim();
    const color = c[v] || '#999';
    return `<span style="background:${color};color:#fff;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:700;letter-spacing:0.3px">${v}</span>`;
}
""")


# ============================================================
# 현황 셀 컬러 배지
# ============================================================
STATUS_CELL_STYLE = JsCode("""
function(params) {
    const colors = {
        'done':'#999999', 'ing':'#FFA000',
        '결제 완료':'#C9A961', '결제완료':'#C9A961',
        '견적 진행':'#1976D2', '견적진행':'#1976D2',
        '예정':'#1976D2', '보류':'#F57C00',
        '취소':'#D32F2F', '문의':'#7B1FA2', '재방문':'#5D4037'
    };
    const v = (params.value || '').toString().trim();
    if (colors[v]) {
        return {
            backgroundColor: colors[v], color: '#fff',
            fontWeight: '700', textAlign: 'center',
            borderRadius: '3px', fontSize: '11px', letterSpacing: '0.5px'
        };
    }
    return {textAlign: 'center'};
}
""")


# ============================================================
# 매출 ₩ 한국 포맷 + 골드 강조
# ============================================================
AMOUNT_FORMATTER = JsCode("""
function(params) {
    if (params.value == null || params.value === '' || params.value === 0) return '—';
    const n = parseInt(params.value, 10);
    if (isNaN(n)) return params.value;
    return '₩' + n.toLocaleString('ko-KR');
}
""")


AMOUNT_STYLE = JsCode("""
function(params) {
    if (params.value && params.value > 0) {
        return {
            color: '#C9A961', fontWeight: '700', textAlign: 'right',
            fontFamily: 'Inter, Pretendard, monospace'
        };
    }
    return {color: '#BBB', textAlign: 'right'};
}
""")


# ============================================================
# 행 타입별 배경 (진행/이슈 강조)
# ============================================================
ROW_TYPE_STYLE = JsCode("""
function(params) {
    const t = params.data?.row_type;
    if (t === 'progress') return {background:'#FFF8E1', fontStyle:'italic'};
    if (t === 'issue')    return {background:'#FFEBEE', fontStyle:'italic'};
    return null;
}
""")


# ============================================================
# 담당자 배지 (정규화된 풀네임 매칭 + 6인 컬러)
# ============================================================
PERSON_BADGE = JsCode("""
function(p) {
    if (!p.value) return '';
    const COLORS = {
        '조이경':'#1976D2', '서영완':'#2E7D32', '추승민':'#7B1FA2',
        '강혁진':'#C2185B', '이현진':'#00838F', '신민정':'#F57C00'
    };
    const raw = String(p.value);
    const tokens = raw.split(/[,，、/]\\s*/);
    let html = '';
    tokens.forEach(t => {
        const cleaned = t.replace(/(선임|사원|부장|과장|대리|팀장|이사님|이사|실장|대표(님)?|차장)$/, '').trim();
        if (!cleaned) return;
        let color = '#5D4037';
        for (const k in COLORS) { if (cleaned.includes(k)) { color = COLORS[k]; break; } }
        html += `<span style="background:${color};color:#fff;padding:2px 8px;margin-right:3px;border-radius:3px;font-size:10px;font-weight:700;letter-spacing:0.3px">${cleaned}</span>`;
    });
    return html;
}
""")
