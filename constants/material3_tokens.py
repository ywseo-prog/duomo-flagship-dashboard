"""Material 3 (Material You) Design Tokens — Duomo Gold 적응판

[참조]
- Google Material 3: https://m3.material.io
- 사용자 인계: Material 3 Design Kit (Community).fig

[색상 시스템]
Duomo Gold (#C9A961)를 Primary로 두고, M3 Tonal Palette 자동 생성.
0(가장 어둡) → 100(가장 밝음) 단계로 11 톤.

[표준 토큰]
- color roles: primary / secondary / tertiary / error / surface / background
- type scale: display / headline / title / body / label (각 large/medium/small)
- shape scale: none / xs / sm / md / lg / xl (corner radius)
- elevation: 0~5 (그림자 5단계)
- state layers: hover 8% / focus·pressed 12% / dragged 16%
- motion: standard / emphasized / spring (easing curves + duration)
"""

# ============================================================
# 1. COLOR (Duomo Gold Tonal Palette + M3 standard roles)
# ============================================================

# Tonal Palettes (각 키 컬러의 11단계)
TONAL_PALETTES = {
    "primary": {  # Gold #C9A961 base (~tone 60)
        0:   "#000000",
        10:  "#241A00",
        20:  "#3E2E00",
        30:  "#5A4400",
        40:  "#785B00",   # primary container dark
        50:  "#9A7700",
        60:  "#BE9526",   # core gold (Duomo)
        70:  "#C9A961",   # ★ Duomo signature gold
        80:  "#E8C97E",
        90:  "#F5E0AE",
        95:  "#FBEDD3",
        99:  "#FFFBF0",
        100: "#FFFFFF",
    },
    "secondary": {  # Warm beige (gold complement)
        0:   "#000000",
        10:  "#221A0B",
        20:  "#382F1E",
        30:  "#4F4533",
        40:  "#675C48",
        50:  "#807460",
        60:  "#9B8E78",
        70:  "#B6A892",
        80:  "#D3C3AC",
        90:  "#F0DFC8",
        95:  "#FFEED5",
        99:  "#FFFBF0",
        100: "#FFFFFF",
    },
    "tertiary": {  # Cool blue accent (data viz contrast)
        0:   "#000000",
        10:  "#001F2F",
        20:  "#003547",
        30:  "#004D65",
        40:  "#1976D2",   # ★ data/info accent
        50:  "#3D8AE0",
        60:  "#5A9EE9",
        70:  "#7BB3F2",
        80:  "#A2D2FF",
        90:  "#D1E9FF",
        95:  "#E9F4FF",
        99:  "#F8FBFF",
        100: "#FFFFFF",
    },
    "error": {
        0:   "#000000",
        10:  "#410002",
        20:  "#690005",
        30:  "#93000A",
        40:  "#B3261E",   # ★ M3 standard
        50:  "#DC362E",
        60:  "#E46962",
        70:  "#EC928E",
        80:  "#F2B8B5",
        90:  "#F9DEDC",
        95:  "#FCEEEE",
        99:  "#FFFBF9",
        100: "#FFFFFF",
    },
    "neutral": {  # Surface / background (Duomo off-white base)
        0:   "#000000",
        4:   "#0A0A0A",   # ★ Duomo black
        6:   "#101010",
        10:  "#1A1A1A",
        12:  "#1E1E1E",
        17:  "#2A2A2A",
        20:  "#333333",
        22:  "#383838",
        24:  "#3D3D3D",
        30:  "#4F4F4F",
        40:  "#666666",
        50:  "#808080",
        60:  "#999999",
        70:  "#B3B3B3",
        80:  "#CCCCCC",
        87:  "#DDDDDD",
        90:  "#E8E8E8",
        92:  "#ECECEC",
        94:  "#F0F0F0",
        95:  "#F5F5F5",
        96:  "#F8F8F8",   # ★ Duomo off-white
        98:  "#FAFAFA",
        99:  "#FCFCFC",
        100: "#FFFFFF",
    },
}


