"""Shared theme (dark/light tokens) and global CSS, used by every page."""

import streamlit as st


def get_theme():
    if st.session_state.get('dark_mode', True):
        return {
            "bg": "#0f1117", "bg2": "#1a1d27", "bg3": "#22263a",
            "surface": "#1e2235", "border": "#2e3350",
            "accent": "#4f8ef7", "accent2": "#7c3aed", "teal": "#0fd4a4",
            "text": "#f0f2ff", "muted": "#8892b0",
            "danger": "#ff4757", "warn": "#ffa502", "success": "#2ed573",
            "input_bg": "#22263a", "scrollbar": "#2e3350",
        }
    return {
        "bg": "#f0f2fc", "bg2": "#ffffff", "bg3": "#eef1fb",
        "surface": "#ffffff", "border": "#dde2f5",
        "accent": "#2563eb", "accent2": "#7c3aed", "teal": "#059669",
        "text": "#111827", "muted": "#6b7280",
        "danger": "#dc2626", "warn": "#d97706", "success": "#16a34a",
        "input_bg": "#f5f7ff", "scrollbar": "#dde2f5",
    }


def apply_global_css(T):
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
    section.main > div {{ padding-top: 0.5rem !important; }}
    h1, h2, h3 {{ color: {T['text']} !important; font-family: 'Inter', sans-serif !important; }}

    [data-testid="stMetric"], [data-testid="metric-container"] {{
        background: {T['surface']} !important;
        border: 1px solid {T['border']} !important;
        border-radius: 12px !important;
        padding: 16px 14px !important;
    }}
    [data-testid="stMetricValue"] {{
        color: {T['accent']} !important; font-size: 1.6rem !important; font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {T['muted']} !important; font-size: 0.75rem !important;
        text-transform: uppercase !important; letter-spacing: 0.06em !important;
    }}
    [data-testid="stMetricDelta"] {{ font-size: 0.75rem !important; }}

    [data-testid="stTabs"] [data-baseweb="tab-list"] {{
        background: {T['bg2']} !important; border: 1px solid {T['border']} !important;
        border-radius: 10px !important; padding: 4px !important; gap: 4px !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab"] {{
        background: transparent !important; border-radius: 7px !important;
        color: {T['muted']} !important; font-size: 0.78rem !important; font-weight: 500 !important;
        border: none !important; padding: 6px 12px !important; transition: all 0.15s ease !important;
    }}
    [data-testid="stTabs"] [aria-selected="true"] {{
        background: {T['accent']} !important; color: #ffffff !important;
    }}
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ display: none !important; }}
    [data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}

    [data-testid="stDataFrame"] {{
        border: 1px solid {T['border']} !important; border-radius: 12px !important;
        overflow: hidden !important; background: {T['bg2']} !important;
    }}
    [data-testid="stDataFrame"] thead tr th {{
        background: {T['bg3']} !important; color: {T['muted']} !important;
        font-size: 0.72rem !important; font-weight: 600 !important;
        text-transform: uppercase !important; letter-spacing: 0.06em !important;
        border-bottom: 1px solid {T['border']} !important;
    }}
    [data-testid="stDataFrame"] tbody tr:hover td {{ background: {T['bg3']} !important; }}

    [data-testid="stButton"] > button {{
        background: linear-gradient(135deg, {T['accent']}, {T['accent2']}) !important;
        color: #ffffff !important; border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 0.82rem !important; padding: 8px 18px !important;
        transition: opacity 0.2s ease !important; font-family: 'Inter', sans-serif !important;
    }}
    [data-testid="stButton"] > button:hover {{ opacity: 0.88 !important; }}

    [data-testid="stDownloadButton"] > button {{
        background: linear-gradient(135deg, {T['teal']}, {T['accent']}) !important;
        color: #ffffff !important; border: none !important; border-radius: 8px !important;
        font-weight: 600 !important; font-size: 0.82rem !important; padding: 8px 20px !important;
    }}

    [data-testid="stFileUploader"] {{
        background: {T['bg2']} !important; border: 2px dashed {T['border']} !important;
        border-radius: 12px !important; padding: 10px !important; transition: border-color 0.2s !important;
    }}
    [data-testid="stFileUploader"]:hover {{ border-color: {T['accent']} !important; }}
    [data-testid="stFileUploader"] label {{ color: {T['text']} !important; font-weight: 500 !important; font-size: 0.85rem !important; }}
    [data-testid="stFileUploader"] small {{ color: {T['muted']} !important; }}

    [data-testid="stSlider"] > div > div > div > div {{ background: {T['accent']} !important; }}
    [data-testid="stSlider"] label {{ color: {T['text']} !important; font-size: 0.82rem !important; font-weight: 500 !important; }}

    [data-testid="stTextInput"] input {{
        background: {T['input_bg']} !important; border: 1px solid {T['border']} !important;
        border-radius: 8px !important; color: {T['text']} !important; font-family: 'Inter', sans-serif !important;
    }}
    [data-testid="stTextInput"] input:focus {{
        border-color: {T['accent']} !important; box-shadow: 0 0 0 3px {T['accent']}22 !important;
    }}
    [data-testid="stTextInput"] label {{ color: {T['muted']} !important; font-size: 0.78rem !important; }}

    [data-testid="stSelectbox"] label {{ color: {T['muted']} !important; font-size: 0.78rem !important; }}

    [data-testid="stAlert"] {{ border-radius: 10px !important; border: 1px solid {T['border']} !important; font-size: 0.82rem !important; }}
    [data-testid="stInfo"] {{ background: {T['accent']}15 !important; border-color: {T['accent']}40 !important; color: {T['text']} !important; }}
    [data-testid="stSuccess"] {{ background: {T['success']}15 !important; border-color: {T['success']}40 !important; color: {T['text']} !important; }}
    [data-testid="stWarning"] {{ background: {T['warn']}15 !important; border-color: {T['warn']}40 !important; color: {T['text']} !important; }}

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {T['text']} !important; font-size: 0.72rem !important; font-weight: 700 !important;
        text-transform: uppercase !important; letter-spacing: 0.08em !important;
    }}
    hr {{ border-color: {T['border']} !important; margin: 0.8rem 0 !important; }}
    [data-testid="stCheckbox"] label {{ color: {T['text']} !important; font-size: 0.82rem !important; }}

    [data-testid="stTable"] table {{ background: {T['bg2']} !important; border-radius: 10px !important; overflow: hidden !important; }}
    [data-testid="stTable"] th {{ background: {T['bg3']} !important; color: {T['muted']} !important; font-size: 0.72rem !important; text-transform: uppercase !important; }}
    [data-testid="stTable"] td {{ color: {T['text']} !important; border-color: {T['border']} !important; }}

    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {T['bg']}; }}
    ::-webkit-scrollbar-thumb {{ background: {T['scrollbar']}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {T['muted']}; }}

    [data-testid="column"] {{ padding: 0 6px !important; }}
    [data-testid="stCaptionContainer"] {{ color: {T['muted']} !important; font-size: 0.75rem !important; }}

    [data-testid="stExpander"] {{ background: {T['bg2']} !important; border: 1px solid {T['border']} !important; border-radius: 10px !important; }}
    [data-testid="stExpander"] summary {{ color: {T['text']} !important; font-weight: 500 !important; }}

    [data-testid="stPageLink"] {{ border-radius: 8px !important; }}
    </style>
    """, unsafe_allow_html=True)


def render_header(T, subtitle="GC-MS Sorting & Cleaning Platform"):
    mode_icon = "🌙" if st.session_state.get('dark_mode', True) else "☀️"
    mode_label = "Dark Mode" if st.session_state.get('dark_mode', True) else "Light Mode"
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
                <div style="font-size:11px; color:{T['muted']}; margin-top:1px;">{subtitle}</div>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:20px;">
            <div style="display:flex; gap:6px;">
                <span style="background:{T['accent']}20; color:{T['accent']}; font-size:10px; font-weight:600; padding:3px 10px; border-radius:20px; border:1px solid {T['accent']}40;">v3.0</span>
                <span style="background:{T['teal']}20; color:{T['teal']}; font-size:10px; font-weight:600; padding:3px 10px; border-radius:20px; border:1px solid {T['teal']}40;">HALAL ANALYTICS</span>
            </div>
            <div style="font-size:11px; color:{T['muted']};">{mode_icon} {mode_label}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
