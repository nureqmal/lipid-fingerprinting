import streamlit as st
import pandas as pd
import io
import json
import os

st.set_page_config(page_title="Lipid EQ", layout="wide", page_icon="⚗️")

# ─── BLACKLIST PERSISTENCE ────────────────────────────────────────────────────
BLACKLIST_CONFIG_FILE = "blacklist_config.json"
DEFAULT_BLACKLIST = ['siloxane', 'phthalate', 'octaxilonaxe', 'bleed', 'plasticizer', 'adipate', 'column bleed']
CONTAMINANTS = ['iodo', 'chloro', 'bromo', 'fluoro', 'iodide', 'chloride', 'thiophene', 'benzo', 'benza', 'cyclo', 'sulphur', 'benzothiophene', 'naphthalene', 'benzene,']

def load_blacklist():
    if os.path.exists(BLACKLIST_CONFIG_FILE):
        try:
            with open(BLACKLIST_CONFIG_FILE, 'r') as f:
                return json.load(f).get('blacklist', DEFAULT_BLACKLIST)
        except Exception:
            pass
    return DEFAULT_BLACKLIST.copy()

def save_blacklist(bl):
    with open(BLACKLIST_CONFIG_FILE, 'w') as f:
        json.dump({'blacklist': bl}, f, indent=2)

if 'blacklist' not in st.session_state:
    st.session_state.blacklist = load_blacklist()
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# ─── THEME ───────────────────────────────────────────────────────────────────
def T():
    if st.session_state.dark_mode:
        return {
            "bg":        "#080d1a",
            "bg2":       "#0d1428",
            "bg3":       "#111c36",
            "surface":   "#111c36",
            "border":    "#1e3060",
            "border2":   "#2a4278",
            "navy":      "#050b18",
            "accent":    "#3dd6c8",
            "accent2":   "#4f8ef7",
            "gold":      "#d4a017",
            "text":      "#d0ddf0",
            "muted":     "#7a90b0",
            "hint":      "#4a6080",
            "danger":    "#ff6b6b",
            "warn":      "#ffa502",
            "success":   "#3dd6c8",
            "red_row":   "#1a0505",
            "yel_row":   "#1a1500",
            "pink_row":  "#1a0510",
        }
    return {
        "bg":        "#f4f6fb",
        "bg2":       "#ffffff",
        "bg3":       "#edf0f8",
        "surface":   "#f0f3fa",
        "border":    "#c8d0e0",
        "border2":   "#9aa8c8",
        "navy":      "#0d1b3e",
        "accent":    "#0a8c7e",
        "accent2":   "#1a3a8e",
        "gold":      "#b8860b",
        "text":      "#0d1b3e",
        "muted":     "#4a5568",
        "hint":      "#8896b0",
        "danger":    "#c0392b",
        "warn":      "#a0690a",
        "success":   "#0a8c7e",
        "red_row":   "#fdf0f0",
        "yel_row":   "#fffbe6",
        "pink_row":  "#fdf0f6",
    }

def css():
    t = T()
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background-color: {t['bg']} !important;
    color: {t['text']} !important;
    font-family: 'Inter', sans-serif !important;
}}

[data-testid="stSidebar"] {{
    background: {t['navy']} !important;
    border-right: 1px solid {t['border']} !important;
}}
[data-testid="stSidebar"] * {{ color: #c8d8f0 !important; font-family: 'Inter', sans-serif !important; }}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {t['accent']} !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
}}

section.main > div {{ padding-top: 0.4rem !important; }}
h1, h2, h3 {{ color: {t['text']} !important; font-family: 'Inter', sans-serif !important; }}
hr {{ border-color: {t['border']} !important; margin: 0.6rem 0 !important; }}

