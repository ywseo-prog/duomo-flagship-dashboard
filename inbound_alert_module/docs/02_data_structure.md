# 02. 데이터 구조 분석

> Chat 세션에서 실제 엑셀 파일 5종을 파싱하여 도출한 컬럼 매핑·패턴 분석 결과

---

## 1. Source 1: 재고 발주 엑셀 (수동 업로드)

### 1.1 파일 목록

| 파일명 | 크기 | 형식 | 비고 |
|---|---|---|---|
| B&B 재고리스트_26_05_13.xlsb | 110MB | xlsb (binary) | `pyxlsb` 필요 |
| PF_CC 재고리스트_26_05_12.xlsx | 272MB | xlsx | openpyxl 가능 |
| 브랜드별 재고리스트_26_05_14.xlsx | TBD | xlsx | Chat에서 미수신 |

### 1.2 PF_CC 파일 시트 구조

```
1. Sale Items 21-04
2. PO                         ← 발주 관리 시트 (핵심)
3. PF&CC (Shinsege Dep)
4. PF (Hyundai Apgujung)
5. PF (Show room)
6. PF (Stock)
7. DUO (Stock)
8. CC (Stock)
9. CC (Showroom)
10. Residance
11. 대여
```

### 1.3 PO 시트 - 카드형 레이아웃

⚠️ **일반 표 형식 아님**. PO 1건 = 1블록(10~30행) 카드형.

```
[메타정보 영역 - 우측 I/J열]
  Row N+0: Date of order:   | 2025-11-20
  Row N+1: Brand:           | Poltrona Frau
  Row N+2: PO number:       | PO-PF-20251120
  Row N+3: Project:         | PF Stock Order
  Row N+4: Client:          | Duomo
  Row N+5: Shipping mode:   | Ocean
  Row N+6: Ready by:        | (공란)
  Row N+7: Delivery time:   | 5/28 입고 예정     ← 핵심!

[테이블 헤더]
  Row N+10: No. | Code | Image | Product | Size | Finish | Quantity | 
            2026 Price | Total | Finishing | 가용 | 홀딩/판매 | 내용

[품목 라인]
  Row N+11~: 4 | 5PF0060807370*001 | | REN DRESSING TABLE | ...
             | 2 | 15950000 | ... | (담당자정보)

[블록 종결]
  PURCHASE ORDER ( P1SO2504... )
```

### 1.4 핵심 컬럼 위치 (PF/CC 기준)

| 컬럼 | 위치 | 내용 |
|---|---|---|
| B (2) | 좌측 | No. / 회사정보 |
| C (3) | 좌측 | Code (SKU) |
| E (5) | 좌측 | Product (제품명) |
| F (6) | 좌측 | Size |
| G (7) | 좌측 | Finish |
| H (8) | 좌측 | Quantity |
| I (9) | 메타키 | `Date of order:`, `Delivery time:` 등 |
| J (10) | 메타값 | 날짜·Brand·PO번호·`5/28 입고 예정` |
| L (12) | 우측 | 가용 수량 |
| **M (13)** | **우측** | **홀딩/판매 (담당자명)** ← 선점 판단 |
| N (14) | 우측 | 내용 (입고완료/화기 등) |

### 1.5 B&B 파일 - 컬럼 위치 차이

| 컬럼 | PF/CC | B&B |
|---|---|---|
| 메타 키/값 | I/J (9/10) | H/I (8/9) |
| 품목 Quantity | H (8) | G (7) |
| Delivery time | J열 | I열 |
| 입고 상태 | N열 (14) | Remarks J(10) |

→ 파일별 컬럼 매핑 필요 (`sheets_mapping.yaml`).

### 1.6 'Delivery time' 자연어 패턴 (6종 혼재)

| 패턴 | 빈도 | 파싱 난이도 |
|---|---|---|
| `5/28 입고 예정` | 多 | 쉬움 |
| `6/4 도착예상` | 多 | 쉬움 |
| `06/11 도착예상` | 中 | 쉬움 |
| `2026-05-21 입항예정` | 中 | 쉬움 |
| `6/4, 7/8 도착예상` | 少 | **중간** (분리선적) |
| `7월말 ~ 8월초 예상` | 少 | **어려움** (수동 처리 권장) |

### 1.7 'M열 담당자' 표기 패턴

