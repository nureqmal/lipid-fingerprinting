import streamlit as st
import pandas as pd
import io
import json
import os

st.set_page_config(page_title="Lipid EQ", layout="wide", page_icon="⚗️" )

# ─── BLACKLIST PERSISTENCE ───────────────────────────────────────────────────
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
    st.session_state.dark_mode = True

# ─── THEME VARIABLES ─────────────────────────────────────────────────────────
def get_theme():
    if st.session_state.dark_mode:
        return {
            "bg":           "#0f1117",
            "bg2":          "#1a1d27",
            "bg3":          "#22263a",
            "surface":      "#1e2235",
            "border":       "#2e3350",
            "accent":       "#4f8ef7",
            "accent2":      "#7c3aed",
            "teal":         "#0fd4a4",
            "text":         "#f0f2ff",
            "muted":        "#8892b0",
            "danger":       "#ff4757",
            "warn":         "#ffa502",
            "success":      "#2ed573",
            "input_bg":     "#22263a",
            "scrollbar":    "#2e3350",
        }
    else:
        return {
            "bg":           "#f0f2fc",
            "bg2":          "#ffffff",
            "bg3":          "#eef1fb",
            "surface":      "#ffffff",
            "border":       "#dde2f5",
            "accent":       "#2563eb",
            "accent2":      "#7c3aed",
            "teal":         "#059669",
            "text":         "#111827",
            "muted":        "#6b7280",
            "danger":       "#dc2626",
            "warn":         "#d97706",
            "success":      "#16a34a",
            "input_bg":     "#f5f7ff",
            "scrollbar":    "#dde2f5",
        }

T = get_theme()

# ─── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    background-color: {T['bg']} !important;
    font-family: 'Inter', sans-serif !important;
    color: {T['text']} !important;
}}

[data-testid="stSidebar"] {{
    background-color: {T['bg2']} !important;
    border-right: 1px solid {T['border']} !important;
}}
[data-testid="stSidebar"] * {{
    color: {T['text']} !important;
    font-family: 'Inter', sans-serif !important;
}}

section.main > div {{
    padding-top: 0.5rem !important;
}}

h1, h2, h3 {{ color: {T['text']} !important; font-family: 'Inter', sans-serif !important; }}

/* Metric cards */
[data-testid="stMetric"] {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    padding: 16px 14px !important;
}}
[data-testid="metric-container"] {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    padding: 16px !important;
}}
[data-testid="stMetricValue"] {{
    color: {T['accent']} !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}}
[data-testid="stMetricLabel"] {{
    color: {T['muted']} !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}}
[data-testid="stMetricDelta"] {{
    font-size: 0.75rem !important;
}}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {T['bg2']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 7px !important;
    color: {T['muted']} !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    border: none !important;
    padding: 6px 12px !important;
    transition: all 0.15s ease !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {T['accent']} !important;
    color: #ffffff !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    display: none !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    display: none !important;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{
    border: 1px solid {T['border']} !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    background: {T['bg2']} !important;
}}
[data-testid="stDataFrame"] thead tr th {{
    background: {T['bg3']} !important;
    color: {T['muted']} !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid {T['border']} !important;
}}
[data-testid="stDataFrame"] tbody tr:hover td {{
    background: {T['bg3']} !important;
}}