[data-testid="stMetric"] {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    padding: 14px 12px !important;
    border-top: 3px solid {t['accent']} !important;
}}
[data-testid="metric-container"] {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    padding: 14px 12px !important;
    border-top: 3px solid {t['accent']} !important;
}}
[data-testid="stMetricValue"] {{
    color: {t['text']} !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
[data-testid="stMetricLabel"] {{
    color: {t['muted']} !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    padding: 4px !important;
    gap: 3px !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 6px !important;
    color: {t['hint']} !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border: none !important;
    padding: 6px 10px !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {t['navy']} !important;
    color: {t['accent']} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}

[data-testid="stDataFrame"] {{
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    background: {t['bg2']} !important;
}}
[data-testid="stDataFrame"] thead tr th {{
    background: {t['navy']} !important;
    color: {t['accent']} !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}}

[data-testid="stButton"] > button {{
    background: linear-gradient(135deg, {t['accent']}, {t['accent2']}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.76rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    padding: 8px 16px !important;
    transition: opacity 0.2s !important;
}}
[data-testid="stButton"] > button:hover {{ opacity: 0.85 !important; }}

[data-testid="stDownloadButton"] > button {{
    background: {t['accent']} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 700 !important;
    font-size: 0.76rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    padding: 8px 20px !important;
}}

[data-testid="stFileUploader"] {{
    background: {t['bg2']} !important;
    border: 2px dashed {t['border']} !important;
    border-radius: 8px !important;
    padding: 8px !important;
}}
[data-testid="stFileUploader"]:hover {{ border-color: {t['accent']} !important; }}
[data-testid="stFileUploader"] label {{ color: {t['text']} !important; font-weight: 600 !important; font-size: 0.78rem !important; }}
[data-testid="stFileUploader"] small {{ color: {t['hint']} !important; }}

[data-testid="stSlider"] > div > div > div > div {{ background: {t['accent']} !important; }}
[data-testid="stSlider"] label {{
    color: #9ab0d0 !important;
    font-size: 0.76rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {{
    color: {t['hint']} !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.68rem !important;
}}

[data-testid="stTextInput"] input {{
    background: #0a1228 !important;
    border: 1px solid {t['border']} !important;
    border-radius: 6px !important;
    color: #c8d8f0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {t['accent']} !important;
    box-shadow: 0 0 0 3px {t['accent']}30 !important;
}}
[data-testid="stTextInput"] label {{
    color: {t['hint']} !important;
    font-size: 0.72rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

[data-testid="stAlert"] {{
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-family: 'Inter', sans-serif !important;
}}

[data-testid="stTable"] table {{
    background: {t['bg2']} !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
}}
[data-testid="stTable"] th {{
    background: {t['navy']} !important;
    color: {t['accent']} !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}}
[data-testid="stTable"] td {{
    color: {t['text']} !important;
    border-color: {t['border']} !important;
}}

[data-testid="stProgress"] > div > div {{ background: {t['accent']} !important; }}

::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {t['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {t['border2']}; border-radius: 3px; }}

[data-testid="stCaptionContainer"] {{
    color: {t['hint']} !important;
    font-size: 0.72rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
</style>
"""

st.markdown(css(), unsafe_allow_html=True)

# ─── HEADER ──────────────────────────────────────────────────────────────────
t = T()
st.markdown(f"""
<div style="
    background:{t['navy']};
    border-radius:10px;
    padding:14px 22px;
    margin-bottom:16px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    border-bottom:3px solid {t['accent']};
">
    <div style="display:flex;align-items:center;gap:14px;">
        <div style="
            width:44px;height:44px;border-radius:8px;
            background:linear-gradient(135deg,{t['accent']},{t['accent2']});
            display:flex;align-items:center;justify-content:center;
        ">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M9 3h6v7l3 4v6H6v-6l3-4V3z" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="M9 10h6M11 3v4M13 3v4" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
                <circle cx="12" cy="17" r="2" fill="white" opacity="0.9"/>
            </svg>
        </div>
        <div>
            <div style="font-size:18px;font-weight:700;color:#ffffff;letter-spacing:-0.01em;font-family:'Inter',sans-serif;">
                Lipid <span style="color:{t['accent']};">EQ</span>
            </div>
            <div style="font-size:10px;color:#7a90b0;letter-spacing:0.12em;text-transform:uppercase;font-family:'JetBrains Mono',monospace;margin-top:1px;">
                GC-MS Analytical Platform
            </div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
        <span style="background:{t['accent']}20;color:{t['accent']};font-size:10px;font-weight:700;padding:4px 12px;border-radius:4px;border:1px solid {t['accent']}50;font-family:'JetBrains Mono',monospace;letter-spacing:0.08em;">
            HALAL ANALYTICS
        </span>
        <span style="background:#ffffff10;color:#7a90b0;font-size:10px;padding:4px 10px;border-radius:4px;border:1px solid #ffffff20;font-family:'JetBrains Mono',monospace;">
            v2.0
        </span>
        <span style="color:#7a90b0;font-size:10px;font-family:'JetBrains Mono',monospace;">
            {'🌙 Dark' if st.session_state.dark_mode else '☀️ Light'}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 10px;">
        <div style="font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{t['accent']};font-family:'JetBrains Mono',monospace;">
            ⚗️ Control Panel
        </div>
    </div>
    """, unsafe_allow_html=True)

    mode_lbl = "☀️ Switch to Light" if st.session_state.dark_mode else "🌙 Switch to Dark"
    if st.button(mode_lbl, use_container_width=True, key="theme_btn"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown(f"""<div style="font-size:9px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{t['accent']};font-family:'JetBrains Mono',monospace;margin-bottom:8px;">⚙️ Analytical Controls</div>""", unsafe_allow_html=True)

    q_threshold = st.slider("NIST Quality Threshold", 50, 95, 80, 5,
        help="Filters compound identity accuracy. (Default: 80)")
    rt_tolerance = st.slider("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
        help="Time error limit for Sample vs Blank. (Default: 0.05)")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
        help="Removes small peaks/noise. (Default: 0.00)")

    st.markdown("---")
    st.markdown(f"""<div style="font-size:9px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:{t['accent']};font-family:'JetBrains Mono',monospace;margin-bottom:6px;">🚫 Blacklist Manager</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="font-size:10px;color:#4a6080;font-family:'JetBrains Mono',monospace;margin-bottom:10px;line-height:1.5;">Compounds whose name contains any keyword will be excluded. Saved across sessions.</div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="font-size:10px;font-weight:600;color:#9ab0d0;font-family:'JetBrains Mono',monospace;margin-bottom:6px;">Active keywords ({len(st.session_state.blacklist)})</div>""", unsafe_allow_html=True)
    for kw in st.session_state.blacklist:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"""
        <div style="background:#0a1228;border:1px solid #1e3060;border-radius:4px;
            padding:4px 10px;font-size:10px;color:#7ab0d0;margin-bottom:2px;
            font-family:'JetBrains Mono',monospace;letter-spacing:0.04em;">
            {kw}
        </div>""", unsafe_allow_html=True)
        if c2.button("✕", key=f"rm_{kw}", help=f"Remove '{kw}'"):
            st.session_state.blacklist.remove(kw)
            save_blacklist(st.session_state.blacklist)
            st.rerun()

    st.markdown(f"""<div style="font-size:10px;font-weight:600;color:#9ab0d0;font-family:'JetBrains Mono',monospace;margin:10px 0 4px;">Add keyword</div>""", unsafe_allow_html=True)
    new_kw = st.text_input("New keyword", placeholder="e.g. trimethylsilyl", label_visibility="collapsed", key="new_kw")
    if st.button("➕ Add to Blacklist", use_container_width=True):
        cleaned = new_kw.strip().lower()
        if not cleaned:
            st.warning("Enter a keyword first.")
        elif cleaned in st.session_state.blacklist:
            st.warning(f"'{cleaned}' already exists.")
        else:
            st.session_state.blacklist.append(cleaned)
            save_blacklist(st.session_state.blacklist)
            st.success(f"Added: {cleaned}")
            st.rerun()

    st.markdown("")
    if st.button("↺ Reset to Default", use_container_width=True, key="reset_bl"):
        st.session_state.blacklist = DEFAULT_BLACKLIST.copy()
        save_blacklist(st.session_state.blacklist)
        st.rerun()

    st.markdown("---")
    sop_steps = [
        "Metadata preserved (rows 1–9)",
        f"Quality gate ≥ {q_threshold}",
        f"Noise cut &lt; {area_threshold:.2f}%",
        f"RT matching ±{rt_tolerance} min",
        f"Blacklist filter ({len(st.session_state.blacklist)} keywords)",
    ]
    st.markdown(f"""
    <div style="background:#0a1228;border:1px solid #1e3060;border-radius:8px;padding:12px;">
        <div style="font-size:9px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
            color:{t['accent']};margin-bottom:10px;font-family:'JetBrains Mono',monospace;">
            📋 SOP Summary
        </div>
        {"".join([f'''
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:7px;">
            <div style="width:18px;height:18px;border-radius:3px;
                background:linear-gradient(135deg,{t['accent']},{t['accent2']});
                display:flex;align-items:center;justify-content:center;
                font-size:9px;font-weight:700;color:#fff;flex-shrink:0;
                font-family:'JetBrains Mono',monospace;">{i}</div>
            <div style="font-size:10px;color:#7a90b0;line-height:1.5;font-family:'JetBrains Mono',monospace;">{s}</div>
        </div>''' for i, s in enumerate(sop_steps, 1)])}
    </div>
    """, unsafe_allow_html=True)

# ─── CORE LOGIC (UNTOUCHED) ───────────────────────────────────────────────────
def classify_compound(name):
    n = str(name).lower()
    if any(x in n for x in st.session_state.blacklist): return "Discard (Artifact)"
    if any(x in n for x in CONTAMINANTS): return "Review (Potential Contaminant)"
    return "Clean (Lipid/Oxidation)"

def get_matched_keywords(name):
    n = str(name).lower()
    return ', '.join([kw for kw in st.session_state.blacklist if kw in n])

def run_strict_procedure(file, q_min, area_min):
    df_full_raw = pd.read_excel(file, sheet_name='LibRes', header=None)
    df_header = df_full_raw.iloc[0:9, :].copy()
    df = pd.read_excel(file, sheet_name='LibRes', header=8)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=['RT (min)', 'Area (Ab*s)']).copy()
    df['Quality'] = pd.to_numeric(df['Quality'], errors='coerce')
    total_area = df['Area (Ab*s)'].sum()
    df['Area (%)'] = (df['Area (Ab*s)'] / total_area) * 100
    df = df[(df['Quality'] >= q_min) & (df['Area (%)'] >= area_min)]
    df['Chemical_Status'] = df['Hit Name'].apply(classify_compound)
    df_excluded = df[df['Chemical_Status'] == "Discard (Artifact)"].copy()
    df_excluded['Matched Keyword'] = df_excluded['Hit Name'].apply(get_matched_keywords)
    df_excluded = df_excluded.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first').sort_values(by='RT (min)')
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return df_header, df.sort_values(by='RT (min)'), df_excluded

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, r in matches.iterrows():
        if abs(row['RT (min)'] - r['RT (min)']) <= tol:
            return "YES", abs(row['RT (min)'] - r['RT (min)'])
    return "RT_SHIFT_DETECTED", matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()

# ─── UI HELPERS ───────────────────────────────────────────────────────────────
def sec_hdr(title, sub=""):
    t = T()
    st.markdown(f"""
    <div style="margin:16px 0 10px;padding-bottom:8px;border-bottom:1px solid {t['border']};">
        <div style="display:flex;align-items:center;gap:8px;">
            <div style="width:4px;height:16px;border-radius:2px;background:linear-gradient(180deg,{t['accent']},{t['accent2']});"></div>
            <div style="font-size:12px;font-weight:700;color:{t['text']};font-family:'Inter',sans-serif;">{title}</div>
        </div>
        {f'<div style="font-size:10px;color:{t["hint"]};margin-top:3px;margin-left:12px;font-family:JetBrains Mono,monospace;">{sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)

def info_card(msg, color=None):
    t = T()
    c = color or t['accent']
    st.markdown(f"""
    <div style="background:{c}12;border:1px solid {c}40;border-left:3px solid {c};
        border-radius:0 8px 8px 0;padding:10px 14px;font-size:11px;
        color:{t['text']};margin-bottom:10px;line-height:1.6;font-family:'Inter',sans-serif;">
        {msg}
    </div>
    """, unsafe_allow_html=True)

def kw_pills(keywords, danger_color):
    pills = "".join([
        f'<span style="background:{danger_color}18;color:{danger_color};'
        f'border:1px solid {danger_color}40;border-radius:4px;'
        f'padding:2px 9px;font-size:10px;font-weight:600;margin:2px;'
        f'display:inline-block;font-family:JetBrains Mono,monospace;'
        f'letter-spacing:0.04em;">{kw}</span>'
        for kw in keywords
    ])
    return pills

def upload_label(text, color):
    st.markdown(f"""
    <div style="font-size:10px;font-weight:700;color:{color};
        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;
        font-family:'JetBrains Mono',monospace;display:flex;align-items:center;gap:6px;">
        <div style="width:8px;height:8px;border-radius:50%;background:{color};"></div>
        {text}
    </div>
    """, unsafe_allow_html=True)

# ─── MAIN TABS ────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["01 · Single File Analysis", "02 · Multi-File PCA Matrix"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    t = T()
    info_card(f"⚠️ Upload your <b>Sample</b> and <b>Blank</b> files in <b>.xlsx</b> format to begin the Lipid EQ pipeline.", t['warn'])

    col1, col2 = st.columns(2)
    with col1:
        upload_label("Sample File", t['accent'])
        sample_file = st.file_uploader("sample", type=['xlsx'], key="s_file", label_visibility="collapsed")
    with col2:
        upload_label("Blank File", t['accent2'])
        blank_file = st.file_uploader("blank", type=['xlsx'], key="b_file", label_visibility="collapsed")

    if sample_file and blank_file:
        try:
            h_s, df_s, df_s_excl = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b, df_b_excl = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]
            res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
            df_b['In_Sample'] = [x[0] for x in res_b]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            total_s = len(df_s)
            excl_blank = len(df_s[df_s['In_Blank'] == "YES"])
            final_n = len(df_final)
            purity = (final_n / total_s * 100) if total_s > 0 else 0

            # METRICS
            t = T()
            st.markdown(f"""
            <div style="margin:16px 0 8px;display:flex;align-items:center;gap:10px;">
                <div style="font-size:13px;font-weight:700;color:{t['text']};font-family:'Inter',sans-serif;">
                    Pipeline Results
                </div>
                <div style="font-size:10px;color:{t['hint']};font-family:'JetBrains Mono',monospace;
                    background:{t['bg3']};border:1px solid {t['border']};border-radius:4px;padding:2px 8px;">
                    {sample_file.name}
                </div>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Peaks", total_s)
            m2.metric("Blank Purged", excl_blank, delta=f"-{excl_blank}", delta_color="inverse")
            m3.metric("Final Compounds", final_n)
            m4.metric("Purity Score", f"{purity:.1f}%",
                help="(Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100")
            m5.metric("Blacklist Excl.", len(df_s_excl), delta=f"-{len(df_s_excl)}", delta_color="inverse")

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            # INNER TABS
            it1, it2, it3, it4, it5 = st.tabs([
                "01 · Solvent Blank", "02 · Sample Mapping",
                "03 · Final Fingerprint", "04 · RT Analysis", "05 · Excluded"
            ])

            with it1:
                sec_hdr("Solvent Blank Profile", "Yellow = matched in sample  ·  Blue RT cell = RT shift detected")
                def hl_b(row):
                    s = ['' for _ in row.index]
                    if row['In_Sample'] == "YES":
                        return ['background-color:#fffbe6;color:#5a4a00' for _ in row.index]
                    if row['In_Sample'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color:#002060;color:white'
                    return s
                st.dataframe(df_b.style.apply(hl_b, axis=1), use_container_width=True)

            with it2:
                sec_hdr("Sample Compound Mapping", "Yellow = found in blank (shared)  ·  Blue RT = shift detected but retained")
                def hl_s(row):
                    s = ['' for _ in row.index]
                    if row['In_Blank'] == "YES":
                        return ['background-color:#fffbe6;color:#5a4a00' for _ in row.index]
                    if row['In_Blank'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color:#002060;color:white'
                    return s
                st.dataframe(df_s.style.apply(hl_s, axis=1), use_container_width=True)

            with it3:
                sec_hdr("Final Lipid Fingerprint", "Clean compounds after blank subtraction — ready for reporting")
                def hl_f(row):
                    if row.get('Chemical_Status') == "Review (Potential Contaminant)":
                        return ['background-color:#fdf0f6;color:#5a0020' for _ in row.index]
                    return ['' for _ in row.index]
                st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']).style.apply(hl_f, axis=1), use_container_width=True)

            with it4:
                t = T()
                sec_hdr("RT Shift Analysis", "Compounds with retention time deviation between sample and blank")
                rt_iss = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_iss.empty:
                    info_card(f"Found <b>{len(rt_iss)}</b> compound(s) with RT shift — <b>retained</b> in final fingerprint.", t['warn'])
                    st.table(rt_iss[['Hit Name', 'RT (min)', 'RT_Diff']])
                else:
                    st.success("✅ No significant RT shifts detected.")

            with it5:
                t = T()
                sec_hdr("Excluded Blacklist Compounds", "Originally in raw data — removed because name contains a blacklisted keyword")

                st.markdown(f"""
                <div style="background:{t['bg3']};border:1px solid {t['border']};
                    border-radius:8px;padding:12px 16px;margin-bottom:14px;">
                    <div style="font-size:10px;font-weight:700;text-transform:uppercase;
                        letter-spacing:0.08em;color:{t['muted']};
                        font-family:'JetBrains Mono',monospace;margin-bottom:8px;">
                        Active blacklist keywords
                    </div>
                    <div>{kw_pills(st.session_state.blacklist, t['danger'])}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div style="font-size:11px;font-weight:700;color:{t['danger']};
                        font-family:'JetBrains Mono',monospace;margin-bottom:6px;">
                        Sample — Excluded ({len(df_s_excl)})
                    </div>""", unsafe_allow_html=True)
                    if df_s_excl.empty:
                        st.success("No blacklisted compounds in Sample.")
                    else:
                        st.dataframe(
                            df_s_excl.style.apply(lambda r: ['background-color:#fdf0f0;color:#5a0000' for _ in r.index], axis=1),
                            use_container_width=True
                        )
                        st.caption(f"[ {len(df_s_excl)} compound(s) excluded · see 'Matched Keyword' column ]")

                with c2:
                    st.markdown(f"""<div style="font-size:11px;font-weight:700;color:{t['danger']};
                        font-family:'JetBrains Mono',monospace;margin-bottom:6px;">
                        Blank — Excluded ({len(df_b_excl)})
                    </div>""", unsafe_allow_html=True)
                    if df_b_excl.empty:
                        st.success("No blacklisted compounds in Blank.")
                    else:
                        st.dataframe(
                            df_b_excl.style.apply(lambda r: ['background-color:#fdf0f0;color:#5a0000' for _ in r.index], axis=1),
                            use_container_width=True
                        )
                        st.caption(f"[ {len(df_b_excl)} compound(s) excluded · see 'Matched Keyword' column ]")

            # DOWNLOAD
            t = T()
            st.markdown(f"""
            <div style="background:{t['bg2']};border:1px solid {t['border']};border-radius:8px;
                padding:14px 18px;margin-top:12px;border-left:3px solid {t['accent']};">
                <div style="font-size:12px;font-weight:700;color:{t['text']};font-family:'Inter',sans-serif;">
                    Export Report
                </div>
                <div style="font-size:10px;color:{t['hint']};margin-top:2px;font-family:'JetBrains Mono',monospace;">
                    Downloads full .xlsx — Dashboard · Analytical Report · Excluded Compounds sheets
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            dl1, dl2 = st.columns([3, 1])
            with dl1:
                custom_filename = st.text_input("filename", value="SF-HEX-1", key="rename_s",
                    label_visibility="collapsed", placeholder="e.g. SF-HEX-1")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            # BUILD EXCEL
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                hdr_fmt  = wb.add_format({'bold':True,'font_size':13,'bg_color':'#0d1b3e','font_color':'white','border':1,'align':'center','font_name':'Calibri'})
                lbl_fmt  = wb.add_format({'bold':True,'bg_color':'#EEF1FB','border':1,'font_name':'Calibri'})
                val_fmt  = wb.add_format({'border':1,'align':'center','font_name':'Calibri'})
                yel_fmt  = wb.add_format({'bg_color':'#FFEB9C','border':1})
                nav_fmt  = wb.add_format({'bg_color':'#002060','font_color':'white','border':1})
                pnk_fmt  = wb.add_format({'bg_color':'#FFC0CB','border':1})
                red_fmt  = wb.add_format({'bg_color':'#FFD7D7','border':1})
                rhdr_fmt = wb.add_format({'bold':True,'font_size':12,'bg_color':'#c0392b','font_color':'white','border':1,'align':'center','font_name':'Calibri'})
                rsub_fmt = wb.add_format({'bold':True,'bg_color':'#FFD7D7','border':1,'align':'center','font_name':'Calibri'})
                note_fmt = wb.add_format({'italic':True,'font_color':'#c0392b','text_wrap':True,'font_name':'Calibri'})
                kw_fmt   = wb.add_format({'border':1,'text_wrap':True,'font_name':'Calibri'})

                # DASHBOARD
                ws_d = wb.add_worksheet('Dashboard')
                ws_d.merge_range('B2:F2','LIPID EQ — ANALYTICAL SUMMARY REPORT', hdr_fmt)
                ml = [
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance (min)', rt_tolerance),
                    ('Area Threshold (%)', area_threshold),
                    ('Total Sample Peaks', total_s),
                    ('Blank Matches Purged', excl_blank),
                    ('Final Unique Compounds', final_n),
                    ('Purity Score', f"{purity:.2f}%"),
                    ('Active Blacklist Keywords', len(st.session_state.blacklist)),
                    ('Blacklist Excluded (Sample)', len(df_s_excl)),
                    ('Blacklist Excluded (Blank)', len(df_b_excl)),
                ]
                for i,(l,v) in enumerate(ml, start=4):
                    ws_d.write(f'B{i}', l, lbl_fmt); ws_d.write(f'C{i}', v, val_fmt)
                kr = 4+len(ml)+1
                ws_d.write(f'B{kr}','Blacklist Keywords Used', lbl_fmt)
                ws_d.write(f'C{kr}', ', '.join(st.session_state.blacklist), kw_fmt)
                ws_d.set_row(kr-1, 28)
                lr = kr+2
                ws_d.write(f'B{lr}','COLOR LEGEND', wb.add_format({'bold':True,'underline':True,'font_name':'Calibri'}))
                ws_d.write(f'B{lr+1}','Yellow Row', yel_fmt); ws_d.write(f'C{lr+1}','Matched in Blank/Sample')
                ws_d.write(f'B{lr+2}','Blue RT Cell', nav_fmt); ws_d.write(f'C{lr+2}','RT Shift Detected (Retained)')
                ws_d.write(f'B{lr+3}','Pink Cell', pnk_fmt); ws_d.write(f'C{lr+3}','Potential Contaminant')
                ws_d.write(f'B{lr+4}','Red Row', red_fmt); ws_d.write(f'C{lr+4}','Excluded Blacklist Artifact (Full Name Preserved)')
                ws_d.set_column('B:B',32); ws_d.set_column('C:C',80)

                # ANALYTICAL REPORT
                rs = 'Analytical_Report'
                h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
                df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
                s2 = len(df_b)+16
                h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
                df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
                s3 = s2+len(df_s)+15
                fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (Clean Version ✅)"
                fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
                df_final.drop(columns=['In_Blank','RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)
                ws_r = writer.sheets[rs]
                bri = df_b.columns.get_loc('RT (min)'); bmi = df_b.columns.get_loc('In_Sample')
                ws_r.conditional_format(11,0,11+len(df_b),len(df_b.columns)-1,{'type':'formula','criteria':f'=${chr(65+bmi)}12="YES"','format':yel_fmt})
                ws_r.conditional_format(11,bri,11+len(df_b),bri,{'type':'formula','criteria':f'=${chr(65+bmi)}12="RT_SHIFT_DETECTED"','format':nav_fmt})
                sri = df_s.columns.get_loc('RT (min)'); smi = df_s.columns.get_loc('In_Blank')
                ws_r.conditional_format(s2+10,0,s2+10+len(df_s),len(df_s.columns)-1,{'type':'formula','criteria':f'=${chr(65+smi)}{s2+11}="YES"','format':yel_fmt})
                ws_r.conditional_format(s2+10,sri,s2+10+len(df_s),sri,{'type':'formula','criteria':f'=${chr(65+smi)}{s2+11}="RT_SHIFT_DETECTED"','format':nav_fmt})
                fsi = df_final.columns.get_loc('Chemical_Status')
                ws_r.conditional_format(s3+10,fsi,s3+10+len(df_final),fsi,{'type':'cell','criteria':'equal to','value':'"Review (Potential Contaminant)"','format':pnk_fmt})

                # EXCLUDED SHEET
                ws_e = wb.add_worksheet('Excluded_Compounds')
                mc = max(len(df_s_excl.columns) if not df_s_excl.empty else 6, len(df_b_excl.columns) if not df_b_excl.empty else 6)
                lc = chr(64+min(mc,26))
                ws_e.merge_range(f'A1:{lc}1','⛔ EXCLUDED BLACKLIST COMPOUNDS — Originally Present in Raw Data', rhdr_fmt)
                ws_e.merge_range(f'A2:{lc}2',f'NOTE: Removed because compound name contains a blacklisted keyword. Active keywords: {", ".join(st.session_state.blacklist)}. See "Matched Keyword" column for per-row reason.', note_fmt)
                ws_e.set_row(1,42)
                ws_e.merge_range(f'A4:{lc}4','SAMPLE — Excluded Blacklist Compounds', rsub_fmt)
                if not df_s_excl.empty:
                    for ci,cn in enumerate(df_s_excl.columns): ws_e.write(4,ci,cn,lbl_fmt)
                    for ri,(_,row) in enumerate(df_s_excl.iterrows()):
                        for ci,val in enumerate(row): ws_e.write(5+ri,ci,val,red_fmt)
                    se = 5+len(df_s_excl)
                else:
                    ws_e.write(4,0,'No blacklisted compounds found in Sample.',wb.add_format({'italic':True,'font_color':'#888'})); se=6
                bs = se+2
                ws_e.merge_range(f'A{bs}:{lc}{bs}','BLANK — Excluded Blacklist Compounds', rsub_fmt)
                if not df_b_excl.empty:
                    for ci,cn in enumerate(df_b_excl.columns): ws_e.write(bs,ci,cn,lbl_fmt)
                    for ri,(_,row) in enumerate(df_b_excl.iterrows()):
                        for ci,val in enumerate(row): ws_e.write(bs+1+ri,ci,val,red_fmt)
                else:
                    ws_e.write(bs,0,'No blacklisted compounds found in Blank.',wb.add_format({'italic':True,'font_color':'#888'}))
                ws_e.set_column('A:A',48); ws_e.set_column('B:G',18)

            with dl2:
                st.download_button("⬇️ Download", data=output.getvalue(), file_name=final_save_name, use_container_width=True)

        except Exception as e:
            st.error(f"Pipeline error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    t = T()
    st.markdown(f"""
    <div style="margin-bottom:16px;">
        <div style="font-size:18px;font-weight:700;color:{t['text']};
            letter-spacing:-0.01em;font-family:'Inter',sans-serif;">
            Multi-File PCA Matrix
        </div>
        <div style="font-size:11px;color:{t['hint']};margin-top:3px;
            font-family:'JetBrains Mono',monospace;">
            Upload one blank + multiple sample files → compound × sample matrix for PCA
        </div>
    </div>
    """, unsafe_allow_html=True)

    info_card(f"⚠️ All files must be <b>.xlsx</b> format. Same analytical controls from sidebar apply.", t['warn'])

    cb, cs = st.columns(2)
    with cb:
        upload_label("Blank File (one)", t['accent2'])
        m_blank = st.file_uploader("blank_m", type=['xlsx'], key="m_b", label_visibility="collapsed")
    with cs:
        upload_label("Sample Files (multiple)", t['accent'])
        m_samples = st.file_uploader("samples_m", type=['xlsx'], accept_multiple_files=True, key="m_s", label_visibility="collapsed")

    if m_blank and m_samples:
        try:
            _, df_b_m, _ = run_strict_procedure(m_blank, q_threshold, area_threshold)
            pca_list, all_cpds = [], set()
            prog = st.progress(0, text="Processing files...")
            for i, sf in enumerate(m_samples):
                _, df_sr, _ = run_strict_procedure(sf, q_threshold, area_threshold)
                res = df_sr.apply(lambda r: check_match_expert(r, df_b_m, rt_tolerance), axis=1)
                df_cl = df_sr[res.apply(lambda x: x[0] in ["NO","RT_SHIFT_DETECTED"])].copy()
                sd = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_cl.iterrows()}
                sd['Sample Name'] = sf.name
                pca_list.append(sd)
                all_cpds.update(df_cl['Hit Name'].tolist())
                prog.progress((i+1)/len(m_samples), text=f"Processing: {sf.name}")
            prog.empty()

            df_pca = pd.DataFrame(pca_list).reindex(columns=['Sample Name']+sorted(list(all_cpds))).fillna(0)

            t = T()
            st.markdown(f"""
            <div style="display:flex;gap:8px;margin:14px 0 12px;flex-wrap:wrap;">
                {"".join([f'''
                <div style="background:{t['bg2']};border:1px solid {t['border']};
                    border-radius:8px;padding:12px 18px;text-align:center;border-top:3px solid {c};">
                    <div style="font-size:22px;font-weight:700;color:{c};font-family:'JetBrains Mono',monospace;">{v}</div>
                    <div style="font-size:9px;color:{t['hint']};text-transform:uppercase;
                        letter-spacing:0.1em;margin-top:2px;font-family:'JetBrains Mono',monospace;">{l}</div>
                </div>''' for c,v,l in [
                    (t['accent'], len(m_samples), 'Samples'),
                    (t['accent2'], len(all_cpds), 'Unique Compounds'),
                    (t['muted'], f"{len(m_samples)}×{len(all_cpds)}", 'Matrix Size'),
                ]])}
            </div>
            """, unsafe_allow_html=True)

            sec_hdr("PCA Matrix — Raw Absorbance", "Rows = samples  ·  Columns = compounds  ·  Missing values filled with 0")
            st.dataframe(df_pca, use_container_width=True)

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("⬇️ Download PCA Matrix", data=pca_out.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"PCA error: {e}")