# Light scheme — 표준 사용
LIGHT_SCHEME = {
    "primary":              TONAL_PALETTES["primary"][70],     # #C9A961 Duomo gold
    "on_primary":           TONAL_PALETTES["neutral"][100],
    "primary_container":    TONAL_PALETTES["primary"][90],
    "on_primary_container": TONAL_PALETTES["primary"][10],
    "secondary":            TONAL_PALETTES["secondary"][40],
    "on_secondary":         TONAL_PALETTES["neutral"][100],
    "secondary_container":  TONAL_PALETTES["secondary"][90],
    "on_secondary_container":TONAL_PALETTES["secondary"][10],
    "tertiary":             TONAL_PALETTES["tertiary"][40],    # #1976D2 blue
    "on_tertiary":          TONAL_PALETTES["neutral"][100],
    "tertiary_container":   TONAL_PALETTES["tertiary"][90],
    "on_tertiary_container":TONAL_PALETTES["tertiary"][10],
    "error":                TONAL_PALETTES["error"][40],
    "on_error":             TONAL_PALETTES["neutral"][100],
    "error_container":      TONAL_PALETTES["error"][90],
    "on_error_container":   TONAL_PALETTES["error"][10],
    "background":           TONAL_PALETTES["neutral"][96],     # #F8F8F8
    "on_background":        TONAL_PALETTES["neutral"][4],      # #0A0A0A
    "surface":              TONAL_PALETTES["neutral"][96],
    "on_surface":           TONAL_PALETTES["neutral"][4],
    "surface_variant":      TONAL_PALETTES["neutral"][90],
    "on_surface_variant":   TONAL_PALETTES["neutral"][30],
    "surface_container_lowest": TONAL_PALETTES["neutral"][100],
    "surface_container_low":TONAL_PALETTES["neutral"][98],
    "surface_container":    TONAL_PALETTES["neutral"][95],
    "surface_container_high":TONAL_PALETTES["neutral"][94],
    "surface_container_highest":TONAL_PALETTES["neutral"][90],
    "outline":              TONAL_PALETTES["neutral"][50],
    "outline_variant":      TONAL_PALETTES["neutral"][80],
    "scrim":                TONAL_PALETTES["neutral"][0],
    "shadow":               TONAL_PALETTES["neutral"][0],
}


# ============================================================
# 2. TYPOGRAPHY — M3 Type Scale
# ============================================================
# Font: Pretendard (KR) + Inter (EN/digits) — 우리 design_system v0.4 유지
TYPE_SCALE = {
    "display_large":   {"size": 57, "line": 64, "weight": 400, "tracking": -0.25},
    "display_medium":  {"size": 45, "line": 52, "weight": 400, "tracking": 0},
    "display_small":   {"size": 36, "line": 44, "weight": 400, "tracking": 0},
    "headline_large":  {"size": 32, "line": 40, "weight": 400, "tracking": 0},
    "headline_medium": {"size": 28, "line": 36, "weight": 400, "tracking": 0},
    "headline_small":  {"size": 24, "line": 32, "weight": 400, "tracking": 0},
    "title_large":     {"size": 22, "line": 28, "weight": 500, "tracking": 0},
    "title_medium":    {"size": 16, "line": 24, "weight": 500, "tracking": 0.15},
    "title_small":     {"size": 14, "line": 20, "weight": 500, "tracking": 0.1},
    "body_large":      {"size": 16, "line": 24, "weight": 400, "tracking": 0.5},
    "body_medium":     {"size": 14, "line": 20, "weight": 400, "tracking": 0.25},
    "body_small":      {"size": 12, "line": 16, "weight": 400, "tracking": 0.4},
    "label_large":     {"size": 14, "line": 20, "weight": 500, "tracking": 0.1},
    "label_medium":    {"size": 12, "line": 16, "weight": 500, "tracking": 0.5},
    "label_small":     {"size": 11, "line": 16, "weight": 500, "tracking": 0.5},
}


# ============================================================
# 3. SHAPE — M3 Corner Radius
# ============================================================
SHAPE_SCALE = {
    "none":          0,
    "extra_small":   4,
    "small":         8,
    "medium":        12,
    "large":         16,
    "extra_large":   28,
    "full":          9999,  # pill / circle
}