/* Buttons */
[data-testid="stButton"] > button {{
    background: linear-gradient(135deg, {T['accent']}, {T['accent2']}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 8px 18px !important;
    transition: opacity 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stButton"] > button:hover {{
    opacity: 0.88 !important;
}}

/* Download button */
[data-testid="stDownloadButton"] > button {{
    background: linear-gradient(135deg, {T['teal']}, {T['accent']}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 8px 20px !important;
}}

/* File uploader */
[data-testid="stFileUploader"] {{
    background: {T['bg2']} !important;
    border: 2px dashed {T['border']} !important;
    border-radius: 12px !important;
    padding: 10px !important;
    transition: border-color 0.2s !important;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: {T['accent']} !important;
}}
[data-testid="stFileUploader"] label {{
    color: {T['text']} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}
[data-testid="stFileUploader"] small {{
    color: {T['muted']} !important;
}}

/* Sliders */
[data-testid="stSlider"] > div > div > div > div {{
    background: {T['accent']} !important;
}}
[data-testid="stSlider"] label {{
    color: {T['text']} !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}}

/* Text input */
[data-testid="stTextInput"] input {{
    background: {T['input_bg']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    color: {T['text']} !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 3px {T['accent']}22 !important;
}}
[data-testid="stTextInput"] label {{
    color: {T['muted']} !important;
    font-size: 0.78rem !important;
}}

/* Alerts */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border: 1px solid {T['border']} !important;
    font-size: 0.82rem !important;
}}
[data-testid="stInfo"] {{
    background: {T['accent']}15 !important;
    border-color: {T['accent']}40 !important;
    color: {T['text']} !important;
}}
[data-testid="stSuccess"] {{
    background: {T['success']}15 !important;
    border-color: {T['success']}40 !important;
    color: {T['text']} !important;
}}
[data-testid="stWarning"] {{
    background: {T['warn']}15 !important;
    border-color: {T['warn']}40 !important;
    color: {T['text']} !important;
}}

/* Sidebar header */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {T['text']} !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}}

/* Sidebar divider */
hr {{
    border-color: {T['border']} !important;
    margin: 0.8rem 0 !important;
}}

/* Checkbox / toggle */
[data-testid="stCheckbox"] label {{
    color: {T['text']} !important;
    font-size: 0.82rem !important;
}}

