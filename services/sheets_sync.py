"""Google Sheets gspread 동기화 모듈 — 본사 시트 read·write 추상화.

- get_client(): service account 인증된 gspread 클라이언트 (st.cache_resource)
- fetch_worklog(): 본사 시트 raw CSV 반환 (gviz/tq 또는 service account)
- push_changes(): AG-Grid의 변경분 list[{row, field, value}] → batch_update
- 모든 함수는 service account 미설정 시 graceful (예외 대신 None/False 반환)
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from io import StringIO

# 기존 worklog_writer 인프라를 위임 (중복 회피)
from parsers.worklog_writer import (
    _get_gspread_client, _has_service_account,
    bulk_update_worklog as _bulk_update,
    append_worklog_row as _append_row,
    append_worklog_block as _append_block,
    COL_MAP,
)
from parsers.worklog_parser import SHEET_ID, WORKLOG_TAB, fetch_sheet_csv


def get_client():
    """gspread 클라이언트 — service account 미설정 시 None."""
    return _get_gspread_client()


def has_service_account() -> bool:
    return _has_service_account()


def fetch_worklog(use_service_account: bool = False) -> str:
    """본사 시트 CSV 텍스트 반환.

    - use_service_account=False (기본): gviz/tq 공개 endpoint (캐시 무관, 비공개 시 실패)
    - use_service_account=True: gspread로 fetch (Service Account 권한 필요)
    """
    if use_service_account:
        client = get_client()
        if not client:
            raise RuntimeError("Service Account 미설정 — secrets.toml의 [gcp_service_account] 확인")
        ws = client.open_by_key(SHEET_ID).worksheet(WORKLOG_TAB)
        rows = ws.get_all_values()
        # raw CSV로 변환
        return "\n".join([",".join([f'"{c}"' for c in row]) for row in rows])
    # 공개 모드 — gviz CSV
    return fetch_sheet_csv(WORKLOG_TAB)


def push_changes(changes: list[dict]) -> dict:
    """AG-Grid에서 감지된 변경 → 본사 시트 batch_update.
    changes: [{row: int, field: str, value: any}, ...]
    field 종류: channel/category/status/customer/phone/content/person/amount
    Returns: {ok: bool, updated: int, error: str | None}
    """
    return _bulk_update(changes, SHEET_ID, WORKLOG_TAB)


def append_row(record: dict, target_date):
    """단건 행 추가 — modules/worklog.py 인라인 폼에서 사용"""
    return _append_row(record, target_date, SHEET_ID, WORKLOG_TAB)


def append_block(records: list[dict], target_date, progress: str = "", issue: str = ""):
    """블록 단위 일괄 추가 — 영업보고 모듈 작성 탭에서 사용"""
    return _append_block(records, target_date,
                         progress_note=progress, issue_note=issue,
                         sheet_id=SHEET_ID, sheet_name=WORKLOG_TAB)
