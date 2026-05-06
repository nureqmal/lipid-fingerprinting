import streamlit as st
import pandas as pd
import io
import json
import os

st.set_page_config(page_title="LIPID EQ", layout="wide", page_icon="⚗️")

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
            "bg":           "#080d1a",
            "bg2":          "#0d1428",
            "bg3":          "#111c36",
            "surface":      "#111c36",
            "border":       "#1e3060",
            "border2":      "#2a4278",
            "navy":         "#050b18",
            "teal":         "#0a7c6e",
            "teal2":        "#0fd4a4",
            "gold":         "#d4a017",
            "text":         "#c8d8f0",
            "muted":        "#6a80a8",
            "hint":         "#3a5070",
            "danger":       "#e05050",
            "warn":         "#c08020",
            "success":      "#0fd4a4",
            "yellow_row":   "#1a1500",
            "red_row":      "#1a0808",
            "pink_row":     "#1a0810",
            "navy_cell":    "#000818",
            "input_bg":     "#0a1020",
            "scrollbar":    "#1e3060",
            "font":         "'Courier New', 'Lucida Console', monospace",
        }
    else:
        return {
            "bg":           "#f4f6fa",
            "bg2":          "#ffffff",
            "bg3":          "#eef0f6",
            "surface":      "#f0f2f8",
            "border":       "#c0c8da",
            "border2":      "#8898b8",
            "navy":         "#0d1b3e",
            "teal":         "#0a7c6e",
            "teal2":        "#0a9e8c",
            "gold":         "#b8860b",
            "text":         "#0d1b3e",
            "muted":        "#4a5568",
            "hint":         "#8896b0",
            "danger":       "#c0392b",
            "warn":         "#a0690a",
            "success":      "#0a7c6e",
            "yellow_row":   "#fffbe6",
            "red_row":      "#fdf0f0",
            "pink_row":     "#fdf0f6",
            "navy_cell":    "#002060",
            "input_bg":     "#f8f9fc",
            "scrollbar":    "#c0c8da",
            "font":         "'Courier New', 'Lucida Console', monospace",
        }

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
def inject_css():
    t = T()
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background-color: {t['bg']} !important;
    font-family: {t['font']} !important;
    color: {t['text']} !important;
}}

[data-testid="stSidebar"] {{
    background-color: {t['navy']} !important;
    border-right: 1px solid {t['border']} !important;
}}
[data-testid="stSidebar"] * {{
    font-family: {t['font']} !important;
    color: {t['text']} !important;
}}
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stTextInput label {{
    color: {t['muted']} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
    color: {t['muted']} !important;
    font-size: 0.72rem !important;
}}

section.main > div {{ padding-top: 0.4rem !important; }}

h1, h2, h3 {{
    font-family: {t['font']} !important;
    color: {t['text']} !important;
    letter-spacing: 0.04em !important;
}}

/* Metric cards */
[data-testid="metric-container"] {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 4px !important;
    padding: 14px !important;
    border-left: 3px solid {t['teal']} !important;
}}
[data-testid="stMetricValue"] {{
    color: {t['navy'] if not st.session_state.dark_mode else t['teal2']} !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    font-family: {t['font']} !important;
}}
[data-testid="stMetricLabel"] {{
    color: {t['muted']} !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: {t['font']} !important;
}}
[data-testid="stMetricDelta"] svg {{ display: none !important; }}
[data-testid="stMetricDelta"] {{
    font-size: 0.7rem !important;
    font-family: {t['font']} !important;
}}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {t['navy']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 4px !important;
    padding: 3px !important;
    gap: 2px !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 3px !important;
    color: {t['muted']} !important;
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    font-family: {t['font']} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border: none !important;
    padding: 6px 10px !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {t['teal']} !important;
    color: #ffffff !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    display: none !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border: 1px solid {t['border']} !important;
    border-radius: 4px !important;
    overflow: hidden !important;
}}
[data-testid="stDataFrame"] thead tr th {{
    background: {t['navy']} !important;
    color: {t['muted']} !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: {t['font']} !important;
}}
[data-testid="stDataFrame"] td {{
    font-family: {t['font']} !important;
    font-size: 0.78rem !important;
    color: {t['text']} !important;
}}
[data-testid="stDataFrame"] tbody tr:hover td {{
    background: {t['surface']} !important;
}}

/* Buttons */
[data-testid="stButton"] > button {{
    background: {t['navy']} !important;
    color: {t['teal2']} !important;
    border: 1px solid {t['teal']} !important;
    border-radius: 3px !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    font-family: {t['font']} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    padding: 6px 16px !important;
    transition: all 0.15s ease !important;
}}
[data-testid="stButton"] > button:hover {{
    background: {t['teal']} !important;
    color: #ffffff !important;
}}

