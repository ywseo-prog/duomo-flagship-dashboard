# Duomo&Co Dashboard — Design System v0.4

**Concept**: 바우하우스 기능미학 × 하이엔드 리테일 × 핀테크 데이터 밀도

레퍼런스 시안 5종 분석 기반 (Whale Loans · Finexy · HR Team · HEALTHIST · Naver 부동산)을 Duomo 톤으로 융합.

---

## ■ Color Tokens

| Role | HEX | 용도 |
|---|---|---|
| `--bg-base` | `#F8F8F8` | 페이지 배경 (오프화이트) |
| `--bg-panel` | `#FFFFFF` | 카드·패널 배경 |
| `--bg-dark` | `#0A0A0A` | KPI 강조 블랙 패널 (시안 1·2 차용) |
| `--bg-dark-soft` | `#1A1A1A` | 블랙 내부 보조 |
| `--accent-gold` | `#C9A961` | 메탈릭 골드 (Duomo 톤, 강조선·VIP) |
| `--accent-orange` | `#FF6B35` | 긴급·액션 (시안 2 차용) |
| `--accent-green` | `#2E7D32` | 성공·매출 상승 |
| `--accent-red` | `#D32F2F` | 위험·하락·결품 |
| `--accent-blue` | `#1976D2` | 정보·진행중 |
| `--text-primary` | `#0A0A0A` | 본문 |
| `--text-secondary` | `#555555` | 보조 텍스트 |
| `--text-muted` | `#999999` | 캡션·placeholder |
| `--text-on-dark` | `#FFFFFF` | 블랙 패널 위 텍스트 |
| `--text-on-dark-soft` | `#BBBBBB` | 블랙 패널 위 보조 |
| `--border` | `#E8E8E8` | 1px solid 보더 |
| `--shadow` | `0 2px 8px rgba(0,0,0,0.04)` | 카드 그림자 |

### Category Colors (캘린더 이벤트)

| 분류 | HEX |
|---|---|
| 발주마감 | `#D32F2F` |
| 매장이벤트 | `#1976D2` |
| 시몬스미팅 | `#7B1FA2` |
| VIP컨설팅 | `#C2185B` |
| 인플루언서협찬 | `#F57C00` |
| 교육 | `#388E3C` |
| 휴가 | `#9E9E9E` |
| 회의 | `#455A64` |
| 출장 | `#5D4037` |
| 기타 | `#607D8B` |

---

## ■ Typography

| Role | Font | Size | Weight | 비고 |
|---|---|---|---|---|
| H1 (페이지 타이틀) | Pretendard + Inter | 28px | 800 | border-bottom 2px |
| H2 (섹션) | Pretendard | 18px | 700 | |
| H3 (서브섹션) | Pretendard | 15px | 600 | |
| Body | Pretendard | 14px | 400 | |
| Caption | Pretendard | 12px | 400 | color: --text-secondary |
| KPI Value (블랙 패널) | Inter | 32px | 800 | letter-spacing: -0.5px |
| KPI Label | Pretendard | 11px | 500 | uppercase, letter-spacing: 0.8px |
| Greeting | Pretendard | 22px | 700 | |
| Badge | Inter | 10px | 700 | uppercase |

**Web fonts**: Google Fonts (Inter) + cdn.jsdelivr.net (Pretendard)

---

## ■ Spacing & Radius

| Token | Value |
|---|---|
| `--radius-card` | `12px` |
| `--radius-btn` | `8px` |
| `--radius-badge` | `4px` |
| `--gap-section` | `24px` |
| `--gap-card` | `16px` |
| `--padding-card` | `20px` |
| `--padding-card-dark` | `24px` |

---

## ■ Components

### Black KPI Panel (시안 1·2 차용)
```
+----------------------------+
| LABEL (uppercase, 11px)    |
| 32px VALUE (white, 800)    |
| +12.3% MoM (orange 14px)   |
+----------------------------+
배경 #0A0A0A, 라운드 12px, padding 24px
```

### Multi-Card Row (시안 2 multi-wallet)
3개 카드 가로 나열, 각각:
- 채널명 (작게)
- 큰 숫자 (28px)
- 우측 작은 차트 또는 트렌드 아이콘

### Greeting Header
```
🌅 Good morning, [Name]
Today, [Date] · [Day of week]
```

### Status Badge
- 라운드 4px · padding 4px 8px · 글자 10px · uppercase
- 색상: `--accent-blue` 등 상황별 자동

### Funnel (시안 3 추세)
- 5~8단계 가로 깔때기
- 각 단계 색상 그라데이션
- value + % 동시 표시

### Today's Timeline (시안 4 차용)
- 시간순 세로 리스트
- 좌측 컬러 바 (분류색)
- 시간 + 제목 + 담당자

### Activity Table (시안 2 Recent Activities)
- 컬럼: ID / Activity / Price / Status / Date
- Status는 컬러 배지

### Hospital Activity Floor Plan → Brand Map (시안 4 변형)
- 백화점 매장 평면도 시각화 자리 (추후)

### Patient by Condition Donut → VIP Tier (시안 4 차용)
- VIP / 일반 / 신규 비중 도넛

### Wallet 3-Card (시안 2)
- 플래그십 / 백화점 / 온라인 채널 매출

---

## ■ Responsive Breakpoints

| Device | Width | Streamlit 적용 |
|---|---|---|
| Mobile | < 768px | 1열 스택 |
| Tablet | 768–1024px | 2열 |
| Desktop | > 1024px | 3-4열 (`st.columns(N)`) |

Streamlit 기본 반응형 + 커스텀 CSS로 mobile 시 카드 size·spacing 조정.

---

## ■ Dark Patterns (블랙 패널 활용 가이드)

블랙 패널은 **데이터 강조**용. 무분별한 사용 금지.

- ✓ KPI Top 4 (월 매출·전월 대비·일평균·MoM)
- ✓ 결품 SKU 카운트 (발주 모듈)
- ✓ AIR 긴급 카운트
- ✗ 일반 테이블 / 차트 컨테이너
- ✗ 폼 입력 영역

---

## ■ Chart Style Guide

- Plotly 기본 테마: `plotly_white`
- Bar 단색: `#0A0A0A` (강조) / `#C9A961` (golden) / `#1976D2` (info)
- Funnel: 그라데이션 (다크블루 → 골드 → 그린)
- Donut: `#0A0A0A` · `#C9A961` · `#999999` · `#E8E8E8` (4단계 시)
- 축 텍스트: 11px / `#555555`
- 그리드: 점선 `#E8E8E8`

---

© Duomo&Co 2026 — Design System v0.4