| 패턴 | 의미 |
|---|---|
| `김수현 (신강/교/판)` | 영업담당자명 (매장약칭/약칭/판매선점) |
| `홍원 (현본/건우/판)\n강인정 (현본/은정/판)` | 복수 담당 (개행 구분) |
| `현본 전시 폴딩` | 비매칭 (전시품 - 선점 아님) |
| `AIR` / `4월 3주차 입고` | 운송·일정 정보 |

**매장 약칭:**
- 신강 = 신세계강남점
- 현본 = 현대백화점본점
- 더현 = 더현대 서울
- 판 = 판교
- 교 = 교육·후속
- 건 = 건축·디자이너

⚠️ **중요**: 4인 이름(서영완/조이경/추승민/윤소담)은 **M열에 직접 표기되지 않음**. M열은 영업사원·매장담당자명임. → **재고엑셀에서 '선점' 판단은 다른 컬럼 또는 다른 파일이 필요할 수 있음.** 추가 분석 필요.

---

## 2. Source 2: 진행일지 (Google Drive)

### 2.1 파일 정보

| 파일명 | Drive File ID | 비고 |
|---|---|---|
| DUOMO 이동가구 진행일지.xlsx | `1Bjxf2H_spRMfdsdEvpSF7ykh6JEqkP3o` | 1.8MB |
| NOTO CASA 이동가구 진행일지.xlsx | `1NB7xqqhh0obYUAfOhJY5_W_ez8js4Xp6` | 752KB |

소유자: **lilychoi@duomonco.com** (공유 권한, Read-Only)

### 2.2 시트 목록

**DUOMO 진행일지:**
- 이동가구일지 (OLD, 입고완료건들) ← 과거 입고완료 누적
- 이동가구일지 Poltrona Frau
- 이동가구일지 Ceccotti Collezioni
- 이동가구일지 (DUOMO KNOLL+외) ← **메인 현재 진행건**
- Fedex, DHL

**NOTO CASA 진행일지:**
- 이동가구일지 (OLD-2)
- BeB 지연 확인
- 이동가구 진행일지 (NOTOCASA) ← **메인 현재 진행건**
- 매터리얼 진행일지 (NOTOCASA)
- 건자재진행일지 (OLD)
- Fedex, DHL

### 2.3 표준 컬럼 구조 (NOTOCASA 시트 기준)

| Col | 컬럼명 | 활용 |
|---|---|---|
| A (1) | No. | |
| B (2) | Supplier | 알람 표시 |
| C (3) | Project | 알람 표시 |
| D (4) | 접수일 | |
| **E (5)** | **영업부 담당자** | **4인 매칭 핵심 키** ✅ |
| F (6) | PO No. | 교차 매칭 키 |
| G (7) | PI. Date | |
| H (8) | P/I No. | |
| I (9) | Inv. Date | |
| J (10) | Inv No. | |
| K (11) | 납품기한 | |
| L (12) | Ready date | |
| M (13) | Shipping | 알람 표시 |
| N (14) | 픽업 | |
| O (15) | 선적/ETD | |
| **P (16)** | **도착/ETA** | **D-14 산출 기준** ✅ |
| **Q (17)** | **입고** | **값 존재 = 입고완료** ✅ |
| R (18) | Code | |
| S (19) | description | 알람 표시 |
| T (20) | qty | 알람 표시 |

### 2.4 시트별 컬럼 위치 변동

⚠️ **시트마다 컬럼 위치가 1~2칸 다름**. 헤더 행을 동적으로 찾아 매핑하는 로직 필수.

| 시트 | ETA(도착) | 입고 |
|---|---|---|
| 이동가구 진행일지 (NOTOCASA) | Q(17) | R(18) |
| 이동가구일지 (DUOMO KNOLL+외) | P(16) | Q(17) |
| 이동가구일지 Poltrona Frau | TBD | TBD |
| 매터리얼 진행일지 | TBD | TBD |

→ `sheets_mapping.yaml`로 관리. 헤더 동적 탐지 로직 권장.

### 2.5 영업담당자 분포 (Top 10, 진행일지 전체 5,512건)

```
김지민    1,008건
이예은      492건
이정용      420건
진나은      234건
이상진      234건
서성미      216건
이병묵      199건
이미경      194건
한동희      169건
손예원      141건
```

→ 4인은 상위에 없으며, 각자 수 건~수십 건 보유.

### 2.6 4인 매칭 실측 (2026-05-13 시점)