/* Download button */
[data-testid="stDownloadButton"] > button {{
    background: {t['teal']} !important;
    color: #ffffff !important;
    border: 1px solid {t['teal']} !important;
    border-radius: 3px !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    font-family: {t['font']} !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}}
[data-testid="stDownloadButton"] > button:hover {{
    background: {t['teal2']} !important;
    border-color: {t['teal2']} !important;
}}

/* File uploader */
[data-testid="stFileUploader"] {{
    background: {t['bg2']} !important;
    border: 1px dashed {t['border2']} !important;
    border-radius: 4px !important;
    padding: 8px !important;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: {t['teal']} !important;
}}
[data-testid="stFileUploader"] label {{
    color: {t['text']} !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: {t['font']} !important;
}}

/* Sliders */
[data-testid="stSlider"] > div > div > div > div {{
    background: {t['teal']} !important;
}}
[data-testid="stSlider"] label {{
    color: {t['muted']} !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: {t['font']} !important;
}}

/* Text input */
[data-testid="stTextInput"] input {{
    background: {t['input_bg']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 3px !important;
    color: {t['text']} !important;
    font-family: {t['font']} !important;
    font-size: 0.78rem !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {t['teal']} !important;
    box-shadow: 0 0 0 2px {t['teal']}33 !important;
}}
[data-testid="stTextInput"] label {{
    color: {t['muted']} !important;
    font-size: 0.68rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-family: {t['font']} !important;
}}

/* Alerts */
[data-testid="stAlert"] {{
    border-radius: 3px !important;
    border-left: 3px solid !important;
    font-size: 0.78rem !important;
    font-family: {t['font']} !important;
    background: {t['bg2']} !important;
}}
[data-testid="stInfo"] {{ border-color: {t['teal']} !important; }}
[data-testid="stSuccess"] {{ border-color: {t['success']} !important; }}
[data-testid="stWarning"] {{ border-color: {t['warn']} !important; }}
[data-testid="stError"] {{ border-color: {t['danger']} !important; }}

/* Table */
[data-testid="stTable"] table {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 4px !important;
    font-family: {t['font']} !important;
    font-size: 0.78rem !important;
}}
[data-testid="stTable"] th {{
    background: {t['navy']} !important;
    color: {t['muted']} !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    font-family: {t['font']} !important;
}}
[data-testid="stTable"] td {{
    color: {t['text']} !important;
    border-color: {t['border']} !important;
    font-family: {t['font']} !important;
}}

/* Caption */
[data-testid="stCaptionContainer"] {{
    color: {t['muted']} !important;
    font-size: 0.7rem !important;
    font-family: {t['font']} !important;
}}

