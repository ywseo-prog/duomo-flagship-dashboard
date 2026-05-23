"""
본사 업무일지 시트 Write 모듈
- gspread + service account 인증으로 행 append
- 시트 구조: 날짜 블록 (날짜 행 + 카테고리 헤더 + 데이터 행 + 진행/이슈 행)
- 동일 날짜 블록 자동 탐지 → 마지막 빈 행 위에 insert
- service account 미등록 시 graceful fallback (TSV 텍스트 반환)
"""
from __future__ import annotations
import streamlit as st
from datetime import datetime, date
from typing import Optional


# 본사 시트 컬럼 매핑 (1-indexed, gspread 호환)
# A=channel, B=category, C=status, D=customer, E=phone, F=content, I=person, J=amount
COL_MAP = {
    "channel":  "A",
    "category": "B",
    "status":   "C",
    "customer": "D",
    "phone":    "E",
    "content":  "F",
    "person":   "I",
    "amount":   "J",
}

CHANNEL_OPTIONS = ["내방", "유선", "온라인", "소개", "기타"]
CATEGORY_OPTIONS = ["소비자", "업체", "디자이너", "기타"]
STATUS_OPTIONS = ["done", "ing", "예정", "보류", "취소", "문의", "재방문"]


def _get_secret(key: str, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


def _has_service_account() -> bool:
    """secrets에 gcp_service_account 블록이 있고 placeholder가 아니면 True"""
    try:
        sa = st.secrets.get("gcp_service_account")
        if not sa:
            return False
        # private_key 가 placeholder ('MIIE...') 이면 미설정
        pk = sa.get("private_key", "")
        return bool(pk) and "MIIE...\\n" not in pk
    except Exception:
        return False


@st.cache_resource
def _get_gspread_client():
    """service account 인증 gspread 클라이언트 (없으면 None)"""
    if not _has_service_account():
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        sa_info = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.warning(f"gspread 인증 실패: {e}")
        return None


def format_row_tsv(record: dict) -> str:
    """폼 입력 → 본사 시트 행 형식 TSV (탭 구분, J열까지 10칸)"""
    cells = ["", "", "", "", "", "", "", "", "", ""]  # A~J
    col_idx = {"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"G":6,"H":7,"I":8,"J":9}
    for key, col in COL_MAP.items():
        if key in record:
            cells[col_idx[col]] = str(record[key]) if record[key] is not None else ""
    return "\t".join(cells)


def format_date_header_tsv(d: date) -> str:
    """날짜 헤더 행 TSV — 본사 시트 형식: B='날짜', C='2026.5.23 (토)'"""
    weekday = ["월","화","수","목","금","토","일"][d.weekday()]
    date_str = f"{d.year}.{d.month}.{d.day} ({weekday})"
    cells = ["", "날짜", date_str, "", "", "내방객(팀)", "", "", "", ""]
    return "\t".join(cells)


def find_date_block_row(ws, target_date: date) -> Optional[int]:
    """본사 시트에서 target_date의 날짜 헤더 행 번호 찾기. 없으면 None"""
    try:
        # B열에서 "날짜" 키워드 → C열 값 매칭
        col_b = ws.col_values(2)  # B열
        col_c = ws.col_values(3)  # C열
        target_str = f"{target_date.year}.{target_date.month}.{target_date.day}"
        for i, val in enumerate(col_b, start=1):
            if str(val).strip() == "날짜":
                c_val = col_c[i-1] if i-1 < len(col_c) else ""
                if target_str in str(c_val):
                    return i
        return None
    except Exception:
        return None


def append_worklog_row(record: dict, target_date: date,
                       sheet_id: str, sheet_name: str = "플래그십 업무일지") -> dict:
    """
    본사 시트에 영업 기록 append.

    Returns:
        {
            "ok": bool,
            "method": "gspread" | "tsv",
            "row": int or None,  # 추가된 행 번호 (gspread 성공 시)
            "tsv": str,          # 사용자 복사용 TSV (fallback)
            "header_tsv": str or None,  # 같은 날짜 블록이 없으면 헤더도 같이
            "error": str or None,
        }
    """
    tsv = format_row_tsv(record)
    result = {"ok": False, "method": None, "row": None, "tsv": tsv,
              "header_tsv": None, "error": None}

    client = _get_gspread_client()
    if not client:
        # Fallback — TSV 텍스트 반환, 사용자가 직접 시트에 붙여넣기
        result["method"] = "tsv"
        result["header_tsv"] = format_date_header_tsv(target_date)
        result["error"] = "Google service account 미설정 — TSV로 복사하여 시트에 붙여넣으세요."
        return result

    try:
        sh = client.open_by_key(sheet_id)
        ws = sh.worksheet(sheet_name)
        header_row = find_date_block_row(ws, target_date)

        if header_row:
            # 해당 날짜 블록 발견 — 카테고리 행(헤더+1) 다음 빈 행에 insert
            # 안전하게 마지막 데이터 다음 행에 추가
            all_rows = ws.get_all_values()
            insert_after = header_row + 1  # 카테고리 행 다음
            # 다음 빈 행 또는 다음 날짜 헤더 직전까지 스캔
            for i in range(header_row + 2, min(len(all_rows) + 1, header_row + 40)):
                row_vals = all_rows[i-1] if i-1 < len(all_rows) else []
                if len(row_vals) > 1 and str(row_vals[1]).strip() == "날짜":
                    insert_after = i - 1  # 다음 날짜 헤더 직전
                    break
                if not any(str(v).strip() for v in row_vals[:6]):
                    insert_after = i - 1
                    break
                insert_after = i
            new_row_idx = insert_after + 1
            ws.insert_row([
                record.get("channel", ""),
                record.get("category", ""),
                record.get("status", ""),
                record.get("customer", ""),
                record.get("phone", ""),
                record.get("content", ""),
                "", "",  # G, H
                record.get("person", ""),
                str(record.get("amount", "")),
            ], index=new_row_idx, value_input_option="USER_ENTERED")
            result["ok"] = True
            result["method"] = "gspread"
            result["row"] = new_row_idx
        else:
            # 새 날짜 블록 — 시트 맨 아래에 헤더 + 데이터 행 append
            weekday = ["월","화","수","목","금","토","일"][target_date.weekday()]
            date_str = f"{target_date.year}.{target_date.month}.{target_date.day} ({weekday})"
            ws.append_row(
                ["", "날짜", date_str, "", "", "내방객(팀)", "", "", "", ""],
                value_input_option="USER_ENTERED",
            )
            ws.append_row(
                ["카테고리", "", "", "", "", "", "", "", "", ""],
                value_input_option="USER_ENTERED",
            )
            ws.append_row([
                record.get("channel", ""),
                record.get("category", ""),
                record.get("status", ""),
                record.get("customer", ""),
                record.get("phone", ""),
                record.get("content", ""),
                "", "",
                record.get("person", ""),
                str(record.get("amount", "")),
            ], value_input_option="USER_ENTERED")
            result["ok"] = True
            result["method"] = "gspread"
            result["row"] = -1  # append (정확한 행 번호는 모름)
            result["header_tsv"] = format_date_header_tsv(target_date)

        return result

    except Exception as e:
        result["method"] = "tsv"
        result["error"] = f"gspread write 실패: {e} — TSV fallback"
        result["header_tsv"] = format_date_header_tsv(target_date)
        return result


def append_worklog_block(records: list[dict], target_date: date,
                         progress_note: str = "", issue_note: str = "",
                         sheet_id: str = "", sheet_name: str = "플래그십 업무일지") -> dict:
    """
    본사 시트에 일자 블록 전체 bulk write:
    - 동일 날짜 블록 있으면 그 안에 모든 행 insert (메모는 별도)
    - 없으면 시트 맨 아래에 새 블록 (날짜 헤더 + 카테고리 헤더 + 데이터 N행 + 진행/이슈)

    records: [{channel, category, status, customer, phone, content, person, amount}, ...]
    """
    result = {"ok": False, "method": None, "rows_added": 0, "tsv_bulk": "", "error": None}

    # TSV bulk 생성 (fallback용)
    tsv_lines = []
    weekday = ["월","화","수","목","금","토","일"][target_date.weekday()]
    date_str = f"{target_date.year}.{target_date.month}.{target_date.day} ({weekday})"
    tsv_lines.append(f"\t날짜\t{date_str}\t\t\t내방객(팀)\t{len(records)}\t\t\t결제 금액")
    tsv_lines.append("\t카테고리\t\t\t\t\t\t\t\t")
    for r in records:
        tsv_lines.append(format_row_tsv(r))
    if progress_note:
        tsv_lines.append(f"\t진행사항\t\t\t\t{progress_note}\t\t\t\t")
    if issue_note:
        tsv_lines.append(f"\t이슈사항\t\t\t\t{issue_note}\t\t\t\t")
    result["tsv_bulk"] = "\n".join(tsv_lines)

    client = _get_gspread_client()
    if not client:
        result["method"] = "tsv"
        result["error"] = "Service account 미설정 — TSV로 복사하여 시트에 붙여넣으세요."
        return result

    try:
        sh = client.open_by_key(sheet_id)
        ws = sh.worksheet(sheet_name)
        header_row = find_date_block_row(ws, target_date)

        rows_to_add = []
        for r in records:
            rows_to_add.append([
                r.get("channel", ""),
                r.get("category", ""),
                r.get("status", ""),
                r.get("customer", ""),
                r.get("phone", ""),
                r.get("content", ""),
                "", "",
                r.get("person", ""),
                str(r.get("amount", "")) if r.get("amount") else "",
            ])

        if header_row:
            # 기존 블록 — 카테고리 행 다음에 batch insert
            all_rows = ws.get_all_values()
            insert_after = header_row + 1  # 카테고리 헤더
            for i in range(header_row + 2, min(len(all_rows) + 1, header_row + 60)):
                row_vals = all_rows[i-1] if i-1 < len(all_rows) else []
                if len(row_vals) > 1 and str(row_vals[1]).strip() in ("날짜", "진행사항", "이슈사항"):
                    insert_after = i - 1
                    break
                if not any(str(v).strip() for v in row_vals[:6]):
                    insert_after = i - 1
                    break
                insert_after = i
            new_row_idx = insert_after + 1
            if rows_to_add:
                ws.insert_rows(rows_to_add, row=new_row_idx, value_input_option="USER_ENTERED")
                result["rows_added"] = len(rows_to_add)
            # 메모는 추가 처리 안 함 (기존 블록 메모 보존)
        else:
            # 새 블록 생성
            ws.append_row(
                ["", "날짜", date_str, "", "", "내방객(팀)", str(len(records)), "", "", "결제 금액"],
                value_input_option="USER_ENTERED",
            )
            ws.append_row(
                ["카테고리", "", "", "", "", "", "", "", "", ""],
                value_input_option="USER_ENTERED",
            )
            for row_data in rows_to_add:
                ws.append_row(row_data, value_input_option="USER_ENTERED")
            if progress_note:
                ws.append_row(
                    ["", "진행사항", "", "", "", progress_note, "", "", "", ""],
                    value_input_option="USER_ENTERED",
                )
            if issue_note:
                ws.append_row(
                    ["", "이슈사항", "", "", "", issue_note, "", "", "", ""],
                    value_input_option="USER_ENTERED",
                )
            result["rows_added"] = len(rows_to_add)

        result["ok"] = True
        result["method"] = "gspread"
        return result

    except Exception as e:
        result["method"] = "tsv"
        result["error"] = f"gspread bulk write 실패: {e} — TSV fallback"
        return result