| 담당자 | 매칭 건수 | 등장 시트 |
|---|---|---|
| 서영완 | 7건+ | NOTOCASA / DUOMO KNOLL+외 |
| 조이경 | 7건+ | NOTOCASA / DUOMO KNOLL+외 |
| 윤소담 | 2건+ | DUOMO Poltrona Frau / KNOLL+외 |
| 추승민 | 0건 | **E열에 직접 등장 없음** |

---

## 3. Notion 발송이력 DB 스키마 (제안)

신규 생성할 Notion DB의 스키마. `INBOUND_HISTORY_DB_ID`로 Secrets 등록.

| 필드명 | 타입 | 설명 |
|---|---|---|
| 알람키 (Title) | Title | `{PO_NO}__{member}__{alarm_type}` (중복 방지 키) |
| 담당자 | Select | 서영완 / 조이경 / 윤소담 / 추승민 |
| 알람유형 | Select | 입항임박_D14 / 입고완료 |
| Supplier | Text | |
| Project | Text | |
| PO No. | Text | |
| ETA | Date | 입항예정일 |
| 입고일 | Date | (2차 알람만) |
| 발송일시 | Date | 알람 발송 timestamp |
| Slack메시지링크 | URL | 발송된 메시지 permalink |
| 상태 | Select | 발송완료 / 발송실패 / 재발송필요 |
| 비고 | Text | |

---

## 4. MCP Drive 접근 시 주의사항

### 4.1 `read_file_content` (자연어 변환)
- ✅ 모든 시트의 텍스트 받을 수 있음
- ⚠️ **행 구분자(`\n`)가 누락됨** → 전체가 1줄로 출력
- 정확 파싱 불가, 권장하지 않음

### 4.2 `download_file_content` (원본 xlsx)
- ✅ 원본 셀 구조 그대로 받을 수 있음
- ⚠️ Chat 환경에서는 **매 호출마다 사용자 승인 필요**
- Claude Code 환경에서는 한 번 인증 후 자유 호출 가능 (장점)

### 4.3 권장 접근 방식 (Claude Code)
```python
# Option A: MCP 사용
from anthropic_mcp import GoogleDriveClient
content = drive.download_file_content(file_id, mime_type="xlsx")
wb = openpyxl.load_workbook(BytesIO(content))

# Option B: Google API 직접 사용 (Service Account)
# 더 안정적, lilychoi 권한 위임 받으면 가능
```

---

## 5. 입고 상태 판단 로직 (확정)

```python
# 입항예정일(ETA) 산출 우선순위
1순위: 진행일지 P열(도착/ETA) 직접 값          ← 가장 신뢰도 높음
2순위: 재고엑셀 'Delivery time' 텍스트 파싱
3순위: PO date + 리드타임(Air 30~45일 / Sea 90~120일)
4순위: 산출 불가 → '확인 필요' 리스트로 분리

# 입고완료 판단
완료    = 진행일지 Q열 '입고'에 날짜 값 존재
미입고  = Q열 비어있음

# 알람 조건
1차 알람 (입항 D-14):
    조건 = (ETA - 오늘) ≤ 14일 AND Q열 비어있음 AND 이력DB에 미발송
    
2차 알람 (입고완료):
    조건 = Q열에 신규 날짜 입력 감지 AND 이력DB에 미발송
    감지방식 = 전회 스캔 결과 캐시와 diff
    
지연 경보 (선택):
    조건 = ETA 경과 + Q열 비어있음 + 이력DB에 미발송
    
발송 제외 = 이력DB에 발송 기록 존재
```

---

## 6. 핵심 함정 정리

| # | 함정 | 대응 |
|---|---|---|
| 1 | MCP read_file_content 행 구분 없음 | download_file_content 사용 |
| 2 | 시트별 컬럼 위치 다름 | 헤더 행 동적 탐지 + sheets_mapping.yaml |
| 3 | '이경' 고객명 빈출 | 풀네임 '조이경'으로만 매칭 |
| 4 | M열 매장 약칭(현본/신강/판) | 4인 이름과 무관, 영업사원 매칭과 별개 |
| 5 | 분리선적 (`6/4, 7/8`) | 2건으로 분리하여 각각 처리 |
| 6 | 모호 일정 (`7월말~8월초`) | 자동 파싱 포기, '확인 필요' 분리 |
| 7 | 추승민 E열 미등장 | R&R 정책 별도 결정 (TBD) |
| 8 | 재고엑셀 M열에 4인 이름 없음 | 재고엑셀의 '선점' 정의 재검토 필요 |