# ============================================================
# 4. ELEVATION — M3 Shadow Levels 0~5
# ============================================================
ELEVATION = {
    0: "none",
    1: "0px 1px 2px 0px rgba(0,0,0,0.30), 0px 1px 3px 1px rgba(0,0,0,0.15)",
    2: "0px 1px 2px 0px rgba(0,0,0,0.30), 0px 2px 6px 2px rgba(0,0,0,0.15)",
    3: "0px 4px 8px 3px rgba(0,0,0,0.15), 0px 1px 3px 0px rgba(0,0,0,0.30)",
    4: "0px 6px 10px 4px rgba(0,0,0,0.15), 0px 2px 3px 0px rgba(0,0,0,0.30)",
    5: "0px 8px 12px 6px rgba(0,0,0,0.15), 0px 4px 4px 0px rgba(0,0,0,0.30)",
}


# ============================================================
# 5. STATE LAYERS — interaction opacity
# ============================================================
STATE_OPACITY = {
    "hover":   0.08,
    "focus":   0.12,
    "pressed": 0.12,
    "dragged": 0.16,
    "selected":0.08,
}


# ============================================================
# 6. MOTION — Standard / Emphasized
# ============================================================
EASING = {
    "standard":          "cubic-bezier(0.2, 0.0, 0, 1.0)",
    "standard_accelerate":"cubic-bezier(0.3, 0.0, 1.0, 1.0)",
    "standard_decelerate":"cubic-bezier(0.0, 0.0, 0.0, 1.0)",
    "emphasized":        "cubic-bezier(0.2, 0.0, 0, 1.0)",
    "emphasized_accelerate":"cubic-bezier(0.3, 0.0, 0.8, 0.15)",
    "emphasized_decelerate":"cubic-bezier(0.05, 0.7, 0.1, 1.0)",
}

DURATION = {
    "short_1":   50,
    "short_2":   100,
    "short_3":   150,
    "short_4":   200,
    "medium_1":  250,
    "medium_2":  300,
    "medium_3":  350,
    "medium_4":  400,
    "long_1":    450,
    "long_2":    500,
    "long_3":    550,
    "long_4":    600,
    "extra_long_1": 700,
    "extra_long_2": 800,
    "extra_long_3": 900,
    "extra_long_4": 1000,
}


# ============================================================
# 7. CSS 변수 생성 헬퍼
# ============================================================
def build_css_variables() -> str:
    """M3 토큰 전체를 :root CSS 변수로 export."""
    lines = [":root {"]
    # Color roles
    for role, hex_v in LIGHT_SCHEME.items():
        lines.append(f"  --m3-{role.replace('_', '-')}: {hex_v};")
    # Tonal palettes (전체 11단계 노출)
    for palette_name, tones in TONAL_PALETTES.items():
        for tone, hex_v in tones.items():
            lines.append(f"  --m3-{palette_name}-{tone}: {hex_v};")
    # Shape
    for name, val in SHAPE_SCALE.items():
        lines.append(f"  --m3-shape-{name.replace('_', '-')}: {val}px;")
    # Elevation
    for lvl, shadow in ELEVATION.items():
        lines.append(f"  --m3-elevation-{lvl}: {shadow};")
    # Type sizes only (간소화 — modules에서 직접 사용)
    for role, spec in TYPE_SCALE.items():
        slug = role.replace('_', '-')
        lines.append(f"  --m3-type-{slug}-size: {spec['size']}px;")
        lines.append(f"  --m3-type-{slug}-line: {spec['line']}px;")
        lines.append(f"  --m3-type-{slug}-weight: {spec['weight']};")
    # Motion
    for name, curve in EASING.items():
        lines.append(f"  --m3-easing-{name.replace('_', '-')}: {curve};")
    for name, ms in DURATION.items():
        lines.append(f"  --m3-duration-{name.replace('_', '-')}: {ms}ms;")
    lines.append("}")
    return "\n".join(lines)


# ============================================================
# 편의 alias (외부 import 호환)
# ============================================================
PRIMARY = LIGHT_SCHEME["primary"]                 # #C9A961
ON_PRIMARY = LIGHT_SCHEME["on_primary"]
PRIMARY_CONTAINER = LIGHT_SCHEME["primary_container"]
SECONDARY = LIGHT_SCHEME["secondary"]
TERTIARY = LIGHT_SCHEME["tertiary"]
ERROR = LIGHT_SCHEME["error"]
SURFACE = LIGHT_SCHEME["surface"]
ON_SURFACE = LIGHT_SCHEME["on_surface"]
OUTLINE = LIGHT_SCHEME["outline"]