/* Table */
[data-testid="stTable"] table {{
    background: {T['bg2']} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stTable"] th {{
    background: {T['bg3']} !important;
    color: {T['muted']} !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
}}
[data-testid="stTable"] td {{
    color: {T['text']} !important;
    border-color: {T['border']} !important;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {T['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {T['scrollbar']}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {T['muted']}; }}

/* Columns gap */
[data-testid="column"] {{ padding: 0 6px !important; }}

/* Caption */
[data-testid="stCaptionContainer"] {{
    color: {T['muted']} !important;
    font-size: 0.75rem !important;
}}

/* Expander */
[data-testid="stExpander"] {{
    background: {T['bg2']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary {{
    color: {T['text']} !important;
    font-weight: 500 !important;
}}
</style>
""", unsafe_allow_html=True)

# ─── HEADER ──────────────────────────────────────────────────────────────────
def render_header():
    mode_icon = "🌙" if st.session_state.dark_mode else "☀️"
    mode_label = "Dark Mode" if st.session_state.dark_mode else "Light Mode"
    st.markdown(f"""
    <div style="
        display:flex; align-items:center; justify-content:space-between;
        background:{T['bg2']}; border:1px solid {T['border']}; border-radius:14px;
        padding:14px 22px; margin-bottom:18px;
    ">
        <div style="display:flex; align-items:center; gap:14px;">
            <div style="
                width:42px; height:42px; border-radius:10px;
                background:linear-gradient(135deg,{T['accent']},{T['accent2']});
                display:flex; align-items:center; justify-content:center;
                font-size:16px; font-weight:800; color:#fff;
            ">EQ</div>
            <div>
                <div style="font-size:17px; font-weight:700; color:{T['text']}; letter-spacing:-0.02em;">Lipid EQ</div>
                <div style="font-size:11px; color:{T['muted']}; margin-top:1px;">GC-MS Sorting & Cleaning Platform</div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:20px;">
            <div style="display:flex; gap:6px;">
                <span style="background:{T['accent']}20; color:{T['accent']}; font-size:10px; font-weight:600; padding:3px 10px; border-radius:20px; border:1px solid {T['accent']}40;">v2.0</span>
                <span style="background:{T['teal']}20; color:{T['teal']}; font-size:10px; font-weight:600; padding:3px 10px; border-radius:20px; border:1px solid {T['teal']}40;">HALAL ANALYTICS</span>
            </div>
            <div style="font-size:11px; color:{T['muted']};">{mode_icon} {mode_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_header()

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 12px;">
        <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:{T['accent']}; margin-bottom:2px;">⚗️ Lipid EQ</div>
        <div style="font-size:10px; color:{T['muted']};">Analytical Control Panel</div>
    </div>
    """, unsafe_allow_html=True)

    # Theme toggle
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:6px;'>Display</div>", unsafe_allow_html=True)
    toggle_label = "Switch to Light Mode ☀️" if st.session_state.dark_mode else "Switch to Dark Mode 🌙"
    if st.button(toggle_label, use_container_width=True, key="theme_toggle"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;'>⚙️ Analytical Controls</div>", unsafe_allow_html=True)

    q_threshold = st.slider("NIST Quality Threshold", 50, 95, 80, 5,
        help="Filters compound identity accuracy. (Default: 80)")
    rt_tolerance = st.slider("RT Tolerance (min)", 0.01, 0.20, 0.05, 0.01,
        help="Time error limit for Sample vs Blank comparison. (Default: 0.05)")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01,
        help="Removes small peaks/noise. (Default: 0.00)")

    st.markdown("---")
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:4px;'>🚫 Blacklist Manager</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:10px; color:{T['muted']}; margin-bottom:10px;'>Compounds whose name contains any keyword below will be excluded. Keywords persist across sessions.</div>", unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{T['text']}; margin-bottom:6px;'>Active keywords ({len(st.session_state.blacklist)})</div>", unsafe_allow_html=True)
    for kw in st.session_state.blacklist:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"""
        <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:6px;
            padding:4px 10px; font-size:11px; color:{T['text']}; margin-bottom:2px;">
            {kw}
        </div>""", unsafe_allow_html=True)
        if c2.button("✕", key=f"rm_{kw}", help=f"Remove '{kw}'"):
            st.session_state.blacklist.remove(kw)
            save_blacklist(st.session_state.blacklist)
            st.rerun()

    st.markdown(f"<div style='font-size:11px; font-weight:600; color:{T['text']}; margin:10px 0 4px;'>Add keyword</div>", unsafe_allow_html=True)
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
            st.success(f"✅ '{cleaned}' added!")
            st.rerun()

    st.markdown("")
    if st.button("↺ Reset to Default", use_container_width=True, key="reset_bl"):
        st.session_state.blacklist = DEFAULT_BLACKLIST.copy()
        save_blacklist(st.session_state.blacklist)
        st.rerun()

    st.markdown("---")
    st.markdown(f"""
    <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px;">
        <div style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;">📋 SOP Summary</div>
        {"".join([f'''<div style="display:flex; align-items:flex-start; gap:8px; margin-bottom:6px;">
            <div style="width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg,{T['accent']},{T['accent2']}); display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; color:#fff; flex-shrink:0;">{i}</div>
            <div style="font-size:11px; color:{T['text']}; line-height:1.4;">{s}</div>
        </div>''' for i, s in enumerate([
            "Metadata preserved (rows 1–9)",
            f"Quality gate ≥ {q_threshold}",
            f"Noise cut &lt; {area_threshold:.2f}%",
            f"RT matching ±{rt_tolerance} min",
            f"Blacklist filter ({len(st.session_state.blacklist)} keywords)"
        ], 1)])}
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
    df_excluded = df_excluded.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first').sort_values(by='RT (min)')
    df = df[df['Chemical_Status'] != "Discard (Artifact)"]
    df = df.sort_values(by='Area (Ab*s)', ascending=False).drop_duplicates(subset=['Hit Name'], keep='first')
    return df_header, df.sort_values(by='RT (min)'), df_excluded

def check_match_expert(row, target_df, tol):
    matches = target_df[target_df['Hit Name'] == row['Hit Name']]
    if matches.empty: return "NO", None
    for _, t_row in matches.iterrows():
        if abs(row['RT (min)'] - t_row['RT (min)']) <= tol: return "YES", abs(row['RT (min)'] - t_row['RT (min)'])
    return "RT_SHIFT_DETECTED", matches.apply(lambda r: abs(row['RT (min)'] - r['RT (min)']), axis=1).min()

# ─── SECTION HEADER HELPER ───────────────────────────────────────────────────
def section_header(title, subtitle=""):
    st.markdown(f"""
    <div style="margin:18px 0 10px;">
        <div style="font-size:14px; font-weight:700; color:{T['text']};">{title}</div>
        {f'<div style="font-size:11px; color:{T["muted"]}; margin-top:2px;">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def info_banner(msg, color=None):
    c = color or T['accent']
    st.markdown(f"""
    <div style="background:{c}15; border:1px solid {c}40; border-radius:10px;
        padding:10px 16px; font-size:12px; color:{T['text']}; margin-bottom:10px; line-height:1.6;">
        {msg}
    </div>
    """, unsafe_allow_html=True)

# ─── MAIN TABS ────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊  Single File Analysis", "🔬  Multi-File PCA Matrix"])

# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    info_banner(f"⚠️ Upload your <b>Sample</b> and <b>Blank</b> files in <b>.xlsx</b> format to begin the Lipid EQ pipeline.", T['warn'])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div style="font-size:11px; font-weight:600; color:{T['accent']}; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px;">📤 Sample File</div>""", unsafe_allow_html=True)
        sample_file = st.file_uploader("Upload SAMPLE", type=['xlsx'], key="s_file", label_visibility="collapsed")
    with col2:
        st.markdown(f"""<div style="font-size:11px; font-weight:600; color:{T['accent2']}; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px;">📤 Blank File</div>""", unsafe_allow_html=True)
        blank_file = st.file_uploader("Upload BLANK", type=['xlsx'], key="b_file", label_visibility="collapsed")

    if sample_file and blank_file:
        try:
            h_s, df_s, df_s_excluded = run_strict_procedure(sample_file, q_threshold, area_threshold)
            h_b, df_b, df_b_excluded = run_strict_procedure(blank_file, q_threshold, area_threshold)

            res_s = df_s.apply(lambda r: check_match_expert(r, df_b, rt_tolerance), axis=1)
            df_s['In_Blank'] = [x[0] for x in res_s]
            df_s['RT_Diff'] = [x[1] for x in res_s]
            res_b = df_b.apply(lambda r: check_match_expert(r, df_s, rt_tolerance), axis=1)
            df_b['In_Sample'] = [x[0] for x in res_b]

            df_final = df_s[df_s['In_Blank'].isin(["NO", "RT_SHIFT_DETECTED"])].copy()
            total_sample = len(df_s)
            excluded_blank = len(df_s[df_s['In_Blank'] == "YES"])
            final_count = len(df_final)
            purity = (final_count / total_sample * 100) if total_sample > 0 else 0

            # ── METRICS ──────────────────────────────────────────────────────
            st.markdown(f"""
            <div style="margin:16px 0 10px; font-size:13px; font-weight:700; color:{T['text']};">
                Pipeline Results
                <span style="font-size:10px; font-weight:500; color:{T['muted']}; margin-left:8px;">
                    {sample_file.name}
                </span>
            </div>
            """, unsafe_allow_html=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Sample Peaks", total_sample)
            m2.metric("Blank Matches Purged", excluded_blank, delta=f"-{excluded_blank}", delta_color="inverse")
            m3.metric("Final Unique Compounds", final_count)
            m4.metric("Purity Score", f"{purity:.1f}%",
                help="(Σ Area of Clean Lipid Peaks / Total Original Peak Area) × 100")
            m5.metric("Blacklist Excluded", len(df_s_excluded), delta=f"-{len(df_s_excluded)}", delta_color="inverse")

            st.markdown("<div style='margin:6px 0'></div>", unsafe_allow_html=True)

            # ── INNER TABS ───────────────────────────────────────────────────
            t1, t2, t3, t4, t5 = st.tabs([
                "1. Solvent Blank", "2. Sample Mapping",
                "3. Final Fingerprint", "4. RT Analysis", "5. Excluded (Blacklist)"
            ])

            with t1:
                section_header("Solvent Blank Profile", "Yellow = matched in sample · Blue RT cell = RT shift detected")
                def hl_blank(row):
                    s = ['' for _ in row.index]
                    if row['In_Sample'] == "YES": return [f'background-color: #FFEB9C; color: #5a4a00' for _ in row.index]
                    if row['In_Sample'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return s
                st.dataframe(df_b.style.apply(hl_blank, axis=1), use_container_width=True)

            with t2:
                section_header("Sample Compound Mapping", "Yellow = found in blank (shared) · Blue RT = shift detected but retained")
                def hl_sample(row):
                    s = ['' for _ in row.index]
                    if row['In_Blank'] == "YES": return [f'background-color: #FFEB9C; color: #5a4a00' for _ in row.index]
                    if row['In_Blank'] == "RT_SHIFT_DETECTED":
                        s[row.index.get_loc('RT (min)')] = 'background-color: #002060; color: white'
                    return s
                st.dataframe(df_s.style.apply(hl_sample, axis=1), use_container_width=True)

            with t3:
                section_header("Final Lipid Fingerprint", "Clean compounds after blank subtraction — ready for reporting")
                def hl_final(row):
                    if row.get('Chemical_Status') == "Review (Potential Contaminant)":
                        return ['background-color: #FFC0CB; color: #5a0020' for _ in row.index]
                    return ['' for _ in row.index]
                st.dataframe(df_final.drop(columns=['In_Blank', 'RT_Diff']).style.apply(hl_final, axis=1), use_container_width=True)

            with t4:
                section_header("RT Shift Analysis", "Compounds with retention time shifts between sample and blank")
                rt_issues = df_s[df_s['In_Blank'] == "RT_SHIFT_DETECTED"]
                if not rt_issues.empty:
                    info_banner(f"Found <b>{len(rt_issues)}</b> compound(s) with RT shift. These are <b>retained</b> in the final fingerprint.", T['warn'])
                    st.table(rt_issues[['Hit Name', 'RT (min)', 'RT_Diff']])
                else:
                    st.success("✅ No significant RT shifts detected.")

            with t5:
                section_header("Excluded Blacklist Compounds", "Originally in raw data — removed because compound name contains a blacklisted keyword")
                st.markdown(f"""
                <div style="background:{T['bg3']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 16px; margin-bottom:14px;">
                    <div style="font-size:11px; font-weight:600; color:{T['text']}; margin-bottom:6px;">Active blacklist keywords</div>
                    <div>{"".join([f'<span style="background:{T["danger"]}18; color:{T["danger"]}; border:1px solid {T["danger"]}35; border-radius:5px; padding:2px 9px; font-size:11px; font-weight:500; margin:2px; display:inline-block;">{kw}</span>' for kw in st.session_state.blacklist])}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"<div style='font-size:12px; font-weight:600; color:{T['danger']}; margin-bottom:6px;'>Sample — Excluded ({len(df_s_excluded)})</div>", unsafe_allow_html=True)
                    if df_s_excluded.empty:
                        st.success("No blacklisted compounds in Sample.")
                    else:
                        st.dataframe(df_s_excluded.style.apply(lambda r: ['background-color:#FFD7D7;color:#5a0000' for _ in r.index], axis=1), use_container_width=True)
                        st.caption(f"🔴 {len(df_s_excluded)} compound(s) — 'Matched Keyword' column shows why each was excluded.")

                with c2:
                    st.markdown(f"<div style='font-size:12px; font-weight:600; color:{T['danger']}; margin-bottom:6px;'>Blank — Excluded ({len(df_b_excluded)})</div>", unsafe_allow_html=True)
                    if df_b_excluded.empty:
                        st.success("No blacklisted compounds in Blank.")
                    else:
                        st.dataframe(df_b_excluded.style.apply(lambda r: ['background-color:#FFD7D7;color:#5a0000' for _ in r.index], axis=1), use_container_width=True)
                        st.caption(f"🔴 {len(df_b_excluded)} compound(s) — 'Matched Keyword' column shows why each was excluded.")

            # ── DOWNLOAD ─────────────────────────────────────────────────────
            st.markdown(f"<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:{T['bg2']}; border:1px solid {T['border']}; border-radius:12px; padding:16px 20px; display:flex; align-items:center; justify-content:space-between; margin-top:8px;">
                <div>
                    <div style="font-size:13px; font-weight:600; color:{T['text']};">Export Report</div>
                    <div style="font-size:11px; color:{T['muted']}; margin-top:2px;">Download full .xlsx report with Dashboard, Analytical Report & Excluded Compounds sheets</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            dl_col1, dl_col2 = st.columns([3, 1])
            with dl_col1:
                custom_filename = st.text_input("Filename", value="SF-HEX-1", key="rename_s",
                    label_visibility="collapsed", placeholder="e.g. SF-HEX-1")
            final_save_name = f"{custom_filename.strip().replace(' ', '_')}.xlsx"

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                wb = writer.book
                header_fmt = wb.add_format({'bold': True, 'font_size': 14, 'bg_color': '#2563eb', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                label_fmt = wb.add_format({'bold': True, 'bg_color': '#EEF1FB', 'border': 1, 'font_name': 'Calibri'})
                val_fmt = wb.add_format({'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                yellow_fmt = wb.add_format({'bg_color': '#FFEB9C', 'border': 1})
                navy_fmt = wb.add_format({'bg_color': '#002060', 'font_color': 'white', 'border': 1})
                pink_fmt = wb.add_format({'bg_color': '#FFC0CB', 'border': 1})
                red_fmt = wb.add_format({'bg_color': '#FFD7D7', 'border': 1})
                red_hdr_fmt = wb.add_format({'bold': True, 'font_size': 12, 'bg_color': '#dc2626', 'font_color': 'white', 'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                red_sub_fmt = wb.add_format({'bold': True, 'bg_color': '#FFD7D7', 'border': 1, 'align': 'center', 'font_name': 'Calibri'})
                note_fmt = wb.add_format({'italic': True, 'font_color': '#dc2626', 'text_wrap': True, 'font_name': 'Calibri'})

                ws_dash = wb.add_worksheet('Dashboard')
                ws_dash.merge_range('B2:F2', 'LIPID EQ — ANALYTICAL SUMMARY REPORT', header_fmt)
                metrics_list = [
                    ('Quality Threshold', q_threshold),
                    ('RT Tolerance (min)', rt_tolerance),
                    ('Area Threshold (%)', area_threshold),
                    ('Total Sample Peaks', total_sample),
                    ('Blank Matches Purged', excluded_blank),
                    ('Final Unique Compounds', final_count),
                    ('Purity Score', f"{purity:.2f}%"),
                    ('Active Blacklist Keywords', len(st.session_state.blacklist)),
                    ('Blacklist Excluded (Sample)', len(df_s_excluded)),
                    ('Blacklist Excluded (Blank)', len(df_b_excluded)),
                ]
                for i, (l, v) in enumerate(metrics_list, start=4):
                    ws_dash.write(f'B{i}', l, label_fmt)
                    ws_dash.write(f'C{i}', v, val_fmt)
                kw_row = 4 + len(metrics_list) + 1
                ws_dash.write(f'B{kw_row}', 'Blacklist Keywords Used', label_fmt)
                ws_dash.write(f'C{kw_row}', ', '.join(st.session_state.blacklist), wb.add_format({'border': 1, 'text_wrap': True, 'font_name': 'Calibri'}))
                ws_dash.set_row(kw_row - 1, 28)
                legend_row = kw_row + 2
                ws_dash.write(f'B{legend_row}', 'COLOR LEGEND', wb.add_format({'bold': True, 'underline': True, 'font_name': 'Calibri'}))
                ws_dash.write(f'B{legend_row+1}', 'Yellow Row', yellow_fmt); ws_dash.write(f'C{legend_row+1}', 'Matched in Blank/Sample (Shared Compound)')
                ws_dash.write(f'B{legend_row+2}', 'Blue RT Cell', navy_fmt); ws_dash.write(f'C{legend_row+2}', 'RT Shift Detected (Retained)')
                ws_dash.write(f'B{legend_row+3}', 'Pink Cell', pink_fmt); ws_dash.write(f'C{legend_row+3}', 'Potential Contaminant')
                ws_dash.write(f'B{legend_row+4}', 'Red Row', red_fmt); ws_dash.write(f'C{legend_row+4}', 'Excluded Blacklist Artifact (Full Name Preserved)')
                ws_dash.set_column('B:B', 32); ws_dash.set_column('C:C', 80)

                rs = 'Analytical_Report'
                h_b.to_excel(writer, sheet_name=rs, startrow=2, index=False, header=False)
                df_b.to_excel(writer, sheet_name=rs, startrow=11, index=False, header=False)
                s2 = len(df_b) + 16
                h_s.to_excel(writer, sheet_name=rs, startrow=s2+1, index=False, header=False)
                df_s.to_excel(writer, sheet_name=rs, startrow=s2+10, index=False, header=False)
                s3 = s2 + len(df_s) + 15
                fh = h_s.copy(); fh.iloc[0, 0] = f"{fh.iloc[0,0]} (Clean Version ✅)"
                fh.to_excel(writer, sheet_name=rs, startrow=s3+1, index=False, header=False)
                df_final.drop(columns=['In_Blank', 'RT_Diff']).to_excel(writer, sheet_name=rs, startrow=s3+10, index=False, header=False)
                ws_rep = writer.sheets[rs]
                b_rt_idx = df_b.columns.get_loc('RT (min)'); b_match_idx = df_b.columns.get_loc('In_Sample')
                ws_rep.conditional_format(11, 0, 11+len(df_b), len(df_b.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65+b_match_idx)}12="YES"', 'format': yellow_fmt})
                ws_rep.conditional_format(11, b_rt_idx, 11+len(df_b), b_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65+b_match_idx)}12="RT_SHIFT_DETECTED"', 'format': navy_fmt})
                s_rt_idx = df_s.columns.get_loc('RT (min)'); s_match_idx = df_s.columns.get_loc('In_Blank')
                ws_rep.conditional_format(s2+10, 0, s2+10+len(df_s), len(df_s.columns)-1, {'type': 'formula', 'criteria': f'=${chr(65+s_match_idx)}{s2+11}="YES"', 'format': yellow_fmt})
                ws_rep.conditional_format(s2+10, s_rt_idx, s2+10+len(df_s), s_rt_idx, {'type': 'formula', 'criteria': f'=${chr(65+s_match_idx)}{s2+11}="RT_SHIFT_DETECTED"', 'format': navy_fmt})
                f_status_idx = df_final.columns.get_loc('Chemical_Status')
                ws_rep.conditional_format(s3+10, f_status_idx, s3+10+len(df_final), f_status_idx, {'type': 'cell', 'criteria': 'equal to', 'value': '"Review (Potential Contaminant)"', 'format': pink_fmt})

                ws_excl = wb.add_worksheet('Excluded_Compounds')
                max_cols = max(len(df_s_excluded.columns) if not df_s_excluded.empty else 6, len(df_b_excluded.columns) if not df_b_excluded.empty else 6)
                lc = chr(64 + min(max_cols, 26))
                ws_excl.merge_range(f'A1:{lc}1', '⛔ EXCLUDED BLACKLIST COMPOUNDS — Originally Present in Raw Data', red_hdr_fmt)
                ws_excl.merge_range(f'A2:{lc}2', f'NOTE: Removed because compound name contains a blacklisted keyword. Active keywords: {", ".join(st.session_state.blacklist)}. See "Matched Keyword" column per row.', note_fmt)
                ws_excl.set_row(1, 42)
                ws_excl.merge_range(f'A4:{lc}4', 'SAMPLE — Excluded Blacklist Compounds', red_sub_fmt)
                if not df_s_excluded.empty:
                    for ci, cn in enumerate(df_s_excluded.columns): ws_excl.write(4, ci, cn, label_fmt)
                    for ri, (_, row) in enumerate(df_s_excluded.iterrows()):
                        for ci, val in enumerate(row): ws_excl.write(5+ri, ci, val, red_fmt)
                    se = 5 + len(df_s_excluded)
                else:
                    ws_excl.write(4, 0, 'No blacklisted compounds found in Sample.', wb.add_format({'italic': True, 'font_color': '#888'}))
                    se = 6
                bs = se + 2
                ws_excl.merge_range(f'A{bs}:{lc}{bs}', 'BLANK — Excluded Blacklist Compounds', red_sub_fmt)
                if not df_b_excluded.empty:
                    for ci, cn in enumerate(df_b_excluded.columns): ws_excl.write(bs, ci, cn, label_fmt)
                    for ri, (_, row) in enumerate(df_b_excluded.iterrows()):
                        for ci, val in enumerate(row): ws_excl.write(bs+1+ri, ci, val, red_fmt)
                else:
                    ws_excl.write(bs, 0, 'No blacklisted compounds found in Blank.', wb.add_format({'italic': True, 'font_color': '#888'}))
                ws_excl.set_column('A:A', 48); ws_excl.set_column('B:G', 18)

            with dl_col2:
                st.download_button("⬇️ Download Report", data=output.getvalue(), file_name=final_save_name, use_container_width=True)

        except Exception as e:
            st.error(f"Pipeline error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    <div style="font-size:22px; font-weight:700; color:{T['text']}; margin-bottom:4px; letter-spacing:-0.02em;">Multi-File PCA Matrix</div>
    <div style="font-size:13px; color:{T['muted']}; margin-bottom:18px;">Upload one blank and multiple sample files to generate a compound × sample matrix ready for PCA.</div>
    """, unsafe_allow_html=True)

    info_banner(f"⚠️ All files must be in <b>.xlsx</b> format. The same analytical controls from the sidebar apply.", T['warn'])

    col_b, col_s = st.columns(2)
    with col_b:
        st.markdown(f"""<div style="font-size:11px; font-weight:600; color:{T['accent2']}; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px;">📤 Blank File (one)</div>""", unsafe_allow_html=True)
        m_blank = st.file_uploader("Blank", type=['xlsx'], key="m_b", label_visibility="collapsed")
    with col_s:
        st.markdown(f"""<div style="font-size:11px; font-weight:600; color:{T['accent']}; text-transform:uppercase; letter-spacing:0.07em; margin-bottom:6px;">📤 Sample Files (multiple)</div>""", unsafe_allow_html=True)
        m_samples = st.file_uploader("Samples", type=['xlsx'], accept_multiple_files=True, key="m_s", label_visibility="collapsed")

    if m_blank and m_samples:
        try:
            _, df_b_multi, _ = run_strict_procedure(m_blank, q_threshold, area_threshold)
            pca_list, all_compounds = [], set()
            progress = st.progress(0, text="Processing files...")
            for i, s_f in enumerate(m_samples):
                _, df_s_raw, _ = run_strict_procedure(s_f, q_threshold, area_threshold)
                res = df_s_raw.apply(lambda r: check_match_expert(r, df_b_multi, rt_tolerance), axis=1)
                df_clean = df_s_raw[res.apply(lambda x: x[0] in ["NO", "RT_SHIFT_DETECTED"])].copy()
                s_dict = {row['Hit Name']: row['Area (Ab*s)'] for _, row in df_clean.iterrows()}
                s_dict['Sample Name'] = s_f.name
                pca_list.append(s_dict)
                all_compounds.update(df_clean['Hit Name'].tolist())
                progress.progress((i+1)/len(m_samples), text=f"Processing {s_f.name}...")
            progress.empty()

            df_pca = pd.DataFrame(pca_list)
            df_pca = df_pca.reindex(columns=['Sample Name'] + sorted(list(all_compounds))).fillna(0)

            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:16px; margin:14px 0 10px;">
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['accent']};">{len(m_samples)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Samples</div>
                </div>
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['teal']};">{len(all_compounds)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Unique Compounds</div>
                </div>
                <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:10px; padding:12px 18px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{T['accent2']};">{len(m_samples) * len(all_compounds)}</div>
                    <div style="font-size:10px; color:{T['muted']}; text-transform:uppercase; letter-spacing:0.06em;">Matrix Cells</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            section_header("PCA Matrix — Raw Absorbance", "Rows = samples · Columns = compounds · Missing values filled with 0")
            st.dataframe(df_pca, use_container_width=True)

            pca_out = io.BytesIO()
            with pd.ExcelWriter(pca_out, engine='xlsxwriter') as writer:
                df_pca.to_excel(writer, sheet_name='PCA_Data', index=False)
            st.download_button("⬇️ Download PCA Matrix", data=pca_out.getvalue(), file_name="PCA_Matrix_Ready.xlsx")

        except Exception as e:
            st.error(f"PCA error: {e}")
