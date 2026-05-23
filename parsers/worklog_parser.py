"""
Duomo&Co 플래그십 업무일지 파서 v0.9
- 5-RowType 분기 (DATE_HEADER / CATEGORY_META / RECORD / PROGRESS / ISSUE)
- parse_worklog_v2(): dict 구조 반환 (스펙 v0.9)
- parse_worklog(): 기존 DataFrame 호환 (v2 위임)
- NEW(2025.10~) / OLD(2025.05) 양식 자동 감지
"""
import re
import pandas as pd
import requests
from io import StringIO
from datetime import datetime
from enum import Enum
import os
import streamlit as st


class RowType(Enum):
    DATE_HEADER   = "date_header"     # ① B="날짜" + C에 날짜 패턴
    CATEGORY_META = "category_meta"   # ② A="카테고리" (J에 일자 총매출)
    RECORD        = "record"          # ③ status/customer 있는 상담 행
    PROGRESS      = "progress"        # ④ 진행사항
    ISSUE         = "issue"           # ⑤ 이슈사항


# 컬럼 매핑 (28컬럼 기준, J까지)
COL = {
    "channel": 0, "category": 1, "status": 2, "customer": 3,
    "phone": 4, "content": 5,
    "team_count_label": 5,     # F (날짜 행에서 "내방객(팀)" 라벨)
    "person": 8, "team_count": 8,    # I (날짜 행에서 팀 수)
    "amount": 9, "date_total_sales": 9,  # J (카테고리 행에서 일자 총매출)
}

SHEET_ID = "1enUaMwY092nn27BDTxvHCz9hmrZRVIxXTSU3JKjmw64"
WORKLOG_TAB = "플래그십 업무일지"
CS_TAB = "CS 상담 이력(현진님)"
CLAIM_TAB = "브랜드 클레임노트 (혁진)"
VISITOR_TAB = "내방객 추이 표"

COL = {"channel":0, "category":1, "status":2, "customer":3, "phone":4, "content":5, "person":8, "amount":9}
DATE_RE = re.compile(r"^(20\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})")
TITLE_RE = re.compile(r"\s*(선임|사원|부장|과장|대리|팀장|이사님|이사|실장|대표(님)?|차장)$")

BRAND_KEYWORDS = {
    "FLOS": ["Flos","FLOS","Luce Sferica","Luce Orizzontale","Luce Cilindrica","루체","Lamina","라미나","Tolomeo","TOLOMEO","톨로메오","2097","LUMINATOR","Aplomb","Choose F","Coordinates","Parentesi","Camouflage","Fucsia","IC T1","Gatto"],
    "ARTEMIDE": ["Artemide","ARTEMIDE","아르떼미데","Melampo","MELAMPO","Tizio","TIZIO","Shogun","SHOGUN","TALO","Callimaco","Alphabet of light","Cometogether","Nessino","NESSINO","Light Au Lait"],
    "LASVIT": ["LASVIT","Lasvit","라스빗","Never-ending glory","Metropolitan Opera","La Scala","Cipher","Bolshoi"],
    "VIABIZZUNO": ["Viabizzuno","비아비주노","N55","H20"],
    "MARSET": ["Marset","Ginger","진저","Dipping","Soap","BOMMA","FollowMe","Bicoca","BICOCA"],
    "VIBIA": ["Vibia","VIBIA"],
    "FOSCARINI": ["Foscarini"],
    "SANTA&COLE": ["Santa&Cole"],
    "INGO MAURER": ["잉고마우어","Ingo Maurer"],
    "B&B": ["B&B","비앤비"],
    "KNOLL": ["KNOLL"],
    "ASTEP": ["Astep","아스텝"],
}

def parse_amount(s):
    if not s: return 0
    s = str(s).replace("₩","").replace(",","").replace(" ","")
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else 0

def normalize_person(raw):
    if not raw: return []
    out = []
    for n in re.split(r"[,，、/]\s*", str(raw)):
        n = TITLE_RE.sub("", n).strip()
        if re.fullmatch(r"[가-힣]{2,4}", n): out.append(n)
    return out

