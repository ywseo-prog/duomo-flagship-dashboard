"""
Duomo&Co 플래그십 업무일지 파서 v0.2
- NEW(2025.10~) / OLD(2025.05) 양식 통합
- 매출/담당자/브랜드 집계
- Streamlit 캐시 호환
"""
import re
import pandas as pd
import requests
from io import StringIO
import os
import streamlit as st

SHEET_ID = "1enUaMwY092nn27BDTxvHCz9hmrZRVIxXTSU3JKjmw64"
WORKLOG_TAB = "플래그십 업무일지"
CS_TAB = "CS 상담 이력(현진님)"
CLAIM_TAB = "브랜드 클레임노트 (혁진)"

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

def parse_worklog(csv_text):
    df_raw = pd.read_csv(StringIO(csv_text), header=None, dtype=str, keep_default_na=False)
    rows = df_raw.values.tolist()
    records = []
    cur_date, cur_fmt = None, None
    for r in rows:
        r = list(r) + [""]*30
        if r[1] == "날짜" or r[0] == "날짜":
            m = DATE_RE.match(r[2].strip())
            if m:
                cur_date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                cur_fmt = "NEW" if r[1] == "날짜" else "OLD"
            continue
        if r[0] == "카테고리" or r[1] == "카테고리": continue
        if r[1] in ("진행사항","이슈사항") or r[0] in ("진행사항","이슈사항"): continue
        if cur_date and (r[2].strip() or r[3].strip()):
            amt = parse_amount(r[9])
            records.append({
                "date": cur_date, "fmt": cur_fmt,
                "channel": r[0], "category": r[1], "status": r[2],
                "customer": str(r[3]).replace("\n"," / "),
                "phone": r[4], "content": r[5],
                "person_raw": r[8], "persons": normalize_person(r[8]),
                "amount": amt, "brands": detect_brands(r[5]),
            })
    df = pd.DataFrame(records)
    if len(df):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["ym"] = df["date"].dt.strftime("%Y-%m")
    return df

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
