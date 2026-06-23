import streamlit as st
from lib import db
from lib.theme import get_theme, apply_global_css, render_header

st.set_page_config(page_title="Lipid EQ", layout="wide", page_icon="⚗️")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()

T = get_theme()
apply_global_css(T)
render_header(T)

with st.sidebar:
    st.markdown(f"""
    <div style="padding:4px 0 12px;">
        <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:{T['accent']}; margin-bottom:2px;">⚗️ Lipid EQ</div>
        <div style="font-size:10px; color:{T['muted']};">Analytical Control Panel</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:6px;'>Display</div>", unsafe_allow_html=True)
    toggle_label = "Switch to Light Mode ☀️" if st.session_state.dark_mode else "Switch to Dark Mode 🌙"
    if st.button(toggle_label, width='stretch', key="theme_toggle_home"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown("---")
    st.markdown(f"<div style='font-size:10px; color:{T['muted']};'>Use the page navigation above to get started.</div>", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:22px; font-weight:700; color:{T['text']}; margin-bottom:4px; letter-spacing:-0.02em;">Welcome to Lipid EQ v3</div>
<div style="font-size:13px; color:{T['muted']}; margin-bottom:20px;">Halal authentication pipeline for GC-MS lipid fingerprinting — now with a proper Blank Pool model.</div>
""", unsafe_allow_html=True)

batches = db.list_batches()
blacklist = db.get_blacklist()

m1, m2, m3 = st.columns(3)
m1.metric("Batches Configured", len(batches))
m2.metric("Total Blanks in Library", int(batches['n_blanks'].sum()) if not batches.empty else 0)
m3.metric("Active Blacklist Keywords", len(blacklist))

st.markdown(f"<div style='height:8px'></div>", unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:13px; font-weight:700; color:{T['text']}; margin:18px 0 10px;">What changed in v3</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:{T['bg2']}; border:1px solid {T['border']}; border-radius:12px; padding:18px 22px; line-height:1.7; font-size:13px; color:{T['text']};">
<b>v2</b> compared one sample against exactly one uploaded blank file.<br>
<b>v3</b> compares one sample against a <b>Blank Pool</b> — every solvent, method, carryover, and reagent blank tagged to that sample's batch — and records <i>which blank type</i> caused each peak to be purged.
<br><br>
<b>Recommended workflow:</b>
<ol style="margin:6px 0 0 18px; padding:0;">
<li>Go to <b>Batch Settings</b> and create a batch for each solvent system (e.g. "Hexane Batch 1").</li>
<li>Go to <b>Blank Library</b> and upload your Solvent / Method / Carryover blanks, tagged to that batch.</li>
<li>Go to <b>Pipeline</b>, pick the batch for your sample, and run the analysis — blank subtraction now uses the full pool automatically.</li>
</ol>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div style='height:18px'></div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
    <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:12px; padding:16px;">
        <div style="font-size:13px; font-weight:700; color:{T['accent']}; margin-bottom:4px;">🧪 Pipeline</div>
        <div style="font-size:11px; color:{T['muted']}; line-height:1.5;">Run single-file analysis or build the multi-sample PCA matrix.</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_🧪_Pipeline.py", label="Open Pipeline", icon="🧪")
with c2:
    st.markdown(f"""
    <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:12px; padding:16px;">
        <div style="font-size:13px; font-weight:700; color:{T['teal']}; margin-bottom:4px;">📦 Blank Library</div>
        <div style="font-size:11px; color:{T['muted']}; line-height:1.5;">Upload and tag Solvent / Method / Carryover / Reagent blanks.</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_📦_Blank_Library.py", label="Open Blank Library", icon="📦")
with c3:
    st.markdown(f"""
    <div style="background:{T['surface']}; border:1px solid {T['border']}; border-radius:12px; padding:16px;">
        <div style="font-size:13px; font-weight:700; color:{T['accent2']}; margin-bottom:4px;">⚙️ Batch Settings</div>
        <div style="font-size:11px; color:{T['muted']}; line-height:1.5;">Create and manage solvent/extraction batches.</div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_⚙️_Batch_Settings.py", label="Open Batch Settings", icon="⚙️")

if batches.empty:
    st.markdown(f"<div style='height:14px'></div>", unsafe_allow_html=True)
    st.warning("No batches configured yet. Start at **Batch Settings** to create your first batch (e.g. by solvent system).")
