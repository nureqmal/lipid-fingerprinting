import streamlit as st
from lib import db, pipeline
from lib.theme import get_theme, apply_global_css, render_header
from lib.sidebar import render_common_sidebar
from lib.ui import section_header, info_banner

st.set_page_config(page_title="Lipid EQ — Blank Library", layout="wide", page_icon="📦")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

db.init_db()
T = get_theme()
apply_global_css(T)
render_header(T, subtitle="Blank Library")

with st.sidebar:
    blacklist = render_common_sidebar(T)
    st.markdown(f"<div style='font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:{T['muted']}; margin-bottom:8px;'>⚙️ Parsing Controls</div>", unsafe_allow_html=True)
    q_threshold = st.slider("NIST Quality Threshold", 50, 95, 80, 5, key="lib_q",
        help="Same quality gate used when parsing this blank file.")
    area_threshold = st.slider("Min Area % (Noise Filter)", 0.00, 5.00, 0.00, 0.01, key="lib_area")

st.markdown(f"""
<div style="font-size:22px; font-weight:700; color:{T['text']}; margin-bottom:4px; letter-spacing:-0.02em;">Blank Library</div>
<div style="font-size:13px; color:{T['muted']}; margin-bottom:18px;">Upload Solvent, Method, Carryover, and Reagent blanks here, tagged to a batch. The Pipeline page automatically pools all blanks tagged to a sample's batch.</div>
""", unsafe_allow_html=True)

batches = db.list_batches()

if batches.empty:
    info_banner(T, "⚠️ No batches exist yet. Go to <b>Batch Settings</b> first and create a batch (e.g. by solvent system) before uploading blanks.", T['warn'])
    st.stop()

section_header(T, "Upload a new blank", "It will be parsed with the controls above and added to the selected batch's pool")

c1, c2 = st.columns(2)
with c1:
    batch_name_to_id = {row['name']: int(row['id']) for _, row in batches.iterrows()}
    sel_batch_name = st.selectbox("Batch", options=list(batch_name_to_id.keys()))
    sel_batch_id = batch_name_to_id[sel_batch_name]
with c2:
    blank_type = st.selectbox("Blank type", options=db.BLANK_TYPES,
        help="Solvent = pure solvent only. Method = full extraction run with no sample. Carryover = solvent injected after a concentrated/high-adulteration sample. Reagent = blank for reagents like NADES.")

blank_file = st.file_uploader("Upload blank (.xlsx)", type=['xlsx'], key="blank_upload")

if blank_file is not None:
    try:
        _, df_clean, df_excluded = pipeline.run_strict_procedure(blank_file, q_threshold, area_threshold, blacklist)
        st.success(f"Parsed **{len(df_clean)}** clean compound(s) and excluded **{len(df_excluded)}** blacklisted artifact(s) from this blank.")
        st.dataframe(df_clean[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status']], width='stretch')

        if st.button("💾 Save to Blank Library", width='stretch'):
            upload_id = db.add_blank_upload(
                sel_batch_id, blank_type, blank_file.name, q_threshold, area_threshold,
                df_clean[['Hit Name', 'RT (min)', 'Area (Ab*s)', 'Area (%)', 'Quality', 'Chemical_Status']]
            )
            st.success(f"✅ Saved as a **{blank_type}** blank under batch **{sel_batch_name}** (upload id {upload_id}).")
            st.rerun()
    except Exception as e:
        st.error(f"Could not parse this file: {e}")

st.markdown(f"<div style='height:14px'></div>", unsafe_allow_html=True)
section_header(T, "Blank pool by batch", "What the Pipeline page will combine for blank subtraction")

for _, brow in batches.iterrows():
    bid = int(brow['id'])
    with st.expander(f"📦 {brow['name']}  ·  {brow['solvent_system']}  ·  {brow['n_blanks']} blank file(s)", expanded=False):
        summary = db.pool_summary(bid)
        if summary.empty:
            st.info("No blanks uploaded for this batch yet.")
        else:
            st.dataframe(summary, width='stretch', hide_index=True)

        blanks_df = db.list_blanks(bid)
        if not blanks_df.empty:
            st.markdown(f"<div style='font-size:11px; font-weight:600; color:{T['text']}; margin:10px 0 6px;'>Uploaded blank files</div>", unsafe_allow_html=True)
            for _, row in blanks_df.iterrows():
                cc1, cc2, cc3, cc4 = st.columns([2, 3, 2, 1])
                cc1.markdown(f"<span style='background:{T['accent']}20; color:{T['accent']}; font-size:10px; font-weight:600; padding:2px 8px; border-radius:6px;'>{row['blank_type']}</span>", unsafe_allow_html=True)
                cc2.markdown(f"<span style='font-size:12px;'>{row['filename']}</span>", unsafe_allow_html=True)
                cc3.markdown(f"<span style='color:{T['muted']}; font-size:11px;'>{row['n_compounds']} compounds</span>", unsafe_allow_html=True)
                if cc4.button("🗑️", key=f"del_blank_{row['id']}"):
                    db.delete_blank_upload(int(row['id']))
                    st.rerun()