def detect_brands(content):
    if not content: return []
    out = set()
    for b, kws in BRAND_KEYWORDS.items():
        if any(k in content for k in kws): out.add(b)
    return sorted(out)

def fetch_sheet_csv(sheet_name, sheet_id=SHEET_ID):
    """공개 시트일 경우 직접 fetch. 비공개시 인증 필요."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
    r = requests.get(url, params={"tqx":"out:csv","sheet":sheet_name}, timeout=15)
    r.raise_for_status()
    return r.text

def detect_row_type(row: list) -> RowType | None:
    """5-RowType 분기 — 우선순위 순서 그대로 검사."""
    r = list(row) + [""] * 30
    # ① DATE_HEADER: B="날짜" + C에 날짜 패턴
    if str(r[1]).strip() == "날짜" and DATE_RE.match(str(r[2]).strip()):
        return RowType.DATE_HEADER
    # 호환: 일부 OLD 양식은 A=날짜
    if str(r[0]).strip() == "날짜" and DATE_RE.match(str(r[2]).strip()):
        return RowType.DATE_HEADER
    # ② CATEGORY_META: A="카테고리"
    if str(r[0]).strip() == "카테고리":
        return RowType.CATEGORY_META
    # ④ PROGRESS
    if str(r[1]).strip() == "진행사항" or str(r[0]).strip() == "진행사항":
        return RowType.PROGRESS
    # ⑤ ISSUE
    if str(r[1]).strip() == "이슈사항" or str(r[0]).strip() == "이슈사항":
        return RowType.ISSUE
    # ③ RECORD: status(C) 또는 customer(D)에 값 있음
    if str(r[2]).strip() or str(r[3]).strip():
        return RowType.RECORD
    return None


def parse_worklog_v2(csv_text: str) -> dict:
    """5-RowType 분기 + dict 구조 반환 (스펙 v0.9)

    Returns:
        {
            "header": {"month": 5, "month_target": 99770000,
                       "current_total": 79854000, "achievement": 0.8004},
            "dates": [
                {
                    "date": "2026-05-23",
                    "_sheet_row": <int>,
                    "fmt": "NEW",
                    "meta": {"weekday": "토", "persons": [...],
                             "visitor_teams": 9, "total_sales": 2335000},
                    "records": [{...}],   # RowType.RECORD
                    "progress": [str],    # RowType.PROGRESS (content 텍스트 리스트)
                    "issues": [str],      # RowType.ISSUE
                }, ...
            ]
        }
    """
    df_raw = pd.read_csv(StringIO(csv_text), header=None, dtype=str, keep_default_na=False)
    rows = df_raw.values.tolist()

    # === 헤더 (행 1-2) ===
    header = {}
    if len(rows) >= 2:
        h_row = list(rows[0]) + [""] * 10
        v_row = list(rows[1]) + [""] * 10
        for i, h in enumerate(h_row):
            h_s = str(h).strip()
            v_s = str(v_row[i] if i < len(v_row) else "").strip()
            if not h_s:
                continue
            m = re.search(r"(\d+)\s*월\s*목표\s*매출", h_s)
            if m:
                num = re.sub(r"[^\d]", "", v_s)
                if num:
                    header["month"] = int(m.group(1))
                    header["month_target"] = int(num)
                continue
            if "매출" in h_s and any(k in h_s for k in ["총 합", "총합", "당일", "금일", "오늘", "누적"]):
                num = re.sub(r"[^\d]", "", v_s)
                if num:
                    header["current_total"] = int(num)
                continue
            if "달성률" in h_s or "달성율" in h_s:
                m = re.search(r"([\d.]+)", v_s)
                if m:
                    val = float(m.group(1))
                    header["achievement"] = val / 100.0 if val > 1 else val

    # === 날짜 블록 누적 ===
    dates = []
    cur_block = None
    cur_fmt = None

    for row_idx, raw in enumerate(rows, start=1):
        r = list(raw) + [""] * 30
        rt = detect_row_type(r)
        if rt is None:
            continue

        if rt == RowType.DATE_HEADER:
            m = DATE_RE.match(str(r[2]).strip())
            if not m:
                continue
            d_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                weekday = ["월","화","수","목","금","토","일"][d_obj.weekday()]
            except ValueError:
                weekday = ""
            cur_fmt = "NEW" if str(r[1]).strip() == "날짜" else "OLD"
            # I열 — 내방객 팀 수
            try:
                visitor_teams = int(re.sub(r"[^\d]", "", str(r[8]).strip()) or 0)
            except (ValueError, TypeError):
                visitor_teams = 0
            cur_block = {
                "date": d_str, "_sheet_row": row_idx, "fmt": cur_fmt,
                "meta": {
                    "weekday": weekday, "persons": [],
                    "visitor_teams": visitor_teams, "total_sales": 0,
                },
                "records": [], "progress": [], "issues": [],
            }
            dates.append(cur_block)

        elif rt == RowType.CATEGORY_META and cur_block:
            # J열 — 일자 총매출
            num = re.sub(r"[^\d]", "", str(r[9]).strip())
            if num:
                try:
                    cur_block["meta"]["total_sales"] = int(num)
                except ValueError:
                    pass

        elif rt == RowType.PROGRESS and cur_block:
            content = str(r[5]).strip()
            if not content:
                content = " ".join(str(r[i]).strip() for i in range(2, 9) if str(r[i]).strip()).strip()
            if content and content != "진행사항":
                cur_block["progress"].append(content)

        elif rt == RowType.ISSUE and cur_block:
            content = str(r[5]).strip()
            if not content:
                content = " ".join(str(r[i]).strip() for i in range(2, 9) if str(r[i]).strip()).strip()
            if content and content != "이슈사항":
                cur_block["issues"].append(content)

        elif rt == RowType.RECORD and cur_block:
            amt = parse_amount(r[9])
            persons = normalize_person(r[8])
            # block meta.persons에 누적 (담당자 자동 추출)
            for p in persons:
                if p not in cur_block["meta"]["persons"]:
                    cur_block["meta"]["persons"].append(p)
            cur_block["records"].append({
                "_sheet_row": row_idx,
                "channel": r[0], "category": r[1], "status": r[2],
                "customer": str(r[3]).replace("\n", " / "),
                "phone": r[4], "content": r[5],
                "person_raw": r[8], "persons": persons,
                "amount": amt, "brands": detect_brands(r[5]),
            })

    return {"header": header, "dates": dates}


def parse_worklog(csv_text: str) -> pd.DataFrame:
    """기존 호환 — DataFrame 반환. 내부적으로 parse_worklog_v2 위임."""
    v2 = parse_worklog_v2(csv_text)
    records = []
    for d in v2["dates"]:
        for r in d["records"]:
            records.append({
                **r, "date": d["date"], "fmt": d.get("fmt"),
            })
    df = pd.DataFrame(records)
    if len(df):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["ym"] = df["date"].dt.strftime("%Y-%m")
    return df

@st.cache_data(ttl=300)
def load_worklog_v2(source: str = "auto") -> dict:
    """parse_worklog_v2의 캐시드 entry — 5-RowType dict 구조 반환."""
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "worklog_sample.csv")
    if source in ("auto", "live"):
        try:
            csv = fetch_sheet_csv(WORKLOG_TAB)
            return parse_worklog_v2(csv)
        except Exception:
            if source == "live":
                raise
    if os.path.exists(sample_path):
        with open(sample_path, encoding="utf-8") as f:
            return parse_worklog_v2(f.read())
    return {"header": {}, "dates": []}


@st.cache_data(ttl=300)
def load_worklog_df(source="auto"):
    """source: 'auto'|'live'|'sample'. live=원격 fetch, sample=로컬 캐시"""
    sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "worklog_sample.csv")
    if source in ("auto","live"):
        try:
            csv = fetch_sheet_csv(WORKLOG_TAB)
            return parse_worklog(csv)
        except Exception as e:
            if source == "live": raise
    if os.path.exists(sample_path):
        with open(sample_path, encoding="utf-8") as f:
            return parse_worklog(f.read())
    return pd.DataFrame()

def aggregate_monthly(df):
    if not len(df): return pd.DataFrame()
    g = df.groupby("ym").agg(
        days=("date", "nunique"),
        entries=("status","count"),
        paid_count=("amount", lambda s: int((s>0).sum())),
        sales=("amount","sum"),
    )
    g["avg_ticket"] = (g["sales"]/g["paid_count"].replace(0,1)).fillna(0).round(0).astype(int)
    return g.reset_index()

def aggregate_by_person(df):
    if not len(df): return pd.DataFrame()
    exp = df.explode("persons").dropna(subset=["persons"])
    exp = exp[exp["persons"]!=""]
    g = exp.groupby("persons").agg(
        consult_count=("status","count"),
        paid_count=("amount", lambda s: int((s>0).sum())),
        sales=("amount","sum"),
    ).sort_values("consult_count", ascending=False)
    return g.reset_index()

def aggregate_by_brand(df):
    if not len(df): return pd.DataFrame()
    exp = df.explode("brands").dropna(subset=["brands"])
    exp = exp[exp["brands"]!=""]
    g = exp.groupby("brands").agg(
        mention_count=("status","count"),
        paid_count=("amount", lambda s: int((s>0).sum())),
        sales=("amount","sum"),
    ).sort_values("mention_count", ascending=False)
    return g.reset_index()


def aggregate_by_customer(df):
    """고객별 집계 — 영업보고 모듈용. 방문/누적/최근/대표 카테고리"""
    if not len(df): return pd.DataFrame()
    work = df[df["customer"].astype(str).str.strip() != ""].copy()
    if not len(work): return pd.DataFrame()
    work["customer_norm"] = work["customer"].astype(str).str.strip().str.split("/").str[0].str.strip()
    work = work[work["customer_norm"] != ""]
    g = work.groupby("customer_norm").agg(
        phone=("phone", lambda s: next((x for x in s if str(x).strip()), "")),
        category=("category", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        channel=("channel", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        visits=("date", "count"),
        sales=("amount", "sum"),
        last_visit=("date", "max"),
    ).reset_index().rename(columns={"customer_norm": "customer"})
    g = g.sort_values("last_visit", ascending=False)
    return g


def daily_report_data(df, target_date):
    """특정 날짜의 영업보고용 데이터 산출. target_date: datetime.date"""
    if not len(df): return None
    work = df.copy()
    today_df = work[work["date"].dt.date == target_date]
    ym = f"{target_date.year}-{target_date.month:02d}"
    month_df = work[work["ym"] == ym]
    paid_today = today_df[today_df["amount"] > 0]
    paid_month = month_df[month_df["amount"] > 0]

    walk_in = int((today_df["channel"] == "내방").sum())
    return {
        "date": target_date,
        "ym": ym,
        "total_entries": int(len(today_df)),
        "walk_in": walk_in,
        "paid_count_today": int(len(paid_today)),
        "paid_sum_today": int(paid_today["amount"].sum()),
        "paid_sum_month": int(paid_month["amount"].sum()),
        "paid_count_month": int(len(paid_month)),
        "paid_today_df": paid_today,
        "consult_today_df": today_df[today_df["amount"] == 0],
    }


def format_katalk_report(data, store_name="조명 플래그십"):
    """일일 영업보고 → 카톡 발송용 텍스트 (참조: sales-report-ivory.vercel.app)"""
    if not data: return ""
    d = data["date"]
    weekday_kor = ["월","화","수","목","금","토","일"][d.weekday()]
    lines = [
        f"{d.month:02d}/{d.day:02d}({weekday_kor}) {store_name} 영업보고",
        "",
        "1. 유입/계약",
        f"- 유입 {data['total_entries']}팀",
        f"   (워크인 {data['walk_in']} / 계약 {data['paid_count_today']})",
        "",
        f"2. {d.month:02d}월 누적 수주액",
        f"- {data['paid_sum_month']:,}원",
        "",
        "3. 금일 계약 총액",
        f"- {data['paid_sum_today']:,}원",
        "",
        "4. 계약건 세부 내용",
    ]
    if data["paid_count_today"] == 0:
        lines.append("- (없음)")
    else:
        for row in data["paid_today_df"].itertuples():
            cust = (row.customer or "").strip().split("/")[0].strip() or "—"
            person = (row.person_raw or "").strip() or "—"
            content = (row.content or "").strip().replace("\n", " ")
            lines.extend([
                f"- {cust} 고객",
                f"  담당 : {person}",
                f"  금액 : {int(row.amount):,}원",
                f"  내용 : {content}",
                "",
            ])
    lines.append("5. 주요 상담")
    consult_df = data["consult_today_df"]
    if not len(consult_df):
        lines.append("- (없음)")
    else:
        # 상위 5건만 (간결성)
        for row in consult_df.head(5).itertuples():
            cust = (row.customer or "").strip().split("/")[0].strip() or "—"
            person = (row.person_raw or "").strip() or "—"
            content = (row.content or "").strip().replace("\n", " ")[:80]
            lines.extend([
                f"- 고객 : {cust}",
                f"- 담당 : {person}",
                f"- 내용 : {content}",
                "",
            ])
    return "\n".join(lines).rstrip()


# ===== 월 목표 매출 / 누적 매출 / 달성률 (시트 1-2행) =====
def parse_monthly_target(csv_text):
    """플래그십 업무일지 1-2행에서 월 목표 매출 + 당일 누적 + 달성률 추출.
    시트가 이미 계산해놓은 값을 그대로 읽음."""
    import csv as _csv
    reader = _csv.reader(StringIO(csv_text))
    rows = list(reader)
    if len(rows) < 2:
        return None
    h, v = rows[0], rows[1]
    result = {
        "month": None, "target": None, "achieved": None,
        "achievement_rate": None,
        "raw_target_text": None, "raw_achieved_text": None, "raw_rate_text": None,
    }
    for i, cell in enumerate(h):
        cell_s = (cell or "").strip()
        val_s = (v[i] if i < len(v) else "").strip()
        if not cell_s:
            continue
        # "5월 목표 매출"
        m = re.search(r"(\d+)\s*월\s*목표\s*매출", cell_s)
        if m:
            result["month"] = int(m.group(1))
            result["raw_target_text"] = val_s
            num = re.sub(r"[^\d]", "", val_s)
            if num:
                result["target"] = int(num)
            continue
        # "금일 기준 매출 총 합" / "당일 매출" / "오늘 매출" — 누적
        if "매출" in cell_s and any(k in cell_s for k in ["총 합", "총합", "당일", "오늘", "금일", "누적"]):
            result["raw_achieved_text"] = val_s
            num = re.sub(r"[^\d]", "", val_s)
            if num:
                result["achieved"] = int(num)
            continue
        # "달성률"
        if "달성률" in cell_s or "달성율" in cell_s:
            result["raw_rate_text"] = val_s
            m = re.search(r"([\d.]+)", val_s)
            if m:
                try:
                    result["achievement_rate"] = float(m.group(1))
                except ValueError:
                    pass
    return result


@st.cache_data(ttl=300)
def load_monthly_target():
    """월 목표 매출 / 누적 / 달성률 로드. 실패 시 None."""
    try:
        csv = fetch_sheet_csv(WORKLOG_TAB)
        return parse_monthly_target(csv)
    except Exception:
        return None


# ===== 내방객 추이 표 (별도 탭) =====
@st.cache_data(ttl=300)
def load_visitor_trend():
    """'내방객 추이 표' 탭 raw fetch. 현재 데이터 미입력 → 빈 DataFrame 또는 헤더만."""
    try:
        csv = fetch_sheet_csv(VISITOR_TAB)
        df = pd.read_csv(StringIO(csv), header=None, dtype=str, keep_default_na=False)
        return df
    except Exception:
        return pd.DataFrame()
