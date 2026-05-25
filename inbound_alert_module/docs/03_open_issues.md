# 03. 미해결 이슈 (Open Issues)

> Claude Code에서 결정·구현이 필요한 항목. 우선순위 순.

---

## 🔴 1순위 (PoC 전 결정 필수)

### Issue #1. 추승민 알람 수신 정책

**현황**: 추승민은 진행일지 E열(영업담당자)에 등장하지 않음. 시스템·BOM·코드 관리 R&R이라 영업 직접 담당이 없음.

**선택지**:

| 옵션 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A | 4인 통합 수신 (모든 건) | 정보 공유 강함 | 본인 무관 건도 다 받음 |
| B | 본인 직접 담당건만 (현재 0건) | 깔끔 | 사실상 수신 없음 |
| C | 시스템 관리자로 분리 (별도 DM) | 역할 명확 | 추가 채널 필요 |
| D | 본인 담당 + 통합 발송 실패 알람만 | 균형 | 구현 복잡 |

**권장**: **C** (시스템 관리자로 분리). 추승민의 R&R(BOM·코드)과 부합.

**결정 사항**: TBD ☐

---

### Issue #2. 발송 이력 DB 선택

**선택지**:

| 옵션 | 장점 | 단점 |
|---|---|---|
| **A. Notion DB** | • 기존 인프라 재활용<br>• 4인 모두 가시성<br>• 수동 수정 가능 | • API 호출 비용<br>• 속도 다소 느림 |
| B. SQLite | 빠름, 단순 | Streamlit Cloud 영속성 이슈 |
| C. JSON 파일 | 가장 단순 | 동시성 이슈, 가시성 낮음 |
| D. Google Sheets | 가시성 좋음 | API 복잡, 권한 필요 |

**권장**: **A. Notion DB**. 기존 OWNER 프로젝트가 이미 Notion 기반이므로 일관성 유지.

**스키마**: `02_data_structure.md` §3 참조.

**결정 사항**: TBD ☐

---

## 🟡 2순위 (MVP 단계 결정)

### Issue #3. Source 1-2 교차 매칭 키

**상황**: 재고엑셀(Source 1)과 진행일지(Source 2) 모두 PO 정보를 가지지만 형식 다름.

**매칭 후보**:
- **PO No.** (가장 신뢰도 높음): `PO-PF-20251120` / `PO-KN-251219` 형식
- Project (고객명): 진행일지 'Project' vs 재고엑셀 'Project' 또는 'Client'
- Brand + 발주일 조합

**권장 로직**:
```python
# 우선순위 매칭
match = None
if po_no_s1 == po_no_s2:           # 완전 일치
    match = "PO_NO_EXACT"
elif project_s1 == project_s2 and brand_s1 == brand_s2:
    match = "PROJECT_BRAND"
elif fuzzy_match(project_s1, project_s2, threshold=0.85):
    match = "PROJECT_FUZZY"
else:
    match = None  # 확인 필요 리스트
```

**결정 사항**: TBD ☐

---

### Issue #4. '조이경' 매칭 시 오탐 방지

**문제**: '이경'은 고객명 빈출 (`이경아 고객님`, `이경화 고객님`). E열에서만 매칭하고, '조이경' 풀네임만 사용.

**대응 코드 (참고)**:
```python
MEMBERS = {
    "서영완": ["서영완"],          # '영완' 단독은 위험할 수 있음
    "조이경": ["조이경"],          # '이경' 절대 금지
    "윤소담": ["윤소담"],
    "추승민": ["추승민"],
}

def match_member(cell_value):
    if not cell_value:
        return None
    s = str(cell_value).strip()
    for std, aliases in MEMBERS.items():
        for a in aliases:
            if a in s:
                return std
    return None
```

**결정 사항**: 위 로직 적용 + 매칭 결과 샘플 검증 ☐

---

### Issue #5. 분리선적 처리

**케이스**: `6/4, 7/8 도착예상` - 한 발주가 두 번에 나눠 입항

**처리 옵션**:

| 옵션 | 내용 |
|---|---|
| A | 2건으로 분리하여 각각 알람 (PO No.에 `__1`, `__2` 추가) |
| B | 가장 빠른 ETA 기준 1차 알람만, 입고 시 분할 표기 |
| C | 진행일지에서 분리선적 별도 행으로 등록 (수동) |

**권장**: **A**. Notion 이력 DB에서도 분리 키로 관리.

**결정 사항**: TBD ☐

---

### Issue #6. 시트별 컬럼 매핑 자동화

**문제**: 시트마다 컬럼 위치 다름 (`02_data_structure.md` §2.4).

**대응**:
1. **헤더 행 동적 탐지** (기본): 'Supplier', '담당자', 'PO No.' 등 키워드로 헤더 위치 찾기
2. **`sheets_mapping.yaml` fallback**: 자동 탐지 실패 시 수동 매핑 적용

**결정 사항**: 헤더 동적 탐지 우선 구현, 실패 케이스만 YAML로 ☐

---

## 🟢 3순위 (운영 단계 결정)

### Issue #7. 실행 스케줄

**선택지**:

| 옵션 | 내용 |
|---|---|
| A | Streamlit 대시보드 내 '🔄 지금 스캔' 버튼 (수동) |
| B | Streamlit + cron (GitHub Actions로 매일 오전 9시) |
| C | Streamlit Cloud의 정기 실행 기능 |

**권장**: A로 시작 → B로 자동화 (안정화 후).

**결정 사항**: TBD ☐

---

### Issue #8. 발송 실패 시 재시도

**케이스**:
- Slack API 일시적 오류
- Notion API rate limit
- 네트워크 끊김

**대응**:
- 3회 재시도 (지수 백오프: 1s, 5s, 25s)
- 최종 실패 시 로컬 로그 + 다음 스캔 시 재시도

**결정 사항**: TBD ☐

---

### Issue #9. 4인 외 인물 신규 입사 시

**현황**: `members.yaml` 수동 갱신

**개선 아이디어**:
- 진행일지 E열의 빈출 인물 자동 감지 → 신규 인물 알림
- 사내 인사 시스템 연동 (가능성 낮음)

**결정 사항**: 수동 갱신으로 진행 ☐

---

### Issue #10. 발주시스템 v3 통합

**옵션**:

| 옵션 | 내용 |
|---|---|
| A | 별도 모듈 유지 (현재 권장) |
| B | v3 패키지에 흡수 (PoC 안정화 후) |
| C | 공통 라이브러리 추출 (loader 등) |

**결정 사항**: A로 시작, MVP 안정화 후 B 검토 ☐

---

## 📋 결정 요약 (Claude Code에서 채워넣기)

```yaml
# decisions.yaml
issue_01_choomin_policy: ""        # A / B / C / D
issue_02_history_db: ""            # A / B / C / D
issue_03_cross_match_key: ""       # PO_NO / PROJECT / HYBRID
issue_04_owner_match: "applied"    # 적용 완료
issue_05_split_shipping: ""        # A / B / C
issue_06_sheet_mapping: ""         # AUTO / YAML / HYBRID
issue_07_schedule: ""              # MANUAL / CRON / AUTO
issue_08_retry: ""                 # 3RETRY / NONE / OTHER
issue_09_member_update: "manual"   # 적용 완료
issue_10_v3_integration: "later"   # 적용 완료
```