/* Expander */
[data-testid="stExpander"] {{
    background: {t['bg2']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 4px !important;
}}

/* Progress */
[data-testid="stProgressBar"] > div > div {{
    background: {t['teal']} !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {t['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {t['scrollbar']}; border-radius: 2px; }}
::-webkit-scrollbar-thumb:hover {{ background: {t['muted']}; }}

hr {{ border-color: {t['border']} !important; margin: 0.6rem 0 !important; }}
[data-testid="column"] {{ padding: 0 5px !important; }}
</style>
""", unsafe_allow_html=True)

inject_css()
t = T()

# ─── HTML HELPERS ─────────────────────────────────────────────────────────────
def topbar():
    mode_lbl = "[ DARK MODE ]" if not st.session_state.dark_mode else "[ LIGHT MODE ]"
    st.markdown(f"""
    <div style="
        background:{t['navy']}; border:1px solid {t['border']}; border-radius:6px;
        padding:12px 20px; margin-bottom:14px;
        display:flex; align-items:center; justify-content:space-between;
    ">
        <div style="display:flex; align-items:center; gap:14px;">
            <div style="
                width:40px; height:40px; background:{t['teal']}; border-radius:4px;
                display:flex; align-items:center; justify-content:center;
            ">
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                    <path d="M8 2h6v7l2.5 3.5V19H5.5V12.5L8 9V2z" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round"/>
                    <path d="M8 9h6M10 2v4M12 2v4" stroke="#ffffff" stroke-width="1.2" stroke-linecap="round"/>
                    <circle cx="11" cy="15" r="1.8" fill="#ffffff"/>
                </svg>
            </div>
            <div>
                <div style="font-size:16px; font-weight:700; color:#ffffff; letter-spacing:0.12em; font-family:'Courier New',monospace;">LIPID EQ</div>
                <div style="font-size:9px; color:{t['muted']}; letter-spacing:0.18em; text-transform:uppercase; margin-top:1px; font-family:'Courier New',monospace;">GC-MS Analytical Platform</div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
            <span style="background:{t['teal']}; color:#fff; font-size:9px; font-weight:700; padding:3px 10px; border-radius:2px; letter-spacing:0.12em; font-family:'Courier New',monospace;">HALAL ANALYTICS</span>
            <span style="background:transparent; color:{t['muted']}; font-size:9px; font-weight:700; padding:3px 10px; border-radius:2px; letter-spacing:0.12em; border:1px solid {t['border']}; font-family:'Courier New',monospace;">v2.0</span>
            <span style="color:{t['hint']}; font-size:9px; font-family:'Courier New',monospace; letter-spacing:0.08em;">{mode_lbl}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def section_hdr(label, sub=""):
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:8px; margin:14px 0 8px; border-bottom:1px solid {t['border']}; padding-bottom:6px;">
        <div style="width:6px; height:6px; background:{t['teal']}; border-radius:1px; flex-shrink:0;"></div>
        <div style="font-size:9px; font-weight:700; color:{t['muted']}; text-transform:uppercase; letter-spacing:0.14em; font-family:'Courier New',monospace;">{label}</div>
        {f'<div style="font-size:9px; color:{t["hint"]}; font-family:Courier New,monospace; margin-left:4px;">// {sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)

def info_bar(msg, color=None):
    c = color or t['teal']
    st.markdown(f"""
    <div style="background:{t['bg2']}; border-left:3px solid {c}; border:1px solid {t['border']};
        border-left:3px solid {c}; border-radius:3px; padding:9px 14px;
        font-size:0.75rem; color:{t['muted']}; margin-bottom:10px;
        font-family:'Courier New',monospace; line-height:1.6;">
        {msg}
    </div>
    """, unsafe_allow_html=True)

def terminal_row(compound, rt, area, keyword):
    st.markdown(f"""
    <div style="background:{t['red_row']}; border:1px solid {t['danger']}44;
        border-radius:3px; padding:6px 12px; margin-bottom:4px;
        font-family:'Courier New',monospace; font-size:0.75rem; color:{t['danger']};">
        &gt; <b>{compound}</b>
        <span style="color:{t['hint']}; margin-left:12px;">RT: {rt}</span>
        <span style="color:{t['hint']}; margin-left:12px;">Area: {area}%</span>
        <span style="background:{t['danger']}22; color:{t['danger']}; font-size:0.65rem;
            padding:1px 6px; border-radius:2px; margin-left:10px; font-weight:700;">
            [{keyword}]
        </span>
    </div>
    """, unsafe_allow_html=True)

topbar()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:6px 0 10px;">
        <div style="font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:0.16em; color:{t['teal2']};">
            // Control Panel
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "[ DARK MODE ]" if not st.session_state.dark_mode else "[ LIGHT MODE ]",
        use_container_width=True, key="theme_toggle"
    ):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown(f"""<div style="font-size:9px; font-weight:700; text-transform:uppercase;
        letter-spacing:0.14em; color:{t['teal2']}; margin-bottom:8px; font-family:'Courier New',monospace;">
        // Analytical Controls</div>""", unsafe_allow_html=True)

    q_threshold = st.slider("NIST Quality Threshold", 50, 95, 80, 5,
        help="NIST Match Factor — filters compound identity accuracy. Default: 80")
    rt_tolerance = st.slider("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
        help="Retention time error limit for Sample vs Blank. Default: 0.05")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
        help="Removes baseline noise peaks. Default: 0.00")

    st.markdown("---")
    st.markdown(f"""<div style="font-size:9px; font-weight:700; text-transform:uppercase;
        letter-spacing:0.14em; color:{t['teal2']}; margin-bottom:6px; font-family:'Courier New',monospace;">
        // Blacklist Manager</div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="font-size:0.68rem; color:{t['hint']}; margin-bottom:10px;
        font-family:'Courier New',monospace; line-height:1.5;">
        Compounds whose name contains any keyword below are excluded. Persists across sessions.</div>""",
        unsafe_allow_html=True)

    st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
        letter-spacing:0.08em; color:{t['muted']}; margin-bottom:6px;
        font-family:'Courier New',monospace;">Active [{len(st.session_state.blacklist)}]</div>""",
        unsafe_allow_html=True)

    for kw in st.session_state.blacklist:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"""
        <div style="background:{t['bg3']}; border:1px solid {t['border']}; border-radius:2px;
            padding:3px 8px; font-size:0.72rem; color:{t['teal2']};
            font-family:'Courier New',monospace; letter-spacing:0.06em; margin-bottom:2px;">
            {kw}
        </div>""", unsafe_allow_html=True)
        if c2.button("x", key=f"rm_{kw}", help=f"Remove '{kw}'"):
            st.session_state.blacklist.remove(kw)
            save_blacklist(st.session_state.blacklist)
            st.rerun()

    st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
        letter-spacing:0.08em; color:{t['muted']}; margin:10px 0 4px;
        font-family:'Courier New',monospace;">Add Keyword</div>""", unsafe_allow_html=True)
    new_kw = st.text_input("New keyword", placeholder="e.g. trimethylsilyl",
        label_visibility="collapsed", key="new_kw")
    if st.button("+ ADD TO BLACKLIST", use_container_width=True):
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
    if st.button("RESET TO DEFAULT", use_container_width=True, key="reset_bl"):
        st.session_state.blacklist = DEFAULT_BLACKLIST.copy()
        save_blacklist(st.session_state.blacklist)
        st.rerun()

    st.markdown("---")
    sop_steps = [
        "Metadata preserved (rows 1–9)",
        f"Quality gate >= {q_threshold}",
        f"Noise cut < {area_threshold:.2f}%",
        f"RT matching +/- {rt_tolerance} min",
        f"Blacklist filter ({len(st.session_state.blacklist)} keywords)",
    ]
    st.markdown(f"""
    <div style="background:{t['bg3']}; border:1px solid {t['border']}; border-radius:4px; padding:10px 12px;">
        <div style="font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:0.14em;
            color:{t['teal2']}; margin-bottom:8px; font-family:'Courier New',monospace;">// SOP Steps</div>
        {"".join([f'''
        <div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
            <div style="width:16px; height:16px; background:{t['teal']}; border-radius:2px; flex-shrink:0;
                display:flex; align-items:center; justify-content:center;
                font-size:9px; font-weight:700; color:#fff; font-family:'Courier New',monospace;">{i}</div>
            <div style="font-size:0.68rem; color:{t['muted']}; font-family:'Courier New',monospace; line-height:1.4;">{s}</div>
        </div>''' for i, s in enumerate(sop_steps, 1)])}
    </div>
    """, unsafe_allow_html=True)

# ─── COMPOUND LOGIC ───────────────────────────────────────────────────────────
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
    df_excluded = (df_excluded
        .sort_values(by='Area (Ab*s)', ascending=False)
        .drop_duplicates(subset=['Hit Name'], keep='first')
        .sort_values(by='RT (min)'))
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return df_header, df.sort_values(by='RT (min)'), df_excluded

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, tr in matches.iterrows():
        diff = abs(row['RT (min)'] - tr['RT (min)'])
        if diff <= tol: return "YES", diff
    return "RT_SHIFT_DETECTED", matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()

# ─── MAIN TABS ────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["// Single File Analysis", "// Multi-File PCA Matrix"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    info_bar(f"Upload Sample and Blank files (.xlsx) to execute the Lipid EQ pipeline.", t['warn'])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
            letter-spacing:0.1em; color:{t['teal2']}; margin-bottom:5px;
            font-family:'Courier New',monospace;">[ Sample File ]</div>""", unsafe_allow_html=True)
        sample_file = st.file_uploader("SAMPLE", type=['xlsx'], key="s_file", label_visibility="collapsed")
    with col2:
        st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
            letter-spacing:0.1em; color:{t['muted']}; margin-bottom:5px;
            font-family:'Courier New',monospace;">[ Blank File ]</div>""", unsafe_allow_html=True)
        blank_file = st.file_uploader("BLANK", type=['xlsx'], key="b_file", label_visibility="collapsed")

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
            total_sample = len(df_s)
            purged = len(df_s[df_s['In_Blank'] == "YES"])
            final_count = len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0

            # ── METRICS ──────────────────────────────────────────────────────
            section_hdr("Pipeline Results", f"file: {sample_file.name}")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Peaks", total_sample)
            m2.metric("Blank Purged", purged, delta=f"-{purged}", delta_color="inverse")
            m3.metric("Final Compounds", final_count)
            m4.metric("Purity Score", f"{purity:.1f}%",
                help="(Σ Area Clean Peaks / Total Area) × 100")
            m5.metric("Blacklist Excl.", len(df_s_excl), delta=f"-{len(df_s_excl)}", delta_color="inverse")

            st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

            # ── INNER TABS ───────────────────────────────────────────────────
            inner = st.tabs([
                "01 // Solvent Blank",
                "02 // Sample Mapping",
                "03 // Final Fingerprint",
                "04 // RT Analysis",
                "05 // Excluded"
            ])

            with inner[0]:
                section_hdr("Solvent Blank Profile", "yellow = matched in sample | navy RT = shift detected")
                def hl_blank(row):
                    if row['In_Sample'] == "YES":
                        return [f'background-color: #fffbe6; color: #5a4a00' for _ in row.index]
                    s = ['' for _ in row.index]
                    if row['In_Sample'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return s
                st.dataframe(df_b.style.apply(hl_blank, axis=1), use_container_width=True)

            with inner[1]:
                section_hdr("Sample Compound Mapping", "yellow = found in blank | navy RT = shift but retained")
                def hl_sample(row):
                    if row['In_Blank'] == "YES":
                        return [f'background-color: #fffbe6; color: #5a4a00' for _ in row.index]
                    s = ['' for _ in row.index]
                    if row['In_Blank'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return s
                st.dataframe(df_s.style.apply(hl_sample, axis=1), use_container_width=True)

            with inner[2]:
                section_hdr("Final Lipid Fingerprint", "clean compounds after blank subtraction")
                def hl_final(row):
                    if row.get('Chemical_Status') == "Review (Potential Contaminant)":
                        return ['background-color: #fdf0f6; color: #5a0020' for _ in row.index]
                    return ['' for _ in row.index]
                st.dataframe(
                    df_final.drop(columns=['In_Blank', 'RT_Diff']).style.apply(hl_final, axis=1),
                    use_container_width=True
                )

            with inner[3]:
                section_hdr("RT Shift Analysis", "compounds with retention time deviation between sample and blank")
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    info_bar(f"DETECTED: {len(rt_issues)} compound(s) with RT shift. Status: RETAINED in final fingerprint.", t['warn'])
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else:
                    st.success("// NO RT SHIFTS DETECTED")

            with inner[4]:
                section_hdr("Excluded Blacklist Compounds", "originally in raw data — removed by keyword match")

                # Keyword pills
                pills = "".join([
                    f'<span style="background:{t["danger"]}18; color:{t["danger"]}; '
                    f'border:1px solid {t["danger"]}40; border-radius:2px; '
                    f'padding:2px 8px; font-size:0.68rem; font-weight:700; '
                    f'margin:2px; display:inline-block; font-family:Courier New,monospace; '
                    f'letter-spacing:0.06em;">{kw}</span>'
                    for kw in st.session_state.blacklist
                ])
                st.markdown(f"""
                <div style="background:{t['bg2']}; border:1px solid {t['border']}; border-radius:4px;
                    padding:10px 14px; margin-bottom:12px;">
                    <div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
                        letter-spacing:0.1em; color:{t['muted']}; margin-bottom:6px;
                        font-family:'Courier New',monospace;">Active Blacklist Keywords</div>
                    <div>{pills}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div style="font-size:0.72rem; font-weight:700; color:{t['danger']};
                        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;
                        font-family:'Courier New',monospace;">
                        SAMPLE — Excluded [{len(df_s_excl)}]</div>""", unsafe_allow_html=True)
                    if df_s_excl.empty:
                        st.success("// NO BLACKLISTED COMPOUNDS IN SAMPLE")
                    else:
                        # Terminal-style log
                        st.markdown(f"""<div style="background:{t['bg2']}; border:1px solid {t['danger']}44;
                            border-left:3px solid {t['danger']}; border-radius:3px;
                            padding:10px 12px; margin-bottom:8px;">
                            <div style="font-size:0.68rem; font-weight:700; color:{t['danger']};
                                text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;
                                font-family:'Courier New',monospace;">// Exclusion Log</div>
                            {"".join([
                                f'<div style="font-family:Courier New,monospace; font-size:0.72rem; '
                                f'color:{t["danger"]}; padding:2px 0; line-height:1.5;">'
                                f'&gt; {row["Hit Name"]} '
                                f'<span style="color:{t["hint"]}">RT:{row["RT (min)"]:.2f} '
                                f'Area:{row["Area (%)"]:.2f}%</span> '
                                f'<span style="background:{t["danger"]}22; color:{t["danger"]}; '
                                f'font-size:0.62rem; padding:1px 5px; border-radius:2px; font-weight:700;">'
                                f'[{row["Matched Keyword"]}]</span></div>'
                                for _, row in df_s_excl.iterrows()
                            ])}
                        </div>""", unsafe_allow_html=True)
                        # Full data table below log
                        st.dataframe(
                            df_s_excl.style.apply(lambda r: ['background-color:#fdf0f0; color:#5a0000' for _ in r.index], axis=1),
                            use_container_width=True
                        )
                        st.caption(f"// {len(df_s_excl)} compound(s) excluded from Sample")

                with c2:
                    st.markdown(f"""<div style="font-size:0.72rem; font-weight:700; color:{t['danger']};
                        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;
                        font-family:'Courier New',monospace;">
                        BLANK — Excluded [{len(df_b_excl)}]</div>""", unsafe_allow_html=True)
                    if df_b_excl.empty:
                        st.success("// NO BLACKLISTED COMPOUNDS IN BLANK")
                    else:
                        st.markdown(f"""<div style="background:{t['bg2']}; border:1px solid {t['danger']}44;
                            border-left:3px solid {t['danger']}; border-radius:3px;
                            padding:10px 12px; margin-bottom:8px;">
                            <div style="font-size:0.68rem; font-weight:700; color:{t['danger']};
                                text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;
                                font-family:'Courier New',monospace;">// Exclusion Log</div>
                            {"".join([
                                f'<div style="font-family:Courier New,monospace; font-size:0.72rem; '
                                f'color:{t["danger"]}; padding:2px 0; line-height:1.5;">'
                                f'&gt; {row["Hit Name"]} '
                                f'<span style="color:{t["hint"]}">RT:{row["RT (min)"]:.2f} '
                                f'Area:{row["Area (%)"]:.2f}%</span> '
                                f'<span style="background:{t["danger"]}22; color:{t["danger"]}; '
                                f'font-size:0.62rem; padding:1px 5px; border-radius:2px; font-weight:700;">'
                                f'[{row["Matched Keyword"]}]</span></div>'
                                for _, row in df_b_excl.iterrows()
                            ])}
                        </div>""", unsafe_allow_html=True)
                        st.dataframe(
                            df_b_excl.style.apply(lambda r: ['background-color:#fdf0f0; color:#5a0000' for _ in r.index], axis=1),
                            use_container_width=True
                        )
                        st.caption(f"// {len(df_b_excl)} compound(s) excluded from Blank")

            # ── EXPORT ───────────────────────────────────────────────────────
            st.markdown("---")
            section_hdr("Export Report", "full .xlsx with Dashboard, Analytical Report & Excluded Compounds")

            dl1, dl2 = st.columns([3, 1])
            with dl1:
                custom_filename = st.text_input("Output filename",
                    value="SF-HEX-1", key="rename_s",
                    label_visibility="collapsed", placeholder="e.g. SF-HEX-1")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                fn = 'Courier New'
                hdr_fmt  = wb.add_format({'bold':True,'font_size':13,'bg_color':'#0d1b3e','font_color':'#ffffff','border':1,'align':'center','font_name':fn})
                lbl_fmt  = wb.add_format({'bold':True,'bg_color':'#eef0f6','border':1,'font_name':fn,'font_size':9})
                val_fmt  = wb.add_format({'border':1,'align':'center','font_name':fn,'font_size':9})
                yel_fmt  = wb.add_format({'bg_color':'#FFEB9C','border':1,'font_name':fn})
                nav_fmt  = wb.add_format({'bg_color':'#002060','font_color':'white','border':1,'font_name':fn})
                pnk_fmt  = wb.add_format({'bg_color':'#FFC0CB','border':1,'font_name':fn})
                red_fmt  = wb.add_format({'bg_color':'#FFD7D7','border':1,'font_name':fn})
                rhdr_fmt = wb.add_format({'bold':True,'font_size':11,'bg_color':'#c0392b','font_color':'white','border':1,'align':'center','font_name':fn})
                rsub_fmt = wb.add_format({'bold':True,'bg_color':'#FFD7D7','border':1,'align':'center','font_name':fn})
                note_fmt = wb.add_format({'italic':True,'font_color':'#c0392b','text_wrap':True,'font_name':fn,'font_size':8})
                kw_fmt   = wb.add_format({'border':1,'text_wrap':True,'font_name':fn,'font_size':8})

                # Dashboard
                ws_d = wb.add_worksheet('Dashboard')
                ws_d.merge_range('B2:F2', 'LIPID EQ // ANALYTICAL SUMMARY REPORT', hdr_fmt)
                rows = [
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance (min)', rt_tolerance),
                    ('Area Threshold (%)', area_threshold),
                    ('Total Sample Peaks', total_sample),
                    ('Blank Matches Purged', purged),
                    ('Final Unique Compounds', final_count),
                    ('Purity Score', f"{purity:.2f}%"),
                    ('Active Blacklist Keywords', len(st.session_state.blacklist)),
                    ('Blacklist Excl. (Sample)', len(df_s_excl)),
                    ('Blacklist Excl. (Blank)', len(df_b_excl)),
                ]
                for i, (l, v) in enumerate(rows, 4):
                    ws_d.write(f'B{i}', l, lbl_fmt); ws_d.write(f'C{i}', v, val_fmt)
                kwr = 4 + len(rows) + 1
                ws_d.write(f'B{kwr}', 'Blacklist Keywords', lbl_fmt)
                ws_d.write(f'C{kwr}', ', '.join(st.session_state.blacklist), kw_fmt)
                ws_d.set_row(kwr-1, 26)
                lgr = kwr + 2
                ws_d.write(f'B{lgr}', 'COLOR LEGEND', wb.add_format({'bold':True,'underline':True,'font_name':fn}))
                ws_d.write(f'B{lgr+1}', 'Yellow Row', yel_fmt); ws_d.write(f'C{lgr+1}', 'Matched in Blank/Sample')
                ws_d.write(f'B{lgr+2}', 'Navy RT Cell', nav_fmt); ws_d.write(f'C{lgr+2}', 'RT Shift Detected (Retained)')
                ws_d.write(f'B{lgr+3}', 'Pink Cell', pnk_fmt); ws_d.write(f'C{lgr+3}', 'Potential Contaminant')
                ws_d.write(f'B{lgr+4}', 'Red Row', red_fmt); ws_d.write(f'C{lgr+4}', 'Excluded Blacklist Artifact')
                ws_d.set_column('B:B', 28); ws_d.set_column('C:C', 80)

                # Analytical Report
                rs = 'Analytical_Report'
                h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
                df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
                s2 = len(df_b) + 16
                h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
                df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
                s3 = s2 + len(df_s) + 15
                fh = h_s.copy(); fh.iloc[0,0] = f"{fh.iloc[0,0]} (Clean)"
                fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
                df_final.drop(columns=['In_Blank','RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)
                wr = writer.sheets[rs]
                bi = df_b.columns.get_loc('RT (min)'); bm = df_b.columns.get_loc('In_Sample')
                wr.conditional_format(11,0,11+len(df_b),len(df_b.columns)-1,{'type':'formula','criteria':f'=${chr(65+bm)}12="YES"','format':yel_fmt})
                wr.conditional_format(11,bi,11+len(df_b),bi,{'type':'formula','criteria':f'=${chr(65+bm)}12="RT_SHIFT_DETECTED"','format':nav_fmt})
                si = df_s.columns.get_loc('RT (min)'); sm = df_s.columns.get_loc('In_Blank')
                wr.conditional_format(s2+10,0,s2+10+len(df_s),len(df_s.columns)-1,{'type':'formula','criteria':f'=${chr(65+sm)}{s2+11}="YES"','format':yel_fmt})
                wr.conditional_format(s2+10,si,s2+10+len(df_s),si,{'type':'formula','criteria':f'=${chr(65+sm)}{s2+11}="RT_SHIFT_DETECTED"','format':nav_fmt})
                fi = df_final.columns.get_loc('Chemical_Status')
                wr.conditional_format(s3+10,fi,s3+10+len(df_final),fi,{'type':'cell','criteria':'equal to','value':'"Review (Potential Contaminant)"','format':pnk_fmt})

                # Excluded sheet
                ws_e = wb.add_worksheet('Excluded_Compounds')
                mc = max(len(df_s_excl.columns) if not df_s_excl.empty else 6, len(df_b_excl.columns) if not df_b_excl.empty else 6)
                lc = chr(64+min(mc,26))
                ws_e.merge_range(f'A1:{lc}1', 'EXCLUDED BLACKLIST COMPOUNDS // Originally Present in Raw Data', rhdr_fmt)
                ws_e.merge_range(f'A2:{lc}2',
                    f'NOTE: Removed because compound name contains blacklisted keyword. '
                    f'Active: {", ".join(st.session_state.blacklist)}. See "Matched Keyword" column.', note_fmt)
                ws_e.set_row(1, 40)
                ws_e.merge_range(f'A4:{lc}4','SAMPLE // Excluded Blacklist Compounds', rsub_fmt)
                if not df_s_excl.empty:
                    for ci,cn in enumerate(df_s_excl.columns): ws_e.write(4,ci,cn,lbl_fmt)
                    for ri,(_,row) in enumerate(df_s_excl.iterrows()):
                        for ci,val in enumerate(row): ws_e.write(5+ri,ci,val,red_fmt)
                    se = 5+len(df_s_excl)
                else:
                    ws_e.write(4,0,'No blacklisted compounds found in Sample.',wb.add_format({'italic':True,'font_color':'#888','font_name':fn}))
                    se = 6
                bs = se+2
                ws_e.merge_range(f'A{bs}:{lc}{bs}','BLANK // Excluded Blacklist Compounds', rsub_fmt)
                if not df_b_excl.empty:
                    for ci,cn in enumerate(df_b_excl.columns): ws_e.write(bs,ci,cn,lbl_fmt)
                    for ri,(_,row) in enumerate(df_b_excl.iterrows()):
                        for ci,val in enumerate(row): ws_e.write(bs+1+ri,ci,val,red_fmt)
                else:
                    ws_e.write(bs,0,'No blacklisted compounds found in Blank.',wb.add_format({'italic':True,'font_color':'#888','font_name':fn}))
                ws_e.set_column('A:A',48); ws_e.set_column('B:G',16)

            with dl2:
                st.download_button(
                    "DOWNLOAD REPORT",
                    data=output.getvalue(),
                    file_name=final_save_name,
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"// PIPELINE ERROR: {e}")

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    <div style="font-size:14px; font-weight:700; color:{t['text']}; letter-spacing:0.08em;
        font-family:'Courier New',monospace; margin-bottom:4px;">// MULTI-FILE PCA MATRIX</div>
    <div style="font-size:0.75rem; color:{t['muted']}; font-family:'Courier New',monospace;
        margin-bottom:14px; line-height:1.6;">
        Upload one blank and multiple sample files to generate a compound x sample matrix ready for PCA.
    </div>
    """, unsafe_allow_html=True)

    info_bar("All files must be .xlsx format. Sidebar analytical controls apply to all files.", t['warn'])

    cb, cs = st.columns(2)
    with cb:
        st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
            letter-spacing:0.1em; color:{t['muted']}; margin-bottom:5px;
            font-family:'Courier New',monospace;">[ Blank File ]</div>""", unsafe_allow_html=True)
        m_blank = st.file_uploader("Blank", type=['xlsx'], key="m_b", label_visibility="collapsed")
    with cs:
        st.markdown(f"""<div style="font-size:0.68rem; font-weight:700; text-transform:uppercase;
            letter-spacing:0.1em; color:{t['teal2']}; margin-bottom:5px;
            font-family:'Courier New',monospace;">[ Sample Files ]</div>""", unsafe_allow_html=True)
        m_samples = st.file_uploader("Samples", type=['xlsx'], accept_multiple_files=True, key="m_s", label_visibility="collapsed")

    if m_blank and m_samples:
        try:
            _, df_bm, _ = run_strict_procedure(m_blank, q_threshold, area_threshold)
            pca_list, all_cpds = [], set()
            prog = st.progress(0, text="// Initialising...")
            for i, sf in enumerate(m_samples):
                _, df_sr, _ = run_strict_procedure(sf, q_threshold, area_threshold)
                res = df_sr.apply(lambda r: check_match_expert(r, df_bm, rt_tolerance), axis=1)
                df_cl = df_sr[res.apply(lambda x: x[0] in ["NO","RT_SHIFT_DETECTED"])].copy()
                sd = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_cl.iterrows()}
                sd['Sample Name'] = sf.name
                pca_list.append(sd)
                all_cpds.update(df_cl['Hit Name'].tolist())
                prog.progress((i+1)/len(m_samples), text=f"// Processing: {sf.name}")
            prog.empty()

            df_pca = pd.DataFrame(pca_list)
            df_pca = df_pca.reindex(columns=['Sample Name']+sorted(list(all_cpds))).fillna(0)

            st.markdown(f"""
            <div style="display:flex; gap:10px; margin:14px 0 10px;">
                {"".join([
                    f'<div style="background:{t["bg2"]}; border:1px solid {t["border"]}; '
                    f'border-left:3px solid {t["teal"]}; border-radius:3px; padding:10px 16px; text-align:center;">'
                    f'<div style="font-size:20px; font-weight:700; color:{t["teal2"]}; font-family:Courier New,monospace;">{v}</div>'
                    f'<div style="font-size:0.65rem; color:{t["muted"]}; text-transform:uppercase; '
                    f'letter-spacing:0.1em; font-family:Courier New,monospace; margin-top:2px;">{l}</div>'
                    f'</div>'
                    for v, l in [(len(m_samples), "Samples"), (len(all_cpds), "Compounds"), (len(m_samples)*len(all_cpds), "Matrix Cells")]
                ])}
            </div>
            """, unsafe_allow_html=True)

            section_hdr("PCA Matrix — Raw Absorbance", "rows = samples | cols = compounds | missing = 0")
            st.dataframe(df_pca, use_container_width=True)

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("DOWNLOAD PCA MATRIX", data=pca_out.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"// PCA ERROR: {e}")
